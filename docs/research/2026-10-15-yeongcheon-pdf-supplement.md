# Yeongcheon Pre-race PDF Gap Closed

## Result and Meaning

Captured the six previously unsupported Yeongcheon races, with **66 runner
appearances**, before the frozen October 16-18 block. Seven HTTP requests
(one complete API26 page plus six PDFs), zero retries. A preceding one-PDF
schema probe is separately retained and is not an eligible source receipt.
The fresh API rows exactly match the original frozen venue-4 entry rows.

Together with PR99's untouched 44-race supplement, this supplies PDF training
count/minutes for **all 50 races / 534 appearances**. This is source coverage,
not prediction accuracy, complete clinical information, or permission to fit.
M0/API27 predictions, model pins, original 24-column reservation and the entire
evaluation population remain unchanged. No outcomes were requested or loaded.

## Identity Evidence

The [official national race list](https://race.kra.co.kr/thisweekrace/ThisWeekDetailInfoList.do)
and [Yeongnam entry list](https://race.kra.co.kr/chulmainfo/ChulmaDetailInfoList.do?Act=02&Sub=1&meet=3)
both associate physical venue 4 with six URLs under the shared
`/down/pdf/busan/chulma/b_run_hr_261018_NN.pdf` location. URL storage and regional
menu code do not determine physical venue. Each actual PDF page explicitly
prints Yeongcheon, race number and date; race 1 was also visually inspected.
No Busan observation was relabeled as Yeongcheon and no prefix was stripped.

The captured official HTML hashes are
`88f26631089b81a62042e37f88d4a3287c4efc43bd233420174efafef7b52fe5` (national)
and `49c67c03204b9ef08ae032c7e50fe98c813f6a7b6338c549e3687e5a31693eba` (regional),
from the 2026-10-15T11:05:10Z schedule capture. Source replay validates every
PDF page, complete full-name/gate/horse-ID entry join and schedule. A Busan
footer at the shared URL fails a Yeongcheon request, and vice versa.

## Availability and Missingness

The six actual PDF completion timestamps span
**2026-10-15T12:02:37.189926Z to 12:02:46.805514Z**, before the first whole-block
cutoff **2026-10-16T01:20:00Z**. These are local capture clocks. A later remote
publication receipt supplies an independent content-existence bound, not an
upstream publication-time or authenticity certificate.

| Field | Observed / 534 | Missing / 534 |
| --- | ---: | ---: |
| training_count, training_minutes | 534 | 0 |
| training_window_days | 137 | 397 |
| training_gu_count, training_seup_count | 397 | 137 |
| swimming_count, swimming_laps | 397 | 137 |
| trainer_wins, trainer_win_rate | 366 | 168 |

The new 66 rows have four missing trainer summaries and all 66 have unknown
training-window duration. Do not impute a two-week window from Jeju's template.
Printed zeros remain zeros; missing values remain null with flags. Across all
534 rows, 14 training summaries remain truncated under the original rules.
Historical result tables adjacent to current-horse panels are not features.

## Connection to Similar-race Research

Exact `(race_id, runner number, canonical horse ID)` joins to PR98's pinned
condition-memory snapshot cover all 534 expected appearances without duplicates.
All **79** appearances lacking observed recent 90-day history now have PDF
inputs (previously 75); all **225** condition-fallback appearances have them
(previously 173), including **52** at Yeongcheon. The historical archive remains
partial: no observed history is not proof of no racing career.

The next testable hypothesis remains that training activity adds information
when similar distance/class history is sparse. The source gap is now closed
for this block; performance remains unknown. Preserve original M0/API27 as the
only committed comparison here. After results, source/label/recipe review may
admit these observations to a training snapshot; any model selected using them
requires a separate, later frozen future block. Do not call a retrospective
ablation on these same races independent validation or promote after one week.

## Frozen-code Compatibility

Initial expansion changed a legacy PDF replay file that is also hash-pinned
by M0 and the outcome evaluator. A broader regression run exposed 14 failures.
Restored the file byte-for-byte; did not change frozen pin constants or skip
those tests. The separate `autoresearch/yeongcheon_pdf_replay.py` supports the
new profile while mirroring the full existing raw-source validation contract.
Shared helpers are reused unchanged. Negative replay tests run for both
physical venues 1 and 4. Final focused and forward/evaluation regression suite:
**360 passed**. Earlier 180 passes are contained in this suite, not additive.

The six source captures and original derived artifacts from commit `2ac5bc5`
remain immutable. After isolating replay, v2 input-plan/bundle files record the
new implementation fingerprint. Their source manifests are identical to v1;
feature bundle content is identical except for the implementation fingerprint.
The original PR99 plan intentionally rejects a changed implementation; reproduce
that full bundle with its original commit `c0367769150211961349c6e7f52ec5b5db9bf5b7`.
Separate raw-chain compatibility checks reparse all 44 previous sources without
changing their saved manifests, parsed outputs, audits or projected features.

## Reproducibility and Limits

Archive: `.cache/autoresearch/yeongcheon-pdf-supplement-20261015`.
Original report SHA256:
`66011ecd1fac7307dabb7f23c818e552cc607e0e1e29bebeaf94fe122ea5d41e`.
The additive public registry is
`supplements/2026-10-16-18/pdf-source-manifest-with-yeongcheon.json`; it references
the unchanged PR99 registry hash, original/v2 extension pins, source hashes,
capture times, full population missingness and local verification-script hash.
It does not overwrite `pdf-source-manifest.json` or any prediction commitment.
Registry SHA256:
`10074357d3582c5aa94b6c8d0c7b9dbcbfa84e4cff9844457c020bc82369a104`.
All 50 raw source chains were revalidated; original M0 model admission also
passed with the actual pinned local model, not only synthetic test fixtures.

The retained `verify_union_v2.py` checks pinned source inputs, old raw replay,
new offline bundle equality and the complete join before producing
`verified-union-manifest-v2.json`. Its exclusive writes prevent replacing an
existing verification record. Reproduce in a separate analysis output location
with the same original archives; do not rerun acquisition merely to reproduce.

Pro consultation is unavailable: the authorized in-app ChatGPT browser was
opened and showed login controls with no authenticated session. No question was
submitted and no consultation is claimed. Model improvement and the 70% goal
remain unproven; actual results are pending.
