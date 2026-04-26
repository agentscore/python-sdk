"""Tests for verify_webhook_signature."""

import hashlib
import hmac
import time

from agentscore import verify_webhook_signature
from agentscore.errors import AgentScoreError

SECRET = "whsec_testsecret"


def _sign(payload: str, ts: int, secret: str = SECRET) -> str:
    signed = f"{ts}.{payload}".encode()
    return hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()


def test_accepts_valid_signature_with_current_timestamp():
    payload = '{"event":"test"}'
    ts = int(time.time())
    sig = _sign(payload, ts)
    result = verify_webhook_signature(
        payload=payload,
        signature_header=f"t={ts},v1={sig}",
        secret=SECRET,
    )
    assert result.valid is True


def test_accepts_bytes_payload():
    payload = b'{"event":"test"}'
    ts = int(time.time())
    sig = _sign(payload.decode("utf-8"), ts)
    result = verify_webhook_signature(
        payload=payload,
        signature_header=f"t={ts},v1={sig}",
        secret=SECRET,
    )
    assert result.valid is True


def test_rejects_timestamp_older_than_tolerance():
    payload = "{}"
    ts = int(time.time()) - 600
    sig = _sign(payload, ts)
    result = verify_webhook_signature(
        payload=payload,
        signature_header=f"t={ts},v1={sig}",
        secret=SECRET,
        tolerance_seconds=300,
    )
    assert result.valid is False
    assert result.reason == "timestamp_too_old"


def test_rejects_timestamp_in_future():
    payload = "{}"
    ts = int(time.time()) + 600
    sig = _sign(payload, ts)
    result = verify_webhook_signature(
        payload=payload,
        signature_header=f"t={ts},v1={sig}",
        secret=SECRET,
    )
    assert result.valid is False
    assert result.reason == "timestamp_in_future"


def test_rejects_signature_mismatch():
    payload = "{}"
    ts = int(time.time())
    sig = _sign(payload, ts, secret="wrong_secret")
    result = verify_webhook_signature(
        payload=payload,
        signature_header=f"t={ts},v1={sig}",
        secret=SECRET,
    )
    assert result.valid is False
    assert result.reason == "signature_mismatch"


def test_no_signatures_for_empty_header():
    result = verify_webhook_signature(payload="{}", signature_header="", secret=SECRET)
    assert result.valid is False
    assert result.reason == "no_signatures"


def test_malformed_header():
    result = verify_webhook_signature(payload="{}", signature_header="just_a_value", secret=SECRET)
    assert result.valid is False
    assert result.reason == "malformed_header"


def test_no_timestamp_when_missing_and_tolerance_positive():
    payload = "{}"
    sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    result = verify_webhook_signature(payload=payload, signature_header=f"v1={sig}", secret=SECRET)
    assert result.valid is False
    assert result.reason == "no_timestamp"


def test_tolerance_zero_skips_timestamp_check():
    payload = '{"event":"test"}'
    sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    result = verify_webhook_signature(
        payload=payload,
        signature_header=f"v1={sig}",
        secret=SECRET,
        tolerance_seconds=0,
    )
    assert result.valid is True


def test_multiple_signatures_any_match():
    payload = "{}"
    ts = int(time.time())
    sig_good = _sign(payload, ts)
    sig_bad = hmac.new(b"wrong", f"{ts}.{payload}".encode(), hashlib.sha256).hexdigest()
    result = verify_webhook_signature(
        payload=payload,
        signature_header=f"t={ts},v1={sig_bad},v1={sig_good}",
        secret=SECRET,
    )
    assert result.valid is True


def test_status_alias_matches_status_code():
    """AgentScoreError.status property mirrors .status_code (parity with node-sdk)."""
    err = AgentScoreError(code="rate_limited", message="too many", status_code=429)
    assert err.status == 429
    assert err.status == err.status_code
