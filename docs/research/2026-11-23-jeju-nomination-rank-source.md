# Jeju nomination rank summaries

Rank semantics evidence SHA256: `12d3336c35d6ce72270e8eb0854c350acbc0ee10ede0314e193eb152358b2779`.

This note supplements the [preliminary nomination source witness](2026-11-23-preliminary-nomination-witness.md).
It does not replace that packet, confirm a final roster, or authorize
use of a new feature. The 14 original preliminary rows and all 42
literal rank cells are retained.

## Documented rule and arithmetic check

The [2026 KRA Jeju racing plan](https://race.kra.co.kr/down/raceplan2026_jeju.pdf),
printed page 31 (PDF page 33), describes recent 3-, 5- and 7-start
average ranks for general handicap nomination priority. It specifies
a score of 10 for stops, disqualifications, and 10th or worse; it also
allows monthly adjustments. The exact PDF was already archived on
November 18, 2026, 21:10:30 UTC and is pinned in the private report.
The plan does not document the webpage rounding or exactly how a short
record is displayed.

Test the fixed hypothesis of one nested sequence of integer scores
from 1 to 10, dividing by the available number if fewer than the
window size are counted. Taking the union of compatible lengths across
the three tested display rules, four of 14 rows require seven or more counted events, seven permit
either a shorter or full history, and three cannot use a full
seven-event denominator. Half-up to one decimal is compatible with
14/14, half-even with 13/14, and truncation with 9/14. These are
feasible totals, not recovered past results or proof of a rule.

## Two dated readbacks

Before reading either history, choose the first row requiring a full
history and the first short-only row with exactly one joint length
and display option. Neither had a previous matching reservation.
The existing collector made one official profile read per case;
both returned HTTP 200 on November 22 at 17:31 UTC, with no retry
or credentials. Each profile's newest regular entry matches the
printed date and the archived same-day result on race and horse ID.
Both reads occurred after the independent nomination-packet witness
and are diagnostic evidence, not older observed input versions.

| Case | Visible earlier regular rows | Used denominators for 3 / 5 / 7 | Display rules that match all three | Same nominal distance and literal grade in used history |
| --- | ---: | --- | --- | ---: |
| Full-window | 15 | 3 / 5 / 7 | Half-up, half-even, truncation | 6 / 7 |
| Short-window | 4 | 3 / 4 / 4 | Half-up only | 0 / 4 |

In the full-window case, counting an explicitly labelled trial
would change the printed seven-event value; exclude trials from
that reconstruction. The short-window case's four-event average of
3.25 appears as 3.3 in both longer columns; truncation or ties to
even give 3.2. One trial has no linked result or printed finish
and stays unresolved, not zero. Neither selected regular window
exercises a 10th-place cap case. These examples do not establish
the implementation's exception policy, complete individual
histories, or every race's applicable annual/monthly rule.

## Intake boundary

The nomination summaries mix distances and grades. In particular
the short history is entirely from grade 6, though the current
nomination is for grade 5. This is not a substitute for comparable
distance/grade form or a mainland prize field. The
[Jeju registration catalog, 15133774](https://www.data.go.kr/data/15133774/openapi.do)
does not advertise these recent-average columns; no operation was
called and no substitute source equivalence is assumed.

In a reviewed future full card, keep the literals and missingness
flags rather than reconstructing omitted printed inputs from newly
read histories. Require an eligible original source witness, same
physical race and exact final-declared horse ID, and preserve the
entire frozen race and runner roster. No schedule, date, prediction
model, result policy, approval, goal or score changed.

The private evidence and both exact source receipts are held in
`jeju-nomination-rank-audit-20261123/` and the two fixed profile
capture folders. Read-only replay reproduces the digest above.
The independent prefix-sum test verifies all 42 literal cells;
139 local source and fixed-pair regressions passed.
