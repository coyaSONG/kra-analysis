# Older Career Memory and Recent Condition Sensitivity

## Result and Decision

Created an isolated, outcome-free feature snapshot for all **50 frozen races /
534 runner appearances** on October 16-18. Additional May observations affect
the separate older-career descriptor of 209 runner appearances. The existing
90-day condition ledger and all M0/API27/public training-input manifest hashes
remain identical. No new predictions, fits, outcome comparisons, score blends,
model promotions or evaluation arms were produced.

The next model hypothesis is that recent condition contrast, support counts,
explicit fallback state and separately represented older general experience
may be more informative together than an unsupported condition score alone.
This snapshot makes that hypothesis testable later; it does not show an
accuracy gain. Keep the existing single recent contrast; do not choose another
window or tune its distance tolerance against these targets.

## Fixed Recipe

Implementation and design were committed as `0da120d` before the real-data
run. Each target row contains only identity plus candidate input features,
source IDs and separately marked sensitivity diagnostics. No target outcomes
are read. The CLI refuses to create a snapshot at/after the first published
cutoff, 2026-10-16T01:20:00Z. Creation was 2026-10-15T11:17:07.233174Z.

The recent band remains `[D-90,D)`: same physical venue, exact class label,
distance within 200m. Its contrast is unchanged `joint90 - expanded90`, with
the existing per-runner baseline fallback. Recent prior count, qualifying
prior count and fallback reason accompany the value.

The older band is disjoint `[D-180,D-90)`, or ages 91-180 days. General career
form uses the existing descriptor `(1 + sum((N-r)/(N-1))) / (2+n)` on these
older observations only. It is null when there are no observations, unlike
an observed value of 0.5. Older count, same-venue/class/distance match count,
other-venue count and missing-condition count remain explicit. This is not a
new 180-day prediction rule, and older similarity does not replace recent
fallback. Source tiers, every contributing race ID and added-May IDs are kept.

Separately, delete each recent observation once and recompute the original
contrast using its original fallback. Store all 1,016 cases, exact Fraction
min/max, disappearance of support, zero collapse and strict sign reversal.
These are deterministic stress diagnostics, **not confidence intervals**,
independent samples or additional candidate input columns. Shrinkage and
membership both change during deletion; no isolated causal condition effect
is inferred.

## Whole-Population Findings

| Quantity | Runner appearances / 534 |
| --- | ---: |
| At least one older-band observation | 378 |
| Older history but no recent 90-day history | 31 |
| At least one same-venue similar older observation | 164 |
| Additional May history contributes to older band | 213 |
| Older-career value changes after May expansion | 209 |
| Recent condition fallback, unchanged | 225 |
| Nonzero recent contrast, unchanged | 114 |
| Exactly one qualifying recent observation | 164 |
| Nonzero contrast can become zero after one deletion | 104 |
| Contrast can reverse sign after one deletion | 13 |

The last two rows overlap and must not be summed. Zero collapse can result
from loss of eligible support or equal surviving form values, not necessarily
an error in data. Observations are partial archived history, not a complete
career census. The 31 older-only rows are not 31 newly covered horses: some
already had June/July older history. May contributes to 213 rows but need not
change their rank average; four retain the same older descriptor.

| Physical venue | Entrants | Older supported | Older only | May contributes | Sign reversal |
| --- | ---: | ---: | ---: | ---: | ---: |
| Seoul | 229 | 157 | 13 | 89 | 6 |
| Jeju | 137 | 102 | 11 | 60 | 4 |
| Busan | 102 | 57 | 3 | 24 | 0 |
| Yeongcheon | 66 | 62 | 4 | 40 | 3 |

Yeongcheon has **zero same-venue similar older observations**. Its 14 entrants
with qualifying recent history each have only one such observation; 52 still
fall back. All nine nonzero recent contrasts can become zero after deletion.
Older general-career coverage therefore must not be called evidence of
Yeongcheon-specific aptitude. Busan remains physical venue 3, not venue 4.
These segment counts diagnose inputs, not subgroup prediction performance.

## Evidence and Reproduction

Input source pins and acquisition details are in
`2026-10-14-history-gap-expansion.md` and
`2026-10-14-condition-delta-diagnostic.md`. The new module reads their exact
SHA-pinned artifacts, verifies target source entries against the frozen
population, rejects target/future history and overlapping conditions, and
compares the entire recent ledger against its previous pin. No fresh API
requests or future-result requests are made.

Artifacts under `.cache/autoresearch/condition-memory-20261015/run-1`:

| Artifact | SHA256 |
| --- | --- |
| report.json | `1d28fe6df8a41bfa15f3342f08dc25fd507ba37461471eb5bbe32f0531daceef` |
| independent-check.json | `369f931a823d6a36ca24c5c9af95de493c3f2306b328e485ff82bf1bd8d8c748` |

The report pins source artifacts, implementation files and the ExecPlan
revision at execution. Later progress edits to the living plan do not replace
that committed revision or overwrite the report. Local-only raw history and
entry data remain in their original archives, with source URLs, receipts,
capture times and raw hashes. The published hashes witness this derived
research snapshot, not an independent certification of the raw upstream data.

Before the cutoff, reproduce in a new directory from the isolated checkout:

    PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.condition_memory_research --output-dir .cache/autoresearch/condition-memory-20261015/replay

After cutoff, inspect the original snapshot; the CLI intentionally refuses
to issue a new timely snapshot. The pure `project` remains usable for offline
recalculation, without backdating or overwriting the original evidence.

An independent calculation scanned all 10,522 historical rows by horse and
integer calendar-day age, used direct Fraction rank arithmetic without the
production window/scoring helpers, and reproduced all 534 feature rows and
1,016 deletion cases. It also checked all source-ID lists, physical-venue
counts, older-band before/after values and the complete target identity set.
All three original public manifest hashes were rechecked unchanged.

Local validation: **350 tests passed** in two disjoint runs (245 + 105), including 26 new tests plus recent
condition projection, historical expansion, fixed form, pre-race conditions
and M0/API27 forward regressions, original source replay and prospective training
reservations. Ruff lint/format pass. At head `8964745`, required Python Checks,
Scripts Checks (including all 26 new tests), Docker Build and Gitleaks passed.
Security Checks failed at dependency audit: its 17 advisory rows in h2,
multidict and pyjwt exactly match PR97 job 115912660044. No dependency manifest
or lockfile changed. Node audit and hygiene were skipped, not passed. Final
head checks and normal merge receipt are tracked in
[PR98](https://github.com/coyaSONG/kra-analysis/pull/98); no admin bypass.

## Limits and Next Experiment

All historical records were acquired after their own races. They are not
pre-race feature examples for those historical targets. This current snapshot
is kept separately before the future October cutoff, but carries
`training_approved=false`, `accuracy=null`, zero fits and no 70% claim.
No uncertainty in prediction accuracy is estimable from this feature audit.
Repeated horses, shared races and overlapping deletion cases are dependent.

After official October results arrive, compare the already published M0/API27
predictions first. Any training or model selection informed by this block's
outcomes must use a later, separately preregistered full-population evaluation.
Do not call the same 50 races independent validation for such a model. Keep
the original 24-column training reservation and published predictions intact.

Attempted to open the authorized Pro research conversation on October 15.
It showed a logged-out screen. No prompt was sent and no new consultation
occurred. Proceeded only with this bounded, outcome-free local research.
