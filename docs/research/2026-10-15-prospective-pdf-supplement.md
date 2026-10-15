# Prospective PDF Supplement for the Frozen October Block

## Result

Acquired **44 official pre-race PDFs / 468 runner rows** before the October
16-18 frozen block. All 44 sources passed the unchanged parser, full-name/gate
join, schedule and T30 timing checks, followed by full raw-source replay. Five
fresh API entry captures exactly match the original frozen API rows. No M0 or
API27 prediction, model, reserved input or evaluation population was changed.

The complete source registry retains **50 races / 534 runner appearances**.
Six Yeongcheon races / 66 rows are explicitly `unsupported_venue`, not absent
races, failures of prediction or a reason to shrink the evaluation denominator.
The existing parser supports physical venues 1/2/3 only. No venue-4 URL or
layout was guessed, and Busan was not relabeled as Yeongcheon.

## Source Registry

Source: official KRA race-card PDF, joined to API26 by exact race identity,
runner number and full normalized horse name, with canonical horse ID from
API26. The URL forms and feature meanings remain those in
`2026-10-10-race-card-pdf-source.md`; no parser or join relaxation was made.
Feature names in this supplement belong to the PDF source namespace. They
must not be silently equated with similarly named API career statistics.

The machine-readable registry is
`supplements/2026-10-16-18/pdf-source-manifest.json`, SHA256
`8dc5e5424914305118d23c47607a32b8d9e024022133a48ba887605117d0316b`.
It records every frozen race, expected/exported row counts, availability state,
source URL, capture time, PDF hash, source-manifest hash, entry-manifest hash
and full-population field missingness. Private local paths, horse names,
credentials and raw files are not included in this published manifest.

| Evidence dimension | State | Evidence / limitation |
| --- | --- | --- |
| Actual original-byte acquisition | confirmed | 44 PDFs, five complete API captures |
| Local pre-race timing | confirmed | PDF completion 2026-10-15T11:35:58.639056Z through 11:37:20.070875Z; first block cutoff 2026-10-16T01:20:00Z |
| Full roster identity join | confirmed for exported sources | 468/468 rows match full frozen rosters; no fuzzy prefix repair |
| Population-wide PDF coverage | partial | 44/50 races, 468/534 appearances; six venue-4 sources unsupported |
| Independent content-existence bound | pending PR receipt at writing | Verify the merge tree contains the exact manifest hash before cutoff; this is not upstream authenticity certification |
| Training approval / model improvement | not established | Labels are pending; no fit, scoring, recipe approval or accuracy evaluation |
| Clinical completeness / causal interpretation | unknown | Printed training/treatment panels are not exhaustive health or causal evidence |

Coverage is 87.6% of all expected runner appearances, not prediction accuracy.
The inner verified PDF bundle has 44 source requests; only the outer registry
has the complete frozen 50-race population. Never substitute the inner bundle
for the evaluation denominator.

## Field Coverage

Null and explicit zero remain different. Missing counts below include the 66
unsupported runner rows; the report also retains exported-row missing counts.

| Numeric field | Observed / 534 | Missing / 534 |
| --- | ---: | ---: |
| training_count | 468 | 66 |
| training_minutes | 468 | 66 |
| training_window_days | 137 | 397 |
| training_gu_count | 331 | 203 |
| training_seup_count | 331 | 203 |
| swimming_count | 331 | 203 |
| swimming_laps | 331 | 203 |
| trainer_wins | 304 | 230 |
| trainer_win_rate | 304 | 230 |

Each field retains its missing flag, plus a separate truncation flag. Fourteen
training summaries are truncated under the existing conservative parser rule.
Jeju's 137 rows have the explicit two-week window; missing Seoul/Busan windows
are not treated as two weeks. Unprinted Jeju swimming/trainer statistics stay
null. For trainer fields, missing exported rows total 164, including Jeju and
27 other rows; do not infer zero wins or poor training from those missing cells.

The extractor uses current-horse panels only. It does not export the adjacent
historical result table, current outcomes, odds, arbitrary treatment scores or
unreviewed text-derived features. Later modifications at the same source URL
cannot overwrite these captured bytes or the original model inputs.

## Connection to Historical-Form Research

Joined the new PDF bundle to the separate, pinned PR98 condition-memory snapshot
using `(race_id, chul_no, canonical horse_id)`, never a fuzzy name join. All 468
PDF keys are unique and belong to the original 534-row target set.

