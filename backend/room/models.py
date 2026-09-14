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
    phase = models.CharField(max_length=10, choices=PHASE_CHOICES, default="waiting")
    owner = models.ForeignKey(
        "Player", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    # Board = {role_code: count}; DB is the only source of truth.
    board = models.JSONField(default=dict)
    # 3 center cards' role codes (set at start_game; never swapped in our variant).
    center = models.JSONField(default=list)
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
    # Only decoys need an extra stored role; real action roles use role directly.
    fake_role = models.CharField(max_length=16, null=True, blank=True)
    # Raw displayed-interface choice; {} means not submitted. Decoys have no effect.
    choice = models.JSONField(default=dict)
    # NULL = not voted; "" = abstain; otherwise the selected player.
    vote_target = models.CharField(max_length=7, null=True, default=None)

    @property
    def display_role(self):
        return self.fake_role or self.role

    class Meta:
        unique_together = (("room", "userid"),)

    def __str__(self):
        return self.userid
