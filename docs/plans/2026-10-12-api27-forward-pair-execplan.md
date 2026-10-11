# Connect API27 to the existing national forward comparison

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

PR88 produced an exact fixed API27 model but no future predictions. Add a small
companion runner and read-only paired evaluator so that API27 and original M0
can be observed on the same October 16-18 national races and original API26
inputs. Keep each arm's single unordered three-horse choice separate. Neither
OR-combining models nor selecting only successful predictions measures the goal.

## Progress

- [x] (2026-10-11 21:21Z) Revalidated merged PR88 checkout, read M0 source/evaluation and API27 artifacts. Previous goal turn was progress.
- [x] (2026-10-11 21:22Z) Fresh official M0 refresh still reports all three dates awaiting cards; 12 responses retained, no predictions.
- [x] (2026-10-11 21:21Z) Submitted public evidence and comparison design to authorized Pro; response is in progress, not yet advice.
- [x] (2026-10-11 21:36Z) Implemented additive runner/evaluator and raw-backed boundary tests without editing frozen M0 modules.
- [x] (2026-10-11 21:36Z) Read completed Pro response (UI 10m50s); corrected denominator inheritance and tested distinct Q/F states. No local-artifact review claimed.
- [x] (2026-10-11 21:38Z) Actual repeated 28/294 and national 50-race rehearsal matched; future path remains unbound; all 103 source/model files unchanged.
- [x] (2026-10-11 21:40Z) Final local regression suite: 229 passed, including 33 new companion cases; Ruff and protocol source pins passed.
- [ ] Push exact protocol evidence and normally merge after required checks; final closure belongs in the PR comment.

## Surprises & Discoveries

The original M0 stores `input_<race>.json` before scoring. A shared-input
comparison need not require M0 scoring success: API27 can use that exact reserved
source even when M0 has not produced a prediction. Missing source remains missing
for both. The companion must not collect a substitute source or change M0 files.

## Decision Log

Preserve PR82/84's full three-date population and publication-before-first-block-
cutoff requirement. Do not create an easier subset study when some dates fail.
Reuse the existing outcome evaluator's replay and H/F/Q/D classification (hit,
miss, pending evidence, undefined target); never duplicate outcome policy.
Decision: Codex, 2026-10-11, confirmed after completed Pro methodological feedback.

Freeze API27's first final PR88 model and receipt, not the newest fit. Use original
reserved API26 source, or the M0 packet reference if the reservation is absent.
Validate equality whenever both references exist. Report shared acquisition
and per-arm computation separately; this is operational performance with shared
intake, not independent collection reliability. No fit or automatic promotion.
Decision: Codex, 2026-10-11. Completed Pro advice supports separate fixed-arm
inference. Reserved-source independence is a deliberate refinement of the
initial M0-packet-only proposal, validated with a scoring-failure regression.

Inherit the original evaluator's final complete-population decision even when
API27 publication is missing. Keep the same N, with API27 Q rather than dropping
the denominator; no paired table until both arms are entirely binary.
Decision: Codex, 2026-10-11 21:36Z, applying completed Pro advice.

## Outcomes & Retrospective

Implementation and actual rehearsal completed. Two real replay reports are
byte-identical, with all 28/294 input rows shared, six different choices and no
accuracy calculation. National 50 retains 21 scored, 7 conflicts, 22 missing.
Final live path has no future population or predictions. Remote checks and
normal merge are the remaining delivery work, not an accuracy milestone.

## Context and Orientation

Use `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf` exclusively.
The primary checkout `/Users/coyasong/Developer/coyasong/kra-analysis` is read-only
raw history. `local_m0_forward.py` owns the original series and atomic slots;
`local_m0_inference.py` validates API26 raw bytes and scores stored coefficients.
`local_m0_evaluation.py` validates a selected exact published commitment, full
national universe and versioned outcomes. `api27_refit.py` produced the separate
model; none of those frozen modules may be edited in this increment.

