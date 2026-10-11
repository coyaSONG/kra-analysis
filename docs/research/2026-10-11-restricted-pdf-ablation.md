# Restricted API/PDF Model Experiment

## Status And Scope

Source and current official label-version review completed before fitting on
2026-10-11. This approves exact frozen bytes for restricted research only, not
production promotion or a claim of 70% future race-level success. Four actual
model fits completed at 2026-10-11T12:54:57.269401+00:00. Both arms hit one of
seven previously observed development races (14.3%); no PDF improvement was
demonstrated, and no champion or production change is justified.

The completed ChatGPT Pro consultation recommended this restricted experiment;
it did not independently inspect the local raw files. Codex performed the raw
replay, source projection, identity join and label-version review described below.
No new Pro consultation is claimed here.

## Frozen Evidence

All paths below are relative to the isolated research checkout. Original raw
source files remain in the owner's read-only checkout. No raw data, credentials
or local cache contents are included in Git.

- Corpus: `.cache/autoresearch/restricted-cohort/20261011T124748.785378Z_ebdf29deaaa9/corpus.json`.
- Corpus SHA256: `d6598f244d6a7b7bc5e65846a4c79ee6ac96ad278b89a14268de332e77526ae2`.
- Implementation/environment SHA256: `a8c36b3114dde88f28302eeb9ecd376f638ec4e70eab34cc102cbc73b0469572`.
- Fixed recipe SHA256: `fe0cd43d1ac6d36fd6c255644f12d93bdb0b2e7dbdbf3ea9a218df1b5656035f`.
- Source plan SHA256: `0ac4a309d07901d6f4da8c4503c937fee9529fb5e05871cfdcd5252116a52be0`.
- Feature bundle SHA256: `8061a185401bf72c4bfee2751529acb164b695eb2985dbf4d6a43e187a8ecdd6`.
- Official-result plan SHA256: `4c3385228e1f80d5a0cd609d9a78b236e3a3d53efdc8676920276039455cfb03`.
- Canonical approval: `data/contracts/restricted_training_review_v1.json`.

The corpus retains the implementation source hashes, exact Python and dependency
versions, source witness ledger and six replayed API214 result-version pins.
GitHub PR61 merged commit `f794ffc24414117420004ca45bd8ae20a04385db` at
2026-10-09T17:08:16Z. Its committed archive document binds all 28 raw chains
before their captured scheduled T30 cutoffs. This trusts GitHub HTTPS metadata,
hash preimage resistance and the original official-source collectors. It is not
independent KRA authentication, an exact capture-clock certificate, a final roster
certificate or proof that predictions were submitted before the races.

Live witness reacquired at 2026-10-11T12:47:49.395933+00:00; raw files and all
result captures were replayed from pinned bytes. Current implementation still
matches the frozen corpus. Numeric and identity checks passed before approval.

## Source And Label Review

The inventory keeps all 28 races. There are 27 source-eligible races; the fixed
ordinary-consecutive-rank/full-observed-roster policy selects 20 races and 209
runner rows. October 10 contributes 13 races/133 rows; October 11 contributes
seven races/76 rows. All selected (gate, canonical horse ID) pairs match the
captured result roster exactly. Leading-zero string IDs and integer IDs are
normalized while preserving raw identity; duplicate canonical IDs are rejected.
Every selected top three has unique official ranks 1, 2 and 3 and valid elapsed
times. Equal rounded elapsed times do not override official rank order.

This is the captured official result version, not a guarantee against later
corrections. Results were collected after both days. The date split is therefore
a post-hoc development replay, NOT a contemporaneous walk-forward test. Both
dates had already been inspected. Selection conditions on ordinary outcomes;
neither its membership nor its accuracy can replace the complete future universe.

Retained exclusions, fixed before fit:

