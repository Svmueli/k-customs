from decimal import Decimal
from datetime import timedelta
from threading import Barrier, Thread
from unittest.mock import Mock, patch

from django.db import close_old_connections, connection
from django.core.cache import cache
from django.core.management import call_command
from django.test import TransactionTestCase, tag
from io import StringIO
from unittest import skipUnless
from django.test import TestCase, override_settings
from django.utils import timezone

from customers.models import Customer
from orders.models import Order

from .daraja import DarajaTimeout
from .models import MpesaCallbackDelivery, MpesaCallbackOutcome, MpesaStkAttempt, Payment
from .security import hash_payment_token, new_payment_token
from .services import (
    apply_stk_callback,
    redact_payload,
    reconcile_unresolved_callbacks,
    start_stk_attempt,
)


class PaymentFactoryMixin:
    def payment(self):
        customer = Customer.objects.create(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.test",
            phone="254712345678",
        )
        order = Order.objects.create(
            customer=customer,
            order_number="KC-TEST0001",
            status=Order.Status.PAYMENT_PENDING,
            subtotal=Decimal("100.00"),
            delivery_fee=Decimal("0.00"),
            total=Decimal("100.00"),
            delivery_address="Nairobi",
            delivery_city="Nairobi",
        )
        token = new_payment_token()
        payment = Payment.objects.create(
            order=order,
            method=Payment.Method.MPESA,
            amount=Decimal("100.00"),
            initiation_token_hash=hash_payment_token(token),
            initiation_token_expires_at=timezone.now() + timedelta(minutes=30),
        )
        payment.test_token = token
        return payment


def callback(*, checkout_id="ws_CO_1", result_code=0, receipt="RCP123", merchant_id="mr_1"):
    items = [
        {"Name": "Amount", "Value": 100},
        {"Name": "PhoneNumber", "Value": 254712345678},
        {"Name": "TransactionDate", "Value": 20260904120000},
    ]
    if receipt:
        items.append({"Name": "MpesaReceiptNumber", "Value": receipt})
    return {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": merchant_id,
                "CheckoutRequestID": checkout_id,
                "ResultCode": result_code,
                "ResultDesc": "Success" if result_code == 0 else "Cancelled by user",
                "CallbackMetadata": {"Item": items},
            }
        }
    }

