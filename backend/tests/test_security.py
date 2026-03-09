"""Password hashing and JWT."""
import pytest

from core.security import hash_password, verify_password, create_access_token, decode_access_token, _password_bytes


def test_password_bytes_truncates_long():
    long_str = "a" * 100
    out = _password_bytes(long_str)
    assert len(out) == 72


def test_hash_and_verify():
    h = hash_password("mypassword")
    assert isinstance(h, str)
    assert len(h) > 20
    assert verify_password("mypassword", h) is True
    assert verify_password("wrong", h) is False


def test_verify_long_password():
    h = hash_password("a" * 100)
    assert verify_password("a" * 100, h) is True


def test_create_and_decode_token():
    token = create_access_token(1)
    assert isinstance(token, str)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "1"


def test_decode_invalid_token():
    assert decode_access_token("invalid") is None
    assert decode_access_token("") is None
