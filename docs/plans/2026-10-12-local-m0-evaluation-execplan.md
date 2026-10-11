# Evaluate the Existing M0 Forward Records Without Rewriting Them

This living ExecPlan follows `.agent/PLANS.md`; keep all progress and evidence
sections current. Work only in the isolated `kra-analysis-race-card-pdf` checkout.

## Purpose / Big Picture

Connect the fixed October 16-18 M0 prediction archive to the versioned result
adapter. A user can inspect the entire declared block, missing predictions,
source conflicts and exact matches without rerunning inference or manufacturing
historical performance. Only a live GitHub publication binding the exact selected
commitment bytes can establish an independent pre-cutoff existence bound. Local
clock evidence remains useful diagnostics, not an automatic verified hit.

## Progress

- [x] Re-read the current fixed predictor, original commitment, model admission,
  result replay and GitHub publication verifier. Prior PR83 is merged and clean.
- [x] Choose an additive read-only evaluator using the completed Pro advice from
  the previous turn; existing hashed inference dependencies will not change.
- [x] Implement full-block replay, optional live publication evidence, outcome
  comparison and complete-population aggregation.
- [x] Test positive source replay, missing/late evidence, voids, corruption,
  historical rejection and no writes to the canonical archive.
- [x] Execute against the real canonical archive and historical rejection case;
  refresh genuine card observations without changing the original contract.
- [ ] Push, inspect remote checks, and merge normally after required checks pass.

## Surprises & Discoveries

The original commitment currently has three `awaiting_card` dates and no study
or prediction pins. This is an unknown universe, not a zero-race successful test.
The existing `observe_packet` helper writes observations if absent; evaluation
must not call it. `recover_packet` is read-only and rechecks original source bytes,
stored inference and model completion time, so it can safely be reused.

## Decision Log

Use a selected commitment plus its SHA256 hash as the snapshot boundary. Never
select the latest run implicitly. Additional local files not bound by that
commitment cannot become verified predictions. A publication witness is fetched
live through `prerace_hash_witness.collect_publication`, not supplied as a boolean
or trusted local JSON. It must publish exactly the selected commitment bytes.

Support one selected publication per report initially. A later commitment cannot
retroactively prove earlier deadlines; report insufficient evidence instead.
Corrections produce a new explicit outcome plan and report; preserve older files
and disclose the selected observation version. This is a versioned comparison,
not a guarantee that official results can never be corrected.

The primary ledger distinguishes confirmed matches, confirmed misses, pending
evidence, and undefined targets. Never use the known-result subset as denominator.
When the full block is unknown, aggregate rates and bounds remain null. Local
raw combination matches are diagnostics, not the primary performance metric.

## Outcomes & Retrospective

Implemented and verified the complete read-only evaluation path. The focused run
passes 226 tests, including 23 new cases. Actual future cards remain unpublished
at the 19:38 UTC observation, so actual evaluation correctly has no denominator,
rate or bounds. Historical dates are rejected. The 70% objective is unachieved.
No paid services, new fits or production approval changes occurred. Remote
publication is the remaining step for this increment.

## Context and Orientation

`packages/scripts/autoresearch/local_m0_forward.py` stores one contract and
per-date `study.json`, `study_observation.json`, `prediction_<race_id>.json`, and
`observation_<race_id>.json`. A commitment hashes those files and lists all races.
`local_m0_inference.py` admits only the original full M0 model and fit receipt.
`versioned_result_observations.py:replay_plan` verifies result and official HTML
archives. Its returned ledger preserves all dated scheduled races and source pins.

The canonical root is `.cache/autoresearch/local-m0-forward/local_m0_20261016_18_v1`.
Contract SHA256 is `ffd068ed7c507e2cf0bef63ed2dcbebf01fdcdd0e38d89c849d03d60c448f59c`.
The existing commitment is `commitment_20261011T184203670339.json`, SHA256
`115a37b728c51da1f04b51dc51e455e26e2c7d4c193268c2fcf57a78040c321f`.
The model directory is `.cache/autoresearch/restricted-models/20261011T125457.212167Z_4113cd1060f9`.
The historical outcome plan in `.cache/autoresearch/versioned-outcomes-20261012-plan.json`
targets October 9-11 and must be rejected for this forward series before comparison.

