# Add frozen A24/B34 inference and public commitments

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

An operator will be able to register a future complete official race block,
score its reviewed pre-race inputs with both PR113 stored models, stage one
public paired commitment, and verify its exact bytes and timely GitHub merge.
No estimator, imputer or scaler is fitted. Without a separately reviewed and
merged future protocol, the real command refuses to execute. This change does
not choose future dates or promote either model.

## Progress

- [x] Read PR113, the saved models, existing source projections, schedule replay and publication witness paths.
- [x] (2026-10-19) Implement model/protocol admission and full-block input replay.
- [x] (2026-10-19) Implement single-use scoring, append-only staging and live publication verification.
- [x] (2026-10-19) Add 68 synthetic/end-to-end and rejection tests with fit-call traps, plus CI; 253 related regressions pass.
- [x] (2026-10-19) Verify 58 original input hashes, both consumed files and unchanged training ledger; document commands and source-review limits.
- [x] (2026-10-19) Commit and push implementation as `ae59d33`; create PR #114 with normal required-check enforcement.
- [ ] Normal merge after final required CI; PR #114 is the authoritative merge/check record.

## Context and Orientation

Work only in `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`.
The user's original checkout is unrelated and dirty. PR113 public snapshots
are in `docs/research/experiments/2026-10-19-condition-training-v1`: A24 model
hash `69f655fd005b59313d0a23dbf44759510c937ef403e8ac4fd844ea67494d635e`, B34
`c03972a447c2a36603717a7107b751f23d0fff08cb204565b68215f955ef16e0`, receipt
`3587c948913c82cc9c0b8c5e64161ef29794ed22a80d08425300e924834aa96e`.
Their two lifetime fits are already consumed. `condition_training_model.score`
uses stored median/scaler/coefficient state; `select` selects exactly three
canonical numeric horse IDs. Neither performs fitting.

`condition_candidate_inputs.build` joins original 24-column packets with ten
memory fields, checks full rosters, identity, columns, null flags and clocks.
Use this pure function, not its October-specific `run`. Upstream raw lineage
must receive a separate source review; a supplied feature table is not proof
of availability. `kra_schedule_snapshot.replay_schedule_snapshot` replays raw
national/regional pages. `prerace_hash_witness.collect_publication` makes two
bounded GitHub requests and checks merged PR metadata, document identity and
Git blob hashes. Reuse these existing boundaries without editing them.

## Plan of Work

Add `condition_forward_contract.py` for pinned stored models, inference runtime
fingerprints and repository-only future protocol admission. The new registry
`data/contracts/condition_forward_reviews_v1.json` is empty. A future record
must bind protocol bytes, complete dates, reviewed raw-source closure, label-
free inputs, statistical/failure policy and exact code/environment. Its bytes
and protocol must match HEAD and origin/main. No command-line substitute or
unregistered date advance is allowed. Reject overlapping registered dates.

Add `condition_forward_inputs.py` to replay every official schedule for each
registered date and compare the entire race ID/cutoff population, pin all
reviewed source receipts, packets and memory, and reconstruct the matrix.
Freeze the entire block before its earliest T-30 cutoff, with no within-block
outcome updates. Future registration supplies complete frozen rosters and
source evidence; this work is not a new collector or a raw-lineage approval.

Add `condition_forward.py` for a CLI with inspect, run, stage and witness
operations. A shared common-Git reservation prevents a new directory/worktree
from reusing the first paired prediction. Reserve before work; preserve failed
attempts and do not regenerate a different pair. Scoring requires a live proof
that the exact protocol was normally merged before the block cutoff. Save
inputs and one paired prediction per race, then observe saved bytes and write
a success receipt only before cutoff. Staging exports those exact bytes to a
fixed repository path; normal git PR publication is a separate visible action.
Witness verifies a live merged PR containing those exact bytes and records
late publication explicitly rather than calling it timely. No accuracy or
promotion is inferred from publication.

## Milestones

First, prove stored inference loads pinned files and matches the old saved
consumed scores without loading labels or fitting. Next, admit a synthetic
complete future protocol and reconstruct both arms' inputs with schedule and
raw-pin checks. Finally, exercise scoring through staging and mocked GitHub
publication, including errors before/after the cutoff. Demonstrate the real
empty registry refuses execution without files or network requests.

## Concrete Steps

