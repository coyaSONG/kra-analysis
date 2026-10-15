# Early May History Expansion

## Result

Collected May 1-14, 2026 into a separate immutable local archive. The existing
collector returned **102 races / 1,029 runner records**. All 102 event identities,
complete rosters, distances and exact class labels agree with official HTML.
The existing conflict policy admits **1,001 records**, increasing the separate
research history from 10,522 to **11,523 records**. The other 28 are retained but
not used as ranked features. This is observed-history expansion, not historical
pre-race training approval or evidence of improved prediction accuracy.

The three original published commitments (M0, API27 and training-inputs), the
whole 50-race / 534-appearance target universe, and the complete recent 90-day
contrast ledger remain unchanged. No fits, new predictions, target outcome
requests, score blends, model promotions or new evaluation arms were made.

## Quality Exception

For `20260510_1_9`, API and official HTML rank values disagree for four runners:

| Gate | API rank | HTML rank |
| --- | ---: | ---: |
| 1 | 7 | 6 |
| 5 | 9 | 8 |
| 8 | 8 | 7 |
| 11 | 10 | 9 |

Their race times agree. The reason for the rank discrepancy has not been
established; do not assume a correction, disqualification rule or parser fault.
The existing `supported_extension` rule withholds **all 11 records of this
race**, including individually matching rows, rather than choosing the preferred
source. Another 17 rows outside that race lack usable matching numeric finish
rank/time. All original observations remain available. No retry was used to
seek a preferred answer and the conflict rule was not relaxed.

## Same-Population Coverage

All counts below are runner appearances, not accuracy or independent samples.
The baseline includes the previous May 15-31 extension.

| Quantity on the same 534 appearances | Before | After |
| --- | ---: | ---: |
| At least one observed prior within 180 days | 486 | 489 |
| At least three observed priors within 180 days | 340 | 356 |
| Same-venue/class, within-200m prior within 180 days | 342 | 346 |
| Older-band history, ages 91-180 days | 378 | 390 |
| Same-venue similar older-band history | 164 | 175 |
| Older-band history but no recent 90-day history | 31 | 34 |
| Recent condition fallback | 225 | 225 |

Early May contributes history and changes the older form descriptor for **147**
appearances: Seoul 66, Jeju 43, Busan 14, Yeongcheon 24. These are not 147 newly
covered runners. Fifteen with no recent history gain older records, but only
three previously had no history anywhere in the selected 180-day archive.

Yeongcheon's 66 appearances retain 66 with any 180-day prior; those with at least
three priors rise from 57 to 59. Same-venue similarity stays **14/66**, all in
the recent band; older same-venue similarity remains zero and recent fallback
remains **52/66**. Do not reinterpret physical Busan history as Yeongcheon
aptitude. The expansion adds general experience but does not solve that gap.

## Acquisition and Availability

The new window lies inside the previously fixed older band. It does not extend
the 180-day lookback, change the recent recipe, or select a window from target
results. The local collection plan inventory showed June onward and May 15-31
already captured; this May 1-14 plan did not overlap those windows.

API collection used **60 requests** against a ceiling of 96, covering all 56
date/physical-venue units once, with pagination, serial pacing and no retries.
Twelve units returned rows; 44 are `empty_unconfirmed`, not proof of no racing.
No authentication, quota, transport or unresolved-identity failure was reported
by this run. Official capture used **114 requests**: 102 detail pages and the
existing collector's 12 list pages. Every HTML receipt is `captured`; list
pagination is limited and does not prove a complete national history.

API availability timestamps run from `2026-10-15T12:29:48.701488Z` to
`2026-10-15T12:30:47.991721Z`. HTML acquisition runs from
`2026-10-15T12:31:23.239204Z` to `2026-10-15T12:32:09.211189Z`.
The derived snapshot was created at `2026-10-15T12:33:27.233765Z`, before the
original `2026-10-16T01:20:00Z` cutoff. These are local acquisition clocks,
not independent upstream publication-time attestations. Records acquired after
their May races are not automatically pre-race feature examples for May.

Raw API bytes, HTML, canonical source URLs, receipts, code fingerprints and
hashes are retained under ignored
`.cache/autoresearch/observed-history-extension-20260501-14`. No original
reservation or report was overwritten. API and HTML may share an upstream
source and are not statistically independent evidence.

## Evidence and Reproduction

| Artifact under that archive | SHA256 |
| --- | --- |
| plan.json | `cde602d1a52d454b32c406e442df7329bc39a56ce555b67d04783a835632c640` |
| seed.json | `561bcfdc6fe2c4733e571b8c77034a2753e88794d5d7d3a6ee5d2ee2f25a5407` |
| official/archive.json | `8ca56ba232156beb824e9baab1f4c8c5b301e8d619f81e17d1213e8f6512e1bd` |
| audit-report.json | `0ff580a8e1ff3123f2f18ffb226ceb7ebf6c759f071697fbde0e9ad67bbb85e3` |
| independent-check.json | `8572f71d67e390439f27c4e23ae1cb0d0db7d6af143c1b20793ba7c6a45d6090` |

Exact copies of the executed scripts are published alongside the existing
supplements: `early-may-audit.py` (SHA256
`970d5477ee8af130e64f2f3fd8bb084485da7704b1932367157d3c5459332f9c`)
and `early-may-independent-check.py` (SHA256
`55f025fecf8d972df36235102b515377e45e8ab253379329fc96c4e694b49fc6`).
They are execution-specific research evidence, not production inference code.
Run from the isolated checkout root with its original local archives present.
Before cutoff, a new offline report can be produced with:

    PYTHONPATH=packages/scripts .venv/bin/python docs/research/supplements/2026-10-16-18/early-may-audit.py --output .cache/autoresearch/observed-history-extension-20260501-14/replay.json

The replay has a new creation timestamp and therefore a new report hash. The
original snapshot remains pinned. After cutoff this script intentionally refuses
to produce a new timely snapshot. Never backdate or overwrite a failed attempt.
The independent script reads the original pinned report and directly recomputes
all 534 feature rows and source-ID sets with integer day ages and Fraction
arithmetic, without production projection/scoring helpers. Its output is
exclusive-write: an existing `independent-check.json` is preserved and makes a
second invocation fail at save, after read-only assertions. Neither script makes
network requests. Do not invoke Python with `-O`, which disables audit assertions.

Local verification: **210 tests passed** across observed-history collection,
frozen replay, official support, history expansion, condition memory, condition
contrast, condition form and pre-race conditions. An independent calculation
matched every feature row, verified 11,523 unique historical keys, all 534 target
identities, quarantined-group exclusion and the three original public hashes.
Remote checks and merge status belong to the PR receipt, not this local claim.

## Research Decision

Keep the fixed recent contrast with explicit support count/fallback state and
separate older career experience as the next model hypothesis. The richer
archive is now sufficient for that input diagnostic; repeatedly extending it
does not itself test prediction quality. Keep the scarce Yeongcheon same-venue
evidence visible. Wait for the pending block's official outcomes, compare the
original M0/API27 predictions first, then use any outcome-informed learning only
with a later independently preregistered full-population evaluation.

The snapshot remains `training_approved=false`, `accuracy=null`, zero fits and
not evidence of reaching 70%. The goal is not complete. No new Pro consultation
was performed for this bounded replay; the earlier logged-out access limitation
must not be represented as advice received.
