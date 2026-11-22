# A24/B34 population observation replay

This is implementation preparation for the unregistered prospective draft,
not an enrollment, approved calendar, complete population, or scoring adapter.
No real scope JSON is created. A24/B34 models and their consumed fit attempts
remain unchanged. The 70% objective remains unmet.

## What is now observable

`condition_population_ledger.py` reads a SHA256-pinned local manifest and
replays two original GitHub publication archives: a declared scope and a
selected journal version. It uses the existing archived-publication validator,
including canonical document bytes, repository, merge metadata and clocks.
This proves the selected public bytes under the existing cooperative-operator
archive trust model. It is not an independent malicious-archive attestation.

The journal contains ordered events, each bound to the scope hash and previous
event hash. Sequence/count/head, recording clocks, evidence hashes and correction
ancestry are checked. Corrections retain their parents; none deletes an event.
A selected public head detects truncation relative to that selected version,
but cannot establish that no newer version or missing branch exists.

Inventory events bind the exact capture hash. The reader validates canonical
source URLs, capture/source clocks, filenames, byte counts and original HTML
hashes before using the existing schedule parser and reconciliation logic.
Missing local originals remain visible as missing; corrupted pinned originals
block replay. Source parse failures remain unparsed observations. None becomes
affirmative evidence that no races occurred.

Every declared week/date/venue scope remains in the output, including weeks
without inventories. Observed canonical IDs are unioned across snapshots:
later absence, changed dates or apparent renumbering cannot remove earlier
observations. IDs outside the declared scope are retained separately for review.
The observed identifier count is explicitly **not physical-race N**. Conflicting
national/regional observations remain in their original reconciliation reports.

## Limits that remain gates

All outputs keep `full_population_verified=false`, `denominator=null`,
`usable_for_scoring=false` and `counts_as_70_percent_evidence=false`.
`observations_replayed` means the selected evidence was processed, not that
all inputs, inventories or obligations were present or complete.

Enrollment, execution-binding, change, identity, closure and correction events
are retained as **unverified assertions**. This reader does not admit reviewer
claims, merge physical identities, reassign predictions/attempts, certify
no-race days, close a week, choose an authoritative latest journal, or invoke
the outcome reducer. A public `complete=true` cannot supply any of those facts.
An inventory event allows only its capture reference, not a caller-provided
race list or completeness flag.

Before activation, further source-backed policy and implementation must
establish complete calendar coverage, authoritative version selection,
physical identity, authorized semantic decisions and all original enrollment/
attempt bindings. Independently required are closed submission evidence,
raw pre-race source admission and target admission. The immutable weekly
contracts and original M0/API27 rules are unchanged.

## Observed limits of the published cards

An offline readback on November 22 compared the first archived complete card
for each of six fixed October-November windows to its immediate successor,
using the saved national and all three regional HTML sources. The original
snapshots contain 304 distinct scheduled identifiers (50, 50, 51, 51, 51,
51). In all five adjacent comparisons the later valid card shows none of the
earlier date labels or race identifiers: **253 previously observed IDs** are
not reproduced. The last 51 have no selected successor in this comparison.
This is observed display rollover, not cancellation, proof of no racing in
an earlier scope, or a count of physical races for any future protocol.
Positive observations must survive the rollover.

