"""Grab-bag of older helper functions used across the payments codebase.

These predate the current module layout and haven't been cleaned up. Treat
this file as "handle with care" -- behavior is relied on elsewhere even
though the documentation here is thin. New code should generally live in a
proper module, not here.
"""

import itertools
import re
import time

_request_counter = itertools.count(1)


def generate_request_id() -> str:
    """Monotonic per-process request id, prefixed with the current timestamp."""
    return f"req_{int(time.time())}_{next(_request_counter)}"


def generate_transaction_id(currency: str) -> str:
    """Transaction id for a payment. Currency prefix helps with grepping logs."""
    return f"txn_{currency.lower()}_{int(time.time() * 1000)}"


def mask_account_number(account_number: str) -> str:
    """Mask all but the last 4 digits of an account number for display/logs."""
    digits = re.sub(r"\D", "", account_number or "")
    if len(digits) <= 4:
        return "*" * len(digits)
    return "*" * (len(digits) - 4) + digits[-4:]


def retry(fn, attempts: int = 3, delay: float = 0.0):
    """Call fn(), retrying on exception up to `attempts` times total.

    No backoff strategy here on purpose -- this was written before we had a
    real retry policy library. Prefer a proper retry decorator for new code.
    """
    last_exc = None
    for _ in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - intentionally broad, legacy code
            last_exc = exc
            if delay:
                time.sleep(delay)
    raise last_exc
