# Compare fixed historical-form predictors without fitting

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

Turn the acquired history into concrete single-three-horse selections and test
whether additional history changes their retrospective matches. This is not a
fit, a model promotion, a pre-race backtest, or evidence for the 70% objective.
The user explicitly requested predictive research rather than more API waiting.
All 671 original archived races remain in every comparison, including unknown
outcomes and runners with no history. Source capture occurred after the targets;
even target rosters are reconstructed from result archives, not frozen entry cards.

## Progress

- [x] (2026-10-13) Inspect existing fit gates, frozen contracts and outcome adapter.
- [x] Request Pro critique of a non-fitting, fixed-candidate experiment.
- [x] Implement a pinned protocol, raw replay, predictors and full-population ledger.
- [x] Pass 26 tests for date boundaries, label isolation, missingness, ambiguity and replay pins; Ruff passes.
- [ ] Execute once on the real archives, interpret all candidates and await Pro completion.
- [ ] Run regressions, document findings, commit, push and normally merge after required CI.

## Context and Orientation

Work in `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`, leaving the
owner's other checkout untouched. `autoresearch.frozen_history_view.replay_frozen`
and `official_history_support.replay_archive` validate captured API and HTML bytes.
`versioned_result_observations.observe_race` checks whole-roster agreement and
unique ranks 1/2/3. Its count argument here is the archived roster count, not an
independently observed scheduled count. Do not export it as schedule verification.
`official_history_catalog.replay` validates the June HTML-only source. No API call
or paid service is needed. Source roots and exact hashes live in the new protocol
`data/contracts/history_form_exploration_v1.json`.

## Plan of Work

First add `packages/scripts/autoresearch/history_form_research.py`. Read a pinned
protocol, replay original July12-October11 records as the target population, and
replay July5-11 plus June1-July4 as earlier sources. Never use the HTML-only source
to create target labels. Keep target identity/gate/date separate from outcomes.
Exclude source-conflict races from numeric history and retain every target slot.

Before any outcome comparison, generate five fixed arms: gate order as a weak
control, mean prior normalized rank with dual-supported 90-day history, the same
with added HTML-only 90-day history, a separately labelled expanded 180-day arm,
and expanded 90-day top-three frequency. Normalized rank is
`1 - (rank-1)/(observed prior roster size-1)`; it is not speed or field strength.
The rank mean has two fixed pseudo-observations at 0.5; top-three frequency has
two at 0.3. Scores are exact rational numbers internally; ties use gate then
numeric horse ID. No strength, window or coefficient is tuned after results.
The 180-day arm never changes the existing frozen 90-day production contract.

Every input observation must precede the entire target date and lie within the
arm's lower-inclusive window. Historical IDs and source tiers accompany scores.
Missing history receives the fixed prior; it never deletes a runner or race.
An insufficient observed roster remains an explicit unpredicted slot. Save the
predictions before joining outcome labels. Report matches, mismatches, undefined
and pending slots, and paired changes against the dual90 arm by month/venue.
Do not report a resolved-subset accuracy or select a winner for deployment.

## Validation and Acceptance

Run from the checkout root with `PYTHONPATH=packages/scripts` and `.venv/bin/python`.
The new module accepts `--plan`, `--plan-sha256`, and a fresh `--output-dir`.
It saves exclusive prediction and report artifacts; a second run requires a new
directory. Tests under `packages/scripts/autoresearch/tests/test_history_form_research.py`
must exercise duplicate identities, strict prior-day boundaries, source overlap,
exact tie ordering, zero history, altered outcome labels, void/ambiguous outcomes,
unchanged target membership and raw tampering. Run existing history, outcome and
M0/API27 regressions, Ruff and diff checks. Real acceptance requires nonempty
predictions for actual archived races and a complete status ledger, not fixtures.

## Decision Log

Use fixed predictors rather than bypass the repository's research-fit approval
gate. Their formulas are hypotheses for feature development, not fitted models.
Do not use present-race rank, recorded time, odds, or an outcome-derived subset
as a predictive input. Target IDs and gates remain post-result reconstructed
context, so chronological exclusion alone does not prove historical availability.
Record all five arms, including weak results. Pro advice is pending and is not
authorization to relax source or training gates.

## Surprises & Discoveries

The repository already contains an explicitly reviewed 20-race fitting recipe;
its review does not cover the newly acquired archive. June history is outside
the frozen October 90-day window. A separate 180-day exploratory arm can measure
its historical value without silently changing that contract.

## Idempotence and Recovery

Never modify source caches, frozen M0/API27 modules, fit reviews, or previous
outputs. Raw data and secrets remain ignored and local. Fail on pin or membership
mismatch, and preserve incomplete artifacts as incomplete rather than overwrite.
Normal PR merge only after required checks; document existing security failures.

## Outcomes & Retrospective

Pending actual execution. The 70% goal remains unverified regardless of these
retrospective diagnostic results.

Revision 2026-10-13: establish concrete non-fitting model research using existing
history, so useful predictive experiments do not depend on API recovery.
