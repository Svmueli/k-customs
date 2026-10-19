from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("payments", "0003_payment_initiation_token_and_callback_merchant_id")]

    operations = [
        migrations.AlterField(
            model_name="mpesastkattempt",
            name="status",
            field=models.CharField(
                choices=[
                    ("dispatching", "Dispatching"), ("accepted", "Accepted"),
                    ("rejected", "Rejected"), ("unknown", "Unknown"),
                    ("failed", "Failed"), ("completed", "Completed"),
                ],
                default="dispatching",
                max_length=20,
            ),
        ),
    ]
