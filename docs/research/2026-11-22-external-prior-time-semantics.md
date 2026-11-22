# External form past-time semantics

Do not use the whole-race time printed in the audited Singapore Pools
past-start rows as that horse's elapsed time. The column matched the
official winner's time in every comparable row. This is a source
decision, not a comparison of forecasts or a new fit.

## Evidence and limits

The exact November 8, 13, 14 and 15 form generations have 710, 353, 459
and 698 recognized dated past-start rows. The original two panels retain
all 102 races and 1,009 declarations. The forms cover 54 fields and
match all 539 declarations in those fields. The other 48 races remain
visible without external observations.

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
| Winner only | 114 |
| Both winner and runner | 14 |
| Runner only | 0 |
| Neither | 0 |
| Outside the fixed reference dates | 2,092 |

The 128 comparisons cover 34 earlier races, not 128 independent
experiments. The 14 matches to both are all for the winner. Nine linked lines
report a field size different from the original declaration count.
Do not infer starters or scratch status from that difference. The
adjacent column labelled Sectional was not mapped to a distance endpoint.
None of these checks generalizes to another provider or an untested
layout. Generation time establishes when exact bytes existed in
storage, not when the public could use them.

## Parser correction

The original November 13 read incorrectly reported Busan race 8 gate
11 absent. PDF page 23 has the row, but its compact age descriptor
lacks a coat token. Two text readers independently counted the printed
gate headings and associated all 2,220 dated lines to their fields
and declarations. The corrected gate-11 line matches the original
API declaration on name, age, sex and assigned weight. Five earlier
lines once attached to gate 10 belong to gate 11. Four remain outside
the comparison dates; one now links to the official reference and
matches only the winning time. The initial 538 matches and 127 time
comparisons become 539 and 128, without changing the interpretation.
Neither an official result nor any frozen roster was corrected.

## Distance and grade support

| Current physical venue | Original races | Same grade, within 200 m: races / declarations | Same grade, exact distance: races / declarations |
| --- | ---: | ---: | ---: |
| Seoul | 42 | 19 / 41 | 8 / 11 |
| Jeju | 28 | no form coverage | no form coverage |
| Busan | 20 | 5 / 14 | 5 / 10 |
| Yeongcheon | 12 | 6 / 20 | 5 / 12 |
| Total | 102 | 30 / 75 | 18 / 33 |

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

Decimal and integer-centisecond checks agreed. The local record
`external-prior-time-20261122/external-prior-time-v2.json` retains
all original positions, source pins, line locations and version differences.
Its SHA256 is `fd57f48f186ece36bab3b68f9c4b6f80a70455ed1d692e73e846f13107d76d37`. The first seal
(`aea79c8cbfe78873c7e30955f890a3205de8ba3ffa3f355782e834dd54a1688e`)
is retained alongside it. See the local ExecPlan for read-only replay.
186 related tests passed. No new request, future outcome, forecast,
training admission or change to the October commitments occurred.

Use reconciled official individual times for any later time-feature
proposal. Keep external entries and earlier lines as identity/history
corroboration candidates, with their respective clocks. Keep the
published M0/API27 models, full future evaluation requirement and
70% objective unchanged.
