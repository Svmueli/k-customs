import hashlib
import json
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.utils import timezone

from orders.models import Order

from .daraja import normalize_kenyan_phone_number
from .models import MpesaCallbackDelivery, MpesaCallbackOutcome, MpesaStkAttempt, Payment


MAX_CHECKOUT_ID = 100
MAX_MERCHANT_ID = 100
MAX_RECEIPT = 100
MAX_PHONE = 30
MAX_TRANSACTION_DATE = 30
MAX_RESULT_CODE = 2_147_483_647
SENSITIVE_KEYS = {
    "password", "passkey", "authorization", "access_token", "token",
    "consumer_key", "consumer_secret",
}


class ActiveAttemptError(Exception):
    pass


class IneligiblePaymentError(Exception):
    pass


class IdempotencyConflictError(Exception):
    pass


def redact_payload(value):
    """Retain provider diagnostics without retaining reusable credentials."""
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if key.lower() in SENSITIVE_KEYS else redact_payload(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    return value


def _payload_hash(payload):
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _safe_string(value, maximum):
    if value is None:
        return ""
    value = str(value)
    if len(value) > maximum:
        raise ValueError(f"Value exceeds {maximum} characters.")
    return value


def _invalid_delivery(payload, note, checkout_request_id=""):
    return MpesaCallbackDelivery.objects.create(
        checkout_request_id=checkout_request_id if len(checkout_request_id) <= MAX_CHECKOUT_ID else "",
        payload=payload if isinstance(payload, dict) else {"raw": str(payload)[:1000]},
        payload_hash=_payload_hash(payload),
        processing_status=MpesaCallbackDelivery.ProcessingStatus.INVALID,
        processing_note=note,
    )


def start_stk_attempt(*, payment, idempotency_key, phone_number, client):
    phone_number = normalize_kenyan_phone_number(phone_number)
    if payment.amount != payment.amount.to_integral_value():
        raise ValueError("M-Pesa payments must be whole Kenyan shillings.")
    with transaction.atomic():
        payment = Payment.objects.select_for_update().select_related("order").get(pk=payment.pk)
        order = Order.objects.select_for_update().get(pk=payment.order_id)
        if order.status != Order.Status.PAYMENT_PENDING:
            raise IneligiblePaymentError("This order is not awaiting payment.")
        if payment.status not in [Payment.Status.PENDING, Payment.Status.FAILED, Payment.Status.PROCESSING]:
            raise IneligiblePaymentError("This payment cannot be retried.")
        existing = MpesaStkAttempt.objects.filter(payment=payment, client_idempotency_key=idempotency_key).first()
        if existing:
            if existing.phone_number != phone_number:
                raise IdempotencyConflictError(
                    "This idempotency key has already been used with different request data."
                )
            return existing, False
        active = MpesaStkAttempt.objects.filter(
            payment=payment,
            status__in=[
                MpesaStkAttempt.Status.DISPATCHING,
                MpesaStkAttempt.Status.ACCEPTED,
                MpesaStkAttempt.Status.UNKNOWN,
            ],
        ).first()
        if active:
            raise ActiveAttemptError("This payment already has an active M-Pesa attempt.")
        attempt = MpesaStkAttempt.objects.create(
            payment=payment,
            client_idempotency_key=idempotency_key,
            phone_number=phone_number,
            amount=payment.amount,
            status=MpesaStkAttempt.Status.DISPATCHING,
        )

    try:
        request_payload, response_payload = client.stk_push(
            phone_number=phone_number,
            amount=payment.amount,
            account_reference=payment.order.order_number,
            transaction_desc=f"KimCustoms {payment.order.order_number}",
        )
    except Exception as exc:
        from .daraja import DarajaTimeout

        status = MpesaStkAttempt.Status.UNKNOWN if isinstance(exc, DarajaTimeout) else MpesaStkAttempt.Status.REJECTED
        MpesaStkAttempt.objects.filter(pk=attempt.pk).update(status=status)
        raise

    accepted = str(response_payload.get("ResponseCode", "")) == "0"
    checkout_request_id = response_payload.get("CheckoutRequestID") or None
    try:
        if checkout_request_id:
            checkout_request_id = _safe_string(checkout_request_id, MAX_CHECKOUT_ID)
        merchant_request_id = _safe_string(response_payload.get("MerchantRequestID", ""), MAX_MERCHANT_ID)
        with transaction.atomic():
            attempt = MpesaStkAttempt.objects.select_for_update().get(pk=attempt.pk)
            payment = Payment.objects.select_for_update().get(pk=attempt.payment_id)
            attempt.request_payload = redact_payload(request_payload)
            attempt.response_payload = redact_payload(response_payload)
            attempt.merchant_request_id = merchant_request_id
            attempt.checkout_request_id = checkout_request_id
            attempt.status = MpesaStkAttempt.Status.ACCEPTED if accepted and checkout_request_id else MpesaStkAttempt.Status.REJECTED
            attempt.save()
            if attempt.status == MpesaStkAttempt.Status.ACCEPTED:
                payment.status = Payment.Status.PROCESSING
                payment.merchant_request_id = merchant_request_id
                payment.checkout_request_id = checkout_request_id
                payment.phone_number = phone_number
                payment.save()
    except (IntegrityError, ValueError):
        MpesaStkAttempt.objects.filter(pk=attempt.pk).update(status=MpesaStkAttempt.Status.UNKNOWN)
        raise
    reconcile_unresolved_callbacks(checkout_request_id=attempt.checkout_request_id)
    return attempt, True


def _callback_values(payload):
    if not isinstance(payload, dict):
        raise ValueError("Callback must be a JSON object.")
    callback = payload["Body"]["stkCallback"]
    if not isinstance(callback, dict):
        raise ValueError("stkCallback must be an object.")
    metadata = callback.get("CallbackMetadata", {})
    items = metadata.get("Item", []) if isinstance(metadata, dict) else []
    if not isinstance(items, list):
        raise ValueError("Callback metadata must be a list.")
    values = {}
    for item in items:
        if not isinstance(item, dict) or "Name" not in item:
            raise ValueError("Callback metadata contains an invalid item.")
        values[str(item["Name"])] = item.get("Value")
    return callback, values


def _normalised_callback(payload):
    callback, values = _callback_values(payload)
    checkout_request_id = _safe_string(callback["CheckoutRequestID"], MAX_CHECKOUT_ID)
    merchant_request_id = _safe_string(callback.get("MerchantRequestID", ""), MAX_MERCHANT_ID)
    result_code = int(callback["ResultCode"])
    if not -MAX_RESULT_CODE - 1 <= result_code <= MAX_RESULT_CODE:
        raise ValueError("Result code is outside database range.")
    try:
        amount = Decimal(str(values["Amount"])) if "Amount" in values else None
    except (InvalidOperation, ValueError):
        amount = None
    phone_number = _safe_string(values.get("PhoneNumber", ""), MAX_PHONE)
    if phone_number:
        phone_number = normalize_kenyan_phone_number(phone_number)
    receipt = _safe_string(values.get("MpesaReceiptNumber", ""), MAX_RECEIPT)
    transaction_date = _safe_string(values.get("TransactionDate", ""), MAX_TRANSACTION_DATE)
    if result_code == 0:
        if not receipt:
            raise ValueError("Successful callback is missing M-Pesa receipt number.")
        if not transaction_date.isdigit() or len(transaction_date) != 14:
            raise ValueError("Successful callback has invalid transaction date.")
    return {
        "checkout_request_id": checkout_request_id,
        "merchant_request_id": merchant_request_id,
        "result_code": result_code,
        "amount": amount,
        "phone_number": phone_number,
        "receipt": receipt,
        "transaction_date": transaction_date,
        "result_description": str(callback.get("ResultDesc", "")),
    }


def _same_outcome(existing, data):
    return (
        existing.result_code == data["result_code"]
        and existing.result_description == data["result_description"]
        and existing.merchant_request_id == data["merchant_request_id"]
        and existing.mpesa_receipt_number == data["receipt"]
        and existing.amount == data["amount"]
        and existing.phone_number == data["phone_number"]
        and existing.transaction_date == data["transaction_date"]
    )


def apply_stk_callback(payload):
    """Audit every parsed delivery; apply no more than one valid outcome."""
    try:
        data = _normalised_callback(payload)
    except (KeyError, TypeError, ValueError) as exc:
        return _invalid_delivery(payload, f"Invalid STK callback: {exc}")
    with transaction.atomic():
        delivery = MpesaCallbackDelivery.objects.create(
            checkout_request_id=data["checkout_request_id"],
            payload=payload,
            payload_hash=_payload_hash(payload),
        )
        attempt = MpesaStkAttempt.objects.select_for_update().select_related("payment__order").filter(
            checkout_request_id=data["checkout_request_id"]
        ).first()
        if not attempt:
            delivery.processing_status = MpesaCallbackDelivery.ProcessingStatus.UNRESOLVED
            delivery.processing_note = "No M-Pesa attempt matches CheckoutRequestID."
            delivery.save(update_fields=["processing_status", "processing_note"])
            return delivery
        delivery.attempt = attempt
        if hasattr(attempt, "callback_outcome"):
            delivery.processing_status = MpesaCallbackDelivery.ProcessingStatus.DUPLICATE if _same_outcome(attempt.callback_outcome, data) else MpesaCallbackDelivery.ProcessingStatus.CONFLICT
            delivery.processing_note = "An identical outcome was already applied." if delivery.processing_status == MpesaCallbackDelivery.ProcessingStatus.DUPLICATE else "A conflicting outcome was received after an outcome was applied."
            delivery.save(update_fields=["attempt", "processing_status", "processing_note"])
            return delivery
        if data["merchant_request_id"] and attempt.merchant_request_id and data["merchant_request_id"] != attempt.merchant_request_id:
            delivery.processing_status = MpesaCallbackDelivery.ProcessingStatus.CONFLICT
            delivery.processing_note = "MerchantRequestID does not match the attempt."
            delivery.save(update_fields=["attempt", "processing_status", "processing_note"])
            return delivery
        if data["result_code"] == 0 and (data["amount"] != attempt.amount or data["phone_number"] != attempt.phone_number):
            delivery.processing_status = MpesaCallbackDelivery.ProcessingStatus.CONFLICT
            delivery.processing_note = "Successful callback metadata does not match the attempt."
            delivery.save(update_fields=["attempt", "processing_status", "processing_note"])
            return delivery
        payment = Payment.objects.select_for_update().get(pk=attempt.payment_id)
        order = Order.objects.select_for_update().get(pk=payment.order_id)
        if payment.status != Payment.Status.PROCESSING or order.status != Order.Status.PAYMENT_PENDING:
            delivery.processing_status = MpesaCallbackDelivery.ProcessingStatus.CONFLICT
            delivery.processing_note = "Payment/order state is incompatible; manual reconciliation required."
            delivery.save(update_fields=["attempt", "processing_status", "processing_note"])
            return delivery
        if data["receipt"] and MpesaCallbackOutcome.objects.filter(mpesa_receipt_number=data["receipt"]).exists():
            delivery.processing_status = MpesaCallbackDelivery.ProcessingStatus.CONFLICT
            delivery.processing_note = "M-Pesa receipt is already associated with another outcome."
            delivery.save(update_fields=["attempt", "processing_status", "processing_note"])
            return delivery
        try:
            with transaction.atomic():
                outcome = MpesaCallbackOutcome.objects.create(
                    attempt=attempt, applied_delivery=delivery, result_code=data["result_code"],
                    result_description=data["result_description"], merchant_request_id=data["merchant_request_id"],
                    mpesa_receipt_number=data["receipt"], amount=data["amount"],
                    phone_number=data["phone_number"], transaction_date=data["transaction_date"],
                )
        except IntegrityError:
            delivery.processing_status = MpesaCallbackDelivery.ProcessingStatus.CONFLICT
            delivery.processing_note = "Callback outcome conflicts with an existing provider record."
            delivery.save(update_fields=["attempt", "processing_status", "processing_note"])
            return delivery
        payment.result_code = data["result_code"]
        payment.result_description = outcome.result_description
        payment.callback_received_at = timezone.now()
        if data["result_code"] == 0:
            attempt.status = MpesaStkAttempt.Status.COMPLETED
            attempt.save(update_fields=["status", "updated_at"])
            payment.status = Payment.Status.COMPLETED
            payment.mpesa_receipt_number = outcome.mpesa_receipt_number
            payment.transaction_reference = outcome.mpesa_receipt_number
            order.status = Order.Status.PAID
            order.save(update_fields=["status", "updated_at"])
        else:
            attempt.status = MpesaStkAttempt.Status.FAILED
            attempt.save(update_fields=["status", "updated_at"])
            payment.status = Payment.Status.FAILED
        payment.save()
        delivery.processing_status = MpesaCallbackDelivery.ProcessingStatus.APPLIED
        delivery.save(update_fields=["attempt", "processing_status"])
        return delivery


def reconcile_unresolved_callbacks(*, checkout_request_id):
    if not checkout_request_id:
        return 0
    count = 0
    for original in MpesaCallbackDelivery.objects.filter(
        checkout_request_id=checkout_request_id,
        processing_status=MpesaCallbackDelivery.ProcessingStatus.UNRESOLVED,
    ).order_by("pk"):
        replay = apply_stk_callback(original.payload)
        original.processing_note = f"Replayed as callback delivery {replay.pk}."
        original.save(update_fields=["processing_note"])
        count += 1
    return count