One additional [KRA Seoul result catalog](https://www.data.go.kr/data/15063950/openapi.do)
was preserved at `2026-11-22T13:21:32.716552Z`, HTML SHA256
`05d1334abf8fa1df9f369c40931a9a673bb511da7a1965e32ce9f79f8c5acac3`.
Its scope is Seoul only. The schema lists a cancellation field
(`noracefl`), division field (`divide`) and race code (`rcCode`), alongside
dated race and runner fields. The documentation does not establish that
cancelled races appear in actual results, that the code survives
renumbering, or that a page total measures physical races. No data
operation was called and entitlement was not tested.

All 31 preserved Seoul entry captures for those 128 races and 1,325
declarations agree with their original roster hashes. Every declaration
contains a dated race key and horse/gate identifiers. None has an
`rcCode`, `divide` or `noracefl` key. These keys are absent, not present
with empty values. Consequently the documented result-only race code
cannot, by itself, bind those original declarations to a rescheduled
or renumbered race. A dated join, whole-race cancellation or physical
identity change requires its own exact evidence. None has been admitted
from this catalog.

The exclusive local evidence files in
`.cache/autoresearch/schedule-rollover-closure-20261122/` are
`schedule-rollover-evidence.json` (SHA256 `f9cae6127864f70c57fbd442e0eb66711946de4c599cb812ef7d520c9261726f`),
`seoul-cancellation-source-registry.json` (SHA256 `2965d9913ec1f03eee42ceae67098b315f3edb6fbe683f29c0ed88d1015fce97`)
and `seoul-entry-result-join-readiness.json` (SHA256
`b872031161084e5b891480d8e30fa6e5dab9321708179f2c37bad69b8805f3f1`).
The original sources and fields were replayed without scoring or altering
any race. Synthetic two-sided reconciliation checks retain previously
observed IDs missing from a proposed list and newly listed IDs not yet
in the ledger. Even agreeing lists cannot certify their own completeness.
The focused and related local suite passed 185 tests.

## Reproducible interface

Run from the isolated research checkout with the existing environment:

```sh
PYTHONPATH=packages/scripts .venv/bin/python -B \
  -m autoresearch.condition_population_ledger \
  --manifest /absolute/path/to/replay-manifest.json --sha256 EXPECTED_SHA256
```

This command only reads local evidence and prints JSON. It performs no
collection, fitting, live inference, registration, outcome loading or writes.
A missing public archive reports `pending_publication`; malformed or damaged
pinned evidence reports `blocked` and exits 2. Missing captured originals can
coexist with other retained observations, always with unknown denominator.

The manifest has exactly `format_version=condition-population-replay-v1`,
`umbrella`, `journal`, and `snapshots`. Each publication reference follows
`condition_historical_publication.archive`: pull number, repository-relative
document path, document SHA256 and four path/hash archive pins. `snapshots`
maps capture SHA256 to a local `{path, sha256}` pin.

The scope document has exactly
`format_version=condition-population-scope-draft-v1` and `weeks`.
Each week declares unique `week_id`, `start_date`, `end_date` (YYYYMMDD) and
sorted venue numbers. Weeks must be consecutive Monday-Sunday calendar weeks,
with all four current venue IDs, plus any explicitly added venue IDs. This
structural check does not approve a duration or prove the venue list exhaustive;
the proposed twelve-week horizon still requires separate prospective approval.

The journal/event schemas and accepted event types are defined by
`condition_population_chain.py`. Each inventory payload is exactly
`{"capture_sha256": "..."}`, also present in `evidence_refs`.
No actual dates, race IDs, sample size or public scope are supplied by this
documentation; historical fixture dates in tests are synthetic only.

## Select one journal from a pinned inventory

For a caller that has archived more than one version, run the read-only
`autoresearch.condition_population_checkpoint` command:

```sh
PYTHONPATH=packages/scripts .venv/bin/python -B \
  -m autoresearch.condition_population_checkpoint \
  --index /absolute/path/to/checkpoint-index.json --sha256 EXPECTED_SHA256
```

The index has exactly `format_version=condition-population-checkpoint-index-v1`,
`evidence_as_of` (offset-aware timestamp), `umbrella` (existing public archive
reference), `journal_document` (one repository-relative journal document path),
`candidates` (path/hash pins of existing v1 replay manifests beside the index)
and `observation_gaps`. Each gap has `expected_at` no later than the boundary
and `status` of `not_observed`, `transport_error`, `auth_error`, `rate_limited`
or `archive_unavailable`. Use the same exact umbrella archive reference in
every candidate. The index is itself checked against the expected digest.

Verified candidates have exact public bytes for the same journal path,
provider merge and archive retrieval at or before the boundary, and valid
event chains. Sort by verified merge time, not list order, retrieval order
or review. Each version must strictly append to its predecessor and keep
earlier snapshot pins intact. Equal merge times, forks, removals, repeated
versions and changed pins block selection. A version merged after the boundary
cannot replace an earlier one. Missing candidate evidence, a version merged
by the boundary but retrieved too late, or a declared observation gap leaves
the selection pending rather than moving back to an older version.

`checkpoint_selected` means the rule selected one version **within this
index** and replayed its raw observations. The selected version can still
contain missing or conflicting captures; the original replay records them.
If its replay cannot run, there is no fallback. `pending_evidence` or
`blocked` exits 2 with no selected version. No result, approval or score is
used to choose the version. The command cannot prove that the caller knew of
all published versions, that the index is complete or prospectively approved,
or that any week is closed. Run before any separate official scope and
physical-identity reconciliation. Denominator and scoring remain unavailable.

## Verification

Synthetic tests cover full public-archive-to-original-HTML replay, missing
weeks and originals, corrupt originals/public documents, unverified semantic
claims, outside-scope observations, changed-date identity ambiguity, chain
reordering/truncation/correction forks, scope/clock failures and unchanged
input bytes. These are software checks, not future performance evidence.
The final local related regression run passed 408 tests in 41.00 seconds,
including 51 new chain/observation tests; Ruff check and format-check passed.

## Completed design consultation

The authorized Chrome ChatGPT Pro consultation in
[the existing research conversation](https://chatgpt.com/c/6ad0d05d-5b08-83e8-b4b5-5252f401bb4d)
finished after 23 minutes on 2026-10-20, and its full response was read.
It reviewed the supplied design and public PR120/121 code, not local official
notices or execution of our tests. It is not independent implementation review
of this PR and not authorization to activate an experiment.

The implemented first stage follows its distinction between source-replayed
membership and completeness. A snapshot is a sequentially collected source
bundle, not proof that every page had one atomic effective instant. Runner
counts do not establish individual horse roster identity. Audit output identifies
the verifier/parser bytes and never promotes a public reviewer name or boolean
to accepted interpretation.

The next semantic-admission milestone needs a separately fixed authority
registry and policy, exact decision/source hashes, source locators and context,
reviewer identity and authority at the time, and publication evidence binding
the actual reviewed version. Capture, review, decision publication, ledger
acceptance and checkpoint clocks must be distinct; source effective time may
be earlier or later. Contradictions need explicit same-subject/scope correction,
not latest-wins. This stage is deliberately not implemented by the observation
reader.

Scope closure requires either a source-backed exhaustive scope listing or a
baseline with a demonstrably complete change history to a declared evidence
version, plus reconciliation of earlier observations. Repeated matching tables
or a search returning no more notices cannot substitute for that boundary.
No originally enrollable races, cancellation of all enrolled races and absent
results are three different claims; cancellation never erases existing records.

Later official identity corrections may join or separate components in a new
projection while retaining both original enrollments, aliases, protocols,
predictions, cutoffs and every consumed attempt. Record counts are not even a
guaranteed lower bound on physical N when duplicates are unresolved. A
component representative is not the owner of prediction authority. Attribution
requires a pre-fixed rule; no later successful prediction can rescue an earlier
miss or absent submission. Cross-week ownership and out-of-period postponement
must preserve original obligations. Preventing duplicate future attempts also
requires a separate execution gate, not just this read-only audit.
