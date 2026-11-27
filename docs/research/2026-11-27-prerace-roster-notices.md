# November 27 pre-race roster notices

The original November 27-29 card remains frozen at 51 races and 547
declarations. [PR #200](https://github.com/coyaSONG/kra-analysis/pull/200)
independently witnesses the original input packet, not a forecast or an
approval. The original common cutoff is `2026-11-27T01:15:00Z`.

## Before the cutoff

The four official schedule pages still agreed with the frozen card at
`2026-11-26T04:33:44.961830Z`. The next four-page comparison, completed at
`2026-11-27T00:11:00.967475Z`, found the same 51 race IDs and scheduled start
times. Three Friday fields showed one fewer expected runner apiece, without
changing their declared counts. That edition shows 544 expected runners over
the full card. This is not the final starter count.

| Physical race | Declared | Latest expected | Official notice | Printed time (KST) |
| --- | ---: | ---: | --- | --- |
| November 27 Jeju 2 | 10 | 9 | Exclusion | November 27 08:54 |
| November 27 Jeju 3 | 10 | 9 | Exclusion | November 27 08:55 |
| November 27 Busan 3 | 7 | 6 | Withdrawal | November 26 17:02 |

One anonymous [Jeju bulletin](https://race.kra.co.kr/raceFastreport/ChulmapyoChange.do?Act=03&Sub=1&meet=2)
read and one [Yeongnam bulletin](https://race.kra.co.kr/raceFastreport/ChulmapyoChange.do?Act=03&Sub=1&meet=3)
read completed at `2026-11-27T00:12:38.053517Z` and
`2026-11-27T00:12:38.207324Z`, respectively. Each physical race, gate,
horse ID and normalized name matches exactly one original API26 declaration.
Two HTML readers agreed after the strict reader handled the optional venue
cell end tag in the known table positions. The three notices account for all
three count changes in this edition. The two sampled bulletins are not a
whole-card census of rider or horse notices.

## Custody and interpretation

- Revised national/regional capture SHA256: `aa3bda07e4718cf6ba55cfa96724676da95f6dcf958358ea640c2ae56ebe2820`.
- Schedule comparison SHA256: `ba6d2c7f460b5358144c345edec06e3384fb14d0e04f48254db36992a547629e`.
- Two-bulletin receipt SHA256: `d253340867409239defcd1a6a7a5a85931ff3b1b1a420d7866e20a4b062f3a3e`.
- Private roster diagnostic SHA256: `599127da7db168e70cfbeeb353819bb816c9cd50196d8aeb4f20a12efadd718b`.

Local archive: `.cache/autoresearch/precutoff-schedule-revision-20261127/`.
The receipt binds exact source bodies, URL, and local observation times.
Printed notice minutes are not independently verified first-publication
times. The original reservations, API26 pages and input witness are
unchanged. No data API retries, result requests, study registration,
training or predictions occurred in this check.

For a separately registered future comparison, keep original declaration,
known pre-cutoff notice and verified actual starter as distinct states.
This single revision does not authorize a notice feature, a later cutoff,
a narrower population, or any change to M0 or API27.
