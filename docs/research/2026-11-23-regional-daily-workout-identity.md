# Regional daily workout identities and whole-roster reconciliation

Local evidence SHA256:
`23f436b7f681e5f6ec57ec42c5ca35a6d32ad56227a2f394aebb183f1bb891e8`.

## Official edition and request bound

Use the official [Jeju](https://race.kra.co.kr/trainer/dailyDayTrainList.do?Act=10&Sub=3&meet=2)
and [Yeongnam](https://race.kra.co.kr/trainer/dailyDayTrainList.do?Act=10&Sub=3&meet=3)
trainer menus, alongside the
[previously verified Seoul edition](2026-11-23-seoul-daily-workout-identity.md).
Use November 18, 2026 KST because the earlier official text
editions and original declarations for that comparison already
exist. One index, one selected date, and one displayed all-selection
control per menu: six anonymous HTTP 200 responses, at least two
seconds between requests, no retries, credentials, profile requests,
API18 requests or outcome reads.

| Menu and stage | Observed UTC on 2026-11-22 | Original SHA256 |
| --- | --- | --- |
| Jeju index | 19:26:28.952220 | `f0ae93576e8a422c0d5a4d822b5832688f85cd21fd52e515fb01042467d8dd89` |
| Jeju date group table | 19:26:31.096740 | `23d0d2c980ea42b465e4fc397f5ab5bcf181f250b8e7fb5473714d9888f18d64` |
| Jeju all-date detail | 19:26:33.528063 | `e6f05f0900846a821cada1637320956ca713ace6ca1cfab5868c1a883eeb2993` |
| Yeongnam index | 19:26:35.670138 | `c5371b8c53b005d001cc4c256f94e3a81eefb712be432108d08dfa329d16cc34` |
| Yeongnam date group table | 19:26:37.825822 | `92791705483d458284aa680758690bd3eaf8aa76a00ff6cbdb294f0ad70d1154` |
| Yeongnam all-date detail | 19:26:40.326256 | `73de8b2be9d02c5291febd1d961aaf190f9dcb301d57c906e99406d6f36d5d5f` |

The two detail bodies have 359 and 662 consecutive rows,
respectively, with distinct horse numbers from the publisher's
horse-profile links. All group/stall keys are unique within a
same-day menu, and all counts agree with the index and the 18
Jeju or 28 Yeongnam group totals. The response weekday token
is the placeholder `??`; the numeric scope fields and printed
detail date agree. Jeju's actual nine-column table has no grade,
distance or gait-count columns. Yeongnam has those columns but
all 662 distance cells are blank. None of these fields implies
zero distance, speed, or a workout intensity measurement. The
Yeongnam menu does not identify each horse's physical workout
venue. The physical race venues below come from the original
API26 declarations, not the menu namespace.

## Versions and time quality

| Earlier text edition | Observed UTC on 2026-11-18 | Exact later row matches | Later-only rows |
| --- | --- | ---: | ---: |
| Jeju | 21:57:06.281456 | 358/358 | 1 |
| Yeongnam | 21:57:10.755467 | 662/662 | 0 |
| Seoul, earlier separate audit | 08:57:45.747424 | 877/877 | 2 |

Earlier text editions have no stable horse numbers. Matches
are by same-day group/stall, normalized name and all three
literal time values. Both editions give inconsistent durations
in Yeongnam detail rows 142 and 161: the printed duration is
17 vs. 16 minutes and 15 vs. 16 minutes by the clocks,
respectively. Preserve their IDs and every printed value, but
leave usable duration missing. Neither row joins the original
declarations. These are cross-edition observations, not verified
correction notices. They do not establish when a later row or
the native ID first became available.

## Original 51-race reconciliation

All 540 original API26 declarations replayed for the unchanged
51 race IDs and their original cutoff, November 20 at 01:15 UTC.
Join by official horse number and exact declared name. For
the same date, compare each joined duration with the separately
archived, pre-cutoff race calendar for the exact race/horse/gate.

| Physical race venue | Exact ID, name and minute matches | Missing in both | Original declarations |
| --- | ---: | ---: | ---: |
| Seoul | 234 | 1 | 235 |
| Jeju | 129 | 1 | 130 |
| Busan | 109 | 0 | 109 |
| Yeongcheon | 66 | 0 | 66 |
| **All** | **538** | **2** | **540** |

All declarations matched in 49 of the 51 races. The Seoul and
Jeju blanks are retained in the 540 denominator and are not zeros.
This measures lookup coverage on one dated sample, not a model's
race-level hit rate.

## Decision for the next prospective comparison

The observed bulk mechanism took three requests per menu on this
one day, or nine across all three, versus one calendar page per
race for the earlier reference. This is worth trying prospectively
on an explicitly registered full card; it does not prove it can
replace the archived race calendars. The native-ID HTML was
collected after the original cutoff. Admit no reconstructed
historical feature on this evidence. Before testing a duration
feature, preserve a fresh pre-cutoff edition and its independent
public timestamp, repeat the exact whole-roster join and record
missingness by venue, distance and class without changing the
population. Then compare a fixed duration-feature variant against
its baseline on a separately preregistered future population.
No model was fitted, promoted or used for predictions, and no new
evaluation was registered here.

The local `regional-native-workout-20261123/` evidence contains
all raw source and receipt references and missingness. A second
HTML reader reproduced all 1,021 regional rows. Offline replays
reproduced the separate Seoul, pre-cutoff calendar, and new
whole-roster evidence digests.
