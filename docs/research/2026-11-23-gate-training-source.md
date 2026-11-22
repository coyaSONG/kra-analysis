# Routine start training printed on the original full cards

Full-card gate training evidence SHA256: `16b01208beb2c76054d5382c8d047d3079654e6afb1eb7a370067cf8768e14b2`.

Routine start practice offers a distinct dated observation when
earlier competitive form is sparse. This source-only review does
not infer a horse's ability, change a prediction, or estimate lift.

## Distinct sources and clocks

The [KRA practice catalog](https://www.data.go.kr/data/15059043/openapi.do)
documents a training day, stable horse ID, rider and practice result.
It groups the southeastern region in the request and is not evidence
of physical venue or exact record publication time. No data operation
was invoked. It differs from the [timed trial catalog](https://www.data.go.kr/data/15056974/openapi.do)
and from the qualification and assistance roles described in the
[KRA starters' instructions](https://race.kra.co.kr/down/starters_Instructions_2024.pdf).
Do not infer frequency, pass/fail, or a preferred sign from one dated
annotation. Special assistance, blank and missing are not equivalents.

Replay the existing independently timed October PDF archive and the
November local-only archive. Check the digest and receipt of every PDF
and match every declared gate and printed name before linking its
original stable horse ID. Read only its current-runner panel. Keep
the exact literal practice line, date, rider, status, page/box, local
receipt and cutoff. The October source manifests in PRs
[#99](https://github.com/coyaSONG/kra-analysis/pull/99) and
[#100](https://github.com/coyaSONG/kra-analysis/pull/100) bind the raw
bytes by the original first cutoff. This does not prove when KRA first
published them, the time the training occurred, or that these
annotations were inputs to the original M0/API27 predictions.

Only a strictly earlier Korean calendar day supplies a date
difference. A printed date on the receipt day is not a known event
time; a blank is not evidence that training did not occur.

| Original complete card | Races / declarations | Earlier printed date | Same receipt day | Blank | Every runner earlier | At least two earlier dates |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Oct 16-18, independent content witness | 50 / 534 | 452 | 0 | 82 | 13 races | 49 races |
| Nov 20-22, local only | 51 / 540 | 315 | 144 | 81 | 1 race | 48 races |

October earlier-date counts by physical venue are Seoul 198/229,
Jeju 98/137, Busan 95/102, and Yeongcheon 61/66. Of the 124 October
declarations lacking both comparable prior form and the signed-burden
reference in the fixed source audit, 104 have a date. This is a
separate measurement, not a recovery of those missing operands.
The complete proposed workload comparison already broke every
exact parent-vector tie on this panel. The new date does not resolve
another such tie; its incremental value versus workload is unknown.
Literal status differs among earlier-date declarations in 25 October
fields; most earlier lines (416/452) print the same favorable word.
Neither the 49 nor the 25 is an accuracy, expected lift, or a
sample of independent trials.

## Bounded original-site corroboration

The [Seoul official routine-practice listing](https://race.kra.co.kr/startingData/startingTrainList.do)
and its exact selected November 18 detail returned HTTP 200, at
2026-11-22 18:53:32.679652 and 18:53:48.557645 UTC. Both were read
once with the existing collector, no credentials or retries. The
daily count of 116 agrees with the sum across 34 trainer groups.
The returned detail is a group index, not a horse sheet; it contains
no per-horse rows. Horse-ID join coverage is therefore unmeasured,
not zero coverage of the underlying registry. No additional group
selection was made. These observations came after the November
cutoff and do not backdate either source or confirm PDF practice
rows from that card.

Seoul group observation SHA256: `3ab6fe4505c62662c0925ebb2edf4e8047dee41124171366e03813d24bbae068`.

## Model research boundary

[Chung et al. (2024)](https://doi.org/10.5351/KJAS.2024.37.2.239)
motivate studying earlier starting practice, not importing a published
feature direction or equating their event counts to one printed date.
[So et al. (2025), Table 6](https://journal.kci.go.kr/jksci/archive/articlePdf?artiId=ART003266151)
report 3.14%, 5.24% and 0.00% for the three models' unordered trio
comparison, different from their NDCG ordering. The study describes
191 Seoul races in grouped folds. Its separate 9,140-observation
collection scope and exact pre-cutoff input versions are not a
complete walk-forward cohort for this research. None of those
figures is a bound on KRA performance or a result for our models.

For a later candidate, first observe the exact prospective PDF
on each official complete card and independently witness its bytes
before the unchanged deadline. Keep training, gate assistance,
trial and competitive results separate. Check a stable dated
practice source against the printed field before proposing which
typed date or status could be eligible. Then compare one fixed
addition against the same eligible base, with an explicit missing
policy and separately preregistered future whole cards. Do not
omit a runner or a race because a source is missing. The M0/API27
whole-card publication takes priority over any optional research.

## Verification

The local archive `gate-training-source-20261123/` retains raw
receipts, complete inventories and replay scripts. The independent
calendar/identity readback SHA256 is
`2b0502ead0a70dfa06acea19cc42c61a55919325d2a300fb741ddfc8dc3d3981`.
All 228 related local tests and Ruff passed. No target outcomes
were loaded; no model was trained, scored or promoted.
