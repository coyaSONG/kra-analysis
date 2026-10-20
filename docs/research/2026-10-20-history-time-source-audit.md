# Historical time fields: source readiness audit

## Decision

The original May 1-14 API archive contains potentially useful elapsed and
sectional information beyond A24/B34's rank-based history. Its raw values are
not yet approved speed features. This audit found **30 time-named fields on
1,029 runner observations in 102 races**, with full identity linkage to the
original seed. No field conversion, model fit, target-label comparison, new
prediction, input replacement or future registration occurred.

The 70% exact-single-set objective remains unmet. This is a feature-source
readiness finding, not evidence of better accuracy. The May inventory is a
source-quality population, not a substitute evaluation population.

## Source register

| Property | Evidence / status |
| --- | --- |
| Candidate source | API214_1 original result elapsed/sectional fields |
| Provenance | Original immutable May 1-14 seed and complete selected raw pages |
| Seed SHA256 | `561bcfdc6fe2c4733e571b8c77034a2753e88794d5d7d3a6ee5d2ee2f25a5407` |
| Original local availability | October 15, 2026, 12:29:48.701488 to 12:30:47.991721 UTC |
| Selected source-clock bound | October 16, 2026, 01:20 UTC; not this audit's creation time |
| Grain and join | date + physical venue + race + gate + normalized horse ID |
| Join coverage | 1,029/1,029 seed records; no duplicate expansion or omitted exception |
| Inventory status | 12 venue/day units reported rows; 44 remain empty_unconfirmed |
| Field presence | All 30 fields present on all 1,029 rows; no null/empty/nonfinite/negative values |
| Positive total time | 1,011/1,029 (98.3%); 18 zero values kept separately |
| Future-target horse coverage | Not measured; this report does not join a new evaluation roster |
| Sectional units / zero semantics | Unknown at field/venue/distance level; not approved |
| Sectional HTML agreement | Not verified by this audit |
| Historical pre-race availability | Not verified for the May races; October acquisition is not May PIT evidence |
| Leakage risk | These are outcomes of prior races; same-target or post-cutoff records must never become target features |
| Training or production status | Unapproved; A24/B34 frozen inputs and models unchanged |

Official [API214 metadata](https://www.data.go.kr/data/15063979/openapi.do),
read October 20, describes result records and sectional fields, and defines
the start/finish-relative 200m and 600m sections. That description does not
resolve every raw field's cumulative-versus-segment representation. It is
metadata, not evidence that a particular raw version existed before a race.

## Raw field findings

| Physical venue | Races | Observations | Positive rcTime | Zero rcTime |
| --- | ---: | ---: | ---: | ---: |
| Seoul | 40 | 431 | 417 | 14 |
| Jeju | 32 | 298 | 296 | 2 |
| Busan | 30 | 300 | 298 | 2 |
| Total | 102 | 1,029 | 1,011 | 18 |

No Yeongcheon rows occur in this selected archive; empty units are not evidence
that no races happened. Do not infer Yeongcheon pace from Busan field names.

All Seoul rows have zero values in the Jeju/Busan-prefixed time columns; all
Jeju rows have zero values in Seoul/Busan columns; Busan rows have zeros in
Seoul/Jeju columns. Some same-venue fields also have fewer positive values:
Seoul `se_1cAccTime` 103 and `se_2cAccTime` 123; Jeju `je_2cTime` 27;
Busan `buG8fAccTime` and `bu_10_8fTime` 11. These are observed counts, not a
validated distance-to-section applicability rule. Pooling these fields or
treating all zeroes as ordinary missing data is unjustified.

The seed has 1,010 `ranked_finish_observed` rows and 19 unresolved rows.
One unresolved row still has positive total time: Seoul `20260510_1_9`,
gate 4, horse 51435, raw rank 91, note `실격`, rcTime 76.3.
Therefore positive time alone is not proof of a usable normal finish.
The original [May audit](2026-10-15-early-may-history.md) already withholds
that entire 11-runner race because of rank-source conflicts. This raw inventory
retains it for diagnosis and does not change that rule or explain the conflict.

## Research implication

A subsequent, separately specified source-validation step can test whether
prior elapsed/sectional history adds information not captured by rank history.
Before constructing any feature, verify the original API field documentation
and matching archived official HTML for each venue and course distance.
Separate unavailable, inapplicable, stopped/disqualified and genuine numeric
observations. Verify cumulative/segment identities without fitting conversion
rules to the 50 October outcomes. Record contradictory sources as unresolved.

Raw metres divided by seconds is not a course/going-adjusted ability estimate.
Any future proposal needs explicit venue/distance/going and race-context rules,
strict prior-race/capture cutoffs, and support/missingness reporting on the
entire later frozen roster. A24/B34's current forward comparison must not gain
new columns, thresholds or fits. Such a proposal requires separate review,
new model approval if learning is involved, and later independent validation.
The next action is source semantic reconciliation, not repeated tuning of
the same development block.

## Reproduction and validation

Saved aggregate [report](experiments/2026-10-20-history-time-audit/report.json)
SHA256: `f844015088ae10ec754bbbfa8e2f0fc0867c9bd58881bdd16bdfed454baee75c`.
It preserves original capture/page pins and its own actual analysis time.
The source audit used zero network requests. Public metadata browsing is not
counted as a dataset/API collection, and no current result version replaced an
original source.

From the isolated repository root:

    PYTHONPATH=packages/scripts PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B \
      -m autoresearch.history_time_audit \
      --root .cache/autoresearch/observed-history-extension-20260501-14 \
      --seed .cache/autoresearch/observed-history-extension-20260501-14/seed.json \
      --sha256 561bcfdc6fe2c4733e571b8c77034a2753e88794d5d7d3a6ee5d2ee2f25a5407 \
      --source-bound 2026-10-16T01:20:00Z

This command reads the complete original archive through the existing frozen
replayer before profiling. It prints a newly timestamped diagnostic, not a
pre-race snapshot; old report bytes are not overwritten. Model outcomes and
training functions are not invoked. Tests cover value-state separation,
identity-based reordering, duplicate/missing/wrong IDs, changed values and
published aggregate arithmetic. All field-state counts reconcile to the full
venue observation denominator.

Final local validation: **125 related tests passed in 1.18s**, including 24
new audit tests. Ruff check/format passed. Synthetic end-to-end replay preserves
all input bytes while network/process calls are trapped; changed raw bytes
are rejected. The six frozen A24/B34 model/receipt, future registry and M0/API27
commitment hashes remain unchanged. Remote CI/merge evidence belongs to the PR.
