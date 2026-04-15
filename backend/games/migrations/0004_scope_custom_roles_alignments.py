from django.db import migrations, models
import django.db.models.deletion
import django.db.models


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0003_gametemplate_created_at_alter_gamesession_created_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="alignment",
            name="name",
            field=models.CharField(max_length=100),
        ),
        migrations.AddField(
            model_name="alignment",
            name="game_template",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="custom_alignments",
                to="games.gametemplate",
            ),
        ),
        migrations.AddField(
            model_name="roletemplate",
            name="game_template",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="custom_roles",
                to="games.gametemplate",
            ),
        ),
        migrations.AddConstraint(
            model_name="alignment",
            constraint=models.UniqueConstraint(
                condition=django.db.models.Q(("game_template__isnull", True)),
                fields=("name",),
                name="unique_global_alignment_name",
            ),
        ),
        migrations.AddConstraint(
            model_name="alignment",
            constraint=models.UniqueConstraint(
                fields=("game_template", "name"),
                name="unique_template_alignment_name",
            ),
        ),
    ]