class MpesaCallbackTests(PaymentFactoryMixin, TestCase):
    def setUp(self):
        self.payment = self.payment()
        self.attempt = MpesaStkAttempt.objects.create(
            payment=self.payment,
            client_idempotency_key="key-1",
            phone_number="254712345678",
            amount=Decimal("100.00"),
            status=MpesaStkAttempt.Status.ACCEPTED,
            checkout_request_id="ws_CO_1",
            merchant_request_id="mr_1",
        )
        self.payment.status = Payment.Status.PROCESSING
        self.payment.save(update_fields=["status"])

    def test_duplicate_callback_is_audited_but_transitions_once(self):
        first = apply_stk_callback(callback())
        second = apply_stk_callback(callback())

        self.payment.refresh_from_db()
        self.payment.order.refresh_from_db()
        self.assertEqual(first.processing_status, MpesaCallbackDelivery.ProcessingStatus.APPLIED)
        self.assertEqual(second.processing_status, MpesaCallbackDelivery.ProcessingStatus.DUPLICATE)
        self.assertEqual(MpesaCallbackDelivery.objects.count(), 2)
        self.assertEqual(MpesaCallbackOutcome.objects.count(), 1)
        self.assertEqual(self.payment.status, Payment.Status.COMPLETED)
        self.assertEqual(self.payment.order.status, Order.Status.PAID)

    def test_conflicting_later_callback_is_audited_without_second_transition(self):
        apply_stk_callback(callback(result_code=1032, receipt=""))
        late_success = apply_stk_callback(callback(result_code=0, receipt="RCP456"))

        self.payment.refresh_from_db()
        self.payment.order.refresh_from_db()
        self.assertEqual(late_success.processing_status, MpesaCallbackDelivery.ProcessingStatus.CONFLICT)
        self.assertEqual(MpesaCallbackOutcome.objects.count(), 1)
        self.assertEqual(self.payment.status, Payment.Status.FAILED)
        self.assertEqual(self.payment.order.status, Order.Status.PAYMENT_PENDING)

    def test_unknown_callback_is_retained_for_reconciliation(self):
        delivery = apply_stk_callback(callback(checkout_id="unknown"))

        self.assertEqual(delivery.processing_status, MpesaCallbackDelivery.ProcessingStatus.UNRESOLVED)
        self.assertEqual(MpesaCallbackDelivery.objects.count(), 1)
        self.assertEqual(MpesaCallbackOutcome.objects.count(), 0)

    def test_success_without_receipt_is_invalid_and_cannot_complete_payment(self):
        delivery = apply_stk_callback(callback(receipt=""))

        self.payment.refresh_from_db()
        self.assertEqual(delivery.processing_status, MpesaCallbackDelivery.ProcessingStatus.INVALID)
        self.assertEqual(self.payment.status, Payment.Status.PROCESSING)
        self.assertEqual(MpesaCallbackOutcome.objects.count(), 0)

    def test_same_code_and_receipt_with_different_metadata_is_conflict(self):
        apply_stk_callback(callback())
        conflicting = callback()
        conflicting["Body"]["stkCallback"]["CallbackMetadata"]["Item"][0]["Value"] = 99

        delivery = apply_stk_callback(conflicting)
        self.assertEqual(delivery.processing_status, MpesaCallbackDelivery.ProcessingStatus.CONFLICT)

    def test_cancelled_order_late_success_requires_manual_reconciliation(self):
        self.payment.order.status = Order.Status.CANCELLED
        self.payment.order.save(update_fields=["status"])

        delivery = apply_stk_callback(callback())
        self.payment.refresh_from_db()
        self.assertEqual(delivery.processing_status, MpesaCallbackDelivery.ProcessingStatus.CONFLICT)
        self.assertEqual(self.payment.status, Payment.Status.PROCESSING)
        self.assertEqual(MpesaCallbackOutcome.objects.count(), 0)

    def test_out_of_order_callback_reconciles_without_reusing_delivery_row(self):
        # Simulate a callback that arrived before its provider ID was persisted.
        self.attempt.checkout_request_id = None
        self.attempt.save(update_fields=["checkout_request_id"])
        original = apply_stk_callback(callback())
        self.attempt.checkout_request_id = "ws_CO_1"
        self.attempt.save(update_fields=["checkout_request_id"])

        reconcile_unresolved_callbacks(checkout_request_id="ws_CO_1")

        original.refresh_from_db()
        self.assertEqual(MpesaCallbackDelivery.objects.count(), 2)
        self.assertIn("Replayed as callback delivery", original.processing_note)
        self.assertEqual(MpesaCallbackOutcome.objects.count(), 1)


