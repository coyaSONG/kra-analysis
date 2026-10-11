# API27 shared-input prospective comparison

## Result

Implemented a separate API27 companion runner and read-only paired evaluator.
Original M0 code, model, archive and evaluation remain unchanged. This is an
operational comparison of two fixed models using the original shared intake,
not independent collection reliability or an isolated causal effect of seven
additional training races. No model is promoted and no accuracy improvement is
claimed. Paid servers remain on hold.

Actual historical raw replay produced both models' predictions for all 28
inventory races / 294 runner rows. The pre-transform API14 rows, identities and
source references were identical. Each model used its own saved imputer/scaler.
The unordered choices differed in 6 of 28 races; this is not a quality metric.
No outcomes were joined. Both repeated replay reports had SHA256
`eb33a76eeb19335a0575937616841a30b12f4360ce844b5836abb2bd77218482`.

The wider national rehearsal retained all 50 races: 21 scored / 225 runner rows,
7 input conflicts and 22 missing inputs. It did not repair old inputs using later
cards, discard failures, or turn an after-target rehearsal into forward evidence.
Original M0/archive/model and API27 fit artifacts: all 103 files retained the
same membership and bytes before/after companion execution and evaluation.

The real October 16-18 path still has no frozen cards, no bound population and
zero predictions. Both denominators and rates are unknown, not zero accuracy.

## Completed Pro Consultation

Authorized conversation:
https://chatgpt.com/c/6aca2dc4-d2e8-83e8-acab-e85f281c27b7

Submitted around 2026-10-11 21:21 UTC; completed response observed before
21:36:04 UTC. UI reported `10m 50s` processing and response completed. Generation
was not stopped, restarted, or subjected to a short completion timeout.

Pro stated it inspected public PR88 merge
`ff63ba82199fb57975cbe3bc870ab898b510a52f`, its training/admission code, review,
tests, report and existing M0 runner/inference/evaluator. It explicitly did not
open local raw files/model artifacts or run tests. This was source-level
methodological advice, not independent approval of the 27-race raw corpus or a
review of the new, then-unpublished companion patch.

Applied advice:

- Keep H/F/Q/D separate: verified hit, verified miss, pending evidence,
  undefined target. A present but unbound/invalid/late packet is Q, not an
  invented missing prediction. Actual absence after cutoff is F only with a
  verified complete universe and unique target. A `(M0=Q, API27=F)` regression
  explicitly remains distinct and produces no paired binary table.
- Inherit M0's final population validation, including extra-result checks.
  API27 publication failure does not erase or redefine the shared denominator;
  it blocks API27 prediction evidence. Never infer N from a partial ledger.
- Use a separate exact API27 wrapper/receipt loader, original API14 projection,
  each model's saved preprocessing, and canonical unordered horse IDs.
- Check API27's own fit, source, computation, readback and publication times.
  Read-only evaluation never creates a packet or observation.
- Retain the conservative first-block-cutoff rule. Every admitted packet and
  readback for all three dates must already be in the selected snapshot before
  that first cutoff. A later Saturday/Sunday prediction cannot be spliced into
  the Friday snapshot, even if made before its individual race cutoff.

One deliberate refinement to the submitted proposal: source inspection found
that original M0 reserves its input before scoring. API27 can therefore use that
exact reservation even when M0 scoring fails. A raw-backed test proves this.
It never requires the parent prediction's success or invents a new acquisition.
Consequently the relevant predecessor time is source availability, not the
completion time of an independently retried M0 scorer. When reservation and M0
packet both exist, their study and source references must agree.

## Frozen Protocol

`data/contracts/api27_forward_contract_v1.json` has SHA256
`649cfe45d3ef17ea936c79e8400b44fc45474bcee12e9f94327a57a5cd856585`.
It binds the original M0 contract, new runner/evaluator, current M0 evaluator,
all October 16-18 dates, API27 model and exact first final fit receipt.

- API27 model: `5f33dfd1e45c493fc5edfd90a8250ac5e91bb841b29124e5988b657994dc17b4`
- API27 receipt: `b91d7b85cef9038a742f2a68a616cc56c627793d5efa4046c21178d00a6833ea`
- Original M0 contract: `ffd068ed7c507e2cf0bef63ed2dcbebf01fdcdd0e38d89c849d03d60c448f59c`
- New canonical series: `api27_shared_20261016_18_v1`

