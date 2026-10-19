# A24/B34 Single-Fit Development Results

## Decision

Both approved estimator fits completed **exactly once**, without retry or
parameter changes. B34 matched one more race than A24 on the same 50 races
used for fitting. This is **in-sample development evidence only**, not an
independent improvement test, a replacement for M0/API27, or a production
promotion. The 70% goal remains unmet.

| Arm | Fits attempted/completed | Exact hits | Misses | Pending | Undefined | Exact accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A24 | 1 / 1 | 4 | 46 | 0 | 0 | 8% |
| B34 | 1 / 1 | 5 | 45 | 0 | 0 | 10% |

B34 minus A24 is **+2 percentage points**. Paired counts are both hit **3**,
A24 only **1**, B34 only **2**, neither **44**. The models select identical
three-ID sets in 20 races and different sets in 30. Every race remains in the
denominator, including the four races with unranked runner exceptions.

There are only 50 races from one three-day block, with 534 runner appearances,
not 534 independent prediction trials. The recipe was fixed after observing
these outcomes, and the same labels were used for fitting and comparison.
An ordinary binomial confidence interval or paired significance test on these
training predictions would not quantify prospective generalization; none is
claimed. A one-race difference does not establish future superiority.
No subset, partial overlap, OR-union or loss metric replaces exact-set accuracy.

The original pre-cutoff [M0/API27 evaluation](2026-10-18-full-block-paired-results.md)
remains 0/50 versus 0/50, with 50 misses, zero pending and zero undefined targets
per model. This new in-sample 8%/10% result is not an 8/10-point prospective
improvement over those old models. No original prediction was replaced.

## Approval And Execution

The owner's conditional request was implemented in the
[separate review](2026-10-19-condition-execution-approval.md), not inferred from
PR110's methodology advice. [PR112](https://github.com/coyaSONG/kra-analysis/pull/112)
normally merged at **2026-10-19T13:12:08Z** (22:12:08 KST), commit
`6dd8e49f216017fa031ca30b34613d8642467eaf`, after required Python Checks passed.
Scripts Checks, API Docker Build and Gitleaks also passed. Security Checks
failed on the same 17 pre-existing Python dependency advisory rows, verified
against the preserved baseline; subsequent security steps were skipped.
No dependency file changed and no protection bypass was used.

After fetching origin/main, the actual approval registry matched both HEAD and
main, all original inputs and implementation/runtime fingerprints matched, the
checkout was clean, and both fixed destinations were absent. The existing
runner was invoked once. Its durable shared-cohort reservation was created
before preprocessing and each arm's attempt was recorded before its fit.

Execution began **2026-10-19T13:12:57.427785Z** and the successful receipt was
created at **13:12:57.857303Z** (22:12 KST). Both optimizers completed in 11
iterations with no captured warnings. Common-24 imputer/scaler statistics
match exactly, saved inference scores match within absolute 1e-12, and all
canonical selected sets replay exactly. Original hashes are unchanged.
No exception row or race was removed; labels remain membership, not ranks.

The fixed reservation is under the repository's common Git directory at
`condition-training-attempts/c25db29f0ba78cd3e7ab49c04950fcde3f3a12686ce4aad1ba69b33fb2616e03`.
The local consumed matrices, scores, models and final receipt are under
`.cache/autoresearch/condition-training-v1/` with the same cohort suffix.
The lifetime budget is consumed. Do not delete it, retry, tune or use another
clone/directory to fit this pair again. Later source corrections require new
linked evidence and review, not an automatic second fit.

## Saved Evidence

Public [comparison](experiments/2026-10-19-condition-training-v1/comparison.json)
contains all 50 targets and both canonical predictions. Public model snapshots
([A24](experiments/2026-10-19-condition-training-v1/A24-model.json),
[B34](experiments/2026-10-19-condition-training-v1/B34-model.json)) and the
[execution receipt](experiments/2026-10-19-condition-training-v1/receipt.json)
are exact canonical copies of the saved outputs. Full consumed matrices stay
local, bound by the receipt hashes. They are not fresh pre-race commitments.

| Artifact | SHA256 |
| --- | --- |
| Approval requirement | 2c6c2251bd718d4316148aaecd0c53270e37dfd64e0ef1d82d9cbb0fcaf1f87b |
| Approval registry bytes | 127d1c5d727831815f86077850c2d3202b2e449b36daa138c1331c2d4796f04b |
| Execution receipt | 3587c948913c82cc9c0b8c5e64161ef29794ed22a80d08425300e924834aa96e |
| A24 model | 69f655fd005b59313d0a23dbf44759510c937ef403e8ac4fd844ea67494d635e |
| B34 model | c03972a447c2a36603717a7107b751f23d0fff08cb204565b68215f955ef16e0 |
| A24 consumed data | 677e84526815066d2ef72bc63aa1daacf148c66f6e99831526e9cbc0d23893a5 |
| B34 consumed data | e74fddb7c4b31ec3ef05e8cfad4b1b8cc31c60164672bcd9ffd458d72f421e9e |
| Development comparison | 34816e00bf57715f9cac56bc42478ace4d288e8e2d7d9b8620d4ba3be2845bbf |
| Group diagnostic | 5b34bc2c6660d9a52e507ad1b83034742ba1c599935872e94efa10ffb505bf29 |

