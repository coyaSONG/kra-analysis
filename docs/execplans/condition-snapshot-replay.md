# Replay frozen condition inputs with their original code

This living ExecPlan follows `.agent/PLANS.md` and extends the publication
stage in `condition-historical-publication.md`. It never authorizes fitting,
new predictions or prospective registration.

## Purpose / Big Picture


The public paired document binds a matrix and protocol, but public existence
does not show that the original calculations match. A read-only replay will
load a complete, hash-pinned source/input snapshot and use its original
functions in a separate Python process. It compares rebuilt inputs and paired
bytes with the existing commitments, never emitting replacement predictions.
The actual current source checkout is not used as the historical implementation.

## Progress


- [x] (2026-10-20) PR120 merge confirmed at `07c21ad09084ed81f649b4fa70531c56392935e5`.
- [x] (2026-10-20) Inspected original matrix builder, stored scorer and import-root
  behavior. These functions can operate against an archived repository layout
  without calling current admission or changing Git refs.
- [x] (2026-10-20) Implement pinned snapshot inventory and isolated original-code replay.
- [x] (2026-10-20) Test actual frozen numerical functions on synthetic inputs, plus missing
  environment, corruption, current-checkout independence and no-write/no-fit guards.
- [x] (2026-10-20) Local regressions: 305 passed in 40.28 seconds, including
  43 new cases; Ruff lint and whitespace checks passed.
- [ ] Required CI, commit, push and normal merge.
- [ ] Later: raw-source derivation closure, submission authority/closure,
  umbrella population/identity ledger and target admission before scoring.

## Surprises & Discoveries


`restricted_cohort.ROOT` is derived from its own source location. Preserving
the original `packages/scripts` tree lets original `matrix_for` resolve pinned
sources under the snapshot without monkeypatching ROOT or runtime checks.
`training.environment()` records numerical libraries, packages, CPU and thread
settings; a text manifest is not a recreated environment. A mismatch must
prevent numerical replay, not prove that the original prediction was invalid.

## Decision Log


- Decision: use the invoking Python interpreter in isolated mode and original
  snapshot imports, not current implementation equivalence or a new scorer.
  Rationale: unrelated later code edits must not rewrite old calculations.
  The operator must invoke the auditor with a preserved compatible environment
  if the currently available interpreter does not reproduce the original one.
  Date/Author: 2026-10-20 / Codex.
- Decision: bind every file in the snapshot and reject extra executable source,
  symlinks, corrupt hashes and changed files during replay.
  Rationale: code hashes in a protocol cannot justify importing unlisted files.
  This is cooperative evidence preservation, not a hostile-code sandbox.
  Date/Author: 2026-10-20 / Codex.
- Decision: guard fit, live admission, publication and collection paths; return
  only agreement facts and reasons. Never stage recomputed triples.
  Rationale: replay of stored commitments is not another prediction attempt.
  Date/Author: 2026-10-20 / Codex.

## Outcomes & Retrospective


Implemented parent auditor `condition_snapshot_replay.py`, stdlib entry point
`condition_snapshot_worker.py`, 43 regression cases and required Python CI step.
An actual subprocess reconstructs synthetic original inputs and frozen-model
predictions, despite traps on the current parent's scorer/runtime. A changed
original environment stops before scoring; a changed original prediction is a
replay conflict, never a race-level miss. Publication, numerical replay, raw-source
derivation, complete submission evidence and population completeness remain
distinct dimensions. Even successful numerical replay cannot establish the
70% objective or activate an unregistered study.

## Context and Orientation


The source functions to reuse are `condition_forward_inputs.matrix_for`,
`condition_forward.paired` and `condition_forward_contract.load_models`.
The original implementation manifest resides in the published protocol's
`runtime.implementation`; the environment is in `runtime.environment`.
The original matrix hash is in the published paired packet.
PR120's `condition_historical_publication.audit` verifies the public chain.

