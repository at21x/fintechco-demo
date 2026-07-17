from decimal import Decimal

import pytest

from payment_service.validation import (
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


def test_to_minor_units_zero_decimal_currency():
    assert to_minor_units(Decimal("500000"), "JPY") == 500000


def test_to_minor_units_three_decimal_currency():
    assert to_minor_units(Decimal("1250.000"), "BHD") == 1250000


def test_to_minor_units_regression_pay_4471():
    # Incident PAY-4471: hardcoded *100 inflated JPY 100x and understated BHD 10x
    assert to_minor_units(Decimal("500000"), "JPY") == 500000
    assert to_minor_units(Decimal("1250.000"), "BHD") == 1250000
