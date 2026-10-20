# Replay original A24 and B34 publication chains

This living ExecPlan follows `.agent/PLANS.md`. It implements the first
evidence adapter component required by
`docs/research/2026-10-20-condition-evidence-boundaries.md`, not the complete
prospective evaluator or approval to execute a study.

## Purpose / Big Picture


An archived protocol, separately published approval registry and paired
prediction must be linked without relying on today's checkout, runtime or
local attempt markers. A read-only CLI will verify these three original
publication archives and their cross-document identities, hashes and clocks.
It will preserve missing evidence as unknown and never manufacture an
absence, a verified inference, a hit or a denominator. This provides a real
input-verification stage for the remaining historical evaluator.

## Progress


- [x] (2026-10-20) Confirmed PR119 merge and clean isolated research checkout.
- [x] (2026-10-20) Inspected original protocol, registry, publication replay,
  forward runner, result arithmetic and synthetic archive fixtures.
- [x] (2026-10-20) Implement pinned byte replay and historical publication-chain audit.
- [x] (2026-10-20) Test current-checkout independence, missing/corrupt evidence, temporal
  and cross-document conflicts, roster membership and scoped arm failures.
- [x] (2026-10-20) All 262 focused tests passed in 6.35s, including 74 new
  cases and 188 existing regressions. Ruff lint passes; formatting is current.
  Stored model/commitment pins and unchanged empty registry verified.
- [ ] Inspect required CI, publish and normally merge this component.
- [ ] Later: preserve/replay original numerical environment and raw inputs,
  bind closed submission authority and complete umbrella identity ledger,
  add target admission and connect the fully verified evidence to accounting.

## Surprises & Discoveries


The existing `condition_forward_publication.replay` already checks GitHub
merge-tree bytes and metadata but reads its own files. Extracting the same
checks into a byte-only helper lets a caller first verify a fixed archive
manifest without rereading mutable files. Current `verify_local` deliberately
depends on today's admission; historical provenance must not call it.
The current registry's review timestamp can precede protocol merge, so the
historical audit must not invent a stricter past review order. Both documents
must nevertheless have been published before recorded inference for the
chain to be consistent.

## Decision Log


- Decision: audit exact original publications using a pinned manifest with
  three archive references, never caller-supplied verified/failure flags.
  Rationale: public byte existence is testable independently of current
  runtime and local loss, but not sufficient for valid inference.
  Date/Author: 2026-10-20 / Codex.
- Decision: emit publication facts and arm-scoped selection checks only;
  do not construct `PredictionEvidence` or call the outcome reducer.
  Rationale: original runtime/input replay, closed submission paths and
  population completeness are still absent. No apparent public match can
  bypass those requirements.
  Date/Author: 2026-10-20 / Codex.
- Decision: treat missing selected archive files as pending, malformed or
  hash-conflicting evidence as a blocked audit, and late publication as a
  timing fact, not automatically proven prediction failure.
  Rationale: an arbitrary selected PR does not prove absence of another
  accepted timely submission; loss of evidence cannot create failure.
  Date/Author: 2026-10-20 / Codex.

## Outcomes & Retrospective


The read-only publication component and CLI are implemented. The preserved
byte verifier is shared with the unchanged live archive wrapper. All 262
focused tests pass, including 74 new synthetic cases. Each result is explicitly
not usable for scoring; original numerical/input replay, closure and umbrella
evidence still need implementation. The overall 70% goal is not achieved.
Stored models, fit allowances, original commitments and empty prospective
registry remain unchanged.

## Context and Orientation


`condition_forward_publication.py` verifies four archive files: `pull.json`,
`document-response.json`, `observed.json` and `published-document.md`.
Their content describes an exact merged PR and exact merge-tree document.
`prerace_hash_witness.validate_publication` checks repository, document, Git
blob and merge metadata. This trusts preserved GitHub HTTPS observations,
not signatures resistant to an operator fabricating all records.

