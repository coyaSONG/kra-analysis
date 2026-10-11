# Diagnose Cross-Date History Identity Collisions

This ExecPlan is maintained under `.agent/PLANS.md`. It is a living document;
update Progress, Surprises & Discoveries, Decision Log, and Outcomes &
Retrospective as evidence changes.

## Purpose / Big Picture

The 70% Goal requires one pre-race unordered three-horse prediction per race
over the complete frozen future national universe. The current history seed
has 671 identity-bound observed races, but three requests have 172 rows without
physical venue. Those gaps invalidate the existing complete-response 90-day
features. Before treating the rows as racing, test data, or absent history,
compare their entire gate/horse membership and all source fields against the
verified-identity observations. A runnable read-only audit will reproduce the
evidence without inventing an event identity or changing model inputs.

## Progress

- [x] (2026-10-11) Revalidated clean isolated checkout and PR78 ordinary merge.
- [x] (2026-10-11) Inspected original gap rows and official result-list UI;
  discovered all 16 unbound groups match an earlier Busan full roster.
- [x] (2026-10-11) Sent evidence and methodological questions to the authorized
  ChatGPT Pro conversation; response is still generating, not yet consulted.
- [x] (2026-10-11) Extract the existing raw-page replay checks without weakening identity
  admission, and implement a frozen-seed collision audit.
- [x] (2026-10-11) Test tampering, identity ambiguity, field differences and
  immutability; 451 focused regressions passed. First full actual audit retained
  368 units and found 100 identity-bound collision groups as well as 16 unbound.
- [x] (2026-10-11) Freeze the final audit bytes and publish hashes/counts;
  deterministic replay confirmed and final 451 tests passed.
- [ ] Read completed Pro response without interruption and incorporate only
  advice consistent with the original Goal and verified evidence.
- [ ] Commit, push, pass required checks, and merge normally.

## Surprises & Discoveries

The unknown August 24 groups 1-6 match August 16 Busan groups 1-6; August 25
groups 1-8 match August 14 Busan groups 1-8; August 31 groups 1-2 match August 23
Busan groups 5-6. Matching means exactly the same complete set of canonical
horse IDs paired with gates, not just a horse-name overlap. This is preliminary
local evidence, not proof of an alias or permission to relabel.

The full executable audit found 100 identity-bound groups (983 rows) in 65
unique full-roster pairs, not only the unbound venue-4 groups. Ten pairs share
the same August 26 date but different physical venues 1 and 3; their only raw
field differences are meet, hrName, and winOdds. All 543 rows of the later
55 groups remain unresolved under the normal-finish predicate. This broadens
the source-quality concern without proving which events are real or fake.

The official Yeongnam result-list UI lists August 7/9/14/16/21/23/28/30 and then
September 4/6/11/13, with September 13 labeled Yeongcheon. The three gap dates
are absent from the inspected pages. Absence in a website list does not certify
that no event occurred. The direct regional August 24 detail was blank and is
not a verified physical-venue lookup.

## Decision Log

- Decision: Keep the old seed, H0/H1 definitions, approvals, and unknown statuses
  unchanged. Rationale: matching rosters can flag suspected reused records but
  cannot prove actual event identity or completeness. Author/date: Codex,
  2026-10-11.
- Decision: Extract page validation from `replay_result_snapshot` into a raw
  evidence reader rather than duplicating its pagination/hash/timestamp logic.
  Rationale: unbound rows require the same byte-level proof as admitted rows.
  Normalized event admission still runs separately. Author/date: Codex,
  2026-10-11.

## Outcomes & Retrospective

Implementation and final evidence are pending. This increment does not fit a
model, upgrade historical availability, provision paid servers, or establish
70% accuracy. A collision report must change the next source-quality decision,
not serve as a replacement for actual future prediction work.

## Context and Orientation

Work in `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`, branch
`codex/history-identity-audit`. Do not touch the owner's dirty primary checkout.
`packages/scripts/autoresearch/kra_result_snapshot.py` captures and replays API214.
Its current replay validates raw bytes then normalizes identity, which rejects
rows with no venue unless a separate full-day API26 roster binds them.
`observed_history_seed.py` replays append-only receipts and retains failed,
empty, unattempted and identity-unresolved units. Its frozen seed is
`.cache/autoresearch/observed-history-20261011/seed-final.json`, SHA256
`0dbe7abe5bdfb0a0b422bb90bddbdf1a3face89e5016254807ba37be95c25c66`.
SHA256 identifies exact file bytes; it does not authenticate the publisher.

