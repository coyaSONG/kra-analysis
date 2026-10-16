# First Intraday Outcome Observations

## Status

This is an observational diagnostic, not a successfully completed canonical
M0/API27 outcome evaluation. The frozen October 16-18 population remains all
50 races. Do not publish a full-block accuracy, a model winner, a 70% claim,
or a model promotion from this report.

At 2026-10-16T02:54Z, API214 captured 170 rows for the two active day/venue
units in three requests. Whole-day responses also contain rows for races
whose scheduled starts are still in the future. Three elapsed races have
matching API and official HTML rosters and unique top-three observations.
The other 47 races remain without a supported outcome in this observation.
An observed unique top three is not a guarantee against later official
correction.

| Race ID | Observed top-three horse IDs | M0 frozen IDs | API27 frozen IDs |
| --- | --- | --- | --- |
| 20261016_2_1 | 3107352, 3107414, 3109099 | 3107414, 3109099, 3109179 | 3108177, 3109099, 3109179 |
| 20261016_2_2 | 3104317, 3107435, 3107507 | 3107435, 3107507, 3107913 | 3107435, 3107507, 3107913 |
| 20261016_3_1 | 56007, 56195, 56446 | 55590, 55874, 56130 | 55590, 55874, 56130 |

Both frozen combinations differ from the observed combination in each of
these three races. This is three combination mismatches per model, not a
completed canonical verified-miss count and not a substitute subset accuracy.
No cancelled or undefined target was established in the three observations;
the target definition of the other 47 is still unknown. Do not convert those
47 to misses. Canonical outcome counts remain unavailable until the outcome
evaluation succeeds. The separate no-outcome verification report has 50
pending entries by construction; it is not a result-informed scorecard.

## Contract Preservation

The current research checkout failed the original paired evaluator's contract
hash check because subsequent PDF research changed files included in the
original implementation fingerprint. No frozen contract hash was changed.
Instead, the repository's PR95 merge commit
`2d78a164e10de0a0249ae8a1968c475295cb5fcc` was extracted into the separate local
cache `.cache/autoresearch/pinned-runtime-pr95`. Its `packages/scripts`,
`data/contracts`, and root `uv.lock` provide the original evaluator runtime.
The existing virtual environment satisfies its pinned dependency checks.

Using this original runtime, the read-only paired evaluator without outcomes
revalidated all 50 races and both models, their original prediction packets,
input reservations, and the archived GitHub publication evidence. Both arms
have `published_before_cutoff` for every prediction. The original M0/API27
commitments still have SHA256 values
`de82b4d1dc1d69b7982af04b7d83557d008381ea23202f0dff661721388f7a2c` and
`a51f7b8ca425251fa6bc7602788031a6675b3b9de195c55db76789d5847f6646`.
The original training-input commitment remains
`b4ab302c93bb01a947bd149622770d3413690f5fa95bbec8c13a00ed2808fa32`.

Attaching the intraday outcome plan to that original evaluator fails closed
with `evaluation_outcome_capture_time_conflict`. The existing adapter retains
whole-day API rows and an official-source receipt for future races; their
capture clocks precede the frozen scheduled start. No exception was caught
and converted into a successful canonical evaluation, and no validator or
frozen implementation was patched to bypass it.

## Collection Scope

The official collector received the complete observed API seed. Its client
guard permitted only the three elapsed detail URLs and the collector's
existing 12 list URLs to reach the network. The 13 future detail URLs were
rejected locally before sending. The legacy receipt format records those
exceptions as `fetch_error`; the sidecar `official-network-scope.json`
explicitly identifies them as local skips, not upstream outages, unpublished
results, authentication failures, or rate limits. They must not be used in
upstream failure statistics. No future detail was fetched and no retry ran.

The raw API capture was copied byte-for-byte into a new frozen seed view,
not re-requested or filtered in place. All original raw capture files remain.
The result observation adapter replayed the 50-race schedule and source pins,
returning `unique_top3_observed=3` and `source_missing=47`.

The schedule retained all 50 identities and roster counts. It updated Jeju
race 2 from 11:40 to 11:43 KST and Busan race 1 from 11:15 to 11:20 KST.
These are monitoring observations, not changes to the frozen cutoff or
population. The six entry API units retained 534 rows. Only `stTime` changed:
10 Jeju race-2 rows and 11 Busan race-1 rows, matching the schedule changes.
No identities were added or removed. No changed response replaced an input.

## Condition-History Diagnostic

