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

    def update(self, instance, validated_data):
        role_slots_data = validated_data.pop("role_slots", None)
        instance.name = validated_data.get("name", instance.name)
        instance.min_players = validated_data.get("min_players", instance.min_players)
        instance.max_players = validated_data.get("max_players", instance.max_players)
        instance.save()

        if role_slots_data is not None:
            # Clear existing slots and add new ones
            GameRoleSlot.objects.filter(game_template=instance).delete()
            for slot in role_slots_data:
                GameRoleSlot.objects.create(game_template=instance, **slot)

        return instance

