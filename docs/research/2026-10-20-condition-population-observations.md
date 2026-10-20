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

## Verification

Synthetic tests cover full public-archive-to-original-HTML replay, missing
weeks and originals, corrupt originals/public documents, unverified semantic
claims, outside-scope observations, changed-date identity ambiguity, chain
reordering/truncation/correction forks, scope/clock failures and unchanged
input bytes. These are software checks, not future performance evidence.