An offline companion, `.cache/autoresearch/verify_condition_training_20261019.py`
(SHA256 `c64dde7ce6b733674f9a8913e3bb79b01c624582bd0ac4e83447c840969c8328`),
rechecked the completion ledger, per-arm attempts, all model/consumed hashes,
original inputs, full row order, X/y/weights, exact constructor parameters,
common statistics and score replay. Separate row-label arithmetic and explicit
sorting agreed with target-set comparison for all 50 races. It never calls
fit. It refuses an existing publication destination; do not rerun it there.
Its first Ruff check misclassified imports outside the package; explicitly
declaring `autoresearch` first-party passes without altering archived bytes.

Surrogate diagnostics (not the goal): A24 weighted-mean binary log loss
0.575677314657, L2 penalty 0.007835142351, objective 0.583512457008;
B34 loss 0.569659689882, penalty 0.010140502358, objective 0.579800192240.
The learner optimizes a binary surrogate, not joint exact-set probability.
Added correlated columns also change L2 representation; this is not a causal
estimate of the ten memory features.

## Failure Diagnosis

The [diagnostic](experiments/2026-10-19-condition-training-v1/diagnostic.json)
joins the already pinned PR107 entry-derived distance/grade/venue metadata to
all 50 rows. Source diagnostic SHA256 is
`74a4959370c68070afdd1cefc8c9fd34f71f5b539839402f522fef2e3e918390`.
All targets match and each grouping reconciles to 50 races and 4/5 hits.
No new source request, input replacement or training occurred.

| Venue | Races | A24 hits | B34 hits |
| --- | ---: | ---: | ---: |
| Seoul | 21 | 2 | 2 |
| Jeju | 14 | 1 | 1 |
| Busan | 9 | 1 | 1 |
| Yeongcheon | 6 | 0 | 1 |

All three hit/miss disagreements are 1200m races. A24 alone hits Seoul
October 17 R5 (domestic class 5); B34 alone hits Seoul October 18 R8 (domestic
OPEN) and Yeongcheon October 18 R1 (domestic class 5). Aggregate 1200m hits are
1/15 versus 2/15; at 1400m both miss all ten. Domestic class-5 totals are
1/9 versus 1/9 despite different hit races; domestic OPEN is 0/2 versus 1/2.
Distance strata contain 2-15 races and grade strata 1-11, too small and
outcome-exposed to support selecting a distance/grade-specific policy.

Among 15 races whose three target horses all have recent similar-history
support, each arm hits two and misses 13. Missing support alone therefore
does not explain the failures. Across other support strata changes go in both
directions. The next hypothesis is that the fixed memory bundle may alter
borderline top-three rankings, but its apparent net gain may be sampling
variation or a regularization representation effect. Keep both stored models
unchanged; examine this hypothesis on future full populations, not by tuning
thresholds or reweighting these same races. Groups are diagnostic only.

## Future Validation Draft

No future dates, population, stopping horizon or new goal have been registered.
This is a preparation plan, not permission to use whatever future subset looks
favorable. Before the next experiment:

1. Publish a separate prospective protocol with explicit dates/venues, every
   official scheduled race, schedule-change/cancellation rules and source
   availability requirements. Choose the horizon and sample-size rationale
   before seeing future outcomes; report the achieved race and week counts.
   Do not reset the October block or stop early after an apparent win.
2. Treat A24 as the reference and B34 as the fixed candidate, while preserving
   both model hashes above. Neither is promoted from this comparison. Freeze
   the inference adapter, exact columns, sources, environment and failure
   treatment; test missingness and canonical selection using synthetic data.
   Reuse stored imputer/scaler state without fitting or tuning either model.
3. Prefer a full-block input freeze before its first cutoff. State explicitly
   whether prior-block results may enter later feature histories; no within-
   block outcome updates under that freeze. Preserve source receipts, clocks,
   hashes, missingness and identity/roster checks. Unknown source availability
   blocks admission; it is not evidence of no races.
4. Save and publicly witness one unordered three-horse prediction per arm per
   race before the registered cutoff. Keep the entire frozen population.
   Late/missing/invalid predictions are protocol failures, not silently dropped
   races or backdated forecasts. Freeze their scoring treatment in the protocol.
5. Apply the versioned official-result policy for ties, cancellations, undefined
   targets, corrections and conflicts. Unknown results remain pending, never
   zero-accuracy failures. If whole-population accuracy is undefined, report
   counts and the limitation, not a substituted subset accuracy.
6. Report full-population accuracy and B34-minus-A24 paired difference, all four
   paired cells, coverage and unresolved counts. Predeclare uncertainty and
   stopping methods that account for race/week dependence. An initial single
   week is descriptive, not evidence of stable superiority. Promotion needs
   a separate decision supported by genuinely prospective evidence.

Readiness gates still needed: a new official schedule, an explicit prospective
protocol (including horizon and uncertainty method), frozen inference plumbing
with tests and timely public commitments. No automatic retraining or automatic
advancement to invented dates is authorized by this result publication.

## Publication Verification

The three added public-artifact regression tests verify receipt/model hashes,
one completed fit per arm, no-promotion flags, canonical sets, every full-50
hit/miss comparison, paired arithmetic and complete diagnostic group joins.
Together with the existing suites, **178 tests pass in 2.12s**, with 15 existing
joblib/NumPy deprecation warnings. Ruff lint/format and diff whitespace checks
pass. These tests use saved public JSON and synthetic fixtures, not another
fit on the actual cohort. Result publication changes no approved runtime,
registry, dependency, original feature packet or original prediction.
