# June historical acquisition during API unavailability

## Result And Research Decision

Acquired official result HTML for 237 listed races from June 1-July 4, containing
2,375 runner observations from 1,905 distinct horse IDs. June alone contributes
204 races and 2,046 rows; July 1-4 contributes 33 races and 329 rows. All 237
detail bodies match their listed date, physical venue and race number. Of the
2,375 rows, 2,339 have a numeric rank and valid positive recorded time; the other
36 remain explicit observations and do not contribute numeric prior counts.

These are **official-HTML-only observations**, not API214 results, dual-format
corroborated rows, approved training samples or prospective performance evidence.
The API remains unavailable in this run. No model fitting or promotion occurred.

Adding this separate evidence tier raises observed prior-history coverage on
the unchanged 6,816 target rows from 4,435 (65.07%) to 5,718 (83.89%). This is a
coverage study, not an accuracy measurement. Keep the original API-supported
count unchanged and report the mixed-source count separately.

The acquisition primarily fills the left edge of the July-October archive.
June events cannot enter an October target's fixed 90-day lookback. They are
useful for historical feature feasibility and longer-horizon candidates, not
an immediate change to the frozen M0/API27 or prospective 24-column contracts.
Before more historical expansion, prioritize API corroboration of this catalog
when service returns, and explicitly review any proposed 180-day feature study.
Do not silently widen the existing 90-day contract to make coverage look better.

## API Failure Evidence

The frozen June 1-July 4 plan covers all 136 date/physical-venue units with a
512-request ceiling. API214 June 1 venues 1, 2 and 3 each timed out after 30
seconds. The existing three-failure breaker stopped the collector. Its exported
attempt contains three failures and 133 unattempted units, not an empty month.

Four separate credential-safe probes also timed out after 45 seconds without
an HTTP status or response bytes: June 5 venue 3 API214, formerly successful
July 5 Seoul API214, June 5 venue 3 API26, and one later June 5 API214 recovery
probe. The last ended October 13 at 00:19:47 KST. An unauthenticated request to
the gateway returned HTTP 400; this confirms reachability only, not authenticated
endpoint health. The failure is not observed solely on June dates. Its root cause,
including whether maintenance, throttling or another upstream issue is involved,
is unknown. No parser, credential, timeout policy or frozen collector was changed.

API usage in this increment was three reserved collector requests plus four
diagnostic requests. No API rows were obtained. Original failure receipts remain
intact; resumption must be an explicit bounded retry, never an overwritten run.

## Official Source Validation

The existing collector first captured 12 official list pages. Their date ranges
extend past June into May in all three menu regions. `official_history_catalog`
replays those pinned pages and filters their listed physical race identities to
June 1-July 4. It does not generate dates or infer races from a usual calendar.

Its explicitly typed request index contains 237 identities and binds a bounded
detail archive: 237 result pages plus 12 list pages collected by the reused
fetcher. Detail observations were captured October 13, 00:16:59-00:18:33 KST.
Including discovery, this increment made 261 official HTML requests. No failed
or unknown detail slots were observed. The 12 fetcher-added lists are retained
but do not silently replace the original discovery index.

Replay verifies source and receipt hashes, request identities, response URLs,
HTTP status, byte counts, local capture ordering, and complete parseable result
table structure. It compares each dated body against the requested physical
race ID, preserves all runner rows, and excludes unresolved rank/time from
numeric history. It does **not** establish API agreement, independent source
corroboration, complete actual starts, global national completeness, historical
pre-race availability or result finality. KRA HTML and API may share upstream data.

Each detail row retains roster/timing positions, and each group retains its
discovery page, list order, row position, links, row text and source receipt.
An explicit void-race notice in a list row withholds that row's numeric history
pending scope review, while preserving the captured detail observations. Such a
notice appeared on the October 10 Seoul row outside this catalog's date window;
none appeared on its 237 selected races. This conservative notice guard does not
prove finality or resolve every possible correction notice. The reused collector
retains its serial requests, 30-second HTTP timeout and 60-second request deadline;
it has no new failure breaker. The fixed plan bounds it to 249 requests, with no
automatic retries. All requests in this run completed successfully.

The reused archive format internally calls the request-index pin `seed_sha256`.
Here that pin refers to `official-list-request-index-v1`, never to a fabricated
API seed. No HTML row enters `reconcile_group` as an invented API row.

## Fixed Target Comparison

The original API/HTML history plus July 5-11 extension was freshly replayed.
Its report exactly reproduced the prior hash. The comparison then pins this
derived baseline and independently replays the new HTML catalog. All original
671 race groups and 6,816 runner rows remain, including unsupported target groups.
Prior events satisfy `[target date - 90 days, target date)`; same-day/future
events never count. Duplicate history identities and overlapping numeric source
tiers are rejected. Zero observations are not interpreted as debut or no starts.

