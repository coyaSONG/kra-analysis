# 출전표 확정 시점 데이터 화이트리스트·블랙리스트 정책 v1

## 목적

이 문서는 KRA 전 경주 top-3 무순서 예측 시스템에서 `출전표 확정 시점까지 실제로 사용 가능한 정보`만 모델 입력으로 허용하기 위한 운영 기준선이다. 목표는 다음 4가지다.

- 출전표 확정 시점(`L0`) 이전에 확보 가능한 원천과 필드만 feature 입력으로 허용한다.
- 같은 API 안에 사전/사후 필드가 섞인 경우에도 필드 단위로 허용/금지 여부를 고정한다.
- 결과, 배당, 실황, 사후 파생치가 연구 코드나 자동 피처 탐색에서 다시 섞여 들어오는 것을 방지한다.
- 홀드아웃 재생, 자동 재학습, 실전 예측 생성이 모두 같은 데이터 정책을 따르도록 한다.

이 문서는 "무엇을 써도 되는가"를 정의한다. 시각 산출과 홀드아웃 분할 자체는 아래 문서를 따른다.

- [홀드아웃 출전표 확정 시점 산출 규칙](/Users/chsong/Developer/Personal/kra-analysis/docs/holdout-entry-finalization-rule.md)
- [최근 기간 홀드아웃 평가 분할 규칙](/Users/chsong/Developer/Personal/kra-analysis/docs/recent-holdout-split-rule.md)
- [KRA 경주 라이프사이클 시점 매트릭스](/Users/chsong/Developer/Personal/kra-analysis/docs/kra-race-lifecycle-timing-matrix.md)
- [출전표 확정 시점 공통 스키마 및 원천 필드 매핑](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-source-schema.md)
- [현재 예측 입력 필드 레지스트리](/Users/chsong/Developer/Personal/kra-analysis/docs/prediction-input-field-registry.md)

## 판정 원칙

1. 최종 모델 입력은 선택된 리비전의 `entry_finalized_at` 이하에서 수집된 값만 허용한다.
2. hard-required source는 `API214_1`, `API72_2`, `API189_1`, `API9_1`이다. 이 네 소스가 없으면 해당 리비전은 운영용 snapshot으로 인정하지 않는다.
3. soft-required source는 `API8_2`, `API12_1`, `API19_1`, `API11_1`, `API14_1`, `API329`이다. 일부 실패해도 경주 예측은 계속 생성해야 하므로 빈 블록/null 허용이다.
4. 같은 원천이라도 필드별로 허용/금지를 따진다. 특히 `API214_1`은 혼합 원천이므로 raw 전체를 모델 입력으로 사용하면 안 된다.
5. 파생 피처는 사용한 원천 중 가장 늦은 시점을 상속한다. 원천 하나라도 `L+1` 금지 데이터면 파생 피처도 금지다.
6. cutoff 이후 재수집 값이 기존 `L0` snapshot을 덮어쓰면 안 된다. 운영·홀드아웃 재생 모두 pre-cutoff snapshot immutability를 전제로 한다.

## 허용 데이터 범주와 예외 규칙

Sub-AC 3 기준으로 허용 데이터는 아래 범주로 고정하고, 각 범주의 시간 경계/예외 규칙을
[prerace_field_validation_spec_v1.csv](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/prerace_field_validation_spec_v1.csv)
의 `allowed_data_category`, `time_boundary_rule`, `exception_rule` 컬럼에 등록한다.

| 범주 | 대표 필드/블록 | 허용 조건 | 시간 경계 규칙 | 대표 예외 규칙 |
| --- | --- | --- | --- | --- |
| `core_card_direct` | `horses[].chul_no`, `hr_no`, `jk_no`, `tr_no`, `ow_no` | 출전표 핵심 카드 값이 cutoff 전에 확정돼 있어야 함 | `VALUE_AT_OR_BEFORE_ENTRY_FINALIZED_AT` | `ENTRY_DROP_FROM_OPERATIONAL_SNAPSHOT` |
| `race_plan_direct` | `race_plan.rank`, `race_plan.rc_dist`, `race_plan.budam` | 경주계획표 사전 공지값을 direct 사용 | `VALUE_AT_OR_BEFORE_ENTRY_FINALIZED_AT` | `NONE` |
| `snapshot_locked_race_state` | `track.*`, `cancelled_horses[]`, `horses[].training` | cutoff 이전 snapshot 잠금본만 허용 | `SNAPSHOT_CAPTURED_AT_OR_BEFORE_ENTRY_FINALIZED_AT` | `KEEP_LOCKED_SNAPSHOT`, `SOFT_FAIL_EMPTY_BLOCK` |
| `stored_detail_lookup` | `hrDetail.*`, `jkDetail.*`, `trDetail.*`, `jkStats.*`, `owDetail.*` | 당시 저장본으로만 조인 | `STORED_ROW_AT_OR_BEFORE_ENTRY_FINALIZED_AT` | `KEEP_STORED_AS_OF_SNAPSHOT` |
| `historical_aggregate` | `horses[].past_stats.*`, `recent_top3_rate`, `recent_win_rate` | 현재 경주보다 과거 결과만 집계 | `LOOKBACK_EVENT_DATE_STRICTLY_BEFORE_RACE_DATE` | `STRICT_PAST_ONLY` |
| `timing_unverified_market` | `horses[].win_odds`, `horses[].plc_odds`, `odds_rank` | 공개 시점 실측 전까지 운영 승격 금지 | `MEASUREMENT_REQUIRED_BEFORE_ENTRY_USE` | `RAW_STORE_ONLY` |

