import secrets
import string

from django.conf import settings
from django.db import models

class AbilityTemplate(models.Model):
    ABILITY_TYPES = [
        ("KILL", "Kill Target"),
        ("PROTECT", "Protect Target"),
        ("INVESTIGATE", "Investigate Alignment"),
        ("BLOCK", "Block Target"),
        ("TRAP", "Trap Target"),
        ("VOTE_STEAL", "Steal Vote"),
        ("DOUBLE_VOTE", "Double Vote"),
    ]

    name = models.CharField(max_length=100)
    ability_type = models.CharField(max_length=20, choices=ABILITY_TYPES)
    phase = models.CharField(max_length=10, default="NIGHT")
    description = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.name} ({self.ability_type})"


class RoleTemplate(models.Model):
    ALIGNMENTS = [
        ("TOWN", "Town"),
        ("MAFIA", "Mafia"),
        ("NEUTRAL", "Neutral"),
    ]

    name = models.CharField(max_length=100)
    alignment = models.CharField(max_length=20, choices=ALIGNMENTS)
    description = models.TextField(blank=True, default="")

    def __str__(self):
        return self.name


class RoleAbility(models.Model):
    role = models.ForeignKey(RoleTemplate, related_name="abilities", on_delete=models.CASCADE)
    ability = models.ForeignKey(AbilityTemplate, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.role.name} → {self.ability.name}"


class GameTemplate(models.Model):
    name = models.CharField(max_length=100)
    min_players = models.IntegerField()
    max_players = models.IntegerField()
    is_public = models.BooleanField(default=True)

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='game_templates'
    )

    def __str__(self):
        return self.name


class GameRoleSlot(models.Model):
    game_template = models.ForeignKey(GameTemplate, related_name="role_slots", on_delete=models.CASCADE)
    role = models.ForeignKey(RoleTemplate, on_delete=models.CASCADE)
    count = models.IntegerField()

    def __str__(self):
        return f"{self.game_template.name}: {self.role.name} x{self.count}"


class PhaseTemplate(models.Model):
    PHASE_TYPES = [
        ("NIGHT", "Night"),
        ("DAY", "Day"),
        ("VOTING", "Voting"),
    ]
    game_template = models.ForeignKey(GameTemplate, related_name="phases", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phase_type = models.CharField(max_length=20, choices=PHASE_TYPES)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.game_template.name} - {self.name} ({self.order})"


class WinConditionTemplate(models.Model):
    ALIGNMENTS = RoleTemplate.ALIGNMENTS

    game_template = models.ForeignKey(GameTemplate, related_name="win_conditions", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    winner_alignment = models.CharField(max_length=20, choices=ALIGNMENTS, default="TOWN")
    
    # JSON structure: [{"type": "ROLE_COUNT", "target": role_id, "count": 0}, ...]
    criteria = models.JSONField(default=list)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.game_template.name} - {self.name} (Winner: {self.winner_alignment})"


class GameSession(models.Model):
    STATUS_LOBBY = "LOBBY"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_LOBBY, "Lobby"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    PHASE_WAITING = "WAITING"
    PHASE_DAY = "DAY"
    PHASE_VOTING = "VOTING"
    PHASE_NIGHT = "NIGHT"
    PHASE_GAME_OVER = "GAME_OVER"

    PHASE_CHOICES = [
        (PHASE_WAITING, "Waiting"),
        (PHASE_DAY, "Day"),
        (PHASE_VOTING, "Voting"),
        (PHASE_NIGHT, "Night"),
        (PHASE_GAME_OVER, "Game Over"),
    ]

    JOIN_CODE_LENGTH = 6
    JOIN_CODE_ALPHABET = string.ascii_uppercase + string.digits

    template = models.ForeignKey(
        GameTemplate,
        related_name="sessions",
        on_delete=models.CASCADE,
    )
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="hosted_game_sessions",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    join_code = models.CharField(
        max_length=JOIN_CODE_LENGTH,
        unique=True,
        db_index=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_LOBBY,
    )
    current_phase = models.CharField(
        max_length=20,
        choices=PHASE_CHOICES,
        default=PHASE_WAITING,
    )
    turn_number = models.PositiveIntegerField(default=0)
    state_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.join_code} - {self.template.name} ({self.status})"

    @classmethod
    def generate_join_code(cls):
        return "".join(
            secrets.choice(cls.JOIN_CODE_ALPHABET)
            for _ in range(cls.JOIN_CODE_LENGTH)
        )

    def save(self, *args, **kwargs):
        if not self.join_code:
            self.join_code = self._get_unique_join_code()
        super().save(*args, **kwargs)

    def _get_unique_join_code(self):
        for _ in range(20):
            code = self.generate_join_code()
            if not GameSession.objects.filter(join_code=code).exists():
                return code
        raise RuntimeError("Unable to generate a unique join code for game session.")


class GameParticipant(models.Model):
    session = models.ForeignKey(
        GameSession,
        related_name="participants",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="game_participations",
        on_delete=models.CASCADE,
    )
    display_name = models.CharField(max_length=100)
    seat_order = models.PositiveIntegerField(default=0)
    is_ready = models.BooleanField(default=False)
    is_connected = models.BooleanField(default=True)
    is_alive = models.BooleanField(default=True)
    role_name = models.CharField(max_length=100, blank=True, default="")
    role_alignment = models.CharField(max_length=20, blank=True, default="")
    joined_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    eliminated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["seat_order", "joined_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "user"],
                name="unique_session_participant_user",
            ),
            models.UniqueConstraint(
                fields=["session", "display_name"],
                name="unique_session_participant_display_name",
            ),
            models.UniqueConstraint(
                fields=["session", "seat_order"],
                name="unique_session_participant_seat_order",
            ),
        ]

    def __str__(self):
        return f"{self.display_name} in {self.session.join_code}"


class GameAction(models.Model):
    STATUS_SUBMITTED = "SUBMITTED"
    STATUS_APPLIED = "APPLIED"
    STATUS_REJECTED = "REJECTED"

    STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_APPLIED, "Applied"),
        (STATUS_REJECTED, "Rejected"),
    ]

    session = models.ForeignKey(
        GameSession,
        related_name="actions",
        on_delete=models.CASCADE,
    )
    participant = models.ForeignKey(
        GameParticipant,
        related_name="actions",
        on_delete=models.CASCADE,
    )
    turn_number = models.PositiveIntegerField(default=0)
    phase = models.CharField(max_length=20, blank=True, default="")
    action_type = models.CharField(max_length=50)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SUBMITTED,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["submitted_at", "id"]

    def __str__(self):
        return f"{self.action_type} by {self.participant.display_name} ({self.status})"
