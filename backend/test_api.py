import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth.models import User
from games.models import GameTemplate

gt = GameTemplate.objects.first()

user = User.objects.first()
client = APIClient()
client.force_authenticate(user=user)

payload = {
    "name": "API Test Update",
    "min_players": 4,
    "max_players": 10,
    "is_public": True,
    "role_slots": [],
    "phases": [
        {"name": "Night", "phase_type": "NIGHT", "order": 0}
    ],
    "win_conditions": [
        {
            "name": "Town Win", 
            "winner_alignment": "TOWN", 
            "order": 0, 
            "criteria": [{"type": "ALIGNMENT_COUNT", "target": "MAFIA", "count": 0}]
        }
    ]
}

response = client.put(f"/game-templates/{gt.id}/", payload, format='json', HTTP_HOST='localhost')
with open('error.html', 'w', encoding='utf-8') as f:
    f.write(response.content.decode('utf-8'))
print("Error HTML saved to error.html")
