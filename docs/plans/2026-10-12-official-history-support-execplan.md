# Reconcile Frozen History With Official Results

This living ExecPlan follows `.agent/PLANS.md` and must retain updated Progress,
Surprises & Discoveries, Decision Log, and Outcomes & Retrospective sections.

## Purpose / Big Picture

The owner requires 70% exact unordered three-horse success on the complete frozen
future national universe. The existing API history has 100 full-roster collision
groups, including 433 normally ranked rows. Replay integrity alone does not
establish that these rows describe actual regular races. This increment captures
dated official result pages, compares all 671 frozen groups, and produces a
separately named officially supported partial-history diagnostic for all 28
target rosters and 294 runner appearances. It does not fit or promote a model.

## Progress

- [x] (2026-10-11 18:02Z) Revalidated clean PR80 checkout, completed Pro response
  (12m27s), and positively inspected official Seoul August 15 race 1 HTML.
- [x] (2026-10-11 18:14Z) Implemented capture/replay and strict official parsing.
- [x] (2026-10-11 18:14Z) Captured all 671 groups plus 12 list pages: 616 exact
  official rosters, 55 blank-body unknowns, 6170 ranked rows supported.
- [x] (2026-10-11 18:14Z) Materialized all 28/294 targets: 474 ranked, 8 linked
  unresolved, 74 withheld lineage links; original 556 links accounted for.
- [x] (2026-10-11 18:16Z) 143 focused tests passed; independent 294-row count
  recomputation, exact deterministic replay and PR80-output equality verified.
- [ ] Commit, push and ordinary merge after required remote checks pass.

## Surprises & Discoveries

The browser's Excel download interception failed; no downloaded file is claimed.
Public direct HTML GET returns EUC-KR bytes with date, physical venue, race number,
whole result roster, goHorse stable IDs and a separate gate-keyed timing table.
Horse-link region is not physical race venue. The completed Pro response agrees
that positive dated official evidence can support an older collision member
without assigning the unresolved later member a guessed event type.

Busan has two timing tables and both must agree. Seoul's void-race list includes
incident numbers outside the race links, so parsing all numbers from a cell is
incorrect. Yeongcheon detail links use physical meet=4, unlike the regional
listing menu=3. The first captured archive is retained, and a corrected archive
reuses 659 unchanged receipts plus 24 newly fetched venue-4 details. Total
collector requests: 707; final selected receipts: 683, all successful.

## Decision Log

- Decision: Keep old seed, H0/H1, observed_partial_v1 and M0/M1 immutable.
  Rationale: New official observations are new information, not retroactive
  evidence for October 10/11. New features are diagnostic only.
  Date/Author: 2026-10-12 / Codex.
- Decision: Separate event, roster, rank and time support. Never infer no-race
  from an empty HTTP-200 template or require consecutive normal ranks.
  Rationale: Actual races can include exclusions, dead heats and other statuses.
  Date/Author: 2026-10-12 / Codex.
- Decision: Paid servers remain deferred by the owner's explicit instruction.
  Rationale: This research runs locally without creating accounts or resources.
  Date/Author: 2026-10-12 / Codex.

## Context and Orientation

Work in the existing `kra-analysis-race-card-pdf` checkout. `autoresearch` and
`shared` below are within `packages/scripts`. `frozen_history_view.replay_frozen`
verifies a seed's selected manifests and pages without choosing later receipts.
`history_identity_audit.audit_replayed_seed` computes collision relationships.
`observed_partial_history.project_partial_history` preserves legacy output and
computes explicitly observed counts. A sidecar is a new file containing evidence
and decisions, never an in-place edit to the source. A canonical horse ID is the
decimal integer ID without leading zeroes; gates remain part of roster keys.

The actual seed is `.cache/autoresearch/observed-history-20261011/seed-final.json`,
SHA256 `0dbe7abe5bdfb0a0b422bb90bddbdf1a3face89e5016254807ba37be95c25c66`.
The corpus is `.cache/autoresearch/restricted-cohort/20261011T124748.785378Z_ebdf29deaaa9/corpus.json`,
SHA256 `d6598f244d6a7b7bc5e65846a4c79ee6ac96ad278b89a14268de332e77526ae2`.
Every corpus ledger roster is a target, independent of labels and eligibility.

