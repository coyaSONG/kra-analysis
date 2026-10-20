# Exact-set objective and next research decision

## Scope

This is a research diagnosis, not a new candidate, approval or registration.
The target remains one unordered three-horse set per race on the complete
frozen universe. A24/B34 remain frozen; their one-fit budgets are consumed.
No new training, live inference, future dates or sample size are authorized.
The [forward protocol draft](2026-10-20-condition-preregistration-draft.md)
continues to have an unset evaluation interval.

## What the current objective does and does not optimize

`condition_training_model.py` uses binary top-three membership labels,
logistic loss and the three largest per-runner scores. A monotonic logistic
transformation does not change that order. This does **not** mean that its
scores are the true conditional inclusion probabilities.

Even if those probabilities were known exactly, selecting their three
largest values maximizes expected overlap with the true three-horse set,
not necessarily the probability of getting the entire set right:

    E[|S intersect T| | X] = sum over h in S of P(h in T | X)
    P(exact hit | X, S) = P(T = S | X)

Here X denotes pre-race information, T the actual unordered triple and S
the single selected triple. The first equality follows from linearity of
expectation and does not require independence. The second objective
requires a joint distribution over triples; marginal probabilities alone
do not generally determine its maximizer.

### Exact synthetic counterexample

Five hypothetical runners have the following complete distribution over
the ten possible triples. The six unlisted triples have probability zero.
These are invented numbers, not KRA observations or fitted estimates.

| True triple | Probability |
| --- | ---: |
| 1, 2, 3 | 0.30 |
| 1, 4, 5 | 0.25 |
| 2, 4, 5 | 0.24 |
| 3, 4, 5 | 0.21 |

The marginal inclusion probabilities are 0.55, 0.54, 0.51, 0.70 and 0.70.
The frozen selector chooses **1, 4, 5**: expected overlap 1.95 and exact
probability 0.25. The joint optimum is **1, 2, 3**: expected overlap 1.60
but exact probability 0.30. The tie between runners 4 and 5 is internal to
the selected set; it does not cause the difference.

The regression test
`test_marginal_selection_is_not_always_joint_exact_set_optimal` uses exact
fractions, enumerates all ten triples, verifies both objective values and
checks the existing selector for all 120 input permutations. It loads no
race data or saved model and calls no fitting routine.

This proves a possible objective mismatch, **not** that it caused the
observed failures, that a learned joint model will improve generalization,
or that KRA accuracy can gain five percentage points. A joint model can
also be misspecified and data-hungry. The current selector is not being
"fixed": changing it would create a different model contract.

### Two changes that do not solve the mismatch

For fixed logits s and p = sigmoid(s), an independent Bernoulli model
conditioned on exactly three included runners assigns weight

    product(p_i for i in S) * product(1-p_i for i outside S)
      = product(1-p_i for every i) * exp(sum(s_i for i in S)).

The common factor and conditional normalization do not change the
maximizing triple: it is still the three largest logits. Merely wrapping
the same scores in a triple-probability calculation cannot improve the
selected set. This statement concerns this specific factorized model,
not arbitrary joint distributions such as the counterexample above.

Similarly, adding the same fixed race-level term to every runner's logit
leaves within-race ordering unchanged. This does not claim that refitting
a model with new variables leaves its other coefficients unchanged.
Two additional tests enumerate all 32 assignments of probabilities 1/5
or 4/5 to five runners and apply five common score shifts to two synthetic
races, respectively. Ties retain the frozen selection policy.

## Evidence boundaries

The old 50-race M0/API27 comparison was 0/50 for each model. The A24/B34
4/50 and 5/50 counts in the
[development report](2026-10-19-condition-development-results.md) are outcome-informed training
results, not independent future performance. Neither establishes the
attainability or impossibility of 70% for every conceivable pre-race model.
Do not reuse the 50 outcomes to choose losses, features or hyperparameters.

