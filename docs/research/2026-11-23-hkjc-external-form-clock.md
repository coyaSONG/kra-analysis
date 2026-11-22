# HKJC Korea form: race-level clocks

In this edition, HKJC's past-form race and sectional clocks repeat
across different runners in the same earlier race. Do not use them as
individual elapsed or split times. This is a source decision, not a new
model, training admission or forecast evaluation.

## Edition and scope

The [HKJC announcement][release] lists two Korean simulcasts on
September 7, 2025. In the [combined form guide][guide], their domestic
keys are Seoul race 7, Korea Sprint (1200 m), and Seoul race 8, Korea
Cup (1800 m), both Grade 3. The overseas slots S1-1 and S1-2 are not
domestic race IDs.

The starter pages (3-4) and runner profiles (9-13 and 16-19) agree on
all 13 and 11 printed program numbers, respectively. These are 24
nominal declarations within the PDF, not verified KRA starters. The
source has not been joined by stable horse or race ID to an official
KRA archive. The two selected stakes fields are not evidence of
coverage for any complete national card.

## Repeated times and missing values

The 24 profiles list 120 dated previous-start lines: 80 marked KOR and
40 foreign. Two PDF readers agreed on every date and on the whole-race
clock and printed sectional entries of all 80 Korean lines. The 40
foreign lines were retained but not timed here.

Group candidate previous races by the printed date, physical track,
distance, condition, purse, field size and three finishers, without
using any clock value for linkage. Require different current
declarations, old draws and ranks among the members. Of the 80 Korean
lines, 77 had enough printed context for this check; three ambiguous
podiums were held. All 16 repeated groups (51 lines) have one whole-race
time and one identical sectional vector per group. For example, in
the candidate for April 13, 2025 Seoul 1200 m, six runners have ranks
1, 2, 4, 8, 9 and 12 with identical clocks. These are within-guide
candidate joins, not 16 independently confirmed official race IDs.

| Previous distance (m) | Korean lines | Printed numeric sum equals race time | Printed numeric sum differs |
| ---: | ---: | ---: | ---: |
| 1200 | 31 | 31 | 0 |
| 1400 | 9 | 9 | 0 |
| 1600 | 16 | 16 | 0 |
| 1800 | 7 | 0 | 7 |
| 2000 | 15 | 0 | 15 |
| 2300 | 2 | 0 | 2 |
| Total | 80 | 56 | 24 |

The 80 vectors contain 289 numeric entries and 31 printed dashes
(all at 1200 m). A dash is not a timed zero; the comparison sums
only visible numbers. Do not infer start or finish boundaries for
individual segments, fill missing values, or reconstruct a horse's
time from the nearby position and margin fields. The audit does
not establish that one of these clocks matches the official winner
or identify the timing algorithm. The related [Singapore Pools
audit](2026-11-22-external-prior-time-semantics.md) matched a
different provider's fields against official individual times.

## Provenance and admission

The Korea section labels its information September 5, 2025. Another
section of the combined file is dated September 6. The PDF's creation
and modification metadata are September 5 at 09:41:32 UTC and
September 6 at 03:03:22 UTC; the HTTP Last-Modified value is September
6 at 03:21:32 UTC. These distinguish dates and versions, but neither
the announcement nor metadata independently witnesses these exact
bytes before any historical forecast cutoff.

One direct public GET returned HTTP 200 (7,965,382 bytes), observed
at `2026-11-22T20:22:33.711315Z`. Body SHA256:
`55d594f0d739a8a502f3549ddd22fc8076332ac45e250fe1cf9281ba2d53dbeb`.
The local `hkjc-seoul-form-source-20261123` reservation retains the
source, request and completion times, receipt, original bytes, row
locations and missingness. Its replay-verified aggregate
`guide-source-audit.json` has SHA256
`fec1c3c6411aae3a0d02faf329f4d25c77691e531211dd715dda4814cdac9d13`.
The PDF and runner-level readings were not republished.

Use only as possible context corroboration when the exact edition's
pre-cutoff acquisition and eligible joins are independently verified.
Official individual times with known availability remain necessary
for a horse-level timing feature. No new scoring, cutoff, frozen
population, M0/API27 input or October commitment was changed.

[release]: https://www.hkjc.com/english/pressrelease/mcs01_showhtml.asp?SelType=NEWS&filename=20250905_185411_E_NEWS.htm
[guide]: https://consvc.hkjc.com/-/media/Sites/JCRW/FormGuide/Simulcast/25_26/20250907/OSE20250907_starter_all.pdf
