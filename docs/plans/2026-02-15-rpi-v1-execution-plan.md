# RPI v1 Execution Plan (2026-02-15)

## 1. Summary
이 문서는 KRA 예측 프롬프트 재귀개선(RPI) 실행 기준을 저장소 수준으로 고정한다.
핵심 원칙은 다음과 같다.

- 기존 `recursive_prompt_improvement_v5.py` 확장
- 평가 지표는 `success_rate` 단일 지표에서 `log_loss/brier/ece/top-k/roi/coverage`로 확장
- 누수(as-of) 검사 실패 시 승격 금지
- 챔피언-챌린저 승격 게이트를 코드로 강제

## 2. Public Interfaces

### 2.1 `evaluate_prompt_v3.py`
추가 옵션:

- `--report-format v1|v2` (default: `v2`)
- `--asof-check on|off` (default: `on`)
- `--topk 1,3[,5]` (default: `1,3`)
- `--metrics-profile rpi_v1` (default: `rpi_v1`)
- `--defer-threshold 0~1` (optional)

### 2.2 `recursive_prompt_improvement_v5.py`
추가 옵션:

- `--metrics-profile rpi_v1` (default: `rpi_v1`)
- `--selection-gate strict|balanced` (default: `strict`)
- `--time-split rolling|holdout` (default: `rolling`)
- `--defer-policy off|threshold|conformal-lite` (default: `threshold`)
- `--asof-check on|off` (default: `on`)

### 2.3 Report v2 schema
`evaluation` 출력 JSON에 다음 필드를 포함한다.

- `report_version`
- 기존 요약 필드(`prompt_version`, `test_date`, `total_races`, `valid_predictions`, `success_rate` 등)
- `metrics_v2`
- `leakage_check`
- `promotion_context`

## 3. Gate Rules
기본 게이트는 `strict`다.

- 조건 A: `challenger.log_loss < champion.log_loss`
- 조건 B: `challenger.ece <= champion.ece`
- 조건 C: `challenger.top3` 개선 또는 `challenger.roi.avg_roi` 개선
- 조건 D: `leakage_check.passed == true`

A~D를 모두 만족할 때만 승격한다.

실패 사유 코드는 다음 중 하나를 사용한다.

- `leakage_check_failed`
- `log_loss_not_improved`
- `ece_regressed`
- `no_top3_or_roi_improvement`

## 4. Leakage Control

### 4.1 Forbidden fields
입력 데이터에서 아래 사후 필드가 의미 있는 값으로 존재하면 누수로 판단한다.

- `rank`, `ord`, `rcTime`, `result`, `resultTime`
- `finish_position`, `top3`, `actual_result`
- `dividend`, `payout`

### 4.2 Enforcement
- `evaluate_prompt_v3.py`에서 `--asof-check on`일 때 누수 검사 실행
- 누수 결과를 `leakage_check`로 리포트에 기록
- RPI 승격 게이트에서 누수 실패 시 자동 롤백

## 5. Metrics Semantics (v1)
현재 파이프라인의 출력 제약(top-3 + confidence)을 고려해 다음과 같이 계산한다.

- `log_loss`, `brier`, `ece`: binary event 기준
  event = "예측 top1 == 실제 1착"
  probability = `confidence` (0~1로 정규화)
- `top_k`: 실제 1착이 예측 상위 k에 포함되는 비율
- `roi.avg_roi`: 예측 top1 단위베팅 수익 평균
- `coverage`: 디퍼 임계값 적용 후 유지된 샘플 비율

## 6. Artifacts

- 평가 리포트: `packages/scripts/data/prompt_evaluation/evaluation_<version>_<timestamp>.json`
- 챔피언 히스토리: `packages/scripts/data/prompt_evaluation/champion_history.jsonl`
- 반복 분석: `packages/scripts/data/recursive_improvement_v5/<timestamp>/`

## 7. Test Scenarios

- `metrics` 계산 검증
- `report_schema` 구조 검증
- `leakage_checks` 누수 탐지 검증
- `should_promote_challenger` 게이트 검증

실행 예시:

```bash
cd packages/scripts
uv run pytest -q tests/test_metrics.py tests/test_report_schema.py tests/test_leakage_checks.py tests/test_recursive_gate.py
```

## 8. Assumptions / Defaults

- 기본 실행은 `strict` 게이트를 사용한다.
- `time_split`/`defer_policy`는 현재 메타 정보 및 옵션 제어 수준으로 도입하며,
  실제 고급 분할/컨포멀 정책은 후속 구현에서 확장한다.
- 기존 `success_rate` 흐름은 유지하되 승격 판단은 `metrics_v2 + leakage_check`를 우선한다.
