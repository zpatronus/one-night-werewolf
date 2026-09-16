"""Game rules for One Night Werewolf.

Pure / DB-only: no timers, no threads. Phase advancement is triggered by the
request that observes the relevant end condition (endpoint-design ``%0.5``).
The DB is the only source of truth; every phase-1 write is gated by ``phase``.
"""
import random


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

ROLE_CODES = [
    "werewolf", "minion", "seer", "robber",
    "troublemaker", "insomniac", "villager",
]

# These roles always make a real choice. Only a lone dealt wolf also acts.
REAL_DISPLAY = {"seer", "robber", "troublemaker"}
FAKE_POOL = ["seer", "robber", "troublemaker", "werewolf"]

MIN_PLAYERS = 3
MAX_PLAYERS = 10


def fake_pool(board):
    """Use operable roles in the template, independent of the deal.

    Boards without any operable roles use the full pool so everyone still acts.
    """
    return [role for role in FAKE_POOL if board.get(role, 0) > 0] or list(FAKE_POOL)


# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------

def board_template(player_count=None):
    """Every new room starts with the same nine-card draft."""
    return {role: 2 if role in ("werewolf", "villager") else 1 for role in ROLE_CODES}


def valid_board_shape(board):
    return isinstance(board, dict) and all(
        role in ROLE_CODES and type(count) is int and count >= 0
        for role, count in board.items()
    )


def valid_choice(role, userid, users, choice):
    """Validate only the displayed interface, never reveal whether it is real."""
    if not isinstance(choice, dict):
        return False
    kind = choice.get("type")
    if role == "werewolf":
        return (kind in ("wolf", "werewolf") and set(choice) == {"type", "target"}
                and isinstance(choice.get("target"), str)
                and choice["target"] in {"center_0", "center_1", "center_2"})
    if kind != role:
        return False
    others = set(users) - {userid}
    def other(value):
        return isinstance(value, str) and value in others
    if role == "seer":
        if set(choice) == {"type", "target"}:
            return other(choice["target"])
        picks = choice.get("center_picks")
        return (set(choice) == {"type", "center_picks"} and isinstance(picks, list)
                and len(picks) == 2 and all(type(i) is int and 0 <= i < 3 for i in picks)
                and picks[0] != picks[1])
    if role == "robber":
        return set(choice) == {"type", "target"} and other(choice["target"])
    if role == "troublemaker":
        return (set(choice) == {"type", "target", "target2"}
                and other(choice["target"]) and other(choice["target2"])
                and choice["target"] != choice["target2"])
    return False


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
        if type(count) is not int or count < 0:
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
    # Keep ``room.board`` intact: it's the public template and is still shown
    # on the reveal page. Phase (not an empty board) tracks game progress.
    room.save(update_fields=["center"])

    lone_wolf = dealt_roles.count("werewolf") == 1
    for p, role in zip(players, dealt_roles):
        p.role = role
        p.choice = {}
        real_action = role in REAL_DISPLAY or (role == "werewolf" and lone_wolf)
        p.fake_role = None if real_action else random.choice(decoys)
        p.vote_target = None
        p.save(update_fields=[
            "role", "choice", "fake_role", "vote_target",
        ])


# ---------------------------------------------------------------------------
# Phase-1 resolver (op -> reveal, runs exactly once per game)
# ---------------------------------------------------------------------------

def _default_choice(player, all_players):
    """Random valid operation for the displayed interface, including decoys."""
    role = player.display_role
    others = [p.userid for p in all_players if p.id != player.id]
    if role == "seer":
        return {"type": "seer", "center_picks": random.sample(range(3), 2)}
    if role == "robber":
        return {"type": "robber", "target": random.choice(others)}
    if role == "troublemaker":
        a, b = random.sample(others, 2)
        return {"type": "troublemaker", "target": a, "target2": b}
    if role == "werewolf":
        return {"type": "wolf", "target": f"center_{random.randrange(3)}"}
    return {}


def run_resolver(room):
    """Freeze raw choices once inside the phase transition transaction.

    Missing/invalid choices receive random defaults. Decoy choices are stored
    like real choices but ignored when deriving cards and private observations.
    """
    players = list(room.players.order_by("id"))
    users = [p.userid for p in players]
    for p in players:
        if not valid_choice(p.display_role, p.userid, users, p.choice):
            p.choice = _default_choice(p, players)
            p.save(update_fields=["choice"])


def final_cards(players):
    """Derive final cards from frozen inputs; never persist a second copy."""
    players = list(players)
    cards = {p.userid: p.role for p in players}
    for p in players:
        if p.role == "robber":
            target = p.choice["target"]
            cards[p.userid], cards[target] = cards[target], cards[p.userid]
    for p in players:
        if p.role == "troublemaker":
            a, b = p.choice["target"], p.choice["target2"]
            cards[a], cards[b] = cards[b], cards[a]
    return cards
