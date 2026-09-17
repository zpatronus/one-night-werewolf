"""HTTP API views for One Night Werewolf.

Everything the frontend asks for is POST with credentials in the JSON body
(never in the URL), so ``roomid/userid/userpsw`` are simple strings. All
responses are ``{"ok": bool, ...}`` and always HTTP 200; failures carry a
stable English error code the frontend ``gameConfig`` maps to Chinese.

No timers / no threads: each endpoint skeleton step 3 calls ``_advance``, which
settles a phase exactly once when its end condition holds (see design.md
``%6.5``). The DB is the single source of truth; every phase-1 / vote write is
a conditional ``UPDATE`` gated on ``room.phase`` so a late/duplicate request is
harmless.
"""
import json
import re

from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone

from onw_backend.config import OPS_DURATION, IS_DEV
from . import game
from .avatars import AVATARS
from .models import Room, Player


_RE_ROOMID = re.compile(r"^[A-Za-z0-9]{1,6}$")
_RE_USERID = re.compile(r"^[A-Za-z0-9_]{1,7}$")
_RE_PSW = re.compile(r"^[A-Za-z0-9]{1,6}$")


class ApiError(Exception):
    def __init__(self, code):
        self.code = code


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _err(code):
    return JsonResponse({"ok": False, "error": code})


def _body(request):
    if request.method != "POST":
        raise ApiError("method_not_allowed")
    try:
        body = json.loads(request.body or b"{}")
        if not isinstance(body, dict):
            raise ApiError("bad_request")
        return body
    except (ValueError, TypeError):
        raise ApiError("bad_request")


def _auth(request):
    """Resolve and authenticate caller's credentials against a room."""
    body = _body(request)
    c = _load(body, ["roomid", "userid", "userpsw"], [_RE_ROOMID, _RE_USERID, _RE_PSW])
    roomid, userid, userpsw = c["roomid"], c["userid"], c["userpsw"]

    room = Room.objects.filter(roomid=roomid).first()
    if room is None:
        raise ApiError("room_not_found")
    player = Player.objects.filter(room=room, userid=userid).first()
    if player is None or player.userpsw != userpsw:
        raise ApiError("bad_credentials")
    return body, room, player


def _load(body, keys, regexes, err="bad_request"):
    values = {}
    for key, regex in zip(keys, regexes):
        v = body.get(key, "")
        if not isinstance(v, str) or not regex.fullmatch(v):
            raise ApiError(err)
        values[key] = v
    return values


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------

def _waiting_payload(room, player):
    users = [{"userid": p.userid, "avatar": p.avatar} for p in room.players.all()]
    return {
        "ok": True,
        "phase": "waiting",
        "users": users,  # entries already carry {userid, avatar}
        "userCount": len(users),
        "host": room.owner.userid if room.owner else None,
        "is_owner": bool(room.owner_id == player.id),
        "board": room.board,
    }


def _op_payload(room, player, deadline):
    total = room.players.count()
    submitted = room.players.exclude(choice={}).count()
    # each player's op is confidential — never expose who has/hasn't submitted
    # or anyone's choice; only this caller's own ``my_choice`` and a total count.
    users = [{"userid": p.userid, "avatar": p.avatar} for p in room.players.all()]
    return {
        "ok": True,
        "phase": "op",
        "role": player.display_role,
        "my_choice": player.choice,
        "submitted": bool(player.choice),
        "submitted_count": submitted,
        "total_count": total,
        "deadline_ms": deadline,
        "op_end_time_ms": int((room.op_start_time + OPS_DURATION).timestamp() * 1000)
        if room.op_start_time else None,
        "users": users,
    }


def _reveal_payload(room, player):
    # minimal: this caller only needs their own vote state. Who has voted is
    # nobody's business and must not be in the API response. vote_target is the
    # caller's own pick ("" = abstain, else a userid) so they can re-highlight
    # their choice after a refresh/rejoin.
    return {
        "ok": True,
        "phase": "reveal",
        "voted": player.vote_target is not None,
        "vote_target": player.vote_target,
    }


