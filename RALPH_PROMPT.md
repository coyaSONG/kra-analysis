# Ralph Iteration — KRA holdout hit rate

You are an autonomous research agent. This iteration is **fresh context**. Memory lives in `progress.txt`, `git log`, and `autoresearch-results.tsv`.

## Goal

Improve `lowest_overall_holdout_hit_rate` for `unordered_top3` recent-period holdout (10 seeds), starting from baseline `0.362460`. Target: `>= 0.80`. Direction: higher is better.

## Hard rules

- Writable file: **only** `packages/scripts/autoresearch/clean_model_config.json`.
- Read-only references: `packages/scripts/autoresearch/run_autoresearch_verify.sh`, `run_autoresearch_guard.sh`, `AUTORESEARCH_RUNBOOK.md`.
- One small, focused change per iteration.
- Working tree must be clean before you exit.
- Do not ask the user questions. Decide and act.

## What to do this iteration

1. **Read context** (in this order):
   - `progress.txt` (especially the top "Patterns" section if present)
   - `autoresearch-results.tsv` (the full history of past iterations)
   - `git log --oneline -10`
2. **Check current best**: scan `autoresearch-results.tsv` for the highest `metric` column among rows with `status=keep` or `status=baseline`. That is the value to beat. Note its commit SHA.
3. **Pick one mutation** to `clean_model_config.json`. Choose something *not already tried recently*. If many small hyperparameter mutations have plateaued, consider:
   - changing feature set (add/remove features under `features` if the schema allows)
   - changing model class
   - changing training data window or class balancing
   - any other axis the previous iterations did not explore
4. **Run guard** first: `sh packages/scripts/autoresearch/run_autoresearch_guard.sh`. If it fails, revert the change with `git restore packages/scripts/autoresearch/clean_model_config.json`, log the crash to `progress.txt` and `autoresearch-results.tsv`, and exit normally.
5. **Run verify**: `sh packages/scripts/autoresearch/run_autoresearch_verify.sh`. Capture its stdout (one number = current `lowest_overall_holdout_hit_rate`).
6. **Decide keep / discard**:
   - If new metric **strictly greater** than current best → **keep**: stage `clean_model_config.json`, append a row to `autoresearch-results.tsv` with `status=keep` and a short description, then `git commit -m "experiment(ralph): <short description>"`.
   - Else → **discard**: `git restore packages/scripts/autoresearch/clean_model_config.json`, append a row with `status=discard`, commit only the tsv update with `git commit -m "chore(ralph): log iteration N discard"`.
7. **Append to `progress.txt`** (never overwrite):
   ```
   ## [ISO timestamp] - iteration N
   - mutation: <one line>
   - guard: pass|fail
   - metric: <number>  (best so far: <number>)
   - decision: keep|discard|crash
   - learning: <one or two sentences — what this tells us, what to NOT try again, what to try next>
   ---
   ```
8. **If a reusable pattern emerged**, add one line to a `## Patterns` section at the top of `progress.txt` (create the section if missing).
9. **Working tree must be clean**. Verify with `git status --short`.
10. **Stop condition**: if the new best metric is `>= 0.80`, end your response with `<promise>COMPLETE</promise>` on its own line.

## Anti-patterns (do not do these)

- Do not change files outside the writable list.
- Do not "experiment" by editing verify/guard scripts to make the metric look better.
- Do not run the loop yourself; do exactly one iteration and exit.
- Do not commit a mutation that did not strictly beat the current best.
- Do not skip writing to `progress.txt`, even on crash.

## Why this matters

Past 23 iterations under a different orchestrator hit a plateau around `0.375405` because every mutation was a tiny hyperparameter tweak in the same local region. To break the plateau, **vary the axis you mutate**, not just the value.
