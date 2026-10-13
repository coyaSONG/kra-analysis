# Compare historical form within similar race conditions

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

The owner requests authenticated API approval/quota checks and concrete research
using similar distance and class. Preserve all 671 archived target races and the
existing 90-day expanded history. These are fixed, non-fitting retrospective
diagnostics, not a historical pre-race backtest or evidence for the 70% goal.
Result-derived target rosters and conditions were captured after the races.

## Progress

- [x] Inspect logged-in API approvals: API214 10,000/day, API26 3,000/day.
- [x] Bounded probes return HTTP 200, code 00 for both APIs on June 7.
- [x] Resume the existing June collection with preserved failed receipts.
- [ ] Freeze condition comparisons before looking at their outcomes.
- [ ] Implement additive pinned condition extraction and focused tests.
- [ ] Execute the full-population experiment and reconcile recovered June rows.
- [ ] Run regressions, document all results, push and normally merge after CI.

## Context and Orientation

Work only in `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf` on
`codex/condition-form-research`. Existing `history_form_research.load_sources`
replays pinned API and official HTML sources. Its protocol remains unchanged.
Add a condition projection from dated official HTML headers; the race identity
must match the expected physical venue, date and number. Missing or ambiguous
conditions must not remove a race. Never infer race class from a runner's finish
rank or merge class labels across venues. Keep raw receipt pins and parse reasons.

## Plan of Work

Freeze five arms: unchanged expanded90; same physical venue; same venue and
distance within 200 metres inclusive; same venue and exact class label; same
venue, distance within 200 metres and exact class label. Each condition arm uses
only that horse's strict prior dates in [D-90,D), with the existing normalized
rank score `(1 + sum((N-r)/(N-1)))/(2+n)` and gate/horse-ID ties. If target context
is missing, or a horse has no eligible condition-matched prior, use that horse's
unfiltered expanded90 score. Report the fallback, eligible prior IDs, source
tiers and boundary ties. This is a sparse-history diagnostic, not a tuned model.
No neighbouring-grade ordinal conversion, condition weights or window search.

Replay sources and persist inputs and predictions before outcome comparison.
Report every arm with match/mismatch/pending/undefined counts and paired changes
against expanded90. Keep the original roster manifest and all unknown outcomes.
Recovered API rows are a separate acquisition audit and do not silently replace
the frozen experiment's HTML-only June tier. Request Pro advice on the fixed
comparison and record only completed advice, not partial generation.

## Validation and Acceptance

Test header identity, malformed/ambiguous conditions, exact class versus finish
rank, inclusive distance limits, date exclusion, unchanged fallback, no target
outcome inputs, duplicate rosters, pin tampering and full-population comparison.
Use `.venv/bin/python` with `PYTHONPATH=packages/scripts`; run focused history and
frozen M0/API27 regressions, Ruff and diff checks. Real acceptance requires all
671 predictions per arm plus independently reproduced baseline selections.
Record raw/report pins and commands in the research note. No model promotion.

## Decisions, Recovery and Outcomes

API approval and actual response are separate facts. The portal displays daily
limits, not verified remaining calls; do not claim a current usage balance.
API214 expires 2027-05-24; API26 expires 2028-06-15. Both are development accounts.
Do not publish credentials, account IDs, cookies or personal contact details.
The existing 512-request June plan is below either daily limit but is not a
claim about the account's other usage. Preserve failed and successful receipts.
Never overwrite artifacts or frozen production contracts. Outcomes pending.

Revision 2026-10-13: initial plan written before condition-arm execution.
