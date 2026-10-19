import hashlib
import secrets


def new_payment_token():
    return secrets.token_urlsafe(32)


def hash_payment_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
