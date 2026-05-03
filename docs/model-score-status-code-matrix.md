# 모델 점수 산출 상태 코드 기준표 v1

## 목적

이 문서는 `packages/scripts/autoresearch/prepare.py`의 `compute_score()` 단계에서 발생할 수 있는 실패, 결측, 보류 조건을 단일 기준표로 고정한다.

핵심 목표는 다음 네 가지다.

- `json_ok`, `coverage`, `set_match`, `avg_correct` 집계가 어떤 상태를 포함하는지 해석이 갈리지 않게 한다.
- 낮은 신뢰도에 따른 `보류`와 출력 스키마/정답 키의 `실패·결측`을 분리한다.
- 이후 `recent holdout` 10시드 반복, 운영 예측 로그, 재학습 자동화가 같은 상태 코드를 재사용할 수 있게 한다.
- 점수 산출 결과가 `race_status` DTO 아래에 상태 코드, 판정 사유, fallback 필요 여부를 같은 필드명으로 반환하게 한다.

기계판독용 원본은 [data/contracts/model_score_status_rules_v1.csv](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/model_score_status_rules_v1.csv) 이다.

## 우선순위 규칙

상태 코드는 아래 순서대로 처음 매칭되는 하나만 선택한다.

1. 정답 키(`actual`) 정합성 실패
2. 예측 payload 부재 또는 `predicted` 스키마 실패
3. `confidence` 결측 또는 비정상
4. 낮은 confidence 에 따른 보류
5. 정상 채점

이 우선순위는 "정답 데이터 오류", "예측 출력 오류", "의도적 보류"를 서로 섞지 않기 위한 것이다.

## 반환 DTO 계약

`compute_score()` 는 경주별 결과마다 아래 구조를 반환해야 한다.

```json
{
  "json_ok": true,
  "deferred": false,
  "race_status": {
    "status_code": "SCORED_OK",
    "status_class": "scored",
    "status_reason": "예측과 confidence가 모두 유효하며 정상 집계 대상이다.",
    "fallback_required": false,
    "fallback_action": "set_match 와 correct_count 를 정상 집계"
  },
  "status_code": "SCORED_OK",
  "status_class": "scored",
  "status_reason": "예측과 confidence가 모두 유효하며 정상 집계 대상이다.",
  "fallback_required": false,
  "fallback_action": "set_match 와 correct_count 를 정상 집계",
  "normalized_confidence": 0.72,
  "coverage_included": true,
  "score_aggregated": true,
  "set_match": 1.0,
  "correct_count": 3
}
```

- `race_status` 가 신규 정규 DTO다.
- top-level `status_code`, `status_class`, `status_reason`, `fallback_required`, `fallback_action` 은 기존 평탄 소비자를 위한 호환 alias다.
- `fallback_required=true` 이면 호출자는 `fallback_action` 을 읽어 후속 처리 또는 운영 기록을 결정해야 한다.

## 단일 기준표

