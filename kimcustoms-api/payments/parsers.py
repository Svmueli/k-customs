import json

from django.conf import settings
from rest_framework.exceptions import ParseError
from rest_framework.parsers import BaseParser


class BoundedJSONParser(BaseParser):
    media_type = "application/json"

    def parse(self, stream, media_type=None, parser_context=None):
        raw = stream.read(settings.MPESA_CALLBACK_MAX_BYTES + 1)
        if len(raw) > settings.MPESA_CALLBACK_MAX_BYTES:
            raise ParseError("Callback body exceeds the configured size limit.")
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ParseError("Malformed callback JSON.") from exc