| Race | Reason |
| --- | --- |
| 20261010_1_1 | Void/unresolved result; no usable ordinary top three |
| 20261010_1_6 | Nonconsecutive/unresolved result ranks |
| 20261010_1_7 | Nonconsecutive/unresolved result ranks |
| 20261010_2_2 | Nonconsecutive/unresolved result ranks |
| 20261011_1_10 | Nonconsecutive/unresolved result ranks |
| 20261011_1_3 | Nonconsecutive/unresolved result ranks |
| 20261011_1_9 | Nonconsecutive/unresolved result ranks |
| 20261011_1_8 | Pre-race PDF/API name-prefix join incomplete |

No runner is removed from a selected race using its outcome. A later schedule
count is not substituted for the original observed roster size.

## Fixed Features

API26 fields follow the [official entry-information catalogue](https://www.data.go.kr/data/15058677/openapi.do).
Burden weight is in kg; rating follows the [KRA rating description](https://race.kra.co.kr/raceoper/RaceoperView.do?Act=13&Sub=6&meet=1).
PDF values use the existing reviewed parser contract and captured horse panels.
Trainer win percentage is converted to a fraction, not mixed with percentage
points. Counts are nonnegative integers. Null, empty and hyphen values remain
missing; literal zero remains observed zero. Missingness indicators are explicit.

| Numeric field | Observed / missing | Observed range |
| --- | --- | --- |
| age (years) | 209 / 0 | 2-11 |
| wgBudam (kg) | 209 / 0 | 51-60 |
| rating | 193 / 16 | 0-77 |
| rcCntT (career starts) | 209 / 0 | 0-135 |
| ord1CntT, ord2CntT, ord3CntT (career place counts, each) | 209 / 0 each | 0-12 each |
| training_count | 209 / 0 | 5-16 |
| training_minutes | 209 / 0 | 54-273 |
| training_window_days | 57 / 152 | 14 |
| training_gu_count | 152 / 57 | 6-31 |
| training_seup_count | 152 / 57 | 0-3 |
| swimming_count | 152 / 57 | 0-11 |
| swimming_laps | 152 / 57 | 0-55 |
| trainer_wins | 145 / 64 | 2-682 |
| trainer_win_rate (fraction) | 145 / 64 | 0.03-0.18 |

PDF missingness reflects heterogeneous panels and may encode venue/layout.
This experiment cannot establish a causal benefit from training or swimming.
Horse identity, names, timestamps, filenames, odds, results and `ilsu` never
enter the feature matrix. M0 has seven API values plus seven missing flags (14).
M1 adds nine PDF values, nine flags and one truncation flag (33 total).

## Fixed Model And Validation

Use train-only median imputation (all-missing columns kept as zero), train-only
standard scaling and L2 logistic regression with lambda=1. Each runner gets
weight 1/observed roster size, so each race has total weight one. For installed
sklearn 1.9.0, C=1/number of training races implements the declared penalty.
The solver is lbfgs, tolerance 1e-8, at most 2,000 iterations, seed 42, intercept
enabled and no class weighting. No hyperparameter search or outcome-based retry.
Rank descending linear score, then ascending gate and canonical ID; emit exactly
three different horses. These scores are NOT joint three-horse probabilities.

Fit October 10, predict October 11 once per arm, then refit each unchanged recipe
on all 20 selected races. Save four portable JSON models and their four consumed
matrices. Verify score reconstruction against sklearn and saved-model inference.
Hash the artifacts, save the paired development report and write the completed
receipt last. Inference itself needs no labels. Production approvals remain
unchanged and empty; models are not promoted or assigned to the B0 forward arm.

Pre-fit validation: 279 focused/shared tests passed, including changed-raw-byte
rejection, exact review admission, label-independent features/inference, train-only
statistics, identical M0/M1 rows/labels/weights, unit-L2 objective gradient,
nonconvergence rejection and immutable completed artifact receipts.

## Results And Next Step

| Fixed arm | Development training | Development exact hits | Full refit |
| --- | --- | --- | --- |
| M0: API-only, 14 columns | 13 races / 133 runners | 1 / 7 (14.3%) | 20 races / 209 runners |
| M1: API plus PDF, 33 columns | 13 races / 133 runners | 1 / 7 (14.3%) | 20 races / 209 runners |

The seven development combinations all differed between arms. M0 alone hit
`20261011_1_11`; M1 alone hit `20261011_1_4`; both hit zero; neither hit five.
Do not combine their successes into a fictitious single-model 2/7 result.
These are exact unordered three-horse hits, not per-horse precision or top-k
coverage. Seven selected, already observed races are insufficient to estimate
future generalization or select a best model. The full refits are not evaluated
on their training races as evidence of performance.

Development M0/M1 converged in 10/11 iterations with C=1/13; full M0/M1 in 9/11
iterations with C=1/20. Independent post-fit replay verified all nine artifact
hashes, identical M0/M1 identities/labels/weights, identical first 14 transformed
columns, saved-model development predictions and the hit counts above. No
hyperparameters, feature membership or cohort selection changed after results.

Run directory:
`.cache/autoresearch/restricted-models/20261011T125457.212167Z_4113cd1060f9`.
Completion receipt SHA256:
`70cf1f7de5a51ae68f4706b6349686276c6bf23978d37f116072bcd61a7ef69b`.
Canonical review bytes SHA256:
`d29499f0b9e409c25e6446ce8d4fe7abcbab71101af0399b72377c3610a5e60f`.

| Artifact | SHA256 |
| --- | --- |
| development_M0_model.json | `6881c6f8efd9743df1c52fbe79e6def4d5795fbd276172996c52c69dabfa691e` |
| development_M1_model.json | `25efb819ce2b472e77fd4e8643988bd50ba5bf7becb47978fed3c9e1a53385e0` |
| full_M0_model.json | `0c0078fb513d4acc2695427475b91668f20441bfab1f4ce05e0418277c8bbb74` |
| full_M1_model.json | `caa7bfd74db5ae9adbee35f3b2bbbd2d4c5d2015f5f9e00438ef1ab951a845da` |
| development_M0_matrix.json | `a7a5d854bb7bee153fd2eb7ae8464d5e59c54bec04dbabd216e89a4308a8f886` |
| development_M1_matrix.json | `4d19eadee89752afe98cc560708cfa27c7704871b78f9aec8e57fc1a23ea8909` |
| full_M0_matrix.json | `59125a8ba9dfaa8ea69fe647324ec4d67c54dcd7b75f63199812e9e759c13a7f` |
| full_M1_matrix.json | `8328d0ee652a6ea00859c5e2063dcf9dcee41392c8b785287787953906c278de` |
| development_report.json | `87cf2c28e0b5b10b5691b022521f81c1da3c4a0d1073780dd2f8f12762a8202d` |

Confidence assessment: share with caveats as an engineering/research result;
not suitable for selecting a production champion or claiming future accuracy.
The negative ablation result is retained, not hidden or re-tuned away. The next
research priority is broader pre-race source coverage and an independent future
evaluation, not optimizing these seven development outcomes. Any later
challenger must receive a separate forward contract/arm; it cannot reuse B0's
identity or change the national denominator.

The complete frozen future race universe and pre-race durable prediction logs
remain required for the 70% objective. Server
configuration is separately recorded in `2026-10-11-forward-server-configuration.md`;
paid provisioning awaits owner approval. This experiment does not resolve that
operational dependency.

## Reproduction

Run from the isolated checkout with the exact corpus, implementation and recorded
environment. Rebuilding a corpus creates new collection metadata and therefore
requires a new explicit review, not an automatic approval update. The production
training gate does not consume this restricted review file.

```sh
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.restricted_ablation \
  --corpus .cache/autoresearch/restricted-cohort/20261011T124748.785378Z_ebdf29deaaa9/corpus.json \
  --output-dir .cache/autoresearch/restricted-models
```

The command creates a fresh directory; it does not replace the original run.
Completion timestamps differ on replay. The original receipt and artifacts
above remain the evidence for this experiment.
