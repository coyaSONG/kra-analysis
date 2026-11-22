# Keep the whole 12-week population in paired condition-model reporting

Maintain this plan under .agent/PLANS.md in the isolated checkout.
No actual calendar, study, population, permission, forecast or fit is
registered. The M0/API27 policies and previously frozen inputs stay
unchanged.

## Purpose / Big Picture

The A24/B34 prospective draft defines an analysis that uses every
fixed calendar week and samples adjacent weeks in pairs. Reporting
only weeks with successful submissions or verified outcomes would
give a different answer. Prepare the reusable calculation now, so
the eventual reviewer can connect verified whole-population evidence
without choosing an interval after seeing results.

## Progress

- [x] (2026-11-22) Review the draft, existing single-universe paired
  states and population boundary.
- [x] (2026-11-22) Implement full-calendar accounting and both
  fixed bootstrap calculations; verify the policy and waiting states.
  Pass 371 adjacent tests and 73 final accounting tests.
- [ ] Run local and provider checks and release the validated code.

## Decision Log

Use the proposed 12 consecutive KST Monday-to-Sunday weeks, not
the next 12 available or successful meetings. Every week occupies
its original position. A missing week remains pending; verified
no racing requires external evidence. Verified operational failures
count as misses only for a unique verified target, with undefined
and pending outcomes kept separate. This module does not verify
or authorize any of those external evidence states.

Keep counts for closed weeks while waiting for the rest. Do not
publish a partial-population accuracy, difference, winner or interval.
Use a ratio of pooled hit and race counts, not the average of weekly
percentages. The primary resamples contiguous non-wrapping two-week
blocks and the sensitivity uses three-week blocks. Keep both arms
together and use the draft's fixed PCG64 seed and 10,000 replicates.
Withhold any degenerate interval rather than display a zero-width
confidence claim. The existing four paired counts and uncertainty
are descriptive, not promotion or goal-completion authority.

## Plan Of Work

Add a typed window wrapper to the existing outcome arithmetic, and
check all scopes against the supplied fixed first Monday. Validate
with only fictional race IDs and normalized outcome states. Use an
independent resampling implementation in tests to verify the original
draft's two fixed intervals and a case with unequal weekly sizes.
Keep the held operational registry untouched.

## Surprises & Discoveries

The weekly sample deliberately varies in size. The pooled accuracy
and the average of weekly accuracies differ even on the same
races. Also, an identical paired prediction history can have an
informative individual-arm interval but an entirely degenerate
difference distribution. The calculation separates those cases.

## Outcomes & Retrospective

The tests keep all 12 calendar positions for a 42-race fictional
sample. Each paired interval and each per-arm interval agrees
with an independent exact-fraction loop using the same locked
random draw stream. Unconfirmed results and proven voids remain
distinct; a proven late prediction becomes a miss only with the
unique verified target. A confirmed no-race week remains in the
calendar and cannot be resampled away. A missing week suppresses
full accuracy and the winner even if other weeks have hits.

The [R boot documentation](https://stat.ethz.ch/R-manual/R-devel/library/boot/html/tsboot.html)
describes fixed-length blocks concatenated from the original series.
The exact non-wrapping starts, lengths, count aggregation, seed,
replications and quantiles here come from the project draft, not
defaults from another package. All outputs are arithmetic only;
an independent adapter still must prove source and population
closure before they can be used in an evaluation.

## Concrete Steps

From the isolated checkout using the existing environment:

    PYTHONPATH=packages/scripts .venv/bin/python -B -m pytest -q -p no:cacheprovider -o addopts='' \
      packages/scripts/autoresearch/tests/test_condition_outcome_accounting.py \
      packages/scripts/autoresearch/tests/test_condition_weekly_uncertainty.py

Expect 73 tests, with synthetic-only records. The CI Python Checks
job uses the equivalent paths. The proposed module is read-only and
does not create a registration, fit or score any live race.
