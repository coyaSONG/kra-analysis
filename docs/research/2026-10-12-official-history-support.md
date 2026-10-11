# Official Support For Frozen History

## Decision And Result

The complete frozen API history now has a dated official-result reconciliation,
not merely a roster-collision warning. Of **671 groups**, **616** have matching
official body date, physical venue, race number and the complete gate/horse-ID
set. All **6,170 normally ranked API rows** in those groups match the official
rank and finish time exactly in displayed decimal seconds. Another **103 rows**
are API-unresolved observations linked to those official events; their actual
start/status meaning is not inferred.

The remaining **55 groups / 543 rows** have no dated result body in their
captured detail responses. They remain unknown, not deleted, fake, withdrawals,
or confirmed no-races. Among the original 100 collision groups, the older 45
are positively supported and the later 55 remain unknown. This is evidence for
the older records themselves, not a classification of the later records.

The 172 rows in 16 identity-unresolved source groups remain outside normalized
history and are retained in the attached original quality audit. No source date,
physical venue, raw row, old feature or model is rewritten.

This increment ran **zero research fits**, registered **zero predictions**, and
created **zero paid resources**. It provides no new exact-success-rate evidence.
The 70% complete-future-universe objective remains unproven. The owner's latest
instruction explicitly defers paid servers and continues local research.

## Actual Evidence

Archive directory: `.cache/autoresearch/official-history-20261012-v2` in the
isolated research checkout. It contains 671 detail receipts and 12 official-list
receipts, each connected to original HTML bytes, byte counts, URL, local start
and completion timestamps, encoding and SHA256. The final selected archive has
683 successful HTML responses and no fetch failures.

| Artifact | SHA256 |
| --- | --- |
| Original unchanged seed | `0dbe7abe5bdfb0a0b422bb90bddbdf1a3face89e5016254807ba37be95c25c66` |
| Final archive.json | `eaece57cdd27ee4e348e171e04368440da9d82a4417110476f0a1a1400e934e2` |
| Final projection-final.json | `565cf2a2c469d3a673f086e39d5ef8f56c61d17ed9390ff9c8745f9e7f485f82` |
| Original target corpus | `d6598f244d6a7b7bc5e65846a4c79ee6ac96ad278b89a14268de332e77526ae2` |
| Preserved first archive, not the final selected view | `c2472110b1cb95a38a547d0ecea3dd1ef27bb62eb5db399580b0ace3d18cb7c6` |

The collector made 707 HTTP requests: the first 683-request archive plus 24
corrected Yeongcheon detail requests. The first implementation incorrectly used
the Yeongnam menu code 3 for physical venue 4. Official detail links explicitly
use 4. The corrected archive reused 659 byte-verified identical-request receipts
and fetched those 24 new requests; the first archive was not overwritten.
Additional source-discovery browser/HTTP reads are not included in this collector
request count. No public-data API quota or API secret was used by this collector.

Detail captures completed between **2026-10-11T18:05:33.164581Z** and
**2026-10-11T18:11:30.128086Z**, local-clock observations only. These are October
12 KST captures, after the October 10/11 diagnostic targets. Neither PR78 nor
PR80's earlier published hash can authenticate these new bytes retroactively.
The final report's hash chain may later be connected to its own publication
event, but this implementation does not claim an independently verified timestamp.

## Official Source Semantics

