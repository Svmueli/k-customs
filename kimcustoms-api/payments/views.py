from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.utils import timezone
from rest_framework.exceptions import ParseError, UnsupportedMediaType
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .daraja import DarajaClient, DarajaConfigurationError, DarajaRequestError, DarajaTimeout
from .models import Payment
from .parsers import BoundedJSONParser
from .security import hash_payment_token
from .serializers import StkPushSerializer
from .services import (
    ActiveAttemptError,
    IdempotencyConflictError,
    IneligiblePaymentError,
    apply_stk_callback,
    start_stk_attempt,
)


class MpesaStkPushView(APIView):
    """Initiate one M-Pesa prompt per payment/idempotency key."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "mpesa_stk_push"

    def post(self, request):
        serializer = StkPushSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        payment = (
            Payment.objects.filter(
                method=Payment.Method.MPESA,
                initiation_token_hash=hash_payment_token(data["payment_token"]),
                initiation_token_expires_at__gt=timezone.now(),
            )
            .order_by("-created_at")
            .first()
        )
        if not payment:
            return Response({"detail": "Payment token is invalid."}, status=status.HTTP_404_NOT_FOUND)
        try:
            attempt, created = start_stk_attempt(
                payment=payment,
                idempotency_key=data["idempotency_key"],
                phone_number=data["phone_number"],
                client=DarajaClient(),
            )
        except ValueError as exc:
            return Response({"phone_number": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ActiveAttemptError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except IdempotencyConflictError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except IneligiblePaymentError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except DarajaConfigurationError:
            return Response({"detail": "M-Pesa is not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except DarajaTimeout:
            return Response(
                {"detail": "M-Pesa response timed out; the attempt is being reconciled."},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except DarajaRequestError:
            return Response({"detail": "M-Pesa request failed."}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            {
                "attempt_id": attempt.pk,
                "status": attempt.status,
                "checkout_request_id": attempt.checkout_request_id,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MpesaCallbackView(APIView):
    authentication_classes = []
    permission_classes = []
    parser_classes = [BoundedJSONParser]

    def post(self, request):
        # The provider is always acknowledged after a bounded audit attempt;
        # malformed/unknown callbacks must not trigger retry storms.
        try:
            content_length = int(request.META.get("CONTENT_LENGTH") or 0)
            if content_length > settings.MPESA_CALLBACK_MAX_BYTES:
                apply_stk_callback({"callback_error": "payload exceeds configured size limit"})
            else:
                apply_stk_callback(request.data)
        except (ParseError, UnsupportedMediaType, RequestDataTooBig, ValueError):
            apply_stk_callback({"callback_error": "malformed or unsupported callback body"})
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})
