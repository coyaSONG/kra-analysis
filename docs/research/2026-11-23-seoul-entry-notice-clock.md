# Seoul entry notice clock and original declaration evidence

Notice edition evidence SHA256: `5da4516bcd3cab354d04bbbd6f59032dbd65866d2c29f431cbd980f99f38bc6d`.

## What the two editions show

The [official Seoul entry-change bulletin](https://race.kra.co.kr/raceFastreport/ChulmapyoChange.do?Act=03&Sub=1&meet=1)
displayed the same November 21-22 Seoul dates in the two preserved
editions. The November 18 original explicitly said there were no
horse-status or rider-change notices in the displayed tables at that
observation. This is not a guarantee that the original assignments
would remain unchanged. A single later anonymous GET returned two
horse-status notices and four rider-change notices. No retries, result
operations, separate regional requests or credential use followed.

| Edition UTC | Raw SHA256 | Horse status / rider change |
| --- | --- | --- |
| 2026-11-18 09:37:30.135982 | `62416791aa64a63f2fcf19971ebd00985a35131e4fa9e3af918132c37a9acac8` | Explicitly empty at observation |
| 2026-11-22 19:05:34.118158 | `7698da40e42767475961951f969182cd4e53bcc82ec511142194ba27cfadccf0` | 2 / 4 |

All six notices match the original physical race, gate, stable horse
ID and printed horse name. The original API26 pages preserve the
old jockey IDs, names and assigned weights in all four rider notices.
Each reports a different rider and unchanged weight. The four
rider changes affect three races. The two exclusion notices
agree with the respective daily reports' sanction tables, while the
different literal timing-table marker remains in both originals.

| Original Seoul race / gate | Notice | Publisher-displayed KST | Minutes before original scheduled start |
| --- | --- | --- | ---: |
| Nov 21 race 7 / gate 5 | Horse exclusion | 14:31 | 44 |
| Nov 22 race 10 / gate 4 | Horse exclusion | 17:25 | 0 |
| Nov 22 race 6 / gate 7 | Rider change | 12:43 | 77 |
| Nov 22 race 9 / gate 5 | Rider change | 13:45 | 190 |
| Nov 22 race 11 / gate 7 | Rider change | 15:08 | 167 |
| Nov 22 race 11 / gate 10 | Rider change | 16:21 | 94 |

The [KRA rules explainer](https://race.kra.co.kr/raceguide/RaceTakePartHorseCancleService.do?Act=05&Sub=3&meet=1)
distinguishes actions before a horse competes from a running stop.
Those rules do not date either notice or authorize a global alias
for differing result-table literals. Zero in the last table column
means the same printed minute as the **scheduled** start, not a
verified actual start, delay or same-minute publication sequence.

## As-of boundary and future use

All six displayed minutes follow the original common deadline,
2026-11-20 01:15 UTC. Five are earlier than the original individual
race T-30; that calculation does not alter the common deadline.
The later bytes were observed only after all six races. These clocks
therefore do not attest the first time that any updated record was
publicly accessible, even for the five with an earlier printed minute.
Do not rewrite a freeze using a rolling latest bulletin or a later
result. The original 51 races and 540 declarations, including both
result-marker holds, were replayed in full and preserved. Only the
22 Seoul races had this notice source checked; the other venues'
notice status was not sampled, not declared empty.

The read-only verifier handles the original's omitted venue cell end
tag only in the two known Seoul tables. It checks full column groups,
three date headings, horse links, the before/after rider layout and
Korean calendar minute. A second HTML reader reproduced all six
literal rows. All 390 related tests passed. The shared result parser
and model runtime are unchanged.

The local `seoul-notice-clock-20261123/` archive retains the exact
request, observation receipt, hashes, notices and original per-race
counts. This is a data quality observation for future protocol review,
not new approved labels, a new evaluation period, or a score. Results
still require the official reconciliation policy. The prior API214
captures stopped without HTTP headers; this read does not establish
API authorization, quota state, availability or denial. Keep the
next whole-card intake and original forecast deadline first.
