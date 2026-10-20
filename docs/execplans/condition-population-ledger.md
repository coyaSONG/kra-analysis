# Preserve the full prospective accountability population

This living ExecPlan follows `.agent/PLANS.md`. It supports the unregistered
`docs/research/2026-10-20-condition-preregistration-draft.md` and the evidence
boundaries in `2026-10-20-condition-evidence-boundaries.md`. No real calendar,
study, roster or N may be selected by this implementation work.

## Purpose / Big Picture


The future comparison must not omit weeks without predictions, late-added
races, cancelled races or races whose official IDs changed. An append-only
evidence ledger must preserve these obligations separately from immutable
weekly execution protocols. The reader must be able to distinguish observed
schedule membership, reviewer interpretations, physical identity and evidence
that a whole scope is complete. Missing scopes must keep the full denominator
unknown, not become zero races or a smaller favorable subset.

## Progress


- [x] (2026-10-20) PR121 normal merge verified at
  `bd1e3443108346cc9fe36a20a771625c3baec9a2`; previous turn made concrete progress.
- [x] (2026-10-20) Re-read the preregistration draft, evidence boundaries and
  official schedule replay/parser. A reconciled snapshot is not full-week
  closure or affirmative no-race evidence.
- [x] (2026-10-20) Sent targeted schema/closure/identity questions to the
  authorized Chrome ChatGPT Pro conversation. Pro selected in UI.
- [x] (2026-10-20) Read the completed 23-minute Pro consultation without stopping generation; resolve
  machine-derived facts versus source-backed reviewer decisions.
- [x] (2026-10-20) Implement the public-journal-to-original-HTML observation
  path, retaining missing scopes and unverified semantic events. No closure or
  physical-identity admission is implemented.
- [x] (2026-10-20) Initial combined regression run: 403 passed in 41.20 seconds;
  expanded focused suite: 49 passed in 2.15 seconds. Original six model,
  receipt, registry and M0/API27 prediction hashes remain unchanged.
- [x] (2026-10-20) Final combined regression after completed consultation:
  408 passed in 41.00 seconds, including 51 new observation/chain tests.
  Ruff check and format-check passed.
- [x] (2026-10-20) Reconcile the implemented observation-only boundary with the completed
  consultation; record the remaining semantic admission work precisely.
- [ ] Run regressions/required CI and normally commit, push and merge.
- [ ] Keep actual registration, training and scoring disabled until the
  remaining source, submission and result-admission gates are complete.

## Surprises & Discoveries


`shared.kra_schedule.reconcile_schedule_cards` validates national/regional
membership and start/count agreement for the selected snapshot. It reports
missing date/source and mixed-week conditions, but absence of a date in that
snapshot does not establish an official no-race decision. Consequently the
number of observed canonical IDs is not the final physical-race denominator.

`kra_schedule_snapshot.replay_schedule_snapshot` reports source failures in
its return value, including integrity failures. A population adapter must
not silently treat a corrupt referenced original as an ordinary unknown
network result: source-pin validation precedes population projection.

## Decision Log


Decision: do not design an authoritative semantic registry from a boolean
reviewed flag. First obtain completed advice on source/evidence scope,
reviewer attestation, authority and versioning. Rationale: a public assertion
can prove what was asserted without proving that every physical race was
enumerated. Date/Author: 2026-10-20 / Codex.

Decision: preserve the existing weekly protocol and original M0/API27 rules.
Rationale: population reconciliation cannot rewrite predictions, move cutoffs
or restore consumed attempts. Date/Author: 2026-10-20 / Codex.

## Outcomes & Retrospective


The observation-only evidence path is implemented and tested; the Pro design
consultation is complete and PR122 is in draft CI. It connects actual archive/source
validation to preserved scope observations, rather than accepting supplied
race lists. It does not implement complete population admission. The full
70% objective remains unmet. Hash-chain validity is never source completeness.

## Context and Orientation


The relevant modules are `packages/scripts/shared/kra_schedule.py`,
`packages/scripts/autoresearch/kra_schedule_snapshot.py`,
`condition_historical_publication.py`, `condition_forward_publication.py`
and `condition_outcome_accounting.py`. The publication archive helper replays
exact GitHub response/document bytes; it does not certify semantic truth.
The outcome reducer consumes normalized verified states; it cannot discover
missing weeks and must not receive invented verification flags.

An enrollment record is an immutable first-recorded race obligation. A
physical identity component is a source-supported grouping of records that
refer to the same real race, not a name/distance/roster similarity match.
Retain all original enrollment and attempt records even if a later identity
correction changes the count of physical components.

## Plan of Work


First specify a versioned root contract, expected date/venue/week obligations
and a selected ordered ledger head bound to archived public bytes. Validate
sequence, previous hashes, umbrella binding, recording clocks and correction
references. Reuse original schedule replay for source-derived membership.
Do not infer an exhaustive time interval from a single observation.

