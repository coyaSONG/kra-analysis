# Target metric is holdout `set_match` ≥ 0.70

The canonical north-star metric for the 삼복연승 prediction system is **`set_match` ≥ 0.70 on the holdout split** (top-3 unordered set agreement between predicted and actual finishers). All evaluation, prompt-improvement, and architecture decisions are measured against this single number.

This ADR resolves two earlier conflicting framings: the vague "70% 적중률" wording in `CLAUDE.md` and the `set_match ≥ 0.50` value used as a hard gate in `packages/scripts/autoresearch/program.md`. Training-set accuracy and `correct_count` are diagnostics, not substitutes.

Source: session decision 2026-05-03. Promoted from `docs/knowledge/decision-2026-05-03-target-metric-set-match.md`.