Only the first packet per race is accepted; occupied invalid packets are not
overwritten. Parent study changes or population regression stop the run. Missing
input remains in the complete race list. No retraining, replacement source,
fallback, model OR, subset rate, winner selection or automatic promotion exists.
Paired both/M0-only/API27-only/neither counts and rate difference require every
race in the full universe to be H/F for both arms.

Publishing this protocol is not publishing predictions. Actual paired evidence
requires exact selected M0 and API27 commitment bytes, independent live GitHub
publication witnesses before the first block cutoff, original raw replay and
the existing versioned outcome policy and all its dependency pins. The API27
commitment binds the exact parent commitment hash. Publish both files together
in a normal checked PR when populated; never publish an empty snapshot as proof
of a complete future population. Local owner/clock trust is still explicit;
GitHub proves published bytes, not an independently audited collection service.

## Actual Local Artifacts

All paths below are relative to the isolated `kra-analysis-race-card-pdf` checkout.

- Original refreshed commitment:
  `.cache/autoresearch/local-m0-forward/local_m0_20261016_18_v1/commitment_20261011T212155259591.json`,
  SHA `115a37b728c51da1f04b51dc51e455e26e2c7d4c193268c2fcf57a78040c321f`.
  Its run/capture records, not this repeatable empty-content hash alone, prove
  the 21:21:55 refresh of 12 official responses.
- Final companion commitment:
  `.cache/autoresearch/api27-forward/api27_shared_20261016_18_v1/commitment_20261011T213702.504497Z_ab527585a1d5.json`,
  SHA `29847b30f1dc5e5a9b28a246c2f2f4fc352712d91d382c705e6c19ec71dbaad9`.
  All three dates are `population_not_bound`; normal pending exit code is 2.
- Final read-only evaluation:
  `.cache/autoresearch/api27-pair-evaluation/report-final.json`,
  SHA `5de9f3cbb1c2ae1674acc5e132f3e5bf12bc6e16f5767a57aa2e2b0f4db42125`.
  No outcomes/publication were supplied; no rates or paired table were produced.
- Real source/model rehearsal:
  `.cache/autoresearch/api27-pair-rehearsal/report.json` and `report-repeat.json`.
  Exact plan SHA `619dfb72764a8ddb467047e3fd687b86f53cbb2d91d1c567d83ff2ed92985922`.

The provisional pre-advice contract `a9c969c54fdebbabd61c82eb8dc6f7a26fff6bdd7158c8b3ac1b55224ab73b83`
had zero predictions/studies and no external publication. Its entire directory
was preserved as `.cache/autoresearch/api27-forward-provisional-20261011T213434`,
not overwritten; its initial evaluation remains `report.json`. It is superseded
before any actual prediction by the protocol above. Do not reset a populated or
published series in this manner.

## Running and Validation

Use `PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.api27_forward`.
`rehearse` takes `--plan`, `--m0-model-dir`, `--api27-model-dir`, `--output`.
`run` instead takes `--parent-root`, `--parent-commitment`, its exact
`--parent-commitment-sha256`, both model directories and a separate output root.
The executable module's `--help` lists the full interface. Model paths and the
exact replay plan are in the companion ExecPlan.

`autoresearch.api27_evaluation` takes both roots, both exact commitments and
hashes, both model directories, and a separate `--output`. Optional outcome
plan/hash and separate `--m0-publication-pr/document`,
`--api27-publication-pr/document` plus a fresh `--witness-directory` enable actual
evidence replay. The CLI collects publication evidence itself. No API key is
needed for companion inference or reading already collected outcomes.

Focused regressions cover raw-backed positive comparison, independent arm
states, parent scoring failure after reservation, absent input, full membership,
missing/tampered/unbound packets, late readback/publication, model pins, no source
writes and immutable retry. CI runs them in Python Checks with numerical deps.
Final local regressions: 229 passed, including 33 new companion cases; Ruff
lint/format passed. Remote check/merge evidence is recorded in the PR closure
comment. Existing security findings must be compared with the prior baseline;
they must not be described as passing or hidden by an administrative merge.

Next useful evidence is a nonempty complete national card and actual pre-cutoff
paired predictions. Further retrospective contract rewrites do not improve
prediction quality or replace that missing forward evidence.
