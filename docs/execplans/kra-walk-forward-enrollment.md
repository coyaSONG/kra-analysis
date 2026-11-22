# Bind a whole-card fold to advance enrollment

Maintain this ExecPlan under `.agent/PLANS.md` in the separate research
checkout. This builds on `docs/execplans/kra-walk-forward-fold.md`.

## Purpose / Big Picture

A fold pairs completed training cards with one later card held out from
training. Its existing verifier proves exact candidate and result versions
were bound by the later cutoff. It does not say why those particular older
weeks were selected. Allow the operator to publish a hash of the complete,
ordered training week roster and the held-out week before the first included
card's original cutoff. Later, check the exact fold plan against that roster
without opening any results. Omitting or swapping a week must fail.

## Progress

- [x] (2026-11-22 23:38Z) Locate the missing enrollment check and identify
  the existing independent publication and input-only replay paths.
- [x] (2026-11-22 23:42Z) Implement marker, receipt capture and read-only
  membership replay; add the cases to the chronological regression step.
- [x] (2026-11-22 23:43Z) Pass 124 local regression cases, including all 15
  new enrollment cases, and the chronological step's Ruff checks.
- [ ] Release through the normal PR and required checks.

## Surprises & Discoveries

The later fold marker fixes exact result versions before the later card,
but after outcomes for the earlier cards can be known. It therefore cannot
substitute for the earlier enrollment marker. Conversely, the enrollment
marker does not certify that a permitted result version was selected.

## Decision Log

- Decision: Identify each slot by its Monday in Korea Standard Time, using
  the official Korean race dates to check membership. Require every declared
  training week, in order, followed by exactly one held-out week.
  Rationale: The official cards are not available when the roster should be
  fixed. A gap must be explicit in the committed roster; it is not evidence
  of no races or permission to drop an enrolled week.
  Date/Author: 2026-11-22 / Codex.
- Decision: Reuse the original fold's verified input replay, not its result
  replay. Keep the new tool outside the fixed `packages/scripts` runtime.
  Rationale: The roster check should be usable before inspecting results and
  preserve the existing release fingerprints and model contracts.
  Date/Author: 2026-11-22 / Codex.

## Outcomes & Retrospective

No real weeks are enrolled by this change. The intended output is evidence
that the exact plan's input weeks match one earlier published roster, not a
finding that the roster is the only authorized one, a trial result, or
permission to train. A missing card blocks this roster; no fixture or
historical version can stand in for it.

The fictional replay matched both training weeks and the later evaluation
week without reading outcomes or changing the archive. It rejected an
omitted week, a repeated or swapped week, the wrong marker, and a merge
at or after the first cutoff. The October forecast and reserved input
hashes are unchanged.

## Context and Orientation

`docs/research/tools/kra_walk_forward_fold.py` verifies the frozen national
population and exact earlier-card results for a named plan. Its `_scope`
function replays only the original, independently witnessed input packet,
including official dates and cutoff. The existing
`packages/scripts/autoresearch/condition_forward_publication.py` captures
and verifies GitHub's merged PR metadata and the marker in the exact merge
tree. A later readback can verify an earlier merge; it does not prove the
local archive already existed at that earlier time.

## Milestones

Add `docs/research/tools/kra_walk_forward_enrollment.py` to parse a pinned
private roster, emit its exact public marker, and replay its saved PR proof
against a pinned fold plan. The policy declares ordered `training_weeks`
and `evaluation_week`, all canonical `YYYY-MM-DD` Mondays; it has the
`format` value `kra-walk-forward-enrollment-v1`. The marker reveals only
the format and policy hash. No outcome or prediction belongs in either file.

Exercise the new tool in `test_kra_walk_forward_enrollment.py` using the
same independently dated fictional source receipts as the existing fold
tests. Wire it into the chronological whole-card regression step in CI.

## Concrete Steps

In the separate checkout with the Python environment already installed:

    PYTHONPATH=packages/scripts .venv/bin/python -B docs/research/tools/kra_walk_forward_enrollment.py --help
    .venv/bin/python -B -m pytest -q -o addopts='' packages/scripts/autoresearch/tests/test_kra_walk_forward_enrollment.py

For a separately authorized study, prepare the policy before any included
cutoff and use `marker --policy PATH --policy-sha256 SHA256`. Publish those
exact bytes at `docs/research/walk-forward-enrollment-witnesses/SHA256.json`
through a normally merged PR. `capture --policy PATH --policy-sha256
SHA256 --pull NUMBER` saves that PR and merge-tree document once. There
are no KRA calls in these commands. When all original input receipts are
ready, run `replay` with the same policy and pull options and
`--plan PATH --plan-sha256 SHA256` before staging the fold or opening
its result files. Use paths relative to the separate checkout and each
file's own SHA256. If the operator replays a replacement plan, check the
new plan's hash again before relying on membership.

## Validation and Acceptance

The complete fictional fold must return `enrollment_membership_verified`
for its plan hash. A missing or swapped training week, an input assigned to
the wrong role, or a publication at the first original cutoff must fail.
Replay must neither open a result plan nor change the private archive.
The original fold verifier must still pass its unchanged regression suite.

## Idempotence and Recovery

Marker generation and replay are read-only. Capture uses a new digest-named
directory beside the policy and will not replace a saved receipt. A partial
capture is not proof; retain it and recover only through a separately
reviewed collection. A late or missing marker cannot be repaired by changing
the policy, moving a cutoff, or choosing different dates after results.

## Artifacts and Notes

The enrollment receipt only binds calendar slots to the exact plan's original
input scopes. Continue to require separate replay of the whole fold, allowed
result versions, independently reviewed live approval, and physical race
lineage where races may have been moved. Do not use it as 70% evidence.

## Interfaces and Dependencies

The tool uses the standard-library calendar and JSON interfaces and the
existing fold and publication replay. It does not import or call a new data
collector, scoring tool, fitter, or prospective prediction writer.

Revision note (2026-11-22): Record fixture and hash verification and make
the pre-result operational order explicit. This does not enroll any week.
