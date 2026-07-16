# Postmortem: PAY-4471 — Currency-Scaling Bug in `to_minor_units()`

**Status:** Resolved | **Severity:** SEV-2 | **Date:** 2026-07-15/16

## Summary
`payment_service` mis-converted payment amounts into minor units (cents,
fils, etc.) for any currency that doesn't use 2 decimal places. JPY payments
were inflated 100x and auto-rejected by the fraud engine; BHD payments were
understated 10x and failed settlement reconciliation. Error rate rose from a
~0.5% baseline to a peak of **33.1%** over ~20 minutes, paged on-call
automatically, and was mitigated within 16 minutes of the page. No funds
were lost — every affected payment was rejected or held, never mis-settled.

## Root Cause
`to_minor_units()` in `validation.py` hardcoded `amount * 100`, ignoring the
`currency` argument entirely. That's correct only for 2-decimal currencies
(USD, EUR, GBP, ...). JPY has 0 minor-unit decimals and BHD has 3, so the
hardcoded factor produced amounts 100x too large (JPY) or 10x too small
(BHD). The correct scale, `10 ** CURRENCY_MINOR_UNIT_EXPONENT[currency]`, was
already documented in `payment_service/CLAUDE.md` but never implemented.
`payment_service` itself returned normally in every case — the bad value
only surfaced once downstream services (`fraud_engine`, a per-currency
threshold check; `ledger_reconciliation`, a merchant-settlement comparison)
compared it against an independently-computed figure.

## Resolution
- **Mitigation (00:05 UTC):** Feature-flagged `disable_auto_processing` for
  JPY and BHD, routing those payments to manual review. Error rate returned
  to baseline (~1%) within ~6 minutes.
- **Permanent fix (next day):** `to_minor_units()` now scales by
  `10 ** CURRENCY_MINOR_UNIT_EXPONENT[currency]` instead of a hardcoded x100
  (commit `7d25954`).
- **Test coverage added:** parametrized JPY/USD/BHD regression tests, a
  full-table test covering every currency in `CURRENCY_MINOR_UNIT_EXPONENT`
  independent of the implementation, and integration tests through
  `validate_payment()` for 0- and 3-decimal currencies — the level at which
  the bug actually surfaced in production.

## Timeline (UTC, 2026-07-15/16)
| Time | Event |
|---|---|
| 23:44 | First JPY payment falsely rejected by fraud engine |
| 23:46 | First BHD settlement mismatch in ledger reconciliation |
| 23:52 | Error rate crosses 15%; PagerDuty auto-opens incident, on-call paged |
| 23:58 | On-call begins triage |
| 00:01 | Peak error rate (33.1%); failures isolated to JPY/BHD |
| 00:04 | Root cause confirmed: hardcoded x100 in `to_minor_units()` |
| 00:05 | Mitigation: manual-review flag enabled for JPY/BHD |
| 00:08 | Incident marked mitigated, error rate <5% |
| 00:11 | Error rate back to baseline (~1%) |
| Next day | Permanent fix + regression tests merged (`7d25954`) |

## Follow-ups
- [ ] Disable `disable_auto_processing` for JPY/BHD now that the fix is
  live; confirm normal auto-processing resumes cleanly.
- [ ] Audit other currency-sensitive code paths (e.g. `legacy_utils.py`) for
  similar 2-decimal assumptions.
- [ ] Add a lint/CI check flagging raw `* 100` near currency-conversion code.
- [ ] `legacy_utils.retry()` masked some of these failures as retriable
  (3 silent attempts before re-raising) — evaluate whether validation
  errors should be retried at all.
