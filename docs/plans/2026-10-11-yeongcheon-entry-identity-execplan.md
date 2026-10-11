# Enable Yeongcheon API entry identities without weakening PDF provenance

This ExecPlan is a living document maintained under `.agent/PLANS.md`. Keep Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective current.

## Purpose / Big Picture

The research target remains 70% exact race-level success for one unordered three-horse prediction over the complete frozen race universe, using only pre-race information. Official October 11 entries and the national start-time table list 11 Seoul races and six Yeongcheon races. The retained research capture inventory contains the Seoul races but none of the six Yeongcheon races. The public API documents Yeongcheon as meeting code 4, but entry capture, HTTP request models, and the canonical SQL constraint rejected that code at the start of this increment.

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
- [x] (2026-10-11 08:37Z) Committed be0cf95, pushed the isolated branch, opened and attached PR #63. Remote source, script, and Docker checks passed on that revision.
- [x] (2026-10-11 08:38Z) Identified three exact Gitleaks env-file false positives: added Python keyword arguments containing the literal synthetic test-credential, not real keys. Added narrowly scoped historical fingerprints using the existing repository pattern.
- [x] (2026-10-11 08:41Z) Required Python Checks, source tests, scripts, Docker, and Gitleaks passed on 1935aa6. The remaining dependency audit has the same 17 findings in three packages as base main; it is not a passing security suite.
- [x] (2026-10-11 08:42Z) Found the active unified SQL baseline still rejects meet=4; ORM-created test databases did not reproduce this constraint. Deferred merge to close the persistence boundary.
- [x] (2026-10-11 08:45Z) Added and registered migration 008 without changing historical SQL. Passed 139 API/migration regressions and lint/format checks locally; three SQL tests are explicitly skipped without the local PostgreSQL service.
- [x] (2026-10-11 08:48Z) Actual isolated PostgreSQL CI passed all three migration cases, with no skips, in the 34-pass integration run. Required Python Checks, dedicated source tests, scripts, Docker, and Gitleaks passed on final head c68743c.
- [x] (2026-10-11 08:49Z) Recorded the unchanged non-required dependency audit failure and normally merged PR #63 at ca3c6d255a3276a7364b0f3047c687aeb8ce7b64, without an administrator bypass or forced merge.

## Surprises & Discoveries

The website's Yeongnam menu uses meet=3 while its rows can describe physical Yeongcheon races. The API explicitly assigns physical Yeongcheon meet=4. Do not copy a website menu selector into an API race key, relabel Busan entries as Yeongcheon, or infer that an empty Busan response proves an empty national race card.

The Yeongnam PDF board advertises an October 11 attachment with a legacy b_run_hr filename, but its actual PDF venue identity has not been inspected. No new URL directory, filename prefix, or footer alias is authorized by this increment.

The actual API26 venue-4 response returned 63 rows despite requesting race 1, consistent with earlier observed ignored race filters. The capture completion time is after the card's cutoff, so it establishes response shape only. The first real replay supplied the narrower .cache archive root even though manifest paths are repository-relative; all races were safely blocked. Using the documented repository-root archive base restored 27 sources/282 rows with no source or path-validation relaxation.

The same raw response contains ten race-4 rows with declared dusu=9 and eleven race-5 rows with declared dusu=10. Both strict projections raise incomplete_entry_field; races 1, 2, 3, and 6 pass the field check only. Runner and horse IDs are unique in each race. Race 6 reports 16:35 rather than the earlier web observation's 16:30. The mismatch cause and historical effective schedule remain unproven. Keep raw evidence and failed rows, do not infer scratches or rewrite a historical cutoff from a later observation.

The first PR security check matched three synthetic Python api_key keyword arguments with the case-insensitive env-file assignment rule. The log fingerprints identify be0cf95 and lines 148, 175, and 202 of the entry capture test. They are not API credentials. The repository already records exact commit/file/rule/line false positives in .gitleaksignore; no secret rule, scan step, or broad path allowance is removed. The base main revision's Gitleaks passed, while its Python dependency audit failed. Confirm the new revision's actual outcome rather than assuming the failure stage stays unchanged.

The production source of truth is the SQL migration manifest, not ORM create_all. The active 001_unified_schema.sql defines races_meet_check for codes 1-3. HTTP and SQLite tests therefore cannot prove venue-4 persistence. The new 008 migration is appended to ACTIVE_MIGRATIONS without rewriting baseline SQL. The local Docker daemon was unavailable; actual PostgreSQL CI, not local ORM tests, demonstrated the three SQL acceptance cases before merge.

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
- Decision: Annotate only the three proven historical synthetic-argument fingerprints in .gitleaksignore.
  Rationale: A new commit cannot erase a scan finding in an earlier pushed commit. Exact fingerprints preserve existing scanning for other lines and real credentials without rewriting published history or weakening the rule.
  Date/Author: 2026-10-11 / Codex.