## Plan of Work

First add `shared/official_result_support.py` to parse original HTML with the
standard HTMLParser and reconcile whole gate/horse sets plus per-row values.
Then add `autoresearch/official_history_support.py` to freeze a request plan,
capture raw HTML with hashes and local timestamps, replay without network, and
materialize a full sidecar and target features. Reuse existing exclusive writes,
frozen reader and old partial projector. Preserve failed requests and allow
resume from completed per-request receipts, never overwrite a receipt. Add a
dedicated test module and CI invocation. Add the final research report only after
real execution, including current official evidence hashes and its later timing.

## Milestones

The capture milestone ends when positive Seoul/Jeju/Busan pages and a blank
collision-date template are archived and parsed from their bytes. The full
execution milestone ends when each seed group has an attempted official query
and the sidecar records supported and withheld rows without changing membership.
The diagnostic milestone ends with the complete 28/294 output, nonempty supported
history, explicit coverage limits and reproducible lineage. Publication is a
separate milestone requiring tests and remote checks, not just local success.

## Concrete Steps

From the checkout root use `.venv/bin/python` with `PYTHONPATH=packages/scripts`.
Run the new module with `--help`, then its explicit `collect` and `materialize`
commands with the pinned paths/hashes above and a new archive directory under
`.cache/autoresearch/official-history-20261012`. Replay twice without network.
Run `.venv/bin/python -m pytest -q packages/scripts/autoresearch/tests/test_official_history_support.py -o addopts=''`
and the existing frozen-history/result/history-audit regressions. Use Ruff on
new modules and tests and `git diff --check`. Record actual counts here once known.

## Validation and Acceptance

Test wrong or missing body dates/venues, HTTP200 blank templates, missing horse
IDs, duplicate gates/IDs, incomplete tables, excluded runners, rank/time conflicts,
same roster on two valid dates, confirmed older/unknown later, capture hash drift,
later receipts, cutoff-after-source rejection, all-target membership and label
independence. Official source availability is local-clock-only until separately
anchored; it cannot borrow PR80's timestamp. No new fit, prediction registration,
training approval or 70% evidence is generated. Missing list scope must be
reported, never presented as complete actual racing coverage.

## Idempotence and Recovery

Store each response before its receipt, verify existing receipt bytes on resume,
and use exclusive output creation. Failed fetches remain explicit; retry into a
new archive/version rather than replacing prior evidence. Do not delete originals
or alter the dirty primary checkout. A single fetch failure does not block
other independent groups; malformed evidence must not silently become zero.

## Artifacts and Notes

The Pro consultation is https://chatgpt.com/c/6aca2dc4-d2e8-83e8-acab-e85f281c27b7.
Its completed answer was read only after the completion notice and final answer
controls appeared. It reviewed public code and official pages, not local bytes
or our test suite. Official detail endpoint is
https://race.kra.co.kr/raceScore/ScoretableDetailList.do with Act=04, Sub=1,
meet=the physical code from the detail link, realRcDate=YYYYMMDD, realRcNo=race number. Body identity is
mandatory and is not supplied from those request fields.

## Interfaces and Dependencies

Use existing httpx, standard library HTMLParser/Decimal, JSON and hash helpers.
Do not add a framework or approval registry. Expose `parse_detail(html)` and
`reconcile_group(records, official)` as pure functions; use explicit archive and
seed hashes in the I/O module. Keep old public contracts unmodified.

## Outcomes & Retrospective

Actual execution and all-group reconciliation are complete. The final report is
`docs/research/2026-10-12-official-history-support.md`, with source/output hashes
and a complete replay command. Officially supported ranked features are unchanged
from PR80, while 74 unsupported unresolved lineage links are withheld explicitly.
No fits or prospective predictions were generated. Remote publication remains.

Revision 2026-10-12: replaced the provisional regional detail-code assumption
with observed physical detail links, required agreement across Busan timing
tables, and restricted list-number parsing to anchors. These changes follow
actual captured source structure and preserve both earlier archives and targets.
