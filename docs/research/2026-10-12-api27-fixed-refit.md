# API27 fixed research refit

## Result and limits

`API27_fixed_v1` is a separately reviewed logistic model trained on **27 races,
283 runners and 14 pre-race API columns**. The existing frozen M0 used 20 races
and 209 runners; all of those 20 races retain exactly the same API features and
top-three labels. This adds seven races and 74 rows, not demonstrated accuracy.

The actual fit converged in 11 iterations. The consumed matrix has 81 positive
and 202 negative runner labels, exactly three positives per race, unique
race/gate/horse identities, finite values and total weight one per race. No
training-hit rate, development-score selection or 70% success claim is made.
The model is **not promoted** and does not replace M0's October 16-18 experiment.
A separately frozen future comparison protocol is still required.

## Data and review

The original 28-race, 294-runner inventory remains intact. Its sole excluded
training race, `20261010_1_1`, is a versioned void observation with no defined
top three. Its 11 rows are retained, not converted into negative labels. This
training selection is not a future evaluation denominator.

All original raw API26 sources are replayed. PR61's publication chain establishes
that the inputs were committed before their original captured T-30 cutoffs.
GitHub bounds existence, not KRA source authenticity or prediction registration.
The frozen API214 and official-HTML result observations match the complete input
rosters. Unique ranks 1, 2, 3 define labels under the fixed PR83 policy; lower-rank
exceptions remain documented. Permanent settlement finality is not established.

The canonical corpus matches PR86's report exactly after removing its volatile
publication-witness audit from the canonical projection. Each run separately
retains the complete freshly fetched witness report and binds its hash in the
run manifest. All 28 source chains and pre-cutoff content bounds pass. The
preparation witness was retrieved at `2026-10-11T21:08:43.151529Z`; the original
publication is `2026-10-09T17:08:16Z`, commit
`f794ffc24414117420004ca45bd8ae20a04385db`.

The 27 selected races cover October 10 (16 races) and October 11 (11 races),
meet 1 (20 races) and meet 2 (7 races). They are not a national untouched test
set. Of seven base fields, only `rating` has missing values: 16/283 (5.65%).
Missing values and their flags are preserved; medians and scaling are fitted
only on this training corpus. The post-target history/recency fields are absent.

`data/contracts/api27_training_review_v1.json` is a **Codex source and label-version
review**, not independent Pro or human approval. It pins the corpus, selected
and inventory membership, runner count, recipe and complete implementation
fingerprint. The existing restricted-training review and admission remain
unchanged. Pro's previous strategy advice preceded the seven-race discovery;
it must not be described as reviewing or approving this refit.

## Fixed recipe

The existing numerical helper is reused behind the new admission gate: median
imputation (all-missing columns become zero), standard scaling, logistic `lbfgs`,
`C=1/27`, per-runner weight `1/roster_size`, no class weighting, intercept enabled,
seed 42, tolerance `1e-8`, maximum 2000 iterations. There is no parameter search
or date split. Tie-breaking remains score descending, gate ascending, horse ID
ascending. Race, horse and gate identities, result labels, source timestamps and
metadata do not enter the 14-column feature matrix.

The new artifact wraps the numerical estimator in
`kra-api27-research-model-v1`. The nested helper's `arm=M0` means only its API14
column selector, not the frozen forward M0. The new recipe removes the old
train/development-date declarations. Both old M0 admission and frozen source
hash checks continue to pass.

## Reproduction and evidence

Run in the isolated research checkout with its existing `.venv` and ignored raw
archive. The primary checkout below is read-only.

```sh
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.api27_refit fit \
  --plan .cache/autoresearch/race_card_pdf_bundles/20261009T165933.854898Z_51a041eda9e6/input_plan.json \
  --bundle .cache/autoresearch/race_card_pdf_bundles/20261009T165933.854898Z_51a041eda9e6/feature_bundle.json \
  --outcome-plan .cache/autoresearch/versioned-outcomes-20261012-plan.json \
  --archive-root /Users/coyasong/Developer/coyasong/kra-analysis \
  --output-dir .cache/autoresearch/api27-refit
```

