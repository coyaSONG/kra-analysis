# Observe Versioned Results Across the Whole Race Population

This living ExecPlan follows `.agent/PLANS.md`. Keep Progress, Surprises &
Discoveries, Decision Log, and Outcomes & Retrospective current.

## Purpose / Big Picture

Read retained API results and official result pages together to identify a
unique observed three-horse result without discarding races with exceptions.
The output describes the particular saved source versions, not eternal finality,
bet settlement, or prediction accuracy. The existing local M0 predictor and its
frozen October 16-18 contract must remain byte-for-byte unchanged. No paid service
is needed. An actual October 9-11 replay must retain all 50 scheduled races.

## Progress

- [x] Read existing population audit, official source replay, and frozen-history
  modules; verify the existing local M0 branch is clean and merged.
- [x] Confirm retained evidence covers all 50 October 9-11 event rosters; request
  Pro advice on exceptional results and whole-population scoring semantics.
- [x] Read the completed Pro answer (9m 1s); distinguish void text, unexplained
  blanks and void/finish conflicts; add policy and source-derived observation IDs.
- [x] Implement an additive versioned-result adapter and focused adversarial tests.
- [x] Replay actual retained sources, document counts and hashes, check that the
  original M0 contract remains unchanged.
- [ ] Run local checks, push a small PR, wait for required remote checks and merge.

## Surprises & Discoveries

The old API-only audit classifies 37 races as ordinary and 13 as requiring
review, yet 49 have unique API first/second/third identities. All 50 match the
official whole roster. One race has only blank official ranks and API notes
reporting a void race. A lower-ranked blank row is not itself a second possible
top-three combination, but it also does not prove a settlement rule.

## Decision Log

Use additive modules. The current predictor hashes its implementation into a
saved contract, so changing shared inference or collection modules could invalidate
the prospective declaration. Do not re-root the study to bypass this protection.

Use executable source replay and tests rather than a notebook because the primary
deliverable is a reusable repository component. An observation describes what
specific captured source bytes say; finality describes whether results can no
longer change. The former must not claim the latter.

## Outcomes & Retrospective

Actual source replay retains 50 races, observes 49 unique top-three sets and one
void-reported race without top three, and preserves all nine count differences.
The final 22 new tests and extended 175-test regression run pass. Pro completion,
lint, format, and unchanged inference contract checks are complete. Remote
publication remains pending. No future accuracy or 70% claim exists.

## Context and Orientation

Work in `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`, leaving the
dirty primary checkout untouched. `packages/scripts/autoresearch/kra_result_population_audit.py`
already keeps the complete official schedule and diagnoses API rank observations.
`packages/scripts/autoresearch/frozen_history_view.py:replay_frozen` replays the
selected API archive and verifies its pins. A pin is a path plus SHA256 content
hash. `packages/scripts/autoresearch/official_history_support.py:replay_archive`
checks a selected set of official HTML captures against that seed.
`packages/scripts/shared/official_result_support.py:reconcile_group` compares
dated event identity, complete gate/horse sets, ranks, and elapsed times. None of
these existing files needs modification.

The frozen seed is `.cache/autoresearch/observed-history-20261011/seed-final.json`
(SHA256 `0dbe7abe5bdfb0a0b422bb90bddbdf1a3face89e5016254807ba37be95c25c66`).
Official evidence is `.cache/autoresearch/official-history-20261012-v2/archive.json`
(`eaece57cdd27ee4e348e171e04368440da9d82a4417110476f0a1a1400e934e2`).
The historical schedule is pinned by `.cache/autoresearch/prior-results/population-plan.json`.
These are local ignored research artifacts, never API credentials.

## Plan of Work

First finish the Pro consultation without interrupting generation. Then add an
observation adapter with an explicit policy version, complete-population projection,
and a read-only replay CLI. It must distinguish missing source, source conflict,
unique observed combination, and unresolved policy cases. Preserve original
exception notes and schedule-count differences. Verify both complete source rosters
before accepting any combination; never join on a convenient intersection.

Keep the initial deliverable outcome-only. Historical full M0 inference happened
after these races, so this replay cannot calculate prospective success. Future
scoring needs a separate prediction-time and population-evidence adapter, plus a
prospective policy for voids and ties. Do not introduce an accept-timing boolean.

## Concrete Steps

From the isolated checkout, implement
`packages/scripts/autoresearch/versioned_result_observations.py` and
`packages/scripts/autoresearch/tests/test_versioned_result_observations.py`.
Add its tests to the existing Scripts CI step that checks official-history support.
Run using the existing environment:

    PYTHONPATH=packages/scripts .venv/bin/python -m pytest -q packages/scripts/autoresearch/tests/test_versioned_result_observations.py -o addopts=''

Run the actual retained sources using:

    PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.versioned_result_observations --plan .cache/autoresearch/versioned-outcomes-20261012-plan.json --plan-sha256 314056646885d6112bbd392dcd7f8a20c2a934b03b6ab788090a270ee02be898 --output <new-report-path.json>

Expect 50 scheduled races, 49 unique observations, one void-reported observation,
nine count differences, and no model performance metric. The initial report hash
is `a628d93e8ceedbadd61a57a782d0de891e383fe0e1173e8b6a7f075ed241953c`.
The durable research note is
`docs/research/2026-10-12-versioned-result-observations.md`.

## Validation and Acceptance

Tests must prove full-population retention when a source is missing, no acceptance
of mismatched complete rosters or dates, ambiguity detection from either source,
preservation of lower-rank exceptions, and no success-rate output for retrospective
observations. Corrupted raw source bytes or manifest pins must fail replay. Actual
source replay must produce exactly 50 ledger rows and retain the void observation.
Check inference contract equality before publication; no new model fit is allowed.

## Idempotence and Recovery

All existing inputs are read-only. New reports use exclusive atomic publication
and refuse replacement. Preserve failed reports and use a new output name after
fixing a genuine implementation or plan error. Do not alter source bytes to pass.
Do not reset, delete, or recreate the local M0 study.

## Artifacts and Notes

Pro consultation: `https://chatgpt.com/c/6aca2dc4-d2e8-83e8-acab-e85f281c27b7`.
The completed 9m 1s response was read in full. Generation was not interrupted.
The final source replay report hash is
`86b88464eaf8b40ba0f55c1af9ba06a158d93adbaea0b25a47dfb44f3881a071`.

## Interfaces and Dependencies

Reuse the Python standard library and existing source replayers. No additional
package or paid infrastructure is required. The adapter will return one ledger
row per scheduled race with source-version provenance and an unordered numeric
horse-ID combination only when the selected evidence uniquely supports it.

Revision note: initial plan records the bounded outcome-only scope while awaiting
methodological advice; the 70% goal and original prospective inference contract
are unchanged.

Revision note: implemented and exercised the additive adapter; actual source
replay and contract comparison are complete. Publication waits for Pro's completed
advice and the final local/remote test results.

Revision note: completed Pro review and incorporated explicit void/missing/conflict
states plus source-derived observation identifiers. This bounded increment is the
outcome-only half; a future evaluation adapter must separately validate timing and
the full prospective population before calculating any performance metric.
