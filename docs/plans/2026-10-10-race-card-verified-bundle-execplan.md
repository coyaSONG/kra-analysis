# Export verified pre-race PDF feature archives

This ExecPlan is a living document maintained under `.agent/PLANS.md`. Update Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective at each stopping point.

## Purpose / Big Picture

The owner is researching a 70% exact race-level success rate for one unordered three-horse prediction. The previous increment captured official race-card PDFs and API26 entry sheets before the scheduled start minus 30 minutes, called the T30 cutoff. It did not predict any outcomes. Researchers now need a reproducible way to consume those captures without trusting edited feature JSON, silently dropping missing races, or replacing missing numeric values with zero. This increment exports a verified feature archive and a pinned input plan. A pinned plan records the SHA-256 digest, a checksum of exact file bytes, for each input manifest and the implementation used for replay.

The archive is not a prediction holdout or proof of a complete evaluation universe. Its scope is an explicit capture inventory. No baseline or new model is promoted, no December 2025 results are reused for selection, and no accuracy is claimed. Entries that are unavailable, mismatched, late, or unverifiable remain in the archive's race inventory with a fallback-required marker, rather than becoming successful subset evaluations.

## Progress

- [x] (2026-10-09 16:44Z) Read the source contracts, collectors, cutoff audit, repository instructions, and separate integration worktree. Preserve the owner's dirty research branch.
- [x] (2026-10-09 16:44Z) Verify that Chrome is still logged out of ChatGPT; no Pro consultation has occurred. Goal status remains paused; this is manually authorized work.
- [x] (2026-10-09 16:59Z) Implement bounded, checksum-pinned replay of PDF and complete API page evidence, including verified same-date shared entry captures.
- [x] (2026-10-09 16:59Z) Implement an immutable feature archive with nine numeric columns, missing flags, source identities, plan-time checks, and every declared race retained.
- [x] (2026-10-09 16:59Z) Pass all 179 offline source tests and lint/format for 15 Python files; extend dedicated PDF CI. Lockfile and diff checks pass without dependency changes.
- [x] (2026-10-09 17:00Z) Replay all 28 actual captures without fetching outcomes: 27 eligible races/282 rows, one blocked race, one unresolved scope. Reusing the exact pinned plan gives identical semantic output, excluding only export time.
- [ ] Commit, push, and normally merge after required Python CI and dedicated PDF tests pass; record any baseline security audit failure without overriding protection.

## Surprises & Discoveries

The archived collector's `parsed` and `audit` fields are useful evidence but are not a trustworthy consumption boundary on their own: they can be modified independently of the downloaded PDF. The PDF embeds a sanitized entry projection and a path to the entry capture, while that capture contains checksums and completion times for every successful raw API page. All of those links must be replayed together.

The current best offline selector chain is not fully available as the same live inference path. A verified feature archive cannot fix that train/serve mismatch and must not imply that predictions exist. The original capture inventory includes 28 known races and an unresolved Busan meeting/date request, not a confirmed national race universe. One Seoul race has regional horse-name prefix mismatches and must remain blocked under the strict full-name join.

Actual cohort replay exposed legitimate same-date API page sharing: the source manifest can reside in race 1's capture directory while another PDF embeds a canonical projection of race 2 from those same complete raw pages. The first development export overconstrained that directory relationship and retained 28 races but authorized only 3. The corrected replay validates the original source identity/projection, page requests and timestamps, same meeting/date, and a separately rebuilt complete target field. The source bytes are unchanged. A regression test proves sharing succeeds while cross-meeting/date reuse fails.

The repository's strict asyncio test mode does not handle an unmarked async fixture used by synchronous tests. The new local capture fixtures use synchronous `asyncio.run` setup while standalone async tests retain the existing explicit marker. This changes no application behavior; the final suite passes 179 tests.

## Decision Log

Decision: Isolate changes on `codex/race-card-pdf-verified-bundle` in `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`, based on current `origin/main`. Do not edit or stage the original dirty research tree.
Rationale: The original branch contains unrelated tracked and untracked research work; the previously merged PDF modules provide a clean, independently testable boundary.
Date/Author: 2026-10-09 / Codex.

Decision: Allow same-meeting/same-date entry capture sharing only after replaying every source page and the original source projection, then rebuilding the target race and comparing it to the PDF's embedded entry envelope. Raw files remain siblings of their own source manifests.
Rationale: The actual capture batch intentionally reuses full API responses to avoid redundant requests. Race-folder equality is not proof of identity; raw row identity, declared field completeness, original acquisition timestamps, and the strict PDF join are the required evidence.
Date/Author: 2026-10-09 / Codex.

