# Enable Yeongcheon API entry identities without weakening PDF provenance

This ExecPlan is a living document maintained under `.agent/PLANS.md`. Keep Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective current.

## Purpose / Big Picture

The research target remains 70% exact race-level success for one unordered three-horse prediction over the complete frozen race universe, using only pre-race information. Official October 11 entries and the national start-time table list 11 Seoul races and six Yeongcheon races. The retained research capture inventory contains the Seoul races but none of the six Yeongcheon races. The public API documents Yeongcheon as meeting code 4, but both entry capture and the HTTP request models currently reject that code.

This increment makes code 4 usable for API entry capture and collection requests. It does not claim a complete national universe, collect retrospective observations as pre-race evidence, approve an existing model, or improve an accuracy score. PDF parsing remains restricted to the three independently verified source profiles. A source profile is the checked PDF directory, filename prefix, and physical venue printed in the document; an API meeting code alone does not verify a PDF profile.

## Progress

- [x] (2026-10-11 08:19Z) Revalidated the active Goal, preserved the owner's dirty working tree, fetched origin, and created `codex/yeongcheon-entry-identity` from origin/main in the clean existing worktree.
- [x] (2026-10-11 08:22Z) Rechecked official API26 metadata: code 4 identifies Yeongcheon. Confirmed that entry normalization, entry collection, and three API request schemas currently reject it.
- [x] (2026-10-11 08:25Z) Added regressions and reproduced eight failing venue-4 entry cases before implementation.
- [x] (2026-10-11 08:26Z) Implemented common physical identity validation, API entry and request support, explicit PDF profile rejection, and dependency fingerprints.
- [x] (2026-10-11 08:28Z) Passed 217 source tests and 82 API/collection tests, including HTTP identity propagation; Ruff lint and formatting checks pass.
- [x] (2026-10-11 08:29Z) Captured a real official venue-4 API response with 63 rows strictly for post-cutoff schema validation, never training or performance evidence.
- [x] (2026-10-11 08:29Z) Replayed unchanged original bytes under a new plan: 27 eligible sources/282 feature rows and the original blockers remain.
- [x] (2026-10-11 08:30Z) Recorded the qualified source, runtime, and historical timing findings in the research note.
- [x] (2026-10-11 08:35Z) Audited all six race projections of the same live response: races 4 and 5 remain blocked by declared-count mismatches. Recorded the later race-6 schedule without backdating any cutoff.
- [x] (2026-10-11 08:36Z) Passed both observed-count capture regressions and reran the source suite: 219 passed; lint and formatting checks remain green.
- [ ] Commit, push, and normally merge after required remote checks pass.

## Surprises & Discoveries

The website's Yeongnam menu uses meet=3 while its rows can describe physical Yeongcheon races. The API explicitly assigns physical Yeongcheon meet=4. Do not copy a website menu selector into an API race key, relabel Busan entries as Yeongcheon, or infer that an empty Busan response proves an empty national race card.

The Yeongnam PDF board advertises an October 11 attachment with a legacy b_run_hr filename, but its actual PDF venue identity has not been inspected. No new URL directory, filename prefix, or footer alias is authorized by this increment.

The actual API26 venue-4 response returned 63 rows despite requesting race 1, consistent with earlier observed ignored race filters. The capture completion time is after the card's cutoff, so it establishes response shape only. The first real replay supplied the narrower .cache archive root even though manifest paths are repository-relative; all races were safely blocked. Using the documented repository-root archive base restored 27 sources/282 rows with no source or path-validation relaxation.

The same raw response contains ten race-4 rows with declared dusu=9 and eleven race-5 rows with declared dusu=10. Both strict projections raise incomplete_entry_field; races 1, 2, 3, and 6 pass the field check only. Runner and horse IDs are unique in each race. Race 6 reports 16:35 rather than the earlier web observation's 16:30. The mismatch cause and historical effective schedule remain unproven. Keep raw evidence and failed rows, do not infer scratches or rewrite a historical cutoff from a later observation.

Read-only probes on the owner's existing artifacts showed that the 28-feature saved LogReg model can perform synthetic venue-4 inference without reading prediction caches. However, 12 features require captured or stored-as-of source evidence. Its named historical training snapshot has 1,520 selected races and 16,146 horse rows, with no per-race snapshot metadata. The 1,758-race dataset manifest is a legacy compatibility manifest: it passes the compatibility branch but fails the strict timestamp audit. This is missing evidence, not proof of leakage. No model is promoted.

