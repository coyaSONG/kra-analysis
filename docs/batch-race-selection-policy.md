# 배치 예측·평가 대상 KRA 경주 선정 정책

이 문서는 배치 예측과 최근 기간 홀드아웃 평가에서 `어떤 경주를 대상 경주로 인정할지`를 고정 규칙으로 선언한다. 실행 시 CLI 인자나 임시 입력으로 바꿀 수 없고, 저장소의 고정 정책과 설정 검증을 동시에 통과해야 한다.

## 정책 식별자

- `policy_version`: `kra-batch-race-selection-policy-v1`
- 구현 모듈: [packages/scripts/shared/batch_race_selection_policy.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/batch_race_selection_policy.py)
- 설정 반영 위치: [packages/scripts/autoresearch/clean_model_config.json](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/autoresearch/clean_model_config.json)

## 고정 선정 기준

1. 대상 범위는 `all_kra_races` 이다.
2. 공식 KRA 경마장 코드는 `1=서울`, `2=제주`, `3=부산경남` 으로 고정한다.
3. 출전표 확정 시점 strict selector는 `include_in_strict_dataset_true` 만 허용한다.
4. 결과 레이블이 존재하는 경주만 평가 대상으로 인정하므로 `required_result_status=collected` 를 요구한다.
5. `basic_data` 가 있어야 하고, pre-race 허용 필드만으로 payload 변환이 가능해야 한다.
6. 후보 말 필터링 후 활성 출전 수가 최소 3두여야 한다.
7. 정답 레이블은 중복 없는 top-3 한 세트여야 하고, 그 3두가 모두 최종 활성 출전군에 포함되어야 한다.
8. leakage check 를 통과한 경주만 배치 평가 대상으로 인정한다.

## 운영 계약

- 정책 블록의 `execution_input_override_allowed=false` 는 실행 입력으로 선정 기준을 덮어쓸 수 없음을 뜻한다.
- 설정 스키마는 `batch_target_selection` 이 저장소 기본 정책과 완전히 동일한지 검증한다.
- holdout manifest 의 `metadata.rule.batch_race_selection_policy_version` 에 동일 버전을 남겨서, 어떤 규칙으로 경주 집합이 확정됐는지 재현 가능하게 기록한다.
