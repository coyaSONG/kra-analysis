# Diagnose historical time information without fitting

This living ExecPlan follows `.agent/PLANS.md`. Maintain Progress, Surprises &
Discoveries, Decision Log and Outcomes & Retrospective as evidence arrives.

## Purpose / Big Picture

Determine whether the original May archive offers nonconstant time quantities
and repeated same-horse observations worth a separately approved future study.
The user can replay a full-population report without training a model, reading
October target outcomes or registering future races. Neither arithmetic agreement
nor descriptive variation proves predictive improvement toward the 70% goal.

## Progress

- [x] Inspect merged PR127, the original replay interfaces and no-fit proposal.
- [x] Implement full-population descriptive quantities and repeat diagnostics.
- [x] Test missingness, exclusions, exact arithmetic and temporal boundaries.
- [x] Replay original sources, interpret results and preserve immutable output.
- [ ] Pass required checks and normally merge; record the merge receipt on PR.

## Surprises & Discoveries

PR127 confirms endpoint arithmetic but does not demonstrate new information
beyond ranks. Its 1,029 observations include 28 withheld starts. Jeju has no
independent cumulative counterpart in this archive; no pace relationship will
be invented for it.

Original replay found 1,029 unique horses in 1,029 observations: there is no
longitudinal support within this short archive. Total-time gaps have 4,381
same-order pairs, 146 printed-time ties and no reversals against rank; pace
ratios have mixed orders, not evidence of predictive skill. Integration exposed
different receipt clock names and extra list-page entries; synthetic loader tests
now preserve both schema distinctions.

## Decision Log

Use exact rational arithmetic for derived ratios, preserving source decimal
precision. The within-race reference median includes all eligible positive-time
finishers, including the focal horse, and requires at least two OTHER eligible
horses (three total). If an otherwise eligible reference has invalid total time,
withhold the gap for the entire reference group rather than quietly shrinking it.
Excluded starters remain visible but never enter references.

Report pairwise order/tie agreement with historical rank, not correlations with
October targets or top-three accuracy. A rank reversal in a speed ratio shows
non-equivalent ordering only, not incremental predictive value. Use the proposed
single 1-180-day same-venue/exact-distance history rule without tuning it.
Historical repeat counts are structural, not May point-in-time training examples.
Synthetic as-of tests require all operand/reference clocks and semantic evidence
strictly before feature freeze, which is strictly before cutoff.

## Context and Orientation

`packages/scripts/autoresearch/sectional_arithmetic_audit.py` verifies the complete
original May seed, official HTML identity, known layouts and endpoint relations.
Its `source.ROOT` identifies the local archived files and `source.SEED_SHA`,
`source.HTML_SHA` pin their versions. `replay_frozen` returns historical records
including source clocks and ranks. `replay_archive` returns official HTML receipts.
The new `time_information_audit.py` must reuse these validators before deriving
anything. Do not import learners, query new results or load saved models.

## Plan of Work

Add one read-only audit module and focused tests. Derive `(T-m)/m`,
`200*T/(E*D)` and `600*T/(L*D)` where T is total seconds, m the eligible historical
race median, E initial 200m, L verified final 600m and D nominal distance.
Preserve each original identity, eligibility, literal class, raw operands,
reference membership and source clocks. Keep missing and unsupported reasons
separate. Summarize all 18 venue/distance groups, exact distributions, rank
ordering disagreements and same-horse repeats. Add the test to existing CI.
Publish a Markdown interpretation with an immutable JSON output in
`docs/research/experiments/2026-10-20-time-information/`.

## Concrete Steps

Run from the isolated repository checkout:

    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m pytest -q -p no:cacheprovider packages/scripts/autoresearch/tests/test_time_information_audit.py
    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m autoresearch.time_information_audit

The second command prints JSON only; preserve a new output file exclusively,
never replace an existing report. The historical cache must be available. Missing
or changed original bytes must fail instead of triggering network collection.

## Validation and Acceptance

All 1,029 identities must remain, with unchanged eligibility totals and no October
outcome reads, fitting, model writes or population registration. Synthetic tests
must demonstrate zero/missing rejection, unchanged input objects, deterministic
row permutations, reference exclusions, tied ranks/times, same-day/future history
exclusion, 180/181-day boundaries and late reference/semantic source rejection.
All unsupported rows retain null values and explicit reasons. Required CI must
pass before a normal merge; never bypass branch protection.

Observed local validation: 45 new cases and 239 related regression cases passed;
Ruff lint and format checks passed. Published model/commitment/registry hashes
remain unchanged. Independent original-byte checks reproduced all 1,029 identities
and the 1,001 / 705 / 705 usable-quantity counts.

## Idempotence and Recovery

The audit only reads pinned original files and prints a timestamped report.
Rerunning cannot update a reservation, model, input or evaluation population.
Inspect failed pins and leave source files untouched. Record new evidence as a
new artifact version. Preserve the user's original dirty checkout.

## Artifacts and Notes

The parent source report is
`docs/research/experiments/2026-10-20-sectional-arithmetic/report.json`, SHA256
`94fbd92c4f5506da4516bfe1e92858018ca9b2be24f567013eb8a4cccd53f18d`.
Source clocks represent local acquisition, not independently witnessed upstream
publication. No May observation collected in October is a May pre-race example.

## Interfaces and Dependencies

Use standard-library Fraction, statistics, datetime, Counter and existing
HTML/replay functions. Provide `describe(rows)`, `prior_rows(rows, target,
freeze=None, cutoff=None)` and `audit(root=source.ROOT)` as pure diagnostics
except for audit's bounded file reads. They are not a live feature builder or
candidate approval path. Test fixtures are synthetic.

## Outcomes & Retrospective

Original replay completed on 2026-10-20 at 18:14:40Z. All 102 races and 1,029
observations remain; 1,001 supported relative-time values and 705 values per pace
ratio are available. A separate HTMLParser/Fraction check, importing no new
auditor, extracted the original bytes and reproduced all eligible ratios and
the no-repeat finding. The bounded May feasibility question is answered: this
archive can describe variation but cannot test repeated-horse stability.
Review existing broader historical evidence next, without changing the window
to chase coverage or fitting a candidate. Dates and N remain unset, A24/B34 fit
budgets consumed and unchanged. No accuracy claim is authorized.

Initial plan records the next no-fit step after merged endpoint audit.
Updated after full original replay: preserve the negative repeat-support result,
adapter repairs and independent computational check rather than continue searching
the same short archive for a favorable outcome.