- Decision: Extend the increment to the actual SQL persistence constraint before merging the request change.
  Rationale: Accepting a request that the active database cannot store is an incomplete integration. A checksum-preserving additive migration is required, with the existing startup guard rejecting a deployment that omits it.
  Date/Author: 2026-10-11 / Codex.

## Outcomes & Retrospective

This increment is implemented, tested, pushed, and normally merged in PR #63. Local validation is 219 source tests and 139 API/migration tests; the three SQL cases were skipped locally and then actually passed in the 34-case PostgreSQL-backed CI integration run. Required Python Checks, dedicated source tests, scripts, Docker, and Gitleaks passed on c68743c. The non-required dependency audit still reports the same 17 records in three packages as base main, with later security steps skipped; this is not a green security suite. No live Supabase migration or application deployment occurred.

The lesson is that physical venue acceptance must be checked through the actual SQL source of truth, not just request and ORM tests. The post-cutoff API source discrepancies and old archive blockers remain intact. No model was trained or promoted and no accuracy increase is claimed. The full 70% research Goal remains active, with next work on strict historical training eligibility, a complete future universe, point-in-time source revisions, and unique trusted-time predictions.

A prior browser consultation with the owner's Pro model completed after 16 minutes 44 seconds; it prioritized freezing the full universe, reproducing a minimal baseline, registering unique timestamped predictions, auditing point-in-time sources, and only then performing a fixed-budget feature comparison. Login is no longer the recorded blocker. Do not publish the private conversation URL or claim a new consultation here.

## Context and Orientation

`packages/scripts/shared/kra_entry_sheet.py` normalizes complete API26 pages into one race's ordered entry identities. At the start of this increment it imported PDF-only `validate_identity` from `shared/kra_race_card_pdf.py` and restricted raw meeting numbers to 1-3. `packages/scripts/autoresearch/kra_entry_sheet_snapshot.py` called the same PDF validator before creating an immutable capture directory or requesting the API. They now use the independent physical identity validator; raw bytes, page checksums, and capture completion timestamps remain unchanged in meaning.

`packages/scripts/shared/kra_race_card_pdf.py` owns the verified Seoul, Jeju, and Busan PDF profiles. `packages/scripts/autoresearch/kra_race_card_pdf_bundle.py` pins its full implementation dependency list. API request bounds are in `apps/api/models/race_dto.py` and `apps/api/models/collection_dto.py`. The dedicated offline source tests and their CI job are in `packages/scripts/autoresearch/tests/` and `.github/workflows/race-card-pdf.yml`.

## Plan of Work

First add `shared/kra_race_identity.py` with explicit physical venue IDs and the existing strict calendar-date and race-number validation. Move the entry meeting-name map there and add the unambiguous Yeongcheon name. Keep the ambiguous Yeongnam grouping unsupported as a physical alias. The common validator accepts only integer meeting IDs 1-4, a valid eight-character 2000-2099 date, and integer race numbers 1-20.

Switch entry normalization and capture to this validator and raise their numeric meeting bound to 4. Keep the PDF-specific validator as an explicit profile gate followed by the common date/race-number checks. Its supported directories, names, footer labels, and parser version do not change. Add the common validator source file to bundle fingerprints.

Update the three collection request schemas to allow 4 and describe Yeongcheon, while still rejecting numbers outside 1-4. Add the new validator and tests to the existing dedicated CI paths and commands. Record official source URLs and the qualified findings in a short research note without storing keys, private browser URLs, or raw personal/account data.

Add apps/api/migrations/008_add_yeongcheon_meet.sql to replace only the named races_meet_check with a validated 1-4 constraint. Append the file to apps/api/infrastructure/migration_manifest.py and update the two tests that assert the former migration head. Add startup-guard coverage for a database missing 008. Existing migration bytes, race keys, unique constraints, and stored rows stay unchanged.

Add apps/api/tests/integration/test_yeongcheon_migration.py using a dedicated KRA_MIGRATION_TEST_DSN pointing only to the loopback test_db service. Each test creates a uniquely named schema, sets its search path, executes the actual migration through the existing transaction/checksum runner, and removes only its own schema in finally. An unset DSN skips locally but fails explicitly in CI; no production settings URL is used. Pass the DSN in the existing integration and coverage CI steps. Verify the old check rejects 4, the new check accepts 1-4 and rejects 0/5, uniqueness and rows persist, reapplication is harmless, and failed validation leaves the previous constraint and migration bookkeeping unchanged.

