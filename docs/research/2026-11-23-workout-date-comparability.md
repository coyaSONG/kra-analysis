# Daily workout measurements are date-specific

Offline diagnostic of the KRA daily workout reports dated November 18
and 22, 2026 (KST). They are measurements on different dates, not
different renderings or a correction of the same workout. This check does
not test predictive value, approve model inputs, or register a cohort.

## Sources and clock

Replay the November 18 [Seoul](2026-11-23-seoul-daily-workout-identity.md)
and [regional](2026-11-23-regional-daily-workout-identity.md) originals
and the [November 22 edition](2026-11-23-daily-workout-edition-witness.md).
The retained independent checks bind the earlier Seoul and regional
data to November 22 at 19:24:42 and 19:34:32 UTC respectively, and the
later edition to 19:43:36 UTC. All are after the November 20-22 block's
original first cutoff, 2026-11-20 01:15 UTC. These are upper bounds on
when the exact evidence existed, not the publisher's first access times
or evidence that the reports were available before that earlier cutoff.
No new network collection was needed.

## Results by source menu

There were 1,900 earlier IDs and 1,628 later IDs. Of the 2,327 distinct
IDs across dates, 699 occurred only on November 18, 427 only on
November 22, and 1,201 on both. Every common ID agreed on the actual
source menu and literal name; two had a duration held because of an
inconsistent clock. Of the 1,199 with two usable observations, 1,058
(88.2%) changed in integer minutes and 141 were unchanged.

| Source menu | IDs on Nov 18 | IDs on Nov 22 | Both durations usable | Duration changed | Median absolute change |
| --- | ---: | ---: | ---: | ---: | ---: |
| Seoul | 879 | 772 | 598 | 523 | 2 min |
| Jeju | 359 | 307 | 192 | 175 | 5 min |
| Yeongnam | 662 | 549 | 409 | 360 | 3 min |

All 1,199 usable common IDs kept the same printed trainer-group
number. Source pairs in the order table are within that group and
menu. The menu does not establish physical workout venue. These pairs
are not independent observations.

## Results by preliminary race

Re-use the [four original detailed nominations](2026-11-23-preliminary-nomination-witness.md)
and [separately archived Jeju OPEN detail](2026-11-23-jeju-nomination-identity.md).
Of the unchanged 34 observed preliminary race keys, 29 lack comparable
runner detail and remain unassessed. The five detailed fields contain
all 84 known nomination positions, not final declarations or starts.

| Physical venue / nominal field | Positions | Both dates | Nov 18 only | Nov 22 only | Neither |
| --- | ---: | ---: | ---: | ---: | ---: |
| Jeju, Nov 27 R3 | 14 | 9 | 0 | 5 | 0 |
| Busan, Nov 27 R7 | 14 | 11 | 0 | 2 | 1 |
| Jeju OPEN, Nov 28 R5 | 12 | 12 | 0 | 0 | 0 |
| Seoul, Nov 29 R5 | 14 | 12 | 0 | 2 | 0 |
| Yeongcheon, Nov 29 R1 | 30 | 20 | 6 | 2 | 2 |
| Known positions total | 84 | 64 | 6 | 11 | 3 |

November 18 alone links 70 positions and all positions in one field.
November 22 alone links 75 positions and all positions in three fields.
Six additional positions link if counting **any dated observation**, but
all six are in a Yeongcheon field that remains incomplete. This union
counts existence only: it adds **no complete field** and produces no
mixed-date durations or ranks. Calendar ages for these five nominal
fields are 9-11 days for the first edition and 5-7 days for the second;
those ages do not establish a publication lag or an eligible lookback.

| Order comparison of two common, usable horses | Within stable source group | Within preliminary field |
| --- | ---: | ---: |
| Same strict order | 4,210 | 243 |
| Strictly reversed | 2,704 | 99 |
| Tied only on Nov 18 | 909 | 27 |
| Tied only on Nov 22 | 1,104 | 42 |
| Tied on both dates | 171 | 2 |
| All compared pairs | 9,098 | 413 |

The reversal fractions among pairs untied on **both** dates are
2,704/6,914 and 99/342 respectively. The latter is only within the
five detailed fields and their common usable runners. The comparisons
reuse horses and groups and cover only two dates. They describe observed
disagreement, not repeatability, a population interval, a weather or
distance effect, or any change in race prediction accuracy.

## Decision and replay

Do not fill a missing single-date measure from a different date. After
protecting the fixed M0/API27 forecasts, first use the
[whole-card audit](2026-11-23-workout-whole-card-audit.md) with one
common edition chosen by a rule set before viewing coverage. Verify
the next actual complete official card, both evidence clocks and its
original first cutoff. Keep distinct source, time and join failures
without excluding any race. Separately defined dated features would
need their own protocol and independent future full populations;
these two dates cannot select or validate one.

The sealed local report is `workout-edition-date-comparison-20261123/dated-workout-comparison.json`
under the separated checkout's `.cache/autoresearch`. Its SHA256 is
`31a659d0c827b0a26654b6d5f2c4d76b3d62f95138b88ea852acfbff55409e33`.
Local `compare.py verify` replays the pinned source receipts and
publication evidence and reproduces the sealed bytes; separate SQLite
queries check the two pair tables and the bulk ID and duration join.
Neither race results, model scores, nor privately recorded identities
are published here. No model was fitted or promoted.
