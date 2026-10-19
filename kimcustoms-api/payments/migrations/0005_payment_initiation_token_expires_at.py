from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("payments", "0004_alter_mpesastkattempt_status")]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="initiation_token_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
