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

from django.db import transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone

from onw_backend.config import OPS_DURATION
from . import game
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
    try:
        return json.loads(request.body or b"{}")
    except (ValueError, TypeError):
        raise ApiError("bad_request")


def _auth(request):
    """Resolve and authenticate caller's credentials against a room."""
    body = _body(request)
    roomid = body.get("roomid", "")
    userid = body.get("userid", "")
    userpsw = body.get("userpsw", "")

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
    submitted = room.players.filter(submitted=True).count()
    # each player's op is confidential — never expose who has/hasn't submitted
    # or anyone's choice; only this caller's own ``my_choice`` and a total count.
    users = [{"userid": p.userid, "avatar": p.avatar} for p in room.players.all()]
    return {
        "ok": True,
        "phase": "op",
        "role": player.display_role,
        "my_choice": player.choice,
        "submitted": player.submitted,
        "submitted_count": submitted,
        "total_count": total,
        "deadline_ms": deadline,
        "users": users,
    }


def _reveal_payload(room, player):
    # minimal: this caller only needs their own voted flag. Who has voted is
    # nobody's business and must not be in the API response.
    return {
        "ok": True,
        "phase": "reveal",
        "voted": player.voted,
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

    op -> reveal when all submitted or the deadline passes; reveal -> result
    when everyone has voted. Only the caller that first observes the end
    condition wins the conditional UPDATE (SQLite serializes its first write),
    so the resolver runs exactly once.
    """
    room.refresh_from_db()

    if room.phase == "op":
        # op -> reveal fires ONLY when the deadline passes. It must NOT advance
        # when everyone has submitted — that would let ring-late players infer
        # who was done early (anti-cheat, see design.md ``%5``). So everyone
        # waits out the full timer regardless of submission state.
        timed_out = room.op_start_time and timezone.now() >= room.op_start_time + OPS_DURATION
        if timed_out:
            with transaction.atomic():
                claimed = Room.objects.filter(
                    id=room.id, phase="op", resolved_flag=False
                ).update(phase="reveal", resolved_flag=True)
                if claimed:
                    claimed_room = Room.objects.get(id=room.id)
                    game.run_resolver(claimed_room)
            room.refresh_from_db()

    if room.phase == "reveal":
        players = list(room.players.all())
        if players and all(p.voted for p in players):
            Room.objects.filter(id=room.id, phase="reveal").update(phase="result")
            room.refresh_from_db()


# ---------------------------------------------------------------------------
# Choice validation (phase 1)
# ---------------------------------------------------------------------------

def _valid_choice(room, player, choice):
    """Structurally validate a phase-1 choice against the operating identity.

    This is the fake interface, so it validates the shape the UI produced; the
    resolver only ever applies choices of real-action roles. Returns True/False.
    """
    if not isinstance(choice, dict):
        return False
    t = choice.get("type")
    others = {p.userid for p in room.players.all() if p.id != player.id}
    centers = {f"center_{i}" for i in range(3)}

    if t == "seer":
        if "target" in choice and choice["target"] in centers:
            return True
        if "target" in choice and choice["target"] in others:
            return True
        if isinstance(choice.get("center_picks"), list) and 1 <= len(choice["center_picks"]) <= 2:
            return all(isinstance(i, int) for i in choice["center_picks"])
        return False
    if t in ("wolf", "werewolf") and choice.get("target") in centers:
        # lone-wolf peek interface (target = one center card). "werewolf" is an
        # accepted alias the client may send.
        return True
    if t == "robber" and choice.get("target") in others:
        return True
    if t == "troublemaker":
        a, b = choice.get("target"), choice.get("target2")
        return a in others and b in others and a != b
    if t == "none":
        return True  # explicit skip
    return False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def csrf(request):
    return JsonResponse({"ok": True, "csrf_token": get_token(request)})


def create_room(request):
    try:
        body = _body(request)
        c = _load(body, ["roomid", "userid", "userpsw"],
                  [_RE_ROOMID, _RE_USERID, _RE_PSW])
        avatar = body.get("avatar", "")
        if Room.objects.filter(roomid=c["roomid"]).exists():
            raise ApiError("roomid_taken")
        with transaction.atomic():
            room = Room.objects.create(roomid=c["roomid"], board={})
            player = Player.objects.create(
                room=room, userid=c["userid"], userpsw=c["userpsw"], avatar=avatar,
            )
            room.owner = player
            room.save(update_fields=["owner"])
        return JsonResponse({"ok": True, "avatar": player.avatar})
    except ApiError as e:
        return _err(e.code)


def join_room(request):
    try:
        body = _body(request)
        c = _load(body, ["roomid", "userid", "userpsw"],
                  [_RE_ROOMID, _RE_USERID, _RE_PSW])
        avatar = body.get("avatar", "")
        room = Room.objects.filter(roomid=c["roomid"]).first()
        if room is None:
            raise ApiError("room_not_found")
        player = Player.objects.filter(room=room, userid=c["userid"]).first()
        if player is not None:
            if player.userpsw != c["userpsw"]:
                raise ApiError("wrong_password")
            # A returning player keeps the avatar they first joined with (mirrors
            # Avalon): the backend is authoritative, so the client's locally
            # picked avatar never overwrites a stored identity. The frontend
            # syncs this res.avatar back into localStorage on a successful join.
            return JsonResponse({"ok": True, "avatar": player.avatar})
        if room.phase != "waiting":
            raise ApiError("room_started")
        player = Player.objects.create(
            room=room, userid=c["userid"], userpsw=c["userpsw"], avatar=avatar,
        )
        return JsonResponse({"ok": True, "avatar": player.avatar})
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
        if not isinstance(board, dict):
            raise ApiError("bad_board")
        room.board = board
        room.save(update_fields=["board"])
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
        n = room.players.count()
        if n < game.MIN_PLAYERS or n > game.MAX_PLAYERS:
            raise ApiError("bad_players_count")
        with transaction.atomic():
            room.refresh_from_db()
            if room.phase != "waiting":
                raise ApiError("not_waiting")
            if not game.validate_board(room.board, n):
                raise ApiError("bad_board")
            room.status = "started"
            room.phase = "op"
            room.resolved_flag = False
            room.op_start_time = timezone.now()
            room.ops = []  # fresh night log for this game
            room.save(update_fields=["status", "phase", "resolved_flag", "op_start_time", "ops"])
            game.deal(room)
        # Return the live op room state so the client renders/jumps instantly.
        return JsonResponse(_room_status(room, player))
    except ApiError as e:
        return _err(e.code)


def night_action(request):
    try:
        _, room, player = _auth(request)
        if room.phase != "op":
            return JsonResponse(_op_payload(room, player, _deadline_ms(room)))
        choice = _body(request).get("choice")
        if not _valid_choice(room, player, choice):
            raise ApiError("bad_choice")
        # conditional write: only lands while the room is still in op
        Player.objects.filter(id=player.id, room__phase="op").update(
            choice=choice, submitted=True,
        )
        room.refresh_from_db()
        player.refresh_from_db()
        _advance(room)
        # Return the live room status (already advanced past reveal if this was
        # the final op) so the client renders instantly, no poll needed.
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
    c = player.choice
    final = player.final_role
    if player.role == "werewolf":
        if c.get("type") == "wolf":
            # the lone wolf chooses a center card to peek: reveal which one and
            # what it was. ``target`` is "center_<idx>" (0-based position).
            return {"teammates": c.get("teammates", []), "target": c.get("target"), "peek": c.get("peek")}
        return {"teammates": c.get("teammates", [])}
    if player.role == "minion":
        return {"teammates": c.get("teammates", [])}
    if player.role == "seer":
        # keep the chosen target so the reveal can name who/what was peeked:
        # ``target`` = a player, ``center_picks`` = ordered center positions.
        return {"target": c.get("target"), "center_picks": c.get("center_picks"), "peeked": c.get("peeked")}
    if player.role == "robber":
        # ``target`` = who they swapped with, ``new_role`` = the card they got.
        return {"target": c.get("target"), "new_role": c.get("new_role")}
    if player.role == "troublemaker":
        return {"target": c.get("target"), "target2": c.get("target2")}
    if player.role == "insomniac":
        return {"final_role": final}
    return {}


def reveal(request):
    try:
        _, room, player = _auth(request)
        if room.phase != "reveal":
            raise ApiError("not_in_reveal")
        return JsonResponse({
            "ok": True,
            "phase": "reveal",
            "role": player.role,
            # ``display_role`` (the fake operating identity) is intentionally
            # withheld — a player should only learn their real initial role.
            # ``final_role`` intentionally withheld for non-insomniac roles:
            # only the insomniac learns it, via ``info``. Never put it here,
            # or a player could read it straight out of the API response.
            "info": _settled_info(room, player),
            "voted": player.voted,
            "users": [{"userid": p.userid, "avatar": p.avatar} for p in room.players.all()],
        })
    except ApiError as e:
        return _err(e.code)


def vote(request):
    try:
        _, room, player = _auth(request)
        if room.phase != "reveal":
            raise ApiError("not_in_reveal")
        target = _body(request).get("target", "")
        if not isinstance(target, str):
            raise ApiError("bad_target")
        if target != "" and not Player.objects.filter(room=room, userid=target).exists():
            raise ApiError("bad_target")
        # conditional write: one vote per player, only while in reveal
        updated = Player.objects.filter(
            id=player.id, room__phase="reveal", voted=False,
        ).update(vote_target=target, voted=True)
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
        players = list(room.players.all())

        # tally votes; ignore abstentions, unique max wins, tie -> no execution
        tally = {}
        for p in players:
            if p.vote_target:
                tally[p.vote_target] = tally.get(p.vote_target, 0) + 1
        executed = None
        wolf_in_tie = False
        if tally:
            votes = sorted(set(tally.values()), reverse=True)
            top = [uid for uid, n in tally.items() if n == votes[0]]
            if len(top) == 1:
                executed = next((p for p in players if p.userid == top[0]), None)
            else:
                # Tie at the top vote: no single execution, but per the rules a
                # werewolf among the tied players means the wolf side loses.
                # (Judged by FINAL role — a villager swapped into a wolf counts.)
                wolf_in_tie = any(
                    p.final_role == "werewolf" for p in players if p.userid in top
                )

        good_win, reason = game.verdict(room, executed)
        if wolf_in_tie:
            good_win = True
            reason = "wolf_in_tie"
        # Faction outcome per player: evil = werewolf/minion, everyone else good.
        # Result phase is fully public — initial/final roles are revealed to all.
        players_out = []
        for p in players:
            # Faction is decided by the FINAL role: a villager who got swapped
            # into a wolf plays for evil, a wolf who ended up a villager plays
            # for good. ``won`` = that final faction won the round.
            evil = p.final_role in ("werewolf", "minion")
            players_out.append({
                "userid": p.userid,
                "avatar": p.avatar,
                "role": p.role,              # started as
                "final_role": p.final_role,  # ended up as
                "won": not evil if good_win else evil,
            })
        return JsonResponse({
            "ok": True,
            "phase": "result",
            "executed": executed.userid if executed else None,
            "players": players_out,
            "board": room.board,
            "center": room.center,
            "votes": tally,
            "good_win": good_win,
            "reason": reason,
            # Night-action log (JSON; frontend renders the sentences).
            "ops": room.ops,
        })
    except ApiError as e:
        return _err(e.code)