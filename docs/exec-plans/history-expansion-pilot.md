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
- [x] (2026-10-12) Commit, push and normally merge PR #90 after required CI passes (merge `fb15e5717abae74f9506e57139972c36837baa6e`).
- [x] (2026-10-13) Initialize June 1-July 4 extension: 136 date/venue units, 512-request ceiling.
- [x] Preserve the failed June API attempt as a pinned zero-row seed; API completion remains deferred until service recovery.
- [x] Replay 237 official result pages for the extension and compare the same 6,816 original target rows with separately labelled source tiers.
- [ ] Record findings, run regressions and publish the June increment after required checks.
- [x] (2026-10-13) Three API failures and four bounded probes timed out; preserve zero-row failed seed and capture official list pages.
- [x] Implement and verify a separately labelled official-HTML-only catalog and fixed-target coverage comparison; pass 180 regressions and Ruff.
- [x] Receive completed Pro advice without interrupting generation; add source positions, notice withholding, source-specific totals and October-window tests.

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

June acquisition encountered timeouts on June 1, June 5, the formerly successful
July 5 control, and API26. The unauthenticated gateway answered, but that does
not establish endpoint health or the failure cause. Official result HTML still
works. Twelve pinned list pages extend past June into May for all three menu
regions, including physical venue identifiers parsed from the listed rows.

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

On October 13, retain the API failure evidence and collect a separate official
HTML catalog instead of repeatedly exhausting the API. Never manufacture an
API seed from HTML rows. `official_history_catalog.py` will build a request index
from replayed list pages filtered to June 1-July 4, reuse the bounded official
HTML fetcher, and replay every detail against its expected identity. The old
fetcher's internal `seed_sha256` field will bind this explicitly typed request
index, not an API result seed. Failed/unknown detail slots remain in the index.
The catalog's numeric rank plus valid recorded time is single-source evidence,
not `ranked_feature_supported` and not corroboration by a second representation.

The catalog comparison will consume an exact pinned, freshly replayed PR90
coverage report and keep all of its target rows. It reports additional HTML-only
prior IDs and combined coverage in separate fields, without altering API-backed
counts. Add tests for index membership, wrong dated body, tampered pages,
same-day exclusion, duplicate identities, and no training/performance approval.
The API path can be retried once after a meaningful interval; do not change its
frozen parser, plan, or failure receipts. The recovery probe also timed out; stop
this diagnostic round. Completed Pro advice supports this source-tier separation
and fixed denominator. Add list/detail row provenance and conservatively withhold
listed rows carrying a void notice pending review. Do not treat June history as
an improvement to the frozen October 90-day feature contract.

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
commands, pins and acquisition priority. PR #90 was merged normally; June
extension acquisition and validation are complete via the official-HTML-only
fallback: 237 races, 2,375 rows (June alone: 204 races, 2,046 rows). Mixed-source
one-prior coverage is 5,718/6,816, versus unchanged supported count 4,435/6,816.
This is coverage, not prediction accuracy. June API collection remains incomplete.
The June increment awaits publication and required CI checks.

Revision 2026-10-12: created to separate actionable historical research from
future-card availability and retain the existing frozen forward experiment.

Revision 2026-10-12: API recovered without parser changes. Extend the study with
fixed-population before/after comparison and record verified acquisition gains.

Revision 2026-10-13: continue the existing collector and study, without changing
their contracts. June source root is
`.cache/autoresearch/observed-history-extension-20260601-0704`; its plan SHA256 is
`679676e6661413ddfe66756b8f15dfe6d69fb35efbaa59d9879dcb099d57ef05`.
Run `observed_history_seed collect`, then `export`, and
`official_history_support collect` with the resulting seed pin. Run
`history_coverage_study` on the original seed with two `--history-source`
arguments: the existing July 5-11 source and the new June 1-July 4 source. All
commands run from the isolated checkout with `PYTHONPATH=packages/scripts` and
`.venv/bin/python -m autoresearch.<module>`. The initial 512-call ceiling includes
pagination and identity-binding API26 requests. Three consecutive failed units
stop collection; investigate with the existing bounded probe before retries.
Record exact commands and resulting pins in the June research note. Acceptance
requires full raw replay, unchanged target membership, no same-day/future result
features, and explicit reporting of unresolved event groups. No training or
prospective-accuracy claim is permitted by this acquisition increment.

Revision 2026-10-13: repeated controls show acquisition failure is not isolated
to June. Add official-only collection so useful history can be acquired without
weakening API validation. Run `.venv/bin/pytest -q
packages/scripts/autoresearch/tests/test_official_history_catalog.py -o addopts=''`
and existing history tests. The new module's `collect` and `compare` help gives
the exact required index/archive/discovery/report pins. Persist artifacts only
under `.cache/autoresearch/official-june-catalog-20261013` and report source tiers
separately in `docs/research/2026-10-13-june-history-expansion.md`.

Revision 2026-10-13: actual HTML acquisition, source replay and Pro consultation
are complete. The research note contains final pins and limitations. Validated
code, tests, CI integration and notes will be committed and normally merged;
record publication closure in the PR once its required checks pass.
