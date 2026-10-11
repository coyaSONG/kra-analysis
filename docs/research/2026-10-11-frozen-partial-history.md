# Frozen partial observed-history features

## Decision and scope

Implemented a selected-source reader and the separate `observed_partial_v1`
feature contract. The reader verifies the SHA-256-pinned seed, original plan,
every selected result/entry manifest and saved raw page, complete ordered source
inventory, normalized records and status counts. Appended receipts and request
reservations do not alter the view. Old collector/latest-reader behavior remains
unchanged. Original request counts and implementation metadata remain pinned
historical metadata, not independently authenticated claims.

This is a diagnostic feature artifact, not a model result. **Zero new research
model fits, API requests, paid resources or prediction submissions** were made.
No historical pre-race approval or 70% evidence is claimed. The completed Pro
consultation documented in the PR79 report recommended this separate contract;
there was no new consultation in this increment.

## Actual evidence

All 28 rosters and 294 runner appearances from the pinned diagnostic corpus
were retained, including races not selected for earlier training. Target result
labels and eligibility flags are not read by the projection. This corpus is
not the complete future national race universe and cannot replace it.

| Partial field | Non-null runners | Zero observations/count | Range |
| --- | ---: | ---: | --- |
| Ranked-finish count, 90 days | 294 | 48 | 0-5 |
| Win count, 90 days | 294 | 248 | 0-2 |
| Top-three count, 90 days | 294 | 184 | 0-3 |
| Top-three fraction among observed ranked finishes | 246 | 136 | 0-1 |
| Unresolved-status count, 90 days | 294 | 231 | 0-3 |

Counts describe returned, identity-bound observations in [D-90,D), not verified
actual starts. A zero is not a debut or proof of nonparticipation. The 48 runners
without ranked observations have a null rate, not a zero rate. There are 556
lineage links for 249 runner appearances; 45 appearances have no observations.
The entire existing H0/H1 projection is exactly equal to `projection-final.json`.
In particular, H0 remains null for all 294 runners. Every target window still
contains 76 nonempty source units, 281 empty-unconfirmed units and three units
with unresolved physical identity. These are distinct from unresolved finish
statuses within identity-bound rows.

## Quality findings

**High severity, verified collision evidence; cause unknown:** the quality
ledger retains 100 identity-bound groups, 65 pairs and 983 source rows with exact
full-roster collisions. Of the 294 target appearances, 58 have at least one
lineage link to those groups, comprising 132 links. The entire raw audit data
equals PR79's `identity-audit-v2.json` except implementation provenance. No
collision side is removed or declared correct. These records are not approved
as genuine historical starts solely because the parser verified their identity.

**High severity, verified missing identity:** 172 rows in 16 unbound groups remain
in the quality report but not in normalized per-horse counts. Full-roster matches
do not establish their physical date/venue. Empty responses are not absence
certificates. Do not remove target races or runners to improve the denominator.

**High severity for retrospective use, verified late availability:** the source
seed was materialized at `2026-10-11T13:45:53.907722+00:00`. The optional source
cutoff check passes at that local time and rejects `2026-10-11T00:00:00+00:00`
with `frozen_history_seed_after_cutoff`. This cannot authorize use for the
already-run October 10/11 races. Tests additionally bound API26 captures for
identity-unresolved units, not just normalized rows. Local clock validation is
not independent timestamp evidence, target-card validation, complete-universe
registration, feature completion before deadline, or prediction commitment.

## Reproduction and pins

Run from the isolated checkout root, selecting a new output filename:

    PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.observed_partial_projection \
      --root .cache/autoresearch/observed-history-20261011 \
      --seed .cache/autoresearch/observed-history-20261011/seed-final.json \
      --seed-sha256 0dbe7abe5bdfb0a0b422bb90bddbdf1a3face89e5016254807ba37be95c25c66 \
      --corpus .cache/autoresearch/restricted-cohort/20261011T124748.785378Z_ebdf29deaaa9/corpus.json \
      --corpus-sha256 d6598f244d6a7b7bc5e65846a4c79ee6ac96ad278b89a14268de332e77526ae2 \
      --output .cache/autoresearch/observed-history-20261011/partial-projection-v2.json

Final output SHA-256:
`b9d545cf23c729380ba7636dc2bd7851808a4afd43dd2bfcc3e038e55c426d7c`.
Prior output v1 is preserved with SHA-256
`8cd315ed220f74dfc8ae0b4ee23c553e7e130d9148e8a2b56b8d3516ddd38d5f`.
Their projected data are equal; provenance records the final strict JSON-type
comparison change. Raw caches remain uncommitted. Replays have a new output
materialization timestamp, so compare data separately from that timestamp.

## Validation and next action

349 focused tests passed, with 15 existing joblib/NumPy deprecation warnings.
Coverage includes frozen/partial, collision, old observed-history, API214,
population audit, PDF replay/bundle, restricted cohort/ablation, publication
witness and training-evidence tests. Ruff lint/format and `git diff --check`
passed. CI now runs the new frozen/partial regressions explicitly. Tests prove
later successful retries cannot replace a frozen failed view, selected failed
partial pages remain pinned, integer/boolean cache substitution fails, and
label changes cannot alter features. Synthetic test fixtures are not performance
evidence.

Before any training approval, resolve or formally review the 100-group source
quality issue without deleting the evaluation population. Before prospective
use, integrate selected history versions with real official future cards,
per-race T30 deadlines, the complete frozen national universe and independent
prediction commit observations. The current forward SQL supports B0 only;
challenger arms need an explicit contract. Paid server deployment still awaits
approval. M0/M1 and the 70% goal remain unchanged; success is not demonstrated.
