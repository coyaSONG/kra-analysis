# Preserved sectional time reconciliation

## Finding

All **102 races / 1,029 runner observations** in the original May 1-14 seed
were linked to the original official HTML by event, gate and horse ID.
Across **10,932 same-venue API-to-HTML time-cell comparisons**, 8,771 positive
values exactly equal the HTML minute/second representation and 2,161 API
zeroes correspond to HTML blanks. There are no observed numerical conflicts
or unparsed cells in this archive.

The comparison resolves a concrete parsing risk: **Busan cumulative columns
change order with race distance**. A fixed S1F-first column mapping is wrong
for most distances in this archive. The new diagnostic validates the complete
known header before comparing values and rejects unobserved layouts.

This is source-quality evidence, not model performance or training approval.
The 70% single unordered three-horse exact-success goal remains unmet.

## Population and source register

| Physical venue | Races | Runner observations | Positive equal cells | API zero / HTML blank |
| --- | ---: | ---: | ---: | ---: |
| Seoul | 40 | 431 | 2,728 | 720 |
| Jeju | 32 | 298 | 1,803 | 581 |
| Busan | 30 | 300 | 4,240 | 860 |
| Total | 102 | 1,029 | 8,771 | 2,161 |

The denominator is **cells**, not independent runner observations: Busan has
both segment and cumulative tables, and its elapsed race time is checked in
both. Other-venue zero-filled API columns are not compared to nonexistent
HTML columns. All 30 time-named API fields have a same-venue correspondence
somewhere in this archive; the report gives each field's full denominator
within 18 venue/distance groups. No matching-only subset was selected.

The original acquisition inventory retains 12 row-bearing units and 44
`empty_unconfirmed` units. No empty response is reclassified as no racing.
There are no Yeongcheon observations here; this evidence does not support a
Yeongcheon time-field mapping or future roster coverage.

Source root: `.cache/autoresearch/observed-history-extension-20260501-14`.
API seed SHA256:
`561bcfdc6fe2c4733e571b8c77034a2753e88794d5d7d3a6ee5d2ee2f25a5407`.
Official archive SHA256:
`8ca56ba232156beb824e9baab1f4c8c5b301e8d619f81e17d1213e8f6512e1bd`.

API local captures span October 15, 12:29:48.701488 to 12:30:47.991721 UTC;
official HTML spans 12:31:23.239204 to 12:32:09.211189 UTC. Original receipts,
canonical URLs, page hashes, roster identities and clocks are replayed before
any comparison. These are local acquisition times, not verified upstream
publication times or proof of pre-race availability for the May races.
The source-clock bound is the original October 16, 01:20 UTC cutoff;
the newly produced audit uses its actual October 20 analysis timestamp.

## Labelled column correspondence

The [official API214 metadata](https://www.data.go.kr/data/15063979/openapi.do)
describes result and sectional data, with F denoting 200m, S1F the initial
200m and G1F/G3F the final 200m/600m. It does not, by itself, establish the
raw names' ordering or zero-value meanings.

In the preserved Seoul HTML, S1F, corner and G1F/G3F checkpoint values appear
under cumulative timing. API `seG1fAccTime` and `seG3fAccTime` numerically
match those checkpoint columns, **not** the separate final-section durations.
For example, the first finisher in `20260502_1_1` has total 75.6 seconds,
G3F checkpoint 37.4 and final 3F duration 38.2. Reusing 37.4 as a final
600m duration would mix cumulative and segment concepts. This example does
not authorize a derived feature.

Busan's two tables explicitly distinguish segment and cumulative timing.
The observed first three cumulative columns map as follows:

| Distance | First column | Second column | Third column |
| --- | --- | --- | --- |
| 1200, 1300, 1400m | G8F | G6F | S1F |
| 1600, 1800m | G8F | S1F | G6F |
| 2200m | S1F | G8F | G6F |

The exact distance-labelled headers and API names are preserved in the report.
For example, the 1200m first finisher in `20260501_3_1` has blank, blank,
13.6 seconds in these columns: they match zero G8F, zero G6F, positive S1F,
not zero S1F and positive G6F. At 1300m the G6F column is labelled 100m,
whereas S1F remains 200m. Unobserved distances, including 2000m in this
archive, are not extrapolated from these six layouts.

Jeju's labelled S-1F, corner, G-3F and G-1F cells also agree numerically.
There is no universal raw-column-order rule across physical venues.

## Remaining risk and next action

The zero/blank relationship is confirmed only as a paired representation.
It does not distinguish inapplicable checkpoints, missing measurements,
nonfinishers or other causes. API and HTML can share an upstream source,
so agreement is not independent truth verification.

The prior [May audit](2026-10-15-early-may-history.md) still withholds the
entire 11-runner `20260510_1_9` race for rank-source conflicts, plus other
unsupported observations under its existing rules. Positive times and this
new agreement do not reinstate them or explain the rank discrepancy.

Source readiness is **partial**: identity linkage and numerical cell
correspondence are confirmed for this archive; zero semantics, other course
layouts and pre-race historical availability remain unverified. The next
useful step is a separately reviewed candidate-feature specification using
only previously supported prior starts, explicit venue/distance support and
missingness, then measuring coverage on a future complete frozen roster.
Do not fit transformations against the 50 October development outcomes.
Do not append time features to the frozen A24/B34 forward comparison.

## Reproduction and checks

From the isolated checkout:

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B \
      -m autoresearch.sectional_source_audit

The command prints a freshly timestamped diagnostic. It makes no network
requests or writes and does not import a learner or prediction runner.
The saved [report](experiments/2026-10-20-sectional-reconciliation/report.json)
has SHA256
`bb2d9ce7031efa252618a5411b3cb8530c028066aac1164671f0a7eb9a06badb`.
It includes source receipts, original URLs/hashes, all observed layouts,
per-field counts and a separate discrepancy list.

Local validation: 191 related tests passed, including changed headers,
distance mismatches, duplicate/missing gates, reordering, malformed values,
changed source hashes and retained numerical conflicts. The A24/B34 model
and training receipt hashes, empty forward registry and M0/API27 prediction
hashes remain unchanged. No training, new predictions, model promotion,
future date/sample-size registration or changes to exclusions occurred.
CI and normal-merge receipts belong to the PR.
