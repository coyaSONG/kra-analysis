# Jeju OPEN nomination identities

Jeju nomination identity evidence SHA256: `a5be5c97ae9d6243f690162766845b2ad92d95435c9c40eab28394c3729e43c0`.

This is cross-source registration evidence, not a verification of the
final race card, starting gates, model inputs, or a prediction.

## One new detail

From the ten pinned fields on the [official Jeju first page](https://race.kra.co.kr/chulmainfo/RegistStateList.do?Act=02&Sub=6&meet=2),
select the unique longest distance. One read of the advertised detail
for November 28 race 5 returned HTTP 200, with 36,586 bytes collected
at 2026-11-22 18:21:08.292061 UTC. The original body confirms the race
date, physical Jeju, 1,610 m, OPEN, handicap and the named stakes race.
There were no retries, credentials, schedule, result, or data API
requests. No earlier page or November 27 detail was renewed.

New detail raw SHA256: `43c8f8bc44b86b3277ee1ae1222424d229f4093d52c363037aaabb9dbee2741c`.
The [weekly report](2026-11-23-jeju-weekly-nominations.md) was collected
earlier and its own exact digest was publicly bound by PR #168 at
18:19:02 UTC. The two clocks and exact reservations are preserved.
They do not establish KRA's first publication or a fixed block cutoff.

## Do not join on the two printed numbers

The original weekly report has 11 fields and 167 nomination rows.
Reopen the existing [November 27 race 3 detail](2026-11-23-preliminary-nomination-witness.md)
and the one new form. Compare rows only within a verified date, venue,
race number and literal conditions. For unique names, check sex, age,
trainer and owner separately; then report rating agreement independently.

| Preliminary field | Rows with web profile IDs | All same-race identity checks agree | Printed ratings agree | Printed numbers equal |
| --- | ---: | ---: | ---: | ---: |
| Nov 27 race 3, 1000 m, grade 5 | 14 | 14 | 14 | 0 |
| Nov 28 race 5, 1610 m, OPEN | 12 | 12 | 12 | 12 |

Neither source's position is an assigned gate. The apparent number
agreement in the OPEN race fails as a general rule in the other race.
There are no profile IDs printed in the weekly report. The 26
corroborations are against web-supplied IDs, not direct ID equality
in both sources or links to actual starters. Preserve the other nine
fields as weekly-only. The web form has no missing last-start date or
printed 3-, 5-, and 7-appearance rank value in the new field, but has
no comparable earnings field. Do not substitute those ranks for the
weekly earnings or assign a new meaning to the windows.

The opt-in `autoresearch.jeju_nomination_roster_link.audit_rosters`
expects parsed receipt-bound inputs. It rejects a different race or
conditions, retains every row when names are ambiguous or one-sided,
and reports missing and conflicting identity values without merging.
Equal numbers do not affect any outcome of the join. The checker
does not fetch data, issue feature values or admit a row to a model.

## Remaining historical support

The two [independently timed prior inventories](2026-11-23-closed-sunday-history.md)
have 41 Jeju race contexts in the preceding 90 days for these dates.
The fixed same-venue, literal-grade, within-200-m check finds 11
archived contexts for the grade-5 field and zero for the OPEN field.
The longest recorded distance in these inventories is 1,400 m.
These are context counts, not individual prior support, verified
training labels, or a claim that Jeju has no such races. For the
long-distance gap, prioritize a separately timed official archive
with OPEN races between 1,410 and 1,810 m before judging any reusable
historical feature. Keep the full future scope, including all
unsupported declarations. No outcome, fitting, model promotion,
registration or score changed.

Local packet: `jeju-open-nomination-20261123/open-nomination-evidence.json`.
A separate literal parser agrees on both row sets and both number
comparisons. The relevant local suite passed 167 tests.