Decision: Treat this deliverable as a capture inventory, not a completed experiment registration. Replaying a locally recorded timestamp and pinning a file now are not third-party evidence of possession before the race.
Rationale: Current captures are prospective, but no historical PDF training corpus or locked baseline is available here. An API request with a race filter also cannot prove a complete unfiltered day's race universe just because the filter was ignored in observed responses.
Date/Author: 2026-10-09 / Codex.

Decision: Recompute parser output, rebuild entries from all stored API pages, and rerun the existing cutoff/complete-join audit. Compare regenerated output to archived projections, and fail closed on changed hashes, incomplete pagination, race identity mismatches, stale parser output, or missing provenance.
Rationale: An `eligible` Boolean in a JSON file is not sufficient to authorize training input. The full chain is inspectable without fetching current-race results or exposing credentials.
Date/Author: 2026-10-09 / Codex.

Decision: Export only the parser's nine declared numeric fields plus their missing indicators and the training-summary-truncated indicator. Keep raw panel text, treatment descriptions, outcomes, IDs used as features, and unrelated API fields out of the numeric feature projection.
Rationale: This is a bounded initial interface for future preregistered ablation. Seoul/Busan and Jeju training windows are not assumed identical, and missing swimming/trainer fields remain null rather than guessed zero.
Date/Author: 2026-10-09 / Codex.

## Outcomes & Retrospective

The consumption boundary is implemented and validated on 179 offline tests and all 28 original captures. The archive preserves the complete declared capture inventory, one blocked source, and one unresolved meeting/date. Only 282 verified horse feature rows are emitted. A pinned-plan rerun reproduces all semantic output. The first failed development export is retained, not overwritten. Remote CI and normal merge remain pending.

The overall 70% Goal is not complete, and automatic continuation remains paused. Pro advice is blocked on the owner's ChatGPT login. Do not claim consultation or stop a future Pro response while it is generating. A verified archive is useful preparation but does not replace baseline inference parity, a full future universe, predeclared ablation, pre-race predictions, or eventual outcome evaluation.

## Context and Orientation

`packages/scripts/shared/kra_race_card_pdf.py` defines the parser, source ID, supported meeting/date/race identities, and `NUMERIC_FIELDS`. `packages/scripts/shared/kra_race_card_pdf_audit.py` verifies that the complete API field joins by runner number and full normalized name and that both source capture completions precede T30. `packages/scripts/shared/kra_entry_sheet.py` validates API pages and reconstructs a canonical horse-ID-bearing entry snapshot. `packages/scripts/autoresearch/kra_entry_sheet_snapshot.py` and `kra_race_card_pdf_snapshot.py` write original bytes and timestamped manifests. The earlier source contract is `docs/research/2026-10-10-race-card-pdf-source.md`.

Add `packages/scripts/autoresearch/kra_race_card_pdf_replay.py` for local bounded file I/O and validation of that evidence chain. Add `packages/scripts/autoresearch/kra_race_card_pdf_bundle.py` for capture-inventory planning, feature projection, and the command-line interface. Tests belong in corresponding `packages/scripts/autoresearch/tests/test_kra_race_card_pdf_*.py` modules and reuse the existing generated PDF fixture. Extend `.github/workflows/race-card-pdf.yml` to exercise the new files without credentials or external requests.

## Plan of Work

First, implement local replay with an explicit archive root. A path recorded inside an untrusted manifest must stay inside that root, PDF bytes must be siblings of the PDF manifest, and raw API pages must be siblings of their entry manifest. Require exact byte counts and checksums, canonical official source URLs, supported source versions, consistent timezone-aware capture ordering, sequential complete API pages, and a matching reconstructed entry envelope. Reparse PDF bytes with the current code and reject any difference from the saved parsing/audit output. Return machine-readable blocker codes and no feature rows on failure.

Second, create a fixed plan from either a previously pinned plan or the explicit cohort capture inventory. For cohort input, pin manifest hashes now and preserve unknown meeting/date observations separately; do not label that pinning time as an acquisition time. Reusing a plan must enforce its implementation fingerprint. Every declared race receives a result, even when its source cannot be used. Export only verified numeric horse rows, their null flags, join identities, source-availability timestamp, and a reference to the replay evidence. Record code checksums, relevant dependency versions, raw hashes, input plan hash, and output hash. Use a timestamp-plus-UUID output directory and exclusive creation so reruns never overwrite evidence.

Finally, test synthetic good captures and altered archives, then replay the original local cohort at `/Users/coyasong/Developer/coyasong/kra-analysis/.cache/autoresearch/race_card_pdf_snapshots/cohort_20261010_11_capture.json`. Expect 28 retained races, 27 eligible sources and 282 feature rows, the known blocked race, and one unresolved Busan scope observation. These are data counts, not predictions. Record the actual result before opening a small PR and normally merging it after checks.

## Concrete Steps

