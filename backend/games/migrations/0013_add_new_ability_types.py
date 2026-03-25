from django.db import migrations

def update_ability_choices(apps, schema_editor):
    # Migration will auto-update choices when models.py changes
    pass

def reverse_update(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('games', '0012_gameaction_turn_number'),
    ]

    operations = [
        migrations.RunPython(update_ability_choices, reverse_code=reverse_update),
    ]