Use `prepare` instead of `fit` for a nontraining replay. Neither accepts an
arbitrary review file. Changed corpus, recipe, source code, Python/dependency
versions or approval flags fail closed; changed environments need a new review,
not automatically rewritten hashes. Every invocation writes a new directory.
The receipt is last and the CLI run manifest binds replay report, corpus and
fit receipt. Partial directories are not completed fits. No credentials or paid
service are required for the GitHub publication read.

First final-implementation run:
`.cache/autoresearch/api27-refit/20261011T211226.789383Z_42d55382ed35/`.
Completed at `2026-10-11T21:12:59.139255Z`.

| Artifact | SHA256 |
| --- | --- |
| Corpus | `5445e7ab3efc2125af52c32e40796220e1f2888e5d8becfd21d88da25d1e1cd3` |
| Model | `5f33dfd1e45c493fc5edfd90a8250ac5e91bb841b29124e5988b657994dc17b4` |
| Consumed matrix | `83392f89bd95168701b4464e320e443df30be94acb44c49f4a8add339eb0f06b` |
| Implementation | `9bafe27172bb8ae543ed222c9e46cbcab02d509b77c18c96c2ea4f4a4e0f3f89` |
| Recipe | `54be896ca77eaac868dbb4715b20b1a0ebd9e73912341c0bcfceee946913e9ab` |
| Repository review bytes | `da0690113c4fa48ea7b765dd9c374caf21b351ea2eabb47d759dfca64ef10240` |
| Canonical review copy | `4ec65ad98a09dbd328113ef702469de9e19d1e5b3258dbf2fbf5f2f43e0b9e00` |
| First final fit receipt | `b91d7b85cef9038a742f2a68a616cc56c627793d5efa4046c21178d00a6833ea` |
| First final replay report | `175f42b1b3439061d671e0a37290cbabafa9429fc0ff84a7e7ee97860ed96cb0` |

The independent repeat is
`.cache/autoresearch/api27-refit/20261011T211324.121640Z_e1a0b03f1b12/`, completed
at `2026-10-11T21:13:56.166844Z`. All five fit artifacts (model, matrix, corpus,
review copy, implementation) are byte-identical. Both runs converged in 11
iterations. Fresh witness timestamps and completion receipts correctly differ.
The repeat receipt hash is
`46d2c7b1a752c5db982f533ca17d3e38d11074ad969ba399aa6aa026214bbd67`.
Run-manifest hashes are
`323910367fd9feb913be4a3e9638cef71caeb1cf749ccab10676c1cded48df9e` and
`ecb3010712022833cd29490c19559658c7777f6bfb37109068c21553a8eac681` respectively.
Each manifest binds that run's complete replay report and fit receipt.

The preliminary `20261011T211032.012042Z_3a4efb7ac9bb` run is superseded: its
model referenced original review bytes while the saved copy was canonically
serialized. The final schema distinguishes `repository_review_sha256` from
`review_sha256` (saved canonical copy). No numerical setting changed. A dedicated
test covers noncanonical review formatting.

## Verification and next step

The new 41 tests and six related suites pass: **189 tests**. Ruff lint and format
checks pass. Coverage includes exact review admission, source/label/membership
changes, schema leakage, roster identity, timing, missing flags, numerical
reproducibility, implementation/review drift, output corruption, solver failure
and CLI evidence binding. Tests use synthetic reviews only; they cannot approve
production inputs.

The original frozen model directory and forward archive retain exactly the
same 80 files and SHA256 values as before this work. The original M0 read-only
loader still admits its 20-race model. No hashed original module was edited.
Final remote CI and merge evidence is recorded in the PR closure comment.

No future cards or predictions were refreshed by this refit. The last separate
M0 refresh on October 11 at 20:53Z still had October 16-18 awaiting cards. Next
work is a separately predeclared paired future comparison of API27 and frozen
M0 over the same complete national universe, without OR-combining their picks,
discarding failures or replacing M0 predictions. API27's relative success rate
is currently unknown. Paid servers remain deferred.