The new `condition_historical_publication.py` will read an explicitly pinned
manifest relative to its own directory. Each of its protocol, approval and
prediction references contains a PR number, repository document path,
document hash and four file pins. Approval must refer to the existing
`data/contracts/condition_forward_reviews_v1.json` path. Its matching study
entry must link the exact protocol hash/path/publication PR. Paired predictions
must link the same protocol, runtime, frozen models and training receipt.
Only declared block membership can be checked here; completeness of the
official multiweek population is a separate evidence stage.

## Plan of Work


First extract the existing archive checks into a pure byte helper and retain
the file-reading wrapper with unchanged behavior. Next implement bounded
manifest/file reads, safe relative paths, canonical JSON and digest checks,
then link the published documents. Verify canonical race IDs, exact block
membership, distinct roster horse IDs, whole-block cutoff and original
publication/computation clocks. Keep each arm's roster selection check
independent when the shared envelope is intact.

Finally expose a CLI that prints a JSON audit without writing files or using
network/Git/fit/run/stage. Missing archive evidence returns pending with the
known publication facts retained. Corruption or structural contradictions
return blocked with a reason. Even a complete public chain reports numerical
inference, source provenance, submission closure and umbrella population as
not verified. Add the test file to required Python CI and document exact CLI
usage and non-activation scope.

## Concrete Steps


From the isolated research checkout, run the following after implementation:

    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m pytest -q -p no:cacheprovider packages/scripts/autoresearch/tests/test_condition_historical_publication.py packages/scripts/autoresearch/tests/test_condition_forward.py packages/scripts/autoresearch/tests/test_condition_outcome_accounting.py packages/scripts/autoresearch/tests/test_versioned_result_observations.py packages/scripts/autoresearch/tests/test_local_m0_evaluation.py

Run Ruff lint/format on the changed modules and tests and `git diff --check`.
Use synthetic archives only. A successful CLI invocation prints a scoped
audit; it does not register races or produce scoring evidence.

## Validation and Acceptance


Tests must prove that current runtime/registry/code lookup, training, network,
forward inference and staging entry points are never invoked. Mutating
unrelated current files must leave selected historical facts unchanged.
Missing archive files must not create proven absence; pin mismatches, wrong
repository/base/PR/document, malformed manifests and conflicting identities
must block. Late witness retrieval must not become late publication, while
merge exactly at earliest cutoff is not timely. Malformed B34 selections
must not erase independently well-formed A24 selections. Neither is an
inference-valid judgment. Original inputs must be byte-identical afterward.

## Idempotence and Recovery


The CLI writes only stdout and opens no live collector. Rerunning the same
manifest rechecks the same facts at the new audit time. Original archives
are never repaired or overwritten. Preserve missing/corrupt evidence and
recover exact bytes through a separate provenance-preserving process; do not
recompute predictions or retry a consumed fit/attempt.

## Artifacts and Notes


No executable future protocol or real audit manifest is created while the
registry is empty. Synthetic fixtures are not registrations.

## Interfaces and Dependencies


Add `replay_contents(contents, number, document, expected_sha)` to publication
replay, where contents maps the four existing filenames to immutable bytes.
Add `audit(manifest_path, expected_sha)` and `main(argv=None)` in the historical
module. Use existing strict JSON, encoding, digest and timestamp helpers and
the canonical race identity validator; no new package is required.

Revision note: the initial plan isolates the original-publication stage so
the full evaluator can later consume verified facts without confusing public
existence with inference validity or population completeness.
Implementation update: added the byte-only archive verifier, bounded manifest
CLI, original publication bindings and 74 tests. Reported arm checks are
explicitly selection shape/membership, not numerical inference. No real
study was registered or evaluated.
Review clarification: timing result fields explicitly refer to the declared
protocol cutoff, because replay of official schedule-derived cutoffs belongs
to the remaining raw-input evidence stage.
