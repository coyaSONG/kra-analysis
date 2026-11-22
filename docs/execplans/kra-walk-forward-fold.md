# Freeze the exact earlier-card inputs for a future whole-card fold

Maintain this ExecPlan under `.agent/PLANS.md` in the existing separate
research checkout. This follows `docs/execplans/kra-whole-card-learning-replay.md`.

## Purpose / Big Picture

An individual development candidate does not prove that its exact
selected results were known before a later evaluation. A fold means
one unchanged future evaluation card and the specific older cards
selected for development before its cutoff. Make the preparation
replayable without touching the evaluation's results or the fixed
M0/API27 commitments. Print only a digest for independent publication.

## Progress

- [x] (2026-11-22 21:43Z) Locate the single-card source replay and its
  timing inputs; verify the missing cross-card freeze and the broad
  fixed-runtime fingerprint.
- [x] Implement exact prior-candidate replay, boundary checks, private
  freeze and independent hash readback.
- [x] Reproduce a complete multi-card fixture and test leakage and
  substitution failures. The related suite passed 182 tests; the
  focused suite also passed all 17 cases from the API CI working
  directory. Ruff passed.
- [x] Read the completed Pro methodology review in the authorized
  browser and identify the claims its clock advice supports.
- [x] Verify the additional clock and merge-tree tests: 185 related
  tests passed, including the final 20 focused cases. Ruff and diff
  checks passed.
- [ ] Release the tested change through the normal required checks.

## Surprises & Discoveries

The result API may require an additional entry observation to resolve
venue/identity. The latest API HTTP clock alone may understate
availability; the replayed frozen result seed carries the combined
source clock per record. A locally timed seed export, candidate readback
and candidate materialization are three different operations.

The shared result verifier reads the whole frozen result archive
before filtering to the selected dates. Precheck that archive's
request plan before any replay, and reject it if it includes the
evaluation date or later.

The fixed training and forward preparation fingerprint includes all
non-test Python code under `packages/scripts`. Keep this opt-in tool
under `docs/research/tools`, outside that fingerprint. Tests are in
the existing tests directory, which the fingerprint excludes.

## Decision Log

Explicitly select exact prior candidates, result versions, and a
separately witnessed evaluation card. A local canonical packet binds
the plan digest and replays all whole scopes without any result for
the evaluation side. Do not select a favorable source or silently skip
an incomplete card. Require earlier nonoverlapping Korean race dates
and exact race identities. A horse can legitimately appear in multiple
weeks; this is not reuse of the same race or independent sampling.
Both the original merge and the locally archived receipt of its proof
must precede the assembly. Receipt retrieval does not establish the
source's original release clock.

Keep the old single-card implementation unchanged so that its
fingerprint remains reproducible. Prove the older candidate is the
same replayed bytes except for its originally recorded clock fields,
and independently check those fields against the raw result source
times, result seed export and the next fold's cutoff. The common
publication proves the existence of the exact packet by the merge; it
does not establish the sources' initial release, reviewer approval,
fit, predictions, or a general rule for selecting future weeks.

The completed Pro method review (displayed processing time 10m 58s)
reviewed only the supplied design. It did not access this checkout,
approve training, or run tests. We keep a separate flag for the local
clock claim and do not certify a common selection rule. Such a rule
must later fix an as-of candidate census, expected selected set and
exclusion reasons, permitted result versions and held-out roles before
the relevant evaluation. Known reschedulings also need the preexisting
population lineage rules; nominal race-key separation alone is not
evidence that an alias of the same physical race has been discovered.

## Outcomes & Retrospective

The fictional multi-card trial binds 28 earlier races and all 14
evaluation races, without loading a result plan for the evaluation.
The existing validation also recovers the same fold after a later
official result version is saved. A date overlap, omitted result
binding, time-conflicting seed export, replaced target, later copy
of a prior outcome, cutoff-equal publication, and changed original
plan cannot establish an earlier fold. The 210 existing fixed-runtime
files still match the original Git blobs and paths.
An identical cutoff represented in Korean time passed; a shifted
cutoff did not. An earlier merge carrying different digest bytes
did not verify the original packet.

The local archive has no real complete card in this particular
input-witness/candidate format. Historical artifacts in different
formats are not backdated into it. The tool and fixture do not
add actual learning rows or performance evidence.

## Context and Orientation

`kra_entry_scope_witness.verify` verifies exact before-cutoff input
publication. `fixed_pair_forward_contract.source` replays the inputs
from their archived readback time. `kra_whole_card_learning.replay`
recreates the prior development candidate from the same official
result plan and archived declarations. The frozen result seed is an
export with exact capture pointers and a combined availability time
for each result row. `condition_forward_publication` verifies one
GitHub merge and the exact file in its merge tree.

## Milestones

First implement `docs/research/tools/kra_walk_forward_fold.py`. The
private plan lists all older cards in time order and exactly one
future evaluation card. Each item pins its original input witness;
each older item also pins its selected result plan and sealed
development candidate. Read the old raw sources and the newest card's
input only. The `stage` operation writes a single fold packet beside
the evaluation receipt before its original cutoff, and emits the
exact public marker. No source collector or learner runs.

Next add the publication capture/replay commands and tests. The only
optional external reads are one GitHub PR and its exact merge-tree
marker. Check that the merge is strictly before the old cutoff. Replay
the saved bytes at any later time without making a new timely packet.
Use the source fixtures to demonstrate that the later evaluation
population is untouched by training result checks.

## Concrete Steps

From the separate checkout with its Python environment:

    PYTHONPATH=packages/scripts .venv/bin/python -B docs/research/tools/kra_walk_forward_fold.py --help
    PYTHONPATH=packages/scripts:apps/api .venv/bin/python -B -m pytest -q -o addopts='' packages/scripts/autoresearch/tests/test_kra_walk_forward_fold.py

Use the private plan schema and command in `packages/scripts/README.md`.
After saving the exact stage marker in a normally merged public PR,
keep the fold packet digest and pass it and the original PR to
`capture`. `replay` verifies the same evidence without network or
mutation. An operator must still have the separately approved
research protocol and model execution path.

## Validation and Acceptance

Two chronological synthetic training cards and one later complete
evaluation card must preserve their distinct totals, missingness,
exact selected versions and original date boundaries. Missing or
changed source bytes, late result evidence, time equality at the
cutoff, a duplicate date/identity, replacement after a correction,
a changed row, or a late publication must not create timely evidence.
No live KRA/API call, training fit, score, or forecast is tested.

## Idempotence and Recovery

Never replace the first packet or published marker. A late merge
can be recorded as late and read again, but cannot reopen the card.
Replays use the originally selected result version, not a newer
file or an unverified latest pointer. A different plan does not
replace the snapshot under the same evaluation receipt.

## Artifacts and Interfaces

The fold packet stores plan and private-source digests, exact date
and race-identity commitments, feature columns and missingness,
the latest API capture and combined-source availability time, seed
export, latest official capture, candidate readback and persistence,
and the unchanged evaluation cutoff and input proof. Only the
digest marker is shared publicly.

## Interfaces and Dependencies

Reuse standard-library JSON handling and the repository's bounded
read, timestamp, canonical hash, exclusive write and publication
helpers. Do not introduce dependencies or change a model or existing
result contract. The test uses the archived GitHub-response fixture,
the public-schedule fixtures and the frozen result-source fixtures.
