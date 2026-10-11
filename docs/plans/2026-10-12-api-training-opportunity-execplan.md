# Replay API only training opportunities

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

Determine whether the original October 10-11 pre-race archive contains usable
API-only training candidates beyond the 20 PDF/API races previously fitted.
The observable result is a reproducible candidate inventory, not another model
score or training authorization. One race is one unordered three-horse target.
The future national evaluation population and the frozen M0 model stay unchanged.

## Progress

- [x] (2026-10-11 20:25Z) Re-fetched the original PR61 publication witness and replayed all 28 original source chains.
- [x] (2026-10-11 20:27Z) Exploratory raw replay found 27 API-only candidates, 283 rows, including seven races absent from the approved 20-race cohort.
- [x] (2026-10-11 20:27Z) Bounded June audit found no newly sufficient training evidence in three normalized datasets and 16 saved HTML pages.
- [x] (2026-10-11 20:34Z) Preserved the October replay as a CLI with 22 focused tests; 130 related regressions and lint passed.
- [x] (2026-10-11 20:35Z) Ran the CLI against the archived originals; all 28 races and 294 feature rows match the exploratory result.
- [x] (2026-10-11 20:36Z) Read the completed Pro strategy response (11m 56s displayed), recorded its scope and adopted future 24-column input capture as the next priority.
- [x] (2026-10-11 20:38Z) Fixed initial CI job placement: the reused M0 adapter needs the existing API/model dependency environment, not the minimal scripts environment.
- [ ] Publish the bounded findings through normal reviewed Git flow.

## Context and Orientation

`autoresearch.prerace_hash_witness` verifies the published plan and feature bundle
against live GitHub PR61 metadata and replays pinned raw sources.
`autoresearch.local_m0_inference.project_capture` projects seven explicitly named
API26 numerical fields plus seven missing flags. It validates the complete roster
but does not enforce a time cutoff itself. `autoresearch.versioned_result_observations`
replays API214 and official result HTML, requiring complete roster equality and
unique ranks 1, 2 and 3. Lower-rank exceptions can coexist with a unique top-three
observation; this is a versioned observation, not settlement finality.

The approved old review is `data/contracts/restricted_training_review_v1.json`.
It authorizes a different, 20-race PDF/API recipe. Do not change it, call its
internal fit function on new data, or relax its admission checks.

## Plan of Work

Add `packages/scripts/autoresearch/api_training_opportunity.py`. Its CLI accepts
the original plan, bundle, raw archive root and outcome plan, but pins the known
input hashes. Fetch the original publication live, then replay the existing raw
source and outcome adapters. Retain every original race in a left-joined ledger,
including void, missing, late or conflicting records. Candidate status requires
pre-cutoff publication, API capture no later than publication, exact complete
input/output roster equality and a unique observed top three. PDF ineligibility
is diagnostic only for this explicitly API-only investigation.

Add focused tests in `packages/scripts/autoresearch/tests/test_api_training_opportunity.py`
for source timing, complete roster joins, void/unknown outcomes and unchanged
feature projection. Add the test command to Python Checks beside the M0 suites. Record source pins,
the bounded June findings and completed Pro advice in a research note.

## Concrete Steps

Work in `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`.
The primary checkout is a read-only archive, not an editing target. Run:

    PYTHONPATH=packages/scripts .venv/bin/python -m pytest -q packages/scripts/autoresearch/tests/test_api_training_opportunity.py -o addopts=''
    .venv/bin/ruff check packages/scripts/autoresearch/api_training_opportunity.py packages/scripts/autoresearch/tests/test_api_training_opportunity.py
    .venv/bin/ruff format --check packages/scripts/autoresearch/api_training_opportunity.py packages/scripts/autoresearch/tests/test_api_training_opportunity.py

For the real replay, invoke `python -m autoresearch.api_training_opportunity`
with `--plan` and `--bundle` in
`.cache/autoresearch/race_card_pdf_bundles/20261009T165933.854898Z_51a041eda9e6/`,
named `input_plan.json` and `feature_bundle.json`, respectively;
`--archive-root /Users/coyasong/Developer/coyasong/kra-analysis`;
`--outcome-plan .cache/autoresearch/versioned-outcomes-20261012-plan.json`;
and a new `--output-dir` below `.cache/autoresearch/api-training-opportunity/`.

## Validation and Acceptance

Expect 28 retained races and 294 input runners, 27 unique-top-three candidate
races with 283 runners, seven additional candidates compared with the old review,
and no training approval or performance claim. Compare every feature, label,
original capture cutoff and additional membership with exploratory artifact
SHA256 `04359e468e1ef3b1836ebc06fe2cc86eaea52319b3429b5d4a48fbf17fa8c6a1`.
Negative tests must retain invalid races with explicit reasons rather than silently
drop them. Run relevant original inference, publication and outcome regression
suites, then required CI checks before a normal merge.

## Idempotence and Recovery

Each run uses a new directory and exclusive artifact writes. A failed live fetch
does not authorize use of hand-written publication metadata. Leave failed output
for diagnosis and rerun into a new directory. No original model, contract,
prediction packet or source archive is modified. No paid service is involved.

## Interfaces and Dependencies

Reuse `httpx`, standard-library time parsing and existing repository raw replay
functions. Separate a pure `assess_race(projected, outcome, audit, cutoff, published)`
policy helper from I/O so negative cases are directly testable. The only public
artifact is an unapproved candidate report. A later reviewed, fixed refit must
have its own exact corpus and recipe approval and cannot replace M0 implicitly.

## Surprises & Discoveries

Six old exclusions concern lower-rank completeness, not ambiguity of the first
three horses under the newer official cross-source outcome policy. One further
exclusion concerns PDF name joining; its API-only input still replays exactly.
The old June HTML joins identify schedules, not complete horse-level features.
The first remote Script Checks failed during test collection because NumPy is
not installed in that job. Move this test to the existing API Python job with
model dependencies; no dependency or lockfile expansion is needed.

## Decision Log

2026-10-11, Codex: preserve all original 28 races, distinguish candidate selection
from evaluation eligibility, and stop the bounded June salvage audit. Raw-backed
October expansion is stronger evidence than timestamp-only normalized June rows.
Keep this increment focused on reproducible data discovery; no opportunistic
retuning on the already seen development races.

2026-10-11, Codex: after Pro's completed strategy response, prioritize a future
24-column input adapter next. The seven new October candidates were discovered
after that consultation request; the advice is not their external approval. Close
the June audit and retain these concrete October candidates without expanding
this increment into model selection or another source-quality framework.

## Outcomes & Retrospective

The CLI reproduces 27 candidates / 283 rows and retains the one void race's 11
rows. All 130 related tests pass. Completed Pro advice is recorded; remote
checks/merge remain. The increase is a data opportunity, not seven independent validation
races or a demonstrated accuracy gain.

Revision: updated after actual replay, negative tests and completed advice.
Corrected CI job placement after observing its actual missing-NumPy failure.
Remaining work is remote publication, not implementation or local validation.
