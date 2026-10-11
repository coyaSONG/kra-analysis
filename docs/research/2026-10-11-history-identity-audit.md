# Observed History Identity Collision Audit

## Finding And Research Decision

The PR78 history seed is **not ready for complete-history feature admission**.
The issue is broader than three unbound venue-4 requests: full-roster matching
finds 100 already identity-bound groups, covering 983 rows, in 65 unique pairs.
This is a source-quality finding, not evidence that all 100 groups are fake or
that any particular source should be deleted. All original rows remain intact.

The new executable audit reads the complete frozen 368-unit inventory and checks
its raw replay against the published seed. It does not train, score, register a
prediction, alter H0/H1, fill nulls, change an event identity, deduplicate starts,
or upgrade an availability flag. The 70% Goal remains unproven.

## Frozen Evidence

Local root in the isolated research checkout:
`.cache/autoresearch/observed-history-20261011`.

| Artifact | SHA256 |
| --- | --- |
| Original seed-final.json, unchanged | `0dbe7abe5bdfb0a0b422bb90bddbdf1a3face89e5016254807ba37be95c25c66` |
| Original plan.json, unchanged | `86b32a93348842575d9620cf124cad31df9c4eb2fb1287a82781480a67279960` |
| identity-audit-final.json | `303f4d5821cb5550cf297330834996867e4c5a4898f3f9d7d4e060d2781a72b8` |

The report retains the entire inventory, original capture/page hashes, entry
binding references, collection timestamps and current implementation fingerprint.
It verifies the original seed content against a new raw replay; only replay
implementation metadata and materialization time may differ. Identity admission
still requires API214 row venue or a complete separate API26 roster binding.
Raw replay alone explicitly returns `event_identity_verified: false`.

These hashes bind file bytes, not source authenticity, historical availability,
actual racing, finality, or an independently registered prediction.

## Unbound Groups

All 172 unbound rows match complete earlier Busan gate/horse rosters; none has
multiple exact candidates within this seed. Matching uses the complete set of
canonical horse IDs paired with gates, not names, ranks, distance, odds or a
partial overlap. Returned race numbers are within-capture references, never
invented physical race IDs.

| Requested day / meet | Returned groups | Rows | Exact earlier roster matches |
| --- | --- | --- | --- |
| 2026-08-24 / 4 | 1-6 | 64 | 2026-08-16 / Busan / 1-6 |
| 2026-08-25 / 4 | 1-8 | 87 | 2026-08-14 / Busan / 1-8 |
| 2026-08-31 / 4 | 1-2 | 21 | 2026-08-23 / Busan / 5-6 |

August 24 groups 3, 4 and 5 additionally have identical ranks and finish times
to their earlier matched groups. Other fields differ: the full report records
per-field changed-row counts and fields equal across every pair. Thus these
are not identical raw records, and whole-roster similarity is not an identity
certificate. August 24 has 52 rows satisfying the normal-finish predicate;
August 25/31 have none. None is promoted into the 6,816 admitted observations.

## Identity-Bound Collisions

The 100 groups contain 433 observed normal finishes and 550 unresolved statuses.
The later 55 groups have 543 rows, all unresolved under the existing predicate.
The older 45 groups are not automatically certified as correct simply because
their dates precede a collision. Pairs can overlap; do not sum pair row counts
as distinct events.

| First date / venue | Second date / venue | Exact roster pairs | Paired rows |
| --- | --- | --- | --- |
| Aug 14 / Jeju | Aug 25 / Jeju | 8 | 75 |
| Aug 15 / Seoul | Aug 26 / Seoul | 10 | 103 |
| Aug 15 / Seoul | Aug 26 / Busan | 10 | 103 |
| Aug 15 / Jeju | Aug 26 / Jeju | 7 | 67 |
| Aug 16 / Seoul | Aug 24 / Seoul | 10 | 95 |
| Aug 23 / Seoul | Aug 31 / Seoul | 10 | 100 |
| Aug 26 / Seoul | Aug 26 / Busan | 10 | 103 |

For the ten same-day cross-venue pairs, the only changed raw fields are `meet`,
`hrName`, and `winOdds`; `ord` and `rcTime` are zero on both sides. Sample Busan
names carry a `[서울]` prefix while keeping the Seoul horse ID and gate. This
strongly motivates source review for reused/test/simulcast-style records, but
their exact upstream purpose remains **unknown**. Do not classify them as
actual starts, withdrawals, formal mock races, or harmless duplicates by guess.

Severity is **high** for history-based model inputs. Counting these observations
as actual starts can distort recency, unresolved-event flags and repeated-start
statistics even though the normal-finish predicate already excludes the 543
later rows. A parser-valid physical venue is not proof of an actual race.

## Official Cross-Check

The [official API214 catalog](https://www.data.go.kr/data/15063979/openapi.do)
documents four venues and meet=4 for Yeongcheon. That documents query semantics;
it does not authenticate the meaning of the three anomalous responses.

On 2026-10-11 the authorized browser inspected the
[official Yeongnam result list](https://race.kra.co.kr/raceScore/ScoretableScoreList.do?Act=04&Sub=1&meet=3)
and its next page. It showed August 7/9/14/16/21/23/28/30 as Busan, September
4/6/11 as Busan, and September 13 as Yeongcheon. August 24/25/31 were absent
from those inspected pages. The regional August 24 detail request rendered an
empty table without a returned date, so it is not accepted as a physical-venue
identity lookup. Website absence is not a no-race certificate or a reason to
change the API inventory. No provider clarification has been received.

These UI observations are supporting investigation notes, not pinned raw
evidence consumed by the audit or used to resolve events.

## Verification And Next Action

The result-page replay extraction preserves the old normalized admission path.
Focused tests cover missing venue, API26 binding, raw/page/manifest tampering,
pagination, timestamps, frozen-seed drift, relative-root CLI paths, exact vs
partial rosters, canonical IDs, duplicate membership, multiple candidates,
field presence/null/type differences, exclusive output and input immutability.
The final combined focused suite passed **451 tests**. Ruff lint/format and
whitespace checks passed. A second real replay reproduced the frozen audit
exactly, with the original plan/seed hashes and 398 request reservations unchanged.
Remote CI results will be recorded with the PR; local tests are not a substitute
for required remote checks.

Reproduce without any network request or API secret:

```sh
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.history_identity_audit \
  --root .cache/autoresearch/observed-history-20261011 \
  --seed .cache/autoresearch/observed-history-20261011/seed-final.json \
  --seed-sha256 0dbe7abe5bdfb0a0b422bb90bddbdf1a3face89e5016254807ba37be95c25c66 \
  --output <new-audit-path.json>
```

Output is deterministic for the same source bytes and implementation and cannot
overwrite an earlier report. The CLI takes the existing collector lock. A
changed receipt or capture fails rather than replacing the pinned frozen view.

Next resolve the observed source-quality concern against dated official race
membership before complete-history admission. Preserve the entire prospective
target universe, including missing-source races. Any separately named partial
observation feature must retain explicit source coverage and cannot silently
replace the existing complete-response H0 contract. Historical targets cannot
use this October 11 capture as pre-race evidence. No new fit is authorized by
this audit, and existing archived pre-race M0/M1 results are unchanged.

Pro methodological advice was requested in the existing authorized conversation
and is pending completion as of this draft. No partial output was used.
