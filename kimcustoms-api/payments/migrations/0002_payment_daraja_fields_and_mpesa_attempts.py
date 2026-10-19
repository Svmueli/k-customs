# Generated manually for the M-Pesa STK Push foundation.

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="merchant_request_id",
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
        migrations.AddField(
            model_name="payment",
            name="checkout_request_id",
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="payment",
            name="result_code",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="payment",
            name="result_description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="payment",
            name="mpesa_receipt_number",
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
        migrations.AddField(
            model_name="payment",
            name="phone_number",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name="payment",
            name="callback_received_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="MpesaStkAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("client_idempotency_key", models.CharField(max_length=128)),
                ("phone_number", models.CharField(max_length=30)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("status", models.CharField(choices=[("dispatching", "Dispatching"), ("accepted", "Accepted"), ("rejected", "Rejected"), ("unknown", "Unknown")], default="dispatching", max_length=20)),
                ("merchant_request_id", models.CharField(blank=True, max_length=100)),
                ("checkout_request_id", models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ("request_payload", models.JSONField(blank=True, default=dict)),
                ("response_payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("payment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="mpesa_attempts", to="payments.payment")),
            ],
        ),
        migrations.CreateModel(
            name="MpesaCallbackDelivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("checkout_request_id", models.CharField(blank=True, db_index=True, max_length=100)),
                ("payload", models.JSONField(default=dict)),
                ("payload_hash", models.CharField(db_index=True, max_length=64)),
                ("processing_status", models.CharField(choices=[("received", "Received"), ("applied", "Applied"), ("duplicate", "Duplicate"), ("conflict", "Conflict"), ("unresolved", "Unresolved"), ("invalid", "Invalid")], default="received", max_length=20)),
                ("processing_note", models.TextField(blank=True)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                ("attempt", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="callback_deliveries", to="payments.mpesastkattempt")),
            ],
        ),
        migrations.CreateModel(
            name="MpesaCallbackOutcome",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("result_code", models.IntegerField()),
                ("result_description", models.TextField(blank=True)),
                ("mpesa_receipt_number", models.CharField(blank=True, max_length=100)),
                ("amount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("phone_number", models.CharField(blank=True, max_length=30)),
                ("transaction_date", models.CharField(blank=True, max_length=30)),
                ("applied_at", models.DateTimeField(auto_now_add=True)),
                ("applied_delivery", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="applied_outcomes", to="payments.mpesacallbackdelivery")),
                ("attempt", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="callback_outcome", to="payments.mpesastkattempt")),
            ],
        ),
        migrations.AddConstraint(
            model_name="mpesastkattempt",
            constraint=models.UniqueConstraint(fields=("payment", "client_idempotency_key"), name="unique_mpesa_idempotency_key_per_payment"),
        ),
        migrations.AddConstraint(
            model_name="mpesacallbackoutcome",
            constraint=models.UniqueConstraint(condition=~Q(("mpesa_receipt_number", "")), fields=("mpesa_receipt_number",), name="unique_nonempty_mpesa_receipt_number"),
        ),
    ]
