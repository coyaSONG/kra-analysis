# Longer-history readiness for a time-information study

## Decision

The preserved longer history **does contain repeated horses**. It has 11,523
admitted historical records for 3,275 horses across 1,156 races, from May 1 to
October 11, 2026. Of those records, **5,173 have at least one earlier start**
for the same horse at the same physical venue and exact distance within the
fixed 1-180-day rule. This removes the short-May archive's structural obstacle,
but does not establish stable time features, pre-race training eligibility or
predictive improvement.

The next bounded no-fit study can examine the existing original time evidence
for Seoul and the already-recognized Busan layouts, keeping the entire declared
historical corpus visible with explicit withheld reasons. There are **3,180
records with an exact prior and recognizable tables on both sides** in those
two venues: 1,952 Seoul and 1,228 Busan. This is diagnostic source readiness,
not a selected evaluation population or 3,180 independent validation examples.
Do not apply this scope as an exclusion rule for future races.

Before deriving quantities beyond the previously checked May archive, replay
the actual endpoint arithmetic and inspect the underlying time operands again.
The current inventory checks literal table structure, not sectional semantics,
API-to-HTML time correspondence or repeated-horse stability.

## Declared Population

This is the complete **existing admitted historical corpus**, not all raw
observed starters and not complete national career history. Its membership is
unchanged: 8,994 baseline + 1,528 later-May + 1,001 early-May records. Existing
quarantined/unresolved starts have not been re-admitted. Source tiers remain
9,184 `dual_supported` and 2,339 `html_only`.

There are 563 horses with one record and **2,712 with multiple records**; the
maximum is 12. These are repeated observations, not independent samples.
Every one of the 11,523 identities contributes to the report's per-race ledger,
which preserves counts, tier counts, exact-prior histograms and an identity/rank
digest linked to the original pinned history.

| Physical venue | Historical records | Any earlier start | Same venue/distance prior | At least three exact priors | Recognized tables on both sides |
| --- | ---: | ---: | ---: | ---: | ---: |
| Seoul | 4,737 | 3,293 | 1,952 | 249 | 1,952 |
| Jeju | 3,399 | 2,571 | 1,943 | 601 | 1,943 |
| Busan | 3,142 | 2,142 | 1,264 | 202 | 1,228 |
| Yeongcheon | 245 | 242 | 14 | 0 | 0 |
| Total | **11,523** | **8,248** | **5,173** | **1,052** | **5,123** |

The “any earlier start” column does not impose venue/distance equality. Exact
priors require horse identity, physical venue and nominal distance equality;
class is retained but is **not** an additional hidden filter. Same-day and
future records are excluded, day 180 is included and day 181 excluded.
No alternative lookback, minimum-support threshold or favorable class subset
was searched. These rules do not change A24/B34's existing approved policy.

All 30 observed venue/distance groups are available in the JSON. Group counts
are diagnostic and never replace the full future race-level accuracy metric.

## Original-Source Checks

The condition registry contains 1,233 event groups: 1,158 observed and 75
unknown. All original receipts were hash-checked and conditions replayed from
their pinned bytes. The 1,156 selected historical races all have observed
conditions. The other 77 groups remain in the inventory: 75 unknown groups and
two observed groups with no admitted history. They are not silently deleted or
converted to no-race declarations.

For every selected race, the original HTML's dated event identity, full roster
size and every selected horse/rank join agree with the pinned history. The
existing source-tier distinction is preserved; this audit does **not** newly
replay the API raw pages or upgrade HTML-only history to dual support.

| Timing-table classification | Selected races | Selected historical records |
| --- | ---: | ---: |
| Recognized literal layout | 1,113 | 11,094 |
| Unrecognized Busan distance layout | 19 | 184 |
| Unsupported physical venue: Yeongcheon | 24 | 245 |
| Total | **1,156** | **11,523** |

The Busan gaps are **17 races at 1000m and two at 2000m**. The earlier May
mapper did not admit these distances; this inventory does not infer their
positions from column order or a different distance.

