# Autoresearch Pilot

이 worktree는 `rrx`와 별도로 `uditgoenka/autoresearch` 루프를 비교하기 위한 격리 실험 공간이다.

## Scope

- 수정 허용: `packages/scripts/autoresearch/clean_model_config.json`
- 읽기 전용 참고:
  - `packages/scripts/autoresearch/run_autoresearch_verify.sh`
  - `packages/scripts/autoresearch/run_autoresearch_guard.sh`
  - `packages/scripts/autoresearch/tests/test_rrx_propose.py`
  - `packages/scripts/autoresearch/tests/test_seed_matrix_runner.py`
  - `packages/scripts/autoresearch/tests/test_dataset_artifacts.py`

## Goal

출전표 확정 시점 정보만 사용한 `unordered_top3` 예측에서
최근 기간 holdout 10시드 기준 `lowest_overall_holdout_hit_rate`를 높인다.

## Metric

- 이름: `lowest_overall_holdout_hit_rate`
- 방향: 높을수록 좋음
- verify command:

```bash
sh packages/scripts/autoresearch/run_autoresearch_verify.sh
```

verify는 숫자 하나만 stdout에 출력한다.
실험 인프라 실패나 invalid config면 non-zero exit로 끝난다.

## Guard

```bash
sh packages/scripts/autoresearch/run_autoresearch_guard.sh
```

## Current Baseline

- lowest: `0.362460`
- mean: `0.382201`
- max: `0.394822`

근거: `.autoresearch/outputs/holdout_seed_summary_report.json`

## Recommended Prompt

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

## Notes

- 이 worktree에는 project-level Codex skill로 `./.agents/skills/autoresearch` 가 설치되어 있다.
- 현재 주 저장소의 `rrx` 실험과 분리되어 있으므로 서로 상태 파일이 충돌하지 않는다.
- 실제 실행 기준은 [AUTORESEARCH_RUNBOOK.md](/Users/chsong/Developer/Personal/kra-analysis-autoresearch-pilot/AUTORESEARCH_RUNBOOK.md) 를 따른다.
