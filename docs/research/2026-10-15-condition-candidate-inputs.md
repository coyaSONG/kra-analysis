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
