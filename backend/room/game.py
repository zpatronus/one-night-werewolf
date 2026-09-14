"""Game rules for One Night Werewolf.

Pure / DB-only: no timers, no threads. Phase advancement is triggered by the
request that observes the relevant end condition (endpoint-design ``%0.5``).
The DB is the only source of truth; every phase-1 write is gated by ``phase``.
"""
import random

from django.db import transaction

from .models import Room, Player

# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

ROLE_CODES = [
    "werewolf", "minion", "seer", "robber",
    "troublemaker", "insomniac", "villager",
]

# Roles with a real night action in phase 1.
ACTION_ROLES = {"seer", "robber", "troublemaker", "werewolf"}

# Roles that are shown their own identity in phase 1 (they have a real night
# interface). A werewolf always shows as a wolf — solo or in a pack, the wolf
# must know it's a wolf and see its teammate/peek interface. Nobody else is
# told a fake identity except the no-action roles (villager/insomniac/minion).
REAL_DISPLAY = {"seer", "robber", "troublemaker", "werewolf"}

# Fake-interface pool: the "operating identity" shown to no-action players so
# everyone visibly acts in phase 1 (anti-cheat, see design.md ``%1``). "werewolf"
# here is the lone-wolf-peek interface used as a decoy.
FAKE_POOL = ["seer", "robber", "troublemaker", "werewolf"]

MIN_PLAYERS = 3
MAX_PLAYERS = 10


def is_real_action(role, lone_wolf):
    """Does ``role`` take a real (server-settled) action in phase 1?"""
    if role in ("seer", "robber", "troublemaker"):
        return True
    if role == "werewolf":
        return lone_wolf  # only a lone wolf actually peeks a center card
    return False


def fake_pool(board):
    """The decoy operating identities available for no-action players.

    Drawn strictly from the roles present in the board TEMPLATE (so a fake
    identity is always plausible in the current game — e.g. no fake seer if the
    seer card isn't in the deck), and limited to the roles that carry a real
    phase-1 interface. Never depends on where the cards happened to land in
    players' hands. The lone-wolf-peek interface is a decoy only when the
    template calls for a lone wolf (exactly 1 werewolf card). Falls back to the
    fixed pool for exotic boards.
    """
    pool = [r for r in ("seer", "robber", "troublemaker") if board.get(r, 0) > 0]
    w = board.get("werewolf", 0)
    # A lone wolf is POSSIBLE whenever the template holds 1..4 werewolves
    # (with up to 3 of them sitting in the center, w don't know the in-play
    # count in advance). In all those ambiguous cases the decoy pool must
    # include the lone-wolf-peek interface so no-action players can impersonate
    # it. Only at >=5 template wolves are >=2 wolves guaranteed in play, so a
    # lone wolf can never occur and the decoy is excluded.
    if 0 < w < 5:
        pool.append("werewolf")
    return pool or list(FAKE_POOL)


# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------

def board_template(player_count):
    """Default ``{role_code: count}`` board for N players (sum = N + 3 center)."""
    n = player_count
    board = {
        "werewolf": 1 if n <= 3 else 2,
        "seer": 1,
        "robber": 1,
        "troublemaker": 1,
        "insomniac": 1,
    }
    board["villager"] = (n + 3) - sum(board.values())
    return board


def validate_board(board, player_count):
    """True if ``board`` is a legal full deck for ``player_count`` players."""
    if not isinstance(board, dict):
        return False
    if not (MIN_PLAYERS <= player_count <= MAX_PLAYERS):
        return False
    total = 0
    for role, count in board.items():
        if role not in ROLE_CODES:
            return False
        if not isinstance(count, int) or count < 0:
            return False
        # Robber and troublemaker are unique — at most 1 each.
        if role in ("robber", "troublemaker") and count > 1:
            return False
        total += count
    return total == player_count + 3


