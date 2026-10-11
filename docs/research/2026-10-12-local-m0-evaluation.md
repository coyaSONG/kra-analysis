# Local M0 Whole Block Evaluation

The fixed M0 archive can now be compared with versioned official results through
a read-only evaluator. It does not rerun collection or inference to fill missing
predictions. Historical October 9-11 outcomes are rejected for the October 16-18
series before any prediction comparison. **No actual future performance is
available yet; the 70% goal remains unverified.**

## Evidence Boundary

The evaluator accepts one explicitly selected commitment and its SHA256. It
checks the original contract, model, fit receipt, declared dates, complete study
membership, original input pages, stored scores, predictions and read-back hashes.
It never calls the existing observation helper that would create missing receipts.
An unbound newer prediction cannot silently enter an older snapshot.

The optional publication path fetches a merged PR and its exact document bytes
from the live GitHub API using the existing publication verifier. The document
must be the selected commitment itself, not a source-code PR or a document that
merely mentions the model. The merge time bounds existence of the committed
bytes under HTTPS metadata and hash-preimage assumptions. It must be before the
block's first cutoff to verify the complete population and before each relevant
prediction cutoff. Local observed times must also be consistent with publication.
Equality at the cutoff is late. A later publication does not retroactively prove
an earlier deadline.

There is no CLI option to approve timing, change dates or the model, move the
clock, or load a hand-written witness JSON. One selected witness per report is
supported; combining multiple incremental publications remains future work.
The owner and local filesystem remain trusted to operate the declared canonical
series without hidden alternative roots or deleting submissions. This is not
tamper-proof storage, a database registration receipt, or proof of publisher
finality. A GitHub witness cannot authenticate the truth of arbitrary local clocks.

The result adapter, its policy and all eleven dependency hashes are pinned to the
PR83 implementation. The fixed dependency-map digest is
`2d9f1a7aeb847048c371408aad35ac52b170526a0871acaec21fcba538d1bb3c`.
Changing
that policy requires explicit review rather than silently changing a result
definition during this series. All selected result source bytes are replayed;
API214 capture completion, combined API26 binding availability and HTML capture
times must be at or after the scheduled start and no later than
the evaluation time. Earlier versions remain available when corrected outcomes
produce new explicitly selected reports. Do not select a favorable older result
version after inspecting model matches.

The actual API214 completion comes from its hash-pinned capture manifest in the
selected seed inventory. A later API26 binding cannot conceal an early API214
response. API26 itself may precede the start; only the actual result observation
and combined availability must satisfy the result timing gate.

## Full Population Metrics

Each frozen race remains in one of four states: verified hit, verified miss,
pending evidence, or undefined target. For a unique observed top three and a
verified pre-cutoff packet, exact equality of the unordered IDs determines hit
or miss. An absent canonical prediction after its deadline is a miss when the
population is independently bound and a unique outcome is available. Corrupt,
unbound or insufficiently witnessed predictions stay pending, never disappear.
Explicit void observations are undefined targets, not invented binary failures.

Let N be the complete verified frozen population, H confirmed hits, F confirmed
misses, Q pending evidence and D undefined targets. All counts retain the full
membership. The exact rate H/N is emitted only when the population is verified,
every target is defined and Q=D=0. The selected-version threshold flag checks
that rate against 70%; it is not a confidence statement about future races.

The interval [H/N, (H+Q)/N] is emitted only when all targets are known to be binary
and the remaining uncertainty is evidence. It is not a confidence interval.
Unknown outcomes may turn out to be void or otherwise undefined, so their
presence suppresses this interval too. If the full three-date block or its
pre-cutoff publication is unproven, the primary denominator, rate and bounds are
null. `local_combination_match_diagnostic` can show a local match without turning
it into a verified hit. No resolved-only rate is produced.

Extra result races are visible and block population verification. The result
inventory cannot replace the original frozen universe or repair a failed input
by rewriting the prediction roster.

## Actual Current Run

At **2026-10-11T19:38:00.835640Z** (October 12 KST), the unchanged forward command
queried the official pages for October 16, 17 and 18. All three remained
`awaiting_card`, with race counts unknown. Twelve new page responses were
retained. No study or prediction was created and no API26 credential was read on
that path. The canonical archive was reused, not re-rooted.

The selected commitment is now
`commitment_20261011T193800835644.json` under
`.cache/autoresearch/local-m0-forward/local_m0_20261016_18_v1`.
It has the same content hash as the earlier awaiting-card commitment:
`115a37b728c51da1f04b51dc51e455e26e2c7d4c193268c2fcf57a78040c321f`.
The adjacent `run_20261011T193800835644.json` records the newly collected source
paths and actual completion time; identical commitments alone do not prove a new
source observation occurred.

