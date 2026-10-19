"""Small, dependency-free client for the Daraja STK Push endpoints."""

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from django.conf import settings


class DarajaConfigurationError(Exception):
    pass


class DarajaTimeout(Exception):
    pass


class DarajaRequestError(Exception):
    pass


class DarajaAmountError(ValueError):
    pass


@dataclass
class DarajaClient:
    config: dict | None = None

    def __post_init__(self):
        self.config = self.config or settings.MPESA_DARAJA

    def _require(self, *keys):
        missing = [key for key in keys if not self.config.get(key)]
        if missing:
            raise DarajaConfigurationError(
                "Missing M-Pesa configuration: " + ", ".join(missing)
            )

    def _request(self, request):
        try:
            with urlopen(request, timeout=self.config["timeout_seconds"]) as response:
                return json.loads(response.read().decode("utf-8"))
        except TimeoutError as exc:
            raise DarajaTimeout("Daraja request timed out") from exc
        except URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise DarajaTimeout("Daraja request timed out") from exc
            raise DarajaRequestError("Daraja request failed") from exc
        except HTTPError as exc:
            raise DarajaRequestError(f"Daraja returned HTTP {exc.code}") from exc
        except (ValueError, UnicodeDecodeError) as exc:
            raise DarajaRequestError("Daraja returned invalid JSON") from exc

    def access_token(self):
        self._require("consumer_key", "consumer_secret", "oauth_url")
        credentials = base64.b64encode(
            f"{self.config['consumer_key']}:{self.config['consumer_secret']}".encode()
        ).decode()
        payload = self._request(
            Request(
                self.config["oauth_url"],
                headers={"Authorization": f"Basic {credentials}"},
                method="GET",
            )
        )
        token = payload.get("access_token")
        if not token:
            raise DarajaRequestError("Daraja OAuth response has no access token")
        return token

    def stk_push(self, *, phone_number, amount, account_reference, transaction_desc):
        self._require(
            "shortcode", "passkey", "callback_url", "stk_push_url", "transaction_type"
        )
        if amount != amount.to_integral_value():
            raise DarajaAmountError("M-Pesa payments must be whole Kenyan shillings.")
        timestamp = datetime.now(ZoneInfo("Africa/Nairobi")).strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            f"{self.config['shortcode']}{self.config['passkey']}{timestamp}".encode()
        ).decode()
        payload = {
            "BusinessShortCode": self.config["shortcode"],
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": self.config["transaction_type"],
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": self.config["shortcode"],
            "PhoneNumber": phone_number,
            "CallBackURL": self.config["callback_url"],
            "AccountReference": account_reference,
            "TransactionDesc": transaction_desc,
        }
        request = Request(
            self.config["stk_push_url"],
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.access_token()}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        return payload, self._request(request)


def normalize_kenyan_phone_number(phone_number):
    digits = "".join(character for character in phone_number if character.isdigit())
    if digits.startswith("0") and len(digits) == 10:
        digits = "254" + digits[1:]
    elif digits.startswith("7") and len(digits) == 9:
        digits = "254" + digits
    elif digits.startswith("254") and len(digits) == 12:
        pass
    else:
        raise ValueError("Enter a valid Kenyan mobile number.")

    if not digits.startswith("2547"):
        raise ValueError("Enter a valid Kenyan mobile number.")
    return digits