def _deadline_ms(room):
    if not room.op_start_time:
        return 0
    remaining = (room.op_start_time + OPS_DURATION) - timezone.now()
    ms = remaining.total_seconds() * 1000
    return max(0, int(ms))


# ---------------------------------------------------------------------------
# Progress / settlement (trigger exactly once when its condition holds)
# ---------------------------------------------------------------------------

def _advance(room):
    """Trigger the next phase exactly once when its end condition holds.

    op -> reveal only when the deadline passes; reveal -> result
    when everyone has voted. Only the caller that first observes the end
    condition wins the conditional UPDATE (SQLite serializes its first write),
    so the resolver runs exactly once.
    """
    room.refresh_from_db()

    if room.phase == "op":
        if IS_DEV:
            # Development: advance only when BOTH the deadline has passed AND
            # every player has operated. A stuck player is then impossible to
            # miss. Not applied in production (see below).
            timed_out = room.op_start_time and timezone.now() >= room.op_start_time + OPS_DURATION
            all_operated = room.players.exclude(choice={}).count() == room.players.count()
            advance = timed_out and all_operated
        else:
            # Production (anti-cheat, design.md ``%5``): op -> reveal fires ONLY
            # when the deadline passes. It must NOT advance when everyone has
            # submitted — that would let ring-late players infer who was done
            # early. So everyone waits out the full timer regardless of state.
            timed_out = room.op_start_time and timezone.now() >= room.op_start_time + OPS_DURATION
            advance = timed_out
        if advance:
            with transaction.atomic():
                claimed = Room.objects.filter(
                    id=room.id, phase="op"
                ).update(phase="reveal")
                if claimed:
                    claimed_room = Room.objects.get(id=room.id)
                    game.run_resolver(claimed_room)
            room.refresh_from_db()

    if room.phase == "reveal":
        players = list(room.players.all())
        if players and all(p.vote_target is not None for p in players):
            Room.objects.filter(id=room.id, phase="reveal").update(phase="result")
            room.refresh_from_db()


# ---------------------------------------------------------------------------
# Choice validation (phase 1)
# ---------------------------------------------------------------------------

def _valid_choice(room, player, choice):
    return game.valid_choice(player.display_role, player.userid,
                             room.players.values_list("userid", flat=True), choice)


def _avatar(value):
    return value if isinstance(value, str) and value in AVATARS else (AVATARS[0] if AVATARS else "")


def _lock_room(room):
    # First statement inside atomic is a write: SQLite serializes join/start/actions.
    Room.objects.filter(pk=room.pk).update(phase=F("phase"))
    room.refresh_from_db()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def csrf(request):
    if request.method != "GET":
        return _err("method_not_allowed")
    return JsonResponse({"ok": True, "csrf_token": get_token(request)})


def create_room(request):
    try:
        body = _body(request)
        c = _load(body, ["roomid", "userid", "userpsw"],
                  [_RE_ROOMID, _RE_USERID, _RE_PSW])
        avatar = _avatar(body.get("avatar"))
        if Room.objects.filter(roomid=c["roomid"]).exists():
            raise ApiError("roomid_taken")
        # A saved template targets a future group, not the lone creator.
        # Invalid or missing drafts must never prevent room creation.
        board = body.get("board")
        if not game.valid_board_shape(board) or not game.validate_board(
            board, sum(board.values()) - 3
        ):
            board = game.board_template()
        with transaction.atomic():
            room = Room.objects.create(roomid=c["roomid"], board=board)
            player = Player.objects.create(
                room=room, userid=c["userid"], userpsw=c["userpsw"], avatar=avatar,
            )
            room.owner = player
            room.save(update_fields=["owner"])
        return JsonResponse({"ok": True, "avatar": player.avatar})
    except IntegrityError:
        return _err("roomid_taken")
    except ApiError as e:
        return _err(e.code)


