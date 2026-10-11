# Stored October paired-error diagnostic

## Result and scope

The stored structured ranker loses five exact hits relative to the stored strict-fallback method on the same 116 October 2025 development races: 58 versus 63. This is a recomputation of old saved predictions, not new inference, a new model ranking, a fresh holdout, or evidence of future 70% performance. This selected development cohort is not the newly required complete national forward universe.

| Stored-prediction outcome | Races |
| --- | ---: |
| Both exact | 51 |
| Strict fallback only exact | 12 |
| Structured ranker only exact | 7 |
| Neither exact | 46 |
| Total | 116 |

The ranker replaces 12 baseline successes with failures and recovers seven other failures, a net loss of five (4.31 percentage points). This is descriptive, not a significance claim or proof of a cause. No per-race oracle combination of the two methods is scored as a model. There are ten dates and 1,308 runner rows, not 1,308 independent races. No stored ranker output abstains; `NONE` remains a failure in regression tests and is not replaced with a retrospective fallback.

## Data quality finding

**High-priority semantic concern:** the rendered `rest` field is constant across every runner within each of all 116 races. Across the full 1,308 rows it has only eight observed values, 75 through 82, and no nulls. Thus it supplies no horse-specific rest distinction within these races. This does not prove every possible model interaction is useless, nor explain the five-hit loss causally.

The current exporter maps `rest` from `rest_days`; `packages/scripts/feature_engineering.py` assigns `horse.get("ilsu")` directly to `rest_days`. The existing [field inventory](../knowledge/discovery-2026-04-10-field-inventory.md) describes `ilsu` as an implementation-day/session identifier, not a horse's recovery interval. The [official entry-sheet catalog](https://www.data.go.kr/data/15058677/openapi.do?recommendDataYn=Y) calls the field only "days" (ilsu); that short description alone does not establish a horse-specific rest interval. Current source code is corroborating evidence, not proof of the exact historical transformation revision.

Confidence is high in the constant-within-race observation and the current code/document contradiction; the exact upstream field definition and historical transform version still need primary-source verification. Treat this as a likely semantic mapping defect, not a confirmed performance gain waiting to be claimed. Do not rewrite old artifacts or relabel the current values as verified rest days.

Other observed missingness, retained without dropping runners or races:

| Rendered field | Null rows / 1,308 |
| --- | ---: |
| horse_place_x10 | 191 |
| recent_top3_x1000 | 184 |
| weight_delta | 84 |

The audit does not identify whether any particular model error was caused by missing information versus failure to use existing information. Historical pre-race source availability remains **unproven for all 116 races**, consistent with the existing legacy evidence limitation.

## One next information hypothesis

Test whether a correctly derived horse-specific interval since the latest qualifying prior start adds exact-hit value beyond the unchanged structured baseline. The current `ilsu`-derived feature does not establish that information.

Required evidence: stable horse ID, dated prior-start records captured or demonstrably available before the current input cutoff, the current race date, and explicit handling of incomplete history and no prior start. Exclude current/future starts from the derivation and preserve unknowns as null with a separate reason. Preserve the full evaluation population and the same fallback; missing history does not delete a race.

First verify field semantics and reconstruct a small source-backed sample before touching the shared feature contract. Then define one ablation with identical eligible training races, candidate generation, hyperparameter budget and fresh future evaluation universe, changing only the rest-interval feature family. Reject the data hypothesis if adequate pre-race history or stable identity cannot be established. Reject the performance claim if that single prespecified future comparison does not establish improvement; do not retune using these October errors or reuse December as untouched evaluation. No model change or experiment claiming that gain has been made here.

## Reproduction and integrity

From the isolated worktree root, using its Python environment:

```bash
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.october_paired_error_audit --research-root /Users/coyasong/Developer/coyasong/kra-analysis --output .cache/autoresearch/october-paired-error-audit-20261011.json
```

Use a new output filename for a repeat run; existing outputs are not replaced. The command reads only the existing trusted local artifact bundle. The joblib cache must not be replaced by an untrusted download: its manifest hash is an integrity check, not a safe deserializer for hostile pickle data.

The full local ledger contains every race's original selections, exact category, omitted/extra runner numbers and missingness, with SHA-256 `7771bbe09cd102b709bede32f3419c7684f7769eb192b501d2c22c4c95a13bac`. Source files are read once, pinned, and the same bytes are consumed. Only the October validation split is evaluated; no December predictions or labels are used for this calculation or model selection.

| Input | SHA-256 |
| --- | --- |
| Stored strict baseline artifact | `b20f80e563436134b236acad6f364e2cddf5b0585806fcd4eb51f8ba6ef57d0c` |
| Stored structured predictions | `4880afa1086bbcb4c292bc2f8c5afe19d78b1b3cc2484e014e0b79732c39e416` |
| Existing ranker report | `7908c046fd8ab57033a95b2f95014c44102489d9ee159439f570a4fa99b97d19` |
| Validation JSONL | `8151aa4bddc49a01b4bd2631d1cbcb600a9a031389fe787dc5ad390144b7c6c6` |
| Existing dataset manifest | `4ff966587fe48e9dcc28b337c2017d6d5e3b539e4a1456d7e90ed54b79473df5` |
| Candidate cache, validation answers only | `da813f4c87ab720cdc08b4456d66910fde92988fffca750d86db7573b532c2c3` |

Validation/candidate hashes match the existing manifests and report. Baseline, ranker, answers and feature states have exactly the same 116 unique keys. Selections are validated against the saved roster, exact hits are recomputed from the saved answer sets, and saved booleans/summary totals are cross-checked. The old report's 63/116 and 58/116 totals reproduce exactly. Current hashes do not retroactively establish original prediction or capture times.

Verification: 14 focused diagnostic tests passed; combined schedule/identity/entry/training/diagnostic regressions passed **193 tests**, with 15 existing joblib/NumPy deprecation warnings. The new focused tests run under required Python CI. No training, promotion, operating prediction, or original-owner checkout modification accompanies this diagnostic.