## Milestones

The first milestone separates physical venue identity from PDF source acceptance. It is verified by the eight originally failing cases, the 219-case source suite, the real post-cutoff shape observation, and unchanged historical archive replay. None of these is an accuracy or pre-race qualification result.

The second milestone closes persistence using migration 008. The 139-case local API/migration suite checks the request and manifest guard. All three SQL cases that were skipped locally passed with the explicit isolated PostgreSQL DSN in CI; the persistence acceptance milestone is complete. Live deployment and database migration were not part of this milestone.

The final milestone published the isolated changes, waited for required checks on the exact head, verified Gitleaks and the remaining dependency audit against base main, and normally merged PR #63. The complete research Goal remains active after this venue-support milestone; missing source timing, full future-universe coverage, and trusted prediction receipts are subsequent gates.

## Concrete Steps

Work in `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`; the original checkout has unrelated owner changes and must not be reset, staged, or committed. The environment is read-only by default but scoped sandbox escalation is now reviewed. Use apply_patch for manual edits and approved commands for test output and Git writes.

From the worktree root, run the focused source suite with the existing Python environment:

    .venv/bin/python -m pytest -q packages/scripts/autoresearch/tests/test_kra_race_identity.py packages/scripts/autoresearch/tests/test_kra_entry_sheet_snapshot.py packages/scripts/autoresearch/tests/test_kra_race_card_pdf*.py

From `apps/api`, run the new model validation tests and existing collection tests with the project's Python dependencies and pytest configuration. Record the exact runnable command and results after inspecting the available environment. Run Ruff checks and formatting checks on changed Python modules. Check `git diff --check` and inspect the staged diff before the Conventional Commit, push, and GitHub PR. Never suppress checks or use an administrator/force merge to bypass a failure.

The actual focused API command (working directory apps/api) is:

    ../../.venv/bin/python -m pytest -q -o addopts='' -W ignore tests/unit/test_collection_venue_identity.py tests/unit/test_collection_result_router.py tests/unit/test_collection_router_errors.py tests/unit/test_collection_router_more_errors.py tests/unit/test_kra_collection_module.py tests/unit/test_collection_service.py tests/unit/test_collection_service_coverage.py tests/unit/test_collection_service_edge_cases.py tests/unit/test_collection_service_helpers.py tests/unit/test_collection_service_more.py tests/unit/test_collection_service_stats.py tests/unit/test_collection_partial_failure.py tests/unit/test_result_collection_service.py tests/unit/test_collection_status_diagnostics.py

It reports 82 passed. The local override avoids generating whole-app coverage reports for a focused invocation; the required full Python CI check is unchanged. The source suite reports 219 passed after the two observed-count regressions. Use Ruff --no-cache for read-only check commands; formatter writes require the reviewed write path.

The final widened API command appends tests/unit/test_database_migration_guard.py, tests/unit/test_job_service.py, tests/unit/test_coverage_low_files.py, and tests/integration/test_yeongcheon_migration.py to the same invocation. It reports 139 passed and 3 skipped locally. CI sets KRA_MIGRATION_TEST_DSN=postgresql://test:test@localhost:5432/test_db. The integration step reports 34 passed, including all three new SQL cases; the existing coverage step selects unit tests and does not establish additional PostgreSQL executions.

## Validation and Acceptance

Synthetic complete API26 rows containing 4, the string 4, or the Yeongcheon venue name produce race identities ending in `_4_<race_no>`. A mocked capture must send meet=4, preserve original response bytes and hashes, retain complete horse entries, and never persist credentials. A Busan row presented as a Yeongcheon row still fails; an empty response still fails to prove a requested race exists. Existing 1-3 observations remain unchanged.

The generic race validator rejects booleans, floats, unsupported venues, invalid calendar dates, and invalid race numbers. PDF URL construction and parsing must continue rejecting code 4 before deriving or fetching any guessed PDF URL. Its three old canonical URL patterns remain exact. A plan whose recorded validator checksum differs from the current fingerprint must fail with plan_implementation_changed.

All three HTTP collection request models accept code 4 and reject 0 and 5. Passing these tests proves request support only, not that every upstream endpoint supports every new venue. A live API26 capture has been separately recorded strictly for post-cutoff schema validation. Its observed venue-4 count mismatches must remain validation_error results while preserving the original bytes and producing no entry snapshot.

