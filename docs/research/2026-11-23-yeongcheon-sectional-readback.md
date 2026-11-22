# Yeongcheon sectional timing evidence, 2026-11-22

The exact [PR191 result version](2026-11-23-yeongcheon-dual-source-history.md)
now supports a separate historical timing check of all six Yeongcheon
races on its original November 22 card. This readback sent no
race-card, result-page or API data requests. It did not score any model.

## Scope and comparison

The join is date, physical venue, race number, program gate and stable
horse ID. The original API26 full-day roster and the official dated
HTML header establish venue 4; the API214 rows do not provide an
explicit venue. The applicable `bu*` fields in these rows agree with
the HTML segment and cumulative tables. That response-field prefix
does not make these Busan races. Both formats come from KRA. The
[API214 documentation](https://www.data.go.kr/data/15063979/openapi.do)
defines the first 200 m and last 200 m/600 m spans and lists venue 4.
Actual checkpoint positions were taken from the distance-specific
HTML labels, not inferred from the API field order.

| Distance | Races | Runner starts | Positive API/HTML cells equal | API zero, HTML structural blank | Exact endpoint checks | Inapplicable endpoint checks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1200 m | 2 | 22 | 286 | 88 | 132 | 44 |
| 1400 m | 3 | 33 | 429 | 132 | 198 | 66 |
| 1800 m | 1 | 11 | 165 | 22 | 77 | 11 |
| Total | 6 | 66 | 880 | 242 | 407 | 121 |

All six match on literal grade, distance, official rank and finish
time. The first 200 m, final 600 m and final 200 m each have a positive
direct value and exact cumulative counterpart for all 66 starts.
All comparisons use decimal seconds at the source precision. The
1,122 cells include finish time twice per start, once per table; the
counts measure agreement, not independent observations. No positive
time was imputed. The 242 structural blanks occupy absent cumulative
checkpoints and spans not possible at these distances. A zero at a
supported position is not accepted as a measurement, even if the HTML
is also blank. Retain the previous
[sectional reconciliation](2026-10-20-sectional-source-reconciliation.md)
and its observed scope; six races on one day do not establish a rule
for all Yeongcheon dates or distances.

## Availability and use

The API capture completed at `2026-11-22T20:44:04.477009Z`; its exact
raw page SHA256 is
`fe87abbc999e125a6f6e95af2c9dd6f4a038aec9acc91151583f5d20f0145df5`.
Per-race HTML receipt times, URLs, raw hashes, values and missingness
are in the new local ledger. The prior
[PR191 merge](https://github.com/coyasong/kra-analysis/pull/191)
at `2026-11-22T22:58:16Z` binds the exact observation ledger and its
raw sources. This is an independent bound on existence, not a second
authority for the measurements or the time when KRA first posted them.
It is after the original `2026-11-20T01:15:00Z` block cutoff. These
values cannot be used as pre-race inputs for that block.

Future work can test whether adding final 600 m information to an
existing early-pace baseline helps, using only completed historical
starts with exact physical venue, distance, grade and stable horse
matches and a proved availability time strictly before the new cutoff.
Freeze the join rule and baseline before the first new result; keep
all races when history is sparse. Do not pool with Busan on the basis
of shared field names or choose a feature using the same evaluation.
No future cohort, training admission or accuracy change is claimed
here. The existing November ledger remains six observed unique trios
and 45 source-missing races out of 51, not a scored evaluation.

## Reproduction

Use the isolated local archive
`.cache/autoresearch/yeongcheon-sectional-readback-20261123/`.
`timing_readback.py verify` replays the prior result version and
publication receipt, then reproduces `timing-evidence.json` byte for
byte. Its SHA256 is
`f742d4e0a3de547e175410f50ed75497b3a7309d00ba562e6044d3dd16379b95`.
The second parser checked the three named spans directly from archived
HTML and API bytes for every start. 202 focused regression tests and
the local formatting and lint checks passed.
