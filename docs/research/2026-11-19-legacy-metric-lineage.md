# Archived overlap score and the exact-triple target

The historical `0.667` is mean partial credit, not a 66.7% exact-triple
hit rate. The [original experiment note](../knowledge/experiment-2026-03-15-autoresearch-heuristic-optimization.md)
is preserved as a record of its own metric. Neither the reported scores
nor the replay below count toward the prospective 70% goal.

## What the archived artifacts reproduce

The audit read the frozen tree at
`b8880d9e08794b438cc5bdec01889c05fd069caa`. It ran only the old fixed
heuristic and scoring functions on the preserved race and answer
inventories. It did not run a collector, training, a parameter search,
or the original LLM fallback. A separate relational calculation
confirmed the complete 0/1/2/3-match histograms.

| Archived inventory | Races with answers | Mean partial credit | 0 correct | 1 correct | 2 correct | 3 correct |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `mini_val`, 2025-09-05 to 2025-10-19 | 200/200 | 0.640 | 6 | 40 | 118 | 36 |
| `holdout`, 2025-10-19 to 2026-02-14 | 500/500 | 0.667 | 9 | 105 | 263 | 123 |

Each race in these two archives has one valid three-gate selection and
one three-gate answer in the archived roster. All were counted. In the
500-race archive, the legacy score awards one third per correct horse:
`(105 + 2*263 + 3*123) / (3*500) = 2/3`. Under the exact definition the
same **retrospective** selections match `123/500 = 24.6%` (377 miss).
The corresponding archived total for `mini_val` is 36/200 (18.0%).
These are not independently published pre-race forecasts. The older
reported `set_match=0.700` has no separately verified exact-run receipt
here and is not evidence that the exact target was ever reached.

The note also reports 0.612 for 1,842 races. The tree contains 1,758
distinct 2025 race keys with 1,758 matching answers. The original
1,842-race calculation and population could not be reconstructed;
no whole-sample exact rate is reported for it. The annual archive
overlaps all 200 mini-val keys and 375 of the 500 holdout keys. Do not
pool those inventories or treat them as independent validation periods.

## Why this does not validate a pre-race model

- The archived scoring code reads `winOdds` and breaks ties using
  `odds_rank`. The snapshot code selects records with results and also
  uses raw `winOdds` to filter the archived roster. In the same tree,
  `collect_race_data` loads the raw race information through
  `API214_1/RaceDetailResult_1`; the adapter preserves the raw item
  fields. All 7,545 runner rows in the 200- and 500-race splits have
  positive `winOdds`. No per-row source/cutoff timestamps were found
  in the checked clock fields, and no exact pre-race odds receipt was
  verified. The result-source path is not a pre-race odds witness.
- Same-race split fields also survived in the archive. The frozen
  heuristic does not read those fields; this does not make the whole
  snapshot safe for feature exploration. Unchanging horse counters
  also do not prove that the version of each value preceded the race.
- Selecting historical database rows that already have results does
  not prove that the complete official calendar was included. The
  deterministic counts above describe the retained archive, not
  polling uncertainty or model accuracy on unseen races.

Do not carry these odds, flattened result rows, or unverified counters
into an as-of training dataset. A career placement signal remains a
hypothesis only when its exact version and early availability are
witnessed separately. Its next test requires a separately registered
whole future population and timely public predictions, not more
selection on these archived outcomes.

The [original PR95 comparison](2026-10-18-full-block-paired-results.md)
remains 0/50 for each of M0 and API27. The models, source commitments,
evaluation windows and the 70% objective are unchanged.

## Reproduction evidence

Git tree paths: `packages/scripts/autoresearch/prepare.py`,
`packages/scripts/autoresearch/train.py`,
`packages/scripts/autoresearch/snapshots/`,
`packages/scripts/shared/data_adapter.py`, and
`apps/api/services/{collection_service,kra_api_service}.py`.
The local aggregate replay and independently computed count receipts
were sealed with SHA-256
`2d5958a487de9ff9b4472df83fa3febd31e19bfbcb24be670fdffeb9a9b89a01`
and
`097bccfd129e8213dddf9f2613fba23549e705083bc818193a86cd2cd5d76ee9`,
respectively. All 89 local checks passed, including the existing M0,
API27 and result versioning regressions. No race data or per-race
predictions are added by this note.