Positive examples include the official
[August 15 Seoul race 1](https://race.kra.co.kr/raceScore/ScoretableDetailList.do?Act=04&Sub=1&meet=1&realRcDate=20260815&realRcNo=1),
[August 14 Jeju race 1](https://race.kra.co.kr/raceScore/ScoretableDetailList.do?Act=04&Sub=1&meet=2&realRcDate=20260814&realRcNo=1),
and [August 14 Busan race 1](https://race.kra.co.kr/raceScore/ScoretableDetailList.do?Act=04&Sub=1&meet=3&realRcDate=20260814&realRcNo=1).
The [August 26 Seoul request](https://race.kra.co.kr/raceScore/ScoretableDetailList.do?Act=04&Sub=1&meet=1&realRcDate=20260826&realRcNo=1)
is an actual archived blank-body counterexample. HTTP200 and requested identity
are never substituted for returned body identity.

The parser reads all official result rows, including empty/exceptional ranks.
Horse-link IDs supply stable horse identity; their region argument does not
supply the physical venue. Body date/venue/race number must identify the event.
Missing IDs, duplicate gates/IDs, incomplete tables and unexplained whole-roster
differences prevent admission. Consecutive 1..N ranks are not required. Busan
provides two timing tables; both complete gate sets, ranks and final times must
agree. Numeric incident text in the list's void-race explanation is not parsed
as a race number: only numbered link labels supply list membership.

Each group has separate event and whole-roster support, followed by per-row rank,
time and status support. An API ranked row contributes to the new ranked counts
only when both rank and finish time match. API-unresolved rows in exact official
rosters have their own explicitly named count, not inferred DNF/non-start codes.
The website and API may share an upstream database; this is dated official
support, not proof of independent data-generating systems or eternal finality.

## Bidirectional List Check

Four pages from each official regional result list were archived. They contain
405 Seoul, 300 Jeju and 299 Yeongnam race entries across their displayed date
ranges. Within each region, entries are unique, day-order numbers are consecutive
from 1, all four pages parse successfully, and the oldest listed date reaches
beyond the seed's July 12 lower boundary. Physical Yeongcheon events remain
distinct from Busan even though both appear in the regional list.

Restricted to July 12 through October 11, no captured official-list race is
missing from the seed. Exactly 55 seed groups are absent from these captured
lists, the same groups with blank detailed bodies. This is a bounded comparison
against these regular-result documents, not a certificate that no other event,
mock run, trial or unlisted race occurred. The 285 originally empty API response
units remain `empty_unconfirmed`; no global completeness flags are upgraded.

## Actual Feature Output

The new `official_supported_partial_v1` output preserves every one of the
**28 target races and 294 runner appearances**, regardless of label or training
eligibility. The full previous `observed_partial_v1`, including legacy H0/H1,
is embedded without modification and compares exactly to PR80's saved output.

| Target lineage across all 294 rows | Links |
| --- | ---: |
| Officially supported ranked observations used | 474 |
| Official-event-linked API-unresolved observations | 8 |
| Observations withheld with explicit reason | 74 |
| Original total, unchanged | 556 |

The 74 withheld links affect 58 target runner appearances. Every ranked count,
win count, top3 count and top3 fraction is unchanged from PR80 for this dataset.
The change is the separation of unsupported unresolved observations from
official-event-linked unresolved observations. No accuracy gain is claimed.
There remain 246 non-null ranked fractions and 48 null fractions; zero counts
mean no supported observations in this selected view, not debut/nonparticipation.

Every used, linked-unresolved and withheld event remains traceable to its group
and captured evidence. Collision relationships are retained without pair-count
double-counting. A later official correction requires a new archive/version;
the existing view does not silently select new receipts.

## Verification And Reproduction

Focused new and existing history regressions passed **143 tests** before final
publication. A complete second offline materialization equals the saved output.
An independent count recomputation checked all 294 output rows. Original seed
hash and the complete embedded PR80 projection remain unchanged. Ruff lint,
format and whitespace checks are required before publication; remote CI results
are recorded on the PR, not assumed from this local run.

From the isolated checkout root:

```sh
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.official_history_support materialize \
  --root .cache/autoresearch/observed-history-20261011 \
  --seed .cache/autoresearch/observed-history-20261011/seed-final.json \
  --seed-sha256 0dbe7abe5bdfb0a0b422bb90bddbdf1a3face89e5016254807ba37be95c25c66 \
  --archive-dir .cache/autoresearch/official-history-20261012-v2 \
  --archive-sha256 eaece57cdd27ee4e348e171e04368440da9d82a4417110476f0a1a1400e934e2 \
  --corpus .cache/autoresearch/restricted-cohort/20261011T124748.785378Z_ebdf29deaaa9/corpus.json \
  --corpus-sha256 d6598f244d6a7b7bc5e65846a4c79ee6ac96ad278b89a14268de332e77526ae2 \
  --output <new-output-path.json>
```

`collect` with an explicit new archive directory captures a new version; the
same completed directory verifies existing receipts without HTTP requests.
The optional history-source cutoff checks both the frozen seed's source
timestamps and every selected official receipt. It is not a future-card freeze,
feature-completion timestamp, training approval or prediction registration.

## Completed Pro Consultation

The authorized [research conversation](https://chatgpt.com/c/6aca2dc4-d2e8-83e8-acab-e85f281c27b7)
completed with **12m27s** displayed processing time. The final answer was read
after the explicit completion notice and final response controls appeared.
Generation was not stopped and no short response deadline was imposed.
The adviser inspected public PR79/80 code and official detail pages, not local
raw bytes or our tests. Its recommendation was amended for the new collision
evidence: preserve the raw partial contract but require dated official event,
whole-roster and field support for a separately named usable-history candidate.

This execution completes that local data-quality increment. The next meaningful
performance step still requires new pre-race-safe target examples and prospective
single-combination predictions across the full frozen universe. A successful
source reconciliation is not itself model improvement or 70% evidence.
