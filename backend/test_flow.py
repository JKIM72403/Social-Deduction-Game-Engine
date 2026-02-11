import os
import django
import sys

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from games.models import AbilityTemplate, RoleTemplate, GameTemplate
from games.serializers import AbilityTemplateSerializer, RoleTemplateSerializer, GameTemplateSerializer

print("--- Starting Backend Flow Test ---")

# 1. Create Ability
print("\n[TestCase] Creating Ability...")
ability_data = {"name": "Test Kill", "ability_type": "KILL", "phase": "NIGHT"}
ability_serializer = AbilityTemplateSerializer(data=ability_data)
if ability_serializer.is_valid():
    ability = ability_serializer.save()
    print(f"SUCCESS: Created Ability: {ability}")
else:
    print(f"FAILURE: Error creating ability: {ability_serializer.errors}")
    sys.exit(1)

# 2. Create Role
print("\n[TestCase] Creating Role...")
role_data = {
    "name": "Test Killer",
    "alignment": "MAFIA",
    "description": "Kills people.",
    "abilities": [ability.id]
}
role_serializer = RoleTemplateSerializer(data=role_data)
if role_serializer.is_valid():
    role = role_serializer.save()
    print(f"SUCCESS: Created Role: {role}")
    # Verify ability details exist in serialized data
    data = role_serializer.data
    ability_details = data.get('ability_details')
    if ability_details and len(ability_details) > 0 and ability_details[0]['id'] == ability.id:
        print(f"SUCCESS: Role Ability Details verified: {ability_details}")
    else:
        print(f"FAILURE: Ability details missing or incorrect: {ability_details}")
else:
    print(f"FAILURE: Error creating role: {role_serializer.errors}")
    sys.exit(1)

# 3. Create Game
print("\n[TestCase] Creating Game...")
game_data = {
    "name": "Test Game",
    "min_players": 4,
    "max_players": 10,
    "role_slots": [
        {"role": role.id, "count": 1}
    ]
}
game_serializer = GameTemplateSerializer(data=game_data)
if game_serializer.is_valid():
    game = game_serializer.save()
    print(f"SUCCESS: Created Game: {game}")
    # Verify role slots
    slots = list(game.role_slots.all())
    if len(slots) > 0 and slots[0].role.id == role.id:
         print(f"SUCCESS: Game Role Slots verified: {slots}")
    else:
         print(f"FAILURE: Game Role Slots missing or incorrect: {slots}")
else:
    print(f"FAILURE: Error creating game: {game_serializer.errors}")
    sys.exit(1)

print("\n--- Backend Flow Test Completed Successfully ---")
