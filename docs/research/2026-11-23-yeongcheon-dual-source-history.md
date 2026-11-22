# Reconciled November 22 Yeongcheon individual result history

All six November 22 Yeongcheon races now have matching API214 and
official detail evidence. Five missing detail pages add **55**
reconciled individual rank/time rows to the previously confirmed
11, for **66 across six races**. This is a post-race source version
for possible later prior-history use. It is not a newly scored
evaluation or admission of the November block for training.

## Scope, requests and version

The [initial observation](2026-11-23-api214-yeongcheon-closed-observation.md)
retains the same API214 response, physical venue binding, daily
report and fourth-race detail. Replaying it still gives one verified
race. The retained official completion list links six dated, finished
events. Check those links against the entire original 51-race
November 20-22 card, all 540 declarations and the original
`2026-11-20T01:15:00Z` cutoff. Do not adopt a later card.

The existing official result collector made five GET requests
for the other race numbers, each once and all HTTP 200. It used
the same [Yeongcheon detail route](https://race.kra.co.kr/raceScore/ScoretableDetailList.do?Act=04&Sub=1&meet=4&realRcDate=20261122&realRcNo=1).
There were zero new API214 requests, list calls, redirects or
retries. The fourth race's readback reused the earlier exact
receipt and body. The API214 capture remains unchanged; its original
venue came from the verified API26 day roster, not from a venue
value in the result response.

| Race | Distance / literal class | Detail receipt UTC, November 22 | Body SHA256 |
| --- | --- | --- | --- |
| 1 | 1400 m / domestic 5 | 22:52:32.952545 | `0e11e6cb70edc0325371aa38c625ce4ff33ec2af8885d02b75bee8e9fb72cd17` |
| 2 | 1200 m / domestic 5 | 22:52:33.157510 | `8369957cc862474934abe08eab9af52fdd7261dc5ed5207d2b85e2a79499c0f1` |
| 3 | 1200 m / mixed 4 | 22:52:33.368852 | `ed8666d0b3842b6a3d940fcbb7ed8a2a92b280e88b0103e41b0cc9e853b70f76` |
| 4 (reused) | 1800 m / domestic 3 | 09:08:38.108698 | `e82a9c5235735b43b80e56a2d4b004dae94cf75508c3586922d057e64440a2b4` |
| 5 | 1400 m / domestic 4 | 22:52:33.579081 | `c0424c80c89407b30b841ee3698546435bef4497702423a956c7c1e1bf960c44` |
| 6 | 1400 m / mixed 3 | 22:52:33.772405 | `0bb87a2dd45fb67cf2bd04407201fd1d325c6679e214e701581d02b89ddf2d1a` |

Under the unchanged versioned result policy, the original 51 now
have **6 unique top-three observations and 45 missing sources**,
compared with 1 and 50 before. No pending or out-of-scope race was
converted to an incorrect forecast. The fourth race did not change.
KRA provides both views; they are not independent publishers. Matching
rank and elapsed time does not establish official result finality,
settlement or the meaning of every sectional clock.

## Timing and use

The last local detail receipt is 2026-11-22T22:52:33.772405Z.
The exact private replay ledger is
`.cache/autoresearch/yeongcheon-nov22-detail-completion-20261123/actual/reconciliation.json`.
Its SHA256 is
`63bd2e2df1299a606b53dc17ef1046938a094e123f6230fec6daf0eb9d658f24`.
It retains original sources and clocks, the new request receipts,
missingness and both result status totals without rewriting earlier
evidence. This document can witness the hash by its verified merge
time, not the first KRA release or an original pre-race capture.

These individual rank/time records can be considered only as
earlier starts for a **separately frozen future card**, after both
source and witness clocks pass its real cutoff and after exact
horse, venue, distance and literal-grade checks. Reuse the existing
similar-history rules. The [earlier nomination audit](2026-11-23-nomination-prior-coverage.md)
found no overlap between its 84 identified nominations and the
original 540 declarations, so these 66 rows cannot by themselves
improve coverage for that preliminary set. Recheck only on a final
whole card; possible benefit remains unmeasured.

## Verification

Read-only replay reproduces the exact ledger. An independent libxml2
HTML parser and decimal conversion checked every saved race/gate,
stable horse ID, rank and elapsed time against the old API body.
All six details' distance and literal grade agree with the preserved
context. The collector and existing policy regression suite passed
110 tests, including failed, empty and mislabeled responses and a
hard stop before a subsequent request.

The original M0/API27 commitments, elapsed cutoff, races, active
training policy and research goal are unchanged. No model was
fit, no prediction produced, and no accuracy was estimated.