The sealed PR102 candidate matrix was read without editing or fitting it.
For the three observed races, recent similar-history fallback counts among
all entrants were 3/10, 2/10, and 5/11 respectively. The observed top-three
horses' similar-history counts were (2, 1, 0), (5, 2, 1), and (0, 0, 1), in
gate order. Thus missing recent history is a plausible diagnostic stratum,
but does not explain every mismatch: all three observed top-three horses in
Jeju race 2 had similar history. There is no causal or performance conclusion
from three races. Retain support counts and fallback indicators; do not tune
their weights or the similarity threshold on these observations.

This is not evidence about Yeongcheon, whose races have not happened. No fit,
training approval, new arm, or new future evaluation block was created. Any
model selected using this block must be tested in a separately fixed later
whole population. The original 70% goal remains unmet.

## Reproduction Evidence

Local observation directory:
`.cache/autoresearch/forward-outcomes/20261016T025641.926810Z`.
It contains immutable `outcome-plan.json`, `outcomes.json`, the frozen seed,
official receipts and raw HTML, the local-skip sidecar, and the separate
`observed-combination-diagnostic.json`.

The outcome-plan SHA256 is
`370bca2adb3e8e00a2d391feb4e978dec37a3a577024120c708ea7404442910b`;
the replayed outcome-report SHA256 is
`05e34664abe55bd973d233c32b9d8e9fc8711d186754f39b37d9c392496d0a92`;
the combination-diagnostic SHA256 is
`6e50de40e32bdcb49ee6e5ced3d3e1dfa72965291ddd64d01e4e60751ec5f901`.
An independent replay reproduced the report and all 50 unique race IDs,
checked the top-three IDs directly from API ranks, and confirmed the original
three commitment pins and the sealed candidate-matrix pin were unchanged.

The no-outcome original-runtime verification is
`pinned-runtime-no-outcome-evaluation.json`, SHA256
`f510f1a39931c0552150a0029c8aaffa80bfd738cdaac41060c99961cf0182a2`.
The unsuccessful outcome run is separately recorded in
`pinned-runtime-outcome-evaluation-error.json`.

The original runtime's `test_local_m0_evaluation.py`,
`test_api27_forward.py`, and `test_versioned_result_observations.py` passed
84 tests. No monkeypatch of runtime policy constants was used for the real
data verification; test fixtures remain synthetic and are not accuracy evidence.

## Next Evaluation Gate

Keep the original evaluator unchanged. A fresh capture after all scheduled
October 16 starts can avoid mixing pre-start rows into that day's outcome
evidence. Capture only that elapsed day and retain the other dates as pending
in the same frozen 50-race universe. Check actual publication, identity,
whole-roster reconciliation, source clocks, and exceptions again; elapsed
time alone does not prove a final result. Do not repeatedly replay the same
known-invalid intraday plan as though new evidence had arrived.
The current last October 16 start is 17:55 KST (08:55 UTC). Defer the next
canonical outcome collection attempt until at least 09:10 UTC and recheck
the official schedule then; this is a collection gate, not a change to any
prediction cutoff or an assertion that results will be published by then.

A separate intraday adapter, if ever introduced, requires explicit review
and tests. It must not silently become the canonical evaluator or alter its
frozen contract. No such adapter is implemented or approved here.

## Completed Pro Consultation

The authorized ChatGPT browser session's model menu showed Pro. Its response
finished with an explicit completion state and a displayed processing duration
of 10 minutes 31 seconds. Generation was not stopped, skipped, or subject to a
short answer timeout. Consultation:
https://chatgpt.com/c/6ad0d05d-5b08-83e8-b4b5-5252f401bb4d

The advisor recommended the separate observational report now, keeping both
the successful no-outcome verification and unsuccessful canonical outcome
evaluation intact. This advice agrees with the implemented boundary. It
reviewed public PR95 code and the supplied execution summary, not the local
raw archive, and did not certify either the observed results or an adapter.

Its main caution was that calling `classify` and `paired_metrics` alone does
not preserve the evaluator's preceding source, identity, full-roster,
lower-rank conflict, population-extra and individual-clock checks. Any later
adapter must preserve those checks, fail on real evidence corruption, and
distinguish narrow proven non-result skips from upstream failures. Its
projection must have a new identity and reference immutable original records.
Differential tests against accepted original-evaluator cases and explicit
mixed future/observed cases are prerequisites, not tests completed here.
This review did not authorize bypassing the original evaluator or changing
the scoring policy. No private raw files or credentials were submitted.
