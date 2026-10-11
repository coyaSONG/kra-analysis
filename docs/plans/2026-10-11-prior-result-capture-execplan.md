# Capture official prior results without inventing start-status semantics

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

The rest-proxy audit in PR #70 found that 1,191 of 1,192 comparable horse-level observed entry gaps differed from the saved race-day value. A roster entry alone cannot establish actual start history. This increment preserves official API214 result pages, proves requested-day identity and pagination, and exposes finish evidence and unknown status codes without silently skipping them. Fresh captures can become inputs for later future races after the relevant coverage review; they do not retroactively prove availability in 2025.

The goal remains 70% exact unordered single-three-horse success over the complete frozen race universe. This increment supplies actual source evidence needed for a corrected feature and future results collection; it is not itself a performance claim.

## Progress

- [x] (2026-10-11 10:55Z) Revalidated PR #70 merged as edb67132fea5f292acb1172038eee3386e3c9487 and created isolated `codex/prior-race-result-capture` from current main.
- [x] (2026-10-11) Asked the user's selected ChatGPT Pro model about official status semantics, finite-window last-start contracts and the smallest operational next step; read the completed answer after 13m 56s without stopping generation.
- [x] Implemented bounded raw capture/replay and status-preserving normalization, plus explicit pinned-plan population replay.
- [x] Collected six actual venue/day groups, 50 races and 510 rows. No missing/extra race IDs; nine runner-count mismatches remain rejected rather than repaired by dropping cancellation rows.
- [x] Independently checked Pro's linked primary catalog, disposition guide and official DNF counterexample; retained API ordinal semantics as unverified.
- [x] Local regressions: 410 passed, 15 existing joblib/NumPy deprecation warnings; focused tests 130 passed. Ruff and diff checks passed; actual report replay was byte-identical.
- [ ] Push and normally merge after CI and required checks. Keep pre-existing dependency audit findings separate; never force a failing required merge.

## Surprises & Discoveries

The repository's API214 sample has a positive `rcTime` of 75.4 for rank 1: this is elapsed race time, not scheduled start time. API26 is an entry-sheet source and API214 is a mixed result source; their identical response envelopes do not give the rows the same temporal meaning. Known past-stat code filters positive odds and 90 days, which is insufficient to certify the most recent actual start.

Actual Yeongcheon API214 rows omit venue in all 63 rows. The API26 full-day original independently supplies venue and matches all 63 stable runner identities. API26 declares 9 for race 4's 10 rows and 10 for race 5's 11 rows. Reusing the pre-race roster builder would incorrectly conflate post-race identity verification with active-roster completeness. Extracted the existing raw-page verifier, leaving pre-race projection checks unchanged and adding a regression for this distinction.

## Decision Log

Decision (2026-10-11, Codex): Capture one physical venue/day per request stream, without relying on `rc_no` filtering. Validate every returned row against the requested venue/date, unique race/gate and stable horse identity. Reuse the existing strict KRA JSON pagination-envelope parser, not its API26 entry projection.

Decision (2026-10-11, Codex): Keep raw `ord` and `rcTime`. Only a valid rank 1-20 plus a finite positive elapsed time is classified as observed ranked finish; all other combinations remain unresolved until documented status mapping is independently verified. This is not a complete actual-start classifier. Neither empty API output nor totalCount proves whole-history or nationwide coverage.

## Outcomes & Retrospective

Completed the source-capture portion with real data, not an empty registry. See `docs/research/2026-10-11-prior-result-capture.md` for immutable source paths, SHA-256 pins and findings. The report has 487 ranked-finish observations and 23 unresolved rows, including 11 rows for one void race. The audit intentionally exits 2 because nine runner counts disagree. A second replay produces identical bytes.

Pro explicitly recommends implementing the actual PostgreSQL B0 registration path next, independently of history classification. This increment does not complete that larger recommendation. Actual future baseline registration and performance remain unfinished. A result capture with unknown statuses must not become exact rest days by skipping the ambiguous latest event. Next work: real PostgreSQL registration/commit observation tests and PR68-to-B0 execution, not more diagnostic expansion.

## Context and Orientation

Work in `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`. The dirty owner checkout is untouched. The known endpoint is `https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1`, used by `apps/api/services/kra_api_service.py`. Existing `shared/kra_entry_sheet.py::parse_entry_sheet_page` validates the standard KRA JSON envelope, success code, page number, page size and exact row count. `shared/kra_race_identity.py` defines physical venues 1-4. `autoresearch/kra_schedule_snapshot.py` replays four pinned dated schedule sources and supplies complete dated race IDs for a comparison, distinct from a future freeze.