## Plan of Work

First extract `replay_result_pages(path)` with the existing manifest/page checks.
Return raw rows and provenance, explicitly without normalized race IDs or a
claim of identity verification. Keep `replay_result_snapshot` behavior identical
by calling that reader before the existing binding and normalization logic.

Next add `autoresearch/history_identity_audit.py`. Pin and recheck the supplied
frozen seed against a fresh raw replay, allowing only materialization time and
replay implementation metadata to differ. Group raw rows by returned date and
race number inside their own capture, validate canonical horse/gate membership,
and match whole rosters across groups. Report all candidates, including ambiguity
and no-match cases. Compare the union of raw fields for aligned gate/horse rows,
distinguishing absent keys, nulls, numeric types and values. Output provenance,
coverage, suspect groups, and observed-to-observed duplicate-roster candidates.
Never attach a candidate's identity to the unbound group. Preserve all failed
and empty request units in the report's inventory.

Then run the audit on the real frozen seed, independently compare its findings
with source bytes, and record concrete results and official UI observations in
`docs/research/2026-10-11-history-identity-audit.md`. Await the completed Pro
answer while this independent audit proceeds; do not send a new message into
its ongoing generation or use partial output as advice.

## Concrete Steps

From the isolated checkout use `.venv/bin/python` with
`PYTHONPATH=packages/scripts` to invoke the new module with `--root`, `--seed`,
`--seed-sha256`, and `--output`. Choose a new output filename on every run;
existing files must not be overwritten. No API credential or new request is
needed. Run focused result/history tests plus existing shared/replay tests, Ruff
lint and format checks, and `git diff --check`. Add the new regression file to
the existing explicit CI history step. Commit Conventional Commits, push a
`codex/` branch, attach its PR, and use ordinary merge only after required checks.

## Validation and Acceptance

Tests must prove the normalized path still rejects missing venue, while the raw
reader returns provenance-checked bytes without assigning physical identity.
Missing pages, changed totals, clock disorder, raw hash changes, and mismatched
frozen-seed content must fail. A full roster match must be order/leading-zero
invariant but reject subsets, changed gates, duplicate horses, and mixed dates.
Field comparisons must detect added/missing keys, null vs absent, type changes,
changed ranks, and changed dates. Multiple candidates remain multiple; no
candidate becomes an accepted replacement. Real replay must retain all 368
units and 6,816 admitted rows without modifying old seed/source bytes.

## Idempotence and Recovery

The audit is read-only except publishing its own exclusive output file. It uses
the collector's existing lock during replay. An interruption cannot change a
frozen seed or old capture. Repeat using a fresh filename. If source files have
changed, fail instead of repairing pins or quietly selecting a new receipt.
Keep failed diagnostic files; never resume collection with changed source code.

## Artifacts and Notes

PR78 merge: `a2261c3ed9274ddfabe874b9dba35dce33ad5fce`.
Pro conversation: `https://chatgpt.com/c/6aca2dc4-d2e8-83e8-acab-e85f281c27b7`.
Official result list:
`https://race.kra.co.kr/raceScore/ScoretableScoreList.do?Act=04&Sub=1&meet=3`.
The raw cache is local and uncommitted; reports publish hashes, not credentials.

## Interfaces and Dependencies

Use standard Python collections/json/pathlib plus existing replay helpers.
`replay_result_pages(path: Path) -> dict` returns rows, original manifest,
manifest SHA256 and page pins. `audit_history(root: Path, seed_path: Path,
seed_sha256: str) -> dict` emits deterministic data, apart from any separately
declared materialization metadata. No new package dependency is needed.

Revision: initial plan after actual cross-date full-roster matches, before edits.

Revision: implemented the evidence reader and audit, corrected relative-root
resolution after the real API26-bound capture exposed a CLI-only path issue,
and recorded the broader 100-group finding after 451 passing regression tests.
