# Yeongcheon API Entry Support and Research Evidence Status

Physical Yeongcheon venue code 4 is now supported by API26 entry normalization, immutable entry capture, and the collection request schemas. PDF provenance remains limited to the independently verified Seoul, Jeju, and Busan profiles. This change removes a known venue coverage rejection; it is not a new model, a complete frozen evaluation universe, or evidence of 70% success.

## Official Venue Identity

The [official API26 metadata](https://www.data.go.kr/data/15058677/openapi.do?recommendDataYn=Y), modified August 6, 2026, assigns Yeongcheon meet=4. The [national start-time table](https://race.kra.co.kr/thisweekrace/ThisWeekBaljuTime.do) and [Yeongnam entries](https://race.kra.co.kr/chulmainfo/ChulmaDetailInfoList.do?Act=02&Sub=1&meet=3) list six Yeongcheon races alongside 11 Seoul races on October 11. The website menu's meet=3 is a regional selector, not a physical API venue identity.

The retained October 10-11 capture inventory contains 28 known races, including only the 11 Seoul races for October 11. None of the six physical venue-4 race IDs is present. The earlier empty venue-3 response must not be interpreted as proof of an empty national card. The web tables establish the observed scheduling gap; they are not immutable pre-race raw captures or a preregistered test cohort.

## Supported Behavior

`shared/kra_race_identity.py` validates physical venues 1-4 independently of source layouts. API entries accept numeric 4, the string 4, and the unambiguous Yeongcheon name. Date, page, runner-count, horse-ID, full-name, credential-redaction, and capture-clock checks remain in force. Busan entries cannot be relabelled as Yeongcheon, and an empty response cannot prove the requested race exists. The ambiguous Yeongnam grouping is not a physical venue alias.

The HTTP collection models accept code 4, and an authenticated mocked request to `/api/v2/collection/` passes it unchanged into the collection command. This proves the request boundary, not successful live behavior for every enrichment or result endpoint.

PDF URL construction and parsing still reject code 4 before guessing a path or accepting a Busan document. No PDF prefix, directory, footer alias, horse-name normalization, or parser version is broadened. The new validator is included in implementation fingerprints; old pinned plans reject implementation drift and need a newly reviewed plan, never edited acquisition timestamps or patched old checksums.

## Live API Shape Check

A direct official API26 request with physical meet=4 completed at `2026-10-11T08:29:48.229419+00:00`, after the Yeongcheon card's race times. It preserved 63 response rows and projected 11 entries for requested race 1, without printing or persisting the credential. This is exclusively a post-cutoff schema check: it is prohibited as training data or 70% evidence. It does not repair the missing original pre-race venue-4 captures.

The ignored capture is under `.cache/autoresearch/yeongcheon_identity_schema_check/20261011_4_1/entries_20261011T082947.283770Z_8956b78a1541/`. Raw pages and their hashes are retained there; public repository files contain no keys or raw API payloads. The existing collector's rc_no filter again returned rows for more than the requested race. A complete future-universe collector must still use and verify unfiltered coverage rather than assuming this behavior is permanent.

Replaying that same retained response separately for all six race identities gives the following source-level checks. These are not race predictions, pre-race observations, or a qualified evaluation subset.

| Race | Response rows | Declared dusu | Strict entry check |
| --- | --- | --- | --- |
| 1 | 11 | 11 | Complete field |
| 2 | 11 | 11 | Complete field |
| 3 | 11 | 11 | Complete field |
| 4 | 10 | 9 | Blocked: incomplete_entry_field |
| 5 | 11 | 10 | Blocked: incomplete_entry_field |
| 6 | 9 | 9 | Complete field |

All rows identify the physical venue as Yeongcheon. Each race has unique runner numbers and horse IDs. The API's race-6 start time is 16:35, whereas the earlier web observation listed 16:30; this later observation cannot establish the historical cutoff. No cause for the race-4/5 count mismatch has been established, and no scratched-runner inference, automatic row removal, count override, or source-gate relaxation is made. Future pre-cutoff captures need independently timed revision and change-notice evidence to reconcile the declared field safely.

## Validation

Before the implementation, all eight added venue-4 entry regression cases failed at the PDF-only identity guard. After implementation, formatting, and the two observed-count regressions, the focused source suite passes 219 tests, and the wider API/request/router/collection suite passes 82 tests. Changed Python files pass Ruff lint and formatting checks. Tests include booleans and unsupported venue rejection, all old canonical PDF URLs, credential-safe raw capture, rejection of inconsistent venue-4 counts without losing raw evidence, HTTP identity propagation, and rejection of a changed validator fingerprint.

Replaying the 28 original raw captures under a new implementation plan preserves 27 eligible sources and 282 feature rows, with the same Seoul race 8 name mismatch and the same unresolved old venue-3 scope. `--require-complete` correctly exits 2. A first replay used the wrong archive root and emitted zero features; it remains in its separate ignored output directory. The documented repository-root archive base restores the expected result without relaxing path safety or modifying original evidence.

## Baseline Qualification

The existing 28-feature LogReg bundle performs synthetic venue-4 inference without a prediction-cache read. Row reversal, a never-seen race ID, and tied scores preserve the prediction; changing a rating changes the scores. All 28 features pass the current static contract, but two require pre-cutoff captures and ten require stored-as-of history. These are interface checks, not observed race accuracy or verified historical availability.

The model's named historical input snapshot selects 1,520 races and 16,146 horse rows through November 15, 2025. None has per-race snapshot metadata or the inspected source timestamp fields. Its 1,758-race manifest is marked legacy_bootstrap, warns that timing coverage is absent, and passes only the legacy compatibility timing branch. The same manifest fails the strict timing branch. The bundle also does not pin its historical training dataset bytes. Missing timing evidence is not proof of leakage, but this model cannot be approved as the strict research baseline on these artifacts alone.

The inspected local artifact hashes are model `bde9fdfaee00c898ef468789e93219c039deb268a4144b98657998fa7b6b604d`, dataset `7870b169992e0b108c75384733ef15e6c790fe62e1005433d007c80b84be9131`, and manifest `52ea1357fe222d4d7c99fa016ac842fab2827bcfbc0e1cd870c99c94178ac2a7`. Matching current counts does not bind these dataset bytes to the original fitted model or supply a historical publication timestamp.

## Next Research Gates

Freeze the complete next future race universe across all physical venues, retain missing sources and failures, and verify entry revisions at the declared cutoff. Join global change notices by date, physical venue, race number, and runner number; the existing helper can misapply a different venue's notice when mixed inputs are provided. Current live caller mixing was not established, and changed_jockey_flag is not one of this saved model's 28 inputs.

Separate legacy offline diagnostics from strict training eligibility, prove source timing, freeze one reproducible baseline and fallback, and register one unique trusted-time three-horse receipt for every race before evaluation. A completed prior Pro consultation recommended this ordering, followed by a fixed-budget structured-versus-PDF comparison. No new training, model promotion, retrospective score selection, or 70% claim accompanies this increment.