Then implement the precise evidence/semantic boundary supported by the
completed consultation. Unknown closure and ambiguous physical identity must
remain visible. Preserve observed additions and disappearances across
snapshots rather than taking only the last or intersected schedule.

The first executable milestone now comprises `condition_population_chain.py`
(ordered event validation), `condition_population_sources.py` (pinned capture
and raw HTML replay) and `condition_population_ledger.py` (public archive
binding and scope projection). Its complete behavior is an observation audit,
not a complete population evaluator. The selected public journal cannot certify
the newest authoritative head. Every semantic event remains an assertion;
correction records never remove parent observations. Physical identity,
authorized source interpretation, closure and missing-submission admission
remain distinct future milestones, not silently accepted flags.

Finally test original-file immutability, missing weeks, zero versus unknown,
late additions, renumbering, replacement, cross-week moves, duplicate attempts,
forks/truncation, corrupt sources and unverified reviewer assertions. Each
judgment must identify whether it was mechanically derived from a source,
attested by an authorized reviewer, or remains unknown.

## Concrete Steps


Use `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`, branch
`codex/condition-population-ledger`, based on `bd1e344`.
The original user checkout is untouched. Use `.venv/bin/python -B`,
`PYTHONPATH=packages/scripts`, `PYTHONDONTWRITEBYTECODE=1`, pytest
`-p no:cacheprovider`, and Ruff `--no-cache`. No new dependencies or services.
Run the focused suite with:

    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m pytest -q -p no:cacheprovider packages/scripts/autoresearch/tests/test_condition_population_chain.py packages/scripts/autoresearch/tests/test_condition_population_ledger.py

Run Ruff check/format-check on `condition_population*.py` and
`tests/test_condition_population*.py`. The Python Checks CI job runs the same
focused suite. Broader local regressions include condition snapshot replay,
historical publication, forward inference, normalized outcome accounting,
local M0 evaluation, versioned result observations and official schedule tests.
Tests use temporary synthetic archives/HTML, never live training or enrollment.

## Validation and Acceptance


A synthetic end-to-end evidence bundle must retain a missing scope and all
previously observed IDs while withholding the full denominator. A later
smaller schedule must not erase earlier obligations. A valid hash chain alone
must not prove full population or no-race semantics. Invalid chains or
corrupt pinned evidence must be blocked, not reported as zero races.
The implemented synthetic bundle contains two declared weeks, four venues and
four observed IDs. Output retains all 56 date/venue scopes with unknown closure.
A changed-date later snapshot retains five observed IDs without identifying
five physical races. Missing local capture yields unknown N, not zero; damaged
captured bytes block replay. Published no-race/identity assertions cannot
override this behavior. Expanded semantic acceptance criteria will follow the
completed review, without claiming those gates are already implemented.

## Idempotence and Recovery


Read-only replay must neither create predictions nor update the ledger,
registries, source originals or Git refs. Missing evidence is recovered by
a separate bounded collection/review process, preserving source bytes and
actual clocks. Original enrollment/attempt records are never deleted to
repair identity or evidence errors.

## Artifacts and Notes


Consultation: `https://chatgpt.com/c/6ad0d05d-5b08-83e8-b4b5-5252f401bb4d`.
Questions were submitted around 2026-10-20 15:43 UTC. No completed answer or
activation approval was claimed before completion. The UI subsequently reported
23m 1s processing and a completed response; its full DOM-rendered answer,
including sections B-3 through E and final recommendation, was read. The
completed consultation is summarized in the population observation document.
It did not verify actual notice semantics or execute the new implementation.
No activation approval is claimed.

## Interfaces and Dependencies


Reuse the existing strict JSON/hash and publication/schedule helpers where
their guarantees apply. Never call live inference, fitting, network collection
or outcome evaluation from population replay. Keep evidence admission distinct
from arithmetic and from actual prospective study approval.

Revision note: initial plan deliberately defers authoritative closure and
identity semantics until the Pro review completes; current parser limitations
were established by reading its code, not inferred from empty responses.

Revision note: added the implemented observation-only milestone and reproducible
tests while the consultation continues. This milestone establishes the raw
evidence path but explicitly leaves semantic admission and actual registration
disabled. No existing frozen artifacts were edited.

Revision note: completed Pro advice separates source facts, authorized human
interpretation and derived closure. A future narrow semantic-admission module
must validate actual review authority, exact reviewed bytes, scope, separate
clocks and corrections; the current observation module intentionally accepts
none of these judgments. Identity components may change in a new projection
without deleting enrollment or attempt history. Source-wide closure and
prediction attribution remain separate unfinished milestones.
