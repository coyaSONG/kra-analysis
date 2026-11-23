# Replay the actual observations behind a frozen result version

Maintain this ExecPlan under `.agent/PLANS.md` in the separate research
checkout. This is an additive check for the workflow in
`docs/execplans/kra-walk-forward-fold.md`.

## Purpose / Big Picture

An evaluation result describes a selected set of source bytes. It does
not prove those sources were acquired in one predeclared observation
window. Before using results for a later learned model, make the
underlying request reservations, API attempt receipts, and official
capture times inspectable without reading or scoring an evaluation
card. A mixed old archive must not look like one timely fresh attempt.

## Progress

- [x] (2026-11-23 00:03Z) Trace the result plan to the exact seed,
  API unit receipts, and official archive. Identify imported receipts
  and missing local request marks in the original October example.
- [x] (2026-11-23 00:04Z) Implement metadata replay; pass five focused
  cases and recover the original 50-race archive's selected page clocks.
- [x] (2026-11-23 00:12Z) Add the half-open local interval check and
  its regression, and wire the custody checks into CI. Preserve a real
  October replayer and a separate clock-only output without rescoring.
- [x] (2026-11-23 00:15Z) Read the completed Pro response and add a
  separate, read-only verifier for one prebound archive slot per week.
- [x] (2026-11-23 00:17Z) Pass 165 related tests, including 13 new
  inventory and slot cases. Keep result references out of a partial
  diagnostic, separate from the all-or-nothing result plan vector.
- [ ] Release the validated changes through normal required checks.

## Surprises & Discoveries

The original October result seed has six units with API result rows
but records four local request reservations. Seven selected API
capture manifests retain ten pages; six pages have no matching
reservation in this version's local prefix. The earliest API request
interval begins 2026-10-16T09:51:48.799716Z. The official detail
requests still cover all 50 original keys. Some raw API results
were captured on earlier days and reused in the final result version.
The later file's materialization time cannot describe the individual
acquisition times. The existing paired evaluation remains valid under
its own contract; do not apply a new research rule retroactively.

The immutable prefix of a stored seed is the only request journal
read by this tool. An appended later request does not create an
implicit result revision. The fixed evaluator still independently
replays selected raw results and official outcomes; this metadata
inventory neither replaces it nor chooses a new version.

The slot verifier makes a different claim about current use of a
specific designated run. It checks the exact terminal inventory and
holds if the run's recorded request journal later grows or if there
is more than one attempt receipt for a unit. It preserves the original
version and does not use the new records as substitutes.

## Decision Log

- Decision: Keep collection and official result classification intact.
  Read their exact pin-linked metadata separately from the fit and
  admission policy. Never replace selected results or assume that
  an unavailable request is a confirmed absence of a race.
  Rationale: Both an observation-window rule and a version review
  need actual provenance, not an inference from the export clock.
  Date/Author: 2026-11-23 / Codex.
- Decision: Use one independently predeclared observation slot per
  enrolled training week, not a rule that finds a better version in
  a directory. Bind the designated terminal record and local raw
  inventory, and stop the whole plan if one slot is held.
  Rationale: The completed Pro consultation highlighted that a window
  by itself allows operators to choose among results. A fixed folder,
  one result filename, one PR number and a matched inventory reject
  alternate versions in the documented workflow. The local clocks
  are not independently authenticated by a later close record.
  Known material corrections need a use hold, not a version election.
  Date/Author: 2026-11-23 / Codex.

## Outcomes & Retrospective

No real data collection or study authorization is in scope. A local
archive can describe which evidence it contains, but it cannot prove
that no unrecorded API request occurred or when the publisher first
released a result.

## Context and Orientation

`packages/scripts/autoresearch/fixed_pair_evaluation.py` verifies the
original frozen scope and selected outcomes. Its outcome plan pins
the local API seed and official archive. The existing
`observed_history_seed.py` stores one local reservation per API HTTP
request and numbered receipts per day and venue. The existing
`official_history_support.py` pins each official response receipt,
including start, completion and status. A receipt may corroborate an
earlier captured result without constituting a second result acquisition.

## Milestones

Add `docs/research/tools/kra_result_observation_inventory.py` to
check and list the pin-bound source metadata for one selected plan,
only after validating that plan's original date and schedule scope.
Compare page reservations against their actual acquisition intervals,
distinguish absent local request marks from an absent result, and
retain the exact source references. The old result evaluator remains
the authority for actual outcome and roster validation.

Add `docs/research/tools/kra_result_slot_witness.py` ahead of the
ordinary fold stage for a separately reviewed research plan. It
replays enrollment and checks the added rule's exact pre-cutoff
publication. It derives result plans only from the designated slot,
and compares their pins to the eventual fold's pins.