Run from the clean integration worktree:

    uv sync --package kra-scripts --extra race-card-pdf --group dev --inexact
    .venv/bin/python -m pytest -q packages/scripts/autoresearch/tests/test_kra_entry_sheet_snapshot.py packages/scripts/autoresearch/tests/test_kra_race_card_pdf.py packages/scripts/autoresearch/tests/test_kra_race_card_pdf_audit.py packages/scripts/autoresearch/tests/test_kra_race_card_pdf_snapshot.py packages/scripts/autoresearch/tests/test_kra_race_card_pdf_replay.py packages/scripts/autoresearch/tests/test_kra_race_card_pdf_bundle.py
    .venv/bin/python packages/scripts/autoresearch/kra_race_card_pdf_bundle.py --cohort /Users/coyasong/Developer/coyasong/kra-analysis/.cache/autoresearch/race_card_pdf_snapshots/cohort_20261010_11_capture.json --archive-root /Users/coyasong/Developer/coyasong/kra-analysis --require-complete
    uv lock --check
    git diff --check

The capture-inventory CLI prints only aggregate counts, blocker codes, and artifact paths. With `--require-complete`, a successfully exported partial archive exits 2. Invalid planning input exits 1; a complete successful archive exits 0. Source failures are represented as blocked races, not skipped outputs. The default output is ignored `.cache/autoresearch/race_card_pdf_bundles/`.

## Validation and Acceptance

Offline tests must prove that a full good source chain emits exactly one numeric row per official runner. Editing PDF bytes, API bytes, manifest digests, source IDs, entry projections, page metadata, timestamps, parser versions, or audit flags must never emit features. Test missing provenance, canonical URL violations, path traversal and escaping symlinks, bounded reads, duplicate plan races, absent snapshots, retained blocked races, null-versus-zero indicators, excluded history/outcome fields, implementation drift, immutable outputs, and CLI exit semantics.

Actual replay must use original locally retained bytes without network calls or outcome reads. Compare its eligible/source/horse counts with the previous contract, and inspect the new input-plan and output checksums. A repeated pinned-plan replay must produce identical semantic race/feature output, excluding actual export timestamps and distinct output paths.

## Idempotence and Recovery

Replay is read-only. Export creates a unique directory and never modifies the old captures. On missing files or corruption, keep the blocked race and original evidence, record the reason, and acquire a new observation through the existing collector if still pre-cutoff. Never repair old capture timestamps or manifest hashes merely to pass a gate. An intentional parser change requires a new reviewed plan; do not silently reuse a fingerprint from a previous implementation. If remote checks fail, diagnose the step without disabling checks, force-pushing, or using an admin merge override.

## Artifacts and Notes

The original cohort checksum is `c0e7ff433484652753e2207b3005dd783186280b204519f63cdf1c844962576c`. Downloaded PDFs/API response bytes and the feature bundle remain in ignored local cache. Commit only code, tests, CI, this plan, and a concise source-backed research note. No keys, authenticated URLs, current-race outcomes, or copied KRA PDFs belong in Git.

The final export is `.cache/autoresearch/race_card_pdf_bundles/20261009T165933.854898Z_51a041eda9e6/feature_bundle.json`, SHA-256 `8061a185401bf72c4bfee2751529acb164b695eb2985dbf4d6a43e187a8ecdd6`; its input-plan SHA-256 is `0ac4a309d07901d6f4da8c4503c937fee9529fb5e05871cfdcd5252116a52be0`. The pinned replay is `20261009T170031.529322Z_69881123d72c/feature_bundle.json`, SHA-256 `bb75f109f1565c7b8239ba0cc42755eab85636353df8e912b5698fe7c0d541c6`. `diff -u` of sorted JSON with only `exported_at` removed exits 0 with no differences. `--require-complete` exits 2 for both, as expected; unknown Busan scope is not a zero-race assumption. The engineering report is `docs/research/2026-10-10-verified-pdf-feature-archive.md`.

## Interfaces and Dependencies

Define `replay_race_card_snapshot(manifest_path, *, archive_root, expected_sha256, expected_identity, expected_pdf_sha256=None, expected_entry_manifest_sha256=None) -> dict[str, Any]`. It returns `eligible_for_prerace_features`, `reasons`, `feature_rows`, identity, and checksum-backed evidence. Define `build_bundle(plan, *, archive_root) -> dict[str, Any]` and CLI `main() -> int` in the bundle module. Use existing parsers and the optional `race-card-pdf` dependency set; no new dependency or production API change is required.

Revision note (2026-10-09): Created this plan before implementation to close the raw-evidence consumption gap without conflating source coverage with the 70% model objective.

Revision note (2026-10-09 17:00Z): Recorded implementation, 179-test evidence, real/pinned replay checksums, and the discovery/correction of shared same-date entry provenance. Preserve all blockers and remaining model-evaluation gates while remote checks are pending.
