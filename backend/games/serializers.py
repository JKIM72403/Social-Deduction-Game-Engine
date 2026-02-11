from rest_framework import serializers
from .models import RoleTemplate, AbilityTemplate, RoleAbility, GameTemplate, GameRoleSlot


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
        abilities = validated_data.pop("abilities")
        role = RoleTemplate.objects.create(**validated_data)
        for ability in abilities:
            RoleAbility.objects.create(role=role, ability=ability)
        return role


class GameRoleSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameRoleSlot
        fields = ["role", "count"]


class GameTemplateSerializer(serializers.ModelSerializer):
    role_slots = GameRoleSlotSerializer(many=True)

    class Meta:
        model = GameTemplate
        fields = ["id", "name", "min_players", "max_players", "role_slots"]

    def create(self, validated_data):
        role_slots_data = validated_data.pop("role_slots")
        game_template = GameTemplate.objects.create(**validated_data)

        for slot in role_slots_data:
            GameRoleSlot.objects.create(game_template=game_template, **slot)

        return game_template

