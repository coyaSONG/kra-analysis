# A24 and B34 prospective evidence boundaries

## Draft status

This is a proposed implementation contract supporting the
[preregistration draft](2026-10-20-condition-preregistration-draft.md), not
registration, execution approval, or a verified prospective evaluation.
Calendar dates, study IDs, rosters and actual N remain UNSET. The 12-week
duration and illustrative 600 races remain proposals, not enrollment or quotas.
No training, live inference, model promotion or M0/API27 contract change is
authorized here.

PR118 supplies arithmetic on normalized states, not evidence verification.
Before activation, a separate adapter must establish publication existence,
historical inference validity, target definition and population completeness.
These are four separate facts: proving one must not imply the other three.

## Current code and demonstrated boundaries

`condition_forward.verify_local()` calls the current `contract.admit()`,
compares the current runtime and rejects a local `failure.json`. That is an
operating gate for new inference/publication. It is not a historical evaluator.
`condition_training_admission.implementation()` includes non-test Python
source under `packages/scripts` as well as dependency/project files. Even
adding evaluator code can change a later runtime relative to a past protocol.

`condition_forward_publication.replay()` independently checks archived GitHub
responses, merge metadata, exact document bytes and their hashes. Four new
synthetic cases demonstrate that runtime drift, a missing or damaged local
paired file, and a later failure marker can make current verification fail
while the original publication archive still replays. These cases establish
only archived public existence and timing, not historical inference validity,
an outcome, population completeness or a hit.

The result observer's `void_reported_no_top3` retains
`official_finality_verified=False` and `settlement_policy_verified=False`.
The existing synthetic void test now asserts both boundaries. This observer
reports API void text with blank HTML results; it does not independently
establish an official whole-race no-target determination.

## Historical replay proposal

Keep the live gate unchanged. A new read-only evaluator must select exact
historical evidence rather than use current HEAD, origin/main, registry or
installed packages as the historical truth. Preserve and bind:

1. Original umbrella and weekly protocol, reviewed registry version, separate
   approval and their publication/merge evidence.
2. Original implementation snapshot, code commit, dependency lock, environment
   manifest and the environment needed to replay frozen inference.
3. Frozen model and training receipt, source/input receipts, matrix, paired
   predictions, reservation, completion/failure records and local receipt.
4. Original prediction publication, exact merge-tree document and archived
   GitHub metadata, plus the selected attempt/submission ledger version.
5. New verifier code/environment, actual replay time and evidence references.

An environment manifest alone is not a preserved runnable environment.
Unavailable replay leaves inference validity unverified while retaining any
independently established publication facts. Do not refit preprocessing,
monkeypatch runtime checks, move current Git refs, or substitute newly computed
predictions. Acceptance of an independently preserved verification receipt
instead of replay would need explicit prior contract approval, not an ad hoc
relaxation after evidence is lost.

Late witness retrieval is not late publication. Verify exact bytes at the
original merge commit and compare the server merge time to the original
earliest block cutoff. Equality with the cutoff is late. Approval evidence
must also prove the applicable reviewed version existed in time; a current
registry entry cannot establish that retrospectively.

## Failure evidence and submission closure

Missing local files, damaged copies, network/authentication errors, current
runtime mismatch and conflicting completion markers do not prove an originally
absent, late or invalid submission. Verified malformed original public bytes
or a deterministic mismatch against the original inference contract can
establish invalidity, limited to the affected arm or shared envelope.

To prove absence, bound the claim to accepted submission slots, not the whole
internet. Before execution, the contract must bind the obligation, cutoff,
repository, document path, arm and a unique publication PR or a finite permitted
candidate set. The authority key must bind umbrella/week and attempt across
study names and clones, not just a local directory. After cutoff, source-backed
closure must cover every permitted slot and preserve the full ledger version.
An arbitrary late PR does not disprove another timely accepted PR.

The current per-study attempt reservation and caller-selected witness PR do
not provide this closure. Prefer one prebound publication PR per weekly pair;
this is a proposed admission change requiring separate review. A missing
weekly protocol also needs prior umbrella obligation and complete authority
history before absence can be established. No supplemental predictions may
be introduced to repair late additions or missed weeks.

Neither `closed=true`, a failure file, nor a hash chain alone proves closure.
Bind the selected sequence and ledger head to independently preserved witness
metadata or a reviewed public version so truncating the tail cannot silently
select an earlier state. The existing trust model relies on archived GitHub
HTTPS metadata, hashes and cooperative preservation. It is not a defense
against an operator forging every local witness and source record.

## Separate target admission

Preserve original observation IDs, statuses, raw sources and policy hashes.
Add an A24/B34 target-admission policy with its own hash and parent observation
references; do not change the historical M0/API27 classifier.

| Evidence | Proposed target state |
| --- | --- |
| Verified unique top three under the selected observation version and identity/roster checks | Unique target |
| Missing, conflicting, ambiguous or identity-unresolved results | Pending evidence |
| `void_reported_no_top3` alone | Pending evidence, reason `void_report_only` |
| Explicit official whole-race cancellation/void establishing no target, with exact identity, scope, version, time and no unresolved contradiction | Undefined target |

A reviewed official status field or explicit official notice can supply the
no-target evidence; a second agency is not inherently required. Individual
withdrawals, postponement, disappearance from a schedule and blank ranks do
not establish it. A unique observed target need not claim perpetual settlement
finality. Later corrections create linked versions without replacing originals.
Prediction failure plus an unknown result remains pending; an established
undefined target remains undefined rather than becoming a miss.

