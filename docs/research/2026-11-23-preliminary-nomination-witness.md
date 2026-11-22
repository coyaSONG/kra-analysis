# Preliminary nomination source packet

Nomination input packet SHA256: `9e314fba0cfc59d945f0d6c1b0712b879d33976250a932e2e5094e3daa304e38`.

This digest binds an exact private packet of four official nomination
details and two earlier weekly reports. It is a source registry entry,
not a whole-card input witness, reviewed study, roster, or prediction.
After verification of this document at its exact merge, that server
event can bound when this packet existed. It does not establish the
provider's first publication or a future race cutoff.

## One new observation

The [saved official Jeju nomination list](https://race.kra.co.kr/chulmainfo/RegistStateList.do?Act=02&Sub=6&meet=2)
exposed ten first-page fields. The earliest printed date and lowest race
number on it selected Jeju November 27 race 3 before looking at detailed
rows. One existing-collector read of its linked form returned HTTP 200.
At 2026-11-22 17:19:32.285008 UTC the collector finished reading 37,677
bytes, with no retry or credentials. The existing three other detail
responses and both weekly reports were replayed, not requested again.
There was no national schedule, public-data API or result request.

The new title, venue, grade, distance and weight rule match the saved
early list: Jeju grade 5, 1000 m, handicap. All 14 printed nomination
positions have distinct profile IDs. These positions are not gate
numbers and a profile ID does not prove final declaration or starter
status. Jeju prints a most recent start date and separate 3-, 5- and
7-appearance rank fields. All 14 dates precede the observation's Korean
calendar day. Keep the rank values as printed: the aggregation formula,
inclusion of exceptions and publication latency have not been verified.
The detail does not print the mainland prize columns.

## Exact source-stage coverage

| Physical venue | Detail fields | Nomination IDs | Missing rating | Rows with both appearance prizes | Rows with all four Jeju operands |
| --- | ---: | ---: | ---: | ---: | ---: |
| Seoul | 1 | 14 | 0 | 14 | Not printed |
| Jeju | 1 | 14 | 0 | Not printed | 14 |
| Busan | 1 | 14 | 14 | 14 | Not printed |
| Yeongcheon | 1 | 30 | 0 | 30 | Not printed |

The three mainland details define the two prize fields by the entry
application day for the intended race. They do not document its exact
clock or imply equivalence to API26 six-calendar-month earnings. In the
58 printed rows, the two prize fields contain 17 and 9 literal zeros,
respectively; none is missing. These are not substituted for missing
ratings or Jeju's unprinted fields. The held Seoul handicap notice
date and one Yeongcheon trainer annotation disagreement remain linked
to their original audits, not resolved or entered as features.

The parent record's 33 observed preliminary keys remain in the packet,
including 29 without a bound detailed source here. The weekly-form
comparison spans a different set of source-stage fields. Incomplete
observed coverage is not a cancellation, a verified empty scope or the
denominator of any experiment. Final race and runner coverage is unknown.

## Next Before-Cutoff Check

When a complete official card is actually observed and its original
cutoff is fixed, compare that cutoff with the verified merge time.
Compare same physical venue, race date/number and conditions, then use
the original canonical horse IDs and corroborate identities in that
race. Record stable-ID conflicts, missing inputs and added/withdrawn
declarations without changing any race population. Keep each typed
source distinct; do not substitute Jeju ranks for prize money or invent
unobserved values. Independent review and a separate full future test
remain required. Do not modify the fixed M0/API27 pair for these fields.

Local packet: `preliminary-nomination-witness-20261123/nomination-input-packet.json`.
The six raw receipts, sources, parent evidence, collection clocks and
row identities are reserved locally. Read-only replay and an independent
raw ID/byte check reproduced the recorded scopes. The related local
suite passed 128 source, publication and fixed-pair regression tests.
No historical or future evaluation population, cutoff, approval,
forecast or score changed.