## Decision Log

- Decision: Separate physical API race identity from supported PDF profiles.
  Rationale: Venue 4 is officially documented, while its PDF layout and physical identity remain unverified. API acceptance must not implicitly authorize a Busan PDF.
  Date/Author: 2026-10-11 / Codex.
- Decision: Preserve existing API request coercion and all pagination, complete-field, horse-ID, name, and timing checks.
  Rationale: This is a venue-support increment, not a redesign of request types or evidence eligibility.
  Date/Author: 2026-10-11 / Codex.
- Decision: Include the new validation dependency in the PDF bundle implementation fingerprint.
  Rationale: A fingerprint is a set of source-file checksums used to reject a plan when its verification code changes. Leaving out an imported validator would let verification behavior change without invalidating a pinned plan.
  Date/Author: 2026-10-11 / Codex.
- Decision: Keep the two live venue-4 field mismatches blocked and add explicit capture regressions.
  Rationale: Accepting the physical venue does not prove a current complete field. A post-cutoff discrepancy cannot justify removing a runner or weakening the declared-count gate.
  Date/Author: 2026-10-11 / Codex.

## Outcomes & Retrospective

The venue-4 implementation and local validation are complete: 219 source tests, 82 API/collection tests, lint, formatting, a credential-safe real post-cutoff API shape check, and unchanged original archive replay. Commit, push, and required remote checks remain. The final research Goal is active, not complete. A prior browser consultation with the owner's Pro model completed after 16 minutes 44 seconds; it prioritized freezing the full universe, reproducing a minimal baseline, registering unique timestamped predictions, auditing point-in-time sources, and only then performing a fixed-budget feature comparison. Login is no longer the recorded blocker. Do not publish the private conversation URL or claim a new consultation here.

## Context and Orientation

`packages/scripts/shared/kra_entry_sheet.py` normalizes complete API26 pages into one race's ordered entry identities. At the start of this increment it imported PDF-only `validate_identity` from `shared/kra_race_card_pdf.py` and restricted raw meeting numbers to 1-3. `packages/scripts/autoresearch/kra_entry_sheet_snapshot.py` called the same PDF validator before creating an immutable capture directory or requesting the API. They now use the independent physical identity validator; raw bytes, page checksums, and capture completion timestamps remain unchanged in meaning.

`packages/scripts/shared/kra_race_card_pdf.py` owns the verified Seoul, Jeju, and Busan PDF profiles. `packages/scripts/autoresearch/kra_race_card_pdf_bundle.py` pins its full implementation dependency list. API request bounds are in `apps/api/models/race_dto.py` and `apps/api/models/collection_dto.py`. The dedicated offline source tests and their CI job are in `packages/scripts/autoresearch/tests/` and `.github/workflows/race-card-pdf.yml`.

## Plan of Work

First add `shared/kra_race_identity.py` with explicit physical venue IDs and the existing strict calendar-date and race-number validation. Move the entry meeting-name map there and add the unambiguous Yeongcheon name. Keep the ambiguous Yeongnam grouping unsupported as a physical alias. The common validator accepts only integer meeting IDs 1-4, a valid eight-character 2000-2099 date, and integer race numbers 1-20.

Switch entry normalization and capture to this validator and raise their numeric meeting bound to 4. Keep the PDF-specific validator as an explicit profile gate followed by the common date/race-number checks. Its supported directories, names, footer labels, and parser version do not change. Add the common validator source file to bundle fingerprints.

Update the three collection request schemas to allow 4 and describe Yeongcheon, while still rejecting numbers outside 1-4. Add the new validator and tests to the existing dedicated CI paths and commands. Record official source URLs and the qualified findings in a short research note without storing keys, private browser URLs, or raw personal/account data.

## Concrete Steps

Work in `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`; the original checkout has unrelated owner changes and must not be reset, staged, or committed. The environment is read-only by default but scoped sandbox escalation is now reviewed. Use apply_patch for manual edits and approved commands for test output and Git writes.

From the worktree root, run the focused source suite with the existing Python environment:

    .venv/bin/python -m pytest -q packages/scripts/autoresearch/tests/test_kra_race_identity.py packages/scripts/autoresearch/tests/test_kra_entry_sheet_snapshot.py packages/scripts/autoresearch/tests/test_kra_race_card_pdf*.py

