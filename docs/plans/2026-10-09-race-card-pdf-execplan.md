# Capture and validate KRA race-card PDF snapshots

This ExecPlan is a living document maintained under `.agent/PLANS.md`. Its Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective sections must be updated as work proceeds.

## Purpose / Big Picture

The research objective is a 70% race-level exact match of one unordered three-horse prediction using information available before the race. Existing public-API snapshots often lack horse-level training and recent treatment information. Official KRA race-card PDFs contain those fields, including for horses that have never raced. This change will capture the original bytes and their actual acquisition time, extract narrowly selected current-horse fields, and check identity and timing before allowing a research feature overlay. It will not change or promote a prediction model.

The observable result is a runnable collector that produces a raw PDF, a SHA-256 content hash, a JSON manifest, parsed horse rows, and an explicit eligibility audit. SHA-256 is a checksum identifying the exact downloaded bytes. Historical downloads must remain diagnostic-only even when the server's Last-Modified header predates the race. Only a locally captured pre-cutoff snapshot with a verified race and horse join can be eligible.

## Progress

- [x] (2026-10-09 14:54Z) Confirm repository write access and KRA PDF network access; identify existing cutoff and script conventions.
- [x] (2026-10-09 15:10Z) Visually inspect representative Seoul, Busan, and Jeju PDFs and isolate the current-horse columns from prior results.
- [x] (2026-10-09 15:38Z) Implement the parser, collector, API26 pagination, original-byte manifests, and fail-closed complete joins and timing checks; validate Seoul race 1 against all 11 official entries.
- [x] (2026-10-09 15:43Z) Capture 28 scheduled Seoul/Jeju races and 294 horse rows for October 10-11; 27 races/282 rows pass. Preserve one name-prefix mismatch and the separate empty Busan API response as unresolved evidence.
- [x] (2026-10-09 15:47Z) Run 107 focused tests, Ruff, and the workspace lock check; add dedicated CI coverage and persistent Pro/push/merge operating instructions.
- [x] (2026-10-09 15:54Z) Commit and push the isolated source increment as `e250b20`; copy only that increment onto clean main as `ef648bd`.
- [x] (2026-10-09 16:05Z) Validate clean-main replay of all 28 raw PDFs, 110 focused tests, 35 API auth tests (two pre-existing skips), RSA/JWT crypto smoke, and the MLflow tracking wrapper. The PDF capture dependency closure has no known pip-audit findings after targeted updates.
- [x] (2026-10-09 16:24Z) Push the clean-main integration branch and normally merge PR #55 into main as `ae9207f`. Python, PDF, scripts, Docker, and the Gitleaks step pass. The pre-existing dependency audit remains failed and is explicitly documented; no admin override or branch-protection change is used.

## Surprises & Discoveries

The active Goal is still paused after filesystem permissions were restored. Manual work in this turn is authorized and possible, but no exposed Goal tool can resume its automatic continuation. This implementation must not claim Goal reactivation.

The official files require meeting-specific prefixes: `s_run_hr` for Seoul, `j_run_hr` for Jeju, and `b_run_hr` for Busan. A real Seoul request returns HTTP 200, application/pdf, and a Last-Modified header. Last-Modified is server metadata, not evidence of when this researcher possessed those bytes.

The repository contains many pre-existing tracked modifications and untracked research scripts. This increment will stage only its explicit new files and clean dependency manifests. No existing dirty file will be reverted or indiscriminately staged.

API26 ignores the supplied `rc_no` on the observed Seoul response: race 1 returns the whole day, with 108 entries across two pages. Start time is `stTime`, such as the printed departure label followed by `10:35`, not `schStTime`. The API mixes numeric and string horse IDs. Preserve the supplied number as a string without inventing leading zeroes, while retaining zeroes in string IDs.

Whole-page word extraction merges two-digit runner numbers with names. The first October 10 race initially yielded nine rows despite eleven official entries. Restricting number extraction to the runner-number column recovered runners 10 and 11; a generated PDF regression test covers all three layouts. Some rider lists overflow the current-panel boundary. Retain the complete training count/minutes prefix with a truncation flag, leaving riders and unprinted suffix values null rather than extending into historical columns.

October 11 Seoul race 8 has nine API names prefixed with the regional label Yeongnam (`[\uc601\ub0a8]`) while the PDF uses Bu (`[\ubd80]`). No alias rule is inferred: complete name matching blocks the whole race. The October 11 Busan request reports zero entries, so its race universe is unknown, not proven empty.

