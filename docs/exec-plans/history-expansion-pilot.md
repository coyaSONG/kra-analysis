# Diagnose historical API access and measure prior-history coverage

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

Continue local research while future entry sheets are unavailable. Distinguish
transport and gateway failures from legitimate empty responses, then measure how
much strictly earlier, officially supported history exists for every archived
runner. This is a data acquisition study, not model training or a 70% claim.

## Progress

- [x] (2026-10-12) Inspect frozen collectors, seed and official support archive.
- [x] Confirm July 5-11 pilot stopped after three timeouts, without new rows.
- [x] (2026-10-12) Implement bounded, credential-safe API diagnosis and tests.
- [x] (2026-10-12) Implement replay-backed history coverage study and tests.
- [x] (2026-10-12) Run real probes, collect 712 rows, verify 485 ranked rows, and compare fixed targets.
- [x] (2026-10-12) Pass 163 regression tests and Ruff checks; record findings and next collection scope.
- [ ] Run regression checks, commit, push, and merge after required CI passes.

## Surprises & Discoveries

The API26 control returned parseable JSON without the required response envelope;
the existing collector correctly rejected it but did not retain structural
diagnostics. API214 timed out on three July 5 venue requests. Neither result
establishes that old dates are unsupported. The goal service still reports
blocked and exposes no resume operation; native Codex UI control is disallowed.
Actual research can proceed independently of this status.

Both old-date probes later returned valid 97-row pages. Retrying the unchanged
collector completed all 28 units. The new seed includes 20 groups without
official event support, so raw acquisition alone overstates usable history.

## Decision Log

Keep frozen collectors and prediction contracts unchanged. Add a probe which
never persists response bodies, headers, URLs with credentials, or exception
messages. Emit only fixed classifications, allowlisted result codes and numeric
metadata. A probe is not a replacement data capture and does not authorize rows.

Replay the pinned seed and official HTML receipts rather than trust a cached
support report. Keep all archived races in the coverage denominator, including
unsupported groups. Same-day and future observations cannot contribute to any
prior feature. Missing history does not mean debut or no previous starts.

After recovery, add optional earlier non-overlapping history sources to the
study. Keep all original targets fixed and report baseline, expanded coverage,
and differences. Reject overlapping or non-earlier extension sources. This
directly measures the value of acquisition without fitting a model.

## Context and Orientation

Work in the isolated `kra-analysis-race-card-pdf` checkout. Research Python lives
in `packages/scripts/autoresearch`; imports require `PYTHONPATH=packages/scripts`.
`observed_history_seed.py` provides exclusive JSON saving and source pins.
`frozen_history_view.replay_frozen` verifies the raw seed captures.
`official_history_support.replay_archive` verifies and parses official receipts;
`shared.official_result_support.reconcile_group` checks event, roster, ranks and
times. The seed has 671 groups and 6,816 runner observations, not 6,816 approved
training rows. Official support covers 616 groups and 6,170 ranked rows.

## Plan of Work

First add `history_api_probe.py` with a one-request CLI for API214 or API26,
strict date/venue validation, no redirects, total deadline, bounded streamed body,
and fixed response categories. Tests exercise JSON, XML, timeout, empty pages,
credential-bearing error bodies, and response limits. Diagnose at most one old
and one known recent date per endpoint before deciding whether retries help.

Then add `history_coverage_study.py`. Replay the seed and official archive,
reconcile each group, and emit one coverage row per original runner. Count
strictly prior supported ranked observations within 90 days, retain unsupported
prior observations separately, and summarize by month and physical venue.
Preserve source pins and false training/performance approval flags. Test date
boundaries, duplicates, unsupported events, same-day exclusion and full roster
membership. Record actual observations in a repository research note.

## Concrete Steps

From checkout root, run:

    .venv/bin/ruff check packages/scripts/autoresearch/history_api_probe.py packages/scripts/autoresearch/history_coverage_study.py packages/scripts/autoresearch/tests/test_history_api_probe.py packages/scripts/autoresearch/tests/test_history_coverage_study.py
    .venv/bin/pytest -q packages/scripts/autoresearch/tests/test_history_api_probe.py packages/scripts/autoresearch/tests/test_history_coverage_study.py -o addopts=''

CLI help must document required pins and output paths. Use the already configured
local key file only for the two official apis.data.go.kr endpoints. Keep generated
artifacts below ignored `.cache/autoresearch/`; never commit raw data or keys.

## Validation and Acceptance

Error JSON/XML must never be accepted as zero rows. A 90-day lower boundary is
inclusive and the target day exclusive. Every seed row survives the study,
including unsupported target events. Tampered raw data must fail replay. Run
existing history and frozen forward tests as regression evidence, add new tests
to Scripts CI, and use a normal PR merge after required Python Checks passes.

## Idempotence and Recovery

Outputs use the existing exclusive save helper: select a new output filename
for another run, never overwrite evidence. Probe has no automatic retries and
no pagination. Existing failed collection receipts remain unchanged. No paid
services, no destructive git commands, no production model promotion.

## Artifacts and Notes

Seed: `.cache/autoresearch/observed-history-20261011/seed-final.json`, SHA256
`0dbe7abe5bdfb0a0b422bb90bddbdf1a3face89e5016254807ba37be95c25c66`.
Official archive: `.cache/autoresearch/official-history-20261012-v2/archive.json`,
SHA256 `eaece57cdd27ee4e348e171e04368440da9d82a4417110476f0a1a1400e934e2`.

## Interfaces and Dependencies

Use existing httpx and Python standard library only. Probe classification is a
pure function of bounded bytes; collection accepts an injected httpx client for
tests. Coverage projection is a pure function of seed records and reconciled
groups; materialization invokes full source replay first. Neither output can be
passed as approved training inputs.

## Outcomes & Retrospective

The overall 70% objective is not complete and no improvement in predictive
accuracy is claimed.

Implementation and measurement are complete: 25 new tests, 163 combined passing
tests; 712 new API observations, 485 supported ranked rows. On fixed original
targets, one-prior coverage increased 4,009 to 4,435; three-prior coverage 469 to
630. See `docs/research/2026-10-12-history-expansion-pilot.md` for exact replay
commands, pins and acquisition priority. Publication remains pending CI.

Revision 2026-10-12: created to separate actionable historical research from
future-card availability and retain the existing frozen forward experiment.

Revision 2026-10-12: API recovered without parser changes. Extend the study with
fixed-population before/after comparison and record verified acquisition gains.
