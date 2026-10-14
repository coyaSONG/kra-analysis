# Fixed Condition Contrast on the New October Block

## Question and Protocol

Before observing any October 16-18 outcomes, determine whether a single fixed
historical condition contrast has within-race variation on the complete newly
published 50-race / 534-runner population. This is the next outcome-free check
recommended by the completed October 13 Pro consultation, not another fit on
the repeatedly inspected October 10-11 sample.

The contrast is `delta = joint90 - expanded90`, with the unchanged policy from
`data/contracts/condition_form_exploration_v1.json`: strictly preceding 90 days,
same physical venue, distance difference at most 200 metres, exact class label,
rank score `(1 + sum((N-r)/(N-1))) / (2+n)`. Missing target conditions or no
eligible history fall back to expanded90 for that runner. Fallback-zero and
observed-zero remain distinct. No parameter sweep, outcome loading, fitting,
selection of three horses, modification of published forecasts or promotion is
part of this diagnostic. A varying contrast establishes only that the feature
could distinguish runners, not that it predicts outcomes or improves accuracy.

## Inputs and Reproduction

Run from the isolated research checkout, with its existing local archive:

    PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.condition_delta_diagnostic --output-dir .cache/autoresearch/condition-delta-20261014/run-1

Choose a new output directory for each replay. The report uses exclusive writes.
The module pins the exact PR95 M0/API27/training manifests and the prior history
and conditions artifacts documented in `2026-10-13-condition-form-research.md`.
It replays the original raw entry pages linked through the published M0 packet
hashes, projects distance/class, and matches all runner identities to the frozen
packet roster. Horse IDs use existing `restricted_cohort.horse_id` normalization,
not fuzzy names. The original reservations, models and forecasts remain read-only.

Historical records were captured after their own races. They do not become
pre-race training examples for those old races. This prospective feature
diagnostic also does not independently re-certify historical training approval
or external publication. Its snapshot excludes later history updates, and all
missing slots remain visible. The existing complete-block M0/API27 outcome
comparison remains the only registered comparison for this week.

## Results

The full 50 races and 534 runner appearances are retained. Distance and class
are observed for all targets. The contrast varies between runners in 38 races;
12 races have constant zero contrast. No race has every runner in fallback.

| Runner-level state | Count | Share of 534 |
| --- | ---: | ---: |
| No eligible similar history; expanded90 fallback | 225 | 42.1% |
| Eligible history, but observed zero contrast | 195 | 36.5% |
| Nonzero contrast | 114 | 21.3% |

Of the 225 fallback rows, 79 have no preceding 90-day history in this snapshot;
146 have history but none meeting the joint condition. Absence from the archive
does not prove a horse has never raced. There are zero missing condition links
among histories used here. Among 309 rows with eligible history, the counts by
number of qualifying prior races are 164 with one, 79 with two, 31 with three,
21 with four, 13 with five and one with six. Of 114 nonzero contrasts, 86 rest on
just one qualifying prior race. These are runner appearances, not independent
observations or unique horses.

| Venue | Races with variation / all | Fallback rows / all |
| --- | ---: | ---: |
| Seoul | 15 / 21 | 92 / 229 |
| Jeju | 11 / 14 | 38 / 137 |
| Busan | 7 / 9 | 43 / 102 |
| Yeongcheon | 5 / 6 | 52 / 66 |

Coverage is especially weak at Yeongcheon (78.8% fallback). National class 6 has
variation in only 4/11 races, while Jeju class 6 has none in 2/2 races. These
small group descriptions diagnose availability only; they do not justify
excluding groups, merging venues/classes, or claiming subgroup performance.
The report also retains distance and class breakdowns for every group.

## Validation and Decision

Raw archive replay reproduced all 8,994 historical rows and 978 condition
records exactly from the pinned source plan. Historical source dates span June
5 through October 11; the histories actually linked into this block span July
18 through October 5. This does not establish exhaustive historical coverage.
The independent direct Fraction calculation verified all 534 contrasts, and
run-1/run-2 produced identical ledgers. Public commitment hashes were checked
before and after execution; all remained unchanged.

Final report: `.cache/autoresearch/condition-delta-20261014/run-2/report.json`.
SHA256: `69d675229d00b00e82f7aed10dd0d951788d5cf7f01965523942dcba5dac1215`.
The original run-1 is preserved as well. The report records raw entry evidence,
the original prediction packet hashes, exact fractions, history race IDs,
fallback state and segment counts. No target outcomes were requested or loaded.

Keep this single contrast as a candidate for a later controlled training
comparison, with fallback state and support counts retained. It passes the
minimum within-race variation check, but substantial sparse support prevents
any effectiveness claim. Do not tune the window or tolerance against this
cohort. After outcomes, compare the original M0/API27 predictions first. Any
model trained or selected using these outcomes must be tested on a later,
separately preregistered full population; no such new evaluation block is
registered here. This result is not model promotion or progress to 70% accuracy.

Focused tests cover exact contrast equivalence to the existing rule, zero vs
fallback separation, temporal exclusion, class/distance/venue mismatches,
missing conditions, duplicate/label-bearing targets, immutable output, and
published-input identity/roster/cutoff/population guards. Run:

    PYTHONPATH=packages/scripts .venv/bin/pytest -q packages/scripts/autoresearch/tests/test_condition_delta_diagnostic.py packages/scripts/autoresearch/tests/test_condition_form_research.py packages/scripts/autoresearch/tests/test_prerace_conditions.py

The combined local run passed 230 tests, including historical-form, unchanged
M0/API27 forward execution and prospective-input regressions. Ruff lint and
format checks also passed. Remote CI results are reported separately in the PR.
