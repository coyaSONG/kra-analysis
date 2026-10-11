# Freeze the complete official future race universe

This living ExecPlan follows `.agent/PLANS.md`. Keep Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective current.

## Purpose / Big Picture

The research target is unchanged: one pre-race unordered three-horse prediction for every race in a complete frozen universe, with 70% exact race-level success. The previous production-training change rejects unproven historical inputs. This increment establishes the missing official race population independently of feature availability, then prepares fixed baseline predictions and trustworthy registration. Missing features, unknown outcomes, scratches, and model failures must not remove a scheduled race from the evaluation population.

The first observable deliverable is an executable collector and replay audit for the official national dated race list and all three regional lists, including physical venue 4 (Yeongcheon). It preserves original HTML, capture completion, hashes and conflicting rows. A requested future date absent from current official cards is unpublished/unknown, never an empty complete evaluation. A locally frozen candidate is not proof of independent pre-deadline registration.

## Progress

- [x] (2026-10-11 09:54Z) Classified the preceding Goal turn as progress: PRs #65 and #67 are merged; the reused worktree is clean at c632e9c8da7889c47bdacf7ac2ea6e5f2daf70a4.
- [x] (2026-10-11 09:56Z) Revalidated official regional dated cards and the undated weekday timetable; identified a Seoul race-10 time discrepancy and the regional-menu/physical-venue distinction.
- [x] (2026-10-11 09:57Z) Submitted a focused follow-up to the authorized Pro model about universe freezing and server-timestamped unique predictions. Wait for its completed answer before claiming advice.
- [x] (2026-10-11 09:58Z) Located the national dated list at ThisWeekDetailInfoList.do, which publishes all 50 rows for October 9-11 and agrees with the dated Seoul card's 17:30 race-10 time.
- [x] (2026-10-11 10:07Z) Implemented structured HTML parsing, four fixed-origin raw captures, pinned replay, and full-date reconciliation; retained the actual official originals.
- [x] (2026-10-11 10:18Z) Source, identity, entry-sheet and training-admission regressions pass: 179 tests (15 existing joblib/NumPy deprecation warnings). Added a whole-request timeout test as well as byte/window bounds.
- [x] (2026-10-11 10:08Z) Implemented local candidate freezing; actual October 11 is rejected as late and October 16 as unpublished. Neither produced a candidate.
- [x] (2026-10-11 10:22Z) Read the completed Pro response after the stop control disappeared and the UI reported completion (20m 40s processing). No generation was interrupted.
- [x] (2026-10-11 10:21Z) Source milestone PR #68 passed required Python and all functional checks, was pushed and normally merged as 472f005dfc342d3691eea0c3ae45b0bce1f7e9eb. The separate security failure exactly matches the existing 17 dependency records in three packages; it was not marked passing or bypassed.
- [ ] Implement the remaining fixed B0, server registration/commit observation, and whole-population execution path; the local freeze alone does not satisfy this milestone.
- [x] (2026-10-11 10:31Z) Recomputed the bounded October 116-race diagnostic from pinned existing predictions/labels: 51 both hit, 12 baseline-only, seven ranker-only, 46 both miss. Discovered a constant-within-race `rest` field and documented one source-backed rest-interval hypothesis. No new inference or training.
- [ ] Publish the completed consultation and diagnostic evidence with tested code through the same normal PR process.

## Surprises & Discoveries

The existing batch holdout policy requires collected results and strict data eligibility, and permits only venues 1-3. It cannot define the future national denominator. `shared/kra_race_identity.py` already distinguishes physical venues 1-4. The website's meet=3 regional page includes both Busan and Yeongcheon, so physical identity must come from the row's venue cell.

The national weekday timetable has no date binding in its race table. Its October 11 Seoul race 10 shows 17:25, while both dated national and regional lists show 17:30. The undated table is supplementary diagnostic evidence, not a replacement calendar or an authority for shifting a declared deadline. The dated national page contains a row per race and separate columns for selling venues; selling marks must not create duplicate races.

The current dated cards are October 9-11. No future full card has been verified. Past source captures may validate parser behavior but cannot become pre-race captures or future prediction evidence.

## Decision Log