검증 규격에 위 범주가 없거나, 범주에 맞는 시간 경계 규칙이 비어 있으면 해당 필드는 운영 기준선 미등록으로 본다.

## 시점 조건

### 1. 입력 허용 기준

- `source_timestamp <= entry_finalized_at`
- `entry_finalized_at <= operational_cutoff_at`
- hard-required source는 같은 리비전 안에서 모두 충족해야 한다.

### 2. 재조회 금지 기준

- 과거 경주를 재평가할 때 결과 확정 후 다시 조회한 값으로 `L0` 입력을 재구성하면 안 된다.
- 과거 snapshot 복원은 당시 저장된 `basic_data` 또는 source-level revision timestamp만 사용한다.

### 3. 변동 필드 고정 기준

다음 필드는 `L0`에도 존재할 수 있지만 확정 후 변동될 수 있으므로 `L0 snapshot`으로 고정된 값만 허용한다.

- `track.*`
- `cancelled_horses[]`
- `race_plan.sch_st_time`
- `horses[].training`

## 모델 입력 화이트리스트

### A. 운영 필수 화이트리스트

| 원천 | 허용 필드군 | 용도 | 시점 조건 |
| --- | --- | --- | --- |
| `API214_1` | `rcDate`, `rcNo`, `meet`, `chulNo`, `hrNo`, `hrName`, `jkNo`, `jkName`, `trNo`, `trName`, `owNo`, `owName`, `age`, `sex`, `name`, `rank`, `rating`, `wgBudam`, `wgBudamBigo`, `wgHr`, `ilsu`, `hrTool` | 출전표 핵심 정보 | 선택 리비전의 pre-cutoff 값만 허용 |
| `API72_2` | `rank`, `budam`, `rcDist`, `ageCond`, `sexCond`, `schStTime`, `chaksun1..5` | 경주 조건, 상금 구조, 예정 시각 | `rcNo` 일치 row만 사용, `schStTime`은 pre-cutoff 값만 허용 |
| `API189_1` | `weather`, `track`, `waterPercent`, `temperature`, `humidity`, `windDirection`, `windSpeed` | 날씨·주로 상태 | `L0` snapshot으로 캡처된 값만 허용 |
| `API9_1` | 취소 row 전체를 정규화한 `cancelled_horses[]` | 취소 반영, 활성 출전마 판정 보조 | pre-cutoff 리비전만 허용 |

추가 규칙:

- `API214_1.rank`는 결과 순위가 아니라 등급 문자열이므로 저장 가능하다. 모델 입력 변환 시 이름을 반드시 `class_rank`로 바꾼다.
- `API9_1`은 빈 배열도 정상 수집으로 인정한다.
- 운영용 snapshot은 활성 출전마가 3두 이상 남아야 한다.

### B. 성능 고도화 화이트리스트

| 원천 | 허용 필드군 | 용도 | 시점 조건 |
| --- | --- | --- | --- |
| `API8_2` | `horses[].hrDetail.*` | 말 누적 성적, 혈통, 과거 이력 | pre-cutoff 저장본만 허용 |
| `API12_1` | `horses[].jkDetail.*` | 기수 프로필 | pre-cutoff 저장본만 허용 |
| `API19_1` | `horses[].trDetail.*` | 조교사 프로필 | pre-cutoff 저장본만 허용 |
| `API11_1` | `horses[].jkStats.*` | 기수 누적 성적 | pre-cutoff 저장본만 허용 |
| `API14_1` | `horses[].owDetail.*` | 마주 누적 정보 | pre-cutoff 저장본만 허용 |
| `API329` | `horses[].training.*` | 조교 현황 | pre-cutoff 저장본만 허용, 이름 매칭 실패는 빈 블록 |

