# Diagnose historical time repeatability without fitting

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

Test whether the verified last-600m measurement contains a repeatable historical
signal rather than merely readable data. Keep all 11,523 admitted records and
use no October16-18 outcomes, saved-model scoring or training. This descriptive
study cannot establish incremental predictive value or 70% exact-triple success.

## Progress

- [x] Confirmed PR130 merge and clean isolated worktree; read predecessor audits.
- [x] Fixed analysis rules before computing any correlations in this study.
- [x] Implement and test quantities, nearest-prior selection and diagnostics.
- [x] Execute once, independently verify, and interpret limitations.
- [ ] Pass required checks and normally merge the bounded change.

## Decision Log

Use exactly one historical match per current record: same horse, physical venue
and exact distance, 1-180 days earlier, latest date first. Select before checking
measurements; never fall back from an unavailable nearest record. If multiple
records share the latest date, leave the prior ambiguous. Do not filter by class,
confidence or favorable coverage.

The raw final-speed ratio is 600*T/(D*L), where T is total seconds, D distance
and L checked final600 seconds. Subtract the median raw ratio of all admitted
members of that same race, including the focal row, to remove a shared race
level. Require at least three members and a valid quantity for every admitted
member; one withheld member withholds the entire race reference. This median is
descriptive contemporaneous race normalization, never a future pre-race input.
Rank fraction is (rank-1)/(observed_roster_size-1), smaller means better.

On the same complete pairs report three fixed Spearman correlations: prior pace
vs current pace, prior rank vs current rank, prior pace vs current rank. Use
average ranks for ties and standard-library Pearson correlation of those ranks.
Do not select a direction, cutoff, metric, lookback or model after results.
These are associations, not a test of conditional added predictive value.

Resample whole horse clusters 1,000 times with seed20261020 for descriptive
95% percentile intervals (inclusive linear interpolation). Undefined draws are
counted; any undefined draw withholds that interval. Shared race/weather and
calendar dependence remain unmodelled, so these are not calibrated inferential
or future-performance intervals. Report all venue/distance groups and all six
leave-one-current-month-out results; never pick the favorable one.

## Context and Orientation

The immutable source is
`docs/research/experiments/2026-10-20-longitudinal-time/report.json`, SHA256
`2ff4ef525c33a6f83e5aa2ecc9f14c9d5942f103386b34d2e4007f4fda1e6f7a`.
It contains original-source pins, raw cells, measurement statuses and all11,523
selected records. It withholds horse51248 at20260703_3_6 for cumulative reversal.
Do not repair that row or re-admit unrecognized layouts. The corpus is not all
raw starters or complete national history. Historical source collection and
semantic-guide clocks are later than these races; never claim historical PIT
(point-in-time, available before each target) validation from these snapshots.

## Plan of Work

Add `packages/scripts/autoresearch/time_repeatability.py` with quantity/reference
construction, nearest-prior pairing, descriptive statistics and a pinned reader.
Write a full per-record ledger, reference membership and exact rational values.
The first milestone passes synthetic tests including nearest missing/no fallback,
ties, 180-day boundaries and invalid race references. The second executes the
fixed analysis and uses independent calculations on the input to cross-check
membership, values and associations. The final milestone publishes the result
and adds the tests to the existing historical audit CI step.

## Concrete Steps

From `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`:

    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m pytest -q -p no:cacheprovider packages/scripts/autoresearch/tests/test_time_repeatability.py
    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m autoresearch.time_repeatability

The CLI prints JSON only. Preserve output with exclusive creation and never
overwrite the input report or any published version.

## Validation and Acceptance

All11,523 rows must have independent current-measurement, prior-selection and
pair statuses. Their counts must sum to the fixed full population. Constant
variables and fewer than three complete pairs yield undefined correlations,
not zero. Tied values receive average ranks. Tests must cover shuffle invariance,
duplicate identities, future/same-day exclusion, 180/181 boundaries, wrong
venue/distance/horse, an ambiguous latest date, and no fallback from missing data.
Bootstrap resamples whole horse clusters and keeps paired variables together.
Compare the main associations and every selected prior against a separate
implementation before interpreting results. No performance or training approval
claim is permitted by this descriptive test suite.

## Surprises & Discoveries

The stronger whole-reference rule withholds all11 members of PR130's conflicting
race and six later pairs; 3,166 complete pairs remain across1,584 horses and612
current races. This differs from the inventory's any-usable-prior count3,179.
The fixed pace-recurrence rho is0.3012, while prior pace/current rank is only
-0.0741. These are dependent historical associations, not prediction accuracy.

## Idempotence and Recovery

Only read pinned local artifacts, no collectors or trainers. Fail on changed
source bytes, duplicate identities or invalid numeric metadata. Preserve failed
run evidence. New outcomes, source corrections or alternate definitions require
a separate version and rationale, not replacement of this fixed analysis.

## Artifacts and Notes

Record input and implementation hashes, Python version, exact rules and seeds,
all row/reference/pair ledgers, full-population missingness, group diagnostics
and uncertainty caveats in the generated JSON and research interpretation.
This is a pre-computation historical analysis rule, not a prospective evaluation
preregistration, approval, training grant or live prediction contract.

## Interfaces and Dependencies

Use Fraction for quantities/ties, statistics for correlation/median/quantiles,
and Random for fixed horse-cluster draws. Add no dependency. Keep model code,
forward registry, date/roster/N, saved-model bytes and fit receipts unchanged.

## Outcomes & Retrospective

Executed once at2026-10-20T19:17:06.927296Z after method commitf8aa2b5.
Independent SQLite/NumPy calculations matched all11,523 rows,1,156 references,
30 groups, six current-month deletion summaries and1,000-draw intervals.
Result SHA256:c3ff4a7e71463bf753d7773192327f6746055a9a948c778e81cf9a09203b16eb.
No fitted model, saved-model scoring or new source request occurred.
Local validation:256 tests across seven historical audit suites pass, including
31 new-module tests; Ruff lint and format checks pass. The initial sandboxed
pytest invocation could not create temporary files; an authorized invocation
completed successfully without changing the tests or data.
Goal remains70%, unmet; future dates/roster/N remain unset.

Initial plan: move from measurement availability to a bounded repeatability
diagnostic with explicitly dependent observations and no retrospective validation
claim.

Execution update: preserve the first result unchanged after independent numerical
verification. Publish all missingness and diagnostics rather than selecting a
favorable distance or month. Required CI and normal merge remain to be completed.
