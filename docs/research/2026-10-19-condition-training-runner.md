# Separate A24/B34 Training Execution

The [PR110 recipe](2026-10-19-condition-recipe-review.md) now has a separate
research admission and single-use runner. This implementation **does not approve
or perform the real experiment**. The new registry is intentionally empty.
Original M0/API27 code, commitments, models, result selection and historical
false approval flags are unchanged. There were no KRA/API requests in this work.

## Admission Boundary

`packages/scripts/autoresearch/condition_training_admission.py` pins the cohort,
matrix, selected outcome version, both source audits and three public commitment
files. It verifies all original packet hashes and every identity/feature cell,
label membership, exception reference, cutoff and race-equal weight. All 50
races and 534 appearances are mandatory: 150 positive and 384 negative labels,
including the four previously documented unranked exceptions. Their labels are
membership, never imputed finish ranks. Historical source limitations in PR108
and PR109 remain; this is not independent retrospective availability proof.

The requirement binds source hashes, ordered identities/columns/missingness,
labels/weights, the fixed numerical recipe, Python source and dependency lock
hashes, installed package versions, CPU/OS, NumPy/SciPy BLAS build configuration,
loaded thread-library hashes and thread settings. Every fit stage checks those
bindings again. Seed 42 alone is not a reproducibility claim.

Only `data/contracts/condition_training_reviews_v1.json` can authorize execution.
One matching review must specify the exact requirement SHA256, a reviewer and
timezone-aware review time, completed source/label-version/implementation reviews,
research-only purpose, and the A24=1/B34=1 budget. Registry bytes must match both
HEAD and origin/main; implementation bytes must match committed source. There
is no alternative registry argument, skip flag, or implicit approval from PR110.
Production training admission remains separate and unchanged.

From the isolated checkout, read-only inspection is:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m autoresearch.condition_training inspect
```

Inspect returns an exact requirement and its digest, never a granted approval.
Preserve that inspection for the separate authorization review. If any binding
changes, inspect and review the new requirement before any training. Do not copy
a previous approval or turn on the old cohort's historical approval flags.
Only after the separate exact authorization is reviewed and normally merged,
fetch origin/main and use the same environment with the `run` subcommand.

## Single-Use Execution

The shared common Git directory contains the lifetime reservation keyed by the
fixed cohort SHA256. Atomic directory creation admits at most one invocation,
including concurrent invocations or other worktrees. It is durable before any
imputer/scaler fitting; a durable per-arm attempt is written before estimator
fitting. Failure consumes the reservation. Changing review ID, code, worktree
or output directory cannot grant another attempt. This is a local repository
guard, not a remote anti-tamper service: never delete the ledger or use a fresh
clone to evade it. No automatic recovery/refit command exists.

New artifacts go only under `.cache/autoresearch/condition-training-v1/` and the
cohort SHA256. Existing/symlink destinations are refused. The learner preserves
the fixed median imputer, unweighted scaler, L2 logistic parameters and weights.
Nonconvergence, iteration exhaustion or nonfinite output rejects the pair.
Successful A24 alone is not a successful experiment if B34 fails.

Stored model state includes classes, imputer statistics, scaler mean/variance/
scale, coefficients/intercept, actual constructor parameters, iterations and
warnings. Consumed data includes raw/transformed X, labels, weights, identities,
decision scores, canonical three-ID sets, and loss/regularization diagnostics.
Reloaded scores must agree within absolute 1e-12 and selected sets exactly;
shared-24 preprocessing must match exactly. Output hashes and original hashes
are checked again. The final receipt is written last and marks development-only,
non-independent, no promotion, and two completed estimator fits. A ledger
completion marker without its matching final receipt is not a successful pair.

## Verification And Actual Status

The new suite has 62 synthetic tests, including full-population rejection,
feature type/null/order checks, all six target permutations, all-equal/near-tied
scores, numeric/large/duplicate IDs, empty columns, replay, constructor values,
approval absence/change, concurrent reservations, durable attempt ordering,
convergence failures and fresh-directory retry refusal. Together with the
existing evidence, restricted learner and candidate input suites, **173 tests
pass**, with 15 existing joblib/NumPy deprecation warnings. Ruff lint/format are
required in the new Python CI step. No local-cache source data is needed by CI.

Real-input inspection passed 50 races, 534 rows, all 18,156 feature cells,
150/384 labels, four exceptions and total weight 50. The empty registry rejects
with `exact_repository_approval_required`, before preprocessing/reservation.
Actual A24 fits: **0**. Actual B34 fits: **0**. No real attempt or output directory
has been created. The separately reviewed exact execution authorization is the
remaining gate; passing implementation tests does not supply it.

The immutable local inspection is
`.cache/autoresearch/condition-training-implementation-20261019/inspection.json`,
SHA256 `c13bc637cedde14455fe693467408a7f2ebb255a25803164644b12c8cb7424f3`.
Its exact requirement digest is
`2c6c2251bd718d4316148aaecd0c53270e37dfd64e0ef1d82d9cbb0fcaf1f87b`.
These hashes identify an unapproved inspection, not execution permission.

Any later fit on these already observed outcomes is development research only.
Report both arms and never claim same-block independent validation, automatically
promote a winner, or replace the original full-50 M0/API27 comparison. The 70%
goal remains unmet; future validation still needs its own complete preregistered
population and timely public predictions.