추가 규칙:

- soft source 일부 누락은 경주 제외 사유가 아니다.
- soft source를 쓰는 파생 피처는 반드시 원천 timestamp audit가 가능해야 한다.
- `API329`는 현재 `hrName` 매칭 기반이므로 동명이마/미매칭 위험을 feature importance 해석에 함께 기록해야 한다.

## 저장은 허용하지만 모델 입력에는 직접 넣지 않는 데이터

| 데이터 | 허용 범위 | 금지 범위 |
| --- | --- | --- |
| `race_info.response.body.items.item[]` raw envelope | 원본 보존, 디버깅, 필드 인벤토리, 재가공 기준선 | raw 전체를 그대로 모델 입력에 전달하는 행위 금지 |
| `collected_at`, `status`, `failed_horses[]` | 시점 감사, 품질 모니터링, 재수집 진단 | 예측 feature 사용 금지 |
| `result_data`, top-3 answer key | 학습 라벨, 평가 정답, 품질 검증 | feature 결합 금지 |

## 모델 입력 블랙리스트

### A. 원천 수준 블랙리스트

아래 소스는 출전표 확정 이후 정보이거나 현재 운영 목표와 충돌하므로 모델 입력에서 금지한다.

| 원천 | 금지 이유 |
| --- | --- |
| `API160_1` | 결과/사후 배당 성격의 odds 원천 |
| `API301` | 결과 확정 이후 정보 |
| 내부 `race_odds` 테이블 | cutoff 이후 odds 적재 경로를 포함 |
| 내부 `result_data` 및 결과 수집 경로 산출물 | 정답/사후 결과 데이터 |

### B. 혼합 원천 내부의 금지 필드

아래 필드는 특히 `API214_1` raw, 결과 payload, 자동 피처 탐색 코드에서 다시 들어오기 쉬우므로 명시적으로 금지한다.

| 금지 필드군 | 예시 |
| --- | --- |
| 결과 확정 필드 | `ord`, `ordBigo`, `rcTime`, `result`, `resultTime`, `finish_position`, `top3`, `actual_result` |
| 결과 파생 필드 | `diffUnit`, `rankRise` |
| 배당/환급 확정 필드 | `dividend`, `payout` |
| 구간 통과 순위/시간 필드 | `sj*`, `bu*`, `se*` 패턴의 `Ord`, `AccTime`, `GTime` |
| 현재 경주 실황에서만 생기는 코너/구간 파생치 | `sjG1fOrd`, `buG6fOrd`, `se_1cAccTime` 등 전체 패턴 |

추가 규칙:

- 위 금지 필드는 raw payload 안에 저장돼 있어도 모델 입력 생성 단계에서 반드시 제거해야 한다.
- 위 금지 필드를 포함한 파생 피처, 랭크 피처, normalization 결과도 모두 금지다.
- "예측력이 지나치게 높은 신규 피처"는 먼저 누수 후보로 분류하고 실시간 미발주 경주 API로 교차 검증해야 한다.

### C. 결과/사후 정보를 암묵적으로 포함하는 파생 피처 블랙리스트

다음 유형의 파생 피처는 명시적 필드명이 달라도 금지한다.

- 현재 경주의 top-3 결과를 직접 또는 간접적으로 복원하는 피처
- 현재 경주의 확정 배당, 환급금, 인기 확정 순위를 이용한 피처
- 현재 경주의 구간 통과 위치, 누적 시간, 결승 기록을 사용한 피처
- 결과 수집 이후 다시 조회한 값으로 만들어진 "사후 보정" 피처

### D. 최종 운영 데이터셋 차단 카탈로그

향후 데이터셋 생성 자동 검증은 아래 4개 그룹을 기준으로 실패시켜야 한다. 기준 구현은
[prerace_field_policy.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prerace_field_policy.py)
의 `validate_operational_dataset_payload()` 이다.

| 그룹 | 최종 차단 목록 |
| --- | --- |
| `HOLD` exact path | `horses[].win_odds`, `horses[].plc_odds`, `horses[].computed_features.odds_rank` |
| `BLOCK` leaf key | `ord`, `ordBigo`, `rankRise`, `diffUnit`, `rcTime`, `result`, `resultTime`, `finish_position`, `dividend`, `payout` |
| `BLOCK` prefix path | `race_odds.*` |
| `LABEL_ONLY` | `top3`, `is_top3`, `actual_result`, `result_data.*` |
| `META_ONLY` | `snapshot_meta.*`, `field_policy.*`, `source_field_tags.*` |

