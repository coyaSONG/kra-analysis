# Saved rest proxy versus horse-specific observed entry gaps

## Result

The existing rest feature needs semantic correction before it can be described as a horse-specific recovery interval. In the same October development population as PR #69, all 116 races have a race-constant saved `rest` value. Stable horse IDs connect 1,192 of 1,308 target runner rows to a strictly earlier observed entry. Only one of these 1,192 saved values equals the calculated date gap. In 111 races, the observed gaps vary between horses.

This is a data-quality diagnosis, not a new prediction experiment. No model was trained, selected, promoted or changed. No future success rate or 70% achievement is claimed. The observed gaps are not certified actual-start rest intervals.

## Population and Checks

The source JSON contains 1,775 race rosters. Targets are exactly the 116 saved October 2025 validation states, totaling 1,308 runners. The command checks unique physical race keys, valid dates, exact target/source roster equality, matching saved `rest` and raw `ilsu`, unique runner numbers and normalized horse IDs, and available embedded horse date/number/venue identity. No names or gate numbers are used as stable horse identities. All target rows remain in the output.

Each diagnostic gap uses the latest strictly earlier date for the same stable horse ID in the supplied source, across venues. Same-day and future entries cannot influence it. Input order is irrelevant. Multiple observations on the latest prior date are retained as provenance, not arbitrarily selected. There are no missing target horse IDs; 116 target rows have no earlier observation and remain null rather than becoming zero or being called debutants. Ninety-one races have observed gaps for every runner.

The command reads neither race outcome labels nor model scores. It does not evaluate December. It parses the supplied roster collection, including later rows, but strict date selection prevents those rows from contributing to earlier target intervals.

## Concrete Example

For race `20251002_3_1`, gate 2 (horse ID 53275) last appears in the supplied earlier rosters on September 7: gap 25 days. Gate 3 (54386) last appears on August 31: gap 32 days. Gate 4 (54800) last appears on September 5: gap 27 days. Their saved `rest` values are all 75. Gate 1 has no earlier observation and remains unknown. These are observations in the supplied dataset, not guarantees about complete official start history.

## Source Interpretation and Risk

`packages/scripts/feature_engineering.py::compute_features` directly assigns `horse['ilsu']` to `rest_days` and derives rest risk from it. The repository inventory `docs/knowledge/discovery-2026-04-10-field-inventory.md` describes `ilsu` as a racing-day/session identifier. The [official entry-sheet API catalog](https://www.data.go.kr/data/15058677/openapi.do?recommendDataYn=Y), read on October 11, lists the field as day count; it does not establish that this means days since an individual horse's previous start. Do not upgrade that short description to stronger official confirmation.

Severity is high for feature interpretation; the observed disagreement is reproducible, but the effect on model accuracy is unknown. A race-constant feature can still interact with other features and changing its meaning under an existing model is unsafe. Existing production input semantics therefore remain unchanged in this increment. This note does not certify or endorse their current interpretation.

The legacy source lacks verified pre-race capture evidence and complete actual-start history. Listed runners may not have started, and missing observations may conceal later starts. Merely filtering by event date does not establish when data was available. Existing overlay notes claiming pre-race safety from date filtering alone are not sufficient for training approval.

## Replay

From the isolated repository root, with its existing Python environment:

    PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.horse_entry_interval_audit --dataset /Users/coyasong/Developer/coyasong/kra-analysis/.cache/autoresearch/full_year_2025_plus_20260613_collector_v2_full_context_training_lookback3_overlay.json --validation /Users/coyasong/Developer/coyasong/kra-analysis/.cache/autoresearch/laya_oof_training_dataset/validation.jsonl --output .cache/autoresearch/horse-entry-interval-audit-20261011-replay.json

Use a new output path on each replay; existing results are never overwritten. The JSON retains all 1,308 rows and pins exactly the bytes parsed. SHA-256 pins identify versions, not source timing or completeness.

The original report `.cache/autoresearch/horse-entry-interval-audit-20261011.json` has SHA-256 `f5d6388465d8afa6e07747597c5dff58e6975e0bb93c13bb48a7881e7d4b4c1a`. Dataset SHA-256 is `906845a664c78b723d37a01540369372a5133ac80e8d89b6a5392987b17a9a17`. Validation SHA-256 is `8151aa4bddc49a01b4bd2631d1cbcb600a9a031389fe787dc5ad390144b7c6c6`, identical to PR #69's paired audit. Raw source and output artifacts remain local; code and bounded findings are committed.

## Verification

Thirty-six focused regression cases passed. The combined source/identity/paired-audit/training-admission suite passed 229 tests with 15 existing joblib/NumPy deprecation warnings. Ruff lint and format checks passed. A second actual replay after venue validation produced byte-identical output.

## Next Experiment

First collect qualified actual-start history with stable IDs, full pagination and explicit coverage windows, preserve source versions and collection times, and distinguish scratched/non-starting entries. Then implement a new versioned horse-rest feature with separate missing-history state and an explicit train/serve migration. Compare it against the old proxy using the same frozen eligible races, fixed model/search budget and complete denominator. Do not silently replace old cached/model inputs or retrain on these unproven historical files. The pending fixed baseline and independent server-timed forward registration remain necessary alongside this feature work.
