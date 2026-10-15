# Separate Condition Candidate Inputs

## Decision Before Outcomes

Prepare one label-free candidate input matrix for all 50 October 16-18 races
and all 534 frozen runner appearances. Keep every original M0/API27 prediction
and original 24-column learning-input reservation unchanged. This is a separate
research artifact, not a replacement reservation, new prediction arm, approved
training cohort or claim of improved accuracy.

The proposed feature comparison is original 24 columns versus the same values
plus ten condition-memory columns. Do not vary similarity distance, class rule,
lookback, source selection or feature membership using this block's outcomes.
The additional history source is the exact early-May audit published in PR101,
not a latest-file lookup. The recently observed 90-day contrast remains fixed.

PDF features are deliberately not in this comparison. Although training count
and minutes are available for all 534 appearances, the training window is
unknown for 397; treating them as uniform per-day workload would invent an
unverified denominator. The raw PDF supplements remain separate for later
research. This is a semantic decision made without target results, not a
performance-based feature selection.

## Schema

The first 24 columns preserve the original API14 and recency10 column order,
values, nulls and boolean flags. Ten new fields are prefixed `memory_`:

- `condition_delta90`: the fixed recent same-venue/class/within-200m contrast.
- `fallback90`: true only for no qualifying recent history, distinct from an
  observed zero contrast.
- `prior90_count` and `similar90_count`: observed, supported history counts,
  not a claim of a complete career census.
- `older_count`, `older_same_venue_similar_count`, `older_other_venue_count`
  and `older_missing_condition_count`: separate support for ages 91-180 days.
- `older_career_form` and `older_career_form_missing`: a missing descriptor stays
  null; it is not replaced with an observed value of one half.

Exact Fraction strings in the source audit become finite floats in the candidate
matrix. The exact rational values remain in the SHA-pinned source report. No
scaling, median filling, parameter optimization or fitting is performed here.
Stress-deletion ranges, sign reversals and expansion diagnostics are not model
columns. Identities and source metadata are not model columns either.

## Execution Contract

`packages/scripts/autoresearch/condition_candidate_inputs.py` is isolated from
the original adapters and contracts. It reads the original public commitments,
checks each selected 24-column packet hash, replays the original target identity
selection and reads the early-May audit by exact SHA256. The complete identity
sets must match, without dropping runners or races. Malformed support counts,
unknown feature columns, duplicate members, inconsistent missingness, non-finite
values, unknown fallback reasons and changed source pins fail closed.

All selected source clocks and original materialization clocks must precede the
new candidate creation time, which must precede every frozen cutoff. Completion
also checks the earliest cutoff. Output goes to a new directory only. Original
inputs and public manifests are rechecked before the write and never modified.
The source audit's complete raw reconciliation remains part of the evidence
chain; this adapter's hash check is not a replacement for that source review.

From the isolated repository root:

    PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.condition_candidate_inputs --output-dir .cache/autoresearch/condition-candidate-inputs-20261015/run-1

Repeat into a new directory only before cutoff; the new timestamp changes its
hash. Never recreate a timely artifact after cutoff or replace the original.
The matrix starts with `training_approved=false`, `publication_review_required=true`,
`accuracy=null` and zero fits. Publication of its hash alone does not flip those
flags or authorize a model. Later outcome attachment must be a separate versioned
artifact and a reviewed dataset-admission decision.

## Next Experiment Boundary

First compare the original M0 and API27 predictions against verified outcomes
under the existing 50-race policy. If these outcomes inform a 24-versus-34-column
fit or model choice, this block becomes development data for that comparison;
it is not independent validation. A later full-population future block must have
its own explicit pre-race protocol, frozen model/input receipts and fixed single
unordered three-horse predictions. No such future evaluation arm is registered
by this artifact, and no automatic model promotion is authorized.

Use the same approved learner and preprocessing in both feature arms to isolate
the added features; do not concurrently change the learner or tune on a small
already-examined cohort. The exact fit recipe, outcome policy and full source
admission must be reviewed and frozen before any fit. This document is an input
comparison contract, not an approval that bypasses those requirements.

The authorized in-app ChatGPT page was checked again this turn and showed a
logged-out state. No question was submitted and no new Pro consultation occurred.
This bounded, outcome-free preparation does not rely on unreceived advice.

## Verification

The focused tests check complete joins, preserved original values, missing versus
observed zero/half, unknown or label-like feature fields, duplicate/missing
members, timing boundaries and invalid numeric/support values. They are included
in Scripts Checks. Real execution results and publication receipts are recorded
below only after validation.

The rules and implementation were committed as `d7ed029` before execution.
The real matrix was created at `2026-10-15T12:52:19.454815Z`: **50 races,
534 appearances, 34 columns**. Its null counts preserve the original 32 missing
ratings and 79 missing values in each of four recency fields. Older career form
is missing for 144 appearances; all remain present with explicit missing flags.

Artifacts under `.cache/autoresearch/condition-candidate-inputs-20261015/run-1`:

| Artifact | SHA256 |
| --- | --- |
| matrix.json | `7277897731011c64706f427cd7733444a5450767d312dabe8293a67c35a788a1` |
| independent-check.json | `e7a33a0d8b3aa176facf0e2c1f433449fe2280ebe3edb9a6356d3fc849ad583f` |

The separate public manifest is
`docs/research/supplements/2026-10-16-18/condition-candidate-inputs.json`, SHA256
`c8af98eae757a104528644d52c87ca06744effcfc5c57528ad2b516434ff8cea`.
It identifies the matrix, implementation, parent public pins, condition-memory
source, exact schema, all 50 race identities, row counts and fixed cutoffs.
Raw feature values remain local; no secrets or source data were copied into it.

An independent read-only traversal loaded every original packet by hash, indexed
the exact memory source by race/gate/canonical horse ID, and checked all **12,816
original values and types** plus all **5,340 added values and types**. It used
direct Fraction conversion rather than the candidate transformation functions.
Full identity sets, per-column null counts and creation-before-cutoff checks
matched. No fitted preprocessing or outcome labels were read.

**165 local tests passed**, including all 38 new cases and existing condition
memory, history expansion, original prospective-input, M0-forward and API27-forward
regressions. Ruff lint/format and whitespace checks pass. Remote check results
and normal merge time are recorded in the PR receipt; local success is not a
claim that every remote check has passed. The original commitment hashes remain
unchanged, and the candidate still requires separate publication/source review
and versioned outcomes before any reviewed training authorization.
