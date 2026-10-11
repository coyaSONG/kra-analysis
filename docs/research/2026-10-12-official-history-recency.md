# Supported Recent History Candidate Features

The new `official_supported_recency_v1` candidate supplies the five recent-form
fields proposed in the completed Pro consultation recorded in the restricted
ablation report. It preserves all **28 diagnostic races and 294 runner
appearances**. **No model was fitted, selected or promoted.** The fixed M0 forward
contract and complete-future-universe 70% objective are unchanged.

## Feature Semantics

Only API records with dated official event identity, exact complete roster, and
matching displayed rank and finish time enter ranked features. History uses
[target date minus 90 days, target date), excluding the entire target date.
The 30-day window includes its lower boundary. Calendar dates, not race-number
or venue ordering, determine recency. The previous official-supported 90-day
features and entire support projection are retained unchanged.

| Candidate | Non-null / 294 | Observed values |
| --- | ---: | --- |
| Supported ranked observations in 30 days | 294 | 178 zero; 116 one |
| Days since latest supported ranked date within 90 days | 246 | 20-85 days |
| Latest supported rank within 90 days | 246 | 1-11 |
| Mean of up to three latest supported ranks within 90 days | 246 | 1-11 |
| Linked API-unresolved record after latest supported ranked date | 246 | 1 true; 245 false |

Forty-eight appearances have no supported ranked observation in the selected
window. Their recency/rank fields are null, not zero or fabricated debut/rest.
Zero counts mean no matching supported observations in the selected sources;
they do not establish complete nonparticipation. In particular, these fields
do not reuse API26 `ilsu` or call the observed interval true rest days.

If two ranked observations share the latest date, the latest rank is null. If
selecting the last three would divide a same-day group, the mean is null. All
selected same-day records can be averaged when no boundary is split. The actual
dataset has zero such ambiguities, but synthetic regressions exercise both.
Same-day unresolved records cannot be ordered after a ranked record; the flag
is null unless a strictly later linked-unresolved record establishes true.
Unresolved does not mean a confirmed DNF, withdrawal or non-start.

## Quality And Availability

Source gaps, empty-unconfirmed responses and withheld observations remain
visible alongside every target. Twenty-one appearances have a withheld record
on or after their latest supported ranked date, or lack a supported ranked date.
Their observed features are not upgraded to complete histories. All previous
55 unsupported official groups and 172 identity-unresolved rows remain recorded
in the embedded source-quality audit, not reclassified or deleted.

The original raw seed and official HTML were captured after these diagnostic
October 10/11 targets. Event-date ordering cannot establish which historical
revision was available at a past cutoff. **Historical pre-race availability,
training approval, independent timestamps and prediction registration remain
false.** These features are not eligible historical training data merely because
replay and calculations passed. The dataset is not the complete national future
race universe and supplies no prediction success metric.

## Reproduction And Evidence

Run from `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`:

```sh
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.official_history_recency \
  --root .cache/autoresearch/observed-history-20261011 \
  --seed .cache/autoresearch/observed-history-20261011/seed-final.json \
  --seed-sha256 0dbe7abe5bdfb0a0b422bb90bddbdf1a3face89e5016254807ba37be95c25c66 \
  --archive-dir .cache/autoresearch/official-history-20261012-v2 \
  --archive-sha256 eaece57cdd27ee4e348e171e04368440da9d82a4417110476f0a1a1400e934e2 \
  --corpus .cache/autoresearch/restricted-cohort/20261011T124748.785378Z_ebdf29deaaa9/corpus.json \
  --corpus-sha256 d6598f244d6a7b7bc5e65846a4c79ee6ac96ad278b89a14268de332e77526ae2 \
  --output <new-output-path.json>
```

The actual output is
`.cache/autoresearch/official-history-recency/features-v1.json`, SHA256
`264a1c62d3740588c440d698b5cdb5a1494d323165804994d4e9f7db50cf52a1`.
The command replays raw sources offline, creates missing output directories and
saves atomically without replacing an existing artifact. The initial actual run
identified a missing-output-directory defect, fixed with a regression before
successful materialization. No raw cache or credentials are committed.

An independent calculation joined original seed records to the official support
sets for each target horse and date window, rather than reading the new output
lineage as its input. All five values matched on all 294 rows; complete target
membership matched the original corpus. The embedded support report equals
PR81's `projection-final.json` exactly. A second complete raw replay produced
the same entire output, not merely equal summary totals.

**154 regression tests passed**, including 19 new cases. These cover the date
boundaries, same-day ambiguity, partial sources, withheld events, label-independent
membership/features, raw corruption, unchanged source files, repeat equality and
non-overwrite. Existing M0 forward and evaluator tests pass without editing their
hashed dependencies. Ruff lint/format and diff checks pass. Remote CI and merge
evidence will be recorded on the PR; this is not an all-security-pass assertion.

## Next Research Step

Collect actual future cards and capture these source versions and candidate
features before each cutoff, without changing M0's occupied prediction slots.
New target examples need separate pre-race evidence review before challenger
training; any challenger requires its own fixed protocol and comparison on the
same full future population. Do not optimize these already observed targets or
present feature coverage as accuracy improvement. No new Pro consultation or
paid resource was used for this additive implementation of the existing advice.
