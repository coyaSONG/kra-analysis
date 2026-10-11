# Top-Three Result Observation Readiness

## Finding

Replaying the six pinned official API214 captures for October 9-11, 2026 retains
all 50 scheduled races and 510 result rows. There are 37 ordinary rank
observations and 13 races requiring review. Forty-nine races have a candidate
unordered set of three stable horse IDs at unique observed ranks 1, 2 and 3.
The remaining race, `20261010_1_1`, has 11 `경주불성립` notes and no candidate.

These are outcome-data diagnostics, **not prediction accuracy**. There are no
pre-race predictions in this retrospective report. No candidate is certified as
an official final outcome, and no race is dropped from the scheduled population.

## Interpretation

`ordinary_rank_observation` requires matching runner counts, unique canonical
horse IDs, all rows classified as ranked finishes by the existing normalizer,
and exactly consecutive ranks 1 through the observed row count. All other races
are `requires_review`. This conservative rule does not decide how cancellations,
disqualifications, dead heats or void races should be scored.

The 13 review races have unresolved runner observations and nonconsecutive
ordinary-finish ranks. Nine also have runner-count mismatches. These counts
overlap; they must not be added to create a race total. Candidate IDs can coexist
with blockers, for example when ranks 1/2/3 are present but an additional runner
has an exclusion note. A raw top-rank duplicate remains ambiguous even if one
of its rows is unresolved. Lower-rank ties also require policy review.

The existing `reconciled_observation_population` remains about row counts,
not outcome finality; CLI exit codes retain that meaning. Reading only exit 0
must not approve labels. All `counts_as_70_percent_evidence` and
`official_finality_verified` flags remain false. No result policy, training
review, champion, dependency, or forward-prediction implementation changes.

## Reproduction

From the isolated repository root:

```bash
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.kra_result_population_audit --plan .cache/autoresearch/prior-results/population-plan.json --output .cache/autoresearch/prior-results/population-top3-audit.json
```

The run exits 2 because the same nine existing count mismatches remain. A second
run to `population-top3-replay.json` is byte-identical (`cmp` exit 0). Exclusive
output creation prevents accidental overwrite. The local files are research
artifacts, not committed source data.

Plan SHA256:
`4c3385228e1f80d5a0cd609d9a78b236e3a3d53efdc8676920276039455cfb03`.

Output SHA256:
`a0ba48dff04841990a52ac0029df4c79d13ec4cff8bf98e4a6c8e69fd2c3851d`.

Source pin details remain in
[the original capture report](2026-10-11-prior-result-capture.md). All six
captures replayed without source failures; no extra or missing race IDs appeared.

## Verification and Next Boundary

The focused result suite passes 84 tests, including 24 new diagnostic cases.
The broader source, replay, schedule and training-evidence regression suite
passes 434 tests with 15 existing NumPy/joblib deprecation warnings. Ruff passes.

Official finality and exception settlement need a reviewed source contract
before these observations become scoring truth. Future comparisons must join
verified outcomes to the entire pre-race-frozen membership and independently
witnessed submissions, retaining unscorable/missing races visibly. No rate on
the 37 ordinary observations or the 49 candidates may replace that denominator.