The actual evaluation at **2026-10-11T19:38:47.808448Z** returned all three dates,
zero known ledger rows, null denominator/rate/bounds and exit 2. This is an
incomplete forward evaluation, not a 0% or 100% result. The final local report is
`.cache/autoresearch/local-m0-evaluation-final.json`, SHA256
`0d8c06a9f8d606c257401976a67d216e9669c8964fd1453da3da23c644bc2be9`.

After the Pro-review fixes, replay at **2026-10-11T20:02:43.580937Z** produced the
same incomplete status in `.cache/autoresearch/local-m0-evaluation-final-v2.json`,
SHA256 `98f238552d928571b1bd8ba91e900c12440c7dfe8769e5ab34a3ee893678838b`.
This re-evaluates the existing commitment, not a new card collection.

Two internal replays at the same explicitly fixed diagnostic evaluation time
were identical, and all **36 canonical archive files** retained identical bytes.
The current inference contract still equals the original saved contract with hash
`ffd068ed7c507e2cf0bef63ed2dcbebf01fdcdd0e38d89c849d03d60c448f59c`.
The actual historical outcome plan with hash
`314056646885d6112bbd392dcd7f8a20c2a934b03b6ab788090a270ee02be898`
was rejected with `evaluation_historical_or_wrong_outcome_dates`.

## Reproduce and Verify

Run from the isolated research checkout:

```sh
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.local_m0_evaluation \
  --root .cache/autoresearch/local-m0-forward/local_m0_20261016_18_v1 \
  --model-dir .cache/autoresearch/restricted-models/20261011T125457.212167Z_4113cd1060f9 \
  --commitment .cache/autoresearch/local-m0-forward/local_m0_20261016_18_v1/commitment_20261011T193800835644.json \
  --commitment-sha256 115a37b728c51da1f04b51dc51e455e26e2c7d4c193268c2fcf57a78040c321f \
  --output <new-report-path.json>
```

When genuine future outcomes exist, add their pinned `--outcome-plan` and
`--outcome-plan-sha256`. For actual pre-cutoff publication, add `--publication-pr`,
`--publication-document` and a new `--witness-directory`. These must identify a
real published commitment; no such future prediction witness is claimed here.
Evaluation outputs and witness directories must be outside the canonical archive.
Reports use atomic exclusive creation and cannot replace older reports.

The final **250-test** regression run passed across the evaluation, forward,
versioned outcomes, seed, official history, publication witness, API214 and
schedule suites, including **29 new evaluation tests**, with Ruff lint/format
and diff checks passing. Source-backed synthetic
fixtures exercise schedule capture, API26 predictions, API214 results, official
HTML and GitHub publication validation through mock HTTP transports. Their
successful 4-race scenario is a software test, not real model performance.
Cases cover wrong publication bytes, cutoff equality, missing read-back,
tampered predictions, partial three-date blocks, absent submissions, historical
inputs, unknown/void outcomes, changed policies and forbidden archive writes.

## Completed Pro Review

The authorized ChatGPT Pro browser reviewed public PR84 head
`ecb1ea1159e3f75af948a26ac2611770c43c7c29`. Its completed response took 9m 28s;
generation was not interrupted. It did not read local archives or run our tests.
It identified two P2 issues: unpinned outcome dependency hashes and combined
availability hiding an early API214 capture. Three changed-dependency cases and
the early-API214 case failed before the fixes; the inverse valid timing case
already passed. All five pass after the fixes. The full dependency map now needs
explicit approval on change, and actual API214 capture time is checked separately.
An additional test verifies that recovered prediction content still matches the
selected commitment pin. All 36 canonical archive files remain unchanged after
repeat replay, and historical outcome dates remain rejected.

Pro reported no other concrete merge blocker under the declared trust assumptions.
That is neither a review of the subsequent fixes nor approval of model accuracy.

## Remaining Research Work

Collect the genuine next cards and preserve the fixed predictions before their
deadlines. Publish their exact commitment bytes before cutoff where possible.
Build result requests from the frozen future universe, not from whichever history
groups happened to return results. Collect and pin post-race source versions;
define and record a consistent correction observation schedule. The read-only
evaluator does not automate those collection or publication operations.

This work implements the evaluation half of the earlier completed Pro advice and
the additional review above. No paid infrastructure, new fit, model promotion, or production
configuration change occurred. Real prediction success and the remaining gap to
70% await an eligible future full-population evaluation.
