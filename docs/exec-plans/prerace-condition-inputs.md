# Verify distance and class in original pre-race API inputs

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

The condition-matched historical experiment improved exact combination matches
from 28 to 32 on the same 671 archived races, but used retrospectively captured
race conditions. Establish whether distance and class can instead be recovered
from independently published pre-race API26 bytes. This is input validation, not
a new performance estimate or permission to train on late historical archives.

## Progress

- [x] (2026-10-13) Refresh the unchanged Oct16-18 M0 archive; all three dates remain awaiting cards. A bounded Oct16 Jeju API26 probe returned code00 and zero rows, not proof of no races.
- [x] (2026-10-13) Inspect original API26 bytes: `rcDist` and `rank` are present. Existing hashed roster projection drops both fields.
- [x] (2026-10-13) Add an independent strict extractor and reproducible original-archive audit, without changing frozen model dependencies.
- [x] (2026-10-13) Pass 51 new tests and 235 related regression tests. Audit all 28 races / 294 runners: both fields observed and matched for every race; all source publication/cutoff checks passed.
- [ ] Record evidence, push a small PR, and merge normally after required checks.

## Surprises & Discoveries

API26 requests with rc_no may return the full day, not only the requested race.
Reuse `build_entry_snapshot` for full identity/roster checks, then select the
requested race locally. A missing condition must not remove that race from the
audit. API `rank` here is the race class string, not the result finishing rank.

The original inventory contains Seoul 21 / Jeju 7 races and no Busan races.
All 13 observed exact class labels and 10 distances matched the pinned official
HTML condition artifact. The 1110m distance was preserved, and the later-void
20261010_1_1 race remained in the inventory. This is not nationwide validation.

## Decision Log

2026-10-13: Do not change hashed shared entry/inference modules, M0, API27 or the
published condition experiment. Add a separate module. Recover distance and class
independently so one missing field does not destroy the other; this changes no
existing model policy. Require every selected runner to have the same valid
value, and retain raw values and reasons. Do not use majority vote or results to
fill a disagreement. Preserve exact class labels, including OPEN.

2026-10-13: Recollect PR61 publication metadata through the existing live GitHub
witness collector, verify the original pinned plan and bundle, then replay raw
pages. Compare against the previously pinned condition artifact only as a
cross-source diagnostic, not as prospective evidence or a source for input
imputation. No outcome labels or fit operations belong in the new module.

## Context and Orientation

Use the isolated checkout `kra-analysis-race-card-pdf`; the owner's original
`kra-analysis` checkout is a read-only raw archive. Original plan and bundle are
in `.cache/autoresearch/race_card_pdf_bundles/20261009T165933.854898Z_51a041eda9e6/`.
The plan hash is `0ac4a309d07901d6f4da8c4503c937fee9529fb5e05871cfdcd5252116a52be0`;
the bundle hash is `8061a185401bf72c4bfee2751529acb164b695eb2985dbf4d6a43e187a8ecdd6`.
PR61 published their hashes before the original race cutoff. "Cutoff" means
30 minutes before the original API start time, in Asia/Seoul. An archive timestamp
alone is not independent proof that information existed then.

`prerace_hash_witness.audit_archive` validates the publication chain, and
`kra_race_card_pdf_replay.replay_entry_pages` checks pagination, hashes and source
identity. `shared.kra_entry_sheet.build_entry_snapshot` checks the complete roster.
The old condition artifact is
`.cache/autoresearch/condition-form-research-20261013/run-2/conditions.json`, hash
`818f0be674ef148b9c83e46192a52686be1e5ba2805b5daf8c601134aaaa6123`.
Its labels are retrospective official HTML headers; they cannot establish
pre-race availability. The original archive covers 28 races, not a complete
future national population. Include the race later reported void.

## Plan of Work

Add `packages/scripts/autoresearch/prerace_conditions.py` with a pure
`project_conditions(rows, *, meet, race_date, race_no, collected_at)` function.
Validate roster, parse distance as a strict integer from 500 through 5000 and
class against the existing exact class grammar, and report unknown per field on
missing/invalid/conflicting values. Add a CLI that verifies the original pinned
archive, uses a fresh publication witness, and writes an exclusive report with
source evidence, per-race availability and condition comparison. Add tests in
`packages/scripts/autoresearch/tests/test_prerace_conditions.py` and include them
in Scripts Checks. Record actual findings in a research note.

## Concrete Steps

From the isolated repository root, run:

    PYTHONPATH=packages/scripts .venv/bin/python -m pytest -q packages/scripts/autoresearch/tests/test_prerace_conditions.py -o addopts=''
    PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.prerace_conditions --plan .cache/autoresearch/race_card_pdf_bundles/20261009T165933.854898Z_51a041eda9e6/input_plan.json --bundle .cache/autoresearch/race_card_pdf_bundles/20261009T165933.854898Z_51a041eda9e6/feature_bundle.json --archive-root /Users/coyasong/Developer/coyasong/kra-analysis --comparison .cache/autoresearch/condition-form-research-20261013/run-2/conditions.json --output-dir .cache/autoresearch/prerace-conditions-20261013/run-1

Run Ruff on new Python files, related replay/witness/condition tests, then inspect
`git diff --check` and staged files. Push with gh/git, attach the created PR, verify
required checks and normal merge eligibility. Never override failing required
checks. Existing dependency advisories must be compared and reported separately.

## Validation and Acceptance

All 28 original race identities and all original runners remain in the report.
Each field is observed only with unanimous valid selected-roster values. Tests
must reject boolean/float/unit-bearing distances, invalid classes, wrong date or
venue, duplicate gates, incomplete rosters and contradictory values. A different
race's condition must not contaminate the requested race. No final result field
may affect extraction. Report pre-race source availability separately from field
completeness, future-universe coverage, training approval and performance claims.
Comparison conflicts remain explicit; never silently substitute the HTML value.

## Idempotence and Recovery

The CLI creates a new output directory and refuses reuse. Failed network/audit
runs retain their partial evidence; retry with a new run directory. All raw
archives, models and prior experiment files remain read-only. No credentials
are read or stored by this audit; the live witness uses public GitHub metadata.

## Artifacts and Notes

The completed audit at `.cache/autoresearch/prerace-conditions-20261013/run-1/report.json`
has SHA256 `81a4221a2429ec93155c5c41c9d28c1f1a099090236cc1e76b0374d5afd26fd3`.
Live PR61 metadata was retrieved at 2026-10-13T13:41:51Z and confirmed merge
`f794ffc24414117420004ca45bd8ae20a04385db` at 2026-10-09T17:08:16Z.

The Oct16 Jeju future probe was HTTP200/code00/zero rows
at 2026-10-13T13:30:35Z. Do not infer the availability of other venue/date pairs.

## Interfaces and Dependencies

Use standard Python, existing httpx witness collection, existing API replay and
roster validation, and the existing `race_conditions.CLASS` grammar. No new
dependency or training algorithm. The CLI prints only its report path, hash and
bounded counts; full evidence lives in the local report.

## Outcomes & Retrospective

The distance/class hypothesis now has a verified pre-race input source for the
original 28-race archive, not merely retrospectively available headers. No fit,
promotion or new accuracy estimate occurred. Both fields can be projected from
future API26 bytes using the same pure extractor, but future collection and
independent publication are still necessary. Historical feature availability
does not approve late-captured past form, prove an improved model or meet 70%.
Any new model still needs a separately reviewed fixed feature contract.

Initial plan created 2026-10-13 after examining the raw API26 schema.
Updated 2026-10-13 after actual archive replay and 235 passing regressions; only
publication of this validated increment remains.
