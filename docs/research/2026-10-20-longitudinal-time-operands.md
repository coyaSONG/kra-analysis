# Original time operands across the preserved history

## Finding and next decision

The original time tables support a bounded no-fit longitudinal measurement study,
but **one internally inconsistent historical row must be withheld** from that
study's candidate time measurements. Keep it in the declared population and
preserve its original admission/tier. This is not a change to A24/B34 history,
models, frozen inputs or any existing evaluation.

After withholding that row, **3,179 historical records** have both a checked
final-600 measurement and at least one earlier checked measurement for the same
horse, physical venue and exact distance within 1-180 days. These are dependent
repeated observations, not independent validation trials or future coverage.
The next useful question is whether these measurements show repeatable
within-horse information, before considering any new feature specification.
Do not fit, select or score A24/B34 using this report.

The fixed population is the prior inventory's **11,523 admitted records,
1,156 races, 3,275 horses**, dated May 1 through October 11, 2026. It is not
all raw starters or complete national career history. All rows remain visible:
9,184 `dual_supported` and 2,339 `html_only`, unchanged. The 77 condition-only
groups also remain in the source ledger. No October 16-18 target was loaded.

## What was checked

Replayed the pinned inventory, original receipts/raw HTML, conditions and
horse/rank/roster joins, then parsed each recognized literal table. Used exact
decimal arithmetic, not a learned tolerance, for the previously defined
cumulative endpoint differences and printed segments. Independently checked
that observed cumulative times increase with their known distance positions;
a missing intermediate value cannot hide reversal between observed positions.

Seoul checks use the known 200m, distance-minus-600m, distance-minus-200m and
finish positions. Corner distances are not invented. Busan checks use the
literal distance-labelled columns for the six previously supported distances.
Jeju has no admitted independent counterpart for these pace definitions.
The guide-pinned 1300m initial-100m exception is retained.

There are **124,848 inspected cells**: 102,869 positive and 21,979 blank.
No malformed or numeric-zero cell occurred in the recognized selected rows.
Blank includes inapplicable layout positions; it is not all missing data.
Unknown-layout rows are retained, not counted as successfully inspected cells.

The segment equations yielded **28,848 exact**, **4,289 unsupported-endpoint**
and **one missing-operand** checks. These equation counts are separate from
the newly detected cumulative-order conflict. Exact local equations do not
guarantee an internally consistent whole record.

| Measurement status | Total | Initial 200m | Final 600m |
| --- | ---: | ---: | ---: |
| Positive total / exact labelled endpoint | 11,093 | 2,957 | 7,694 |
| Seoul label only, no independent initial counterpart | 0 | 4,737 | 0 |
| Jeju pace definition unverified | 0 | 3,399 | 3,399 |
| Unrecognized Busan distance layout | 184 | 184 | 184 |
| Unsupported physical venue, Yeongcheon | 245 | 245 | 245 |
| Withheld because of internal conflict | 1 | 1 | 1 |
| Full declared historical population | **11,523** | **11,523** | **11,523** |

`positive_total` means a positive parsed total with no detected row conflict.
It is not a fresh independent API check: the detail parser reads total time
from these same HTML tables. `exact_endpoint` means the corresponding printed
segment equals the checked cumulative difference, with row consistency checks.
Seoul's initial value remains label-only even though it is positive and ordered.
The source's existing dual/HTML-only tiers are inherited, never upgraded.

Structural rows with a qualifying current and prior measurement are **5,122
total**, **1,227 initial-200**, and **3,179 final-600**. Initial-200 pair counts
exclude Seoul's label-only values; this is a measurement-status distinction,
not an evaluation subset. The JSON retains all 30 venue/distance groups and
six calendar-month groups, including their full denominators and failure states.

## One source anomaly

**High analytical risk for time-feature use; confirmed internal inconsistency,
unknown cause.** Race `20260703_3_6`, horse `51248`, 1800m, original rank 10,
source tier `html_only`:

| Literal checkpoint | Printed cumulative time |
| --- | --- |
| 600m | 0:39.2 |
| 1000m | **1:34.0** |
| 1200m | **1:16.8** |
| 1400m | 1:30.6 |
| 1600m | 1:44.2 |
| Finish | 1:58.3 |

