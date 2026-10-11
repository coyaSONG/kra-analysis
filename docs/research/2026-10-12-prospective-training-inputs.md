# Sealed prospective learning inputs

The local adapter now connects the frozen M0 source selection to a separate
24-column learning-input archive. It does not fit or select a model, change M0,
read target labels, or claim improved accuracy. **Actual prospective packets:
0**, because the October 16-18 cards were still unavailable on the live refresh.
The complete-week data acquisition milestone remains unfinished.

The nonempty end-to-end check used real October 10-11 raw inputs: **28 packets,
294 runner rows, 24 columns each**. All values equal the existing API14 and PR85
recency10 projections. All 28 packets are explicitly historical diagnostics and
fail pre-race timing. They are not additional approved 24-column training races.

## What the adapter does

`packages/scripts/autoresearch/prospective_training_inputs.py` reads each existing
M0 study's complete national race list. If a prediction exists, its original
capture is replayed through M0's recovery validator. If only a reserved input
exists, that same raw capture is replayed. Missing or conflicting inputs stay in
the race ledger. No result roster, preferred later snapshot, or PDF-only eligibility
filter supplies missing members. A missing study remains unknown, not zero races.

For each available complete roster, the existing recency projector joins the fixed
history version without target labels. Its five values and five missing flags
join the original API14 columns. No imputation, scaling, optimization or extra
feature selection happens. Other history fields, source coverage and lineage are
retained as evidence, not additional model columns. Null history retains runners;
observed zero counts are not claims of complete nonparticipation.

The separate first eligible input slot is written atomically once, then observed
after persistence. Repeated runs reconstruct and compare the entire packet except
its original materialization timestamp; valid files retain their first timestamps
and bytes. Conflicting occupied files are not replaced. Even occupied invalid
packets and observations have their hashes retained in the run manifest. Parent
M0 studies, captures, model and predictions are read-only to this adapter.

The contract fixes the parent series, October 16-18 dates, 24 column names, history
source pins and transformation source hashes. It uses the existing owner/filesystem
and local-clock trust assumptions. It is not tamper-proof storage against the
machine owner, independent prediction registration or a model-training approval.

## Time and publication boundaries

The selected history source chain is:

- Seed SHA256 `0dbe7abe5bdfb0a0b422bb90bddbdf1a3face89e5016254807ba37be95c25c66`.
- Official archive SHA256 `eaece57cdd27ee4e348e171e04368440da9d82a4417110476f0a1a1400e934e2`.
- Exact PR85 merged document SHA256 `42bebb6385f704be9b657dfbba8735c0e818e7f56765fee13c0e9e467b25ac0a`.
- Server merge commit `cbd299b7f36e317a1583becaa376be9deca15e08`, at `2026-10-11T20:17:47Z`.

The adapter retrieves this exact publication live and verifies the source hashes
in it. It replays the selected raw API214 pages, API26 identity bindings and official
HTML. The latest selected source/seed clock is `2026-10-11T18:11:30.128086Z`, before
the publication bound. Replaying the same pinned source later does not make it a
new historical source revision.

History availability and publication, target API capture, materialization and
readback must satisfy the individual frozen T-30 cutoff. A current history event
date alone never makes its later-collected revision available at a past cutoff.
A late readback is not backdated. The historical diagnostic mode records timing
failures but cannot produce a `locally_sealed` prospective status.

**The new packet itself is not independently published by this code.** Every run
keeps `independently_published_packet_count` at zero and training approval false.
When real cards become available, publish the exact new manifest bytes and verify
their packet/raw hash closure against a live server merge event before each
applicable race cutoff. Keep the original M0 commitment bytes in a separate file;
do not wrap or rewrite them. This external publication/evidence review is still
required. A local packet, or a hash printed here after a historical race, is not
independent pre-race certification.

## Actual execution

Successful diagnostic output lives under
`.cache/autoresearch/prospective-training-inputs-v2/diagnostic/`.
Its first manifest is `20261011T205232.661246Z_e581a860d543/manifest.json`, SHA256
`4fc53b37e910bc740821a21d55e217aab694a0c7d8a5ec64a7177961d0f81a79`.
The repeat is `20261011T205433.591189Z_47278a60175e/manifest.json`, SHA256
`79b054afa67de040e9c5759069c044f834f2f4600c5f55dbb939147e867c6acc`.
Both have identical 28 packet hashes, complete ledgers and original readback
observations. Their shared history projection SHA256 is
`36528d92b0eeaf0e7e93ada686ace97edf41e14e3db115dc392f199fc673f501`.

