from rest_framework import serializers
from django.contrib.auth.models import User
from .models import RoleTemplate, AbilityTemplate, RoleAbility, GameTemplate, GameRoleSlot, PhaseTemplate, WinConditionTemplate


class AbilityTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbilityTemplate
        fields = "__all__"


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
        fields = ["id", "name", "alignment", "description", "abilities", "ability_details"]

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
        fields = ["id", "name", "min_players", "max_players", "role_slots", "phases", "win_conditions", "creator_name", "creator_id"]

    def get_creator_name(self, obj):
        return obj.creator.username if obj.creator else None

    def create(self, validated_data):
        role_slots_data = validated_data.pop("role_slots", [])
        phases_data = validated_data.pop("phases", [])
        win_conditions_data = validated_data.pop("win_conditions", [])
        
        # Ensure we don't pass extra fields to create
        game_template = GameTemplate.objects.create(**validated_data)

        for slot in role_slots_data:
            GameRoleSlot.objects.create(game_template=game_template, **slot)

        for phase in phases_data:
            PhaseTemplate.objects.create(game_template=game_template, **phase)
            
        for win_condition in win_conditions_data:
            WinConditionTemplate.objects.create(game_template=game_template, **win_condition)

        return game_template

    def update(self, instance, validated_data):
        role_slots_data = validated_data.pop("role_slots", None)
        phases_data = validated_data.pop("phases", None)
        win_conditions_data = validated_data.pop("win_conditions", None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
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