The 1000m clock is 17.2 seconds later than the 1200m clock. The printed
4-2F segment is blank, so the old endpoint equation reports missing instead
of exposing this reversal. Six other local equations still match exactly.
Do not infer a typo, repair 1:34.0 into another number, or use apparently
unaffected segments to bypass the row-level withholding policy.

This affects **1/11,523 records (about 0.0087%)**, in July/Busan1800m.
Small prevalence does not make it safe for a repeatedly reused horse history.
All original 11 rows of the race remain admitted; the new measurement report
withholds only the affected row's candidate durations. Revisit that decision
only with explicit source evidence, not target performance.

Original [official source](https://race.kra.co.kr/raceScore/ScoretableDetailList.do?Act=04&Sub=1&meet=3&realRcDate=20260703&realRcNo=6),
locally captured **2026-10-12T15:18:24.536006Z**:

- Raw HTML SHA256: `bb848042c1fcee57c474a31f18f6298384006bbcaaf98b71174b62ff1acf99c6`
- Receipt SHA256: `4f1764b4953351c625ccedb477057fa6849a9759af26c1d56b7b1f3c9b6f098d`
- Preserved directory: `.cache/autoresearch/official-june-catalog-20261013/details`

No official correction was fetched or assumed. This is a correction to our
audit's detection scope, not an upstream corrected result.

## Version evidence and reproducibility

The final [report](experiments/2026-10-20-longitudinal-time/report.json) was
created at **2026-10-20T19:00:36.981995Z**, SHA256:
`2ff4ef525c33a6f83e5aa2ecc9f14c9d5942f103386b34d2e4007f4fda1e6f7a`.
It includes the implementation hashes, pinned predecessor report, source
receipts/clocks/hashes, every selected identity, raw time columns, measurement
statuses, arithmetic exceptions and complete monthly/venue-distance summaries.

The initial local equation-only run is preserved separately at
`.cache/autoresearch/longitudinal-time-operands/report-v1.json`, SHA256
`dd1b1f73bc7b73f71b32ca58c411e3cf5e7617f3ae8bfcd79ad0c2ef8184c2cf`.
It had no row issues and one more usable measurement in each category.
Adding the cumulative-order check changed one row to withheld and decreased
each paired-current/prior support count by one. Sources, population and original
tiers did not change. That initial result is superseded, not erased.

The monotonic-check version v2 has SHA256
`971b9bacde5ebd968dc7a2827718eb3b03023ea77d0a1168e4f386f6d4241652`.
The published v3 repeats the complete audit after an explicit `zip(strict=False)`
lint fix. Its research values equal v2 exactly; only creation time and code hash
differ. All three local versions remain preserved.

From the isolated checkout:

    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m autoresearch.longitudinal_time_audit
    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m pytest -q -p no:cacheprovider packages/scripts/autoresearch/tests/test_longitudinal_time_audit.py

An independent local companion,
`.cache/autoresearch/longitudinal-time-operands/independent_check.py`, imports
neither the new audit nor its arithmetic helpers. Separate Decimal calculations
on all exported raw cells reproduced the equation counts and sole reversal;
SQLite temporal self-joins reproduced the three pair counts. This independently
checks the calculations, not a second extraction of the official HTML.
The original extraction is separately pinned and replayed by the auditor.

Local validation passed **312 related tests**, including 37 new cases, and Ruff
lint/format checks. The published report's hash, full denominator, one anomaly
and correspondence to the executed implementation hash are regression-tested.
Required CI and normal merge evidence are recorded in the PR receipt.

## Limits and research status

Confirmed: original identity/source replay; literal positive/blank operands;
defined endpoint arithmetic; the one reversed clock; unchanged full membership.

Partial: measurements are supported only for the recognized layouts and stated
endpoints. Busan1000/2000m (184 rows) and Yeongcheon (245) remain unsupported;
Jeju pace semantics and Seoul independent initial counterpart remain unresolved.

Unknown: repeatability, incremental prediction value, historical pre-race
availability and future target coverage. October source capture cannot be
backdated to before these historical races. The guide's October20 collection
is also not independent proof of historical publication. Any subsequent
historical stability analysis is descriptive, not walk-forward validation.

The 70% single-unordered-triple objective remains unmet. No fit, scoring,
source network request, enrollment, model promotion or frozen prediction change
occurred. Future dates, roster and N remain unset.
