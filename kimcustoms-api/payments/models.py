from django.db import models
from django.db.models import Q

from orders.models import Order


class Payment(models.Model):
    class Method(models.TextChoices):
        MPESA = "mpesa", "M-Pesa"
        CARD = "card", "Card"
        CASH = "cash", "Cash on delivery"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    method = models.CharField(
        max_length=20,
        choices=Method.choices,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    transaction_reference = models.CharField(
        max_length=100,
        blank=True,
    )

    provider_reference = models.CharField(
        max_length=150,
        blank=True,
    )

    # Daraja identifiers
    merchant_request_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
    )

    checkout_request_id = models.CharField(
        max_length=100,
        blank=True,
        unique=True,
        null=True,
    )

    result_code = models.IntegerField(
        null=True,
        blank=True,
    )

    result_description = models.TextField(
        blank=True,
    )

    mpesa_receipt_number = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
    )

    phone_number = models.CharField(
        max_length=30,
        blank=True,
    )

    callback_received_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    initiation_token_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        unique=True,
    )

    initiation_token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.order.order_number} - {self.method}"


class MpesaStkAttempt(models.Model):
    class Status(models.TextChoices):
        DISPATCHING = "dispatching", "Dispatching"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        UNKNOWN = "unknown", "Unknown"
        FAILED = "failed", "Failed"
        COMPLETED = "completed", "Completed"

    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name="mpesa_attempts",
    )
    client_idempotency_key = models.CharField(max_length=128)
    phone_number = models.CharField(max_length=30)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DISPATCHING,
    )
    merchant_request_id = models.CharField(max_length=100, blank=True)
    checkout_request_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )
    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["payment", "client_idempotency_key"],
                name="unique_mpesa_idempotency_key_per_payment",
            ),
        ]

    def __str__(self):
        return f"M-Pesa attempt {self.pk} for {self.payment}"


class MpesaCallbackDelivery(models.Model):
    class ProcessingStatus(models.TextChoices):
        RECEIVED = "received", "Received"
        APPLIED = "applied", "Applied"
        DUPLICATE = "duplicate", "Duplicate"
        CONFLICT = "conflict", "Conflict"
        UNRESOLVED = "unresolved", "Unresolved"
        INVALID = "invalid", "Invalid"

    attempt = models.ForeignKey(
        MpesaStkAttempt,
        on_delete=models.PROTECT,
        related_name="callback_deliveries",
        null=True,
        blank=True,
    )
    checkout_request_id = models.CharField(max_length=100, blank=True, db_index=True)
    payload = models.JSONField(default=dict)
    payload_hash = models.CharField(max_length=64, db_index=True)
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.RECEIVED,
    )
    processing_note = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"M-Pesa callback {self.pk} ({self.checkout_request_id})"


class MpesaCallbackOutcome(models.Model):
    # One-to-one is the database-level guarantee that an attempt has only one
    # callback outcome applied, irrespective of concurrent callback requests.
    attempt = models.OneToOneField(
        MpesaStkAttempt,
        on_delete=models.PROTECT,
        related_name="callback_outcome",
    )
    applied_delivery = models.ForeignKey(
        MpesaCallbackDelivery,
        on_delete=models.PROTECT,
        related_name="applied_outcomes",
    )
    result_code = models.IntegerField()
    result_description = models.TextField(blank=True)
    merchant_request_id = models.CharField(max_length=100, blank=True)
    mpesa_receipt_number = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    transaction_date = models.CharField(max_length=30, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["mpesa_receipt_number"],
                condition=~Q(mpesa_receipt_number=""),
                name="unique_nonempty_mpesa_receipt_number",
            ),
        ]

    def __str__(self):
        return f"M-Pesa outcome for {self.attempt}"