Original M0 archive:
`.cache/autoresearch/local-m0-forward/local_m0_20261016_18_v1`.
Original model directory:
`.cache/autoresearch/restricted-models/20261011T125457.212167Z_4113cd1060f9`.
API27 directory:
`.cache/autoresearch/api27-refit/20261011T211226.789383Z_42d55382ed35/fit`.
Model SHA256 `5f33dfd1e45c493fc5edfd90a8250ac5e91bb841b29124e5988b657994dc17b4`,
receipt SHA256 `b91d7b85cef9038a742f2a68a616cc56c627793d5efa4046c21178d00a6833ea`.
The complete historical rehearsal plan is
`.cache/autoresearch/local-m0-rehearsal/plan-final.json`, SHA256
`619dfb72764a8ddb467047e3fd687b86f53cbb2d91d1c567d83ff2ed92985922`.
It contains both original 28-race inventory and a separate 50-race national
schedule. Historical inference is diagnostic only, never prospective accuracy.

## Plan of Work

Add `api27_forward.py` for exact model admission, fixed contract, source sharing,
first-write packets and full-population commitment. Add `api27_evaluation.py` to
call the original M0 evaluator, validate the separate companion publication and
source/packet hashes, and classify the same result rows for API27. Do not require
M0 hit/miss completeness to keep an API27 race in the denominator. Paired result
counts and rate difference appear only when both full-population arms are fully
evaluated. Report no winner or automatic promotion.

Create focused tests using the existing real collector/parser HTTP-mock fixture.
Exercise per-arm missing/late packets, missing common source, wrong parent
commitment, hash substitution, population holes, missing/late publication,
historical rejection, void/unknown results, resume invariance and read-only
archives. Add a Python CI step for numerical dependencies.

## Concrete Steps

From the isolated checkout, run new `api27_forward run` with the original root,
M0 model directory, API27 model directory, explicit M0 commitment path and hash,
and separate `.cache/autoresearch/api27-forward` output. Run `rehearse` against
the exact plan above and both models. Run `api27_evaluation` on explicit paired
commitments; publication evidence is obtained through existing live GitHub
`collect_publication`, never user booleans. CLI details will be completed with
observed run paths after implementation.

## Validation and Acceptance

Use `PYTHONPATH=packages/scripts .venv/bin/python -m pytest -q` on the new
test file plus original M0 forward/evaluation, API27 refit and witness suites,
with `-o addopts=''`. Run Ruff lint/format. Actual raw rehearsal must produce
nonempty predictions with both stored models and exactly equal API14 inputs,
while preserving all 28 inventory and 50 national races including missing or
conflicting inputs. It must not compute historical hit rates. Before and after
companion operations, hash every original M0/model file and compare membership.
Actual future output must truthfully report awaiting cards if still unavailable.

## Idempotence and Recovery

One canonical companion series and one race slot; no model/date/arm overrides,
fallback, overwrite or output in parent/model directories. Existing packets and
observations are replayed and retain their timestamps; invalid occupied slots
remain visible in commitments. Each attempt has a distinct manifest. Changed
contracts stop rather than relocating to another root. Preserve failed outputs.

## Artifacts and Notes

Live refresh `run_20261011T212155259591.json` completed
`2026-10-11T21:21:55.259586Z`; commitment hash
`115a37b728c51da1f04b51dc51e455e26e2c7d4c193268c2fcf57a78040c321f` still represents
three unknown dates. It is not a frozen complete universe or prediction record.
The completed Pro response, actual source/model artifacts and final CI evidence
must be recorded in the research note and PR closure comment. Do not claim Pro
reviewed local files or a patch it has not seen.

## Interfaces and Dependencies

Reuse existing `save`, `exclusive`, `observe_packet`, `project_capture`,
`score_capture`, `evaluate`, `publication_bound`, `observation`, `classify` and
`aggregate`. No new library, server, data collection policy or training approval.
All publication and local-clock trust limitations remain explicit.

Final contract SHA `649cfe45d3ef17ea936c79e8400b44fc45474bcee12e9f94327a57a5cd856585`
is checked in at `data/contracts/api27_forward_contract_v1.json`. Actual replay
and evaluation hashes, the preserved zero-prediction draft, Pro scope and CLI
arguments are recorded in `docs/research/2026-10-12-api27-forward-pair.md`.
Remote closure is recorded in the PR comment to avoid post-merge metadata churn.

Revision: Implementation, completed consultation, corrected denominator policy,
and actual source-backed runs recorded on 2026-10-11 21:38Z.