From the isolated checkout use its existing `.venv` and no new dependencies:

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m pytest -q -p no:cacheprovider packages/scripts/autoresearch/tests/test_condition_forward.py packages/scripts/autoresearch/tests/test_condition_training.py -o addopts=''
    .venv/bin/ruff check packages/scripts/autoresearch/condition_forward*.py packages/scripts/autoresearch/tests/test_condition_forward.py
    .venv/bin/ruff format --check packages/scripts/autoresearch/condition_forward*.py packages/scripts/autoresearch/tests/test_condition_forward.py
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m autoresearch.condition_forward inspect

Inspect prints model and runtime hashes, fit count zero and registered studies;
it never creates a protocol or invokes fitting. Add the same tests to Python
Checks in `.github/workflows/ci.yml`. Existing schedule, candidate, witness and
training regressions must remain green. Required CI must pass before normal
merge; disclose unchanged security baseline failures without bypassing rules.

## Validation and Acceptance

Trap every estimator/imputer/scaler fit method and training runner entry point
while exercising inference. Test changed models, receipt, columns, source
hashes, raw schedules, unknown/duplicate/dropped races or runners, invalid
missing flags, nonfinite values, future-source clocks and post-cutoff execution.
Test uncommitted/unmerged protocols and registry, wrong fingerprints, overlapping
dates, missing review flags, old October dates and absent statistical policies.
Test score/canonical-set replay, concurrent/repeated runs, symlink destinations,
mutation after saving, deadline crossing during scoring or staging, fake/late
GitHub contents and response hashing. No partial successful arm may become a
complete paired commitment. Full population stays present even when failure
is recorded, and public status requires external evidence, not a local flag.

## Idempotence and Recovery

Inspection and read-only verification are repeatable. Actual paired generation
uses an exclusive shared reservation; a failed attempt is not cleared or
restarted. Fix a missing future registration before starting a real attempt.
Staging never overwrites an existing file; verify/reuse identical staged bytes.
Publication observation may append a new witness attempt with read-only score
replay but without replacing predictions or fitting;
late or failed witnesses never rewrite earlier observations. No raw sources,
old commitments, training models or training ledgers are overwritten.

## Surprises & Discoveries

The existing source builders' CLI entry points hard-code October dates, while
their pure validation/projection functions are reusable. Preserve those CLI
contracts and add a new explicit future registration boundary. The training
requirement fingerprints all scripts; adding inference code changes a future
live fingerprint, not the immutable historical training receipt. Never amend
that receipt or its consumed fit budget to make it current.

Raw schedule replay exposed the need to compare official runner counts as well
as race IDs; the new adapter now rejects roster counts that differ. Original
registry snapshots must be canonical byte-for-byte so durable replay preserves
their exact digest. A later nonoverlapping registration must not invalidate an
older study's snapshot: verify its preserved registry hash and unchanged review,
not equality with the entire newly extended registry. Tests cover both cases.

## Decision Log

Use a separate empty repository registry instead of auto-registering a guessed
next block. Require full block freeze and paired publication; do not extend the
old M0/API27 population or choose a model from the development score. Reuse
the exact stored numerical adapter and existing GitHub witness; no new numerical
library or collector is needed. Source review remains an explicit human/owner-
authorized repository review, not a claim that hashes authenticate official data.

## Outcomes & Retrospective

The inference and publication implementation is complete locally, with 68 new
tests and 253 passing related regressions (4.62 seconds). Including the existing
M0/API27 forward paths, 315 regressions pass (8.51 seconds). A read-only replay
reproduced all 534 saved scores and 50 canonical sets per arm with maximum
score difference 0.0. All 58 original input hashes match; the training ledger
still has exactly reservation, two attempts and completion. Real empty-registry
admission returns `forward_exact_registered_study_required` before reservation
or network. CPU fingerprint inspection requires the host's read permission;
environment-probe errors are reported as blocked, not success.

Actual future runs, publications and new real fits are zero. Normal PR merge
and required CI remain pending. Statistical horizon and uncertainty method
still require explicit future registration. The 70% goal is unchanged and unmet.

PR #114's first security job (118096855598) has exactly the same 17 advisory
rows as the preserved PR109 baseline; no dependency files changed. Local
comparison `.cache/autoresearch/condition-forward-20261019/pr114-security-initial/comparison.json`
has SHA256 `f09ccd9cc176dc8ec1431c52e8a56f25d9667ab82c0e7b7997f436e4fd22cff5`.
This is not an all-green CI claim. Final checks and normal merge are recorded
on https://github.com/coyaSONG/kra-analysis/pull/114; no bypass is permitted.

Plan created October 19, 2026 for the owner's PR113 inference/publication request.
Updated October 19 after full synthetic and original-byte replay verification;
added runner-count, canonical registry, append-only review and late-witness cases.
