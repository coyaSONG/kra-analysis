# Historical time-information feasibility, without fitting

## Decision

The original May archive can support descriptive time-gap and pace-allocation
quantities, but **cannot test their within-horse repeatability**: all 1,029
observations belong to different horses. Do not fit a new candidate from this
bounded study or infer that pace has improved future prediction.

Relative time has the same nondecreasing order as historical finishing rank,
with printed-time ties. Pace ratios have mixed ordering relative to rank, so
they are not simply the same ordering in another unit. Neither result measures
incremental predictive information. A time gap can retain margin magnitude
even when its ordering repeats rank; non-equivalent pace ordering can also be
noise rather than useful ability information.

The next useful research action is to inventory repeated, correctly linked
starts in the **already preserved broader historical corpus**, before proposing
any extension of this measurement. Keep the proposed 1-180-day, same-physical-
venue, exact-distance rule fixed; do not extend it until coverage looks better.
Any additional source mapping needs its own source/version/availability audit.
No new fitted candidate, A24/B34 retraining, future roster or date enrollment
is authorized by this report.

## Population and Coverage

The grain is one horse in one historical start. All **102 races / 1,029
observations** are retained. The archive's planned interval is May 1-14; its
row-bearing dates are May 1, 2, 3, 8, 9 and 10. Its 44 `empty_unconfirmed`
inventory units remain unresolved, not declarations of no racing.

The unchanged historical support policy admits 1,001 observations, excludes
11 for a whole-race source/rank conflict, and withholds 17 other starts.
Passing time arithmetic does not override those exclusions.

| Descriptive quantity | Non-null / all 1,029 | Missing breakdown |
| --- | ---: | --- |
| Relative total time | 1,001 (97.28%) | 11 conflict + 17 other withheld |
| Initial speed ratio | 705 (68.51%) | 296 supported Jeju endpoints unverified + 28 withheld |
| Final speed ratio | 705 (68.51%) | 296 supported Jeju endpoints unverified + 28 withheld |

These percentages are **input coverage, not triple accuracy**. Among the
1,001 supported observations, 705 have pace ratios; that denominator is not
a substitute for the full population. Future target coverage is unknown
while the interval, roster and N remain unset.

All 18 observed venue/distance groups are retained in the JSON, with counts,
distinct values, minimum, median, maximum and missing reasons. The full
population is not replaced by the groups where pace exists.

## Definitions and References

The computation uses exact rational arithmetic over the printed decimal seconds.
Let T be total seconds, E the initial 200m seconds, L the verified final 600m
seconds, and D nominal distance in metres:

    relative_time       = (T - m) / m
    initial_speed_ratio = 200 * T / (E * D)
    final_speed_ratio   = 600 * T / (L * D)

m is the median total time of all already-supported finishers of the same
historical race, including the focal horse. There must be at least two OTHER
eligible comparison horses. If an otherwise eligible reference has invalid
total time, the entire reference median is withheld rather than silently
dropping that runner. Positive-time excluded starts never enter the reference.

There are **101 usable reference groups**, containing 7-15 supported finishers,
and one zero-member group from the excluded conflict race. Every usable group
has nonconstant relative times. Both pace quantities vary within each of the
69 races where they are available; the other 33 races are all-missing for pace.
Every group preserves its member IDs, excluded IDs/reasons and exact median.

Seoul uses the separately printed final-600m value only after replaying its
agreement with total minus the identified cumulative checkpoint. Busan uses
the verified segment table; the previous audit also validates the labelled
cumulative positions. Jeju retains total time but receives null pace quantities:
we do not invent a cumulative relationship or transfer another venue's layout.
Overlapping final 600m and 200m values are never summed.

The output preserves raw time columns, event/gate/horse IDs, nominal distance,
literal conditions, support status and operand/reference clocks. Fractions
in the output are exact ratios, not claims of precision beyond the original
one-decimal time measurements.

## Rank Redundancy Diagnostic

For all unordered runner pairs within each original historical race, the
following compares the sign of the quantity difference to the rank-number
difference. Missing pairs include withheld and unverified observations.
It does **not** choose a favorable direction or calculate top-three hits.

| Quantity | Same order | Opposite order | Quantity-only tie | Missing pair |
| --- | ---: | ---: | ---: | ---: |
| Relative time | 4,381 | 0 | 146 | 222 |
| Initial speed ratio | 1,817 | 1,456 | 18 | 1,458 |
| Final speed ratio | 1,114 | 2,172 | 5 | 1,458 |

Each row accounts for the same 4,749 within-race pairs. Pairs are highly
dependent and are not 4,749 independent validation samples. No rank-only
tie occurs in this source subset. The synthetic tests cover both types of
ties so printed precision is not misreported as strict rank equivalence.

