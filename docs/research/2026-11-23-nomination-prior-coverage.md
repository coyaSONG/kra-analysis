# Prior history coverage of observed nominations

Initial nomination coverage SHA256: `933e06e38ba95ac308c2c7f53cf021ebe999ef90d5e0b1b0591c9438c9781444`.

Additional prior archive comparison SHA256: `6fe95862d7dfbe1a0817cb8108a56b0e69c3f86c6fb56b4ab6217ebb5792c879`.

This is a coverage audit, not a training matrix, a future race card,
or an estimate of exact-trio accuracy. Retain all 33 earlier
[nomination keys](2026-11-23-preliminary-nomination-witness.md) and
the separate [Jeju weekly-only key](2026-11-23-jeju-weekly-nominations.md).
Only five of the 34 have bound identity-bearing details, including
the [Jeju OPEN detail](2026-11-23-jeju-nomination-identity.md). The 29
others stay unknown; they contribute neither a zero nor an assumed
nomination count. The identified scope comprises 84 nominations.

## Prior sources

- [PR #81](https://github.com/coyaSONG/kra-analysis/pull/81): replay
  the literal dated official result HTML. Its reference grade, distance,
  rank and elapsed fields are not described as result API confirmations.
- [PR #108](https://github.com/coyaSONG/kra-analysis/pull/108): replay the
  separately published official and API result inventory. Preserve its
  roster and ranked-row restrictions; do not reinterpret unranked rows.
- [PR #156](https://github.com/coyaSONG/kra-analysis/pull/156): verify the
  earlier 51-race official report packet and its raw source pins.
  All 540 canonical original IDs are disjoint from the 84 nominations.
  This is zero overlap in these exact sources, not no racing or a
  missing-result failure. The original two race-marker holds remain.
- [PR #146](https://github.com/coyaSONG/kra-analysis/pull/146): in a
  separate version, replay all 135 fields from October 23 to November
  15 and compare to the original published packet. It contributes
  52 observed nonduplicate prior rows across 31 fields for the
  identified horses. One roster-conflict hold remains; KRA report
  and HTML views are not the missing API reconciliation.

Keep stable horse ID, physical race ID, original observation clock,
independent publication clock and result role separate. The known
nomination publication at 2026-11-22 18:28:05 UTC is an audit anchor,
not the first cutoff. The existing 90 prior Korean calendar days, same
physical venue, literal grade and within-200-m definitions are frozen.
Two exact-distance runs on one day do not count as two prior days.

## Diagnostic coverage

Each cell is the reference count followed by the hypothetical count
if the separately held earlier archive were eligible. Neither is the
number of confirmed final starters or of independently trained cases.

| Preliminary field | Known rows | Same grade/venue, within 200 m | Exact distance as well | Exact on two days |
| --- | ---: | ---: | ---: | ---: |
| Jeju Nov 27 race 3 | 14 | 6 to 10 | 5 to 8 | 2 to 5 |
| Busan Nov 27 race 7 | 14 | 5 to 6 | 2 to 2 | 0 to 1 |
| Jeju Nov 28 race 5 | 12 | 6 to 6 | 6 to 6 | 0 to 0 |
| Seoul Nov 29 race 5 | 14 | 6 to 8 | 2 to 7 | 0 to 2 |
| Yeongcheon Nov 29 race 1 | 30 | 12 to 17 | 5 to 5 | 0 to 0 |
| Identified rows only | 84 | 35 to 47 | 20 to 28 | 2 to 8 |

Any observed numerical prior in these archives rises from 61 to 70.
The 11/20-22 archive contributes no overlap. The separate older
archive adds zero exact coverage to the OPEN Jeju field; the six
identified prior links there stand independently of it.

As a source acquisition priority only, October 24 Seoul has the
largest single date/venue gain in first exact support (3 identified
rows). October 25 Yeongcheon adds the most first within-200-m
support (3) without adding exact-distance support. Different dates'
individual potential gains overlap and are not additive. Reassess
against the final card before requesting anything, confirm the result
API entitlement and existing receipts, and preserve both source
versions. This does not admit an older input or license a retry.
The unchanged whole-card M0/API27 contract has priority.

Both private ledgers retain the original keys, distinct typed source
roles, clocks, raw references and per-ID comparisons. Independently
recounting the sealed ledger reproduced all totals and the 29 unknown
fields. Ruff and 130 related local tests passed. No KRA or data API
request, real model fit, forecast, training approval or accuracy
calculation was performed.