## Umbrella completeness ledger

Keep each weekly execution protocol immutable. A separate append-only ledger
records the umbrella's full accountability population, including missed weeks,
late-added races and schedule/identity exceptions. A minimal proposal uses
one pinned umbrella document and one ordered event file, not a new service.

Each event needs schema version, umbrella hash, sequence, previous-event hash,
event type, week ID, an immutable enrollment slot ID for race events, actual
recording time, official effective time when known, hashed source references
and payload. Corrections additionally refer to the superseded event. Proposed
types are inventory, enrollment, execution binding, race change, identity link,
week closure and correction. Replay verifies referenced evidence rather than
trusting a status field.

An enrollment slot represents one physical race; official date/venue/number
identities may acquire aliases. Officially established renumbering preserves
one slot. Cancellation followed by a distinct replacement keeps two slots.
No heuristic joining by similar name, distance or runners is acceptable.
The same postponed race appearing in a later week must not receive a second
attempt or count twice. Admission must check this before execution as well
as evaluation. Ambiguous identity or reuse of a canonical race ID blocks
projection to PR118's race-ID interface; never invent a fake race number.

Missing weeks remain obligations. Later reconstructed full official inventories
may establish completeness even when predictions failed. Late additions enter
the exception ledger without changing a consumed protocol or retroactively
invalidating every earlier valid prediction. Races moved beyond the study end
remain enrolled, with unresolved outcomes pending at the fixed snapshot.
Cancellations remain visible; affirmative official evidence is required for
a zero-race week. Neither empty API responses nor absent protocols prove zero.

Completeness requires every expected week/date/venue scope to be accounted for,
full official inventories or affirmative no-race evidence, reconciled changes,
resolved physical identity and a verified selected ledger head/version.
Prediction success and result availability are separate from completeness.
If the number of races in a missing scope is unknown, report known ledger
races and unresolved scopes with full denominator null. Do not use a synthetic
pending race, the planning number 600 or a known subset as the full denominator.

## Adapter and acceptance requirements

The future read-only path should accept an exact analysis-manifest path/hash
and a new output location. It must replay ledger/identity evidence, historical
prediction evidence and selected raw result versions before constructing
PR118 inputs. No caller switches for verified population, proven absence,
confirmed void, ignored runtime mismatch or latest/favorable result version.
No fetching, collection, Git-ref changes, inference, fit, staging or publication
inside evaluation. Missing closure evidence needs a separate source-preserving
collection procedure; the evaluator cannot manufacture its own justification.

Ordinary scoped missing evidence yields pending. Proven original contract
violations yield scoped failure. Invalid root manifests, policy hashes,
ledger forks or structural identity conflicts block evaluation; do not hide
all exceptions as either failure or pending. Preserve PR118's explicit
`normalized_input_arithmetic_only_not_prospective_evidence` scope inside the
outer report, whose provenance establishes the evidence checks.

Before activation, test immutable original-snapshot replay across current
code/package/registry drift; missing environment; late or wrong-version approval;
lost copies versus malformed originals; multiple publication candidates;
missing or conflicting closure; renamed studies/clones; crashes at every
reservation/output/completion/publication boundary; cutoff equality; per-arm
failure; reported void versus explicit whole-race decisions; unchanged top
three with other source conflicts; missed/partial weeks; late additions;
cross-week identity changes; ledger forks/truncation; linked corrections;
and read-only traps with unchanged original file hashes.

Horse-ID padding must be normalized only through verified roster identity,
not blind integer conversion. PR118 compares string sets while rejecting
numeric duplicate IDs; the adapter must bridge source representation without
losing original bytes or accepting collisions.

Two integration properties are required: current checkout changes cannot
rewrite historical judgments, and removing evidence cannot by itself create
a proven prediction failure. The tests added here demonstrate narrower
existing publication/observer boundaries, not these complete adapter properties.

## Review and validation record

The owner-authorized Chrome ChatGPT conversation
[methodology review](https://chatgpt.com/c/6ad0d05d-5b08-83e8-b4b5-5252f401bb4d)
was used for follow-up review. Pro was selected in the UI. The follow-up was
submitted on 2026-10-20 and the completed answer was read by 14:39 UTC without
stopping generation or requesting a short answer. The conclusions above are
a synthesis checked against the local code, not a verbatim transcript or an
independent audit of local raw archives. The consultation expressly withheld
activation approval and any PASS claim for an unimplemented adapter.

Local focused validation after all assertions were added: 188 tests passed
in 5.75 seconds across forward inference, outcome accounting, versioned
observations and historical M0 evaluation. Ruff lint/format and whitespace
checks passed. Stored model and M0/API27 commitment hashes matched their pins;
the approval registry remained empty.
No production source, frozen model, registry or historical commitment changed.

The bounded schedule check at 2026-10-20T14:29:58.025281Z made four official
schedule requests, all HTTP 200. Raw and parsed content still matched the
previous October 16-18 schedules. Capture:
`.cache/autoresearch/published-card-monitor/20261020T142958.025281Z_d5f068af6748/capture.json`;
review SHA256: `6b6db65751bd02ac323144ee3a5c275d4991fff9d44eae32bbf92e12d2b9c124`.
There were no API/result calls or retries: no future schedule-anchored units
were available. This is not a no-race finding. No additional poll was needed
while preparing this contract.
