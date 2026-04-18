"""Unit tests for app.services.auth: password hashing + JWT."""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
import pytest
from jose import jwt
from app.config import get_settings
from app.models.base import UserRole
from app.models.user import User
from app.services.auth import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def _user(user_id: int = 1, role: UserRole = UserRole.USER) -> User:
    """Build a detached User ORM instance for token-signing tests."""
    u = User(
        email="who@example.com",
        password_hash="x",
        first_name="W",
        last_name="H",
        role=role,
    )
    u.id = user_id
    return u


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        assert hash_password("hunter2") != "hunter2"

    def test_hash_is_bcrypt_format(self):
        # bcrypt hashes start with $2a/$2b/$2y$
        h = hash_password("hunter2")
        assert h.startswith("$2")

    def test_same_password_produces_different_hashes(self):
        # Salt randomisation → two hashes of the same password differ.
        assert hash_password("hunter2") != hash_password("hunter2")

    def test_verify_accepts_correct_password(self):
        h = hash_password("correct horse battery staple")
        assert verify_password("correct horse battery staple", h) is True

    def test_verify_rejects_wrong_password(self):
        h = hash_password("correct horse battery staple")
        assert verify_password("wrong", h) is False

    def test_verify_rejects_malformed_hash(self):
        # Returning False (not raising) is the expected behaviour — keeps
        # the login endpoint safe if a row has a corrupt hash column.
        assert verify_password("whatever", "not-a-bcrypt-hash") is False

    def test_verify_rejects_empty_hash(self):
        assert verify_password("whatever", "") is False


# ---------------------------------------------------------------------------
# JWT creation / decoding
# ---------------------------------------------------------------------------
class TestJWT:
    def test_token_round_trip(self):
        token = create_access_token(_user(user_id=42, role=UserRole.ADMIN))
        payload = decode_token(token)
        assert payload is not None
        assert payload.sub == 42
        assert payload.role == "admin"

    def test_token_sub_is_string_in_claims(self):
        # We store `sub` as string per JWT best practice (RFC 7519 §4.1.2).
        token = create_access_token(_user(user_id=7))
        settings = get_settings()
        raw = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert raw["sub"] == "7"

    def test_decode_tampered_token_returns_none(self):
        token = create_access_token(_user())
        # Flip a character in the signature part.
        head, payload, sig = token.split(".")
        tampered = f"{head}.{payload}.{sig[:-2]}aa"
        assert decode_token(tampered) is None

    def test_decode_wrong_signature_returns_none(self):
        # Create a token with a totally different secret.
        forged = jwt.encode(
            {
                "sub": "1",
                "role": "admin",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            "attacker-secret",
            algorithm="HS256",
        )
        assert decode_token(forged) is None

    def test_decode_expired_token_returns_none(self):
        settings = get_settings()
        expired = jwt.encode(
            {
                "sub": "1",
                "role": "user",
                "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
            },
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        assert decode_token(expired) is None

    def test_decode_garbage_returns_none(self):
        assert decode_token("not.a.jwt") is None
        assert decode_token("") is None

    def test_decode_missing_sub_returns_none(self):
        settings = get_settings()
        token = jwt.encode(
            {"role": "user", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        assert decode_token(token) is None