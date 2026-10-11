# Build Supported Recent-History Candidate Features

This living ExecPlan follows `.agent/PLANS.md`. Work only in the isolated
`/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf` checkout.

## Purpose / Big Picture

Prepare the previously proposed H1 recency features for a future challenger,
using only dated, whole-roster, rank/time-supported observations. The existing
official partial contract supplies 90-day counts but not supported recency.
The new artifact makes the extra feature values and their evidence inspectable
without fitting again on the already observed seven development races.
This is feature preparation, not demonstrated prediction improvement.

## Progress

- [x] Re-read PR76's completed Pro proposal, PR81 source reconciliation, PR82's
  fixed M0 and PR84's merged evaluator. Prior turn was verified progress.
- [x] Select an additive candidate contract without altering frozen dependencies.
- [x] Implement pure recency projection and pinned-source replay command.
- [x] Test time boundaries, same-day ambiguity, absent/withheld observations,
  target independence, source corruption, reproducibility and fixed membership.
- [x] Materialize actual 28-race/294-runner data; independently check every row.
- [x] Document evidence and limitations; pass 154 tests including 19 new cases.
- [ ] Push, inspect checks and merge normally.

## Surprises & Discoveries

Only 20 races have reviewed restricted training approval, and both original
development arms achieved 1/7. New historical backfill was acquired after those
targets; it cannot authorize retrospective training under this Goal. The PR81
support archive resolves many source concerns but does not change acquisition
time or certify complete actual start history. Its recency candidate can still
be prepared and tested for future, separately approved training examples.

## Decision Log

Use a new `official_supported_recency_v1` contract with explicit observed-source
semantics. Call the existing official materializer to replay the seed, HTML and
rosters; never trust a cached projection supplied as an approval. Retain its full
output unchanged. Derive five new values from supported lineage: 30-day ranked
count, days since the latest observed ranked date, latest rank, mean of up to
three latest ranks and newer linked-unresolved presence. Calendar dates alone
cannot order same-day events: latest rank and a split last-three boundary become
null rather than being selected by venue or race number.

Keep source gaps and withheld records visible. Observed counts may be zero but
never imply debut, no starts or a complete response history. Newer unresolved
means a returned API-unresolved record linked to an official event, not DNF.
Retain missingness, gate, venue and fixed roster size. Do not read target labels,
select races by outcomes, fit, change M0, register predictions or approve training.

## Outcomes & Retrospective

The candidate is implemented and all 294 rows were independently checked against
the original seed and official support sets. The full embedded PR81 projection
is identical, as is a second raw-source replay. Recent ranks/recency are available
for 246 appearances and null for 48. The 30-day count is zero for 178 and one for
116 appearances. No fit or accuracy estimate occurred. The full national forward
70% target remains unachieved. Remote checks/publication remain for this increment.

## Context and Orientation

`autoresearch/official_history_support.py:materialize` replays frozen raw sources
and returns `groups` with official row support, and `races` preserving each
target roster. Each supported runner has used, linked-unresolved and withheld
lineage, plus 90-day observed counts. The new script belongs alongside it in
`packages/scripts/autoresearch/official_history_recency.py`; tests belong in
the adjacent `tests/test_official_history_recency.py`. Existing files hashed by
M0 and PR84 must remain unchanged. Add a separate Scripts Checks CI step.

## Plan of Work

First implement the pure projection from the freshly replayed support report.
Validate lineage membership, uniqueness and [D-90,D) boundaries before computing.
Then add a CLI with the same explicit seed/archive/corpus pins and optional
source cutoff as the existing materializer. The output keeps source provenance,
the original projection, feature schema and false approval/performance flags.
Save atomically to a new filename; no network request is needed.

The second milestone adds synthetic counterexamples and raw-source integration
tests. The third runs the actual sources, checks feature counts and calculations
independently, writes the repository research note and publishes tested changes.

## Concrete Steps

From the isolated checkout run:

    .venv/bin/python -m pytest -q packages/scripts/autoresearch/tests/test_official_history_recency.py -o addopts=''

For actual materialization use module `autoresearch.official_history_recency`
with `PYTHONPATH=packages/scripts`, the seed root
`.cache/autoresearch/observed-history-20261011`, seed `seed-final.json` with hash
`0dbe7abe5bdfb0a0b422bb90bddbdf1a3face89e5016254807ba37be95c25c66`,
archive `.cache/autoresearch/official-history-20261012-v2` with hash
`eaece57cdd27ee4e348e171e04368440da9d82a4417110476f0a1a1400e934e2`,
and corpus `.cache/autoresearch/restricted-cohort/20261011T124748.785378Z_ebdf29deaaa9/corpus.json`
with hash `d6598f244d6a7b7bc5e65846a4c79ee6ac96ad278b89a14268de332e77526ae2`.
Choose a new output under `.cache/autoresearch/official-history-recency/`.

## Validation and Acceptance

Every original target and runner must remain. Exact day-30/day-90 records count;
same-day target and future records do not enter features. Same-day ordering
ambiguity yields explicit nulls. Empty history has zero observed counts and null
rank/recency, not invented rest. Unsupported records never affect supported
rank values. Changing target labels/eligibility must not change feature rows.
Raw hash changes fail replay; identical pinned inputs yield identical output.
Verify actual row calculations against the source lineage, not just tests or
summary totals. Existing M0/evaluator regressions must still pass unchanged.

## Idempotence and Recovery

All commands are offline replay. Preserve older artifacts and use new output
paths. Missing raw sources or pin conflicts are errors, not automatic repairs.
Do not update training approvals or the frozen M0 contract to make tests pass.

## Artifacts and Notes

The controlling Pro proposal is recorded in the PR76 research note; no new
consultation has occurred in this increment. Reconsult if new methodological
uncertainty prevents a defensible feature definition. Actual evidence and
publication closure will be recorded in the research note and PR.

## Interfaces and Dependencies

Expose `project_recency(replayed_support)` and a `materialize` wrapper calling
the existing source replayer. Reuse Python standard library and existing
dependencies only. Feature outputs are diagnostic candidates with training,
independent timing and 70% evidence flags false.

Revision note: initial plan fixes the candidate semantics before examining its
actual distributions. No model choice, hyperparameter search or new target is
introduced.

Revision note: implementation, 19 new tests and actual row-by-row validation are
complete. The first real run exposed a missing output-directory error; the CLI
now creates the parent while preserving atomic non-overwrite. Actual artifact
`.cache/autoresearch/official-history-recency/features-v1.json` is pinned by
`264a1c62d3740588c440d698b5cdb5a1494d323165804994d4e9f7db50cf52a1`.
The research note records distributions and unverified historical availability.
