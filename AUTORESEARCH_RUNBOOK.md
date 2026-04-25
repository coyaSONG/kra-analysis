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

- experiment writable:
  - `packages/scripts/autoresearch/clean_model_config.json`
- log writable:
  - `autoresearch-results.tsv`
  - `progress.txt`
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
- 로그는 `autoresearch-results.tsv`와 `progress.txt`만 수정한다.
- 누수 필드, 결과 필드, 시장 배당 필드는 추가하지 않는다.
- 한 iteration 당 변경은 하나의 연구 축으로 제한한다.
- plateau가 길어지면 작은 HGB 값 조정 대신 모델군, 피처군, class weighting, 검증 window 같은 새 축을 우선 탐색한다.
- `model.positive_class_weight`와 `experiment.common_hyperparameters.positive_class_weight`는 항상 동기화한다.
- guard 실패면 discard 한다.
- verify metric이 개선될 때만 keep 한다.

## Research Review

각 iteration 시작 전 반드시 확인한다.

- `progress.txt`
- `tail -20 autoresearch-results.tsv`
- `git log --oneline -20`
- 마지막 keep commit의 diff 또는 stat
- 현재 `clean_model_config.json`

판단 기준:

- 최근 5개 resolved iteration이 최고 기록을 못 넘으면 작은 값 조정보다 새 연구 축을 고른다.
- 최근 10개 resolved iteration이 최고 기록을 못 넘으면 radical experiment를 고른다.
- 이미 discard된 axis/value 조합은 같은 조건으로 반복하지 않는다.
- 결과 row description에는 어떤 연구 축을 왜 테스트했는지 남긴다.
- `progress.txt`에는 hypothesis, metric, decision, learning을 append한다.

## Prompt

```text
$autoresearch
Goal: Improve leakage-free recent-holdout 10-seed lowest hit rate for unordered top-3 horse prediction. Current best must be read from `autoresearch-results.tsv`; baseline is 0.362460.
Scope: packages/scripts/autoresearch/clean_model_config.json
Metric: lowest_overall_holdout_hit_rate
Direction: higher is better
Verify: sh packages/scripts/autoresearch/run_autoresearch_verify.sh
Guard: sh packages/scripts/autoresearch/run_autoresearch_guard.sh
Iterations: 1
```

## Preflight

반복 루프 시작 전 확인:

```bash
git status --short
git log --oneline -5
tail -20 autoresearch-results.tsv 2>/dev/null || true
```

Historical note:

- `autoresearch-results.tsv` currently has a duplicated display iteration `24` from an external experiment. Supervisor progress uses physical row count, while research display numbering should use `max(numeric iteration column) + 1`.