# ---------------------------------------------------------------------------
# Deal
# ---------------------------------------------------------------------------

def deal(room):
    """Deal the board's 3 center cards + 1 card per player.

    Assigns each player's real ``role``, their phase-1 ``display_role``
    (real action role, or a random fake interface), and resets all per-player
    phase fields for a fresh game.
    """
    players = list(room.players.order_by("id"))
    board = room.board

    bag = []
    for role in ROLE_CODES:
        bag += [role] * board.get(role, 0)
    random.shuffle(bag)

    room.center = bag[:3]
    dealt_roles = bag[3:]  # one card per player

    # Decoy identities come purely from the board template (see fake_pool) —
    # NOT from which roles happened to land in players' hands.
    decoys = fake_pool(board)
    room.save(update_fields=["center"])

    for p, role in zip(players, dealt_roles):
        p.role = role
        p.final_role = None
        p.choice = {}
        # Real action roles (and every real werewolf) show their own identity;
        # everyone else acts under a plausible decoy interface.
        p.display_role = role if role in REAL_DISPLAY else random.choice(decoys)
        p.submitted = False
        p.vote_target = ""
        p.voted = False
        p.save(update_fields=[
            "role", "final_role", "choice", "display_role",
            "submitted", "vote_target", "voted",
        ])


# ---------------------------------------------------------------------------
# Phase-1 resolver (op -> reveal, runs exactly once per game)
# ---------------------------------------------------------------------------

def _default_choice(player, board, all_players):
    """Best-effort random choice for a real-action player that never submitted."""
    r = player.role
    others = [q.userid for q in all_players if q.id != player.id]
    if r == "seer":
        return {"type": "seer", "target": "center_0"}
    if r == "robber":
        return {"type": "robber", "target": random.choice(others)}
    if r == "troublemaker":
        a, b = random.sample(others, 2)
        return {"type": "troublemaker", "target": a, "target2": b}
    if r == "werewolf":  # lone wolf: system randomly assigns a center card
        return {"type": "wolf", "target": f"center_{random.randint(0, 2)}"}
    return {}


