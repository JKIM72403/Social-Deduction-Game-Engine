from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    AbilityTemplate,
    GameAction,
    GameParticipant,
    GameRoleSlot,
    GameSession,
    GameTemplate,
    PhaseTemplate,
    RoleAbility,
    RoleTemplate,
    WinConditionTemplate,
)


class AbilityTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbilityTemplate
        fields = ["id", "name", "ability_type", "phase", "description", "is_default"]


class RoleAbilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleAbility
        fields = ["ability"]


class RoleTemplateSerializer(serializers.ModelSerializer):
    abilities = serializers.PrimaryKeyRelatedField(
        many=True, queryset=AbilityTemplate.objects.all(), write_only=True
    )
    ability_details = serializers.SerializerMethodField()

    def get_ability_details(self, obj):
        abilities = [ra.ability for ra in obj.abilities.all()]
        return AbilityTemplateSerializer(abilities, many=True).data

    class Meta:
        model = RoleTemplate
        fields = ["id", "name", "alignment", "description", "abilities", "ability_details", "is_default"]

    def create(self, validated_data):
        abilities = validated_data.pop("abilities", [])
        role = RoleTemplate.objects.create(**validated_data)
        for ability in abilities:
            RoleAbility.objects.create(role=role, ability=ability)
        return role

    def update(self, instance, validated_data):
        abilities = validated_data.pop("abilities", None)
        instance.name = validated_data.get("name", instance.name)
        instance.alignment = validated_data.get("alignment", instance.alignment)
        instance.description = validated_data.get("description", instance.description)
        instance.save()

        if abilities is not None:
            # Clear existing abilities and add new ones
            RoleAbility.objects.filter(role=instance).delete()
            for ability in abilities:
                RoleAbility.objects.create(role=instance, ability=ability)

        return instance


class GameRoleSlotSerializer(serializers.ModelSerializer):
    role_details = RoleTemplateSerializer(source='role', read_only=True)

    class Meta:
        model = GameRoleSlot
        fields = ["role", "count", "role_details"]


class PhaseTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhaseTemplate
        fields = ["id", "name", "game_template", "phase_type", "order"]
        read_only_fields = ["game_template"]


class WinConditionTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WinConditionTemplate
        fields = ["id", "name", "game_template", "winner_alignment", "criteria", "order"]
        read_only_fields = ["game_template"]


class GameTemplateSerializer(serializers.ModelSerializer):
    role_slots = GameRoleSlotSerializer(many=True)
    phases = PhaseTemplateSerializer(many=True, required=False)
    win_conditions = WinConditionTemplateSerializer(many=True, required=False)
    creator_name = serializers.SerializerMethodField()
    creator_id = serializers.IntegerField(source='creator.id', read_only=True, default=None)

    class Meta:
        model = GameTemplate
        fields = ["id", "name", "min_players", "max_players", "is_public", "role_slots", "phases", "win_conditions", "creator_name", "creator_id"]

    def get_creator_name(self, obj):
        return obj.creator.username if obj.creator else None

    def create(self, validated_data):
        role_slots_data = validated_data.pop("role_slots", [])
        phases_data = validated_data.pop("phases", [])
        win_conditions_data = validated_data.pop("win_conditions", [])
        
        game_template = GameTemplate.objects.create(**validated_data)

        for slot in role_slots_data:
            GameRoleSlot.objects.create(game_template=game_template, **slot)

        # If no phases provided, create default Night -> Day -> Voting cycle
        if not phases_data:
            default_phases = [
                {"name": "Night", "phase_type": "NIGHT", "order": 0},
                {"name": "Day", "phase_type": "DAY", "order": 1},
                {"name": "Voting", "phase_type": "VOTING", "order": 2},
            ]
            for phase in default_phases:
                PhaseTemplate.objects.create(game_template=game_template, **phase)
        else:
            for phase in phases_data:
                PhaseTemplate.objects.create(game_template=game_template, **phase)

        # If no win conditions provided, create default Town and Mafia win conditions
        if not win_conditions_data:
            default_win_conditions = [
                {
                    "name": "Town Victory",
                    "winner_alignment": "TOWN",
                    "criteria": [{"type": "ALIGNMENT_COUNT", "target": "MAFIA", "count": 0}],
                    "order": 0,
                },
                {
                    "name": "Mafia Victory",
                    "winner_alignment": "MAFIA",
                    "criteria": [{"type": "ALIGNMENT_COUNT", "target": "TOWN", "count": 0}],
                    "order": 1,
                },
            ]
            for wc in default_win_conditions:
                WinConditionTemplate.objects.create(game_template=game_template, **wc)
        else:
            for win_condition in win_conditions_data:
                WinConditionTemplate.objects.create(game_template=game_template, **win_condition)

        return game_template

    def update(self, instance, validated_data):
        role_slots_data = validated_data.pop("role_slots", None)
        phases_data = validated_data.pop("phases", None)
        win_conditions_data = validated_data.pop("win_conditions", None)
        instance.name = validated_data.get("name", instance.name)
        instance.min_players = validated_data.get("min_players", instance.min_players)
        instance.max_players = validated_data.get("max_players", instance.max_players)
        instance.is_public = validated_data.get("is_public", instance.is_public)
        instance.save()

        if role_slots_data is not None:
            GameRoleSlot.objects.filter(game_template=instance).delete()
            for slot in role_slots_data:
                GameRoleSlot.objects.create(game_template=instance, **slot)

        if phases_data is not None:
            PhaseTemplate.objects.filter(game_template=instance).delete()
            for phase in phases_data:
                PhaseTemplate.objects.create(game_template=instance, **phase)

        if win_conditions_data is not None:
            WinConditionTemplate.objects.filter(game_template=instance).delete()
            for win_condition in win_conditions_data:
                WinConditionTemplate.objects.create(game_template=instance, **win_condition)

        return instance

# --- Auth Serializers ---

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class SignupSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, default='')
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class GameSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameSession
        fields = [
            "id",
            "template",
            "host",
            "join_code",
            "status",
            "current_phase",
            "turn_number",
            "state_json",
            "created_at",
            "updated_at",
            "started_at",
            "ended_at",
        ]
        read_only_fields = fields


class GameParticipantSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = GameParticipant
        fields = [
            "id",
            "session",
            "user",
            "username",
            "display_name",
            "seat_order",
            "is_ready",
            "is_connected",
            "is_alive",
            "role_name",
            "role_alignment",
            "joined_at",
            "last_seen_at",
            "eliminated_at",
        ]
        read_only_fields = fields


class CreateSessionSerializer(serializers.Serializer):
    template_id = serializers.IntegerField()
    display_name = serializers.CharField(max_length=100, required=False, allow_blank=True)


class JoinSessionSerializer(serializers.Serializer):
    join_code = serializers.CharField(max_length=GameSession.JOIN_CODE_LENGTH)
    display_name = serializers.CharField(max_length=100, required=False, allow_blank=True)


class SessionReadySerializer(serializers.Serializer):
    is_ready = serializers.BooleanField(required=False)


class SubmitSessionActionSerializer(serializers.Serializer):
    action_type = serializers.ChoiceField(choices=["VOTE"])
    target_participant_id = serializers.IntegerField()