All 294 API14 vectors match the PR86 exploratory raw replay, and all recency10
values plus entire row-level history evidence match PR85. The recent-count column
is non-null for 294 rows; each of the other four history values is non-null for
246 rows. The 48 missing cases remain present. All 28 historical packets carry
both history-before-cutoff and materialization-before-cutoff rejection reasons.

The original M0 command refreshed 12 official schedule pages at
`2026-10-11T20:53:00.002293Z`. All three dates remained `awaiting_card`, with
race counts unknown. The new adapter's actual future manifest is
`.cache/autoresearch/prospective-training-inputs-v2/local_m0_20261016_18_v1/20261011T205401.147852Z_1173768b3b06/manifest.json`,
SHA256 `291feab000be7599a07b1e0a1facd3ab7feb10fb30a26b8045f04493a1b23422`.
It preserves those three unknown dates and has zero local or independently
published prospective packets. No future predictions or accuracy were generated.

The initial 63 M0/model files were unchanged. The intentional original forward
refresh added 17 files. Before/after the new live adapter, all 80 files and the
file membership were exactly unchanged. This distinguishes intended collection
by the original command from read-only behavior of the new adapter.

Contract SHA256: `3dd3bc49ec64e9c34e8b616f109ab660e305f2edd30f28176cc67ccb50c202b2`.
Adapter SHA256: `ee86f1c18cc6b49fce59adf6b4014468ae433f02acd4ce7fc56df260938996cd`.

## Reproduction

From `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`, first run
the original M0 command documented in `2026-10-12-local-m0-forward.md`. Then:

```sh
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.prospective_training_inputs run \
  --parent-root .cache/autoresearch/local-m0-forward/local_m0_20261016_18_v1 \
  --model-dir .cache/autoresearch/restricted-models/20261011T125457.212167Z_4113cd1060f9 \
  --history-root .cache/autoresearch/observed-history-20261011 \
  --seed .cache/autoresearch/observed-history-20261011/seed-final.json \
  --archive-dir .cache/autoresearch/official-history-20261012-v2 \
  --output-dir .cache/autoresearch/prospective-training-inputs-v2
```

For historical diagnostics, replace `run` with `diagnose` and add:

```sh
  --plan .cache/autoresearch/race_card_pdf_bundles/20261009T165933.854898Z_51a041eda9e6/input_plan.json \
  --raw-archive-root /Users/coyasong/Developer/coyasong/kra-analysis
```

Use the same prospective output root on subsequent runs. An exit code of zero
means execution completed, not that inputs exist or are approved; inspect the
explicit counts and whole day/race ledger. Contract changes require a reviewed
protocol amendment, not deleting existing slots. Cache files are local and
ignored by Git; no credential or raw dataset is committed.

## Validation and remaining work

**170 tests passed**, including 25 new cases. The source-backed positive fixture
uses actual API/HTML capture and replay paths with a test-only publication witness,
not a claim of external certification. Fixed test clocks avoid dependence on the
date CI runs. Tests cover missing/conflicting complete rosters, missing history,
labels not entering X, changed raw HTML, late source/publication/readback, source
and packet hashes, occupied-slot non-overwrite and unchanged parent files.
Existing M0 forward/evaluator, frozen source and recency regressions pass. Ruff
lint and format pass. CI runs in the existing Python job with model dependencies.

The first actual run exposed a publication reader assuming inline-backtick hashes;
PR85's pins are in its shell example. Exact whole-token matching fixed it, with
five positive/negative layout cases. The failed v1 directory remains diagnostic
evidence and is not treated as a source cohort. No existing hashed module changed.

This implements the completed Pro strategy advice recorded in PR86; no new Pro
consultation or code-review approval is claimed. The next substantive completion
condition is real future card acquisition, immutable 24-column inputs and timely
independent publication, then separate versioned outcome attachment. Models fit
using that week's labels must be evaluated on a later period, never retroactively
on the same week. The 70% objective is unachieved. Paid server provisioning
remains deferred.
