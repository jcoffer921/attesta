import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("facilities", "0001_initial"),
        ("validation", "0002_limitresult_explanation_refs"),
    ]

    operations = [
        migrations.RenameField(
            model_name="limitresult",
            old_name="gemini_explanation",
            new_name="explanation",
        ),
        migrations.AddField(
            model_name="validationrun",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="validation_runs",
                to="facilities.organization",
            ),
        ),
    ]
