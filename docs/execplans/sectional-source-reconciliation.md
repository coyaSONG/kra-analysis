# Reconcile preserved time fields with official result tables

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

Determine whether API elapsed and sectional values correspond to the labelled
columns of the original official HTML, without fitting a model or treating
agreement as training approval. PR124 established raw presence but did not
compare sectionals across sources. This step makes that evidence inspectable
over every record in the same May acquisition seed.

## Progress

- [x] Read the source audit, original acquisition report and replay APIs.
- [x] Replay original archives and inspect all 14 timing header variants.
- [x] Implement a read-only, fail-closed labelled-column comparison.
- [x] Replay the entire archive; retain discrepancies and zero/blank pairs.
- [x] Run 191 related tests and save the report and research findings.
- [ ] Complete lint, remote checks and normal merge.

## Surprises & Discoveries

Busan exposes separate segment and cumulative tables; Seoul's timing table
contains cumulative columns plus two final-section durations. Headers and
distance labels are evidence, not interchangeable column positions. Jeju
uses another schema. No Yeongcheon rows occur in this seed.

The first replay rejected an assumed fixed Busan cumulative column order.
Inspection showed S1F in the third column at 1200/1300/1400m, second at
1600/1800m and first at 2200m. Explicit observed layouts now retain this
distinction. All 10,932 comparisons reconcile: 8,771 positive equal values
and 2,161 API-zero/HTML-blank pairs; no conflicts in the selected archive.

## Decision Log

Use exact known headers and Decimal minute/second parsing, rejecting unknown
schemas and duplicate/missing gates. Preserve all seed identities, including
unresolved ranks. Numerical agreement will not override existing exclusions.
This decision was made on October 20, 2026 before any target outcome comparison.

Do not generalize the six Busan layouts to an unobserved distance. This
deliberately rejects a new course configuration until its original headers
are inspected. Existing rank conflicts remain withheld despite time agreement.

## Outcomes & Retrospective

The full original seed and HTML archive have been replayed. Source agreement
is now quantified for every runner, including unresolved outcomes. The
distance-dependent Busan order is a concrete prevention of mislabelled future
features. No new API requests, models, target predictions or future
registrations occurred. The 70% goal remains unmet.

## Context and Orientation

The isolated checkout is `kra-analysis-race-card-pdf`. Original source root is
`.cache/autoresearch/observed-history-extension-20260501-14`. The seed hash is
`561bcfdc6fe2c4733e571b8c77034a2753e88794d5d7d3a6ee5d2ee2f25a5407`;
`official/archive.json` hash is
`8ca56ba232156beb824e9baab1f4c8c5b301e8d619f81e17d1213e8f6512e1bd`.
`frozen_history_view.replay_frozen` checks the original API inventory.
`official_history_support.replay_archive` checks original HTML receipts,
URLs, clocks, hashes and event/horse identities. Neither fetches data.

## Plan of Work

Add `packages/scripts/autoresearch/sectional_source_audit.py` and matching
tests. Reuse the original replayers before extracting the labelled timing
tables with `shared.official_result_support.tables`. Join API and HTML by
event, gate and normalized horse ID; never row order. Group diagnostics by
physical venue and distance. Preserve unmatched values explicitly, rather than
filtering failures out. Save a separate timestamped report and research note.

## Concrete Steps

From the isolated checkout, run the new module with `PYTHONPATH=packages/scripts`
and `.venv/bin/python -B -m autoresearch.sectional_source_audit`. It reads only
the original pinned May root and prints JSON. Use the existing exclusive
`observed_history_seed.save` helper for a new report path; never overwrite it.
Run `.venv/bin/python -B -m pytest -q -p no:cacheprovider` on the new tests,
`test_history_time_audit.py`, and the existing official-history tests with
`PYTHONDONTWRITEBYTECODE=1`. Run Ruff check and format checks on changed Python.

## Validation and Acceptance

All 102 races / 1,029 rows must remain represented. Every recognized table must
cover exactly the verified roster. Test changed headers, distances, identities,
duplicate gates, row reordering, unsupported time strings and zero/blank pairs.
An exact numeric match is distinct from a zero/blank correspondence. A
disagreement is an output finding, not an exclusion. Source bytes are never
modified. Tests must not require a live API or invoke training.

## Idempotence and Recovery

Replays are read-only and may be repeated. Generated reports have their actual
analysis time; never backdate them to the original acquisition cutoff. Stop on
pin or schema errors and investigate. Do not recapture to obtain a preferred
value. Keep original conflict exclusions and all A24/B34 artifacts unchanged.

## Artifacts and Notes

The new report and note will live under `docs/research`, with a reproducible
command and source pins. Remote CI and merge evidence belong to the PR.

Saved report:
`docs/research/experiments/2026-10-20-sectional-reconciliation/report.json`,
SHA256 `bb2d9ce7031efa252618a5411b3cb8530c028066aac1164671f0a7eb9a06badb`.
Findings: `docs/research/2026-10-20-sectional-source-reconciliation.md`.
The first test invocation named a nonexistent `test_race_conditions.py`
and ran zero tests; after locating the actual condition tests, 191 tests
passed in 0.72s. No source files were modified to make the result agree.

## Interfaces and Dependencies

Use Python standard library Decimal and collections plus existing frozen/API/
HTML replayers. Expose pure header/table validation and comparison helpers for
unit tests. No dependency changes, network client, learner or inference import.

Initial plan: bounded source reconciliation, not a new modelling experiment.
Update: completed full source replay, documented the Busan layout discovery,
and recorded local tests. CI/merge remain pending.
