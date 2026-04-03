"""
Unit tests — app.core.security
Tests: password hashing, JWT creation & decoding.
"""
import time
import pytest
import jwt as pyjwt
from datetime import timedelta

from app.core.security import hash_password, verify_password, create_access_token, decode_token
from app.core.config import settings


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        h = hash_password("mysecret")
        assert h != "mysecret"

    def test_verify_correct_password(self):
        h = hash_password("correct_horse")
        assert verify_password("correct_horse", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("correct_horse")
        assert verify_password("wrong_password", h) is False

    def test_same_password_produces_different_hashes(self):
        """bcrypt uses random salt per call."""
        h1 = hash_password("password")
        h2 = hash_password("password")
        assert h1 != h2

    def test_both_hashes_verify(self):
        h1 = hash_password("password")
        h2 = hash_password("password")
        assert verify_password("password", h1)
        assert verify_password("password", h2)

    def test_empty_password(self):
        h = hash_password("")
        assert verify_password("", h) is True
        assert verify_password("notempty", h) is False

    def test_unicode_password(self):
        pwd = "пароль123!@#"
        h = hash_password(pwd)
        assert verify_password(pwd, h) is True


class TestJWT:
    def test_create_and_decode_token(self):
        token = create_access_token({"sub": 42, "roles": ["admin"]})
        payload = decode_token(token)
        assert payload["sub"] == 42
        assert payload["roles"] == ["admin"]

    def test_token_contains_expiry(self):
        token = create_access_token({"sub": 1})
        payload = decode_token(token)
        assert "exp" in payload

    def test_custom_expiry(self):
        token = create_access_token({"sub": 1}, expires_delta=timedelta(hours=2))
        payload = decode_token(token)
        # exp should be ~2 hours from now
        remaining = payload["exp"] - time.time()
        assert 7100 < remaining < 7300  # between 1h58m and 2h1m

    def test_expired_token_raises(self):
        token = create_access_token({"sub": 1}, expires_delta=timedelta(seconds=-1))
        with pytest.raises(pyjwt.ExpiredSignatureError):
            decode_token(token)

    def test_invalid_signature_raises(self):
        token = create_access_token({"sub": 1})
        # Tamper with token
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + ".invalidsignature"
        with pytest.raises(pyjwt.InvalidSignatureError):
            decode_token(tampered)

    def test_malformed_token_raises(self):
        with pytest.raises(Exception):
            decode_token("not.a.jwt.token.at.all")

    def test_token_string_type(self):
        token = create_access_token({"sub": 1})
        assert isinstance(token, str)

    def test_extra_claims_preserved(self):
        token = create_access_token({"sub": 5, "email": "x@x.com", "custom": [1, 2]})
        payload = decode_token(token)
        assert payload["email"] == "x@x.com"
        assert payload["custom"] == [1, 2]
