# Pre-race distance and class: original API26 archive

## Finding

All **28 races / 294 runners** in the original Oct10-11 API26 archive contain
unanimous valid race distance (`rcDist`) and exact race class (`rank`). Both
fields match the pinned retrospective official-header conditions in all 28
races. The raw API pages were bound by the original PR61 hash publication before
each race's original T-30 cutoff. This establishes availability of these input
values, **not a model improvement, training approval or a 70% success rate**.

The inventory is Seoul 21 / Jeju 7, Oct10 17 / Oct11 11. It contains no Busan
race. Thirteen exact classes and ten distances are represented, including
`국OPEN` and 1110m. The subsequently void `20261010_1_1` remains included.
There are zero missing fields, runner disagreements or cross-source condition
conflicts in this bounded inventory. That is not evidence of zero missingness
on all future cards or races.

## Method

The new `autoresearch.prerace_conditions` module verifies the original plan and
bundle hashes, recollects live GitHub publication evidence for PR61, and replays
the complete hashed API26 pages with the existing strict replay implementation.
It uses the original roster validator, checks all day/venue identities and
selects the target race locally because the API rc_no parameter is unreliable.
Every selected runner must contain the same valid condition value. Missing,
malformed or conflicting values produce a per-field unknown, without dropping
the race or copying a later HTML result into the input.

Distance and class are projected independently. This differs from the frozen
retrospective whole-header parser only in handling hypothetical partial fields;
no frozen experiment, M0/API27 model, hashed shared module or feature contract
was changed. `rank` is the race-class field in this entry-sheet schema, not the
finishing-rank label in a result table. No result rank, time, odds or labels are
used by the projection.

The comparison reads the already pinned historical condition artifact from
PR93; it is a cross-source diagnostic, not another pre-race witness and not a
fresh independent replay of all historical HTML. It cannot impute a value.
An additional standard-library-only check rehashed every referenced raw page,
recomputed selected-roster values and publication/cutoff ordering, and verified
the same full plan membership without importing the new projection module.

## Evidence

- Original plan SHA256: `0ac4a309d07901d6f4da8c4503c937fee9529fb5e05871cfdcd5252116a52be0`.
- Original bundle SHA256: `8061a185401bf72c4bfee2751529acb164b695eb2985dbf4d6a43e187a8ecdd6`.
- Comparison artifact SHA256: `818f0be674ef148b9c83e46192a52686be1e5ba2805b5daf8c601134aaaa6123`.
- New report: `.cache/autoresearch/prerace-conditions-20261013/run-1/report.json`.
- Report SHA256: `81a4221a2429ec93155c5c41c9d28c1f1a099090236cc1e76b0374d5afd26fd3`.
- Projection implementation SHA256: `6b8805e881a0da49fc7a3e77d3aef518175ba9f965715f85a57e8b14cef085a6`.
- PR61 merge: `f794ffc24414117420004ca45bd8ae20a04385db`, `2026-10-09T17:08:16Z`; fresh metadata retrieved `2026-10-13T13:41:51Z`.

The CLI command and recovery procedure are in
`docs/exec-plans/prerace-condition-inputs.md`. Artifacts include raw source paths,
hashes, original roster identities, per-runner raw condition values and the
publication witness; credentials are not involved.

## Verification

51 new tests cover strict numbers, exact classes, partial values, majority-vote
rejection, inconsistent rosters, date/venue isolation, irrelevant result fields,
original schedules, late publication, hash drift, non-overwriting output and
non-imputing comparisons. The related witness/replay/condition/M0/API27 suite
passed **235 tests**. Ruff lint/format checks pass for both new Python files.

## Forward Status

At `2026-10-13T13:29:52Z`, the unchanged M0 refresh still had no confirmed
Oct16-18 cards or frozen race population. A single bounded Oct16 Jeju API26
probe at `13:30:35Z` returned HTTP200/code00 with zero rows. This does not
confirm that there are no scheduled races, nor test every date/venue pair.
No future predictions or new 70%-goal evidence were created.

The earlier authenticated portal check confirmed API214 development approval
with a 10,000/day allocation and API26 development approval with 3,000/day.
These are allocations, not measured remaining requests. The portal login is
not proof that it caused API recovery. See the prior condition-form research
note for June recovery, the fixed 671-race experiment and its limitations.

## Decision

Distance/class inputs can be recovered from genuinely pre-race API bytes and
are worth carrying into a separately frozen prospective feature study. The
prior joint-condition 32 versus baseline 28 retrospective matches remain
hypothesis-generating only; this audit does not convert them into prospective
successes. Late-captured history remains unapproved for retrospective fitting.
Keep existing M0/API27 forecasts unchanged and preserve the full future race
universe when cards become available. No paid infrastructure was used.