The SQL migration must pass all three isolated PostgreSQL integration tests in the CI service. A skipped local PostgreSQL test is not a pass. The existing migration runner records 008 with its checksum, and the runtime manifest guard rejects a database that has only 001-007. Apply migration 008 using scripts/apply_migrations.py before deploying this API revision. Do not apply it to the owner's live Supabase database as part of these tests.

## Idempotence and Recovery

Old captures and model files are never rewritten. Existing pinned PDF plans must reject implementation drift; create a newly reviewed plan from unchanged original bytes instead of modifying old hashes or acquisition timestamps. Re-running mocked tests writes only test artifacts. If remote checks fail, preserve the branch and diagnose the failure without changing the owner's checkout or overriding branch protection.

Migration 008 runs in the existing transaction and does not remove data. A rejected new constraint rolls the transaction back. Reapplication through the runner is a no-op when the recorded checksum matches. Coordinate the schema and application rollout: older code's strict manifest guard rejects an unexpected 008, so do not restart an old revision against the new manifest or assume it is a compatible rollback. Recover using an application version that recognizes 008 or a separately reviewed procedure; do not blindly restore a 1-3 constraint after venue-4 rows exist, delete those rows, rewrite migration history, or alter a live database without review.

## Artifacts and Notes

Official API26 metadata: https://www.data.go.kr/data/15058677/openapi.do?recommendDataYn=Y (modified 2026-08-06, rechecked 2026-10-11).

Official national start-time table: https://race.kra.co.kr/thisweekrace/ThisWeekBaljuTime.do . Official Yeongnam entry table: https://race.kra.co.kr/chulmainfo/ChulmaDetailInfoList.do?Act=02&Sub=1&meet=3 . These are source references, not immutable raw observations or proof of a frozen evaluation cohort.

Merged implementation: https://github.com/coyaSONG/kra-analysis/pull/63 at 2026-10-11T08:49:07Z, final head c68743c2156f98ff8ea10246d4b0e8d829e87153, merge ca3c6d255a3276a7364b0f3047c687aeb8ce7b64. Exact-head Python/SQL/script/Docker/security-stage evidence is in https://github.com/coyaSONG/kra-analysis/actions/runs/38125986105 and dedicated source evidence is in https://github.com/coyaSONG/kra-analysis/actions/runs/38125986094. Base-main dependency audit comparison is https://github.com/coyaSONG/kra-analysis/actions/runs/37964641112.

## Interfaces and Dependencies

Use only the standard library and existing pytest/httpx/Pydantic/asyncpg dependencies. The new shared module exports `MEET_NAMES` and `validate_race_identity(meet: int, race_date: str, race_no: int) -> None`. Keep `shared.kra_race_card_pdf.validate_identity` as the existing source-specific entry point. The sole schema change broadens the named physical venue check to include 4. No new runtime library, model parameter, holdout score, or PDF alias is introduced.

Revision note (2026-10-11): Created before implementation after scoped write approval became available. The increment closes the known API venue coverage rejection without weakening source provenance or claiming the full 70% objective is achieved.

Revision note (2026-10-11 08:30Z): Recorded passing local validation, the strictly post-cutoff live schema observation, and unchanged original-source replay. Kept remote publication and merge incomplete until their authoritative results are available.

Revision note (2026-10-11 08:35Z): Recorded per-race source checks, the two declared-field blockers, and the schedule discrepancy. Added regression coverage without relaxing eligibility or treating the four complete source projections as an evaluation subset.

Revision note (2026-10-11 08:38Z): Recorded the first pushed revision, PR #63, and the narrowly established synthetic-keyword scanner false positives. Kept final remote checks and merge pending until verified on the updated head.

Revision note (2026-10-11 08:43Z): Extended the plan before editing SQL to close the newly discovered production constraint. Defined isolated PostgreSQL acceptance, unchanged historical checksums, migration-before-deployment, and non-destructive recovery; normal merge remains pending.

Revision note (2026-10-11 08:45Z): Recorded additive migration implementation, the wider local regression result, explicitly skipped PostgreSQL tests, and rollout instructions. Preserved the requirement for actual SQL execution in CI before normal merge.

Revision note (2026-10-11 08:49Z): Closed this increment from actual exact-head CI and normal merge results. Distinguished skipped local SQL tests from real CI executions, documented the existing security failure, and clarified strict-manifest rollout compatibility without marking the 70% research Goal complete.
