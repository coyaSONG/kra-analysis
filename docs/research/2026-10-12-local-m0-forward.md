# Local M0 Forward Research

## Result and Scope

A paid database is no longer needed to execute the existing frozen M0 as a
local research arm. The new command connects official national schedule capture,
whole-day population freezing, original API26 replay, fourteen input columns,
stored-model inference, exclusive prediction publication, read-back observation
and full-population reporting. B0 and its PostgreSQL contract are unchanged.

This increment performed **zero fits**, purchased no resources and changed no
production approval. It establishes execution, not accuracy improvement. The
old development M0 and M1 each scored 1/7 on already observed races; that is not
a performance estimate for the full 20-race M0 used here. The 70% goal remains
unverified and requires the complete frozen future population and outcomes.

## Fixed Protocol

The initial canonical series is `local_m0_20261016_18_v1`, covering October
16-18 nationwide. M0 is selected for API-only deployability, not demonstrated
superiority. There is no model search, automatic study alias, per-race arm choice,
overwrite option, or fallback to a different predictor. Invalid input remains
a missing prediction in the full denominator. A missing or invalid individual
runner never disappears so that the rest of the race can be scored.

The exact `full_M0_model.json` hash is
`0c0078fb513d4acc2695427475b91668f20441bfab1f4ce05e0418277c8bbb74`.
Its original fit receipt hash is
`70cf1f7de5a51ae68f4706b6349686276c6bf23978d37f116072bcd61a7ef69b`.
The original restricted training review, recipe, training IDs and unchanged
inference dependencies are checked. The original refit gate remains strict:
it now rejects the old corpus because result-collection code changed after its
review. Read-only portable-model admission does not relax that refit gate.

The contract is saved before source processing. Each date's full official
population must be frozen and locally read back before its earliest fixed T30
deadline. Every configured date stays in the report. The commitment separately
reports whether all three dates were frozen before the entire block's first
deadline; partial-date execution is not a replacement study.

For each unsealed race, an invocation attempts at most one capture, with a
60-second bound further limited by the remaining deadline. Processing follows
deadline order. The first validated input is pinned before scoring; retries
reuse it. A saved prediction occupies one series/date/race slot, never a slot
expanded with a different input or model hash. Resume verifies the original
model, inputs, scores, combination and original read-back record; it does not
fetch a newer roster for an occupied slot. Changed contracts are rejected.

Every successfully projected runner has a linear score; exactly three IDs are
selected by the existing score/gate/numeric-ID ordering, then stored in numeric
order as an unordered combination. These are not joint three-horse probabilities.
No PDF, result label, training-selection flag, `ilsu`, result odds or new history
feature enters this adapter.

## Actual Source Rehearsal

Two populations were exercised separately with the actual saved model and
original API26 bytes. No clock was moved backwards and no historical replay
was submitted as a prospective prediction.

| Population | Result |
| --- | --- |
| Original independently pinned API/PDF capture inventory | All 28 races / 294 runners scored through API-only inference |
| Existing reviewed feature reference | All 282 available reference rows exactly equal on identity and fourteen columns |
| Original full M0 consumed matrix | 209 x 14 transformed matrix matched; maximum absolute difference 0 |
| Original full M0 score reconstruction | Maximum absolute score difference 0; tolerance fixed to rtol=atol=1e-12 |
| Existing complete feature-reference combinations | All 27 combinations exactly equal |
| Separate dated national schedule, October 9-11 | All 50 races retained: 21 scored / 225 runners, 7 input conflicts, 22 missing inputs |

The 28-race inventory is not the national population. It uses each original
API26 roster and its original schedule for computation equivalence. Its IDs
must equal the complete pinned original input plan. The separate 50-race run
enforces the later captured official national schedule. Disagreement is retained,
not resolved by overwriting either source. Five schedule-time conflicts are
October 10 Seoul R2 and Jeju R1, and October 11 Seoul R3/R9/R10. Two runner-count
conflicts are October 10 Seoul R7 and Jeju R2. The 22 unavailable inputs are
October 9's 16 races and October 11's six Yeongcheon races in this specific
source inventory; this does not claim no other archives exist.

October 11 Seoul R8, previously blocked by the PDF name-prefix join, scores
successfully using API26 only. No outcome-based exclusion is used. Rehearsal
does not calculate accuracy: the full model was fitted after these targets.

Local ignored directory: `.cache/autoresearch/local-m0-rehearsal` in the isolated
research checkout. Original API bytes are read from the unchanged primary
checkout; no primary files are edited.

| Artifact | SHA256 |
| --- | --- |
| Original 28-race input plan | `0ac4a309d07901d6f4da8c4503c937fee9529fb5e05871cfdcd5252116a52be0` |
| Current actual national schedule capture | `b4bee247a67dd44cf28d09aca555d43fd3c6b7043f465ea631c783831678f57a` |
| plan-final.json | `619dfb72764a8ddb467047e3fd687b86f53cbb2d91d1c567d83ff2ed92985922` |
| report-final.json, both complete populations | `eb006739295828c934046e7d72be728f1952de7a021efeb886b3eadfc6860b0e` |

