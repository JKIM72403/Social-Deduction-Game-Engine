import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from games.serializers import GameTemplateSerializer
from games.models import GameTemplate

gt = GameTemplate.objects.first()
if getattr(gt, 'id', None) is None:
    print("No game templates found, creating one.")
    gt = GameTemplate.objects.create(name="Test", min_players=1, max_players=2)

try:
    serializer = GameTemplateSerializer(gt, data={
        "name": "Test Update", 
        "min_players": 1, 
        "max_players": 5,
        "phases": [{"name": "Day 1", "phase_type": "DAY"}],
        "win_conditions": [{"name": "Town Win", "winner_alignment": "TOWN"}]
    }, partial=True)
    if serializer.is_valid(raise_exception=True):
        print("VALID")
        serializer.save()
        print("SAVED SUCCESSFULLY")
except Exception as e:
    import traceback
    traceback.print_exc()
