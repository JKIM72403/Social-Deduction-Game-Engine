from django.db import models
from django.conf import settings

class AbilityTemplate(models.Model):
    ABILITY_TYPES = [
        ("KILL", "Kill Target"),
        ("PROTECT", "Protect Target"),
        ("INVESTIGATE", "Investigate Alignment"),
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
