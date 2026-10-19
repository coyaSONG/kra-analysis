# A24 and B34 prospective inference and publication

The PR113 stored models now have a local inference and public-commitment path.
No fitting, parameter search, model promotion or future registration occurs in
this implementation. The registry at
`data/contracts/condition_forward_reviews_v1.json` deliberately contains no
approved studies. New official schedules and a separately reviewed prospective
protocol are required before a real attempt can start.

This implements the inference readiness gate in
[the PR113 future validation plan](2026-10-19-condition-development-results.md#future-validation-draft),
not an independent validation result. The target remains one exact unordered
three-horse combination per race over the complete frozen population, with a
70% goal. A24 remains the reference and B34 the candidate; neither is promoted.

## Frozen models

The files in `experiments/2026-10-19-condition-training-v1/` are unchanged:

| File | SHA256 |
| --- | --- |
| A24-model.json | 69f655fd005b59313d0a23dbf44759510c937ef403e8ac4fd844ea67494d635e |
| B34-model.json | c03972a447c2a36603717a7107b751f23d0fff08cb204565b68215f955ef16e0 |
| receipt.json | 3587c948913c82cc9c0b8c5e64161ef29794ed22a80d08425300e924834aa96e |

Inference uses the existing `condition_training_model.score` and `select`
functions. Missing numeric values use the stored medians, followed by the
stored scaler and coefficients. Scores descend; ties use numeric gate then
numeric horse ID. The three selected distinct IDs are serialized in ascending
numeric order. Both arms consume the same complete identity ordering, with
the first 24 columns for A24 and all 34 for B34. The numerical adapter, typed
feature reader and candidate matrix builder must retain the exact code hashes
from the training receipt. No estimator or preprocessing fit is called.

Adding new scripts changes the live implementation fingerprint intentionally.
The historical training approval/receipt is not rewritten to match it. Its
one-fit-per-arm lifetime budget remains consumed.

## Separate protocol approval

After the new code is normally merged, run the read-only inspector from the
isolated research checkout:

```sh
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.condition_forward inspect
```

The returned `runtime` binds all non-test scripts, dependency lock/config,
Python/library/CPU/thread environment, model hashes and fixed policies. Use
that exact object in a new protocol. Inspection does not create or approve it.
The registry, protocol and every fingerprinted implementation file must agree
with both local HEAD and fetched origin/main when admitted. Do not update the
environment during a registered block; preserve its checkout for later replay.

Create canonical JSON using `restricted_cohort.encoded` for both registry and
protocol. Save the protocol under
`docs/research/protocols/`. The protocol fields are:

| Field | Required content |
| --- | --- |
| format_version | `condition-forward-protocol-v1` |
| study_id | Unique lower-case alphanumeric/hyphen ID, at most 80 characters |
| created_at | Actual timezone-aware registration time, after the stored-model receipt and before every cutoff |
| race_dates | Sorted unique YYYYMMDD dates after the October 16-18 development block |
| runtime, policies | Exact inspector runtime and `condition_forward_contract.POLICIES` |
| horizon, sample_size_rationale | Explicit fixed horizon and rationale chosen before future outcomes |
| uncertainty, stopping | Explicit race/week-dependence-aware uncertainty and stopping methods |
| prediction_failure_scoring | Exact full-population treatment of missing, invalid and late predictions; never silently drop races |
| prior_block_history_policy | Whether/how already available prior-block results enter reviewed histories; no within-block updates |
| races | Sorted complete race IDs, each with `feature_cutoff_at` and full `roster` of integer `chul_no` and canonical string `horse_id` |
| schedules | One `{path, sha256, race_date}` capture-manifest pin per registered date |
| packets | `{path, sha256}` pins for every pre-race 24-column feature packet |
| memory | `{path, sha256}` pin for the label-free native condition-memory table |
| source_receipts | Nonempty unique `{path, sha256, available_at}` pins covering all reviewed original source evidence |

Each packet uses the existing candidate-builder schema: `race_id`,
`feature_cutoff_at`, `materialized_at`, `target_outcomes_loaded: false`,
`api_source.available_at`, `history_source.available_at`,
`history_source.public_existence_bound_at`, and complete `feature_rows` with
gate, horse ID and exactly the 24 base features. Memory uses `created_at`,
`target_outcomes_loaded: false`, `training_approved: false`, and the native
memory `rows` consumed by `condition_candidate_inputs.build`. Retain all source
URLs, collection times, raw bytes, hashes, missingness and identity links in
the pinned original evidence. All inputs must already exist by protocol creation.

An owner-authorized reviewer must inspect the exact upstream source-to-feature
derivation and availability evidence, not merely set flags on a feature table.
The code replays raw national/regional schedule captures, verifies pinned raw
bytes and clocks, full race IDs, official runner counts, rosters, column types
and missing flags. It does **not** independently regenerate every historical
API/memory feature from those raw receipts or authenticate the official source.
That source-closure review is an explicit admission requirement. Unknown source
availability blocks review; it never means no races. Statistical-method strings
must be substantively reviewed; nonempty text alone is not scientific approval.

Publish the exact protocol in a normally merged PR before the first cutoff.
Then add a separate reviewed record to `approved_studies` and normally merge it:

```json
{
  "study_id": "REGISTERED-ID",
  "race_dates": ["REGISTERED-DATE"],
  "protocol": {"path": "docs/research/protocols/REGISTERED-ID.json", "sha256": "EXACT-SHA256"},
  "protocol_publication_pr": 123,
  "reviewed_at": "ACTUAL-REVIEW-TIME",
  "reviewer": "AUTHORIZED-REVIEWER",
  "raw_source_closure_reviewed": true,
  "label_free_inputs_reviewed": true,
  "protocol_reviewed": true
}
```

This is a schema illustration, not a usable approval or proposed date/PR.
Registered dates cannot overlap any previous registered study, including a
failed study. Never delete an old registration or reset its population to retry.

## Execution and publication

After approval and normal merges, replace `REGISTERED-ID` with that exact ID:

```sh
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.condition_forward run --study REGISTERED-ID
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.condition_forward verify --study REGISTERED-ID
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.condition_forward stage --study REGISTERED-ID
```

`run` reserves the pair once in the common Git directory's
`condition-forward-attempts/<study>/`, shared across worktrees. It preserves
the original registry snapshot and complete race IDs. It makes two bounded
GitHub requests with no retry to verify the exact merged protocol bytes, then
replays local sources and scores both arms without fitting. It saves
`matrix.json`, `paired.json` and `receipt.json` under
`.cache/autoresearch/condition-forward-v1/<study>/`. The whole block must finish
before its earliest scheduled start minus 30 minutes. There is no caller-supplied
clock or alternative output directory. Failures consume the attempt, retain
full-population failure records and prohibit regeneration.

`verify` is repeatable and read-only. It rechecks model/input hashes and
deterministically recomputes the same stored scores for comparison, never
replaces predictions or fits. `stage` writes only those exact paired bytes to
`docs/research/commitments/condition-forward-v1/<study>/paired.json`. Existing
different bytes are never replaced. Late staging is recorded as failure.
New unrelated registrations do not invalidate the preserved registry snapshot,
but changes to this study, its sources, code or environment block replay.

Staging is **not publication**. Commit the staged file, run tests and required
checks, push and normally merge its PR before the first cutoff. Do not force
a failing merge or backdate a missed deadline. Then record the external proof:

```sh
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.condition_forward witness --study REGISTERED-ID --pull PREDICTION-PR-NUMBER
```

Each witness makes at most two bounded GitHub requests, pins the immutable
merge commit rather than the current branch, and preserves raw responses,
response hashes, document bytes, retrieval time and a report. It verifies the
repository, main target branch, PR identity, merged state, file path, blob
hash and exact local prediction bytes. Only a server merge before the earliest
cutoff yields `published_before_cutoff`; a later merge yields
`published_after_cutoff`. Network or evidence failures yield
`publication_unverified`, never a fabricated timely success. Observation after
the race is acceptable only when the server merge itself was timely. Further
observations append a fresh directory and do not overwrite prior evidence.

Local filesystem and clock integrity remain trusted; GitHub establishes a
public existence bound, not source authenticity. Losing the common ledger or
using a new clone is not permission to rerun a consumed study.

## Evaluation boundary

This path does not load future targets or compute accuracy. Local completion,
staging and public existence are distinct states. Every artifact keeps
`actual_fit_count: 0`; publication reports keep the 70%-evidence and promotion
flags false. Timely publication is necessary, not sufficient, for independent
evaluation under the separately registered protocol.

After official results arrive, preserve versioned originals and apply the
existing tie/cancellation/correction/conflict policy. Report each arm's full-
population hits, misses, pending and undefined counts, all four paired cells,
B34-minus-A24 percentage-point difference, race/week counts and registered
uncertainty. Pending results are never failures. If whole-population accuracy
is undefined, report that limitation rather than substitute subset accuracy.
One week cannot automatically promote a model. No new dates, horizon or
evaluation population are registered by this implementation.

## Verification

The new suite exercises actual stored models and raw synthetic official-page
replay through staging and mocked publication, with estimator, imputer, scaler
and training entry points trapped against fitting. It includes population and
runner omissions, changed bytes/columns/clocks, admission drift, concurrent
runs, symlinks, deadline crossings and late/invalid external evidence. Python
Checks runs this suite with Ruff lint/format. Locally, all 68 new tests and
253 combined inference/training-admission/candidate/schedule/witness regressions
pass (4.62 seconds for the combined run).

Local read-only replay of the original 534 consumed rows reproduced both arms'
50 canonical predictions and every saved score exactly (maximum difference
0.0). All 58 historical input hashes still matched. The training ledger still
contains only its original reservation, A24 attempt, B34 attempt and completion.
The real empty registry rejects an unregistered run before reservation or
network calls. Real future inference attempts and new real fits remain zero.
