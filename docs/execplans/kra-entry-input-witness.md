# Prove that complete API26 inputs existed before cutoff

Maintain this ExecPlan under .agent/PLANS.md in the isolated
kra-analysis-race-card-pdf checkout.

## Purpose / Big Picture

An independently observed publication time for exact input bytes lets a
future owner review point-in-time eligibility without relying on a
collector's local clock. The 254 later archived race rows lack that proof.
Use the existing whole-card source preflight and public merge reader to
make that procedure executable. This is neither a model change nor a new
study, permission to score, or prediction commitment.

## Progress

- [x] (2026-11-22) Verify the released intake and inspect the original
  whole-card and publication gates and prior local custody rehearsal.
- [x] (2026-11-22) Implement one digest-only publication path and
  read-only replay of the preserved provider responses. Ten focused
  tests pass with no real HTTP requests.
- [x] (2026-11-22) Check the unchanged October commitments and empty
  condition review registry, Ruff, and 608 focused and adjacent tests.
- [ ] Release through the required checks and normal repository merge.

## Surprises & Discoveries

Live preflight quite correctly refuses a check after cutoff. Historical
verification must instead reproduce an existing sealed packet at its
recorded readback instant, and obtain the actual time bound only from
the separately retained provider evidence. This must not reopen staging.

## Decision Log

Use the first original schedule digest and cutoff, supplied separately
from the collection receipt. Reuse the verified national/regional sources,
API26 receipts and fixed common input projection; do not create a second
source parser. A private canonical packet binds the original receipt and
schedule (which bind the raw pages) and every projected race. The public
marker is canonical JSON with only its type and the packet SHA-256. The
path in the archived merged tree is fixed by that digest. No source rows,
keys, picks, or raw files are made public.

Require a normal merge into the known repository's main branch. Read the
merged SHA and timestamp from GitHub before reading that exact tree's
file, not a mutable branch, draft or comment. Reuse the bounded witness
collector and preserve its responses. GitHub proves content existence
under the HTTPS metadata and hash trust model; it does not independently
authenticate the official source or pre-race clocks in the private file.

## Outcomes & Retrospective

The new command preserved a fictional card spanning all four venues
and ten declared horses per race. A mock GitHub client needed two GETs
and returned the exact public file at the merge commit. Offline replay
reproduced the report with no further request or write, even after
cutoff; another capture could not replace the archive. The same
procedure keeps a real late merge visible without certifying it.

The focused and adjacent test suite reported 608 passed in 45.31
seconds. Both original M0/API27 commitment hashes still match, and
the actual condition review registry was unchanged. No live racing
request, source admission, roster enrollment, fit, or prediction
occurred.

## Context and Orientation

The scope collector in
packages/scripts/autoresearch/kra_entry_scope_intake.py writes an immutable
whole-card receipt. Its neighbor kra_entry_scope_inputs.py reconstructs
the official schedule and shared M0/API27 features and refuses incomplete
or late inputs. condition_forward_publication.py reads a single PR and its
document from the merged commit, retaining and replaying exact responses.
The new kra_entry_scope_witness.py uses both without changing them.

## Plan of Work

Stage once at the real clock. Save a private packet next to a completed
intake receipt without replacement and return the exact marker bytes
only after a separate post-write cutoff check. Validate the private
packet by rehashing and replaying its full source closure before any
provider request. The witness operation can run after race day, archives
the two provider responses once, and treats a merge at or after cutoff
as late. The replay mode makes no requests and cannot create a packet.

## Concrete Steps

From the isolated repository root with the existing Python environment:

    export PYTHONPATH=packages/scripts
    .venv/bin/python -m autoresearch.kra_entry_scope_witness --help
    .venv/bin/python -B -m pytest -q -p no:cacheprovider -o addopts='' \
      packages/scripts/autoresearch/tests/test_kra_entry_scope_witness.py \
      packages/scripts/autoresearch/tests/test_kra_entry_scope_intake.py

For operation, use the original independently held schedule digest, cutoff
and completed receipt path/hash with stage, capture, and replay as described
in packages/scripts/README.md. Publishing an exact marker still requires
an authorized, normally checked PR. This plan does not publish one.

## Validation and Acceptance

Exercise raw in-memory mock responses, then an exact provider archive,
including post-cutoff replay of a timely merge. Reject incomplete receipts,
changed raw bytes, another original schedule pin, wrong marker bytes,
an impossible merge clock, reused writes and a late stage. A cutoff-time
merge is recorded separately and cannot pass. No fixture hits a real data
API or creates a real race prediction.

## Idempotence and Recovery

Stage cannot overwrite an original. Once the publication attempt directory
exists, it cannot be recreated by this tool. Preserve incomplete and failed
archives. Offline replay can be repeated without writes or changing state.
No automated retry or alternate publication is authorized.

## Artifacts and Notes

Keep the private packet, the original data and all four saved provider
archive files together. Only the two-field marker can be published.
The previously published M0/API27 predictions are separate artifacts.

## Interfaces and Dependencies

Use Python's existing local archive utilities, atomic receipt writer and
bounded GitHub witness collector. Add no package, key or server.
