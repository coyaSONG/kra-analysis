# Fit a separately reviewed API27 research model

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

Turn PR86's 27 pre-race API-only candidates (283 runners) into a reproducible,
separately reviewed research model, without changing the frozen 20-race M0 or
its October 16-18 evaluation. Refit means learning new coefficients with the
same numerical recipe, not selecting new parameters on already observed races.
The output is not proof of improved accuracy or of the 70% goal.

## Progress

- [x] (2026-10-11 21:05Z) Read existing training admission, raw replay and numerical helpers; isolated branch from PR87 merge.
- [x] (2026-10-11 21:09Z) Implemented candidate preparation, exact review admission and fixed refit; initial 36 tests passed. Added artifact readback and run-manifest evidence binding before real fit.
- [x] (2026-10-11 21:10Z) Replayed raw sources; exact corpus agrees with PR86. Reviewed 27 races/283 rows, sole void exclusion and fixed recipe; related 184 tests passed.
- [x] (2026-10-11 21:14Z) Final implementation fitted twice: five artifacts byte-identical, 11 iterations, 27 races/283 rows/81 positives; all 80 original M0 files unchanged and old loader still admits.
- [x] (2026-10-11 21:14Z) Final 41 new tests and six related suites passed (189 tests); lint/format passed; documented actual artifacts.
- [ ] Push and normally merge after required checks; final remote closure evidence belongs in the PR comment.

## Surprises & Discoveries

The old restricted trainer admits only its 20-race PDF/API corpus and old label
policy. Reusing or weakening that admission would conflate two different source
reviews. Its numerical `fit`, `input_matrix` and `predict` helpers can be reused
only behind a new explicit gate. The new model must not inherit the old recipe's
train/development date claims.

The first actual fit converged in 11 iterations but exposed an artifact
provenance ambiguity: the copied review JSON is canonically serialized while
the repository review may have different whitespace/key ordering. Preserve
both hashes with explicit names, add a noncanonical-review regression, and
supersede that preliminary fit without changing coefficients or tuning.

## Decision Log

Use API14 only: seven API values and seven missing flags. The ten recently
collected history columns were unavailable before these historical targets.
Keep the original 28-race inventory, including the void race, in the corpus;
only 27 unique-top-three observations train. This is training selection, never
a replacement evaluation denominator. Decision: Codex, 2026-10-11.

Reuse the original logistic numerical settings without search or development
scoring. Store the estimator inside a differently versioned API27 artifact,
with no automatic M0 promotion. A later future protocol is required for testing.
Decision: Codex, 2026-10-11.

## Outcomes & Retrospective

The separately admitted API27 model now exists and is reproducible. Two final
runs have model hash `5f33dfd1e45c493fc5edfd90a8250ac5e91bb841b29124e5988b657994dc17b4`
and matrix hash `83392f89bd95168701b4464e320e443df30be94acb44c49f4a8add339eb0f06b`.
Corpus hash is `5445e7ab3efc2125af52c32e40796220e1f2888e5d8becfd21d88da25d1e1cd3`.
The review approved training only. No improvement in future accuracy is known,
no original M0 files changed, and a separate paired future protocol remains.
Paid servers remain deferred. Remote verification/merge is pending.

## Context and Orientation

Work in `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`.
`packages/scripts/autoresearch/api_training_opportunity.py:prepare` replays the
original API26 input archive and frozen API214/official HTML outcome version.
It verifies PR61's GitHub publication before each original T-30 deadline (30
minutes before the captured start). GitHub bounds content existence, not KRA
authenticity. `restricted_ablation.py:fit` supplies the fixed logistic solver;
`restricted_cohort.py` supplies numeric and identity validation and fingerprints.
`local_m0_inference.py:load_model` must continue admitting the original model.

Inputs are ignored local artifacts: original plan and bundle under
`.cache/autoresearch/race_card_pdf_bundles/20261009T165933.854898Z_51a041eda9e6/`,
outcome plan `.cache/autoresearch/versioned-outcomes-20261012-plan.json`, and raw
archive rooted at `/Users/coyasong/Developer/coyasong/kra-analysis` (read-only).
The selected outcome version is not permanent settlement finality.

## Plan of Work

Add `api27_refit.py`, its tests, an exact JSON review under `data/contracts/`,
a research note and one Python CI step. Preparation saves the full raw replay
report plus a deterministic corpus without volatile witness retrieval metadata.
The corpus still includes all race records, source pins and label-version pins.
Preparation never approves training. Review pins exact corpus, implementation,
recipe, membership and row count. Fit repeats raw replay with a fresh publication
witness, compares corpus bytes, checks the committed review, then trains once.
Store model, consumed matrix, replay evidence and receipt in a new directory.
The receipt is last; partial output never proves completion.

## Concrete Steps

From the isolated checkout, use `PYTHONPATH=packages/scripts .venv/bin/python
-m autoresearch.api27_refit prepare` with `--plan`, `--bundle`, `--outcome-plan`,
`--archive-root` paths above and `--output-dir .cache/autoresearch/api27-refit`.
Inspect every selected roster, feature schema, source timing and versioned label.
Add the exact review only after that inspection. Repeat with subcommand `fit`
and the same input arguments; no arbitrary review path is accepted. Run twice
and compare corpus, model and consumed matrix hashes, not timestamped receipts.

Run `PYTHONPATH=packages/scripts .venv/bin/python -m pytest -q
packages/scripts/autoresearch/tests/test_api27_refit.py -o addopts=''`, then the
restricted, source witness, API opportunity, M0 forward/evaluation and prospective
input suites. Run Ruff check and format check for new files. Push a Conventional
Commit and open/attach a PR. Wait for required Python Checks and inspect all
other checks; compare any nonrequired security failure with the existing exact
17-row h2/multidict/pyjwt baseline, never call it all green. Merge normally only.

## Validation and Acceptance

Actual training must consume 27 races, 283 unique runner identities, 14 columns,
81 positive labels and race-normalized weights. No label/identity/source metadata
may enter X. Two runs must produce identical model and matrix hashes and saved
scores must match the numerical estimator. Tests must reject modified sources,
membership, labels, extra features, review flags, recipe and implementation;
failure must not produce a completion receipt. Confirm the original M0 model,
receipt and complete forward archive file hashes and membership stay unchanged.

## Idempotence and Recovery

Every command uses an exclusive new timestamped output directory; failed runs
are retained and retried into another directory. Never edit a source archive,
old review, frozen M0 or existing prediction. No paid service or secret output.
No prospective success claim follows from training or deterministic replay.

## Artifacts and Notes

Record actual hashes, test results and numerical fit evidence in the research
note. The PR closure comment records final CI and merge evidence because the
merge commit cannot be known before it exists.

## Interfaces and Dependencies

Expose `corpus_from_report(report)`, `implementation()`, `admit(corpus)` and
`run(admitted, directory)`. Use immutable serialized bytes in the admitted
object; recheck implementation before and after fitting. Reuse NumPy and the
existing scikit-learn solver, atomic exclusive `observed_history_seed.save`,
and `api_training_opportunity.prepare` for raw evidence. No new dependency.

Revision: Updated with raw replay review, actual two-run fit evidence, a fixed
review-serialization provenance ambiguity, 189 passing tests and unchanged M0.
All numerical settings remained fixed; no outcome-based tuning was performed.
