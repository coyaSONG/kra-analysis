# October Block Development Source Audit

## Decision And Scope

The completed October 16-18 block now has a separate, immutable development
link: all **50 races and 534 frozen runner appearances**, with the original
34-column candidate features and the observed unordered three-horse targets
kept in separate fields. It is **not an approved training dataset or recipe**.
No fitting, selection, model promotion, future registration or new accuracy
claim occurred. The 70% goal remains unmet. M0/API27's published 0/50 results
and original commitments are unchanged; see the full-block results report.

This was an offline audit, with **zero source-network requests**. The completed
block was not collected again and no new dates were silently substituted.
Original predictions, input reservations, source files and the pre-outcome
candidate matrix were not overwritten. The new artifact is explicitly dated
after outcomes: 2026-10-18T11:53:35.653362Z. It is not backdated pre-race data.

## Checks And Findings

| Check | Evidence | Interpretation |
| --- | --- | --- |
| Full frozen identity join | 50 races; 534 unique race/gate/horse keys on each side | No row loss, duplicate expansion or subset selection |
| Sealed feature reproduction | 18,156 / 18,156 cells equal; 24 original plus 10 memory columns | No outcome fields or post-race replacements enter features |
| Original entry sources | 50 manifests; 80 page references replayed | Original hashes, rosters, page clocks and packet sources agree |
| May extension source replay | 2,529 supported rows: 1,528 plus 1,001 | Both frozen API seeds and three official archives replayed |
| Official receipts | 113 + 64 + 114 = 291, including regional lists | Hashes, bytes and local completion clocks checked by existing replay |
| Memory reconstruction | All 534 rows and the recent-history ledger agree | Existing fixed transformations reproduced without tuning |
| Baseline history | 8,994 derived rows hash-checked | Raw baseline lineage not yet replayed in this audit; approval remains blocked |
| Result observations | 530 ranked; four runner observations retain `unresolved` evidence | Exclusion/stop/withdrawal notes preserved; no invented runner labels |

All 50 race targets remain `unique_top3_observed`, with three distinct target
horses in each frozen roster. The four unresolved **runner** observations do
not mean four pending **race** targets. They retain original exception notes,
source hashes and timestamps; no runner or race is excluded. The artifact
contains race-level targets and raw result observations separately, without
approving a runner-level training-label policy.

The original candidate was materialized at 2026-10-15T12:52:19.454815Z.
The historical extension replay uses the earlier memory materialization time,
2026-10-15T12:33:27.233765Z, as the local source-clock bound. The existing
candidate validator also rechecks entry availability, original history
availability/publication bound, packet materialization and per-race cutoffs.
Its historical creation timestamp is used only to reproduce and compare old
values, never to claim a new timely prediction or replace the old matrix.

These checks establish the described local October-source lineage, **not**
that October-collected versions were available before the historical May
races. Complete career history and independent historical event-time
availability remain unverified. Baseline raw source and original recency
lineage must still be replayed before any whole-dataset training approval.

Missingness is unchanged: rating is absent for 32/534 appearances (6.0%);
each of four recency fields is absent for 79/534 (14.8%); older-career form
is absent for 144/534 (27.0%). Missing flags are preserved. These counts can
overlap and must not be summed as disjoint missing runners. Zero condition
contrast remains distinct from missing similar-history support. No imputation
rule, threshold or feature selection was chosen from these outcomes.

## Verification And Artifacts

The existing candidate-input, condition-memory, observed-history-seed,
official-history-support and history-gap suites passed **117 tests in 1.13s**.
Five additional local negative checks rejected duplicate result identities,
missing roster members, pending targets, mismatched parent race IDs and
out-of-roster top-three IDs. A separate check compared complete identity
counters and feature rows with the original matrix and verified the saved
cohort hash. These checks do not replace the remaining raw-lineage audit.

Local companion: `.cache/autoresearch/audit_development_cohort_20261018.py`.
It refuses an existing output directory and uses the repository's append-only
JSON writer. It calls existing replay/projection functions, not collectors.
Development corrections distinguished shared regional list receipts from
race-detail identities and created the new destination directory before the
atomic save. Earlier attempts wrote no cohort or audit artifact. An initial
test invocation named a nonexistent test file and ran zero tests; the corrected
suite above is the reported result.

Archive: `.cache/autoresearch/development-source-audit-20261018/run-1`.

| Artifact | SHA256 |
| --- | --- |
| audit.json | 56255f1cca70ba40aabad36f852da5bb831d3e4aeb9a28fc2671c100cd844d37 |
| development-cohort.json | c25db29f0ba78cd3e7ab49c04950fcde3f3a12686ce4aad1ba69b33fb2616e03 |
| independent-check.json | ad134cf1f5235a3c6ef4a5328744c9a5f1adb2f8abf48517c36aed8cfd9e2486 |
| Local companion | c7b2515d1c2a45002be2bcd44968bb2e4b91e3227e1e9820e330ace20e270f9b |
| Original feature matrix | 7277897731011c64706f427cd7733444a5450767d312dabe8293a67c35a788a1 |
| Selected outcome version | 0cf7be483e1089ba55db78f70c51c9a6dbcaf8738847460f469ee11901ac0cbb |

The audit pins the three original public commitments again. Raw sources,
runner data and credentials remain local; this change publishes findings only.

## Next Work

Finish baseline-history and original-recency raw lineage checks, then specify
and review one fixed same-learner, same-cohort 24-versus-34-column training
recipe, including missingness and exception handling. Retain distance/class
support diagnostics as hypotheses, not performance substitutes. Do not make
automatic recipe approval or production promotion contingent merely on a
successful join. No approved recipe was added to the training review registry.

This block is development data once used for learning or model selection.
It cannot independently validate such a candidate. Any improvement claim needs
a separately preregistered future complete population, timely frozen inputs
and published single-combination predictions. Do not reset this block or
repeatedly tune its 50 outcomes. Result corrections require new linked versions,
never overwriting this development link or its selected outcome source.
