# Audit historical sectional endpoint arithmetic

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

PR125 checked API-to-HTML cells but skipped Seoul's separately printed final
600m and 200m durations. PR126 proposed checking all preserved historical
rows before defining time features. This read-only audit tests whether
printed segment duration equals the difference between its labelled
cumulative endpoint times. It is not a model or an accuracy experiment.

## Progress

- [x] Read PR125 replayer, original support policy and PR126 no-fit proposal.
- [x] Implement full-original-population arithmetic and eligibility audit.
- [x] Test endpoint errors, missingness and preservation of exclusions.
- [x] Run original archive, independently check findings, publish report.
- [ ] Pass required checks and normally merge.

## Surprises & Discoveries

Busan's early cumulative column position varies with distance. Two names
can describe the same physical position (for example S1F and G6F at 1400m);
the labelled distance header, not field-name order, supplies the endpoint.
Jeju's one table lacks an independent cumulative counterpart, so it cannot
provide the same arithmetic test.

The first literal-span pass found 44 positive Busan 1300m `8-6F` values
outside the implied race endpoints. The original HTML linked an official
guide which explicitly identifies that column as the initial 100m.
One guide capture was preserved with a receipt and raw hash; all 44
subsequently equal the cumulative 100m value exactly. This was a documented
semantic correction, not tolerance tuning.

## Decision Log

Reuse the original pinned source audit and exact header parser. Do not
modify frozen input contracts or introduce a generic feature framework.
Use decimal arithmetic with no fitted tolerance. Keep every observation,
including excluded starts, in the diagnostic population; eligibility and
arithmetic are separate attributes. Recompute the existing whole-race
conflict exclusion with `reconcile_group`, never reinstate a row because
its time is positive. Date: 2026-10-20 UTC.

Require the pinned current guide and its explicit 1300m row before using
the special 0-100m mapping. Do not generalize to the guide's unseen result
layouts or claim the guide was captured before the historical cutoff.
Date: 2026-10-20 UTC.

## Outcomes & Retrospective

Original execution retained 102 races/1029 rows and reproduced the
1001 supported/28 withheld split. There are 2805 exact, 417 unsupported
span and 40 missing checks. Jeju's 298 observations have no independent
cumulative test. Separate HTMLParser/Fraction verification reproduced all
731 tested rows and all check counts. Local related tests: 194 passed,
including 37 new tests; Ruff passed. Frozen model, receipt, prediction
and empty forward-registry hashes are unchanged.

No fitting, future registration or prediction occurred. Remaining research
is descriptive information/coverage and point-in-time transferability,
not a new training approval. The 70% goal remains unmet.

## Context and Orientation

The isolated checkout is `kra-analysis-race-card-pdf`. The source root is
`.cache/autoresearch/observed-history-extension-20260501-14`.
`sectional_source_audit.py` pins its seed and official archive and validates
all API/event/gate/horse joins. `timing_rows` enforces the original labelled
headers and complete gate set. `official_result_support.reconcile_group`
checks each historical rank/time against the official row; the existing
`history_gap_expansion.supported_extension` withholds a whole race if any
rank/time conflict exists. Reproduce that policy without reading October
target files or importing its broader experiment runner.

## Plan of Work

Add `packages/scripts/autoresearch/sectional_arithmetic_audit.py`.
Parse exact minute:second tokens and preserve blanks/zero separately from
positive durations. For Seoul compare the two printed final durations to
total minus their cumulative checkpoint. For Busan use labelled cumulative
metre positions, zero at start and the printed total at finish; test each
named segment independently, never sum overlapping final segments.
Retain unsupported endpoints, missing values and residuals as explicit
statuses. Jeju rows remain present with no independent arithmetic test.

Report all observations, support/exclusion counts, relation counts by
venue/distance, all non-equal evaluable checks and source pins. Add focused
tests in `tests/test_sectional_arithmetic_audit.py` and include them in the
existing Historical time source audit CI step. Publish a timestamped
original-archive report and a research interpretation in `docs/research`.

## Concrete Steps

From the isolated checkout:

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B \
      -m autoresearch.sectional_arithmetic_audit

The command emits JSON to stdout, with no writes or network requests.
Use a separate exclusive-create artifact writer only to publish a new report.

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B \
      -m pytest -q -p no:cacheprovider \
      packages/scripts/autoresearch/tests/test_sectional_arithmetic_audit.py

## Validation and Acceptance

All 102 races and 1029 rows must remain represented; support policy must
reproduce 1001 admitted and 28 withheld rows, not silently filter the audit.
The report must distinguish exact arithmetic, missing operands, physically
unsupported endpoints and numerical disagreement without converting them
to model performance. Synthetic tests must catch changed headers/identity,
zero/blank ambiguity, reversed endpoints, positive-time excluded starts,
and mismatching printed final durations. Independently replay arithmetic
against original HTML without using the new arithmetic functions.
Required CI must pass before normal merge.

The local six-file test command passed 194 tests. The new test file alone
contains 37 cases. Published report SHA256:
`94fbd92c4f5506da4516bfe1e92858018ca9b2be24f567013eb8a4cccd53f18d`.
Independent verifier:
`.cache/autoresearch/sectional-arithmetic/independent_check.py`.

## Idempotence and Recovery

Reruns read the same pinned bytes and emit a new analysis timestamp.
Never overwrite original captures or existing report versions. Hash
failure stops execution. A disagreement is a result to retain, not a reason
to tune tolerances or fetch a replacement original.

## Artifacts and Notes

No real future dates/N, target outcomes, saved model inference or training
are needed. May results collected in October do not establish May
pre-race availability. Source agreement and arithmetic consistency do not
prove predictive value.

## Interfaces and Dependencies

Use the Python standard library Decimal, Counter, pathlib and existing
replayers. `audit(root=source.ROOT)` returns a JSON-serializable report;
`relations(kind, distance, values)` defines printed endpoint checks;
`check_relation(...)` returns a status and exact residual. No learner or
HTTP client is introduced.

Update note (2026-10-20): recorded the officially documented 1300m special
case, real archive totals and independent verification; CI/merge pending.