The [sectional reconciliation](2026-10-20-sectional-source-reconciliation.md)
establishes API/HTML numerical correspondence for the preserved May
archive, not pre-race availability or pace-feature predictive value.
Zero/blank causes, unobserved venue/distance layouts and timing eligibility
still need separate evidence. A positive elapsed time is not sufficient
to admit a disqualified or unresolved start.

## Completed Pro consultation

On October 20 UTC (October 21 KST), the authorized Chrome conversation
[methodology review](https://chatgpt.com/c/6ad0d05d-5b08-83e8-b4b5-5252f401bb4d)
was accessible with Pro selected. The follow-up question was sent once;
the UI reported **15m 49s** processing and then a completed response.
Generation was not stopped or given a short response limit. The completed
answer was read in full.

The question shared public aggregate findings, the public source-audit
URL and the research restrictions. No credentials or raw archive were
uploaded. The advisor reviewed public descriptions/code, not the local
archive, and explicitly did not produce new empirical audit results.
Its recommendations are methodological input, not an independent
validation or execution approval.

The accepted priority is a bounded **May time-information feasibility
audit**, after the synthetic objective checks above. Do not build another
general approval platform or a new joint learner in this step.
The remaining sections specify a proposal, not completed implementation.

## Proposed no-fit audit

### Inputs and admission

Read only the original May 1-14 API/HTML archive, its source receipts,
existing supported-history exclusions and synthetic fixtures. Do not
read the October 50 targets, predictions, scores or comparison rows for
this audit. May ranks/exception states can establish historical start
eligibility; never report how May finishing times predict the same May
race's top three.

Start with all 1,029 observations and retain a reason for each missing or
excluded value. The existing 1,001 supported observations are an upper
bound, not a claim that 1,001 complete time-feature rows exist. Keep the
11-row conflict race and other 17 withheld observations excluded.
Positive time does not reinstate disqualified/nonfinishing starts.
No unsupported history removes a runner or race from a future population.

The observation grain is one horse in one historical start. Preserve
event/gate/horse identity, physical venue, distance, literal class,
observed course/header version, raw API and HTML values, units/precision,
cumulative-versus-segment type, verified start/end positions, operand
IDs, source versions and availability clocks. Unknown locations of named
corners must not become invented segment distances.

### First question: endpoint arithmetic

PR125's Seoul mapping skips the two separately printed final-section
columns. Its API/HTML equality report therefore does not establish
`total - cumulative checkpoint = final segment` on every row.
The next audit must independently check these relations against those
printed columns over the full preserved archive, preserving all residuals.
Only identified contiguous, nonoverlapping sections may be summed;
the final 600m and final 200m overlap and must not be added together.

Use decimal source precision. Keep unexplained residuals unresolved;
do not choose a tolerance to make the report pass without an evidenced
rounding rule. Reject unknown venue/distance layouts and keep API
zero/HTML blank as null with unknown cause, not measured zero seconds.
Numerical agreement remains distinct from independent source truth.

### Minimal candidate quantities, not approved model columns

For an eligible historical start define total time T, initial 200m time E,
verified final 600m time L and nominal distance D. A cumulative
checkpoint may supply L = T - C(D-600) only after its endpoints and
arithmetic have been validated.

Inspect three proposed quantities: `(T-m)/m`, `(200/E)/(D/T)`, and
`(600/L)/(D/T)`. Here m is the median total time of the explicitly
identified eligible finishers of that same historical race. Preserve
reference IDs/count/exclusion reasons and require at least two eligible
comparison runners; a single runner's forced zero is not relative evidence.
Missing operands produce missing quantities. Keep raw T/E/L/D for audit,
not additional automatically approved model columns.

These express time gaps and speed allocation, not a track-adjusted ability
rating or guaranteed favorable direction. Pooling physical venues or
learning class/distance corrections is out of scope. For a possible later
history summary, propose one rule only: the median of eligible prior
starts 1-180 calendar days earlier at the same physical venue and exact
distance, with support count, latest age and missing state. This proposal
does not alter A24/B34's existing history policy or authorize applying it
to a real future roster.

### Point-in-time boundary and normalization

An eventual training row needs the target's full pre-race roster and
covariates, its selected historical sources/reference groups and a
separately versioned target. A prior start must precede the target date,
and every operand/reference source version must have been available
before feature freeze, itself before cutoff. Local collection time alone
does not prove earlier upstream publication.

A median within an already completed historical race is permissible only
when its entire selected reference evidence was available by the target
freeze. This is different from learning an imputer, scaler, track
correction or regression residual across training races; none of those
fits is allowed here. Later source corrections must not rewrite an earlier
as-of view. May results collected in October are not May pre-race examples,
and a newly designed time feature is not retroactively a sealed A24/B34
input.

### Diagnostics and stopping rules

Report the funnel from all observations to supported starts, known layouts,
valid operands and usable reference groups, by the 18 observed
venue/distance groups. Distinguish cell coverage, eligible-start coverage
and future target coverage. The last remains unknown while future
dates/rosters/N are unset.

Inspect descriptive variation, precision, deterministic redundancy with
rank, same-horse/same-venue/same-distance repeat observations and history
aging. Do not fit regressions/PCA, rank features by target correlation,
search lookbacks, or treat past time/rank association as future skill.
May-only support will age out of a finite lookback; report this limitation
without extending the window to improve coverage.

Use synthetic cases for wrong checkpoint meaning, distance-dependent
column order, zero denominators, overlapping sections, positive-time
disqualifications, wrong horse/event, missing reference runners and late
source versions. Row permutations must not change results; withheld
observations must never enter reference groups; later evidence must not
change an earlier as-of view.

Stop an invalid audit on changed source hashes, identity duplication or
missing identity, forbidden October outcome access or any fitting path.
Withhold an ambiguous mapping/derived value on unexplained endpoint,
unit or arithmetic conflicts. All-missing, constant or deterministically
rank-equivalent quantities establish no new information in that scope;
insufficient repeat/PIT evidence leaves transferability unknown. Stop the
bounded study when every original observation has a fixed status and all
unresolved issues are listed, not when a favorable result appears.
Do not invent a coverage threshold that automatically approves training.

Deliver only a small endpoint mapping, a full-population
arithmetic/eligibility/variation report, and synthetic time-boundary
checks. Even successful completion would establish feasibility, not
predictive improvement. Any new fitted candidate needs separate approval
and later independently preregistered future evaluation.

## Honest future conclusions

On a fully resolved frozen population of N races, H hits give H/N.
A model below 70% has failed the target on that block even if it beats a
comparator; one block does not establish a universal ceiling or guarantee.
Pending/undefined outcomes or unresolved population completeness prevent
the complete accuracy claim under the existing policy.

If only V races have valid timely predictions, H/N cannot exceed V/N
when all targets and N are resolved. In contrast, time-feature coverage
is not an accuracy ceiling: other features might support a correct
prediction when time history is absent. High source coverage also does
not demonstrate skill. The 70% goal remains unmet.

## Reproduce the synthetic check

From the repository root:

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B \
      -m pytest -q -p no:cacheprovider \
      packages/scripts/autoresearch/tests/test_condition_training.py \
      -k 'marginal_selection or probability_repackaging or common_race_score'

Expected: seven passed cases. This is mathematical and selector-contract
verification only. It must never be counted as empirical model validation.

Local regression: **211 tests passed** across `test_condition_training.py`,
`test_condition_forward.py` and `test_condition_outcome_accounting.py`;
Ruff checks and formatting passed. Published M0/API27 predictions,
A24/B34 saved models and fit receipt, and the empty forward-review
registry retain their prior SHA256 values. No production code changed.
Required CI and normal-merge evidence are recorded on the PR.