The in-app browser is unavailable in this session. The connected Chrome opens ChatGPT without a login. A login handoff has been requested; no Pro question or reply has occurred in this increment.

The initial clean-main dependency audit still reports findings in anyio, cryptography, and urllib3. The integration branch updates them to 4.14.2, 50.0.2, and 2.8.0 and regenerates API requirements from the lock. MLflow 3.14 explicitly requires cryptography <49, so the solver also moves its three-package family to 3.17.0. Its tracking wrapper passes an isolated SQLite smoke check. An all-workspace/all-extra audit still reports 94 entries (including duplicate advisory IDs) across 13 other existing packages; this is not a clean whole-repository security bill. The latest main CI already fails its security audit while Python, scripts, and Docker jobs pass. GitHub currently requires the Python Checks status, with strict up-to-date enforcement.

## Decision Log

Decision: Implement an additive research source, keeping PDF libraries out of the API runtime and keeping live model behavior unchanged. Rationale: new data quality must be demonstrated before production integration or model promotion. Date/Author: 2026-10-09 / Codex.

Decision: Store original bytes and actual timezone-aware collection timestamps; do not accept backdated server headers as cutoff evidence. Rationale: retrospective downloads cannot establish immutable pre-race availability. Date/Author: 2026-10-09 / Codex.

Decision: Extract current horse training, gate-training, swimming, and recent listed treatment entries only; do not parse prior-race result tables in this increment. Rationale: those tables can mix columns and horse names, while this bounded scope isolates new candidate-quality information. Date/Author: 2026-10-09 / Codex.

Decision: Add an API26 capture option with complete pagination and exact response identity checks. Rationale: accepting manually guessed entry metadata would leave the core availability and full-field join unproven. Preserve successful original response pages and their actual completion time, but never save authenticated request URLs or HTTP exception strings containing the service key. Date/Author: 2026-10-09 / Codex.

Decision: Persist the owner's research operating rules in `AGENTS.md`: consult the browser Pro model when research becomes difficult, wait for completion without a short timeout or stopping generation, and commit/push/merge validated increments. Rationale: these rules must survive future goal continuations; unavailable access must be reported honestly. Date/Author: 2026-10-09 / Codex.

Decision: Integrate through a separate clean-main worktree and cherry-pick only this increment. Rationale: the current branch has 25 earlier commits not present on main; merging that whole branch would exceed this change's reviewed scope. Date/Author: 2026-10-09 / Codex.

Decision: Apply only the capture dependency security updates and the solver-required MLflow family update on the clean integration branch, keeping the owner's dirty working tree untouched. Rationale: the optional PDF path must not introduce known vulnerable dependencies; repository-wide unrelated maintenance requires its own review. Keep existing failed audit evidence visible, and do not use an admin override or alter required checks. Date/Author: 2026-10-09 / Codex.

## Outcomes & Retrospective