- Decision: Use PostgreSQL for the next primary registration boundary, with an existing frozen membership row locked before the server deadline check, explicit commit, and a different transaction observing the committed payload before reading server time. Bind writer transaction identity and disallow same-transaction observations.
  Rationale: A timestamp generated before a uniqueness lock wait or a delayed commit is not evidence of pre-deadline visibility. A late observation means timing unproven, not necessarily actual late submission. Runtime mutation restrictions are not protection against the DB owner.
  Date/Author: 2026-10-11 / Codex, integrating completed Pro advice; implementation and deployment remain pending.
- Decision: In parallel with the future registration milestone, audit only stored October fold_a predictions and labels for the same 116 races. Pin every input and recompute exact hits instead of trusting stored booleans or aggregate summaries.
  Rationale: This can identify one next information hypothesis without waiting for unpublished cards or repeating model searches. It is development-only diagnosis, not a fresh holdout or production eligibility approval.
  Date/Author: 2026-10-11 / Codex, before diagnostic implementation.
- Decision: Reconcile the national dated list with the union of all regional dated lists before a future freeze.
  Rationale: This gives independent presentations of all four physical venues, detects missing rows, and avoids treating API empty pages as proof of no racing.
  Date/Author: 2026-10-11 / Codex.
- Decision: Retain all scheduled rows and their published notes even when a race is cancelled or features cannot be assembled.
  Rationale: Later joins must account for every frozen row; cancelled/undefined targets cannot silently improve the success rate.
  Date/Author: 2026-10-11 / Codex.
- Decision: Use the existing standard-library and httpx source-capture approach, and isolate changes from the owner's dirty checkout.
  Rationale: This needs structured table parsing and bounded original-byte capture, not another data framework or dependency update.
  Date/Author: 2026-10-11 / Codex.

## Outcomes & Retrospective

The source milestone is implemented and merged in PR #68. No actual future universe, baseline submission, new future accuracy measurement, model training, or 70% achievement is claimed. Source completeness, local content freezing, independent registration time, and prediction performance are separate requirements. The Goal remains active and the server registration milestone is unfinished.

## Context and Orientation

Work in `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf` on `codex/forward-race-universe`. The original owner checkout is unrelated and dirty. Existing `packages/scripts/autoresearch/kra_entry_sheet_snapshot.py` preserves API26 raw pages and validates full runner identity; `packages/scripts/shared/kra_entry_sheet.py` parses those rows. Existing model training now requires reviewed source evidence and currently approves no real recipes. Existing prediction database rows allow multiple records and do not define a frozen study/universe contract.

The four capture URLs are the fixed HTTPS national `https://race.kra.co.kr/thisweekrace/ThisWeekDetailInfoList.do`, regional `https://race.kra.co.kr/chulmainfo/ChulmaDetailInfoList.do?Act=02&Sub=1&meet=1` and the equivalent menu codes 2 and 3. The undated `https://race.kra.co.kr/thisweekrace/ThisWeekBaljuTime.do` was inspected as diagnostic background but is not collected by this command or used for admission. Region 3 covers physical venues 3 and 4. A source capture is original response bytes plus the actual request start/completion, fixed URL, encoding, size, and SHA-256. A replay audit reads these exact bytes, verifies pins, parses the official table and compares each race key and schedule. A universe is the explicit complete race-ID set for the predeclared date, independent of model or feature status.

## Plan of Work

Add a cohesive `shared/kra_schedule.py` parser and reconciliation module. Parse HTML with the standard-library HTMLParser rather than matching whole documents with regex. Identify tables by exact known headers/captions, reject malformed/truncated tables and unexpected body layouts, preserve dates/physical venue/number/start/count/notes, check row ordinals and unique keys, and ignore selling columns as identity sources. Dated rows must have valid calendar dates, weekday and times, supported physical venues, and contiguous race numbers per venue/date.

Add an `autoresearch/kra_schedule_snapshot.py` collector/replay command following the existing source capture patterns. Request only the fixed public origins, bound response size and whole-request duration, reject redirects/error pages, write originals without replacement, preserve failures, and verify content pins before replay. Collect all four dated pages in one bounded batch; the undated timetable is discovery background only. The audit must list source failures, date absence, rows present in only one presentation, schedule/count conflicts and source capture times. It must not emit a partial selected subset as a complete universe.

Continue with the smallest real freeze/baseline/registration workflow based on the completed Pro answer. The fixed baseline must execute on current qualified inputs without historical prediction lookups. The final receipt needs an independently observed server time and a unique study/race/arm key. A local hash or editable timestamp is insufficient. Decline late registration and conflicting retries, preserve identical retry idempotence, and keep missing predictions/results in left joins from the frozen population. Do not deploy production database changes without confirming the actual available environment and testing its migration path.

