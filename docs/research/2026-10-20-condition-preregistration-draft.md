# A24 and B34 prospective preregistration draft

## Status and decision boundary

**DRAFT ONLY. Not a registration, approval, executable protocol, or permission
to infer or fit.** Prepared on 2026-10-20 KST. Start/end dates, study IDs,
actual race count, race IDs, rosters, source pins and live runtime are deliberately
UNSET. Do not put this document in the execution registry or substitute
placeholder JSON for a reviewed protocol.

This develops the [PR113 future validation plan](2026-10-19-condition-development-results.md#future-validation-draft)
using the [PR114 inference and publication contract](2026-10-19-condition-forward.md).
The registry `data/contracts/condition_forward_reviews_v1.json` remains empty.
The latest reviewed schedule observation, collected at
2026-10-20T12:32:24Z, still exposes only October 16-18 races; it does not prove
that no future races exist. No new schedule or API request is needed to write
this draft. Confirm actual official schedules before selecting any interval.

A24 is the reference; B34 is the candidate. Keep the published stored models:

| Artifact | SHA256 |
| --- | --- |
| A24-model.json | 69f655fd005b59313d0a23dbf44759510c937ef403e8ac4fd844ea67494d635e |
| B34-model.json | c03972a447c2a36603717a7107b751f23d0fff08cb204565b68215f955ef16e0 |
| Training receipt | 3587c948913c82cc9c0b8c5e64161ef29794ed22a80d08425300e924834aa96e |

These files are under `docs/research/experiments/2026-10-19-condition-training-v1/`.
The lifetime fit allowance is exhausted: one fit per arm, no retries, refits,
scaler/imputer fitting, threshold search, arm selection or automatic promotion.
The October 16-18 development block and its 4/50 versus 5/50 training results
are excluded from prospective evidence. Original M0/API27 commitments and
their separate 0/50 versus 0/50 evaluation remain unchanged.

## Proposed population and calendar

Propose **12 consecutive KST calendar weeks**, Monday 00:00 through the end
of Sunday of week 12. This duration is a planning proposal, not a selected
calendar interval. After an actual new official schedule is available, choose
and separately approve the exact start/end timestamps before any included
race cutoff or outcome. Never enter a week after its first cutoff, skip to
a convenient later week, or redefine the start after seeing performance.
If readiness fails before registration, leave the study unregistered and
record why; a later proposal is not a retrospective replacement.

Include every official race in scope across all KRA venues represented by
the reconciled national and regional official schedules, including any new
venue. No filtering by distance, grade, field size, predicted confidence,
history support, API completeness, or whether either arm produces a prediction.
Use canonical `race_date/meet/race_no` identities, not horse-level rows as trials.
Record the exact venue scope when the schedule is confirmed; an unsupported
venue is an admission blocker, not permission to remove its races.

Future weekly schedules are not available all at once. Use an umbrella
methodology plus disjoint weekly execution protocols, not a fabricated
12-week roster. The umbrella fixes calendar boundaries, inclusion, statistics
and failure policy before week 1. Each week's protocol freezes all that week's
race IDs and rosters, linked source evidence and inputs before its earliest
cutoff. It must link the umbrella hash in its reviewed horizon text. Later
weekly registrations implement that fixed rule; they may not change it in
response to previous scores. A week with no usable inputs or no timely approval
stays in the umbrella accountability ledger, even though execution is blocked.

The umbrella population is the union of its frozen weekly full rosters plus
explicit completeness exceptions. Audit against later official schedules:
never silently remove cancelled races, failed weeks or late-added races.
Preserve the original execution populations byte-for-byte. A newly added race
after freeze is an umbrella coverage exception with no valid precommitted
prediction; retain its official identity in a separate append-only exception
ledger. Do not insert it into a consumed execution protocol. A proven prediction
failure may be scored only under the rules below. Until all exceptions are
reconciled, overall population verification and full accuracy remain unavailable.

Preserve original IDs and clocks for postponements, withdrawals, replacements,
renumberings or official corrections. Do not regenerate selections or move
cutoffs later to rescue a late prediction. Resolve identity changes using
official evidence; ambiguous links remain pending. Races moved outside the
calendar remain visible as original population exceptions, not substitute slots.
No-race weeks require affirmative official evidence, not an empty API response.

## Duration and sample size rationale

Twelve weeks provide repeated operating conditions and more than a single
week's comparison. At an illustrative 50 races/week, the planning size is
**600 races**. This is not a forecast, minimum quota, exact enrollment, or a
power guarantee. Actual N is determined only by complete official schedules.
Retain all races even if N is smaller or larger; never stop at the 600th race
midweek or extend the calendar to reach 600 or a desired result.

For scale only, under independent Bernoulli trials the nominal normal 95%
half-width at p=0.70 and N=600 is
`1.96 * sqrt(0.70 * 0.30 / 600) = 0.0367`, about 3.67 percentage points.
The worst-case p=0.50 benchmark is about 4.00 points. Races share meetings,
horses and weather; these are optimistic planning calculations, not the
reported uncertainty method. A 2-point in-sample difference from 50 races
does not supply a defensible power assumption. Do not claim this design has
80% power or can establish 70% generalization.

Before actual registration, review schedule-based expected race/week counts
and the operational burden. Any change to this proposed duration must be
made before the first included outcome and reflected in the approved umbrella.
After registration, a shortfall is reported, not repaired by adding weeks.

## Input freeze and timely publication

For each weekly block, use all inputs available before protocol creation,
and freeze the whole block before the earliest scheduled start minus 30 minutes.
Protocol publication, separate approval, inference, staging and normal
prediction-PR merge must all precede that earliest cutoff. Local persistence
or staging alone is not public existence. Preserve server merge evidence,
exact bytes, UTC timestamps, source URLs, raw hashes, missingness and joins.

Use the stored medians/scalers and fixed ordering/selection in PR114. A24 uses
the first 24 columns and B34 all 34 of the same identity-ordered matrix.
Each produces exactly one unordered set of three distinct roster horse IDs.
Never use an OR-union, top-k list, portfolio or fallback model.

Proposed history policy: officially observed prior-block outcomes may enter
the existing fixed history feature definitions only if their source snapshots
and availability are verified before this block's input freeze. No within-block
outcome update, backfill from a later snapshot, manual error correction based
on target outcomes, learned parameter change or feature-definition change.
Both arms use the same reviewed history version. Record history version
changes per block so this operational policy is distinguishable from fitting.

Unknown source availability, incomplete source-to-feature provenance, missing
rosters, authentication/rate/network errors and source conflicts block admission.
They are not proof of no races. Retain known population slots and failure reasons.
The current runner permits one pair attempt per study across worktrees;
a failed attempt consumes it. Read-only replay may check existing bytes but
may not produce a replacement. Preserve all original ledgers and receipts.

## Scoring and prediction failures

The estimand is operational race-level exact success using only pre-race
information: one timely, valid public triple equals the official unique
unordered top-three target. Apply the same rules independently to both arms.
Keep prediction state and outcome state as separate columns.

| Evidence state | Proposed accounting |
| --- | --- |
| Timely valid public triple; unique verified target | Exact equality is a hit; any other triple is a miss |
| Proven absent, late or invalid prediction; unique verified target | Miss, with a separate protocol-failure reason; never drop the race |
| Publication proof temporarily unavailable or conflicting | Pending evidence, not a presumed late failure; preserve append-only witness attempts |
| Result missing, conflicting, ambiguous top three or identity unresolved | Pending evidence, even if a prediction failure is already known |
| Official void/cancellation establishing no target | Undefined target, even if a prediction failure is known |

A malformed set (wrong size, duplicate IDs, out-of-roster IDs), hash mismatch,
late computation/publication or a consumed run with no output cannot earn a
hit by matching a later result. Operational proof of failure is required;
an inaccessible file alone is not proof. A whole-block failure affects every
retained race for the affected arm once its unique target is verified.
An arm-specific failure does not erase the other arm's valid prediction.

Use `versioned_result_observations.py` for source comparisons and target states.
Do not invent a target for a boundary dead heat or choose a favorable source;
unresolved top-three membership stays pending under the existing policy.
Withdrawn runners do not authorize replacing a predicted horse. A valid unique
target is compared to the original selection; no unique target is fabricated.
Official corrections create linked new outcome/evaluation versions with old/new
counts and conclusions, never edits to predictions or the original result.

For each arm require `N = hits + misses + pending + undefined`.
Only when the whole population is verified, N>0 and pending=undefined=0:
`accuracy = hits/N`, `delta_pp = 100*(B34_hits-A24_hits)/N`.
Also publish both-hit, A24-only, B34-only and neither-hit counts, whose sum must
be N for a complete paired comparison. With unresolved rows, report resolved
paired cells plus unresolved counts, not a subset accuracy or final winner.
Undefined targets prevent the stated whole-population exact accuracy; do not
remove them or silently score them zero. Pending results are never misses.
Prediction-failure incidence and timely coverage are separate diagnostics.

**Implementation gate:** PR114 provides inference/publication, not an A24/B34
outcome evaluator or umbrella enrollment ledger. The existing
`local_m0_evaluation.classify` counts a missing prediction as a miss with a
verified target, but leaves other unverified publication states pending.
Do not claim it already implements the proposed proven-late/invalid rule.
Before registration, implement and separately review a read-only A24/B34
adapter and completeness ledger, with synthetic tests for every row above,
partial-arm failure, late-added races, missed weeks and corrections. Do not
alter M0/API27's historical scoring contract. This draft executes no adapter.

## Uncertainty and reporting

Primary comparative quantity is the paired B34-minus-A24 full-population
percentage-point difference. Report both exact accuracies and achieved N,
calendar weeks, race-bearing weeks, venues, coverage and failures alongside it.
Point estimates describe this fixed population; intervals concern uncertain
generalization beyond it, not uncertainty about an already observed count.

Proposed primary interval: paired moving-block bootstrap of chronological
weekly totals `(N_w, hits_A_w, hits_B_w)`, block length two adjacent calendar
weeks. At 12 weeks, sample six blocks with replacement uniformly from starts
1 through 11, concatenate to 12 weeks, preserving both arms and all races
within each week. Recompute ratios of summed hits to summed N, never average
weekly percentages. Use 10,000 replicates, NumPy PCG64 seed 20261020,
2.5/97.5 percentile endpoints with linear quantiles; freeze implementation and
runtime before registration. A fixed length-three block sensitivity uses four
blocks from starts 1 through 10 and the same seed, reported regardless of
whether it weakens the conclusion. Never select the nicer interval.

This follows the fixed-block resampling family described in the
[R boot documentation](https://stat.ethz.ch/R-manual/R-devel/library/boot/html/tsboot.html);
the parameters above are proposed study choices, not recommendations from
that source. Blocks retain local temporal dependence, but 12 weeks are few
and dependencies may persist longer than two or three weeks. Stationarity and
representativeness are assumptions, not verified facts. Both intervals are
approximate descriptive uncertainty, not guaranteed coverage or a promotion test.
With fewer than 12 race-bearing weeks, incomplete targets/population, zero
denominators or degenerate bootstrap distributions, report the limitation and
do not claim reliable generalization from an interval. No iid binomial or
unpaired comparison substitutes for the registered primary method.

No confirmatory significance claim or automatic goal completion is proposed.
A point estimate at least 70% is a descriptive threshold crossing only;
it is not evidence that a long-run rate is at least 70%. Report both arms,
not a post-hoc best arm. Any promotion or stronger claim needs separate review
of prospective evidence and its uncertainty. Distance/grade/venue/support
analyses are exploratory diagnostics, with counts and small-sample caveats.
No segment selection, multiple-comparison fishing or in-study tuning.

## Stopping and unresolved evidence

Stop enrollment at the approved calendar end, regardless of hits, apparent
superiority, 70% crossing, low power, cancellations or API problems. No efficacy
or futility interim stopping. Interim updates may report counts and integrity
issues but cannot change models, inclusion, horizon or the analysis.

Propose one scheduled analysis snapshot 14 calendar days after the fixed end
at 12:00 KST; exact timestamp is UNSET until the interval is approved. This is
an evidence cutoff, not permission to turn pending results into misses.
If incomplete, publish counts and limitations. Later official releases or
corrections append revised analyses without extending enrollment or resetting N.
Do not repeatedly fetch completed outcomes without a correction/conflict signal.

Stop new inference immediately on model/input/runtime integrity failure,
target leakage, lost attempt ledger or unavailable required authorization.
Preserve consumed attempts, report deviations and never restart that block.
An administrative stop does not shrink the intended umbrella calendar: keep
its missed blocks and completeness gaps visible. Contaminated observations
cannot be advertised as independent validation or rescued as a favorable
subset. Any later experiment needs a distinct prospective protocol, while
this attempt remains permanently recorded.

## Registration checklist and draft validation

Before activation, confirm the actual official schedule, precise calendar
boundaries and venue scope; reconcile full IDs/rosters and all completeness
exceptions; approve this methodology and the not-yet-implemented evaluator/
umbrella ledger; freeze runtime, source derivation and history rules; publish
the exact executable weekly protocol; obtain a separate owner-authorized
review; normally merge approval and predictions before cutoff; retain witnesses.
Leave dates, IDs, N and evidence pins UNSET until those facts are available.
Publishing or merging this Markdown draft satisfies none of these gates.

Draft QA covers full-denominator arithmetic, sample-size benchmark arithmetic,
stored-model hashes, unchanged empty approval registry and the existing frozen
inference regression suite. It cannot validate future availability, determine
the eventual sample size, or establish bootstrap coverage. No live inference,
training, new registration or collection is performed for this document.

Local validation on 2026-10-20: `test_condition_forward.py`,
`test_local_m0_evaluation.py` and `test_versioned_result_observations.py`
passed 119 tests in 6.59 seconds with `PYTHONPATH=packages/scripts`,
`PYTHONDONTWRITEBYTECODE=1` and pytest `-p no:cacheprovider`. A separate
read-only check verified all three artifact hashes and the empty registry,
255 nonempty synthetic paired-cell combinations, and planning half-widths
3.666824/4.000833 percentage points. `git diff --check` passed. These checks
validate the draft's references and arithmetic, not future outcomes or the
proposed adapter, which remains an activation blocker.

## Accounting preparation after the draft

`autoresearch/condition_outcome_accounting.py` implements only the proposed
arithmetic on normalized synthetic evidence. It has no CLI and is not called
by the forward runner or historical evaluators. It cannot establish source
authenticity, publication timing, roster membership, correction ancestry,
or completeness of an umbrella population. Caller-supplied verification
states are preconditions, not evidence that those gates passed.

The reducer retains every explicitly supplied race, rejects extra evidence
IDs, separates proven failures from unknown publication evidence, and withholds
full rates for unresolved targets or an unverified population. Its 65 tests
cover state combinations and 80 nonempty paired count tables; 119 existing
regressions also passed locally. An actual evidence-replay adapter and
append-only completeness ledger remain unimplemented activation blockers.
This preparation selects no interval, registers no race, and performs no fit,
live inference, outcome collection, or prospective performance comparison.