| Measure on identical targets | API and HTML supported history | Including new HTML-only history |
| --- | ---: | ---: |
| Runner rows | 6,816 | 6,816 |
| At least one prior result | 4,435 | 5,718 |
| At least three prior results | 630 | 1,519 |
| Groups where all runners have a prior result | 155 | 237 |
| Groups where all runners have three prior results | 0 | 0 |

An additional 1,283 target rows gain at least one observed prior result. By
target month, the gains are July 734, August 471, September 78 and October 0.
There are still 1,098 target rows without such a prior observation. No complete
three-prior roster exists even in the mixed-source view. More history can reduce
sparsity, but it does not eliminate missingness or prove predictive value.

The new HTML-only tier alone supplies at least one prior observation for 3,348
targets and at least three for 94. These overlap the original supported-history
population and must not be added to its covered-target counts. The 5,718 combined
count is computed per target, not by adding 4,435 and 3,348.

## Reproduction And Pins

The base source pins and replay command are in
`docs/research/2026-10-12-history-expansion-pilot.md`. Running that command to
`.cache/autoresearch/history-coverage-20261013/baseline-replayed.json` reproduced
SHA256 `724d0427aaf35b3da2a247faf1bbb10d6b99f49decab93f0155e076742818620`.

The new API plan SHA256 is
`679676e6661413ddfe66756b8f15dfe6d69fb35efbaa59d9879dcb099d57ef05`.
Its failed `seed-attempt-1.json` SHA256 is
`e37820d22512420cbc176419c1697ffa824d4414029c9c31b310845f2495b279`.
Both are under `.cache/autoresearch/observed-history-extension-20260601-0704`.

From the isolated checkout root, replay the catalog comparison with a fresh
output filename; exclusive saves intentionally reject overwriting evidence:

```sh
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.official_history_catalog compare \
  --directory .cache/autoresearch/official-june-catalog-20261013 \
  --discovery .cache/autoresearch/official-june-discovery-20261013 \
  --index-sha256 2bc608269678ba7ebcfa55a8a7650cbc7b4d7987435dee367f2da0f5976dd7dd \
  --archive-sha256 5208e231e93289ca1a9e3d21e68d4e5051f830dd7b1afa3246fe00a2415fb220 \
  --baseline .cache/autoresearch/history-coverage-20261013/baseline-replayed.json \
  --baseline-sha256 724d0427aaf35b3da2a247faf1bbb10d6b99f49decab93f0155e076742818620 \
  --output .cache/autoresearch/history-coverage-20261013/replay.json
```

The discovery archive SHA256 is
`bd3e5440ca35e0594ca017a02272dee2976d1a6536ad98d8bcb6e3a14c42f0b8`.
The final executed `html-only-comparison-v2.json` SHA256 is
`f11b00bf586877fcc4ff1a2b86924174334c12c27b9e3b55ed18406a9928b98d`.
The first comparison remains preserved alongside it; the final version adds
source positions, list-notice withholding, reasons and separate HTML-only totals.
The comparison embeds the full catalog observations, per-target source-tier
counts and lineage, and false training/performance approval flags. Raw archives
and secrets stay local and are not committed.

## Validation And Open Questions

Seventeen new tests exercise mocked capture through raw replay, source pins,
changed membership, wrong dated bodies, failed detail retention, exact prior-day
boundaries, unresolved ranks, duplicate targets/history, tier overlap, repeated
list pages, void-notice withholding, and June exclusion from October 16's window.
The combined new/history/M0/API27 regression run passed 180 tests. Ruff passed.
No existing
frozen collector, model or forward contract source was edited.

The authorized [ChatGPT Pro consultation](https://chatgpt.com/c/6aca2dc4-d2e8-83e8-acab-e85f281c27b7)
completed on October 13 KST. Generation was not interrupted and the response
was read only after completion. Pro reviewed the shared evidence and public
PR90, not this local archive or new implementation. Its advice supports an
explicit HTML-only acquisition tier, unchanged target membership and API counts,
ending this unsuccessful API diagnostic round, and separate future review of
longer lookbacks. We adopted source-row provenance, notice withholding,
source-specific totals and an October-window regression. It did not independently
validate the 2,375 local rows and does not provide training approval.

Remaining limitations are API unavailability, unproven completeness and data
finality, and late capture relative to historical targets. Existing prospective
collection can continue independently when cards become available. Paid services
remain deferred, and coverage gains do not count toward 70% prediction success.
