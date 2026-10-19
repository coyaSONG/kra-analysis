# Separate A24/B34 Execution Approval

## Decision And Authority

The owner explicitly requested review of PR111's exact inputs, code and
environment, a separate approval record, testing and normal merge, followed by
one fit per arm only if all conditions pass. This record implements that
conditional authorization for **research-only development fitting**. Codex
performed the review; it is not an independent human review or a new ChatGPT
Pro approval. PR110's completed methodology consultation remains distinct.

Approval is limited to requirement SHA256
`2c6c2251bd718d4316148aaecd0c53270e37dfd64e0ef1d82d9cbb0fcaf1f87b`.
The complete [machine-readable requirement](approvals/2026-10-19-condition-training/requirement.json)
publishes the exact 58 input paths/hashes, 163 source/lock hashes, ordered
columns, population, label/weight/feature digests and environment fingerprint.
It contains no credentials or full feature matrices. Raw archives remain local.
The [separate registry](../../data/contracts/condition_training_reviews_v1.json)
must match committed HEAD and fetched origin/main before even preprocessing.
This approval is not effective merely because its file exists locally.

The reviewed implementation is PR111 merge
`15eed4775742c9190244b646752c0ba255b7f813`. Source bytes were checked against
both HEAD and origin/main; no numerical or admission code changes accompany
this authorization. The current requirement equals the preserved pre-approval
inspection byte-for-byte. No reservation/output directory existed at review.

## Evidence And Limits

The [PR108 source audit](2026-10-18-development-source-audit.md) and
[PR109 baseline audit](2026-10-18-baseline-lineage-audit.md) reconstruct the
entry, historical, condition-memory and original recency lineage. Their exact
audit bytes are pinned again. The review retains their limitations: local
capture clocks are not independent timestamps; HTML-only support, unknown
conditions, incomplete career history and historical event-time availability
are not made certain by an approval. These limitations permit this local
development comparison, not an independent retrospective validation claim.

The current read-only admission checked every identity and all 18,156 feature
cells against the original sealed matrix and packets, without fitting:

| Gate | Reviewed result |
| --- | --- |
| Frozen population | Exactly 50 races, 534 unique appearances; no dropped or expanded joins |
| Labels | 150 positive / 384 negative unique-top-three membership labels |
| Selected result version | `0cf7be483e1089ba55db78f70c51c9a6dbcaf8738847460f469ee11901ac0cbb` |
| Cohort | `c25db29f0ba78cd3e7ab49c04950fcde3f3a12686ce4aad1ba69b33fb2616e03` |
| Matrix | `7277897731011c64706f427cd7733444a5450767d312dabe8293a67c35a788a1` |
| Weights | Each race sums to one; total 50; no class rebalance |
| Exceptions | All four original unranked observations retained; no rank imputation |
| Missingness | Rating 32; each of four recency fields 79; older-career form 144 |
| Input clock | Matrix creation precedes every pinned race cutoff |

Exception membership-zero follows absence from a verified three-ID target,
not exception text alone. Their ranks remain unresolved. All targets are
`unique_top3_observed`, not irreversible official finality. Corrections need
new linked versions; they cannot overwrite this result version or trigger
a repeat fit. Original M0/API27 commitments and false historical cohort flags
remain unchanged. No KRA/API request or outcome refresh occurred in this review.

## Exact Code And Runtime

The four PR111 modules were reviewed for complete-population validation,
outcome/feature separation, fixed recipe, canonical selection, repository-only
admission and durable single-use execution. The shared Git-directory reservation
precedes preprocessing, and each estimator attempt is recorded before fit.
No alternate output directory, review ID or worktree grants a new budget.
Nonconvergence, exhausted iterations, nonfinite output, changed bindings or
failed replay rejects the pair. Failure consumes the reservation; no retry.

A24 uses the original first 24 columns; B34 adds the fixed ten memory columns.
Both use median imputation, retained empty columns, unweighted StandardScaler,
L2 logistic lbfgs C=0.02, tolerance 1e-8, max_iter=2000, seed 42, intercept and
no class weighting. No tuning, deterministic refit or subset selection is
authorized. Shared preprocessing must match exactly; disk replay must match
scores within absolute 1e-12 and all selected sets exactly.

Runtime: CPython 3.13.13, NumPy 2.5.1, SciPy 1.18.0, scikit-learn 1.9.0,
macOS 26.5.1 arm64, Apple M1 Max, ten logical CPUs. NumPy/SciPy report
Accelerate; its version is unknown, not invented. libomp hash and ten OpenMP
threads, all installed package versions and six unset thread environment
variables are recorded in the requirement. A synthetic-only fit confirmed
the environment fingerprint stays unchanged after fitting. It did not load
the real cohort and does not consume its budget. Seed alone does not promise
bitwise reproducibility on another environment.

## Execution And Publication Conditions

Run the synthetic admission/runner and existing evidence/ablation/input tests,
Ruff lint/format and required CI checks. Normally merge this separate approval,
fetch origin/main, revalidate the exact requirement and registry, and confirm
both lifetime reservation and fixed output destinations are absent. Only then
invoke `autoresearch.condition_training.run()` once in the same local runtime.
Its A24=1/B34=1 budget is a maximum, not permission to repeat a failed attempt.

Preserve the final receipt, both models and consumed inputs, approval bytes,
per-arm attempt ledgers and completion hash. Verify without refitting. An
incomplete pair must be reported as failed/incomplete, never a successful
single-arm comparison. Actual fits at the time of this review: **zero each**.
The later execution report must state actual attempted/completed counts.

Compare both arms on all 50 races only as **in-sample development results**.
The recipe was chosen after outcomes and the same labels train the models.
No accuracy or confidence interval here estimates prospective generalization;
534 appearances are not 534 independent race trials. Keep original prospective
M0/API27 0/50 versus 0/50 results separate. No production promotion or 70% goal
completion is authorized. A future complete block needs its own protocol and
timely public predictions before outcomes; dates/population are not registered
by this approval.

## Pre-Merge Verification

The two portable approval-manifest tests and 173 existing admission, runner,
evidence, restricted-ablation and input tests pass: **175 tests in 2.10s**,
with 15 existing joblib/NumPy deprecation warnings. Ruff lint passes; its
initial format check requested formatting of the new tests, which was applied.
The actual admission rejected the local record with `uncommitted_approval`;
both real destinations remained absent. CI/merge are still execution gates,
not inferred from these local checks.
