# Official PDF numbers do not reproduce the fixed API26 inputs

The official race card is useful for checking visible entry numbers.
It cannot replace the original API26 packet for M0 or API27. Keep all
101 original races and their declared runners in the audit. This is
not a test of predictions, active starters, or any alternative model.

## Original inputs and exact comparisons

Compare the seven operands actually read by the frozen models: age,
assigned kilograms, rating, career starts and career first-, second-
and third-place counts. Each also has its own model missing flag.
Use the exact original API26 declarations and official current-runner
PDF panel, joined on physical race, saddlecloth number, full normalized
name and the original API horse ID. Do not derive an ID from a PDF
name. The [official Seoul](https://race.kra.co.kr/down/pdf/raceView_seoul.pdf)
and [Jeju](https://race.kra.co.kr/down/pdf/raceView_jeju.pdf) guides supply
column examples; they do not establish either archived edition's clock.

The October inputs were bound in [PR #95](https://github.com/coyaSONG/kra-analysis/pull/95).
The exact PDF union was bound in [PR #100](https://github.com/coyaSONG/kra-analysis/pull/100)
on October 15 at 12:20:13 UTC, before the October 16 01:20 UTC cutoff
but after the original forecasts. The PDFs were not their inputs.
The November edition has pre-cutoff local receipts only. Keep that
state separate and do not reinterpret a current or later revision.

| Measure | Oct 16-18, witnessed | Nov 20-22, local only |
| --- | ---: | ---: |
| Original races / declarations | 50 / 534 | 51 / 540 |
| All seven values visibly numeric and equal | 240 / 534 | 247 / 540 |
| All declared runners in the field meet that test | 13 / 50 | 12 / 51 |
| Printed career placing dashes paired with numeric API zero | 532 / 532 | 557 / 557 |
| No printed rating; API zero / API null | 110 / 32 | 112 / 37 |
| Races where the same rating omission represents both states | 7 | 7 |

Every pair where both sides have numbers agrees. One October
weight cannot be confirmed from the PDF header; preserve that runner
and the grade/race entry unchanged. The dashes empirically agree
with API zero for these 1,089 career-count cells. That does not
authorize treating a dash or an unresolved cell as zero in another
layout, revision, or field. No zeros were filled.

## The blank rating is not recoverable by one default

For each race, consider a hypothetical default of either API zero or
API null for all its printed rating omissions. Even an oracle that
knows the original values when choosing the default per race must
misrepresent at least 26 October or 21 November declarations. This is
the sum of the smaller of the two original-state counts per race.
It is not prediction loss and does not rule out information from a
different verified source.

The API normalizer's numeric zero has a false missing flag. Null
uses the stored imputed rating and a true missing flag. From the
frozen coefficients alone, changing numeric zero to null while
holding everything else fixed changes the linear predictor by
about -0.280 for M0 and -0.254 for API27. Compute the two terms
`rating_coefficient * imputed_rating / rating_scale` and
`rating_missing_coefficient / rating_missing_scale`; the means
and intercept cancel. These are not probability-point differences.
No race scores, ordering, selections or outcomes for either block were
read or recomputed in this comparison.

Protect the next actual whole-card API26 freeze and the authorized
publication first. Use a separately timed PDF as a corroborating
source for its literal operands, not to invent missing flags, use an
older cohort, or rescue an expired submission. No fallback, refit,
promotion, new date, or change to the 70% success criterion follows.

## Reproduction

The local `pdf-api14-equivalence-20261123/operand-agreement.json`
pins original source and clock references, archived PDF bytes and
each literal/model state. SHA256:
`36571490367295a12d49b32fb3dd0c3af03ebcf608739e493ce634172ea4ec87`.
The local `audit.py verify` re-opens both original cards without a
race or API request. Independent Ruby accounting reproduced the
whole-card and per-race collision counts. `rating_pair_effect.py`
reads only the two pinned model/receipt pairs for the formula.
197 related tests and the nine-case focused rerun passed. No result
collection, race-source request, training or forecast took place.