Source ingestion is implemented, demonstrated with actual pre-race captures, pushed, and merged through [PR #55](https://github.com/coyaSONG/kra-analysis/pull/55). All 28 Seoul/Jeju PDFs parse, training counts/minutes are present for 294/294 horses, and complete identity/timing eligibility passes for 27/28 races. The unresolved name-prefix race contributes zero usable feature rows and remains in the recorded universe. These are source coverage figures, not prediction accuracy. No new exact-match result or model promotion is claimed. The spent December 2025 holdout must not be reused for model selection. A new, frozen forward holdout and a preregistered ablation remain necessary. This source-ingestion ExecPlan is complete; the 70% research Goal is not complete and its automatic continuation remains paused.

## Context and Orientation

The monorepo uses pnpm for applications and uv for Python. `packages/scripts/autoresearch/` contains research command-line tools; `packages/scripts/shared/` contains reusable parsing and validation logic. Python imports from that scripts root are established using a short path setup for direct execution. Tests are under `packages/scripts/autoresearch/tests/`.

The existing operational prediction deadline is 30 minutes before the scheduled race start. `packages/scripts/shared/operational_cutoff.py` implements that rule. A join means matching two descriptions of the same entity. For this source, an exact horse join requires meeting, race date, race number, runner number (`chulNo`), and normalized horse name (`hrName`). PDF horse names alone are not a unique key. The public entries supply the persistent horse number (`hrNo`); the PDF must never fabricate that number.

Official URLs are `https://race.kra.co.kr/down/pdf/{meeting}/chulma/{prefix}_run_hr_{YYMMDD}_{NN}.pdf`, with meeting/prefix pairs seoul/s, jeju/j, and busan/b, and race number NN zero-padded. Numeric API meeting codes are 1, 2, and 3 respectively. Representative diagnostic files are Seoul and Jeju 20260627 race 1 and Busan 20260626 race 1. Their race dates are in the past, so newly downloaded copies cannot pass a forward cutoff.

## Plan of Work

First inspect the actual PDFs, including their layout, and record which coordinate ranges belong to each current horse rather than the historical results. Add a PDF optional dependency to `packages/scripts/pyproject.toml` and refresh the workspace lockfile. Use pdfplumber's character and bounding-box APIs instead of flattening the entire page into one unstructured text string.

Add a parser in `packages/scripts/shared/kra_race_card_pdf.py`. It will validate document identity against the requested meeting/date/race, identify current-horse sections, extract bounded fields, preserve field evidence and page coordinates, and report missing or ambiguous data rather than substituting zero. Add `packages/scripts/autoresearch/kra_race_card_pdf_snapshot.py` as the HTTP and filesystem entry point. It will validate the response, preserve original bytes and headers, write collection metadata, call the parser, and audit optional entry joins and the supplied scheduled start. Persist snapshots without overwriting earlier observations.

Add independent tests for URL construction, fake HTML responses, changed content, duplicate/mismatched horse joins, missing timestamps, post-cutoff historical captures, date mismatches, missing training fields, and historical table exclusion. Include a real PDF parsing round trip in tests without committing downloaded official PDFs. Update this plan with actual commands and outputs before committing only the new module, collector, tests, plan, and dependency files.

API normalization belongs in `packages/scripts/shared/kra_entry_sheet.py`, and HTTP/page preservation in `packages/scripts/autoresearch/kra_entry_sheet_snapshot.py`. `packages/scripts/shared/kra_race_card_pdf_audit.py` emits rows only after both sources pass the deadline and every entry joins one-to-one. The dedicated `.github/workflows/race-card-pdf.yml` installs the optional research extra and runs the focused tests, including real PDF round trips, without an API credential or a live KRA request. The source contract and observed coverage are recorded in `docs/research/2026-10-10-race-card-pdf-source.md`.

## Concrete Steps

All commands run from `/Users/coyasong/Developer/coyasong/kra-analysis` unless explicitly stated otherwise. Install the research extra with `uv sync --package kra-scripts --extra race-card-pdf --group dev --inexact`; the last option preserves separately installed model-research dependencies. Run the focused tests with `.venv/bin/python -m pytest -q packages/scripts/autoresearch/tests/test_kra_entry_sheet_snapshot.py packages/scripts/autoresearch/tests/test_kra_race_card_pdf.py packages/scripts/autoresearch/tests/test_kra_race_card_pdf_audit.py packages/scripts/autoresearch/tests/test_kra_race_card_pdf_snapshot.py`. The current result is 110 passed, with no skipped PDF round trips when the extra is installed. The clean integration worktree is `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf` on `codex/race-card-pdf-snapshots`; the dependency audit and broad compatibility checks refer to that newer environment, not the original research branch's older lockfile.

The collector CLI accepts `--meet`, `--race-date`, `--race-no`, `--output-dir`, optional `--entries` JSON or mutually exclusive `--fetch-entries`, and optional `--scheduled-start-time` in HHMM format. An entries file contains `meet`, `race_date`, `race_no`, timezone-aware `collected_at`, `scheduled_start_time`, and an `entries` list with `chulNo`, `hrName`, and optional `hrNo`. Both capture times must pass the deadline, and PDF and API start times must agree. Automatic API capture requires `KRA_API_KEY`, an explicit `--api-key-file`, or the owner's existing local secret file at `~/.codex/secrets/kra_api_key`. Only the credential value is read; it is never persisted.

The real successful smoke command was:

    .venv/bin/python packages/scripts/autoresearch/kra_race_card_pdf_snapshot.py --meet 1 --race-date 20261010 --race-no 1 --fetch-entries --require-eligible

It produced `horse_count: 11`, `parser_status: parsed`, `eligible_for_prerace_features: true`, and no audit reasons. `--require-eligible` returns exit 2 for a noneligible attempt; ordinary diagnostic mode can return zero for a parsed but ineligible capture. Fetch/parse failures return exit 1. Downloading a historical file must remain ineligible even when its Last-Modified predates the race.

## Validation and Acceptance

Tests must demonstrate that a before-cutoff capture with verified identity and complete one-to-one entry joins can pass, whereas a late capture, missing schedule, stale/mismatched document, missing horse name, duplicate runner number, unsupported layout, or non-PDF response cannot pass. Missing numeric features must remain null; an explicitly printed zero may remain zero. No current-race outcome may be generated or consumed. Real-source checks must report extracted runner counts and field coverage separately from strict training eligibility.

Use the PDF renderer and inspect the first page of each supported layout to verify row boundaries and exclusion of result tables. Run Ruff on the explicit touched Python files, check `git diff --check`, inspect the staged diff, and push only after focused tests pass. Because this change adds research ingestion only, starting an API or frontend server is not needed.

## Idempotence and Recovery

Each acquisition creates an independent timestamped snapshot. The raw content filename includes a checksum so identical bytes can be recognized, and manifests retain individual collection times. A failed request or parse records a failure and cannot replace a successful snapshot or silently become training data. Retry by rerunning the same CLI. Raw downloads and generated artifacts belong under `.cache/autoresearch/` and must not be committed.

## Artifacts and Notes

Initial network evidence:

    HTTP/1.1 200 OK
    Content-Type: application/pdf
    Content-Length: 1488207
    Last-Modified: Wed, 24 Jun 2026 07:00:59 GMT

The existing offline leader's 83/147 = 56.46% is not a validated forward result and is not changed by source ingestion. Neither top-k containment nor retrospective parsing coverage satisfies the 70% objective.

The local cohort manifest is `.cache/autoresearch/race_card_pdf_snapshots/cohort_20261010_11_capture.json`, SHA-256 `c0e7ff433484652753e2207b3005dd783186280b204519f63cdf1c844962576c`. PDF captures span 2026-10-09 15:42:01Z through 15:42:41Z, equivalent to October 10 00:42 KST. The captured subsets contain October 10 Seoul 10 races/108 horses, October 10 Jeju 7/65, and October 11 Seoul 11/121. Do not count the unresolved Busan universe as zero races when assessing nationwide coverage.

Merge evidence: PR #55 is MERGED at 2026-10-09 16:24:48Z, commit `ae9207fd02e8723353899c99f0bd368e6b796c61`. The [final PR CI run](https://github.com/coyaSONG/kra-analysis/actions/runs/37958404047) passes Python, scripts, Docker, and its Gitleaks step; its existing dependency audit fails. The [dedicated PDF run](https://github.com/coyaSONG/kra-analysis/actions/runs/37958404095) passes. GitHub required Python Checks at merge time. No claim of whole-repository security clearance is made.

## Interfaces and Dependencies

The research extra will contain pdfplumber. HTTP requests use existing httpx. Persistent JSON uses the standard json parser; dates use timezone-aware datetime values. The parser must expose a public `parse_race_card_pdf` function accepting bytes and explicit requested race identity. The collector must expose an injectable HTTP collection function so no unit test needs KRA network access. The join/timing audit must be a deterministic public function and must not inspect result labels.

`build_entry_snapshot(rows, *, meet, race_date, race_no, collected_at)` returns the canonical entry envelope. `collect_entry_sheet_snapshot` captures every response page and returns a manifest plus that envelope. `audit_race_card_snapshot(parsed, *, collected_at, scheduled_start_time, entries)` returns reasons and no feature rows on failure. `collect_race_card_pdf` preserves the raw bytes before parsing and returns its manifest. Existing `shared.operational_cutoff` supplies the deadline and timezone semantics. The optional dependency resolves to pdfplumber 0.11.10, pdfminer.six 20260107, pypdfium2 5.14.0, and Pillow 12.3.0; pdfplumber requires Pillow >=12.2.0, so the Pillow update is necessary.

Plan revision: 2026-10-09, initial self-contained source-ingestion plan after permission restoration.

Plan revision: 2026-10-09, record completed implementation, API pagination and numeric-ID discoveries, two-digit runner recovery, actual cohort evidence, strict unresolved joins, Pro login handoff, and isolated integration requirements.

Plan revision: 2026-10-09 16:05Z, record source push, clean-main replay and dependency/compatibility checks, CLI failure precedence, and the distinction between a clean capture dependency closure and pre-existing whole-repository audit failures.

Plan revision: 2026-10-09 16:24Z, close the ingestion plan with verified normal merge and CI evidence, keeping source/model readiness and the paused research Goal distinct. The first PR run's three Python-keyword/test-fixture Gitleaks false positives were handled on the integration branch through exact immutable fingerprints only.