Jeju's 1,943 recognizable-layout pairs remain **semantically unverified for the
proposed pace ratios**. Recognizing their labels does not provide an independent
cumulative counterpart. Yeongcheon remains a distinct physical venue, not Busan
under another name. Neither group is discarded from the declared corpus.

Recognizable tables can still contain missing or invalid times. The table
classification is not a count of valid derived pace rows. Only a subsequent
operand/arithmetic audit can establish that narrower measurement claim.

## Availability and Leakage Limits

Original official receipt clocks range from **2026-10-11T18:05:33.164581Z** to
**2026-10-15T12:32:04.466206Z**, before the preserved original source bound of
2026-10-16T01:20:00Z. These are local collection clocks, not independent
attestations of upstream publication. Sources captured in October cannot be
treated as having existed before their own May-October historical races.

The repeated-start counts are structural. They deliberately do not claim
point-in-time feature availability for each historical target. No train/test
split, future target roster, target outcome comparison or model fitting was
performed. The old artifact's unrelated target/coverage/projection fields are
not used; only `records`, `extension_history` and the corresponding historical
condition fields enter this inventory.

The exact-single-triple 70% objective remains unchanged and unmet. Old M0/API27
commitments and A24/B34 models/fit budgets are untouched. Future dates, roster
and N remain unset; future feature coverage is unknown.

## Evidence and Reproduction

The immutable [report](experiments/2026-10-20-longitudinal-readiness/report.json)
was produced at **2026-10-20T18:34:18.996274Z**, SHA256:
`a338c67f005c1ff56d3ab418f44073d7d76de0a2e3b879d7172a2a8f430e9701`.

Its four source pins are:

| Local artifact | SHA256 |
| --- | --- |
| `condition-form-research-20261013/run-1/history.json` | `f718152b1465bea5990145ed30afb2402eaaba9ce2640a89163841e6211e5125` |
| `condition-form-research-20261013/run-1/conditions.json` | `818f0be674ef148b9c83e46192a52686be1e5ba2805b5daf8c601134aaaa6123` |
| `history-gap-expansion-20261014/report-v2.json` | `3302c5bb1abb62f70565535751991c01896b9b437e4160168ea3700fbbc09866` |
| `observed-history-extension-20260501-14/audit-report.json` | `0ff580a8e1ff3123f2f18ffb226ceb7ebf6c759f071697fbde0e9ad67bbb85e3` |

Paths above are relative to `.cache/autoresearch`. The report retains every
original official source URL, receipt/raw hash, clock, condition/layout status,
selected count and complete per-race support ledger.

From the isolated repository root:

    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m autoresearch.longitudinal_history_inventory
    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m pytest -q -p no:cacheprovider packages/scripts/autoresearch/tests/test_longitudinal_history_inventory.py

The audit prints JSON and has no write, collection, fitting or prediction path.
Missing/changed source bytes, changed conditions or identity/rank/roster joins
stop it. Unrecognized layouts remain explicit statuses.

A separate local companion,
`.cache/autoresearch/longitudinal-readiness/independent_check.py`, imports no
new inventory code. It verifies the input/report pins and uses an in-memory
SQLite temporal self-join to independently reconstruct all five support counts
for **all 1,156 race ledgers**, including 5,173 exact-prior records and 1,052
with three or more priors. Its layout-pair arithmetic consumes the already
inspected classification; it is not a second independent layout parser.

Local verification passed **275 related regression tests**, including 36 new
inventory cases, plus Ruff lint and format checks. Required CI and normal merge
evidence belong to the PR receipt. No dependency change is part of this work.

## Research Status

Confirmed: repeated identities exist; the declared history, condition registry
and selected original HTML roster/rank joins reproduce; known layout counts
and temporal support counts are independently checked.

Partial: original tables are present, but broad time-operand and endpoint
validation outside the earlier May study remains to be done.

Unknown: longitudinal stability, incremental prediction value, independent
historical pre-race availability, and future target coverage.

This historical inventory made no source requests, retraining, live inference,
evaluation registration or automatic promotion. Continue the measurement study without treating
structural coverage as success or repeatedly tuning the October 50 races.
