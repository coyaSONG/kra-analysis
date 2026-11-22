# External form past-time semantics

Do not use the whole-race time printed in the audited Singapore Pools
past-start rows as that horse's elapsed time. The column matched the
official winner's time in every comparable row. This is a source
decision, not a comparison of forecasts or a new fit.

## Evidence and limits

The exact November 8, 13, 14 and 15 form generations have 710, 353, 459
and 698 recognized dated past-start rows. The original two panels retain
all 102 races and 1,009 declarations. The forms cover 54 fields and
match 538 declarations. The other 48 races remain visible without
external observations. One missing printed declaration in a covered
race stays missing; it was not removed from the original.

Compare only with the [original October 16-18 result
version](2026-10-18-full-block-paired-results.md), whose digest was
public by PR #107 at 2026-10-18 09:57:21 UTC, before all four
form generations. Reuse the full, unchanged 50-race reference.
A match requires an unambiguous stable horse ID joined from the
current declaration, earlier date, physical venue, earlier gate,
distance, numeric or open class, and rank. The runner and the unique
rank-1 horse both need agreeing official HTML and API times. Compare
exact decimal values, without a rounding tolerance.

| Printed whole-race time compared with official values | Past lines |
| --- | ---: |
| Winner only | 113 |
| Both winner and runner | 14 |
| Runner only | 0 |
| Neither | 0 |
| In scope, horse identity unlinked | 1 |
| Outside the fixed reference dates | 2,092 |

The 127 comparisons cover 34 earlier races, not 127 independent
experiments. The 14 matches to both are all for the winner. The one
unlinked line is retained without a time match. Nine linked lines
report a field size different from the original declaration count.
Do not infer starters or scratch status from that difference. The
number in parentheses was not mapped to a sectional endpoint.
None of these checks generalizes to another provider or an untested
layout. Generation time establishes when exact bytes existed in
storage, not when the public could use them.

## Distance and grade support

| Current physical venue | Original races | Same grade, within 200 m: races / declarations | Same grade, exact distance: races / declarations |
| --- | ---: | ---: | ---: |
| Seoul | 42 | 19 / 41 | 8 / 11 |
| Jeju | 28 | no form coverage | no form coverage |
| Busan | 20 | 5 / 13 | 5 / 9 |
| Yeongcheon | 12 | 6 / 20 | 5 / 12 |
| Total | 102 | 30 / 74 | 18 / 32 |

Count each current declaration once per condition if it has a linked
earlier start in the preceding 90 calendar days at the same physical
venue and with the same **literal KRA grade**. This is support from
the fixed earlier archive, not the horse's full history. In particular,
the November 8 Yeongcheon 2000 m grade-2 race still has no such link
within 200 m in this reference, even though all ten declarations have
a [matching external roster](2026-11-22-external-nov08-form.md).
These counts are not accuracy, a scoring population, or evidence to
broaden a distance rule.

## Verification and decision

Two PDF text readers reproduced all 2,220 comparison signatures;
decimal and integer-centisecond checks agreed. The local
`external-prior-time-20261122/external-prior-time.json` retains all
original positions, underlying source pins, line locations and states.
Its SHA256 is `aea79c8cbfe78873c7e30955f890a3205de8ba3ffa3f355782e834dd54a1688e`.
See the adjacent local ExecPlan for the read-only reproduction command.
181 related tests passed. No new request, future outcome, forecast,
training admission or change to the October commitments occurred.

Use reconciled official individual times for any later time-feature
proposal. Keep external entries and earlier lines as identity/history
corroboration candidates, with their respective clocks. Keep the
published M0/API27 models, full future evaluation requirement and
70% objective unchanged.
