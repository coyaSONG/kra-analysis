# Historical Expansion for Sparse Entrants

## Result

Added May 15-31, 2026 API observations for **153 races and 1,551 runner rows**.
All 153 races match the official HTML event identity and complete roster;
1,528 rows also match numeric finish rank and race time. The other 23 remain
preserved observations, not ranked feature rows. All 153 official headers
provide distance and exact class. This increases the separate supported/form
history from 8,994 to 10,522 rows. No fitted model, published prediction,
reserved input, 24-column packet or evaluation population was changed.

The new May observations link to 213 distinct horses in the frozen 534-row
October 16-18 population. This is additional history, not 213 newly covered
horses. For 19 horses without a preceding 90-day record in the old snapshot,
May reveals an older start. Absence from a short archive is not proof of debut.

## Why This Window

First captured the existing collector's four official result-list pages for
each of three menu regions. The 583 listed race IDs between July 18 and October
11 all already have observed conditions in the pinned old archive, including
24 Yeongcheon races on September 13, September 20, October 4 and October 11.
This is a check of those 12 pages, not proof of complete national history or
proof that unlisted dates had no races. Repeating those dates was not selected
as an acquisition strategy. June and early July were already archived.

The same pages expose 101 previously absent May 15-31 races, with uneven list
coverage: oldest visible dates are May 23 for Seoul, May 29 for Jeju and May 15
for the Yeongnam menu. These dates do not establish a complete May population.
The API subsequently supplied another 52 race IDs outside those list pages;
the existing official detail collector verified them individually. No calendar
assumption or invented race roster was used to admit them.

May is outside the fixed October 90-day window. The user requested historical
expansion; this increment stores May independently and inspects **180-day
coverage only**, not a new score, new prediction arm or a selected lookback.
There is no tuning against target outcomes. The original 90-day rule remains
unchanged and its complete 534-row contrast ledger must reproduce byte-for-byte
as structured data after the extension. It does.

## Yeongcheon and Coverage

| Coverage on the same targets | Before | After |
| --- | ---: | ---: |
| All 534 entrants: at least one observed prior in 180 days | 481 | 486 |
| All entrants: at least three observed priors in 180 days | 308 | 340 |
| All entrants: at least one same-venue/class, within-200m prior in 180 days | 335 | 342 |
| Yeongcheon 66 entrants: at least one prior in 180 days | 65 | 66 |
| Yeongcheon entrants: at least three priors in 180 days | 51 | 57 |
| Yeongcheon entrants: at least one similar prior in 180 days | 14 | 14 |

Forty distinct Yeongcheon entrants gain 46 May records, all from **physical
Busan venue 3**, not Yeongcheon venue 4. Thus general career coverage improves,
but the 52/66 same-venue similarity gap does not disappear. Do not relabel
Busan history as Yeongcheon aptitude or treat their regional menu as a physical
venue identity. The official [API214 metadata](https://www.data.go.kr/data/15089492/openapi.do)
distinguishes these physical venues. A general-career feature and a venue-specific
feature would need separate interpretation and future validation.

The baseline 90-day diagnostic still has 225 fallback rows, 195 observed-zero
contrasts and 114 nonzero contrasts across all 534 entrants. No target labels
were requested, no performance metric was computed, and no progress toward
70% exact-three accuracy is established by these coverage changes.

## Acquisition and Provenance

All files are under ignored `.cache/autoresearch/history-gap-expansion-20261014`.
The unchanged API collector ran a May 15-31 plan across 68 date/venue units,
with a 128-request ceiling, serial pacing, no retry and its existing three-error
breaker. It used 74 requests: 18 units returned rows and 50 were
`empty_unconfirmed`. Empty does not certify no racing; all 68 units are retained.
There were no authentication, transport, quota or unresolved-identity failures
reported by this completed run. This does not guarantee future API health.

Official HTML collection used 12 discovery requests, 113 catalog requests
(101 details plus 12 lists), and 64 additional requests (52 details plus 12
lists). The original 101 detail pages were reused, not requested again for the
API-discovered gap. Total requests: 189 HTML and 74 API. Raw bytes, hashes,
canonical source URLs without API credentials, acquisition times, identities
and incomplete observations remain available for replay. Original snapshots
were never overwritten. API and HTML may share an upstream source; matching
formats are corroboration, not statistical source independence or finality.

| Artifact | SHA256 |
| --- | --- |
| `discovery/archive.json` | `dd76fe35cf9c4d16fd5343b5dc847581faf8e2168803b9819b62a95ef30704fc` |
| `may-api/plan.json` | `5ebd01a08cab3082b250c781094a2192340b7ca90f0c9d0ddb2ed5bc96bf39fe` |
| `may-api/seed.json` | `eb54c47dcabecca2f579f7e6821ddc3ffa400e5b935eaeca0353f6d01c77b73a` |
| `may-catalog/index.json` | `ce18a669a35c0d37ee7b92ee7fd7813ce342e96e3de3dec6dad09554b5bd7949` |
| `may-catalog/details/archive.json` | `3bbdbad2fd5da816685297f224b991d6f631f3a2b6b173db9cf33ff9d6fb38d7` |
| `official-gap-index.json` | `6d7559a66f47eccbfa9481844fe794ab7bc92becb540a641e9af479a27f2d809` |
| `additional-official/archive.json` | `5fb136518473aaf45e605bb878cceaa4c00e8ce34dccf41d50a3bece277c676f` |
| `report-v2.json` | `3302c5bb1abb62f70565535751991c01896b9b437e4160168ea3700fbbc09866` |

Report-v1 is preserved. V2 adds reproducible evidence for the recent-list gap
check; the history and target coverage are unchanged. The report contains the
new per-race support checks, all admitted history rows, dated header provenance,
per-target added IDs and complete denominator counts. It rejects overlapping
history, target/future result imports, or any change to the frozen 90-day ledger.

## Reproduction and Tests

From the isolated checkout root with its local archives available, use a new
output filename; exclusive writes reject replacing old reports:

    PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.history_gap_expansion --output .cache/autoresearch/history-gap-expansion-20261014/report-replay.json

The audit is offline and makes no further requests. Focused tests cover physical
venue separation, exact class/distance policy, 180-day boundaries, unchanged
90-day inputs, target/future exclusion, duplicate history, whole-roster and
rank/time conflicts, explicit unresolved observations and target label rejection.
They are included in Scripts Checks.

The combined local run passed 288 tests covering the new audit, original
collectors, frozen-history replay, condition projection, M0/API27 execution
and prospective-input contracts. Ruff lint and formatting passed. An independent
date-window calculation checked all 534 per-target counts, and V1/V2 have
identical coverage. Remote checks are recorded separately on the PR.

## Research Decision and Limitations

Retain May as a separate acquired history snapshot for later feature construction.
Do not backfill it into the published M0/API27 predictions or their original
training inputs. Capture after the May races does not supply May pre-race
features or authorize retrospective model training. Today these records precede
the future October block, but independent historical availability and full
180-day coverage remain unproven. No April expansion or 180-day scoring arm is
implicitly registered by this coverage audit.

For future research, distinguish general past experience, similarity within the
same venue and explicit missingness/support counts. Keep the venue-specific
gap visible; collect future Yeongcheon observations rather than synthesizing
same-venue history. After the pending 50 outcomes, compare the already published
models first. Any model trained or selected with those results needs a separate
subsequent preregistered evaluation block.

Attempted the authorized Pro consultation through the in-app browser, opening
the existing research conversation. ChatGPT showed the logged-out screen, so no
prompt was submitted and no new consultation occurred. The bounded acquisition
and coverage audit proceeded without changing model or inference policy.