Relative time is a monotonic transformation of total time within a fixed
reference race, so lack of reversed ordering is expected. The different
pace-ratio orderings establish only descriptive nonredundancy of ordering.
There is no target-correlation screen, learned normalization, PCA,
regression, loss selection or model fitting.

## Repeat Support and Time Boundaries

The seed independently contains **1,029 unique horse IDs, one observation
per horse**. Consequently no observation has an earlier same-horse start
under the proposed rule, even before imposing venue or distance restrictions.
All 1,029 rows retain a zero structural-prior count rather than disappearing.
This does not imply that those horses never raced before or that a future
roster has zero coverage; this short archive simply cannot answer that question.

For illustration of the fixed window's calendar boundary, the latest observed
May 10 start can contribute through **November 6, 2026** under an inclusive
180-day rule, and none of these starts can contribute after that date. This
is an expiration calculation, **not a registered evaluation date**.

Structural counts ignore source availability deliberately and are labelled as
such. Applying an as-of diagnostic additionally requires:

- The historical start is 1-180 calendar days before the hypothetical target.
- Horse ID, physical venue and exact distance agree.
- The historical start remains supported.
- Every selected operand, historical reference member and semantic-source
  version is known strictly before feature freeze, itself strictly before cutoff.

Synthetic tests cover same-day/future starts, 180/181-day boundaries, late or
missing source clocks, late reference members, and ambiguous duplicate versions.
The helper rejects multiple versions unless one was already explicitly pinned;
it does not choose a latest version or rewrite an earlier as-of view.

Historical results were locally collected in October, not before their May
starts. The official sectional guide was captured on October 20 at
17:51:17.911965Z. The diagnostic conservatively includes that semantic-evidence
clock. This does not prove upstream publication time and cannot insert new
time-derived inputs retroactively into the frozen October A24/B34 contract.
No actual future roster was passed to the helper.

## Provenance and Reproduction

The audit first replays the entire
[endpoint arithmetic audit](2026-10-20-sectional-arithmetic.md), which replays
original source hashes, API/HTML identities, known layouts and preserved
eligibility. It then joins only the frozen race IDs, not unrelated list-page
receipts in the same archive. No collection or retry occurs.

Original root: `.cache/autoresearch/observed-history-extension-20260501-14`.
Seed SHA256:
`561bcfdc6fe2c4733e571b8c77034a2753e88794d5d7d3a6ee5d2ee2f25a5407`.
Official archive SHA256:
`8ca56ba232156beb824e9baab1f4c8c5b301e8d619f81e17d1213e8f6512e1bd`.

The immutable [report](experiments/2026-10-20-time-information/report.json),
generated at **2026-10-20T18:14:40.697686Z**, has SHA256:
`f9d8e4843ba4144bb3ee5d154fb09af4aa2bd7a8582e99d49484314c7f65905f`.
It carries implementation hashes, all original official source pins/URLs,
the guide receipt, full-population observations and derived summaries.

From the repository root:

    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m autoresearch.time_information_audit
    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m pytest -q -p no:cacheprovider packages/scripts/autoresearch/tests/test_time_information_audit.py

The audit prints a timestamped report; do not overwrite the published version.
A separate local companion,
`.cache/autoresearch/sectional-arithmetic/check_time_information.py`, imports
neither the new audit nor its functions. Its HTMLParser extracts the original
102 pinned pages, checks all 1,029 identities and API total times, independently
recomputes eligible medians and ratios, and confirms 1,001 / 705 / 705 non-null
counts and 1,029 unique horses. This is computational cross-checking of the
same evidence, not external truth or predictive validation.

The initial integration run exposed two adapter assumptions: the guide receipt
uses `capture_completed_at`, unlike a race receipt's `completed_at`, and the
archive includes list responses. Both were fixed with loader regression tests.
No remote requests or original-file edits were used to recover.

Local validation passed **239 related tests**, including 45 cases for the new
diagnostic, plus Ruff lint and format checks. The saved-model, fit-receipt,
M0/API27 commitment and empty forward-registry hashes were checked unchanged.

## Status

Confirmed: original identities, unchanged support population, arithmetic-backed
quantities, descriptive variation and absence of repeated horses in this archive.
Partial: time-information feasibility; Jeju pace semantics remain unverified.
Unknown: longitudinal stability, additional predictive value and future coverage.
Not approved: training, model promotion or evaluation enrollment.

The 70% full-universe exact-single-triple goal is still unmet. M0/API27 commitments,
A24/B34 saved models and consumed fit budgets, earlier reservations and the empty
future-review registry remain unchanged. Required-check and normal-merge receipts
are recorded on the pull request; this report is not independent future validation.