| 우선순위 | 상태 코드 | 분류 | 반환 `status_reason` | 판정 규칙 | `json_ok` | `coverage` 분자 포함 | `set_match`/`avg_correct` 집계 | `fallback_required` | 대응 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | `FAIL_ACTUAL_TOP3_MISSING` | failed | 정답 키 `actual_top3` 구조가 누락되었거나 길이 3 계약을 만족하지 않는다. | `actual` 이 list 가 아니거나 길이가 3이 아님 | 아니오 | 예 | 아니오 | 예 | `set_match=0`, `correct_count=0`, answer key 복구 이슈로 기록 |
| 20 | `FAIL_ACTUAL_TOP3_INVALID` | failed | 정답 키 `actual_top3` 값이 양수 정수 3개로 정규화되지 않거나 중복이 있다. | `actual` 3개를 서로 다른 양수 정수로 정규화할 수 없음 | 아니오 | 예 | 아니오 | 예 | `set_match=0`, `correct_count=0`, 정답 키 정합성 이슈로 기록 |
| 30 | `FAIL_PREDICTION_PAYLOAD_MISSING` | failed | 예측 payload 자체가 dict 형태가 아니라 채점을 진행할 수 없다. | `prediction` 이 dict 가 아님 | 아니오 | 예 | 아니오 | 예 | `set_match=0`, `correct_count=0` |
| 40 | `MISSING_PREDICTED_TOP3` | missing | 예측 payload에 핵심 필드 `predicted_top3` 가 없다. | `prediction` dict 에 `predicted` 키가 없음 | 아니오 | 예 | 아니오 | 예 | `set_match=0`, `correct_count=0` |
| 50 | `FAIL_PREDICTED_TOP3_INVALID` | failed | `predicted_top3` 값이 양수 정수 3개로 정규화되지 않거나 중복이 있다. | `predicted` 가 길이 3 list 가 아니거나, 3개의 서로 다른 양수 정수로 정규화되지 않음 | 아니오 | 예 | 아니오 | 예 | `set_match=0`, `correct_count=0` |
| 60 | `MISSING_CONFIDENCE` | missing | `confidence` 값이 없어 보류/정상 채점 여부를 결정할 수 없다. | `confidence` 키가 없거나 `None`/빈 문자열임 | 아니오 | 예 | 아니오 | 예 | `set_match=0`, `correct_count=0` |
| 70 | `FAIL_CONFIDENCE_INVALID` | failed | `confidence` 값이 숫자 정규화 또는 `0..1` 범위 검증을 통과하지 못했다. | `confidence` 가 수치가 아니거나 정규화 후 `0..1` 범위를 벗어나거나 finite 하지 않음 | 아니오 | 예 | 아니오 | 예 | `set_match=0`, `correct_count=0` |
| 80 | `DEFERRED_LOW_CONFIDENCE` | deferred | 예측은 유효하지만 `confidence` 가 defer 임계값보다 낮아 집계에서 보류된다. | 모든 입력이 유효하고 `normalized_confidence < defer_threshold` | 예 | 아니오 | 아니오 | 예 | `set_match`, `correct_count` 는 계산하되 집계 제외 |
| 90 | `SCORED_OK` | scored | 예측과 `confidence` 가 모두 유효하며 정상 집계 대상이다. | 모든 입력이 유효하고 `normalized_confidence >= defer_threshold` | 예 | 예 | 예 | 아니오 | 정상 집계 |

## 집계 해석 규칙

- `json_ok`는 `DEFERRED_LOW_CONFIDENCE`, `SCORED_OK` 두 상태만 `true`다.
- `coverage` 는 기존 `prepare.py` 규칙을 유지해 `보류`만 제외한다. 즉 실패·결측은 `coverage` 분자에는 남고 `json_ok` 에서만 차감된다.
- `set_match`, `avg_correct` 는 `SCORED_OK` 상태만 집계한다.
- `DEFERRED_LOW_CONFIDENCE` 는 실패가 아니므로 raw `set_match`, `correct_count` 는 남겨 분석용으로 보존한다.

## 정규화 기준

- `predicted`, `actual` 은 길이 3의 list 여야 하며 각 원소는 양수 정수로 정규화 가능해야 한다.
- `predicted`, `actual` 모두 중복 말번호를 허용하지 않는다.
- `confidence` 는 우선 `float` 로 파싱한다.
- `confidence > 1.0` 이면 `0~100` 스케일로 보고 `100` 으로 나눈다.
- 정규화 후 `confidence` 는 finite 한 `0..1` 범위여야 한다.

## 구현 기준점

- 점수 산출 구현: [packages/scripts/autoresearch/prepare.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/autoresearch/prepare.py)
- 기계판독 계약: [packages/scripts/shared/model_score_status_schema.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/model_score_status_schema.py)
- 기준표 원본: [data/contracts/model_score_status_rules_v1.csv](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/model_score_status_rules_v1.csv)