class MpesaInitiationTests(PaymentFactoryMixin, TestCase):
    def setUp(self):
        cache.clear()
        self.payment = self.payment()

    def test_same_key_returns_original_attempt_without_second_prompt(self):
        client = Mock()
        client.stk_push.return_value = (
            {"PhoneNumber": "254712345678"},
            {
                "ResponseCode": "0",
                "MerchantRequestID": "mr_1",
                "CheckoutRequestID": "ws_CO_1",
            },
        )
        first, created = start_stk_attempt(
            payment=self.payment,
            idempotency_key="retry-safe-key",
            phone_number="0712345678",
            client=client,
        )
        second, repeated = start_stk_attempt(
            payment=self.payment,
            idempotency_key="retry-safe-key",
            phone_number="0712345678",
            client=client,
        )

        self.assertTrue(created)
        self.assertFalse(repeated)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(client.stk_push.call_count, 1)

    def test_timeout_is_unknown_and_does_not_allow_another_prompt(self):
        client = Mock()
        client.stk_push.side_effect = DarajaTimeout("timeout")

        with self.assertRaises(DarajaTimeout):
            start_stk_attempt(
                payment=self.payment,
                idempotency_key="timeout-key",
                phone_number="0712345678",
                client=client,
            )

        attempt = MpesaStkAttempt.objects.get()
        self.assertEqual(attempt.status, MpesaStkAttempt.Status.UNKNOWN)

    def test_failed_payment_can_retry_and_complete_with_a_new_attempt(self):
        first = MpesaStkAttempt.objects.create(
            payment=self.payment,
            client_idempotency_key="first-key",
            phone_number="254712345678",
            amount=Decimal("100.00"),
            status=MpesaStkAttempt.Status.ACCEPTED,
            checkout_request_id="ws_CO_failed",
            merchant_request_id="mr_failed",
        )
        self.payment.status = Payment.Status.PROCESSING
        self.payment.save(update_fields=["status"])
        apply_stk_callback(callback(checkout_id=first.checkout_request_id, result_code=1032, receipt="", merchant_id="mr_failed"))

        client = Mock()
        client.stk_push.return_value = (
            {"Password": "secret", "PhoneNumber": "254712345678"},
            {"ResponseCode": "0", "MerchantRequestID": "mr_retry", "CheckoutRequestID": "ws_CO_retry"},
        )
        retry, created = start_stk_attempt(
            payment=self.payment,
            idempotency_key="retry-key",
            phone_number="0712345678",
            client=client,
        )
        apply_stk_callback(callback(checkout_id=retry.checkout_request_id, receipt="RCP-RETRY", merchant_id="mr_retry"))

        self.payment.refresh_from_db()
        self.payment.order.refresh_from_db()
        retry.refresh_from_db()
        self.assertTrue(created)
        self.assertEqual(self.payment.status, Payment.Status.COMPLETED)
        self.assertEqual(self.payment.order.status, Order.Status.PAID)
        self.assertEqual(retry.request_payload["Password"], "[REDACTED]")

    def test_fractional_amount_is_rejected_before_provider_call(self):
        self.payment.amount = Decimal("100.50")
        self.payment.save(update_fields=["amount"])
        client = Mock()

        with self.assertRaises(ValueError):
            start_stk_attempt(
                payment=self.payment,
                idempotency_key="fraction-key",
                phone_number="0712345678",
                client=client,
            )
        self.assertFalse(client.stk_push.called)
        self.assertEqual(MpesaStkAttempt.objects.count(), 0)

    def test_redaction_removes_all_provider_secret_fields(self):
        payload = redact_payload({
            "Password": "password", "Authorization": "Bearer token",
            "access_token": "token", "nested": [{"consumer_secret": "secret"}],
        })
        self.assertEqual(payload["Password"], "[REDACTED]")
        self.assertEqual(payload["Authorization"], "[REDACTED]")
        self.assertEqual(payload["access_token"], "[REDACTED]")
        self.assertEqual(payload["nested"][0]["consumer_secret"], "[REDACTED]")

    def test_reconciliation_command_reports_stuck_attempt_without_prompting(self):
        MpesaStkAttempt.objects.create(
            payment=self.payment,
            client_idempotency_key="unknown-key",
            phone_number="254712345678",
            amount=Decimal("100.00"),
            status=MpesaStkAttempt.Status.UNKNOWN,
        )
        output = StringIO()
        call_command("reconcile_mpesa_attempts", "--older-than-minutes", "0", stdout=output)
        self.assertIn("stuck_attempts=1", output.getvalue())

    @patch("payments.views.DarajaClient")
    def test_endpoint_requires_and_replays_idempotency_key(self, client_class):
        client_class.return_value.stk_push.return_value = (
            {"PhoneNumber": "254712345678"},
            {
                "ResponseCode": "0",
                "MerchantRequestID": "mr_1",
                "CheckoutRequestID": "ws_CO_1",
            },
        )
        url = "/api/payments/mpesa/stk-push/"
        data = {"payment_token": self.payment.test_token, "phone_number": "0712345678"}

        missing = self.client.post(url, data, content_type="application/json")
        first = self.client.post(url, data, content_type="application/json", headers={"Idempotency-Key": "api-key"})
        second = self.client.post(url, data, content_type="application/json", headers={"Idempotency-Key": "api-key"})

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(client_class.return_value.stk_push.call_count, 1)

    def test_endpoint_rejects_missing_or_invalid_payment_token(self):
        url = "/api/payments/mpesa/stk-push/"
        missing = self.client.post(url, {"phone_number": "0712345678"}, content_type="application/json", headers={"Idempotency-Key": "key"})
        invalid = self.client.post(url, {"payment_token": "not-a-payment-token", "phone_number": "0712345678"}, content_type="application/json", headers={"Idempotency-Key": "key"})

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(invalid.status_code, 404)

    @patch("payments.views.DarajaClient")
    def test_endpoint_rejects_expired_payment_token(self, client_class):
        self.payment.initiation_token_expires_at = timezone.now() - timedelta(seconds=1)
        self.payment.save(update_fields=["initiation_token_expires_at"])

        response = self.client.post(
            "/api/payments/mpesa/stk-push/",
            {"payment_token": self.payment.test_token, "phone_number": "0712345678"},
            content_type="application/json",
            headers={"Idempotency-Key": "expired-key"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(client_class.return_value.stk_push.called)

    def test_idempotency_key_cannot_be_reused_for_another_phone_number(self):
        client = Mock()
        client.stk_push.return_value = (
            {"PhoneNumber": "254712345678"},
            {"ResponseCode": "0", "MerchantRequestID": "mr_1", "CheckoutRequestID": "ws_CO_1"},
        )
        start_stk_attempt(
            payment=self.payment,
            idempotency_key="fixed-key",
            phone_number="0712345678",
            client=client,
        )
        from .services import IdempotencyConflictError

        with self.assertRaises(IdempotencyConflictError):
            start_stk_attempt(
                payment=self.payment,
                idempotency_key="fixed-key",
                phone_number="0712345679",
                client=client,
            )
        self.assertEqual(client.stk_push.call_count, 1)


class MpesaCallbackEndpointTests(PaymentFactoryMixin, TestCase):
    def test_malformed_callback_is_audited_and_acknowledged(self):
        response = self.client.post("/api/payments/mpesa/callback/", "{bad", content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(MpesaCallbackDelivery.objects.get().processing_status, MpesaCallbackDelivery.ProcessingStatus.INVALID)

    @override_settings(MPESA_CALLBACK_MAX_BYTES=1)
    def test_oversized_callback_is_audited_and_acknowledged(self):
        response = self.client.post("/api/payments/mpesa/callback/", {"Body": {}}, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(MpesaCallbackDelivery.objects.get().processing_status, MpesaCallbackDelivery.ProcessingStatus.INVALID)

    def test_overlong_callback_identifier_is_audited_and_acknowledged(self):
        payload = callback(checkout_id="x" * 101)
        response = self.client.post("/api/payments/mpesa/callback/", payload, content_type="application/json")

        delivery = MpesaCallbackDelivery.objects.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(delivery.processing_status, MpesaCallbackDelivery.ProcessingStatus.INVALID)
        self.assertEqual(delivery.checkout_request_id, "")


@tag("postgresql")
@skipUnless(connection.vendor == "postgresql", "requires PostgreSQL row locks and partial indexes")
class PostgreSQLPaymentIntegrationTests(PaymentFactoryMixin, TransactionTestCase):
    reset_sequences = True

    def test_concurrent_duplicate_callbacks_apply_exactly_one_outcome(self):
        payment = self.payment()
        attempt = MpesaStkAttempt.objects.create(
            payment=payment,
            client_idempotency_key="pg-key",
            phone_number="254712345678",
            amount=Decimal("100.00"),
            status=MpesaStkAttempt.Status.ACCEPTED,
            checkout_request_id="ws_CO_pg",
            merchant_request_id="mr_pg",
        )
        payment.status = Payment.Status.PROCESSING
        payment.save(update_fields=["status"])
        barrier = Barrier(2)
        errors = []

        def deliver():
            try:
                close_old_connections()
                barrier.wait()
                apply_stk_callback(callback(checkout_id=attempt.checkout_request_id, merchant_id="mr_pg"))
            except Exception as exc:  # pragma: no cover - only executed on PostgreSQL CI
                errors.append(exc)
            finally:
                close_old_connections()

        threads = [Thread(target=deliver), Thread(target=deliver)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])
        self.assertEqual(MpesaCallbackDelivery.objects.count(), 2)
        self.assertEqual(MpesaCallbackOutcome.objects.count(), 1)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.COMPLETED)
