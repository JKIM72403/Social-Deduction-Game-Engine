from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction
from .models import (
    Alignment,
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


def normalize_target_name(value):
    if not isinstance(value, str):
        return ""
    return value.strip().upper()


def validate_criteria_targets(criteria, *, valid_role_names=None, valid_alignment_names=None):
    valid_role_names = {normalize_target_name(name) for name in (valid_role_names or set()) if name}
    valid_alignment_names = {normalize_target_name(name) for name in (valid_alignment_names or set()) if name}

    for index, criterion in enumerate(criteria):
        ctype = criterion.get("type")
        target = normalize_target_name(criterion.get("target"))

        if ctype == "ROLE_COUNT" and target not in valid_role_names:
            raise serializers.ValidationError(
                {"criteria": f"Criterion #{index + 1} references unknown role target '{criterion.get('target')}'."}
            )

        if ctype == "ALIGNMENT_COUNT" and target not in valid_alignment_names:
            raise serializers.ValidationError(
                {"criteria": f"Criterion #{index + 1} references unknown alignment target '{criterion.get('target')}'."}
            )
            


class AlignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alignment
        fields = ["id", "name", "is_default", "game_template"]


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
    alignment_name = serializers.CharField(source='alignment.name', read_only=True)

    def get_ability_details(self, obj):
        abilities = [ra.ability for ra in obj.abilities.all()]
        return AbilityTemplateSerializer(abilities, many=True).data

    class Meta:
        model = RoleTemplate
        fields = ["id", "name", "alignment", "alignment_name", "description", "abilities", "ability_details", "is_default", "game_template"]

    def validate(self, attrs):
        alignment = attrs.get("alignment", getattr(self.instance, "alignment", None))
        game_template = attrs.get("game_template", getattr(self.instance, "game_template", None))

        if alignment and alignment.game_template_id and game_template and alignment.game_template_id != game_template.id:
            raise serializers.ValidationError(
                {"alignment": "Alignment must belong to the same game template."}
            )

        return attrs

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
        extra_kwargs = {"game_template": {"required": False}}


class WinConditionTemplateSerializer(serializers.ModelSerializer):
    winner_alignment_name = serializers.CharField(source='winner_alignment.name', read_only=True)

    class Meta:
        model = WinConditionTemplate
        fields = ["id", "name", "game_template", "winner_alignment", "winner_alignment_name", "criteria", "order"]
        extra_kwargs = {"game_template": {"required": False}}

    def validate_criteria(self, value):
        if not isinstance(value, list) or len(value) == 0:
            raise serializers.ValidationError("At least one criterion is required.")

        valid_types = {"ROLE_COUNT", "ALIGNMENT_COUNT", "SURVIVAL"}
        for index, criterion in enumerate(value):
            if not isinstance(criterion, dict):
                raise serializers.ValidationError(f"Criterion #{index + 1} must be an object.")

            ctype = criterion.get("type")
            if ctype not in valid_types:
                raise serializers.ValidationError(
                    f"Criterion #{index + 1} has unsupported type '{ctype}'."
                )

            count = criterion.get("count")
            if not isinstance(count, int) or count < 0:
                raise serializers.ValidationError(
                    f"Criterion #{index + 1} count must be a non-negative integer."
                )

            if ctype in {"ROLE_COUNT", "ALIGNMENT_COUNT"}:
                target = criterion.get("target")
                if not isinstance(target, str) or not target.strip():
                    raise serializers.ValidationError(
                        f"Criterion #{index + 1} target is required for {ctype}."
                    )

        return value

    def validate(self, attrs):
        winner_alignment = attrs.get("winner_alignment", getattr(self.instance, "winner_alignment", None))
        game_template = attrs.get("game_template", getattr(self.instance, "game_template", None))

        if winner_alignment and winner_alignment.game_template_id and game_template and winner_alignment.game_template_id != game_template.id:
            raise serializers.ValidationError(
                {"winner_alignment": "Winner alignment must belong to the same game template."}
            )

        return attrs


class GameTemplateSerializer(serializers.ModelSerializer):
    role_slots = GameRoleSlotSerializer(many=True)
    phases = PhaseTemplateSerializer(many=True, required=False)
    win_conditions = WinConditionTemplateSerializer(many=True, required=False)
    creator_name = serializers.SerializerMethodField()
    creator_id = serializers.IntegerField(source='creator.id', read_only=True, default=None)

    class Meta:
        model = GameTemplate
        fields = ["id", "name", "min_players", "max_players", "is_public", "created_at", "role_slots", "phases", "win_conditions", "creator_name", "creator_id"]

    def get_creator_name(self, obj):
        return obj.creator.username if obj.creator else None

    def validate(self, attrs):
        min_players = attrs.get("min_players", getattr(self.instance, "min_players", None))
        max_players = attrs.get("max_players", getattr(self.instance, "max_players", None))

        if min_players is not None and min_players < 1:
            raise serializers.ValidationError({"min_players": "Must be at least 1."})
        if max_players is not None and max_players < 1:
            raise serializers.ValidationError({"max_players": "Must be at least 1."})
        if min_players is not None and max_players is not None and min_players > max_players:
            raise serializers.ValidationError({"min_players": "Min players cannot exceed max players."})

        role_slots = attrs.get("role_slots")
        if role_slots is not None:
            if len(role_slots) == 0:
                raise serializers.ValidationError({"role_slots": "At least one role slot is required."})

            total_roles = 0
            for slot in role_slots:
                count = slot.get("count", 0)
                if not isinstance(count, int) or count <= 0:
                    raise serializers.ValidationError({"role_slots": "Each role slot count must be a positive integer."})
                total_roles += count

            if min_players is not None and total_roles < min_players:
                raise serializers.ValidationError({"role_slots": "Total role slots must be at least min_players."})
            if max_players is not None and total_roles > max_players:
                raise serializers.ValidationError({"role_slots": "Total role slots cannot exceed max_players."})

        phases = attrs.get("phases")
        if phases is not None and len(phases) > 0:
            phase_types = [phase.get("phase_type") for phase in phases]
            required = {"NIGHT", "DAY", "VOTING"}
            missing = required.difference(phase_types)
            if missing:
                raise serializers.ValidationError({"phases": f"Missing required phase types: {', '.join(sorted(missing))}."})
            if len(phase_types) != len(set(phase_types)):
                raise serializers.ValidationError({"phases": "Duplicate phase types are not allowed."})

        win_conditions = attrs.get("win_conditions")
        if win_conditions is not None:
            role_names = set()
            alignment_names = {alignment.name for alignment in Alignment.objects.filter(game_template__isnull=True)}

            if role_slots is not None:
                for slot in role_slots:
                    role = slot.get("role")
                    if role is not None:
                        role_names.add(role.name)
                        if role.alignment_id:
                            alignment_names.add(role.alignment.name)

            for win_condition in win_conditions:
                winner_alignment = win_condition.get("winner_alignment")
                if winner_alignment is not None:
                    alignment_names.add(winner_alignment.name)

                validate_criteria_targets(
                    win_condition.get("criteria", []),
                    valid_role_names=role_names,
                    valid_alignment_names=alignment_names,
                )

        return attrs

    def create(self, validated_data):
        role_slots_data = validated_data.pop("role_slots", [])
        phases_data = validated_data.pop("phases", [])
        win_conditions_data = validated_data.pop("win_conditions", [])

        with transaction.atomic():
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
                town_alignment, _ = Alignment.objects.get_or_create(
                    name="Town", defaults={"is_default": True}
                )
                mafia_alignment, _ = Alignment.objects.get_or_create(
                    name="Mafia", defaults={"is_default": True}
                )
                default_win_conditions = [
                    {
                        "name": "Town Victory",
                        "winner_alignment": town_alignment,
                        "criteria": [{"type": "ALIGNMENT_COUNT", "target": "MAFIA", "count": 0}],
                        "order": 0,
                    },
                    {
                        "name": "Mafia Victory",
                        "winner_alignment": mafia_alignment,
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
        with transaction.atomic():
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
    action_type = serializers.ChoiceField(
        choices=["USE_ABILITY", "VOTE", "SKIP", "ADVANCE_PHASE"]
    )
    ability_index = serializers.IntegerField(required=False, min_value=0)
    target_participant_id = serializers.IntegerField(required=False)
