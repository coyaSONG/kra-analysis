# Condition Candidate Pre-Fit Review

## Decision And Consultation

The same-cohort A24/B34 experiment has a fixed numerical design and a completed
ChatGPT Pro methodology review. **This document is not training approval.**
Actual development fits remain zero; the cohort's approval flags and production
registry are unchanged. A separately reviewed admission contract and runner
must pass their checks before any preprocessing or estimator fitting.

The authorized browser submitted the preserved question on
2026-10-18T23:58:12Z after the earlier failed submissions and recorded backoff.
The UI displayed a completed response after **15m46s**; completion was observed
before this record at 2026-10-19T00:16:06Z. Generation was neither interrupted
nor given a short response deadline. Earlier failed consultation receipts remain
unchanged. The [consultation conversation](https://chatgpt.com/c/6ad0d05d-5b08-83e8-b4b5-5252f401bb4d)
contains the full response; the findings below are a summary, not a verbatim
archive. Pro reviewed the supplied evidence and public code at
`c2b55cf806585cd27e8b3a123a99684fa4c8d9c5`, not the local raw data independently.
Its conditional methodological support is not an execution authorization.

This recipe is fixed **after observing the October outcomes**, although its
feature matrix was sealed before them. It is not an outcome-blind preregistration
or a new prospective prediction. No KRA/API source requests were made in this
review: the completed block was not recollected and no new future block was
registered. No claim of fresh source availability is made.

## Immutable Inputs And Target

Use all **50 races / 534 frozen runner appearances**, without removing any
exception, race or venue. The source audits are
[PR108's development audit](2026-10-18-development-source-audit.md) and
[PR109's baseline audit](2026-10-18-baseline-lineage-audit.md).

| Input | SHA256 |
| --- | --- |
| PR108 development-cohort.json | c25db29f0ba78cd3e7ab49c04950fcde3f3a12686ce4aad1ba69b33fb2616e03 |
| Original 34-column matrix | 7277897731011c64706f427cd7733444a5450767d312dabe8293a67c35a788a1 |
| Selected outcomes.json | 0cf7be483e1089ba55db78f70c51c9a6dbcaf8738847460f469ee11901ac0cbb |
| Baseline lineage audit.json | 8dfaf0063472a8f811e25cdaad14c43be97d269abef59921a502fced3d5fba4f |

The proposed operational label is membership in the observed unique unordered
top-three set of the **frozen candidate roster**. It is not finish-rank imputation,
counterfactual ability, refund treatment or an assertion of eligibility at cutoff.
Cancellation announcement timing has not been independently established here.

Before deriving labels, every race must have exactly three distinct target IDs
inside its exact frozen roster, with unique identity joins and no unresolved
target conflict. Under those conditions all 534 rows remain: 150 membership-one
and 384 membership-zero. The four exception observations retain their original
notes and unresolved rank status: Busan October 16 R8 exclusion, Seoul October
17 R3 stopped running, Seoul October 17 R4 exclusion, and Seoul October 18 R6
withdrawal. Their absence from a verified top-three set supports membership-zero,
not an invented numeric rank. Exception text alone never supplies a zero label.

Any undefined, conflicting, tied or missing target that does not meet the existing
unique-target policy blocks the entire fixed run, not just that race. Keep
`unique_top3_observed` distinct from irreversible official finality. Corrections
require new linked versions and review, never overwriting these inputs. Do not
feed these membership labels into historical ranked-form observations.

## Fixed Numerical Recipe

The scientific comparison is the whole feature bundle under one learner, not
proof that any individual memory field causally improves prediction.

| Component | Fixed choice |
| --- | --- |
| A24 | Original first 24 columns, in the pinned matrix order |
| B34 | The same 24 plus the original ten condition-memory columns |
| Population and row order | All 50/534; race ID ascending, then numeric gate ascending |
| Data type | float64; only permitted nulls become NaN; reject invalid numbers/infinity |
| Imputer | Median, keep_empty_features=True, no new missing indicators |
| Scaler | StandardScaler default unweighted mean/variance |
| Estimator | LogisticRegression; lbfgs; L2 (l1_ratio=0); fit_intercept=True |
| Regularization | C=1/50=0.02; no class weights |
| Optimization | tol=1e-8; max_iter=2000; random_state=42 |
| Sample weight | 1 / frozen roster size for every appearance, including exceptions |
| Fit budget | One estimator fit per arm, two total; no deterministic refits |
| Selection | Score descending, numeric gate ascending, numeric horse ID ascending |
| Serialization | Selected three distinct canonical horse IDs in numeric ascending order |

Each race's sample weights sum to one and the total is 50. Do not renormalize
weights, rebalance classes, remove exception rows or apply weighted scaling.
The loss is race-equal; preprocessing is appearance-weighted. With total weight
50 and C=0.02, the objective is weighted-mean binary logistic loss plus
`0.5 * ||beta||^2`, with unpenalized intercept. Shared-column imputation/scaling
statistics must match exactly across arms; shared-column fitted coefficients
need not match. Added correlated columns also change L2 representation effects.

The ten additional columns, in order, are `memory_condition_delta90`,
`memory_fallback90`, `memory_prior90_count`, `memory_similar90_count`,
`memory_older_count`, `memory_older_same_venue_similar_count`,
`memory_older_other_venue_count`, `memory_older_missing_condition_count`,
`memory_older_career_form`, `memory_older_career_form_missing`. Do not change
distance/class matching, lookbacks, thresholds, interactions or feature selection.
The 11,523 historical rows remain feature evidence, not extra training instances.
PDF period fields with unknown semantics remain excluded.

This learner optimizes a binary surrogate, not joint exact-set probability.
Ranking marginal scores cannot in general maximize the probability of one exact
three-horse set. Row-level accuracy, including the 384/534 all-zero baseline,
is not the 70% objective. Coverage and subgroup diagnostics cannot replace the
complete race-level metric or support a winner selected on this development set.

## Admission And Implementation Gates

The existing `restricted_cohort` label admission requires
`ordinary_rank_observation`; it does not admit this new exception membership
policy. `restricted_ablation.run` also fits development/full phases for two arms,
four fits total, with the older feature/date contract. Do not call it unchanged
or patch its frozen constants to accommodate this experiment. Keep M0/API27's
original code, models, commitments and evaluations untouched.

A separate official research admission path must be reviewed under the repository
training policy. Its immutable approval must bind the exact cohort, selected
outcome version, label policy, recipe, code, environment and fit budget. It may
reference the old cohort while preserving its historical false approval flags;
it must not bypass them by merely inventing a new script or treating this advice
as approval. Production promotion is a separate decision.

Required checks before fitting even an imputer or scaler:

- Verify all input hashes, 50 race IDs, 534 unique identity keys and exact roster
  equality; reject wrong outcome versions or any dropped/expanded join.
- Verify all 18,156 feature cells and missingness against the original matrix;
  B34's first 24 columns must equal A24 in values, nulls, types and order.
- Check each membership label, all four exception references and each race's
  weight sum; counts alone are insufficient. Outcome/exception note mutations
  must not change X or weights. No post-outcome fields may enter X.
- Verify actual constructor parameters and refuse reused output destinations,
  original artifact paths, absent approvals or exhausted fit budgets.
- Write a durable attempt ledger before each estimator fit. Failure consumes
  that attempt; no fresh-directory retry or parameter adjustment. An incomplete
  pair cannot become an A-only or B-only success claim.

ConvergenceWarning is an error; `n_iter >= 2000` and nonfinite coefficients,
intercepts, statistics or scores reject the run. Reload/inference checks do not
refit. Serialized decision scores must match sklearn within 1e-12 and the
selected sets must agree exactly for every race, including near-boundary scores.
Synthetic tests must cover ties, near ties, all-equal scores, numeric versus
lexicographic IDs, large IDs and duplicate IDs. No epsilon ties, rounding or
abstention may change the fixed selection rule.

Canonicalization is essential: the old learner returns score-ordered IDs while
the original evaluator compares canonical lists. The new adapter must sort the
selected set before serialization and test all six permutations as equivalent.
This is a future adapter requirement, not evidence that the published M0/API27
0/50 evaluation is wrong.

The final receipt, written last, must bind attempt/reviewer/time/approval, exact
code and dependency hashes, ordered identities/columns, raw and transformed X,
y and weights, fitted imputer/scaler state, coefficients/intercepts/classes,
actual estimator parameters, iterations/warnings, replay results and unchanged
original hashes. Preserve `classes=[0,1]`, scaler mean/variance/scale, missingness,
exception counts and common-24 checks. Include loss and regularization diagnostics.
Record Python/NumPy/SciPy/sklearn, BLAS, CPU and thread settings; seed alone does
not guarantee byte reproducibility. Store development-only, non-independent,
no-promotion and actual-fit-count flags. Future inference uses the stored
preprocessing, never newly fitted statistics.

## Verification And Next Boundary

The existing training-evidence, restricted-ablation and condition-candidate-input
suites passed **111 tests in 2.93s**, with 15 existing joblib/NumPy deprecation
warnings. These use synthetic fixtures; there was no actual October fitting.
A read-only check of the pinned cohort confirmed 50/534 identities, target
membership counts 150/384, exact rational weight total 50 and unchanged false
training flags. The observed environment was Python 3.13.13, NumPy 2.5.1,
SciPy 1.18.0 and scikit-learn 1.9.0; the future executable approval still needs
the complete environment fingerprint and new runner tests described above.

Next implement and test the separate fail-closed admission/runner with an
ExecPlan, then review its exact immutable research authorization before fitting.
The completed methodology consultation removes the consultation-access blocker,
not the implementation or approval gates. No new recipe entered the production
registry and no future dates were selected in this change.

Independent improvement testing requires a separately registered future complete
block: exact dates/venues, roster and schedule-change rules, cutoffs, model/code/
environment hashes, feature sources and missingness, public canonical predictions,
failure/late-output treatment, result/correction policy and uncertainty/stopping
rules. State whether inputs freeze block-wide before first cutoff or race-wise,
and whether earlier-block outcomes can enter later features. Do not choose dates
based on development scores, replace post-cutoff predictions or use an OR-union
of the two arms. Report both arms; a single week never automatically promotes one.

The [original full-block result](2026-10-18-full-block-paired-results.md) remains
M0 0 hits / 50 misses and API27 0 hits / 50 misses, with zero pending or undefined
race targets. Both exact accuracies are 0%, difference 0 percentage points;
paired counts are 0 both, 0 M0-only, 0 API27-only and 50 neither. The block is a
tie, not general model equivalence. The nominal IID 95% exact binomial interval
is 0-7.11% for each arm and does not account for within-week dependence. The
70% goal is unmet. These 50 races cannot independently validate a model learned
or selected from them; 534 appearances are not 534 independent race trials.
