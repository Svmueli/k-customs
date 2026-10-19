# Generated manually for payment initiation authorization and callback audit.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("payments", "0002_payment_daraja_fields_and_mpesa_attempts")]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="initiation_token_hash",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="mpesacallbackoutcome",
            name="merchant_request_id",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
