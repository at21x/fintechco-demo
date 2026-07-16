"""Request handlers for incoming payment requests.

This models the shape of what a Flask/FastAPI view function would do --
take a parsed JSON payload in, return a JSON-serializable response dict out
-- without actually running a web server, so the demo stays dependency-free.
"""

from __future__ import annotations

from typing import Any

from . import legacy_utils
from .validation import ValidationError, validate_payment


def handle_payment_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Entry point for a single incoming payment request."""
    request_id = legacy_utils.generate_request_id()

    try:
        validated = validate_payment(payload)
    except ValidationError as exc:
        return {
            "status": "error",
            "request_id": request_id,
            "error": str(exc),
        }

    transaction_id = legacy_utils.generate_transaction_id(validated["currency"])

    return {
        "status": "ok",
        "request_id": request_id,
        "transaction_id": transaction_id,
        "currency": validated["currency"],
        "amount": str(validated["amount"]),
        "amount_minor_units": validated["amount_minor_units"],
        "masked_account": legacy_utils.mask_account_number(payload.get("account_number", "")),
    }


def handle_batch(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Process a batch of payment requests sequentially, in order."""
    return [handle_payment_request(payload) for payload in payloads]
