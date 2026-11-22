# Replay a whole card as a development-data candidate

Maintain this execution plan under `.agent/PLANS.md`. Use the existing
isolated research checkout and its local Python environment.

## Purpose / Big Picture

A complete card can have a timely published input fingerprint without
having timely predictions. Researchers need to be able to prove which
exact input and result bytes can be combined for later training without
using the lack of predictions to reject good inputs or using good inputs
to repair a missed prediction. The new command checks the original card
and the selected result version, then either accounts for every reason
the whole dataset is not ready or saves one local candidate for review.
It is not an evaluator, feature expansion, training admission or fit.

## Progress

- [x] Reuse existing whole-card input publication, immutable result
  observation and race context interfaces. Locate the absent join that
  does not require a prediction protocol or result of a prediction.
- [x] Implement full-ledger replay, exclusive staging, user instructions
  and the new regression tests in the existing result CI step.
- [x] Exercise positive and blocked cases from raw synthetic receipts.
  Verify 228 focused and adjacent tests, the original PR95 digests,
  and the declaration/result join on the complete October archive.
- [ ] Release the reviewed change through the normal required checks.

## Surprises & Discoveries

The live readback deliberately rejects after-cutoff staging. The
witness replay can recover an already observed input at its original
readback instant, but cannot stage a new one. The paired evaluator
requires a registered protocol and a separate independent reviewer.
Neither is a source requirement for separately witnessed development
inputs. The result policy can also retain a valid top three even when
the version lacks a declared horse. A development candidate needs the
full declared roster in both selected result sources.

## Decision Log

Keep the original schedule hash and first cutoff independent from the
input receipt. Reuse the existing hash witness and fixed-pair result
version replay, not a reconstructed new snapshot or newly contacted
provider. A selected result plan pins the original dates, original
schedule, API data, official detail and result policy. Extra races,
missing or ambiguous targets, mismatched horses and absent declarations
block the whole candidate without deleting their original slots. Even
an observed void supplies no positive training target.

The only inputs are the unchanged API26 projection and literal
original meet, distance and class context. Preserve missing values
and flags. Keep labels separately ordered by race identity; include
no predicted selections, model scores or labels in feature records.
The local output clock is current, not a reconstructed earlier date.
It does not approve use for training or count as future verification.
Distinct user-selected result plans create separate candidate versions;
the current code never assumes which is latest or corrects the old one.

## Outcomes & Retrospective

On the synthetic 14-race card, the source witnesses, separate targets and
missingness replayed without a prediction or approval. An omitted lower
runner kept the whole candidate on hold despite a unique top three.
Cutoff-time or missing publication, result clocks in the future, extra
IDs, a different schedule hash and missing results cannot seal. A
selected correction keeps both local artifacts and the same input rows.
The default CLI prints no feature or target payload.

The separate real join control re-read the existing October result plan,
`bb122ca93d14c56e7fe6bba969fe1df0c5add72c09b135ced8f8e949cd2834e0`,
and declaration keys from the archived development cohort,
`c25db29f0ba78cd3e7ab49c04950fcde3f3a12686ce4aad1ba69b33fb2616e03`.
All 50 original races and 534 declarations in that selected version
joined, including four races with result exception notes. This exercised
the new roster/target join only. It did not replace the older witness
format, stage a second October dataset, compute forecasts or fit a model.
The latest local archive and the inspected main tree have no actual
witness in the new API26 input-packet format to seal with this command.
Existing originals, three PR95 commitments and model approvals are unchanged.

## Context and Orientation

`packages/scripts/autoresearch/kra_entry_scope_witness.py` proves exact
input packet bytes existed on GitHub before the earliest cutoff.
`fixed_pair_forward_contract.source` replays the exact API26 inputs
that the packet bound. `fixed_pair_evaluation.outcome_version` reads a
versioned API214 and official HTML result plan under the original result
policy. Its `outcome_evidence` checks capture clocks and compares
horse/saddlecloth keys. None of those methods needs to run a prediction.

## Milestones

First add `packages/scripts/autoresearch/kra_whole_card_learning.py`.
The default CLI reads the exact input witness and optional selected
result plan and prints a readiness ledger rather than feature values.
The local seal requires every original race to join and writes an
exclusive JSON next to the intake receipt, named by the result plan
digest. It emits the candidate hash but not the feature or target
payload. No collector, GitHub action, model loader or trainer runs.

Next add `test_kra_whole_card_learning.py`, using the existing synthetic
multi-venue inputs and results, with no prediction approval. Include
missing results, roster conflicts and withdrawals, exact cutoff,
scope drift, explicit correction, no write on incomplete data and
exclusive output. Check no result or original artifact changes.

## Concrete Steps

From the isolated repo, set `PYTHONPATH=packages/scripts` and use the
existing `.venv/bin/python`. Run:

    .venv/bin/python -B -m autoresearch.kra_whole_card_learning --help
    .venv/bin/python -B -m pytest -q -p no:cacheprovider -o addopts='' --import-mode=importlib packages/scripts/autoresearch/tests/test_kra_whole_card_learning.py

Use the original independently held receipt path and digest, schedule
digest, first cutoff, input packet digest and input witness PR. Supply
both the selected result plan path and digest or neither. To add one
candidate, specify `--seal` only after the full-ledger readback passes.
These commands are for original saved evidence, never for replaying a
later input capture as though it were available earlier.

## Validation and Acceptance

The fictional complete 14-race card must produce 14 aligned feature
groups and 14 unique observed targets without calling a provider. A
single incomplete or contradictory race retains all 14 slots and
prevents sealing any. A missing or late input witness cannot become
timely. A corrected selected plan has a separate path and digest.
Local tests, Ruff, the required GitHub checks and both original PR95
prediction hashes are verified before merge.

## Idempotence and Recovery

Verification is read-only. The only exclusive write is the candidate
for an explicitly selected version; use the existing version or
independently select a later result plan, never replace a saved file.
A failed or partial readback is not a training admission. Preserve the
original bytes and clocks and later verify any training approval and
separate future population under their own contracts.

## Artifacts and Interfaces

The local candidate binds its witness, original cutoff and roster,
result plan and observation IDs, and current materialization clock.
The CLI prints a short operator report with URL/path-free source
accounting apart from local artifact references. The test fixtures
exercise the existing archived-publication and result replay layers.
