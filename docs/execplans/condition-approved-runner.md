# Implement the separate A24/B34 research runner

This is a living ExecPlan maintained under `.agent/PLANS.md`.

## Purpose / Big Picture

Enable a local, explicitly approved comparison of the frozen 24 original
features (A24) and the same features plus ten memory fields (B34). The operator
can inspect the exact approval requirements without fitting, and execute only
the repository-approved pair once. This is development research on already
observed outcomes, never independent evidence for the 70% prediction goal.

## Progress

- [x] Read PR110, existing admission, learner and pinned artifact schemas.
- [x] Implement pure full-population validation and fixed numerical learner.
- [x] Implement repository-only approval, immutable evidence and shared fit budget.
- [x] Add synthetic positive/negative tests and CI coverage; inspect real inputs without fitting.
- [x] Commit and push validated implementation; open PR111.
- [ ] Pass final remote checks and normally merge PR111.
- [x] Evaluate actual-fit conditions: exact repository approval is absent; no real fits permitted.

## Context and Orientation

`docs/research/2026-10-19-condition-recipe-review.md` specifies the experiment.
The existing `restricted_ablation.py` fits four times and its admission rejects
exception observations; neither it nor M0/API27 may change. PR108's local
development-cohort.json contains 534 identities, 34 features per appearance,
50 targets and separate raw observations. The original matrix, selected outcomes,
source audits and public commitments have fixed SHA256 hashes in PR110.
The four unranked exceptions stay in the frozen roster. A label is one exactly
when the horse belongs to the verified three-horse target, not a finish rank.

## Plan of Work

Add `condition_training_data.py` to validate complete identity joins, exact
feature bytes/types, targets and observations and to prepare ordered arrays.
Add `condition_training_model.py` for the unchanged numerical recipe and
canonical unordered-three selection. Add `condition_training.py` for the local
CLI and single-use execution ledger; `condition_training_admission.py` holds
fixed pins, environment/code fingerprints and repository approval. Add an empty research-only approval registry at
`data/contracts/condition_training_reviews_v1.json`. No CLI flag can supply an
alternative approval file or disable checks. An inspection command emits the
exact requirements; it does not approve them.

The separate approval must bind source and label review, recipe, code, runtime,
complete input hashes and two estimator attempts. Its existence requires an
explicit reviewed repository change after implementation validation. Production
approval stays empty. A durable exclusive reservation under the common Git
directory keys the experiment to its frozen cohort, not a review ID or output
path; it prevents retries through another worktree or newly named review. The
pair is reserved before preprocessing; each arm is recorded before its one
estimator call. Failures remain visible and never auto-retry. Final receipt is
written last. Output has a fixed separate cache directory, not caller-chosen
paths that might overwrite originals.

## Milestones

First establish data and inference behavior using synthetic fixtures with
ranked and unranked observations. Then exercise the complete admission and
single-use runner using temporary test roots, proving invalid approvals never
reach preprocessing. Finally inspect real pinned inputs with zero fits, review
test and CI evidence, and publish the implementation. Only a subsequent exact
approval may admit the actual pair; do not infer approval from passing tests.

## Concrete Steps

Work in the existing isolated checkout, not the owner's original tree. Run:

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m pytest -q -p no:cacheprovider packages/scripts/autoresearch/tests/test_condition_training.py
    .venv/bin/ruff check packages/scripts/autoresearch/condition_training*.py packages/scripts/autoresearch/tests/test_condition_training.py
    .venv/bin/ruff format --check packages/scripts/autoresearch/condition_training*.py packages/scripts/autoresearch/tests/test_condition_training.py
    PYTHONPATH=packages/scripts .venv/bin/python -B -m autoresearch.condition_training inspect

The inspect command must show 50 races, 534 rows, 150 positive labels, 384
negative labels and zero fits. The run command without approval must reject
before producing any models. Add the same regressions to the existing Python
CI job and require its success before normal merge without protection bypass.

## Validation and Acceptance

Test changed hashes, missing or duplicate races/horses/gates, altered columns,
types and missing flags, target conflicts and out-of-roster targets. Verify
exception rows are retained and outcomes cannot enter X or weights. Check
all-missing columns, shared-24 statistics, convergence warnings, iteration
limits, nonfinite values, exact set replay, ties, near ties, numeric IDs and
all six target permutations. Check no approval, changed environment/code,
exhausted budget, failures after reservation, concurrent claims, different
review IDs and output directories cannot cause extra fits. Successful synthetic
execution must perform two fits, write consumed matrices and models, then a
receipt with hashes, environment, iterations and non-independent flags.

## Idempotence and Recovery

Inspection is read-only and repeatable. Actual run is deliberately not
repeatable; even a failed reserved run cannot silently reset its budget.
Preserve partial output and attempt ledgers. Diagnose failures without fitting;
any future experiment requires a separately reviewed protocol, not deletion of
evidence. Original source and prediction bytes must be checked again at exit.

## Interfaces and Dependencies

Use existing NumPy, SciPy, sklearn, threadpoolctl and repository JSON/hash
helpers. The numerical recipe is median imputation keeping empty columns,
unweighted StandardScaler, L2 logistic lbfgs C=0.02, tolerance 1e-8, maximum
2000 iterations, seed 42, unpenalized intercept and no class balancing.
Weights are 1/frozen roster size. Preserve stored scaler variance and scale.
Score descending/gate ascending/numeric ID ascending chooses three, serialized
in numeric ID order. No outcome-driven tuning, refits or new dependencies.

## Surprises & Discoveries

The production registry is intentionally empty. Existing API27 research review
is separate from production and is a useful precedent, not approval for this
new experiment. Local runtime sklearn is 1.9.0; pin actual runtime and BLAS
fingerprints, not only a random seed.

## Decision Log

Use a shared common-Git-directory reservation rather than an output-directory
lock. A fresh directory or worktree must not reset the two-fit budget. Reserve
the whole pair before preprocessing to fail conservatively on interruption.

## Outcomes & Retrospective

The new 62-test synthetic suite and 111 existing admission/ablation/input tests
pass together (173 total; 15 existing joblib/NumPy deprecation warnings).
Read-only real-input validation confirms all 50/534 identities, 150/384 labels,
four retained exceptions and weight total 50. Exact approval is absent, and
neither the real reservation nor model output directory exists. Implementation
publication is pending CI. Actual research fits remain zero, original results
remain unchanged, and no future evaluation interval has been registered.

October 19 update: split admission and execution into separate small modules;
require the approval registry to match both HEAD and origin/main. Record NumPy
and SciPy build configuration because Accelerate is not listed by threadpoolctl.
Added concurrent-claim, revocation and exception/null tests before publication.
A variable-extra-column/missing-value synthetic test additionally verifies exact
shared preprocessing statistics. PR111 is open; normal merge awaits final CI.

Initial plan written October 19, 2026: additive implementation only, with actual
fitting conditional on a separately bound and reviewed repository approval.