## Concrete Steps

From the isolated checkout in the existing Python environment, run:

    .venv/bin/python -B -m pytest -q -o addopts='' packages/scripts/autoresearch/tests/test_kra_result_observation_inventory.py
    .venv/bin/python -B -m pytest -q -o addopts='' packages/scripts/autoresearch/tests/test_kra_result_slot_witness.py

Before the first enrolled cutoff, a separately approved study may
commit a private rule JSON with `format` set to
`kra-walk-forward-result-slot-plan-v1`, `enrollment_sha256` for the
advance enrollment policy, and `slots` in exact training-week order.
Each slot is an object with its `week` Monday, explicit timezone-aware
`opens_at` and `closes_at`, a distinct `receipt_pull`, and the
original `api_request_budget`. The original whole-card cutoffs do not
change. Publish `rule_marker(SHA256)` at `rule_document(SHA256)`
through normal merge and retain the provider archive in
`result-slot-rules-publication-SHA256/` beside the rule.

The sole local slot directory is
`result-observation-slots-SHA256/WEEK/` beside the rule. A documented
observed slot holds `outcome-plan.json`, `history/selected-seed.json`
and its API receipts, and `official/` with the exact official
archive. `terminal.json` has the format
`kra-walk-forward-result-slot-terminal-v1`, `policy_sha256`, `week`,
the original `schedule_sha256` and `population_sha256`, the local
`closed_at`, a `state` of `observed`, `failed` or `not_run`,
and `result_plan_sha256` and `inventory_sha256`. Set both digests
to null in the last two states. The observed inventory hash is
SHA256 of the canonical JSON returned by the custody replayer.
Independently publish `terminal_marker(rule_hash, week, terminal_hash)`
at `slot_document(rule_hash, week)` in the prebound PR and keep
its archived evidence under the slot's `terminal-publication/`.

Recheck the exact plan before opening the fold's result targets:

    PYTHONPATH=packages/scripts .venv/bin/python -B docs/research/tools/kra_result_slot_witness.py \
      --rules RULES --rules-sha256 RULE_HASH --rules-pull RULE_PR \
      --enrollment ENROLLMENT --enrollment-sha256 ENROLLMENT_HASH --enrollment-pull ENROLLMENT_PR \
      --fold-plan FOLD_PLAN --fold-plan-sha256 FOLD_HASH

The window is half-open for source acquisition. The terminal
evidence must be published after closing, strictly before the
later original evaluation cutoff. Retain an absent or failed slot,
and do not republish an alternative as the first observation.

No live fixture or source collector is invoked by the addition.

## Validation and Acceptance

A complete fictional result archive must reconcile its captured API
pages and all logged requests. An imported source without a matching
request stays visible, not silently fresh. A missing or incompatible
pin, wrong official scope, or impossible clock fails closed. Test
the original October metadata only as an older mixed archive, not a
new fit, collection or result scoring pass.

Fictional slot tests close two earlier cards and leave the later card
input-only. Accept only both exact declared result references; withhold
the entire vector if one fails or has an added request, and reject a
different result plan or independent evidence at either cutoff.
Successful replay does not admit result labels or authorize a fit.
Verify raw result rosters and rule exceptions separately and review
known official corrections before use. This tool does not operate a
durable collection reservation or a correction journal; a separately
reviewed operator workflow is necessary for actual use.

## Idempotence and Recovery

Read-only replay. No request retries, file replacement, new studies,
time overrides, or changes to the result policy. Keep all existing
private source material in the existing archive.

## Artifacts and Notes

Keep result collection evidence separate from original pre-race input
proof, official result acceptance, independent registration, training
approval and pre-cutoff prediction publication.

The local October script and its sealed report are under
`.cache/autoresearch/result-observation-custody-20261123/`. The
report SHA256 is
`68624b05cb77ae91a97bbc58071b4e2c95223229746262f2dc30959dbd5df872`.
The last collection's diagnostic interval is not a new registered
policy for October. It correctly holds the older API and official
captures and the six pages without a local request mark.

## Interfaces and Dependencies

Use the existing local result-plan schema, seed and official metadata
schemas, canonical JSON, SHA256, and timezone-aware clock helpers.

Revision 2026-11-23 00:12Z: Record the finished source metadata
replay and the real preserved negative control. No past result,
evaluation date or model has been changed.

Revision 2026-11-23 00:15Z: Incorporate the completed consultation's
one-slot decision as a separate version replay check. Do not treat
the check as an acquisition controller, official finality or approval.
