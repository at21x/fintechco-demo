# Postmortem: PAY-4471 — Currency-Scaling Bug in `to_minor_units()`

**Status:** Resolved | **Severity:** SEV-2 | **Date:** 2026-07-15/16

## Summary
Between 23:44 UTC on 2026-07-15 and 00:08 UTC on 2026-07-16, `payment_service`
mis-scaled amounts for any currency without a 2-decimal minor unit. JPY
payments were inflated 100x and falsely rejected as fraud; BHD payments were
understated 10x and failed settlement reconciliation. Payment-service error
rate peaked at **33.1%**, PagerDuty auto-opened an incident at 23:52 UTC, and
on-call mitigated by 00:06 UTC. No funds were lost — all affected payments
were rejected or held, not mis-settled.

## Root Cause
`to_minor_units()` in `validation.py` hardcoded `amount * 100`, ignoring the
`currency` parameter entirely. This assumed every currency uses 2 decimal
places, which is wrong for JPY (0 decimals) and BHD (3 decimals). The
correct convention — `10 ** CURRENCY_MINOR_UNIT_EXPONENT[currency]` — was
already documented in `payment_service/CLAUDE.md` but not implemented.
Downstream consumers (`fraud_engine`, `ledger_reconciliation`) compared the
bad values against independently-computed figures, which is where the
corruption surfaced as errors.

## Resolution
- **Last night (mitigation):** Feature-flagged `disable_auto_processing` for
  JPY and BHD, routing those payments to manual review. Error rate returned
  to baseline (~1%) within 5 minutes.
- **Today (permanent fix):** `to_minor_units()` now scales by
  `10 ** CURRENCY_MINOR_UNIT_EXPONENT[currency]` instead of a hardcoded x100.
- **Test coverage added:** parametrized JPY/USD/BHD unit tests, a full-table
  test covering every currency in `CURRENCY_MINOR_UNIT_EXPONENT`
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
| 00:01 | Failures isolated to JPY/BHD; scaling bug suspected |
| 00:04 | Root cause confirmed: hardcoded x100 in `to_minor_units()` |
| 00:05 | Mitigation: manual-review flag enabled for JPY/BHD |
| 00:08 | Incident marked mitigated, error rate <5% |
| 00:11 | Error rate back to baseline (~1%) |
| Next day, 18:07 | Permanent fix + regression tests merged |

## Follow-ups
- [ ] Disable `disable_auto_processing` flag for JPY/BHD now that the fix is
  live, and confirm normal auto-processing resumes cleanly.
- [ ] Audit other currency-sensitive code paths (e.g. `legacy_utils.py`) for
  similar assumptions about 2-decimal currencies.
- [ ] Consider a lint/CI check that flags any raw `* 100` near currency
  conversion code.