def join_room(request):
    try:
        body = _body(request)
        c = _load(body, ["roomid", "userid", "userpsw"],
                  [_RE_ROOMID, _RE_USERID, _RE_PSW])
        avatar = _avatar(body.get("avatar"))
        room = Room.objects.filter(roomid=c["roomid"]).first()
        if room is None:
            raise ApiError("room_not_found")
        with transaction.atomic():
            _lock_room(room)
            player = Player.objects.filter(room=room, userid=c["userid"]).first()
            if player is not None:
                if player.userpsw != c["userpsw"]:
                    raise ApiError("wrong_password")
            else:
                if room.phase != "waiting":
                    raise ApiError("room_started")
                if room.players.count() >= game.MAX_PLAYERS:
                    raise ApiError("room_full")
                player = Player.objects.create(
                    room=room, userid=c["userid"], userpsw=c["userpsw"], avatar=avatar,
                )
        # Return the live room status so the client can route straight to the
        # right view (op/reveal/result) on a rejoin, instead of always glancing
        # at the waiting room first. ``_room_status`` already carries ``phase``
        # plus the full phase payload; avatar is patched on for the client.
        payload = _room_status(room, player)
        payload["avatar"] = player.avatar
        return JsonResponse(payload)
    except ApiError as e:
        return _err(e.code)


def set_board(request):
    try:
        _, room, player = _auth(request)
        if room.phase != "waiting":
            raise ApiError("not_waiting")
        if room.owner_id != player.id:
            raise ApiError("not_host")
        board = _body(request).get("board")
        if not game.valid_board_shape(board):
            raise ApiError("bad_board")
        if not Room.objects.filter(pk=room.pk, phase="waiting").update(board=board):
            raise ApiError("not_waiting")
        room.board = board
        return JsonResponse({"ok": True, "board": room.board})
    except ApiError as e:
        return _err(e.code)


def start_game(request):
    try:
        _, room, player = _auth(request)
        if room.owner_id != player.id:
            raise ApiError("not_host")
        if room.phase != "waiting":
            raise ApiError("not_waiting")
        with transaction.atomic():
            _lock_room(room)
            n = room.players.count()
            if n < game.MIN_PLAYERS or n > game.MAX_PLAYERS:
                raise ApiError("bad_players_count")
            if room.phase != "waiting":
                raise ApiError("not_waiting")
            if not game.validate_board(room.board, n):
                raise ApiError("bad_board")
            room.phase = "op"
            room.op_start_time = timezone.now()
            room.save(update_fields=["phase", "op_start_time"])
            game.deal(room)
        # Return the live op room state so the client renders/jumps instantly.
        return JsonResponse(_room_status(room, player))
    except ApiError as e:
        return _err(e.code)


def night_action(request):
    try:
        _, room, player = _auth(request)
        with transaction.atomic():
            _lock_room(room)
            _advance(room)
            if room.phase != "op":
                return JsonResponse(_room_status(room, player))
            choice = _body(request).get("choice")
            if not _valid_choice(room, player, choice):
                raise ApiError("bad_choice")
            Player.objects.filter(id=player.id, room__phase="op").update(
                choice=choice,
            )
            _advance(room)
        return JsonResponse(_room_status(room, player))
    except ApiError as e:
        return _err(e.code)


def _room_status(room, player):
    """The in-room snapshot for ``player``, keyed by current phase.

    Shared by ``room_state`` (polling) and the mutating endpoints (``vote``,
    ``night_action``), so a write can return the same payload the next poll
    would — letting the client render the new room state instantly instead of
    waiting for the next 2s tick.
    """
    player.refresh_from_db()
    if room.phase == "waiting":
        return _waiting_payload(room, player)
    if room.phase == "op":
        return _op_payload(room, player, _deadline_ms(room))
    if room.phase == "reveal":
        return _reveal_payload(room, player)
    # result phase: empty; real content comes from /api/result/
    return {"ok": True, "phase": "result"}


def room_state(request):
    try:
        _, room, player = _auth(request)
        _advance(room)
        return JsonResponse(_room_status(room, player))
    except ApiError as e:
        return _err(e.code)


