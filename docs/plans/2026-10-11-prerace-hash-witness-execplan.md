# Verify A Pre-Race Public Hash Commitment

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

The 2026-10-10/11 PDF feature archive may have stronger timing evidence than
previously recorded. PR61's GitHub merge event precedes those races and its
immutable merge tree contains hashes of the actual local input plan and feature
bundle. Verify that chain to establish a latest possible existence time under
explicit GitHub/hash/collector trust assumptions. Do not turn a hash commitment
into official-source authentication, prediction registration, a full national
evaluation universe, or automatic training approval.

## Progress

- [x] Verify PR73 is merged and resolve its CI skip question: all PDF tests ran in the separate dependency-enabled Scripts job.
- [x] Confirm PR61 server merge time is 2026-10-09T17:08:16Z and inspect its exact merge-tree document.
- [x] Send the new evidence question to the user's selected Pro model; response is generating and must finish without interruption.
- [x] Implement bounded live GitHub evidence acquisition and complete local source replay.
- [x] Exercise tampering, late publication, wrong tree, incomplete joins and original eligibility preservation: 28 focused tests pass, 462 regressions pass.
- [x] Run the actual 28-race archive: 28 source chains have a pre-cutoff content bound; 27 races/282 feature rows reproduce; the original blocked race remains blocked.
- [ ] Read the completed Pro response, reconcile its advice with actual evidence, and publish tested work.

## Surprises & Discoveries

The previous archive report described only local capture timing. Its feature
bundle and input-plan SHA256 values were already present in the merge tree
`f794ffc24414117420004ca45bd8ae20a04385db`. GitHub REST currently reports that
tree was merged before either race day. Client-controlled Git author/commit
dates and mutable PR descriptions are not used for this inference.

## Decision Log

Decision: verify a bounded, explicit PR/document/artifact chain using existing
replay functions, with no change to production training admission.
Rationale: this can yield actual positive source evidence rather than another
empty approval mechanism. External publication is an existence bound, not a
replacement for feature semantics and source review.
Date/Author: 2026-10-11, Codex.

## Context and Orientation

`autoresearch/kra_race_card_pdf_bundle.py` exports a local feature bundle and pins
an input plan. The plan records all 28 races and exact raw manifest/PDF hashes.
`autoresearch/kra_race_card_pdf_replay.py` verifies the original PDF and API26
pages, reparses values, and checks complete identities and pre-race timing. The
current production registry remains empty, and retrospective 2025 sources are
not approved. The October archive is a training-source candidate, not a new
holdout. Results for these dates have already been examined.

## Plan of Work

Add `packages/scripts/autoresearch/prerace_hash_witness.py`. Fetch the public PR
record, require a completed merge into the named repository, then fetch the
exact document at that merge commit through GitHub's contents endpoint. Preserve
the raw API response bytes, document bytes, retrieval time and hashes locally.
Validate the returned file identity and Git blob hash; require both actual
artifact SHA256 values in the document. Replay every race from the pinned plan,
compare the old exported feature rows with the current projection, and report
the external existence bound separately from capture timestamps and eligibility.
Record implementation drift; do not bypass the old plan's production checks.

Add focused tests in `packages/scripts/autoresearch/tests/test_prerace_hash_witness.py`
and run them in the PDF-enabled CI step. Use the existing synthetic original
capture fixture for a genuine parser/replay test, not only mocked success flags.
Store actual evidence and the completed Pro advice in a repository research
report after the live run. Never publish API credentials or private chat URLs.

## Milestones

First, test the external commitment and retained-byte contract. Second, prove
that the actual input plan and bundle and all their source paths still match
the pre-race publication hashes. Third, determine the smallest source-reviewed
training-cohort follow-up from those findings and the completed Pro response.

## Concrete Steps

From the isolated repository root, run the new module with the existing bundle
directory `.cache/autoresearch/race_card_pdf_bundles/20261009T165933.854898Z_51a041eda9e6`,
archive root `/Users/coyasong/Developer/coyasong/kra-analysis`, PR61, and the
document `docs/research/2026-10-10-verified-pdf-feature-archive.md`.
Use fresh timestamped output directories. Run focused pytest with `-o addopts=''`,
Ruff lint/format, and the existing source/training regression set. Check the
exact head's required CI and merge normally only after it passes.

## Validation and Acceptance

Wrong/unmerged PRs, missing hashes, changed blob content, wrong paths, changed
local files, late merge times, invalid clocks, duplicate/missing race records,
and replay drift must never produce approved features. The actual report must
keep all 28 inventory races and the original blocked race. Expected source
eligibility is 27, to be measured rather than asserted. No model fitting,
production approval, accuracy, or prediction registration is part of this audit.

## Idempotence and Recovery

Read original caches without editing them. Preserve each acquisition separately,
including failed attempts. Never backdate the retrieval timestamp or change
captured timestamps. The current main implementation replays old data under its
own recorded fingerprint; it does not pretend to be the originally pinned
implementation. Retry the same live source in a new output directory if needed.

## Artifacts and Notes

Expected artifact hashes are feature bundle
`8061a185401bf72c4bfee2751529acb164b695eb2985dbf4d6a43e187a8ecdd6`
and input plan
`0ac4a309d07901d6f4da8c4503c937fee9529fb5e05871cfdcd5252116a52be0`.
The new report must independently derive these from retained bytes.

## Interfaces and Dependencies

Use existing `httpx`, JSON/hashlib/base64, bounded local replay readers and the
existing PDF projector. Public unauthenticated GitHub reads require no credential
handling. The evidence collector has a bounded request timeout; the Pro response
does not have a short generation deadline.

## Outcomes & Retrospective

The actual chain supports a positive public content-existence bound for all 28
retained races under the explicit service/hash trust model, with 27 source-review
candidates. A candidate corpus with independently reviewed labels and the completed
Pro advice remains to be addressed. Pro advice alone is not approval.

Revision: initialized on 2026-10-11 after checking a previously overlooked
server-timed publication of the original archive hashes.

Revision: after actual execution, recorded 28/27/282 evidence and 462 passing
tests. Original source files, timestamps, model and training registry are unchanged.
