# Autoresearch Runbook

이 worktree는 `unordered_top3` 최근 기간 holdout 10시드 최저 적중률 개선을 위한
`autoresearch` 전용 실행 공간이다.

## Current Baseline

- source: `.autoresearch/outputs/holdout_seed_summary_report.json`
- metric: `lowest_overall_holdout_hit_rate`
- baseline lowest: `0.362460`
- baseline mean: `0.382201`
- baseline max: `0.394822`

## Scope

- writable:
  - `packages/scripts/autoresearch/clean_model_config.json`
- read-only references:
  - `packages/scripts/autoresearch/run_autoresearch_verify.sh`
  - `packages/scripts/autoresearch/run_autoresearch_guard.sh`
  - `packages/scripts/autoresearch/tests/test_rrx_propose.py`
  - `packages/scripts/autoresearch/tests/test_seed_matrix_runner.py`
  - `packages/scripts/autoresearch/tests/test_dataset_artifacts.py`

## Objective

출전표 확정 시점 정보만 사용한 `unordered_top3` 예측에서
`lowest_overall_holdout_hit_rate`를 baseline `0.362460`보다 높인다.

## Verify

```bash
sh packages/scripts/autoresearch/run_autoresearch_verify.sh
```

- stdout: 숫자 1개
- direction: `higher_is_better`
- failure semantics:
  - invalid config / 실행 인프라 실패 -> non-zero exit
  - 성공 -> lowest hit rate 숫자 출력
- every verify run uses a fresh output dir under `.autoresearch/verify-runs/`
- `.autoresearch/outputs` 는 최신 verify run 결과를 가리키는 심볼릭 링크다.

## Guard

```bash
sh packages/scripts/autoresearch/run_autoresearch_guard.sh
```

- expectation: exit code `0`
- purpose: proposer/runner/dataset artifact 회귀 차단

## Working Rules

- 실험은 `clean_model_config.json`만 수정한다.
- 누수 필드, 결과 필드, 시장 배당 필드는 추가하지 않는다.
- 바꿀 수 있는 축은 `HGB params`, `positive_class_weight`, 허용 feature subset 뿐이다.
- 한 iteration 당 변경은 작게 유지한다.
- guard 실패면 discard 한다.
- verify metric이 개선될 때만 keep 한다.

## Prompt

```text
$autoresearch
Goal: Improve leakage-free recent-holdout 10-seed lowest hit rate for unordered top-3 horse prediction beyond 0.362460.
Scope: packages/scripts/autoresearch/clean_model_config.json
Metric: lowest_overall_holdout_hit_rate
Direction: higher is better
Verify: sh packages/scripts/autoresearch/run_autoresearch_verify.sh
Guard: sh packages/scripts/autoresearch/run_autoresearch_guard.sh
Iterations: 5
```

## Preflight

반복 루프 시작 전 확인:

```bash
git status --short
git log --oneline -5
tail -20 autoresearch-results.tsv 2>/dev/null || true
```
