# Fit The Reviewed PDF/API26 Cohort

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

Turn the actual pre-race committed October 10/11 archive into two small trained
research models. A cohort is the explicitly selected collection of training
races, not the future national evaluation universe. M0 uses fixed API26 fields;
M1 adds the existing PDF block. Both must consume identical runners and labels.
The user can inspect the complete 28-race selection ledger, frozen inputs,
consumed matrices, development predictions and completed model receipts.
Nothing here certifies the 70% goal, replaces the champion or submits predictions.

## Progress

- [x] (2026-10-11) Revalidate PR74 merge, clean isolated checkout, actual source evidence and completed Pro advice.
- [x] Verify installed sklearn 1.9.0 uses l2_reg_strength=1/(C*sum(weights)); official API26 catalogue lists selected field meanings.
- [ ] Implement source-only projection, pinned result replay and full inventory selection ledger.
- [ ] Review actual frozen corpus and register its exact restricted research recipe before fitting.
- [ ] Fit fixed M0/M1 date replay and full-cohort models; verify saved-model inference and receipts.
- [ ] Run focused and shared regressions, publish evidence, push and ordinarily merge after required checks.

## Context and Orientation

Use the isolated checkout `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`.
Original PDF/API26 bytes live under the owner's read-only checkout
`/Users/coyasong/Developer/coyasong/kra-analysis/.cache/autoresearch/race_card_pdf_snapshots`.
PR74 established the live GitHub PR61 merge/document/plan/bundle/raw chain through
`packages/scripts/autoresearch/prerace_hash_witness.py`. The input bundle under
`.cache/autoresearch/race_card_pdf_bundles/20261009T165933.854898Z_51a041eda9e6`
has 28 inventory races, 27 eligible feature sets and 282 runner rows.
Its input-plan hash is `0ac4a309d07901d6f4da8c4503c937fee9529fb5e05871cfdcd5252116a52be0`;
bundle hash is `8061a185401bf72c4bfee2751529acb164b695eb2985dbf4d6a43e187a8ecdd6`.
PR61 merged at 2026-10-09T17:08:16Z, before all captured scheduled T30 cutoffs.
Trust GitHub HTTPS metadata, hash preimage resistance and original official-source
collectors, without claiming independent KRA authentication or exact capture time.

Result plan `.cache/autoresearch/prior-results/population-plan.json`, SHA256
`4c3385228e1f80d5a0cd609d9a78b236e3a3d53efdc8676920276039455cfb03`, pins API214
captures. Existing `kra_result_snapshot.py` returns verified normalized rows.
`kra_result_population_audit.inspect_top3` identifies ordinary consecutive ranks.
Use the captured official version for labels, not an assertion of eternal finality.
All results have already been seen; the October 11 replay is development only.

## Decision Log

Decision: use a new restricted research-only contract, preserving the unchanged
legacy production gate and zero production approvals. Exact reviewed frozen bytes
and the implementation/environment must match before any fit or model output.
Rationale: the new sources do not satisfy the legacy multi-source feature schema.
Date/Author: 2026-10-11, Codex, implementing the completed Pro recommendation.

Decision: conservatively select only ordinary consecutive-rank observations with
complete matching (gate, canonical horse ID) rosters, explicit raw-ID agreement,
and source eligibility. Keep all other inventory records with reasons. Freeze
the policy before model outcomes; do not expand it based on measured performance.
Rationale: this yields a clear initial label version without guessing exceptional
statuses. It is training selection, never a reduced future evaluation denominator.
Date/Author: 2026-10-11, Codex.

Decision: API fields are age, wgBudam, rating, rcCntT, ord1CntT, ord2CntT,
ord3CntT, with explicit missing flags. M1 adds all nine existing PDF numeric
fields, their missing flags and training_summary_truncated. Rate units are fractions.
Raw identity, ilsu, odds, outcome codes, filenames and timestamps are not features.
Use median imputation with zero for entirely missing training columns, train-only
standard scaling, L2 logistic regression, lambda=1, sample_weight=1/field_size,
C=1/training_races, lbfgs, tol=1e-8, max_iter=2000, seed=42, no class weighting.
Rank scores descending, then gate and canonical ID ascending, exactly three.
Date/Author: 2026-10-11, Codex, before fitting.