def run_resolver(room):
    """Settle the night per design.md ``%6.2`` order and write final roles.

    Must be invoked inside ``transaction.atomic`` and gated by
    ``resolved_flag`` (first write wins). Real-action choices are applied;
    fake choices from no-action players are ignored.
    """
    players = list(room.players.order_by("id"))
    board = room.board
    by_uid = {p.userid: p for p in players}
    seat = {p.userid: i for i, p in enumerate(players)}
    cards = [p.role for p in players]  # the card currently held at each seat
    wolves = [p for p in players if p.role == "werewolf"]
    # lone only when exactly one wolf is actually among the players (a second
    # wolf in the center doesn't count as a packmate — that wolf peeks).
    lone_wolf = len(wolves) == 1
    wolf_uids = [w.userid for w in wolves]

    # The public night-action log, in resolution order. Stored on the room and
    # shown on the result page once the game is over (everything is public).
    ops = []

    # 0) default-fill unsubmitted real-action players (submitted stays False)
    for p in players:
        if not p.submitted and is_real_action(p.role, lone_wolf):
            p.choice = _default_choice(p, board, players)

    # 1) wolves / minion mutual recognition (info, no card movement).
    #    A wolf sees its packmates (not itself); the minion sees every wolf.
    #    A lone wolf ends up with an empty pack.
    for p in players:
        if p.role == "werewolf":
            pack = [uid for uid in wolf_uids if uid != p.userid]
            p.choice = {**p.choice, "teammates": pack}
        elif p.role == "minion":
            # the minion sees every wolf (they can't see the minion back).
            p.choice = {**p.choice, "teammates": wolf_uids}
    if wolves:
        ops.append({"type": "wolf", "wolves": wolf_uids})
    if any(p.role == "minion" for p in players):
        ops.append({"type": "minion", "wolves": wolf_uids})

    # 2) lone wolf peeks one center card
    if lone_wolf and wolves:
        lw = wolves[0]
        t = lw.choice.get("target", "center_0")
        idx = int(t.split("_")[1])
        # keep ``target`` so the reveal can say which center card was chosen.
        lw.choice = {"teammates": [], "type": "wolf", "target": t, "peek": room.center[idx]}
        ops.append({"type": "lone_wolf", "center": idx, "card": room.center[idx]})

    # 3) seer: peek a player's current card or 1-2 center cards (info only)
    for p in players:
        if p.role != "seer":
            continue
        c = p.choice
        t = c.get("target")
        if isinstance(t, str) and t.startswith("center_"):
            idx = int(t.split("_")[1])
            c["peeked"] = [room.center[idx]]
        elif isinstance(t, str) and t in by_uid:
            c["peeked"] = [cards[seat[t]]]
        elif isinstance(c.get("center_picks"), list):
            c["peeked"] = [room.center[i % 3] for i in c["center_picks"][:2]]
        p.choice = {"type": "seer", **{k: v for k, v in c.items() if k != "type"}}
        ops.append({
            "type": "seer",
            "seer": p.userid,
            "target": c.get("target"),
            "center_picks": c.get("center_picks"),
            "peeked": c.get("peeked"),
        })

    # 4) robber: swap cards with chosen player, then sees its new card
    for p in players:
        if p.role != "robber":
            continue
        c = p.choice
        tgt = c.get("target")
        if tgt not in by_uid:
            continue
        i, j = seat[p.userid], seat[tgt]
        cards[i], cards[j] = cards[j], cards[i]
        c["new_role"] = cards[i]  # what the robber now holds (their memory)
        p.choice = {"type": "robber", "target": tgt, "new_role": cards[i]}
        # After the swap: robber holds the victim's old card, victim holds 'robber'.
        ops.append({"type": "robber", "robber": p.userid, "target": tgt,
                    "robber_new": cards[i], "target_new": cards[j]})

    # 5) troublemaker: swap two other players' cards (no peeking)
    for p in players:
        if p.role != "troublemaker":
            continue
        c = p.choice
        a, b = c.get("target"), c.get("target2")
        if a not in by_uid or b not in by_uid:
            continue
        i, j = seat[a], seat[b]
        cards[i], cards[j] = cards[j], cards[i]
        p.choice = {"type": "troublemaker", "target": a, "target2": b}
        ops.append({"type": "troublemaker", "troublemaker": p.userid,
                    "a": a, "b": b, "a_new": cards[i], "b_new": cards[j]})

    # 6) final_role = the card now at each seat
    for i, p in enumerate(players):
        p.final_role = cards[i]
        p.save(update_fields=["final_role", "choice"])
    for p in players:
        if p.role == "insomniac":
            ops.append({"type": "insomniac", "insomniac": p.userid, "card": p.final_role})

    room.ops = ops
    room.save(update_fields=["ops"])
    Room.objects.filter(id=room.id).update(resolved_flag=True)


# ---------------------------------------------------------------------------
# Win conditions (design.md ``%1.2``)
# ---------------------------------------------------------------------------

def verdict(room, executed):
    """Return ``(good_win: bool, reason: str)`` for the final reveal.

    Good wins iff the executed player's final_role is a werewolf — or, when
    there is no werewolf left on the board at all (only a minion), that minion.
    No execution (abstain/tie) -> evil wins.

    ``reason`` is a short English code; the frontend renders the sentence via
    ``gameConfig`` (backends stay language-free — see design.md ``%8``).
    """
    if executed is None:
        return False, "no_execution"
    any_ww = any(p.final_role == "werewolf" for p in room.players.all())
    if executed.final_role == "werewolf":
        return True, "wolf_executed"
    if not any_ww and executed.final_role == "minion":
        return True, "minion_executed_no_wolf"
    return False, "villager_executed"