주의:

- 위 목록은 **최종 운영 데이터셋 export 기준**이다.
- raw ingress 누수 검사는 별도로 [leakage_checks.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/evaluation/leakage_checks.py)
  를 유지한다.
- raw 단계에서는 `rank`, `top3`, `actual_result`, 구간 패턴(`sj|bu|se` + `Ord/AccTime/GTime`)을 더 보수적으로 막고,
  canonical export 단계에서는 `class_rank` 같은 변환 결과만 허용한다.

## 보류 목록

아래 데이터는 저장소에 존재하거나 일부 운영 로직에서 보조적으로 쓰이지만, 최종 성공 판정용 feature로는 아직 화이트리스트에 넣지 않는다.

| 데이터 | 현재 취급 |
| --- | --- |
| `horses[].win_odds`, `horses[].plc_odds` 수치 자체 | `L0` 공개 시점 실측 검증 전까지 성공 판정용 feature 사용 보류 |
| `win_odds == 0` 여부 | 활성 출전마 필터링 보조 신호로만 제한 허용 |

즉, odds 수치 자체를 모델 성능 핵심 feature로 주장하려면 "출전표 확정 시점에 안정적으로 공개된다"는 실측 로그가 먼저 필요하다.

## 운영 적용 규칙

1. snapshot 생성기는 화이트리스트 외 필드를 모델 입력 직렬화 단계에서 제거해야 한다.
2. 누수 검사는 최소한 [packages/scripts/evaluation/leakage_checks.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/evaluation/leakage_checks.py) 의 금지 필드군을 포함해야 한다.
3. 새 source/API를 추가할 때는 이 문서에 먼저 분류를 추가한 뒤 수집 파이프라인에 반영해야 한다.
4. hard-required source timestamp와 revision 이력을 저장하지 못하면 strict replay 최종 인증에 사용할 수 없다.
5. cutoff 이후 정정/재발행은 운영 로그와 결과 해석에는 남기되, 이미 잠긴 예측 입력을 덮어쓰면 안 된다.

## 자동 검증 체크리스트

데이터셋 생성기 또는 snapshot export 검증은 아래 체크리스트를 모두 통과해야 한다.

1. `ALLOW`, `ALLOW_SNAPSHOT_ONLY`, `ALLOW_STORED_ONLY` 외 플래그가 최종 export payload에 남아 있지 않아야 한다.
2. `HOLD` 필드가 하나라도 남아 있으면 운영 데이터셋 생성 실패로 처리한다.
3. `BLOCK` 필드 또는 `race_odds.*` 블록이 남아 있으면 즉시 실패한다.
4. `LABEL_ONLY` 필드(`top3`, `is_top3`, `actual_result`, `result_data.*`)가 feature payload에 남아 있으면 실패한다.
5. `META_ONLY` 블록(`snapshot_meta.*`, `field_policy.*`, `source_field_tags.*`)이 feature payload에 남아 있으면 실패한다.
6. raw ingress 단계에서는 `check_detailed_results_for_leakage()` 도 함께 실행해 `rank`, 결과/배당 필드, 구간 순위/시간 패턴이 다시 유입되지 않았는지 확인한다.

즉, 자동 검증은 **raw ingress guard + canonical export guard** 의 2단 구조로 운영한다.

## 현재 예측 입력 표준

- 현재 `ralph` 탐색 후보군과 `research_clean.py` 입력 후보 전체의 canonical registry는 [prediction_input_field_registry_v1.csv](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/prediction_input_field_registry_v1.csv) 이다.
- 이 레지스트리에서 `train_inference_flag` 가 `ALLOW`, `ALLOW_SNAPSHOT_ONLY`, `ALLOW_STORED_ONLY` 인 필드만 최종 운영 후보로 인정한다.
- `HOLD` 로 분류된 `winOdds`, `plcOdds`, `odds_rank`, `winOdds_rr`, `plcOdds_rr` 는 연구 저장은 가능하지만 최근 기간 홀드아웃 최종 성공 판정과 실전 운영 직전 기준에서는 제외한다.

## 구현 기준선

- [packages/scripts/shared/prerace_source_schema.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prerace_source_schema.py)
- [packages/scripts/evaluation/leakage_checks.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/evaluation/leakage_checks.py)
- [apps/api/services/race_processing_workflow.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/race_processing_workflow.py)
- [apps/api/services/result_collection_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/result_collection_service.py)
- [docs/knowledge/discovery-2026-03-15-sectional-data-leakage.md](/Users/chsong/Developer/Personal/kra-analysis/docs/knowledge/discovery-2026-03-15-sectional-data-leakage.md)