## Plan of Work

Add `restricted_cohort.py` for the contract, verified source projection, pinned
result join, source/label ledger and corpus preparation CLI. Reuse strict live
publication acquisition and raw replay, consuming returned verified row objects
and the already retained original bundle bytes rather than unverified rereads.
Add `restricted_ablation.py` for canonical research review admission, fixed model
fitting and JSON inference artifacts. Keep dependencies in the existing environment.
Save corpus first, inspect real source fields and labels, then manually add a
positive exact-recipe entry in `data/contracts/restricted_training_review_v1.json`.
Do not write a review before examining actual evidence. This registry cannot
authorize the old production training path or arbitrary synthetic fixtures.

## Milestones

First produce a frozen corpus and full ledger from actual raw replay. Verify
source hashes, feature nulls/ranges, runner identity, result version and exclusions.
Second approve those exact bytes for restricted research, then train October 10
and predict October 11 once per model; refit the same recipes on all selected
training races. Third verify numeric matrices, deterministic reload inference,
full development membership and exact artifact hashes before publishing.

## Concrete Steps

From the isolated root, use `PYTHONPATH=packages/scripts .venv/bin/python -m
autoresearch.restricted_cohort` with the original plan/bundle, owner's archive root,
the pinned result plan and a fresh `.cache/autoresearch/restricted-cohort` output.
Then use `autoresearch.restricted_ablation --corpus <frozen-corpus.json>
--output-dir .cache/autoresearch/restricted-models` after the canonical review exists.
Exact commands, hashes and counts will be recorded in the research report.
Run `.venv/bin/python -m pytest` on the two new test files with `-o addopts=''`,
plus existing witness/replay/result/training suites. Run Ruff lint/format and
`git diff --check`. CI must actually execute model tests with sklearn present
and source tests with the PDF extra present.

## Validation and Acceptance

Changed raw bytes, missing keys, duplicate identities, wrong labels, noncanonical
IDs, altered cohort or implementation and absent approvals must fail before fit.
Labels must not influence feature projection. M0/M1 consume the same runners,
labels and split; imputation/scaling learn only from training rows. All-null
columns remain present. Nonconvergence is failure, not a parameter search.
Persist actual X/y/weights and row identities and hash their bytes; bind saved
model bytes to the same source review in a completion receipt written last.
No partial run may look complete; no existing artifact is overwritten.

## Idempotence and Recovery

Use unique output directories. Retain original source files and failed runs.
If code changes after review, reject the old implementation pin and explicitly
review a new recipe; do not rewrite original capture timing or feature files.
The user's dirty checkout is read-only. No training or evaluation subset may
change the full frozen future universe or the goal definition.

## Surprises & Discoveries

The API26 source roster matches all 27 feature-eligible result rosters, even where
a later schedule count differs. The conservative ordinary intersection is 20
races/209 rows, 13 on October 10 and seven on October 11, pending full review.

## Interfaces and Dependencies

Use existing JSON/hash utilities, raw replay and inspect_top3. Model fitting uses
installed sklearn SimpleImputer, StandardScaler and LogisticRegression. Save
portable JSON parameters and verify their score reconstruction against sklearn.
The installed solver explicitly divides penalty by C times total sample weight;
equal per-race weights therefore require C=1/R for fixed lambda=1.

## Outcomes & Retrospective

Implementation and actual fits are pending. The 70% goal remains unproven.
The owner subsequently requested the server configuration first. That decision
is recorded in `docs/research/2026-10-11-forward-server-configuration.md`;
provisioning and payment are not performed. Resume the fixed local model work
from the first unchecked milestone without changing its pre-fit policy.

Revision: initial fixed experiment and conservative cohort policy recorded before
training, following the completed Pro advice and authoritative PR74 evidence.

Revision: preserve the not-yet-executed model plan while answering the owner's
server-configuration request first; no fit, approval or model output occurred.
