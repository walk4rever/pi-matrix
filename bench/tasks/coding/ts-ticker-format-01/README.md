# ts-ticker-format-01

**Category:** coding · **Oracle:** test (high confidence) · **Difficulty:** low

## Provenance

Adapted from a real production bugfix: an upstream data provider's ticker
resolution occasionally emitted malformed values that flowed into storage
unvalidated. The fix added a pure-function format validator and rejected
non-conforming values at the write boundary.

Resynthesized for this repo: scoped down to the pure-function validator only
(`isValidTickerFormat`), dropping the integration call site, which depended
on a proprietary database schema and import pipeline not relevant to the
task itself. No business-specific data, names, or logic beyond generic
public stock-market ticker formats (US/HK/CN) are included.

## Grading notes

The held-out test file (`oracle/tests/ticker.test.ts`) also re-verifies the
pre-existing `normalizeTicker` function as a regression check — a correct
solution must not touch it. Confirmed the oracle fails against the
unmodified fixture (no `isValidTickerFormat` export exists yet) and passes
against the real historical fix.
