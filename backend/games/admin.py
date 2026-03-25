from django.contrib import admin

from .models import (
    AbilityTemplate,
    GameAction,
    GameParticipant,
    GameRoleSlot,
    GameSession,
    GameTemplate,
    RoleAbility,
    RoleTemplate,
)


@admin.register(RoleTemplate)
class RoleTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "alignment")
    search_fields = ("name",)


@admin.register(AbilityTemplate)
class AbilityTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "ability_type", "phase")
    list_filter = ("ability_type", "phase")
    search_fields = ("name", "description")


@admin.register(RoleAbility)
class RoleAbilityAdmin(admin.ModelAdmin):
    list_display = ("id", "role", "ability")
    autocomplete_fields = ("role", "ability")


@admin.register(GameTemplate)
class GameTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "min_players", "max_players", "is_public", "creator")
    list_filter = ("is_public",)
    search_fields = ("name", "creator__username")


@admin.register(GameRoleSlot)
class GameRoleSlotAdmin(admin.ModelAdmin):
    list_display = ("id", "game_template", "role", "count")
    autocomplete_fields = ("game_template", "role")


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "join_code", "template", "host", "status", "current_phase", "turn_number", "created_at")
    list_filter = ("status", "current_phase")
    search_fields = ("join_code", "template__name", "host__username")
    readonly_fields = ("join_code", "created_at", "updated_at", "started_at", "ended_at")


@admin.register(GameParticipant)
class GameParticipantAdmin(admin.ModelAdmin):
    list_display = ("id", "display_name", "session", "user", "seat_order", "is_ready", "is_connected", "is_alive")
    list_filter = ("is_ready", "is_connected", "is_alive")
    search_fields = ("display_name", "user__username", "session__join_code")
    autocomplete_fields = ("session", "user")


@admin.register(GameAction)
class GameActionAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "participant", "action_type", "phase", "status", "submitted_at")
    list_filter = ("status", "phase", "action_type")
    search_fields = ("session__join_code", "participant__display_name", "action_type")
    autocomplete_fields = ("session", "participant")
