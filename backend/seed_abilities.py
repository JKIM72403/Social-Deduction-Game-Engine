import os
import django
import sys

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from games.models import AbilityTemplate

def seed_abilities():
    abilities = [
        {
            "name": "Kill",
            "ability_type": "KILL",
            "phase": "NIGHT",
            "description": "Choose a player to kill at night."
        },
        {
            "name": "Save",
            "ability_type": "PROTECT",
            "phase": "NIGHT",
            "description": "Choose a player to protect from death at night."
        },
        {
            "name": "Investigate",
            "ability_type": "INVESTIGATE",
            "phase": "NIGHT",
            "description": "Discover the alignment of another player."
        }
    ]

    print("Seeding Abilities...")
    for data in abilities:
        ability, created = AbilityTemplate.objects.get_or_create(
            name=data["name"],
            defaults=data
        )
        if created:
            print(f"Created: {ability}")
        else:
            print(f"Already Exists: {ability}")

if __name__ == "__main__":
    seed_abilities()