Of 79 runner appearances without any observed preceding 90-day history, **75
have PDF features**. Of the 225 condition-fallback appearances, **173 have PDF
features**. The remaining PDF gaps are retained. These counts are not new
history records or evidence that these horses never raced: the historical
archive remains partial.

The useful future hypothesis is complementary information: observed training
activity may help when distance/class history is sparse. This does not establish
predictive benefit. Compare a narrowly fixed training-feature addition only
after source/label/recipe admission, on a later separately registered full
future population. Do not repeatedly select features on the already examined
27 training races or evaluate an October-trained model on the same October block.

## Bounded Execution and Artifacts

Orchestration was committed before collection as `d95b004`, with lint-only
cleanup `a490604`. It reused existing collectors and raw replay unchanged.
The acquisition plan was saved before requests. The sole run used **52 HTTP
requests: eight API pages and 44 PDFs**, zero retries. There were no captured
source failures or entry-row drift. A limit of 60, three-consecutive-PDF-failure
breaker and earliest-block deadline constrained the run. Duplicate canonical
execution refuses the existing directory; interrupted sources are retained.

The local archive is
`.cache/autoresearch/prospective-pdf-supplement-20261015`.

| Artifact | SHA256 |
| --- | --- |
| acquisition-plan.json | `b2b2ceff8289e9bb9a4541aeff8e744b926fe8b073b9f5fc9fe83ef1cf2ed426` |
| input-plan.json | `a38646826e35c91a7865491f1d94702fde9564370770cf08087b8d103e1899bf` |
| feature-bundle.json | `f96989ced4f2b419b55cc978c7dc7bb6455773f3a31c582f9f455555ec78fc4b` |
| report.json | `f63f94590751880623b388508289fbd94092af84b07a1bf2ee4ca2626b0dc259` |
| join-diagnostic.json | `32c72451cee5ab09ed42932c3cffb46960a192256d4aefd8383a1fabac5c981e` |
| offline-replay-check.json | `a231c0c5e372251b07d0a0b0785ec0e4c96dc453ce7a57e9ce02c9904710d317` |

The actual source run completed at 2026-10-15T11:38:02.786250Z. Each original
PDF and successful API page has its own raw bytes, timestamp and hash. Local
clock evidence does not independently certify the server's publication time.
The supplementary manifest does not amend PR95's original 24-column reservation.

To reproduce offline, load the exact input-plan hash above with `read_pin`,
call `kra_race_card_pdf_bundle.build_bundle(plan, archive_root=ROOT.resolve())`,
and compare its complete result with the pinned feature bundle. This re-parses
PDF bytes and all API pages; it makes no network request. Use
`prospective_pdf_supplement.finalize(targets, bundle)` for the complete registry
counts, where `targets` comes from the existing pinned `delta.load_targets`.
Do not rerun collection or change capture clocks to reproduce the source.

## Validation and Remaining Gate

The final local suite passed **307 tests**, including 16 new supplement cases,
original PDF parser/audit/collector/replay/bundle tests, API capture tests,
M0/API27 forward regressions, original prospective-input reservations and
condition-delta guards. The earlier 206-test run is contained in this final
suite, not additional independent tests. A second offline replay reproduced
the entire bundle and full-population summary exactly with zero requests.
Ruff lint and formatting pass after the recorded cleanup. Remote CI and merge
evidence are tracked on [PR99](https://github.com/coyaSONG/kra-analysis/pull/99).
Its first secret-scan run flagged the Python keyword `api_key=key` in commit
`d95b004`, line 167, as an env-file assignment. Inspection of that exact commit
confirmed a runtime variable, not a credential literal. Added only that exact
commit/path/rule/line fingerprint to the existing `.gitleaksignore`; no path,
rule or secret-scan job was disabled, and captured implementation bytes stay
fixed. The final-head scan must pass before merge. All three original
public M0/API27/training-input hashes are checked unchanged before and after
acquisition. No target outcome endpoint was called and no prediction was made.

First compare the actual pending race results with the original M0/API27
commitments. This supplement can inform later training only with a separate
review and subsequent future evaluation. Source acquisition advances the data
corpus, not the measured 70% exact-three success rate. The goal remains active.
Pro was logged out when checked earlier today; no new consultation is claimed.
