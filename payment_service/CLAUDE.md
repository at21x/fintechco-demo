# payment_service

A small simulated payments validation microservice for a fictional fintech
company. This is a demo/sample project, not a production service — there's
no real web server, database, or external payment processor wired up.

## Layout

- `payment_service/api.py` — request handlers. Models what a Flask/FastAPI
  view function would do (payload in, response dict out) without an actual
  server.
- `payment_service/validation.py` — validates and normalizes incoming
  payment payloads (currency, amount).
- `payment_service/legacy_utils.py` — older helper functions (ids, masking,
  retry). Lightly documented on purpose — this file predates the current
  module layout and is a stand-in for the kind of legacy code real services
  accumulate. Handle with care; don't assume its behavior from the name
  alone.
- `tests/` — pytest test suite.

## Conventions

- **Money is always `Decimal`, never `float`.** Binary floating point can't
  represent most decimal fractions exactly, which is unacceptable for
  monetary amounts. Amounts enter the system as strings/ints and are parsed
  into `Decimal` immediately in `validation.parse_amount`.
- **Minor units are currency-dependent.** Not every currency has 2 decimal
  places of subunit. `validation.CURRENCY_MINOR_UNIT_EXPONENT` records the
  correct exponent per currency (e.g. `JPY`/`KRW` = 0, `KWD`/`BHD`/`OMR` = 3,
  most others = 2). Any code converting a major-unit amount to minor units
  must scale by `10 ** CURRENCY_MINOR_UNIT_EXPONENT[currency]`, not by a
  hardcoded 100 — a hardcoded scale factor silently produces wrong results
  for non-2-decimal currencies.
- **Validation failures raise `ValidationError`**, defined in
  `validation.py`. Handlers in `api.py` catch it at the boundary and turn it
  into an `{"status": "error", ...}` response rather than letting it
  propagate.
- **Currency codes are normalized to uppercase** as early as possible
  (`validate_currency`), so downstream code can assume canonical form.

## Testing

- Tests use `pytest` and live under `tests/`.
- Run with `pytest` from the project root (a root `conftest.py` puts the
  project root on `sys.path` so `import payment_service` works without an
  install step).
- Favor small, direct unit tests over end-to-end ones — there's no real
  server or network boundary to test against here.
