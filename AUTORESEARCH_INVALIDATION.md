# Autoresearch Invalidation Notice

Status: `INVALID_LEAKAGE`

Date: 2026-04-26

The existing `autoresearch-results.tsv` leaderboard and previously selected best
model must not be used for model selection or performance claims.

Reason:

- `full_year_2025.json` raw `horses[:3]` matched the answer top-3 for all
  checked races.
- `research_clean.py` previously allowed stored `computed_features` from the
  snapshot to override freshly recomputed features.
- `clean_model_config.json` included `rating_rank`, so stored rank leakage could
  affect the reported holdout metrics.

Known affected result:

- Prior best row: `13`
- Prior best commit: `2869a73`
- Prior best metric: `lowest_overall_holdout_hit_rate=0.378641`

The research loop should only resume after leakage guards pass and a new clean
dataset/config version is evaluated from a fresh baseline.

Operational guard:

- `run_autoresearch_supervisor.py` refuses normal starts against the historical
  default `autoresearch-results.tsv` while this file exists.
- Clean v2 research must use `full_year_2025_prerace_canonical_v2` and
  `autoresearch-results-clean-v2.tsv`.
- `--allow-invalidated-results` is reserved for manual recovery-only runs, not
  metric research continuation.