## Plan of Work

Add `packages/scripts/autoresearch/local_m0_evaluation.py`, its focused test file,
and an API-environment CI step because admission uses the existing NumPy stack.
First verify exact contract, dates, study membership, raw hashes and read-back
times. Then replay pinned outcomes and compare horse IDs without modifying any
prediction. Finally aggregate all rows with explicit timing and outcome status.
The optional GitHub witness must be collected from the live public API and saved
outside the canonical archive. No evaluation command invokes run, fit or collect
entry sources; there is no date, clock, arm or acceptance override on the CLI.

## Concrete Steps

Run from `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`:

    PYTHONPATH=packages/scripts .venv/bin/python -m pytest -q packages/scripts/autoresearch/tests/test_local_m0_evaluation.py -o addopts=''

Run the current actual snapshot with:

    PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.local_m0_evaluation --root .cache/autoresearch/local-m0-forward/local_m0_20261016_18_v1 --model-dir .cache/autoresearch/restricted-models/20261011T125457.212167Z_4113cd1060f9 --commitment .cache/autoresearch/local-m0-forward/local_m0_20261016_18_v1/commitment_20261011T193800835644.json --commitment-sha256 115a37b728c51da1f04b51dc51e455e26e2c7d4c193268c2fcf57a78040c321f --output <new-report-path.json>

Expect exit 2, all three dates present and null metrics, not an empty successful
study. Output files use atomic exclusive publication outside the canonical root.
Actual report `.cache/autoresearch/local-m0-evaluation-final.json` has SHA256
`0d8c06a9f8d606c257401976a67d216e9669c8964fd1453da3da23c644bc2be9`.

## Validation and Acceptance

Use source-backed fixtures from the existing local runner tests for a positive
prediction chain, not invented trusted timing flags. Verify full membership,
local-only evidence remaining pending, live publication binding, cutoff equality
rejection, missing predictions, undefined outcomes and corruption. Tests must
show that current unpublished dates yield null denominator/rates, historical
outcome dates are rejected, no canonical file is changed, and the old contract
remains byte-for-byte identical. Repeat actual replay for determinism where the
evaluation time is a documented input to the internal function.

## Idempotence and Recovery

Preserve every existing archive and report. Choose a new output path on retries.
Missing observations are evidence gaps, never created by evaluation. A changed
contract is an error; do not delete or re-root the archive to bypass it. Failed
publication queries leave partial witness evidence and cannot approve timing.

## Artifacts and Notes

Previous completed Pro advice is recorded in
`docs/research/2026-10-12-versioned-result-observations.md`. It requires preserving
voids and unknowns, forbids historical full-M0 performance, and distinguishes
versioned observations from finality. The new actual evidence will be recorded
in `docs/research/2026-10-12-local-m0-evaluation.md`.

## Interfaces and Dependencies

Expose read-only `evaluate(root, model_dir, commitment_path, commitment_sha,
outcome_plan=None, outcome_sha=None, publication=None, evaluated_at=None)` and
a CLI. `publication` is an internal object returned only by the live collector;
it is not a CLI file or approval switch. Reuse existing Python dependencies and
source replayers. Do not edit any file included in the frozen inference contract.

Revision note: initial plan defines the whole-block evaluator and its evidence
boundary before implementation; it does not redefine the 70% research goal.

Revision note: implementation, source-backed tests, actual card refresh, historical
rejection and unchanged 36-file archive replay are complete. Bounds now require
every target to be defined, not merely absence of a reported void. Result policy
and adapter hashes are fixed, and extra-result conflicts are reported explicitly.