def _settled_info(room, player):
    """The one-per-game reveal body for ``player`` (idempotent, phase=reveal).

    Returns only information that role is entitled to: the insomniac learns
    their own ``final_role``; every other role learns just what their initial
    role's night action revealed. ``final_role`` is never put in the payload
    for a role that lacks the ability to know it (anti-leak).
    """
    choice = player.choice
    roles = dict(room.players.values_list("userid", "role"))
    wolves = [uid for uid, role in roles.items() if role == "werewolf"]
    if player.role == "werewolf":
        info = {"teammates": [uid for uid in wolves if uid != player.userid]}
        if len(wolves) == 1:
            target = choice["target"]
            info.update(target=target, peek=room.center[int(target.split("_")[1])])
        return info
    if player.role == "minion":
        return {"teammates": wolves}
    if player.role == "seer":
        if "center_picks" in choice:
            picks = choice["center_picks"]
            return {"center_picks": picks, "peeked": [room.center[i] for i in picks]}
        target = choice["target"]
        return {"target": target, "peeked": [roles[target]]}
    if player.role == "robber":
        target = choice["target"]
        return {"target": target, "new_role": roles[target]}
    if player.role == "troublemaker":
        return {"target": choice["target"], "target2": choice["target2"]}
    if player.role == "insomniac":
        return {"final_role": game.final_cards(room.players.all())[player.userid]}
    return {}


def reveal(request):
    try:
        _, room, player = _auth(request)
        if room.phase != "reveal":
            raise ApiError("not_in_reveal")
        return JsonResponse({
            "ok": True,
            "phase": "reveal",
            # One-shot room + "who am I" context (static, so it lives in this
            # body rather than the 2s poll): room id, player count, the public
            # template board, and who *I* am (id + avatar).
            "roomid": room.roomid,
            "user_count": room.players.count(),
            "board": room.board,
            "me": {"userid": player.userid, "avatar": player.avatar},
            "role": player.role,
            "action_was_fake": player.fake_role is not None,
            # ``display_role`` (the fake operating identity) is intentionally
            # withheld — a player should only learn their real initial role.
            # ``final_role`` intentionally withheld for non-insomniac roles:
            # only the insomniac learns it, via ``info``. Never put it here,
            # or a player could read it straight out of the API response.
            "info": _settled_info(room, player),
            "voted": player.vote_target is not None,
            "users": [{"userid": p.userid, "avatar": p.avatar} for p in room.players.all()],
        })
    except ApiError as e:
        return _err(e.code)


def vote(request):
    try:
        _, room, player = _auth(request)
        with transaction.atomic():
            _lock_room(room)
            if room.phase != "reveal":
                raise ApiError("not_in_reveal")
            target = _body(request).get("target", "")
            if not isinstance(target, str) or target == player.userid:
                raise ApiError("bad_target")
            if target != "" and not Player.objects.filter(room=room, userid=target).exists():
                raise ApiError("bad_target")
            # conditional write: one vote per player, only while in reveal
            updated = Player.objects.filter(
                id=player.id, room__phase="reveal", vote_target__isnull=True,
            ).update(vote_target=target)
            if not updated:
                raise ApiError("already_voted")
            _advance(room)
        # Return the live room status (already advanced past reveal if this was
        # the deciding vote) so the client renders instantly, no poll needed.
        return JsonResponse(_room_status(room, player))
    except ApiError as e:
        return _err(e.code)


def result(request):
    try:
        _, room, player = _auth(request)
        if room.phase != "result":
            raise ApiError("not_done")
        # All secrets are public only after everyone has voted. The client
        # derives tally, victory and replay from these persisted facts.
        return JsonResponse({
            "ok": True,
            "phase": "result",
            "center": room.center,
            "players": [{
                "userid": p.userid,
                "avatar": p.avatar,
                "role": p.role,
                "choice": p.choice,
                "vote_target": p.vote_target,
            } for p in room.players.order_by("id")],
        })
    except ApiError as e:
        return _err(e.code)