Earlier rehearsal versions are retained. The first attempt used an overly narrow
archive root and correctly failed all 28 manifest path contracts. The corrected
plan uses the original repository root for manifests containing repository-relative
paths; no originals or validation rules were rewritten to pass.

## Actual Next Card Run

The new live command completed at **2026-10-11T18:42:03.670335Z** (October 12
KST). All three dates returned `awaiting_card`, race count unknown, and exit
status 2. It retained 12 official-page responses. No API26 credential was read
on this awaiting-card path; zero future studies and zero predictions were created.
This is a tested unpublished-card path, not prospective execution success.

The canonical local archive is
`.cache/autoresearch/local-m0-forward/local_m0_20261016_18_v1`.
The contract hash is
`ffd068ed7c507e2cf0bef63ed2dcbebf01fdcdd0e38d89c849d03d60c448f59c`.
The first `commitment_20261011T184203670339.json` hash is
`115a37b728c51da1f04b51dc51e455e26e2c7d4c193268c2fcf57a78040c321f`.
It records all three dates as unknown and `complete_block_freeze_not_proven`.
The adjacent `run_20261011T184203670339.json` binds the source capture paths.

Do not create another archive root or delete this contract to bypass a conflict.
Use the same command and root when genuine cards appear. A later source/code
change requires an explicit prospective protocol amendment, preserving this
declaration and all observations; it cannot silently replace an occupied slot.

## Execution and Verification

Run from the isolated checkout with its existing environment:

```sh
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.local_m0_forward run \
  --archive .cache/autoresearch/local-m0-forward \
  --model-dir .cache/autoresearch/restricted-models/20261011T125457.212167Z_4113cd1060f9 \
  --api-key-file /Users/coyasong/.codex/secrets/kra_api_key
```

There is no CLI date, study, clock, model-hash or arm override. The model directory
must contain the exact admitted files. `run` also resumes original local records;
exit 0 means all configured days are locally complete, not externally certified.

```sh
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.local_m0_forward rehearse \
  --plan .cache/autoresearch/local-m0-rehearsal/plan-final.json \
  --plan-sha256 619dfb72764a8ddb467047e3fd687b86f53cbb2d91d1c567d83ff2ed92985922 \
  --model-dir .cache/autoresearch/restricted-models/20261011T125457.212167Z_4113cd1060f9 \
  --output <new-report-path.json>
```

Rehearsal is a separate command and cannot write prospective slots. Repeated
computation must equal the saved report; an existing output is not overwritten.
Focused regressions passed **206 tests**, including 29 new local-path cases.
Ruff lint and format checks pass. Remote checks are reported on the PR rather
than assumed from local results.

## Trust and Remaining Work

Files are published atomically without replacement under an exclusive process
lock. Post-publication read-back verifies complete bytes and binds their hash
to a local observation time. Lost read-back followed by a late retry is timing
unproven, not backdated success. This is **program-enforced non-overwrite**, not
tamper-proof storage or independent time. The local owner can alter/delete files,
start a hidden alternate root or change the clock. Laptop availability, off-host
backup and continuous scheduling are not guaranteed by this command.

Each run emits a commitment manifest binding the canonical contract, dates,
frozen populations, occupied prediction slots and observation hashes. Publishing
that manifest before cutoff could establish a hash-based existence bound under
the existing GitHub trust assumptions; the manifest alone does not prove that
publication occurred. This PR's protocol hash does not authenticate any future
prediction that has not yet been created. No PostgreSQL receipt is claimed.

Results, cancellations, ties and corrections are not joined by this increment.
Every unresolved race must remain in the complete frozen population; normal
outcome subsets cannot be reported as national accuracy. Missing valid timely
predictions cannot count as successes. Actual future collection, externally
bounded prediction evidence, full outcome reconciliation and a substantially
larger new training/evaluation corpus remain necessary for the 70% objective.

## Completed Pro Advice

The authorized [Pro research conversation](https://chatgpt.com/c/6aca2dc4-d2e8-83e8-acab-e85f281c27b7)
displayed a completed response with **10m30s** processing time. The full final
answer was read after completion; generation was neither stopped nor subject
to a short completion deadline. Pro reviewed public PR81 code and the supplied
evidence, not local model/source files or our test execution.

Its priority was A: deploy the frozen API-only M0 research path; then use new
pre-race history for later research; do not repeatedly refit the same small
observed development set. The implementation includes its requested positive
28-race raw-source run, separate 50-race membership check, 209-row transform
equivalence and commitment manifest. The optional fallback proposal was not
adopted: this first protocol is explicitly pure M0 with visible failed slots,
not an unnamed hybrid selected after outcomes. The full denominator is retained.