## Milestones

The source milestone provides a repeatable command that collects originals and reproduces the complete dated-card comparison. It must detect the currently unpublished future card and the actual 50-row historical source population without turning either into future performance evidence. The next milestone creates a valid future freeze only from complete mutually consistent official dated sources collected before the earliest cutoff. The registration milestone executes one fixed baseline and stores one immutable logical choice per study/race/arm with server timing. Its operational acceptance must be tested on the actual chosen persistence boundary, not only a mock clock. Normal required CI and merge publish validated increments; unfinished real-data requirements remain explicit.

## Concrete Steps

From the worktree root, use `.venv/bin/python -m pytest -q packages/scripts/autoresearch/tests/test_kra_schedule.py packages/scripts/autoresearch/tests/test_kra_race_identity.py packages/scripts/autoresearch/tests/test_kra_entry_sheet_snapshot.py packages/scripts/autoresearch/tests/test_training_evidence.py -o addopts=''`. Run Ruff lint/format and `git diff --check`. Add the focused cases to required Python CI using its existing environment. Preserve captured public originals under a task-specific ignored cache directory; publish evidence summaries and synthetic regression fixtures, with no credentials or private browser URL.

## Validation and Acceptance

Test all four physical venues, the meet=3 regional menu covering venue 4, multi-date cards, duplicate/gapped ordinals, missing rows at either source, time/count disagreement, unsupported venues, invalid dates/weekdays, empty/error/truncated tables, changed source hashes, redirects/oversized responses, past/future timing, and no files overwritten on retry. Every malformed row must cause a visible failure rather than disappear from the denominator. The complete synthetic positive path proves software behavior only. Actual current captures establish current published source structure, not a future freeze. Registration tests must cover cutoff versus receipt time, concurrent normal/fallback writers, identical/conflicting retries, post-deadline requests, and unchanged frozen population after outcome joins.

## Idempotence and Recovery

Each capture has a unique new directory. Completed originals are retained even when a later source fails. Replay is read-only and returns explicit reasons. No active model, owner dataset, existing receipt, or frozen universe is replaced. Retry failures in new capture directories; do not backdate them or patch captured originals. Source conflicts require new evidence or a predeclared source policy, not selective row removal. Failed or incomplete studies remain visible.

## Artifacts and Notes

Authoritative baseline for the source implementation is commit c632e9c8da7889c47bdacf7ac2ea6e5f2daf70a4. The public source observations above were made at October 11 evening KST. Capture `.cache/autoresearch/forward-schedule/20261011T100723.518882Z_a349dc8395f0/capture.json` has SHA-256 `08fe1bb58be2a394476158e8a52697a2ae2e77c9e1bf6084b1e11972fae3a7c7`. Full source hashes and findings are in `docs/research/2026-10-11-forward-race-universe.md`. Completed Pro advice is summarized there without publishing the private conversation URL. The follow-up branch `codex/forward-pro-advice` starts from merged source commit 472f005dfc342d3691eea0c3ae45b0bce1f7e9eb.

## Interfaces and Dependencies

Use immutable parsed race values, standard-library HTMLParser/datetime/hashlib/JSON/pathlib, existing shared identity helpers, and httpx. Keep pure parsing/reconciliation free of HTTP and filesystem writes. Keep collection and commands in the existing script I/O layer; any eventual application domain service belongs in `apps/api/services` with HTTP adapters in routers. Freeze bytes and hashes must identify exactly the source versions actually parsed.

Revision note (2026-10-11 10:00Z): Created before implementation from current official pages and repository inspection. The initial uncertainty about a dated national source was resolved by locating ThisWeekDetailInfoList.do; remaining timing and registration concerns were submitted to Pro without stopping its response.

Revision note (2026-10-11 10:18Z): Source capture/replay/local freeze is implemented and tested against both synthetic cases and retained official originals. This first increment deliberately does not claim a baseline execution, server receipt, production deployment, or performance result. The live registration milestone remains unfinished.

Revision note (2026-10-11 10:31Z): Integrated completed Pro advice after normal source milestone merge. Added a bounded stored-prediction diagnostic and 14 regression cases, with 193 combined tests passing. The real B0/server execution milestone remains next; the diagnostic is not a replacement for it or for the 70% objective.
