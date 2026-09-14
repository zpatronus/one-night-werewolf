from django.db import models


class Room(models.Model):
    """A game room. One room == one game; phases never reset to waiting."""

    PHASE_CHOICES = [
        ("waiting", "waiting"),
        ("op", "op"),        # phase 1: everyone acts (no results shown)
        ("reveal", "reveal"),  # phase 2: reveal + one vote each
        ("result", "result"),  # phase 3: everyone voted, final reveal
    ]

    roomid = models.CharField(max_length=6, unique=True)
    status = models.CharField(max_length=10, default="waiting")  # waiting | started
    phase = models.CharField(max_length=10, choices=PHASE_CHOICES, default="waiting")
    owner = models.ForeignKey(
        "Player", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    # Board = {role_code: count}; DB is the only source of truth.
    board = models.JSONField(default=dict)
    # 3 center cards' role codes (set at start_game; never swapped in our variant).
    center = models.JSONField(default=list)
    # Phase-1 settlement guard: ensure resolver runs exactly once.
    resolved_flag = models.BooleanField(default=False)
    # Night-action log (JSON list) built by the resolver; shown on the result
    # page after the game is public. Every entry is {type, ...} — English role
    # codes only; the frontend renders sentences (design.md ``%8``).
    ops = models.JSONField(default=list)
    op_start_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.roomid


class Player(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="players")
    userid = models.CharField(max_length=7)
    userpsw = models.CharField(max_length=6)  # plain; dev game, mirrors Avalon
    avatar = models.CharField(max_length=64, default="")
    # Real initial identity (dealt at start_game).
    role = models.CharField(max_length=16, null=True, blank=True)
    # The identity this player "operates as" in phase 1 (fake for no-action roles).
    display_role = models.CharField(max_length=16, null=True, blank=True)
    # Post-settlement identity (after robber/troublemaker swaps).
    final_role = models.CharField(max_length=16, null=True, blank=True)
    # Phase-1 choice {type, target, target2, center_picks} (real action only).
    choice = models.JSONField(default=dict)
    submitted = models.BooleanField(default=False)
    # Phase-2 vote. "" = abstain.
    vote_target = models.CharField(max_length=7, default="")
    voted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("room", "userid"),)

    def __str__(self):
        return self.userid