# Actual Observed-Event History Seed

## Result And Scope

Collected all 368 fixed venue/date units for July 12-October 11, 2026, using
398 HTTP request reservations: 391 API214 requests and seven API26 identity
bindings. Raw replay yielded **671 observed races, 6,816 usable runner-event
records and 2,790 distinct canonical horse IDs**. This is source-data progress,
not a fitted model, registered prediction or 70% performance result.

The intended current 90-day seed is July 14-October 11. Two earlier days were
fixed before collection to support diagnostic lookback calculations for existing
October 10/11 rosters. All four physical venues and every calendar date remain
in the request ledger. This calendar request inventory is not the future national
race universe, and empty responses are not certificates of no racing.

## Source Registry And Pins

Source: [KRA API214 official result information](https://www.data.go.kr/data/15063979/openapi.do),
with API26 full-day roster binding only where result rows omit physical venue.
Read-only replay checks original page hashes, page numbering, total counts,
timestamps, date/venue identity and complete binding membership. No result-query
parameter alone is substituted for missing row-level venue evidence.

Local root: `.cache/autoresearch/observed-history-20261011` in the isolated
research checkout. Raw cache files and credentials are not committed to Git.

| Frozen artifact | SHA256 |
| --- | --- |
| plan.json | `86b32a93348842575d9620cf124cad31df9c4eb2fb1287a82781480a67279960` |
| seed-final.json | `0dbe7abe5bdfb0a0b422bb90bddbdf1a3face89e5016254807ba37be95c25c66` |
| projection-final.json | `4ca3470222564f4414863c446458f82a2a4f81e7ddf1bf8b46016bc16ff92e62` |
| original seed-v1.json, retained | `7fc46aa100b575ff247dc17e9d8cea0949edb025e517b44b58d058590cd7ddfe` |
| original projection-v1.json, retained | `81eb49ba9aa942a2f8c013a4b1f6a26e9992ea50578ce4f83bd09221d5e5bdda` |

The independently archived target-roster corpus remains SHA256
`d6598f244d6a7b7bc5e65846a4c79ee6ac96ad278b89a14268de332e77526ae2`.
The collection used source bytes in commit
`e3491e2a4cc77f784b52e3ef91e5b2420f6b961b`; final replay records its current
source fingerprint separately from the original collection fingerprint.
Python is 3.13.13 and httpx 0.28.1. Existing API214/API26 collectors and their
normalizers were not modified. Original seed, plan, receipts and capture bytes
were retained; no network recollection was used for the transformation correction.

Usable source availability spans 2026-10-11T13:33:08.224903+00:00 through
2026-10-11T13:39:47.158299+00:00. Those are local capture-completion observations,
not independent timestamps. Publishing the hashes allows a later GitHub server
commit witness to bound existence before future cutoffs under the existing
GitHub/hash/collector trust assumptions. It does not authenticate KRA independently,
prove historical availability or register a prediction. No seed flag is silently
upgraded by this document.

## Coverage And Quality

| Physical venue | Nonempty usable units | Empty unconfirmed units | Identity-unresolved units | Observed races | Usable event rows |
| --- | --- | --- | --- | --- | --- |
| Seoul (1) | 28 | 64 | 0 | 285 | 2,969 |
| Jeju (2) | 28 | 64 | 0 | 205 | 1,923 |
| Busan (3) | 20 | 72 | 0 | 157 | 1,676 |
| Yeongcheon (4) | 4 | 85 | 3 | 24 | 248 |
| Total | 80 | 285 | 3 | 671 | 6,816 |

There were no failed or unattempted units at collection end. This does not mean
all units supplied usable identity. The three unresolved units are August 24,
25 and 31 at requested venue 4. API214 returned 64, 87 and 21 raw rows without
venue, respectively; API26 returned zero entries for each day, preventing an
independent full-roster binding. All **172 unbound raw rows** remain on disk but
are not treated as venue-verified history. Their meaning is unknown, not inferred
as trial racing, cancelled starts or another venue. Severity is high for full
90-day aggregates because these gaps can change counts and older-event summaries.

Of the 6,816 usable-identity rows, 6,170 satisfy the existing observed normal
finish predicate; 646 remain unresolved status observations. They are retained,
not converted to non-starts or removed. Complete actual start history and finality
against later corrections remain unverified. Successful pagination proves only
the complete response for that request, not complete real-world race coverage.

Primary keys are race identity plus gate, with canonical horse identity checked
within each race. All usable events were replayed from pinned source bytes, and
duplicate event membership was rejected. Identity-bound venue-4 observations use
the complete separately captured entry roster, never partial horse matching.

## Actual Feature Replay

Projected **all 28 archived target rosters and all 294 runners**, including records
excluded from the earlier model-training cohort. No target outcome, training
eligibility flag or result-roster deletion changes target membership. There are
556 prior-event lineage links across 249 runners; 45 have no linked observed
events. The latter is not evidence of debut status or true absence of starts.

The first implementation conservatively erased every history feature if any
90-day request was unresolved. Actual replay exposed excessive propagation of
the three old August gaps into independently observed September/October data.
The original all-null projection is retained. Before any fit, the correction
limited missingness to each feature's required dates:

- All five 90-day aggregates stay null on any 90-day source gap.
- The 30-day finish count needs only complete observed responses for those 30 days.
- The latest finish date/rank needs coverage from that date to the target; older
  gaps cannot create a newer event. Same-day ambiguity remains explicit.
- The latest-three mean requires enough identified recent finishes and complete
  coverage from the third-latest date, with no ambiguous ordering at the boundary.
- A newer unresolved-event flag is retained only when its dependent recent window
  is known. No value is called a true last-start interval.

| Feature | Present / missing among 294 runners | Observed range |
| --- | --- | --- |
| Each 90-day aggregate (five fields) | 0 / 294 | All missing |
| Observed normal finishes in 30 days | 294 / 0 | 0-1 |
| Days since latest observed normal finish | 158 / 136 | 20-36 days |
| Latest observed normal-finish rank | 158 / 136 | 1-11 |
| Mean rank of up to three latest observed normal finishes | 0 / 294 | Missing due to coverage/history limits |
| Newer unresolved event after latest observed normal finish | 158 / 136 | False for the known cases |

Every 30-day count was independently recomputed from the normalized event table
by horse ID and strict date bounds and matched the projection. Final replay
reproduced the same event rows, request inventory and corrected features.
Source availability, raw pins and 398 request reservations remained unchanged.
No unseen historical version was inferred to fill a missing feature.

## Validation And Interpretation

**Confirmed:** actual source capture, immutable raw/page pins, 368-unit inventory,
identity-verified 671-race event table, independent 28-roster feature replay and
351 passing focused/shared tests (32 new tests). Ruff lint/format and whitespace
checks pass. New CI explicitly executes collection and transformation regressions.

**Partial:** the 90-day source window has three unresolved identity units. Recent
features can be calculated only where the missing dates cannot affect them.
The dataset is not an approved complete-history training corpus.

**Unknown/unproven:** historical point-in-time availability, complete national
actual-start coverage, independent source authentication, stable final results,
future prediction accuracy and the 70% Goal. Today's capture is after the
October 10/11 targets; this replay is diagnostic only, never pre-race training
evidence for those historical targets.

No new model fitting, production approval, B0/champion replacement or paid server
creation occurred. Existing restricted-model approvals and old bootstrap rejection
remain unchanged. Research can continue with this future-input source seed while
server provisioning still needs owner approval.

The source ledger includes all failed/empty/unresolved states; durable JSON
publication uses exclusive atomic links and synced bytes. Tests simulate a
process interruption after request reservation and confirm that resume counts
the reservation rather than repeating it outside the budget. Plan-wide limits
cover pagination and API26 binding. Collection resume requires its original code;
read-only replay can use new code only with separately recorded provenance.

The initial Gitleaks check identified two Python `api_key=api_key` keyword
forwarding lines, not literal secrets. Two exact commit/file/rule/line fingerprints
were documented in the existing ignore file; broad scanning rules were not changed.
Final remote check outcomes will be recorded on PR78 before ordinary merge.

## Reproduction And Next Action

From the isolated checkout, the final read-only replay commands are:

```sh
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.observed_history_seed export \
  --root .cache/autoresearch/observed-history-20261011 \
  --output <new-output-path.json>
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.observed_history_seed project \
  --root .cache/autoresearch/observed-history-20261011 \
  --corpus .cache/autoresearch/restricted-cohort/20261011T124748.785378Z_ebdf29deaaa9/corpus.json \
  --corpus-sha256 d6598f244d6a7b7bc5e65846a4c79ee6ac96ad278b89a14268de332e77526ae2 \
  --output <new-projection-path.json>
```

Existing outputs cannot be overwritten. Materialization timestamps change in
new exports; the listed frozen hashes identify this run. Future source collection
requires a new fixed plan for new dates, not editing historical timestamps.

Next, investigate independent identity evidence for the three precise August
gaps and capture newly completed days before the next future-card cutoff. Do not
drop venue 4, shorten the 90-day definition to hide gaps or treat a query parameter
as proof. Use the current seed only within its observed-version evidence scope;
new fitting still requires a reviewed pre-race-safe frozen dataset. The complete
future universe and durable per-race prediction registration remain separate
requirements, not satisfied by collecting more past rows.
