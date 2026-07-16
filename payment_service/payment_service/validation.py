"""Validation rules for incoming payment payloads.

All monetary amounts are handled as `Decimal`, never `float`, to avoid binary
floating-point rounding error on money. See CLAUDE.md for the full
money-handling convention, including how minor units (e.g. cents) are meant
to be derived per currency.
"""

from decimal import Decimal, InvalidOperation

# Number of minor-unit decimal places per currency. Most currencies use 2
# (dollars/cents), but not all of them do -- zero-decimal currencies like JPY
# have no subunit, and a few (KWD, BHD, OMR) use 3.
CURRENCY_MINOR_UNIT_EXPONENT = {
    "USD": 2,
    "EUR": 2,
    "GBP": 2,
    "CAD": 2,
    "AUD": 2,
    "JPY": 0,
    "KRW": 0,
    "BHD": 3,
    "KWD": 3,
    "OMR": 3,
}

SUPPORTED_CURRENCIES = set(CURRENCY_MINOR_UNIT_EXPONENT)

MAX_PAYMENT_AMOUNT = Decimal("1000000")  # single-transaction ceiling


class ValidationError(Exception):
    """Raised when a payment request fails validation."""


def validate_currency(currency: str) -> str:
    """Check that `currency` is a supported ISO 4217 code, and normalize it."""
    if not currency or not isinstance(currency, str):
        raise ValidationError("currency is required")

    currency = currency.upper()
    if currency not in SUPPORTED_CURRENCIES:
        raise ValidationError(f"unsupported currency: {currency}")
    return currency


def parse_amount(raw_amount) -> Decimal:
    """Parse a raw amount (str/int/float) into a Decimal, rejecting garbage input."""
    try:
        amount = Decimal(str(raw_amount))
    except (InvalidOperation, TypeError):
        raise ValidationError(f"invalid amount: {raw_amount!r}")

    if amount <= 0:
        raise ValidationError("amount must be positive")
    if amount > MAX_PAYMENT_AMOUNT:
        raise ValidationError("amount exceeds maximum allowed payment")
    return amount


def to_minor_units(amount: Decimal, currency: str) -> int:
    """Convert a major-unit decimal amount (e.g. dollars) into its integer
    minor-unit representation (e.g. cents) for the given currency.
    """
    exponent = CURRENCY_MINOR_UNIT_EXPONENT[currency]
    return int(amount * (10 ** exponent))


def validate_payment(payload: dict) -> dict:
    """Validate an incoming payment payload and return a normalized version.

    Raises ValidationError on any problem. On success, returns a dict with
    normalized `currency`, `amount` (Decimal), and `amount_minor_units` (int).
    """
    if "currency" not in payload:
        raise ValidationError("missing required field: currency")
    if "amount" not in payload:
        raise ValidationError("missing required field: amount")

    currency = validate_currency(payload["currency"])
    amount = parse_amount(payload["amount"])
    minor_units = to_minor_units(amount, currency)

    return {
        "currency": currency,
        "amount": amount,
        "amount_minor_units": minor_units,
    }
