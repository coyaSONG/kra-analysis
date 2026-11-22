# Same-trainer pair support in six original API26 cards

The number of same-trainer pairs in a trio can distinguish combinations
beyond any sum of individual runner scores. Across six complete archived
cards this happens in 161 of 304 races, including 26 of the 50 with an
independently witnessed original input clock. The term is sparse: only
1,995 of 42,177 possible trios contain such a pair. None of these counts
is an observed hit, an accuracy measure, or a reason to select a subset.

## Source and timing

The [KRA API26 specification](https://www.data.go.kr/data/15058677/openapi.do)
lists trainer number and name in advance entry data from all four physical
venues. Use the exact original `trNo` and `trName` only; never substitute
a result-page trainer, infer an ID from a name, or combine identities
across races. Group the verified full declarations by original race,
saddlecloth and stable horse ID. Normalize number padding and name
spacing but retain unavailable names/IDs and any nonunique ID-name
relationship as separate states. All 3,140 original declarations
joined one-to-one and passed this **within-field** role check. This
does not establish global trainer identity or active starters.

The 80 original manifests and 124 response pages retain their source,
local collection clocks and exact hashes. Entry timestamps run from
2026-10-14 06:17:32.670523 UTC to 2026-11-18 07:44:20.812708 UTC,
each before its own original first block cutoff. Only the original
October 16-18 entry packets have an independent pre-cutoff bound
here: [PR #95](https://github.com/coyaSONG/kra-analysis/pull/95)
merged at 2026-10-14 06:33:13 UTC, before October 16 01:20 UTC.
Its archived merge evidence binds the same raw API pages. This is
neither the first KRA release time nor a timely publication of this
newly derived feature. All 254 later races remain local-clock only.

## Whole-field comparison

| Card first date (KST) | Races | Declarations | Nonadditive | Trios with a pair / all trios |
| --- | ---: | ---: | ---: | ---: |
| October 16 | 50 | 534 | 26 | 360 / 7,629 |
| October 23 | 50 | 518 | 24 | 364 / 7,001 |
| October 30 | 51 | 539 | 28 | 326 / 7,674 |
| November 6 | 51 | 496 | 27 | 295 / 5,879 |
| November 13 | 51 | 513 | 27 | 319 / 6,506 |
| November 20 | 51 | 540 | 29 | 331 / 7,488 |
| Total | 304 | 3,140 | 161 | 1,995 / 42,177 |

For one trio, count the pairs whose trainer IDs both pass the within-field
check and agree. A missing role contributes no **confirmed** pair, not
evidence of a different trainer. The tool retains every candidate and its
original roster. The balanced four-trio comparison uses the same fifth
runner in each trio. Compare the two triples formed from one pairing of
the other four runners with the two triples formed from another pairing.
Each runner appears equally often, so any sum of individual runner
scores cancels; only the same-trainer pair contrast can remain.

Independently, a field of at least five has a nonzero contrast exactly
when a verified group contains two runners and leaves at least two
outside that group (equivalently its size is from 2 to field size minus
2). Those four can be paired within and across the group. If no group
qualifies, there are either no pairs or a single group containing all
or all but one runner, both additive on triples. With three or four
declared runners any trio feature can be represented by runner scores.

The structural counts vary by physical venue (Seoul 54/128, Jeju 43/83,
Busan 37/57, Yeongcheon 27/36), distance (1200 m 53/76 versus 1400 m
24/62), and grade (domestic class 5: 34/59; class 6: 29/62). These
are audits of candidate geometry, not evidence of a stable venue or
class effect. The private record retains all observed grades and
distances. In the 143 other races this term is identically zero; with
common scores held fixed, it cannot directly change the selected trio
there. Re-estimating shared coefficients is different.

## Research decision and verification

Keep this as a single-source interaction candidate. It needs no prior
form join, but numeric coverage is not outcome information. This work
does not choose it over the older pace hypothesis. The [exact-trio
fit review](../execplans/kra-exact-trio-ridge-fit.md) calls for one
prespecified differing feature with common scores, missingness rules
and normalization. That comparison still needs eligible earlier
whole cards, explicit approval, and independently fixed future cards
and timely predictions. Do not fit again on the already exposed October
50 or treat the other 254 as timely validation. Neither the original
M0/API27 commitments nor the 70% criterion changes.

The append-only local `api26-trainer-pair-20261123/trainer-pair-evidence.json`
records the 304 races, complete declarations, field-level role states,
source clocks and separate independent-publication flags. SHA256:
`2556b14c6586e5418fb15fda5c8579b1be448d2db868e45c72abdd7403a2473a`.
It was generated from the original sources at 2026-11-22 22:43:31.842610
UTC. Read-only replay reproduced the exact bytes. A separate Ruby
readback rehashed all pages, independently counted triples from verified
trainer group sizes, and checked each constructive contrast.

From the isolated research checkout:

    a=.cache/autoresearch
    d=$a/api26-trainer-pair-20261123
    p=packages/scripts:$a/rating-trajectory-20261118:$a/race-evidence-registry-20261118
    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$p .venv/bin/python -B "$d/audit.py" --verify
    ruby "$d/independent_check.rb"

The focused and adjacent local suite passed 202 tests, including 11
new cases. No source data API requests, result reads, live estimates,
predictions, new registrations, or accuracy updates were performed.
