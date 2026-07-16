from decimal import Decimal

import pytest

from payment_service.validation import (
    CURRENCY_MINOR_UNIT_EXPONENT,
    ValidationError,
    parse_amount,
    to_minor_units,
    validate_currency,
    validate_payment,
)


def test_validate_payment_accepts_valid_usd_payload():
    result = validate_payment({"currency": "usd", "amount": "19.99"})

    assert result["currency"] == "USD"
    assert result["amount"] == Decimal("19.99")
    assert result["amount_minor_units"] == 1999


def test_validate_payment_missing_currency_raises():
    with pytest.raises(ValidationError):
        validate_payment({"amount": "10.00"})


def test_validate_payment_missing_amount_raises():
    with pytest.raises(ValidationError):
        validate_payment({"currency": "USD"})


def test_validate_currency_rejects_unsupported_code():
    with pytest.raises(ValidationError):
        validate_currency("XYZ")


def test_parse_amount_rejects_negative_amount():
    with pytest.raises(ValidationError):
        parse_amount("-5.00")


def test_parse_amount_rejects_non_numeric_input():
    with pytest.raises(ValidationError):
        parse_amount("not-a-number")


def test_parse_amount_rejects_amount_over_max():
    with pytest.raises(ValidationError):
        parse_amount("1000000.01")


def test_to_minor_units_converts_dollars_to_cents():
    assert to_minor_units(Decimal("5.00"), "USD") == 500


@pytest.mark.parametrize(
    "currency, amount, expected_minor_units",
    [
        ("JPY", Decimal("500000"), 500000),      # 0-decimal currency: no scaling
        ("USD", Decimal("19.99"), 1999),          # 2-decimal currency: x100
        ("BHD", Decimal("1250.000"), 1250000),    # 3-decimal currency: x1000
    ],
)
def test_to_minor_units_scales_by_currency_exponent(currency, amount, expected_minor_units):
    """Regression test for PAY-4471: to_minor_units must scale per-currency,
    not by a hardcoded factor. JPY and BHD were the two currencies whose
    minor-unit exponent (0 and 3, respectively) differs from the common
    2-decimal case, which is exactly what the hardcoded *100 bug missed.
    """
    assert to_minor_units(amount, currency) == expected_minor_units


@pytest.mark.parametrize("currency", sorted(CURRENCY_MINOR_UNIT_EXPONENT))
def test_to_minor_units_matches_exponent_table_for_every_supported_currency(currency):
    """Full-table regression test: derive the expected scale from
    CURRENCY_MINOR_UNIT_EXPONENT independently of to_minor_units's own
    implementation, so adding a new currency to the table without wiring it
    through correctly would be caught here rather than in production.
    """
    exponent = CURRENCY_MINOR_UNIT_EXPONENT[currency]
    amount = Decimal("7")
    expected = int(amount * (10 ** exponent))

    assert to_minor_units(amount, currency) == expected


def test_validate_payment_computes_correct_minor_units_for_zero_decimal_currency():
    """Integration-level check through the full validate_payment path for a
    0-decimal currency (JPY) -- this is the level at which PAY-4471 actually
    surfaced, since the bug only became visible once a downstream service
    consumed amount_minor_units.
    """
    result = validate_payment({"currency": "JPY", "amount": "500000"})

    assert result["amount_minor_units"] == 500000


def test_validate_payment_computes_correct_minor_units_for_three_decimal_currency():
    """Integration-level check through the full validate_payment path for a
    3-decimal currency (BHD).
    """
    result = validate_payment({"currency": "BHD", "amount": "1250.000"})

    assert result["amount_minor_units"] == 1250000
