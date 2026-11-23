# Run and close one designated result observation

Maintain this living plan under `.agent/PLANS.md` in the isolated research
checkout. It extends the result-clock and result-version replay in
`docs/execplans/kra-result-observation-custody.md`.

## Purpose / Big Picture

An operator can now verify a designated outcome version after the fact, but
has no supported way to consume exactly one approved observation window and
create the closure that verification expects. Add an explicit operator command
for an already enrolled training card. The command must use the existing raw
source collectors and produce the private result plan and exact public closure
marker without allowing a restart, version substitution or held-out probe.
This does not register a real study or grant authority to fit or predict.

## Progress

- [x] (2026-11-23 00:25Z) Confirm PR #197 and the latest national observation;
  identify the missing reservation and terminal writer, and trace both raw
  collectors and the existing read-only verifier.
- [x] (2026-11-23 00:29Z) Implement the window-bound capture and append-only
  closure, document operator commands and connect the regression step.
- [x] (2026-11-23 00:31Z) Pass 396 adjacent regressions and 14 final focused
  cases, and replay the closure with the existing verifier and whole-card
  preparation without a model or live provider.
- [ ] Run the required checks and merge a normally reviewed PR.

## Surprises & Discoveries

The future evaluation card does not exist when an earlier card's result slot
opens. Use the enrolled training prefix with already witnessed original inputs,
not a completed fold plan, to guard collection. The later verifier still checks
the actual evaluation cutoff. The history format includes a full date/venue
grid; its seed can correctly report untouched scopes as `not_attempted`.
The existing official archive format requires its fixed twelve list requests
in addition to the exact frozen race detail requests. No list or empty API
response is evidence of no races.

## Decision Log

- Decision: Reuse API214's existing capture and replay, API26 only when the
  existing result identity fallback calls for it, the existing official HTML
  archive, the existing result plan format and the existing result policy.
  Rationale: Slot orchestration need not change any prior capture, policy or
  replay fingerprint. Restrict API queries to original date/venue scopes and
  cap pages from the declared runner count; stop on failure without retry.
  Date/Author: 2026-11-23, Codex.
- Decision: Require pre-cutoff enrollment and rule proof, a pinned prefix up
  to this training week and a strictly later Korean date than the latest
  scheduled start. Carry one durable claim per KST week in the shared Git
  directory and hold the claim through a capture. A claim survives interruption
  and is not a permit to start a second process.
  Rationale: Reopening an interrupted or unobserved week would allow a human
  to choose the result version retrospectively. All eligible weeks retain their
  recorded state, including a missing or failed one.
  Date/Author: 2026-11-23, Codex.

## Outcomes & Retrospective

Two fictional 14-race original cards were captured and closed via two
separate slots. Each used five API214 pages, one API26 identity page and
26 official pages including the fixed twelve lists. The existing verifier
returned both exact result plan references; the whole-card tools joined the
two candidates and staged a later input-only card. No evaluation results
were read and none of that evidence admits training or establishes a score.

Authentication and quota errors, empty replies, a placeholder web page,
an interrupted capture, a changed HTML body, and arrival at the exact
closing instant all withheld a result version. An unrun slot closed without
requests. Another rule could not restart a consumed week. The three October
commitment byte hashes matched their published originals. The latest real
national observation still covers November 20-22 only; no new source call,
study registration, training admission, real fit or prediction was made.

## Context and Orientation

`kra_walk_forward_enrollment.py` verifies saved merged PR proofs and original
input scope. `kra_result_slot_witness.py` pins a single result plan and time
window per previously enrolled training week. Its terminal format distinguishes
`observed`, `failed`, and `not_run`. `observed_history_seed.py` defines the API
journal and seed format; `kra_result_snapshot.py` and `official_history_support.py`
store the raw API and web replies. The ordinary result policy is applied only
in a separate, later whole-card readback. The shared Git directory is the local
store common to related worktrees, so changing worktree names cannot reset a
week's reservation.

## Plan of Work

Add `docs/research/tools/kra_result_slot_runner.py` and its source adapter
`docs/research/tools/kra_result_slot_collectors.py`. Verify private file hashes
and the already merged public markers without touching later-card results.
Use the original scoped roster and reservation for URL, page and time checks
before each network request. Save raw receipts under the designated archive. After
the closed boundary, write the terminal record atomically, including exact plan
and inventory digests only for a complete successful observation. Publish its
marker in the PR number fixed in the original rule, then capture the proof with
the existing GitHub archive helper. The caller decides separately whether the
official result policy and present corrections allow training use.

Exercise both collectors through mock HTTP and synthetic input custody, including
one approved observed result and interrupted, not-run and gateway-failed slots.
Register the tests in the existing whole-card CI step.

## Concrete Steps

From the isolated repository root, use the existing virtual environment:

    export PYTHONPATH=packages/scripts
    .venv/bin/python -B docs/research/tools/kra_result_slot_runner.py --help
    .venv/bin/python -B -m pytest -q -p no:cacheprovider -o addopts='' --import-mode=importlib packages/scripts/autoresearch/tests/test_kra_result_slot_runner.py

Use a separately authorized plan and real time only. Save the approved enrollment
and rule proofs, and the original input witness for each training slot through
the appointed week. Use `collect` only inside the fixed window; use `seal` only
after it closes. It prints a hash-only marker, even when the run could not
complete. `witness` saves the evidence of the exact normal merge in the named
PR. More precise input and command examples belong in `packages/scripts/README.md`.

## Validation and Acceptance

Show a complete bounded observation for the original races, with one terminal
marker, and confirm its version with the existing read-only verifier. A missed,
expired, interrupted, duplicated, empty, denied, or throttled observation never
becomes a selectable plan. The captured sources are not themselves an approval
or evidence of 70 percent accuracy. The original commitment, existing collectors
and prior evaluation stay unchanged.

## Idempotence and Recovery

Do not remove or replace a shared claim after an interruption. Retain raw pages
and local receipts. When a slot closes, record `failed` or `not_run` without a
replacement digest where applicable. Reprinting a recorded closure is read-only;
repeating capture for a consumed week is rejected before a network request.

## Artifacts and Notes

Keep the approved rule files, immutable run, raw sources, completion state,
`terminal.json` and its provider proof together in the private archive. Only
the hash marker is destined for the prebound public PR. This local coordinator
does not schedule itself, enforce remote machine coordination, or implement a
later correction approval journal.

## Interfaces and Dependencies

Reuse the existing Python environment, `httpx`, the shared Git and local atomic
receipt helpers, and the saved pre-race input witness. No new endpoint, package,
paid server, model runtime or scoring dependency.

Revision 2026-11-23 00:31Z: Record the complete mock capture, publication and
whole-card handoff, and clarify that a successful observation is not a fit.
