# Select a public population checkpoint without looking at scores

Maintain this ExecPlan in accordance with .agent/PLANS.md. This is work
toward a future A24/B34 evaluation, not the registration of one.

## Purpose / Big Picture

The population observation reader replays a single supplied version of the
race journal. It cannot tell if the caller skipped a later, incomplete
version or supplied an alternative branch. Give the operator a read-only
command that selects one version mechanically from a pinned inventory and
calls that same reader. Reject attempts to drop earlier observations,
silently fall back to an older version, or use proof acquired after the
declared evidence boundary.

## Progress

- [x] (2026-11-22) Verify the current main, the empty weekly approval registry,
  the existing version reader, and the archived evidence of display rollover.
- [x] (2026-11-22) Implement the selection and raw-observation replay, keeping the selected
  checkpoint separate from research approval and complete-population claims.
- [x] (2026-11-22) Run end-to-end fixtures and related research regressions,
  including a local replay of all six original cards under fictional journal
  publications.
- [ ] Submit the small, validated change through the normal CI and merge path.

## Surprises & Discoveries

All 253 original identifiers in the first five adjacent comparisons of
the archived cards disappear in the next display. The journal must
accumulate positive observations rather than replacing a week with the
latest display. The public archive verifier already records both the
provider's merge clock and the actual local archive retrieval clock.
Neither clock can be inferred from a journal event's effective date.

## Decision Log

On 2026-11-22, choose the journal with the latest verified provider merge
among the supplied archived versions retrieved no later than a pinned
evidence boundary. Retrieval order cannot decide which version is later.
Reject tied merge clocks, repeated or short chains, divergent histories,
and modifications to earlier snapshot pins. Later appends must preserve
the exact earlier event prefix. A version merged by the boundary but
captured later, an inaccessible candidate, or a recorded observation gap
prevents selection. A genuinely later merge is recorded but cannot affect
the earlier selection. No review status or result is used. A missing raw
capture inside the selected replay is reported in that replay, without
trying an older version.

The input digest makes this view reproducible but cannot prove inventory
completeness or replace a separately approved rule and actual independent
authority. Do not fill in future dates, select an actual sample, approve
an umbrella, or infer that an empty cell means no races.

## Outcomes & Retrospective

The selector and command are implemented with the existing observation reader
unchanged. The 779 related tests passed, including 19 new selection cases.
The local original-byte fixture retained all 304 archived IDs, compared with
51 in the latest single display. With the last fictional publication
receipt absent, selection remained pending. These are population
observation replays, not six registered weeks or scored results.

An attempted collection of every test under autoresearch stopped at seven
import errors in existing single-combination materializer tests. Their three
missing selector diagnostic modules are absent from the unchanged base
tree as well. The related suite was run explicitly and the existing
required population check now includes the new test file; neither result
is a claim that the whole repository suite passed.

## Context and Orientation

`packages/scripts/autoresearch/condition_population_ledger.py` validates a
pinned replay manifest, one archived scope, one public journal version and
raw snapshot evidence. The journal is a linked list of hash-pinned events.
Its validator is `condition_population_chain.py`. Each capture refers to
archived official HTML. Same-day national and regional agreement is
valuable membership evidence, not proof of full scope. Today's inputs
and all A24/B34 and M0/API27 data and rules remain unchanged.

## Plan of Work

Add `packages/scripts/autoresearch/condition_population_checkpoint.py` and
its tests. Use one digest-pinned index listing the fixed journal document,
exact shared scope archive, independent evidence boundary, explicitly
missing observations and original v1 replay-manifest pins. Require the
replay manifests beside the index so snapshot paths are comparable.
Verify public archive bytes and clocks, then verify each timely
candidate's event chain and compare heads at previous prefix lengths.
Pass only the selected original v1 manifest to the existing reader. Its
observed IDs and missing evidence remain intact. The new summary cannot
emit a denominator, outcome count, authorization, or accuracy.

## Concrete Steps

Work in the separate research checkout. Run the new command with a
digest and a locally pinned input:

    env PYTHONPATH=packages/scripts .venv/bin/python -B \
        -m autoresearch.condition_population_checkpoint \
        --index /absolute/path/to/checkpoint-index.json --sha256 EXPECTED_SHA256

Use a fixture to supply archived merge metadata, scope and journal bytes
and original local HTML. Run:

    env PYTHONPATH=packages/scripts PYTHONDONTWRITEBYTECODE=1 \
        .venv/bin/python -B -m pytest -q -p no:cacheprovider \
        packages/scripts/autoresearch/tests/test_condition_population_checkpoint.py \
        packages/scripts/autoresearch/tests/test_condition_population_ledger.py \
        packages/scripts/autoresearch/tests/test_condition_population_chain.py

## Validation and Acceptance

Expect a selected digest and preserved scheduled observations for one
verified lineage even if the index and retrieval order differ from merge
order. Expect no selected version on missing or late prior proof, chain
forks or reductions, ambiguous merge times, changed earlier snapshot pins,
wrong scope/path or malformed pinned bytes. A post-boundary append and a
missing raw page must not repair the chosen earlier state. All states
remain ineligible for population closure and scoring. Verify the immutable
October commitment hashes and the empty weekly review registry.

## Idempotence and Recovery

The command reads only local files. It never retrieves a missing archive,
writes a replacement, tries another journal after a failed replay, or
re-runs a live collector. A later source correction requires a separate
versioned index at its own evidence boundary.

## Interfaces and Dependencies

Use existing `pin`, `archive`, `timestamp`, `chain.validate` and
`condition_population_ledger.audit` with no new dependency or runtime
service. No model, prediction, outcome, policy or registry is modified.

Revision, 2026-11-22: recorded the working selector, original-card replay,
and regression results. Added the case list to the existing population
CI step so future changes cannot omit the new tests.