From `apps/api`, run the new model validation tests and existing collection tests with the project's Python dependencies and pytest configuration. Record the exact runnable command and results after inspecting the available environment. Run Ruff checks and formatting checks on changed Python modules. Check `git diff --check` and inspect the staged diff before the Conventional Commit, push, and GitHub PR. Never suppress checks or use an administrator/force merge to bypass a failure.

The actual focused API command (working directory apps/api) is:

    ../../.venv/bin/python -m pytest -q -o addopts='' -W ignore tests/unit/test_collection_venue_identity.py tests/unit/test_collection_result_router.py tests/unit/test_collection_router_errors.py tests/unit/test_collection_router_more_errors.py tests/unit/test_kra_collection_module.py tests/unit/test_collection_service.py tests/unit/test_collection_service_coverage.py tests/unit/test_collection_service_edge_cases.py tests/unit/test_collection_service_helpers.py tests/unit/test_collection_service_more.py tests/unit/test_collection_service_stats.py tests/unit/test_collection_partial_failure.py tests/unit/test_result_collection_service.py tests/unit/test_collection_status_diagnostics.py

It reports 82 passed. The local override avoids generating whole-app coverage reports for a focused invocation; the required full Python CI check is unchanged. The source suite reports 219 passed after the two observed-count regressions. Use Ruff --no-cache for read-only check commands; formatter writes require the reviewed write path.

## Validation and Acceptance

Synthetic complete API26 rows containing 4, the string 4, or the Yeongcheon venue name produce race identities ending in `_4_<race_no>`. A mocked capture must send meet=4, preserve original response bytes and hashes, retain complete horse entries, and never persist credentials. A Busan row presented as a Yeongcheon row still fails; an empty response still fails to prove a requested race exists. Existing 1-3 observations remain unchanged.

The generic race validator rejects booleans, floats, unsupported venues, invalid calendar dates, and invalid race numbers. PDF URL construction and parsing must continue rejecting code 4 before deriving or fetching any guessed PDF URL. Its three old canonical URL patterns remain exact. A plan whose recorded validator checksum differs from the current fingerprint must fail with plan_implementation_changed.

All three HTTP collection request models accept code 4 and reject 0 and 5. Passing these tests proves request support only, not that every upstream endpoint supports every new venue. A live API26 capture has been separately recorded strictly for post-cutoff schema validation. Its observed venue-4 count mismatches must remain validation_error results while preserving the original bytes and producing no entry snapshot.

## Idempotence and Recovery

Old captures and model files are never rewritten. Existing pinned PDF plans must reject implementation drift; create a newly reviewed plan from unchanged original bytes instead of modifying old hashes or acquisition timestamps. Re-running mocked tests writes only test artifacts. If remote checks fail, preserve the branch and diagnose the failure without changing the owner's checkout or overriding branch protection.

## Artifacts and Notes

Official API26 metadata: https://www.data.go.kr/data/15058677/openapi.do?recommendDataYn=Y (modified 2026-08-06, rechecked 2026-10-11).

Official national start-time table: https://race.kra.co.kr/thisweekrace/ThisWeekBaljuTime.do . Official Yeongnam entry table: https://race.kra.co.kr/chulmainfo/ChulmaDetailInfoList.do?Act=02&Sub=1&meet=3 . These are source references, not immutable raw observations or proof of a frozen evaluation cohort.

## Interfaces and Dependencies

Use only the standard library and existing pytest/httpx/Pydantic dependencies. The new shared module exports `MEET_NAMES` and `validate_race_identity(meet: int, race_date: str, race_no: int) -> None`. Keep `shared.kra_race_card_pdf.validate_identity` as the existing source-specific entry point. No new runtime library, database schema, model parameter, holdout score, or PDF alias is introduced.

Revision note (2026-10-11): Created before implementation after scoped write approval became available. The increment closes the known API venue coverage rejection without weakening source provenance or claiming the full 70% objective is achieved.

Revision note (2026-10-11 08:30Z): Recorded passing local validation, the strictly post-cutoff live schema observation, and unchanged original-source replay. Kept remote publication and merge incomplete until their authoritative results are available.

Revision note (2026-10-11 08:35Z): Recorded per-race source checks, the two declared-field blockers, and the schedule discrepancy. Added regression coverage without relaxing eligibility or treating the four complete source projections as an evaluation subset.