Add a parent audit module and a standard-library worker under
`packages/scripts/autoresearch/`. The worker must not import the current
autoresearch package before selecting the preserved source tree. Parent
validation first checks the public chain and snapshot pins; the worker repeats
the inventory checks before importing and after replay. No Git operations,
network collection, package installation or environment repair is allowed.

## Plan of Work


Define a pinned replay manifest linking the PR120 publication manifest, a
snapshot directory and a complete repository-relative file inventory, and
the original matrix path. Require the source inventory to match the published
implementation map and include the frozen models/receipt and exact protocol
and paired documents at their original repository paths.

Run a separate isolated Python process. Reproduce only the recorded thread
environment variables, then compare the complete original environment record.
If unavailable or mismatched, return pending without scoring. Otherwise load
the original stored models, reconstruct the matrix at its original creation
clock, and rebuild paired bytes at the original computation clock. Compare
exact artifacts; do not save new matrix/predictions or alter attempts.

The output retains publication facts and explicitly withholds scoring readiness.
Missing files/environment remain pending, corrupt inventories block, and a
calculation disagreement is a replay conflict, not an automatically assigned
race-level miss. Separate closure and source-admission stages still apply.

## Concrete Steps


Use the isolated research checkout and `.venv/bin/python` with
`PYTHONDONTWRITEBYTECODE=1` and `PYTHONPATH=packages/scripts`. Add the new tests
to required Python CI, run them with the historical publication and existing
forward/accounting/M0/observation regressions, then Ruff and whitespace checks.
Use synthetic race inputs only; no real protocol exists in the empty registry.

From the research checkout, the local regression command is:

    .venv/bin/python -B -m pytest -q -p no:cacheprovider packages/scripts/autoresearch/tests/test_condition_snapshot_replay.py packages/scripts/autoresearch/tests/test_condition_historical_publication.py packages/scripts/autoresearch/tests/test_condition_forward.py packages/scripts/autoresearch/tests/test_condition_outcome_accounting.py packages/scripts/autoresearch/tests/test_local_m0_evaluation.py packages/scripts/autoresearch/tests/test_versioned_result_observations.py

Observed: `305 passed in 40.28s`. Run Ruff check/format-check on
`condition_snapshot_replay.py`, `condition_snapshot_worker.py` and
`tests/test_condition_snapshot_replay.py`. The user-facing manifest schema and
CLI are documented in `docs/research/2026-10-20-condition-snapshot-replay.md`.

## Validation and Acceptance


An actual subprocess must replay the original frozen scorer on synthetic
preserved inputs and match the already-recorded matrix/paired documents.
Changing unrelated current checkout files cannot change this comparison.
Source/input damage, extra source, symlinks, missing matrix, unavailable
environment and malformed worker output must not create a proven failure.
All snapshot bytes must remain unchanged. Fit, live run, stage, witness,
network and Git entry points must be guarded; no refitting or replacement
predictions may appear in output or on disk.

## Idempotence and Recovery


Audits write stdout only and make one worker attempt per invocation, with no
automatic retries. Missing environment is an explicit pending condition.
Recover only exact preserved files/environment through a separate authorized
process; never backdate evidence, change current Git refs or fit again.

## Interfaces and Dependencies


Use existing published model constants, strict JSON and publication audit.
The worker is internal trusted verifier code; it executes original repository
code only after exact pins are checked. It is not a security boundary against
a malicious operator who fabricates all GitHub witnesses. Report the worker
hash, selected snapshot hash, original environment hash and actual replay time.
No new dependencies or services are needed.

Revision note: original-code execution was selected over comparing all current
source files with old hashes, because that would unnecessarily make unrelated
later edits a historical replay dependency.

Implementation revision: clean subprocess environment capture in synthetic
fixtures avoids pytest's unrelated loaded numerical libraries. Guards are
explicitly cooperative, not a hostile-code sandbox; trusted snapshot imports
and environment capture precede them. Rechecked inventory/public pins, chronology,
18 forbidden fit/live entry points and environment/conflict cases have executable
tests. Public execution/merge evidence is still pending.
