# Same-trainer contrasts beyond the screened pace information

In the original six cards, the same-trainer pair term distinguishes
some trios in 67 of the 120 races that have no qualifying early or
closing pace contrast under any preserved route assumption. In 53
of the 304 races neither proposed interaction supplies such a
contrast under any assumption. The 304 races and 3,140 declarations
are all retained. No results, forecasts or fitted scores enter these
counts.

## Comparable scope

Replay the [API26 trainer-pair audit](2026-11-23-api26-trainer-pair-support.md)
and the sealed route, early-pace and closing-pace comparison through
the same original operand packet and entry manifest identifiers.
Match race ID, original program gate and stable horse roster, physical
venue, distance, literal grade and original cutoff. Keep the prior
source holds and the exact list of eligible historical starts. The
[newly verified November 22 result times](2026-11-23-yeongcheon-sectional-readback.md)
were not available at these original cutoffs and add nothing to this
readback.

The trainer contrast counts confirmed pairs of declared trainers
within one trio. The pace flags describe variation of the specified
centered terms within their original missingness groups. They address
different hypotheses; a positive flag does not imply a different
chosen trio, stable predictive direction, or independence between
the terms. For each card, give the same past race one route assignment
across every declaration and every candidate. Count which races
support pace alone, trainer alone, both, or neither on that joint
assignment. Do not add independently selected extrema.

## Whole-card support

| Card first date (KST) | Races | Shared assignments | Pace only or both | Trainer only or both | Either interaction | Trainer where no route supports pace |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| October 16 | 50 | 256 | 26-28 | 26 | 40-42 | 14 |
| October 23 | 50 | 1,024 | 25-28 | 24 | 39-41 | 13 |
| October 30 | 51 | 1,024 | 30-31 | 28 | 41-42 | 11 |
| November 6 | 51 | 2,048 | 29-32 | 27 | 40-41 | 9 |
| November 13 | 51 | 1,024 | 30-33 | 27 | 42-44 | 11 |
| November 20 | 51 | 2,048 | 30-32 | 29 | 41 | 9 |

The last column is a count of fields with a trainer contrast but no
pace contrast in *any* assignment, not a sum of the conditional
trainer-only counts. The separate Jeju nominal endpoint sensitivity
leaves the either-interaction range unchanged on all six cards. Of
the 53 fields not reached by either method in any assignment, 30 are
in Seoul (128 original races), 6 in Jeju (83), 11 in Busan (57), and
6 in Yeongcheon (36). Treat these groups as acquisition guidance,
not estimates of venue-specific accuracy or future coverage.

The trainer term counts at least one confirmed pair in just 868 of
the 9,650 possible trios in the 67 additional fields. It should not
be mistaken for broad evidence about every trio in those races.
Only the first 50 races have a timely independently bound original
entry packet in this comparison; 14 of the 67 come from that card.
The derived interaction flags were not published before its cutoff.
There is no new independent holdout or accuracy estimate here.

## Research decision

Keep a same-trainer contrast as a separate candidate for a fixed
single-term comparison on a new whole field: it does not depend on
comparable pace history and reaches a different part of the original
scope. Do not combine and tune the terms on these cards. Additional
independently clocked pre-race evidence for fields without either
contrast is a separate priority; verify its marginal coverage
without discarding races. Any fit requires earlier admitted whole
cards, an explicit comparison recipe and a different prospectively
registered complete evaluation. Preserve the existing M0/API27
operation and the original unordered single-trio 70 percent criterion.

## Reproduction

The local `trainer-pace-complement-20261123/trainer-pace-reach.json`
SHA256 is
`560c8c20cc018b8f52c23ed037bf1e19505188417ce794dae2004595e110c6e8`.
It stores source hashes, original cutoffs, the role and pace states
for every field and the exact shared-assignment counts. Run
`reach.py verify` in the isolated local archive. A second enumeration
reproduced the full count distribution for both pace variants across
all 7,424 per-card assignments. 174 focused and adjacent tests and
Ruff passed. No live KRA/API request, training admission, fit, new
forecast, study registration or outcome accounting was performed.