## Plan of Work

Add a pure `shared/kra_result_history.py` normalizer and an I/O command `autoresearch/kra_result_snapshot.py`. Preserve all complete response bytes before parsing, actual request/page completion timestamps, safe request parameters, hashes and byte counts. Reject redirects, oversized/slow responses, changing totals, repeated rows, identity conflicts and malformed pages. Never serialize service keys or HTTP exception strings. Replay must re-read pinned local original bytes, reject path traversal/symlinks, validate time order and reconstruct the projection rather than trust a saved summary. No production DB or model changes.

Add synthetic tests for complete multi-page responses, failure preservation, timing, credentials, duplicates, empty unknown outputs and replay tampering. Capture the actual October 9-11 venue/day groups identified by the retained dated official schedule, then compare expected and observed race IDs and counts without dropping cancelled, unresolved or missing races. Record this as a historical source/coverage audit, not a frozen future test. Integrate completed Pro advice before deriving any last-start semantics.

## Milestones

First prove a command preserves and replays a complete API day. Next collect actual source originals and report which declared races are represented, which status values are unknown, and which identities join. Then use verified official code semantics or keep blockers explicit; the final deliverable must contain real data evidence, not only synthetic tests or an empty registry. Publish through the existing normal PR workflow. A later versioned rest-feature replacement needs actual-start and coverage proof and will not silently change existing model inputs.

## Concrete Steps

From the isolated root run `.venv/bin/python -m pytest -q packages/scripts/autoresearch/tests/test_kra_result_snapshot.py -o addopts=''`, Ruff lint/format on the new files and `git diff --check`. Run `PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.kra_result_snapshot capture --meet <1..4> --race-date <YYYYMMDD> --api-key-file /Users/coyasong/.codex/secrets/kra_api_key --output-dir .cache/autoresearch/prior-results`. The key is read only by the authenticated request path; never print it or put it in a command argument. Replay with `audit --capture <capture.json>` and require the reconstructed row counts and pins to match.

## Validation and Acceptance

Successful software behavior means complete synthetic pages survive round-trip and malformed or tampered evidence is visibly rejected. Actual source acceptance requires all retained originals and matching requested identities; unknown codes stay unknown. Real schedule comparison must retain missing/extra races and unequal counts. Tests cannot certify official semantics, source reporting completeness, independent timestamps or model performance.

## Idempotence and Recovery

Each capture creates a fresh directory. Never replace originals or previous manifests, including failed captures. HTTP or validation failure retains safe previously received bytes and a static error code. Retry into a new directory. Replay does not access the network. Do not make operational DB changes or expose credentials in files, logs or PRs.

## Artifacts and Notes

Input dated schedule bundle is `.cache/autoresearch/forward-schedule/20261011T100723.518882Z_a349dc8395f0/capture.json`, previously pinned at SHA-256 08fe1bb58be2a394476158e8a52697a2ae2e77c9e1bf6084b1e11972fae3a7c7. It is a post-race parser/coverage source, never a future freeze. Completed Pro findings and actual result capture hashes will be recorded here or in an accompanying research note.

## Interfaces and Dependencies

Use standard-library JSON, pathlib, datetime, hashlib, asyncio and existing httpx. `normalize_result_rows(rows, *, meet, race_date)` returns a stable sorted projection and uncertainty flags. `collect_result_snapshot` accepts a provided httpx client/clock for tests, but the CLI exposes no clock override. `replay_result_snapshot(capture_path)` hashes and parses the same retained bytes. Keep domain normalization independent of I/O.

Revision note (2026-10-11): Created before implementation after confirming the source gap and submitting the method/source questions to Pro. No start-status meaning has been invented from undocumented numeric codes.

Revision note (2026-10-11 11:22Z): Recorded completed Pro advice, actual missing-venue discovery and bounded API26 identity binding, preserved count mismatches, and 410 passing local regressions. CI now explicitly runs source tests and enables the existing PDF extra for replay regressions; no dependency versions or model artifacts changed.

Revision note (2026-10-11): First PR #71 scan flagged the Python keyword expression reading the caller's key file, not a credential. Reused the repository's exact commit/file/rule/line fingerprint policy for that one historical false positive and changed the CLI to the existing credential-dictionary calling pattern. No scanner rules or broad path exclusions were changed. Re-run all CI before merge. Local Docker CLI exists but its daemon is unavailable; the next PostgreSQL increment can use the existing disposable CI PostgreSQL service and must not claim local DB tests ran.
