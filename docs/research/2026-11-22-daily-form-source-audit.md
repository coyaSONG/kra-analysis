# Dated KRA form inputs and the whole-card cutoff

Do not admit these APIs to training or prediction yet. A date filter does
not prove that an exact record version was available before cutoff.

## API153: cumulative form at a historical start

The [official catalog](https://www.data.go.kr/data/15138452/openapi.do)
explicitly includes races run on the requested reference date. Its embedded
schema has racecourse name, actual race date and number, gate, and stable
horse ID, but no row-level publication or revision clock. The six-month
counts are a lagged form candidate; they do not supply distance or class
history by themselves.

A [secondary sample](https://smartrace.kr/data/kra/%ED%95%9C%EA%B5%AD%EB%A7%88%EC%82%AC%ED%9A%8C-%EA%B2%BD%EC%A3%BC%EB%A7%88-%EC%9D%BC%EC%9E%90%EB%B3%84-%ED%86%B5%EC%82%B0%EC%A0%84%EC%A0%81-20240922)
shows three runners from the same September 6 Seoul race. Gate and horse ID
matched three rows in the [official result](https://race.kra.co.kr/raceScore/ScoretableDetailList.do?Act=04&Sub=1&meet=1&realRcDate=20260906&realRcNo=1),
which was already held locally. Each displayed runner has one start in both
lookback windows; the first-, second-, and third-place counts agree with
its official finish (first, third, or eighth). This corroborates same-race
information in the sample, not the completeness or consistency of the feed.
The mirror displayed an update date after the race; a separate raw capture
timed out without retry. Eight official result rows were not in the excerpt.
Provider-wide missingness and join coverage are unknown.

Replaying the unchanged schedules for 304 races and 3,140 declarations
across six blocks gives this calendar-only check:

| Rule or risk indicator | Races | Declarations |
| --- | ---: | ---: |
| Race date minus one day is on or after the first block cutoff's KST date | 204 | 2,089 |
| Within those reference windows, the same physical venue had an earlier scheduled day after the cutoff | 106 | 1,082 |
| Same stable horse ID declared on an earlier date in that within-block window, across all venues | 0 | 0 |

The same-venue count includes 66 Seoul and 40 Jeju races. Matching the
original declaration keys shows why it is a schedule-level hazard, not
106 leaked outcomes or rows for those horses: none of the later declarations
has the same ID on an earlier date within its block. This does not establish
what an API153 response would contain or exclude other late records or
revisions. No such response or result values from these 304 races were used.

## The request clock matters too

For all six original panels, recheck the first complete national and regional
schedule capture and the last original API26 entry receipt. At the later of
the two saved observations, both inputs were locally available on a
Wednesday. Using just the day before the Friday first cutoff would select
Thursday, which was still in the future in **all six**. The most recent
completed day at the observed readiness point was Tuesday, two calendar
days earlier than the cutoff-only limit. This describes the saved receipts,
not a publication schedule or the availability of an API153 response on Tuesday.

For any separately authorized trial, cap both the requested reference date
and every returned source race date at one calendar day before the earlier
of the KST date of the actual request start and that of the original whole-card
cutoff. Require request and receipt before the cutoff, and independent
evidence that the exact bytes existed before it. The day limit is necessary
under this completed-day policy, not sufficient to admit any value.
Bind each row to a completed earlier race using physical venue, date,
race number, gate and horse ID, then join the frozen target roster by
stable horse identity. Confirm coverage, zeros versus missing rows and
revisions; keep unknowns distinct. Do not join by name, subtract target
results from cumulative fields, or delay the existing M0/API27 collection
to wait for this optional source.

## Other catalog candidates

- [API316](https://www.data.go.kr/data/15133742/openapi.do) describes confirmed
  Busan and Yeongcheon entries, including equipment and prior-treatment text.
  The public description lists no physical venue or stable horse ID. Verify
  the actual fields; without a venue field, require a complete official
  schedule that uniquely assigns the date to one of the two venues. The
  mirror's 7,988 records are not a frozen roster or proof of publication time.
- [API23_1](https://www.data.go.kr/data/15056699/openapi.do) describes
  nominations, not a confirmed roster. The previously observed gateway code
  30 remains an access failure. No new request was made.
- [API151](https://www.data.go.kr/data/15138444/openapi.do) includes the
  reference day for jockey form and documents a combined southeastern region.
  Its regional code is not a physical venue ID.

## Local evidence

- API153 catalog captured once at `2026-11-22T11:32:53.788255Z`, raw SHA-256
  `0e603ec88763859323e326222eb296d8f69e52406b9b6d1fb6d4039aaac94210`.
- Official result captured earlier at `2026-10-11T18:08:36.069038Z`, raw
  SHA-256 `5be5f268e78ebe0e2b1e11647787a35c3e16a002568788e1c46daec64928307b`.
- Receipts and reproducible offline observations are in the ignored local
  archive `.cache/autoresearch/api153-daily-form-source-20261122/`;
  `readback.json` SHA-256
  `896022fa48f190e4e8cb5ad3d6809a5a8894760bc13d00d5f79cd5a21511b763`.

- The completed-day audit is retained separately in the ignored local
  archive `.cache/autoresearch/daily-form-effective-cutoff-20261123/effective-cutoff.json`
  with SHA-256 `c72dde2b7dad94ac5bbb049d1973f80ad12596f04ad58cb2ba472858b3fac284`.
  It replays the exact schedules and 80 entry manifests without new calls.
  The Python and SQL identity counts agree, and a separate calendar check
  reproduces the six boundaries from the pinned times.

The catalog is not a dated-form response. No live data API was called, no
training rows were admitted, and no evaluation dates or model files changed.
