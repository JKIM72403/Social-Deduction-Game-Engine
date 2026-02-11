from django.db import models

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

    def __str__(self):
        return self.name


class GameRoleSlot(models.Model):
    game_template = models.ForeignKey(GameTemplate, related_name="role_slots", on_delete=models.CASCADE)
    role = models.ForeignKey(RoleTemplate, on_delete=models.CASCADE)
    count = models.IntegerField()

    def __str__(self):
        return f"{self.game_template.name}: {self.role.name} x{self.count}"
