"""Webhook signature verification — HMAC-SHA256, Stripe-pattern.

Use this when AgentScore (or any service that signs outbound webhooks with this
convention) sends a webhook to your endpoint. Validates the
``X-AgentScore-Signature`` (or compatible) header before trusting the payload.

Generic enough to cover any HMAC-signed webhook source: pass the right secret + header
name. Tolerant of multiple signature versions in the same header
(``t=...,v1=...`` style).
"""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class VerifyWebhookSignatureResult:
    """Result of :func:`verify_webhook_signature`."""

    valid: bool
    reason: (
        Literal[
            "no_signatures",
            "no_timestamp",
            "timestamp_too_old",
            "timestamp_in_future",
            "signature_mismatch",
            "malformed_header",
        ]
        | None
    ) = None


def verify_webhook_signature(
    payload: str | bytes,
    signature_header: str,
    secret: str,
    tolerance_seconds: int = 300,
    timestamp_key: str = "t",
    signature_key: str = "v1",
) -> VerifyWebhookSignatureResult:
    """Verify an HMAC-SHA256 signed webhook signature, Stripe-compatible.

    Header format: ``t=<unix_seconds>,v1=<hex_hmac>``. The signed payload is
    ``f"{timestamp}.{raw_body}"``. Returns a result with ``reason`` set on failure so
    callers can differentiate transient (timestamp drift) from permanent (mismatch).

    Args:
        payload: Raw request body. MUST be the unparsed body — even one byte of
            re-serialization breaks the signature. Capture before any JSON parse.
        signature_header: Value of the signature header from the incoming request.
        secret: Shared secret the sender uses to sign.
        tolerance_seconds: Tolerance in seconds for timestamp-replay protection.
            Default 300 (5 min) per Stripe convention. Set to 0 to disable.
        timestamp_key: Override the timestamp parameter name. Default ``"t"``.
        signature_key: Override the signature parameter name. Default ``"v1"``.

    Example::

        from flask import request
        from agentscore.webhooks import verify_webhook_signature

        @app.post("/webhooks/agentscore")
        def handle_webhook():
            result = verify_webhook_signature(
                payload=request.get_data(),  # raw bytes — DO NOT parse JSON first
                signature_header=request.headers.get("X-AgentScore-Signature", ""),
                secret=os.environ["AGENTSCORE_WEBHOOK_SECRET"],
            )
            if not result.valid:
                return {"error": result.reason}, 400
            event = request.get_json(force=True)
            # ... handle event ...
    """
    parts = [p.strip() for p in signature_header.split(",") if p.strip()]
    if not parts:
        return VerifyWebhookSignatureResult(valid=False, reason="no_signatures")

    params: dict[str, list[str]] = {}
    for p in parts:
        if "=" not in p:
            return VerifyWebhookSignatureResult(valid=False, reason="malformed_header")
        key, _, value = p.partition("=")
        params.setdefault(key, []).append(value)

    timestamp_str = params.get(timestamp_key, [None])[0]
    if tolerance_seconds > 0:
        if not timestamp_str:
            return VerifyWebhookSignatureResult(valid=False, reason="no_timestamp")
        try:
            ts = int(timestamp_str)
        except ValueError:
            return VerifyWebhookSignatureResult(valid=False, reason="no_timestamp")
        now_sec = int(time.time())
        if ts < now_sec - tolerance_seconds:
            return VerifyWebhookSignatureResult(valid=False, reason="timestamp_too_old")
        if ts > now_sec + tolerance_seconds:
            return VerifyWebhookSignatureResult(valid=False, reason="timestamp_in_future")

    signatures = params.get(signature_key, [])
    if not signatures:
        return VerifyWebhookSignatureResult(valid=False, reason="no_signatures")

    payload_bytes = payload.encode("utf-8") if isinstance(payload, str) else payload
    signed_payload = f"{timestamp_str}.".encode() + payload_bytes if timestamp_str else payload_bytes

    expected_hex = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    expected_bytes = bytes.fromhex(expected_hex)

    for sig_hex in signatures:
        try:
            actual_bytes = bytes.fromhex(sig_hex)
        except ValueError:
            continue
        if len(actual_bytes) != len(expected_bytes):
            continue
        if hmac.compare_digest(actual_bytes, expected_bytes):
            return VerifyWebhookSignatureResult(valid=True)

    return VerifyWebhookSignatureResult(valid=False, reason="signature_mismatch")


__all__ = ["VerifyWebhookSignatureResult", "verify_webhook_signature"]
