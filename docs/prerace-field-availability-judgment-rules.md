# 출전표 확정 시점 가용성 판정 규칙 v1

## 목적

이 문서는 KRA 원천 필드와 현재 저장소가 생성하는 가공 필드를 한 번에 분류해, 각 필드가 언제 처음 공개되는지, 이후 갱신될 수 있는지, 어떤 근거로 판정했는지를 운영 규칙으로 고정한다.

이 문서의 목표는 다음 4가지다.

- 출전표 확정 시점 이전에 사용할 수 있는 필드와 사후 필드를 필드군 단위로 분리한다.
- 원천 필드뿐 아니라 `computed_features`, 과거 통계, 내부 메타데이터까지 함께 분류한다.
- 최종 운영 feature whitelist, 홀드아웃 재생, 자동 재학습이 같은 판정 규칙을 따르도록 한다.
- 판정 근거를 "공식 엔드포인트 목록", "현재 수집 경로", "사후 수집 경로", "가공 코드"에 연결한다.

관련 기준 문서:

- [출전표 확정 시점 표준 필드 카탈로그 v1](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-standard-field-catalog.md)
- [출전표 확정 시점 필드 메타데이터 스키마 v1](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-field-metadata-schema.md)
- [KRA 경주 라이프사이클 시점 매트릭스 v1](/Users/chsong/Developer/Personal/kra-analysis/docs/kra-race-lifecycle-timing-matrix.md)
- [DB 테이블·컬럼 가용 시점 매핑 v1](/Users/chsong/Developer/Personal/kra-analysis/docs/table-column-availability-map.md)
- [출전표 확정 시점 데이터 화이트리스트·블랙리스트 정책 v1](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-data-whitelist-blacklist-policy.md)
- [홀드아웃 출전표 확정 시점 산출 규칙 v1](/Users/chsong/Developer/Personal/kra-analysis/docs/holdout-entry-finalization-rule.md)
- [출전표 정규화·조인 전처리 규칙 v1 CSV](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/prerace_entry_preprocessing_rules_v1.csv)

## 근거 우선순위

필드 가용 시점은 아래 순서로 판정한다.

1. 공식 엔드포인트 등록 근거
   - [data-go-kr-api-application.md](/Users/chsong/Developer/Personal/kra-analysis/docs/prompts/data-go-kr-api-application.md)
2. 현재 런타임 수집 경로
   - [kra_api_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/kra_api_service.py)
   - [collection_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/collection_service.py)
   - [race_processing_workflow.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/race_processing_workflow.py)
3. 사후 결과/배당 수집 경로
   - [result_collection_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/result_collection_service.py)
   - [leakage_checks.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/evaluation/leakage_checks.py)
4. 가공 필드 생성 경로
   - [feature_engineering.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/feature_engineering.py)
   - [db_client.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/db_client.py)

공식 문서와 런타임 경로가 충돌하면, 최종 운영 판정은 더 보수적인 쪽을 택한다.

## 판정 라벨

### 최초 공개 시점

| 라벨 | 의미 |
| --- | --- |
| `L-1` | 출전표 확정 전에도 조회 가능한 누적/마스터 정보 |
| `L0` | 출전표 확정 시점에 최초 운영 사용 가능 |
| `L0 snapshot` | `L0`에 존재하지만 이후 값이 바뀔 수 있어 cutoff 시점 스냅샷만 허용 |
| `?` | 저장소 근거만으로 최초 공개 시점을 단정할 수 없어 실측 검증 필요 |
| `L+1` | 출전표 확정 후 또는 결과 확정 후에만 의미가 생김 |

### 갱신 가능 여부

| 값 | 의미 |
| --- | --- |
| `불변` | 동일 식별자에 대해 운영상 다시 변하지 않는다고 간주 |
| `가변` | cutoff 이후 값이 바뀔 수 있으므로 최초 정상 snapshot을 고정해야 함 |
| `재조회 의존` | 값 자체는 사전 정보지만 과거 재조회 시 최신 상태로 바뀔 수 있어 당시 저장본만 허용 |
| `사후 전용` | 결과/배당 확정 뒤에만 생성되거나 저장됨 |

### 학습·추론 공통 플래그

| 플래그 | 의미 |
| --- | --- |
| `ALLOW` | 출전표 확정 시점 기준으로 바로 학습/추론 입력 허용 |
| `ALLOW_SNAPSHOT_ONLY` | cutoff 이전에 잠긴 snapshot 값만 허용 |
| `ALLOW_STORED_ONLY` | 사전 정보지만 과거 재조회 오염 방지를 위해 당시 저장본만 허용 |
| `HOLD` | raw 저장과 연구는 가능하지만 최종 학습/추론 입력에서는 제외 |
| `BLOCK` | 사후/누수 필드라서 입력 금지 |
| `LABEL_ONLY` | 정답/라벨 전용 |
| `META_ONLY` | 시점 감사/운영 메타데이터 전용 |

## 판정 규칙

1. `result_collection_service.py` 에서만 수집하거나 그 경로가 명시적으로 호출하는 원천은 기본적으로 `L+1`이다.
2. `API214_1` 같이 사전/사후 필드가 섞인 원천은 API 단위가 아니라 필드군 단위로 나눈다.
3. `track.*`, `cancelled_horses[]`, `race_plan.sch_st_time`, `horses[].training` 같이 변동 가능한 사전 필드는 `L0 snapshot`으로만 허용한다.
4. 가공 필드는 입력 원천 중 가장 늦은 시점을 상속한다.
5. 가공 필드가 `winOdds` 또는 `plcOdds`에 의존하면, 해당 필드는 odds 공개 시점 실측 전까지 `보류`다.
6. 과거 통계는 반드시 기준 경주일 이전 데이터만 사용해야 하며, 현재 저장소에서는 [db_client.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/db_client.py) 의 `r.date < race_date` 조건이 그 근거다.
7. 내부 메타데이터는 시점 감사에는 필요하지만 모델 입력에는 직접 사용하지 않는다.
8. 학습·추론 코드의 최종 포함 여부는 [prerace_field_policy.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prerace_field_policy.py) 의 `train_inference_flag` 해석을 따른다.
9. 조인 블록이나 파생 컬럼도 독립 필드처럼 메타데이터를 가져야 하며, 최소한 `source_field`, `join_key`, `exception_rule` 에 조합 근거를 남겨야 한다.

## 조인 컬럼 판정 규칙

조인 컬럼은 "원천 블록 하나를 붙였다"가 아니라 아래 4가지를 모두 만족할 때만 출전표 확정 시점 입력으로 인정한다.

1. **조인 키가 cutoff 이전에 확정되어 있어야 한다.**
   - `hr_no`, `jk_no`, `tr_no`, `ow_no` 같이 `API214_1` 핵심 카드에서 나오는 canonical key가 기본이다.
   - 조인 키가 `L+1` 이거나 결과 수집 후 생성되는 값이면 해당 조인은 즉시 `BLOCK` 이다.
2. **조인 대상 원천이 cutoff 이전에 조회 가능해야 한다.**
   - `API8_2`, `API12_1`, `API19_1`, `API11_1`, `API14_1` 처럼 `L-1` 또는 `L0 snapshot` 원천이면 후보가 될 수 있다.
   - `API160_1`, `API301`, `result_data` 처럼 `L+1` 원천이면 조인 결과도 전부 금지다.
3. **과거 홀드아웃 재생 시 당시 저장본으로 재현 가능해야 한다.**
   - 과거 경주를 다시 조회해서 최신 누적값으로 붙이면 `재조회 의존` 오염이므로 `ALLOW_STORED_ONLY` 또는 그보다 보수적인 판정만 허용한다.
4. **조인 실패 시의 운영 처리 방침이 고정돼 있어야 한다.**
   - `모든 경주 예측 생성` 제약 때문에 soft source 조인은 기본적으로 `빈 dict/null 유지 + 예측 계속` 이어야 한다.
   - hard-required key 자체가 깨지면 field null이 아니라 `entry_drop_from_operational_snapshot` 또는 `race_quarantine` 으로 올린다.

### 조인 유형별 판정표

| 조인 유형 | 예시 | 선행 조건 | 시점/플래그 상한 | 예외 처리 기준 |
| --- | --- | --- | --- | --- |
| 결정적 ID 조인 | `horses[].hrDetail <- hr_no`, `jkDetail <- jk_no`, `trDetail <- tr_no`, `owDetail <- ow_no` | 정규화된 canonical ID 존재, 조인 대상이 pre-cutoff 저장본에 존재 | 기본 `L-1`, 최종 플래그는 `ALLOW_STORED_ONLY` 상한 | 미조인 시 `empty dict`, `*_missing` flag, 예측 계속 |
| 결정적 ID 조인의 누적 통계 조인 | `horses[].jkStats <- jk_no` | ID 일치 + 누적 수치가 비음수/정상 범위 | 기본 `L-1`, `ALLOW_STORED_ONLY` | 파싱 실패는 field null, 원천 row 전체는 raw 보존 |
| 동일 경주 내부 조인/집계 | `field_size`, `rating_rank`, `wg_budam_rank`, `gap_3rd_4th` | 동일 snapshot 안의 활성 출전마 집합만 사용 | 부모 필드 중 가장 늦은 시점 상속 | 취소 반영 필드는 `ALLOW_SNAPSHOT_ONLY`, 그 외는 부모 상속 |
| 과거 DB 히스토리 조인 | `past_stats`, `recent_top3_rate`, `recent_win_rate` | 집계 조건이 현재 경주보다 과거만 참조 | 현재 구현 기준 `L0`, `ALLOW` | 집계 실패는 null 허용, 현재 경주 결과 참조 시 즉시 `BLOCK` |
| 이름/퍼지 매칭 조인 | `horses[].training <- hr_name` | canonical ID 부재, 이름 매칭 로그와 실패 flag 필요 | `L0 snapshot`, `ALLOW_SNAPSHOT_ONLY` 또는 더 보수적 | `training_unmatched` 는 soft-fail, 예측 계속 |
| odds/시장 신호 조인 | `win_odds`, `plc_odds`, `odds_rank` | 공개 시점 실측 완료 전에는 불충분 | 현재는 `?`, `HOLD` | raw 저장만 허용, 성공 판정 feature 금지 |
| 결과/배당/사후 조인 | `result_data`, `race_odds`, `actual_result`, `finish_position` | 없음. 항상 금지 | `L+1`, `BLOCK` 또는 `LABEL_ONLY` | 예외 없음 |

### 조인 키 표기 규칙

- 메타데이터 CSV의 `join_key` 는 "무슨 값으로 붙였는가"를 사람이 다시 추적할 수 있어야 한다.
- 단일 key는 `horses[].hr_no -> hrDetail.hrNo` 처럼 표기한다.
- 복합/보조 key는 `horses[].hr_name -> training.hrName (fallback)` 처럼 fallback 여부까지 남긴다.
- 조인 키가 문자열 정규화에 의존하면 `notes` 또는 `exception_rule` 에 `strip_decimal_suffix`, `owner_id_string_cast`, `id_normalized` 같은 보정 근거를 함께 적는다.

## 파생 컬럼 판정 규칙

파생 컬럼은 "코드에서 새로 만들었다"가 아니라 입력 원천의 시점과 예외를 그대로 상속하는 필드다. 판정은 아래 순서로 고정한다.

1. **원천 집합 수집**
   - `source_field` 에 직접 사용한 원천 필드와 조인 블록을 모두 적는다.
   - race-relative 파생이면 `|race-relative rank`, `|same-race aggregate` 같은 범위를 명시한다.
2. **시점 상한 계산**
   - 파생 컬럼의 `availability_stage` 는 부모 중 가장 늦은 시점을 상속한다.
   - 부모 중 하나라도 `L0 snapshot` 이면 파생도 최소 `L0 snapshot` 이다.
   - 부모 중 하나라도 `?` 이면 파생도 최소 `?` 이다.
   - 부모 중 하나라도 `L+1` 이면 파생은 무조건 `L+1` 이고 입력 금지다.
3. **플래그 상한 계산**
   - 부모 중 `BLOCK` 이 있으면 파생도 `BLOCK`.
   - 부모 중 `LABEL_ONLY` 만으로 성립하면 파생도 `LABEL_ONLY`.
   - 부모 중 `HOLD` 가 있고 `BLOCK` 은 없으면 파생은 `HOLD`.
   - 부모가 `ALLOW`, `ALLOW_SNAPSHOT_ONLY`, `ALLOW_STORED_ONLY` 만 있으면 가장 보수적인 플래그를 따른다.
4. **동일 경주 상대 파생 보정**
   - `rating_rank`, `wg_budam_rank`, `draw_rr` 처럼 같은 경주 안에서만 상대화한 피처는 부모의 시점은 그대로 유지한다.
   - 단, 취소 반영 live field를 사용하면 `ALLOW_SNAPSHOT_ONLY` 로 올린다.
5. **히스토리 집계 보정**
   - 과거 DB 집계는 현재 경주보다 엄격히 과거인 row만 허용한다.
   - 현재 구현처럼 `r.date < race_date` 를 쓰는 경우, 동일 날짜 이전 경주는 보수적으로 제외한 것으로 간주한다.

### 파생 유형별 판정표

| 파생 유형 | 예시 | 판정 규칙 | 현재 결론 |
| --- | --- | --- | --- |
| 직접 단항 파생 | `age_prime`, `rest_risk`, `country`, `weight`, `weight_delta` | 단일 부모 필드 시점/플래그 상속 | `age`, `ilsu`, `wg_hr`, `name` 기반 허용 |
| 누적 통계 비율 파생 | `horse_win_rate`, `trainer_place_rate`, `owner_skill` | 조인된 detail/stats 블록이 `ALLOW_STORED_ONLY` 면 파생도 동일 | `ALLOW_STORED_ONLY` |
| 동일 경주 순위 파생 | `rating_rank`, `horse_skill_rank`, `jk_skill_rank`, `tr_skill_rank`, `wg_budam_rank` | 같은 snapshot 내부 정렬이면 부모 상속 | 대부분 `ALLOW` |
| 동일 경주 live context 파생 | `field_size_live`, `cancelled_count`, `wet_track`, `recent_training` | 취소/주로/조교 snapshot 의존이면 `ALLOW_SNAPSHOT_ONLY` | `ALLOW_SNAPSHOT_ONLY` |
| odds 의존 파생 | `odds_rank`, `winOdds_rr`, `plcOdds_rr` | 부모 odds가 `HOLD` 면 파생도 `HOLD` | 운영 보류 |
| 결과 복원 파생 | `top3`, `is_top3`, 현재 경주 성적 기반 정규화 | 결과/사후 필드 포함 시 즉시 차단 | `LABEL_ONLY` 또는 `BLOCK` |

## 예외 처리 기준

`exception_rule` 은 자유서술 메모가 아니라 운영 행동을 고정하는 규칙이어야 한다. 아래 taxonomy를 우선 사용한다.

| 예외 규칙 | 언제 쓰는가 | 운영 영향 | 대표 예시 |
| --- | --- | --- | --- |
| `cutoff 이전 최초 정상 snapshot만 허용` | 값이 사전 정보지만 이후 변동 가능 | 과거 replay/운영 모두 최초 정상본 고정 | `track.*`, `cancelled_horses[]`, `sch_st_time`, `training` |
| `당시 저장본만 허용` | pre-cutoff 정보지만 재조회하면 최신값으로 바뀔 수 있음 | 홀드아웃 재생 시 live 재조회 금지 | `hrDetail`, `jkDetail`, `trDetail`, `jkStats`, `owDetail` |
| `soft-fail empty block` | soft source 조인 실패가 전체 예측 실패 사유가 아니어야 함 | 빈 dict/null 유지, 예측 계속 | `training_missing`, `hrdetail_missing` |
| `field_null_only` | 개별 필드 파싱 실패가 출전마 제외 사유는 아님 | 해당 값만 null, 엔트리는 유지 | `rating`, `ilsu`, `wg_hr` 파생 |
| `entry_drop_from_operational_snapshot` | 핵심 카드 필드가 없어 운영 입력으로 쓸 수 없음 | 해당 출전마만 운영 snapshot에서 제외 | `chul_no`, `hr_no`, `jk_no`, `tr_no`, `ow_no`, `wg_budam` |
| `race_quarantine` | 핵심 필드 이상이 여러 마리/경주 수준 문제로 번짐 | 해당 경주 전체를 strict snapshot 인증에서 제외 | core key 중복, 출전마 3두 미만 등 |
| `raw_store_only` | 운영 입력으로는 못 쓰지만 원문 보존은 필요 | raw/shadow 보관, feature 차단 | blocked result fields, 보류 odds |
| `join mismatch warning only` | join key는 있으나 이름/보조 값이 불일치 | warning flag만 남기고 기본 join 결과 유지 또는 빈 블록 | `hrdetail_join_mismatch`, `training_unmatched` |

### 예외 우선순위

1. `BLOCK`/`LABEL_ONLY` 판정이 가능한 경우 다른 예외보다 우선한다.
2. hard-required core field 위반은 `field_null_only` 로 낮추지 않고 `entry_drop_from_operational_snapshot` 또는 `race_quarantine` 을 우선한다.
3. soft source 조인 실패는 `never_drop_entry > keep_empty_dict` 원칙을 따른다.
4. 파생 컬럼의 예외는 부모 예외보다 완화할 수 없다. 예를 들어 부모가 `당시 저장본만 허용` 이면 자식 파생도 live 재조회 허용으로 내릴 수 없다.
5. `HOLD` 는 "연구 가능"이지 "운영 허용"이 아니므로, 보류 필드를 이용한 파생도 최종 scorecard에서는 제외한다.

## 원천 필드군 판정표

| 필드군 | 저장 경로 | 최초 공개 시점 | 갱신 가능 여부 | 운영 판정 | 근거 출처 |
| --- | --- | --- | --- | --- | --- |
| `API214_1` 핵심 출전표 필드 `rcDate`, `rcNo`, `meet`, `chulNo`, `hrNo`, `hrName`, `jkNo`, `jkName`, `trNo`, `trName`, `owNo`, `owName`, `age`, `sex`, `name`, `rank`, `rating`, `wgBudam`, `wgBudamBigo`, `wgHr`, `ilsu`, `hrTool` | `race_info`, `horses[]` | `L0` | `가변` | `허용` | [kra_api_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/kra_api_service.py), [prerace-standard-field-catalog.md](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-standard-field-catalog.md) |
| `API72_2` 경주 조건 `rank`, `budam`, `rcDist`, `ageCond`, `sexCond`, `chaksun1..5` | `race_plan.*` | `L-1` | `가변` | `허용` | [kra_api_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/kra_api_service.py), [data-go-kr-api-application.md](/Users/chsong/Developer/Personal/kra-analysis/docs/prompts/data-go-kr-api-application.md) |
| `API72_2.schStTime` | `race_plan.sch_st_time` | `L0 snapshot` | `가변` | `허용` | [holdout-entry-finalization-rule.md](/Users/chsong/Developer/Personal/kra-analysis/docs/holdout-entry-finalization-rule.md), [kra-race-lifecycle-timing-matrix.md](/Users/chsong/Developer/Personal/kra-analysis/docs/kra-race-lifecycle-timing-matrix.md) |
| `API189_1` 주로/날씨 `weather`, `track`, `waterPercent`, `temperature`, `humidity`, `windDirection`, `windSpeed` | `track.*` | `L0 snapshot` | `가변` | `허용` | [kra_api_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/kra_api_service.py), [kra-race-lifecycle-timing-matrix.md](/Users/chsong/Developer/Personal/kra-analysis/docs/kra-race-lifecycle-timing-matrix.md) |
| `API9_1` 취소 row 전체 | `cancelled_horses[]` | `L0 snapshot` | `가변` | `허용` | [kra_api_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/kra_api_service.py), [holdout-entry-finalization-rule.md](/Users/chsong/Developer/Personal/kra-analysis/docs/holdout-entry-finalization-rule.md) |
| `API8_2` 말 상세 row 전체 | `horses[].hrDetail` | `L-1` | `재조회 의존` | `허용` | [kra_api_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/kra_api_service.py), [collection_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/collection_service.py) |
| `API12_1` 기수 상세 row 전체 | `horses[].jkDetail` | `L-1` | `재조회 의존` | `허용` | [kra_api_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/kra_api_service.py), [collection_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/collection_service.py) |
| `API19_1` 조교사 상세 row 전체 | `horses[].trDetail` | `L-1` | `재조회 의존` | `허용` | [kra_api_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/kra_api_service.py), [collection_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/collection_service.py) |
| `API11_1` 기수 누적 성적 row 전체 | `horses[].jkStats` | `L-1` | `재조회 의존` | `허용` | [kra_api_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/kra_api_service.py), [collection_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/collection_service.py) |
| `API14_1` 마주 정보 row 전체 | `horses[].owDetail` | `L-1` | `재조회 의존` | `허용` | [kra_api_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/kra_api_service.py), [collection_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/collection_service.py) |
| `API329` 조교 현황 row 전체 | `horses[].training` | `L0 snapshot` | `가변` | `조건부 허용` | [kra_api_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/kra_api_service.py), [collection_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/collection_service.py) |
| `API214_1.winOdds`, `API214_1.plcOdds` | `horses[].win_odds`, `horses[].plc_odds` | `?` | `가변` | `보류` | [kra-race-lifecycle-timing-matrix.md](/Users/chsong/Developer/Personal/kra-analysis/docs/kra-race-lifecycle-timing-matrix.md), [prerace-data-whitelist-blacklist-policy.md](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-data-whitelist-blacklist-policy.md) |
| `API214_1` 결과 필드 `ord`, `ordBigo`, `rankRise`, `diffUnit`, `rcTime` | raw `race_info` 내부 | `L+1` | `사후 전용` | `금지` | [result_collection_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/result_collection_service.py), [leakage_checks.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/evaluation/leakage_checks.py) |
| `API214_1` 구간 순위/기록 `sj*`, `bu*`, `se*` + `Ord/AccTime/GTime` | raw `race_info` 내부 | `L+1` | `사후 전용` | `금지` | [leakage_checks.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/evaluation/leakage_checks.py) |
| `API160_1`, `API301` 배당 row 전체 | `race_odds.*` | `L+1` | `사후 전용` | `금지` | [result_collection_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/result_collection_service.py), [collection_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/collection_service.py) |

## 가공 필드군 판정표

| 가공 필드군 | 포함 필드 | 최초 공개 시점 | 갱신 가능 여부 | 운영 판정 | 근거 출처 |
| --- | --- | --- | --- | --- | --- |
| 하위 호환/메타 파생 | `schema_version`, `date`, `race_number`, `collected_at`, `status`, `failed_horses[]` | `L0` | `가변` | `메타 전용` | [prerace_source_schema.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prerace_source_schema.py) |
| 출전표 직접 파생 | `burden_ratio`, `rest_days`, `rest_risk`, `age_prime`, `horse_consistency` | `L0` | `가변` | `허용` | [feature_engineering.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/feature_engineering.py) |
| 말/기수/조교사 누적 통계 파생 | `jockey_win_rate`, `jockey_place_rate`, `jockey_form`, `jockey_recent_win_rate`, `horse_win_rate`, `horse_place_rate`, `horse_avg_prize`, `trainer_win_rate`, `trainer_place_rate`, `horse_top3_skill`, `horse_starts_y`, `horse_low_sample`, `jk_qnl_rate_y`, `jk_qnl_rate_t`, `jk_skill`, `tr_skill`, `owner_win_rate`, `owner_skill` | `L-1` | `재조회 의존` | `허용` | [feature_engineering.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/feature_engineering.py), [collection_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/collection_service.py) |
| 조교 현황 파생 | `training_score`, `training_missing`, `days_since_training`, `recent_training` | `L0 snapshot` | `가변` | `조건부 허용` | [feature_engineering.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/feature_engineering.py) |
| 과거 경주 히스토리 파생 | `recent_race_count`, `recent_win_count`, `recent_top3_count`, `recent_win_rate`, `recent_top3_rate` | `L0` | `불변` | `허용` | [db_client.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/db_client.py) |
| 경주 상대 순위 파생 중 사전 확정형 | `rating_rank`, `horse_skill_rank`, `jk_skill_rank`, `tr_skill_rank`, `wg_budam_rank`, `gap_3rd_4th`, `field_size`, `field_size_live`, `wet_track`, `cancelled_count` | `L0` 또는 `L0 snapshot` | `의존 필드 상속` | `허용` | [feature_engineering.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/feature_engineering.py) |
| 경주 상대 순위 파생 중 odds 의존형 | `odds_rank` | `?` | `가변` | `보류` | [feature_engineering.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/feature_engineering.py), [kra-race-lifecycle-timing-matrix.md](/Users/chsong/Developer/Personal/kra-analysis/docs/kra-race-lifecycle-timing-matrix.md) |
| 결과/사후 데이터 파생 | `top3`, `is_top3`, 정답 라벨, 결과 기반 랭킹/정규화값 | `L+1` | `사후 전용` | `라벨 전용` | [db_client.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/db_client.py), [leakage_checks.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/evaluation/leakage_checks.py) |

## 필드군별 판정 메모

### 1. `API214_1` 혼합 응답

- 같은 엔드포인트를 [kra_api_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/kra_api_service.py) 의 `get_race_info()` 와 `get_race_result()` 가 함께 사용한다.
- 따라서 `API214_1` raw 전체는 저장 가능하지만, 운영 입력으로는 허용 필드군만 선별해야 한다.
- 특히 `ord`, `diffUnit`, 구간 순위/시간 필드는 raw에 남아 있어도 반드시 제거한다.

### 2. 마스터/누적 통계 계열

- `hrDetail`, `jkDetail`, `trDetail`, `jkStats`, `owDetail` 는 출전표 확정 전에도 조회 가능한 누적 정보로 본다.
- 다만 과거 홀드아웃 재생에서 결과 확정 후 재조회한 최신 상태를 쓰면 시점 오염이 생기므로, 당시 저장본만 허용한다.
- 따라서 이 계열을 부모로 쓰는 비율/스킬 파생도 모두 `ALLOW_STORED_ONLY` 상한을 유지한다.

### 3. 변동 snapshot 계열

- `track.*`, `cancelled_horses[]`, `training`, `sch_st_time` 은 출전표 확정 시점 전후로 값이 바뀔 수 있다.
- 운영 입력은 "cutoff 이전 최초 정상 snapshot"을 기준값으로 잠가야 한다.
- 이 계열을 부모로 사용하는 `field_size_live`, `cancelled_count`, `wet_track`, `recent_training` 같은 파생도 `ALLOW_SNAPSHOT_ONLY` 로 고정한다.

### 4. odds 계열

- 현재 저장소는 일부 정리 로직과 `odds_rank` 계산에서 `winOdds` 를 참조한다.
- 그러나 이 값이 정확히 언제 공개되는지는 저장소 내부 근거만으로 확정되지 않았으므로, 운영 성공 판정 feature에서는 `보류` 상태를 유지한다.
- 따라서 `winOdds`, `plcOdds` 뿐 아니라 race-relative 정규화/순위 파생도 모두 함께 `HOLD` 로 묶어야 한다.

### 5. 과거 히스토리 계열

- [db_client.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/db_client.py) 의 `get_past_top3_stats_for_race()` 는 `r.date < race_date` 조건으로 현재 경주 이전 데이터만 집계한다.
- 따라서 해당 파생치는 현재 경주 결과를 참조하지 않는 한 `L0` 허용으로 본다.
- 같은 날짜의 이전 경주를 별도 시각으로 분리하지 않는 현재 구현에서는, 동일 날짜 intra-day 정보는 보수적으로 제외된 것으로 간주한다.

## 운영 적용 규칙

1. 운영 feature set은 `허용`, `조건부 허용` 필드만 포함한다.
2. `조건부 허용` 필드는 snapshot timestamp audit가 가능한 경우에만 최종 운영에 넣는다.
3. `보류` 필드는 raw 저장과 오프라인 연구는 허용하되, 최근 기간 홀드아웃 성공 판정과 실전 운영 scorecard에서는 제외한다.
4. `금지`와 `라벨 전용` 필드는 snapshot export, 학습 입력, 추론 입력에서 모두 차단한다.
5. 새 API나 새 가공 필드를 추가하면, 코드 반영 전에 이 문서에 먼저 필드군을 등록해야 한다.

## 현재 결론

- 실전 운영용 핵심 원천은 `API214_1` 허용 필드군, `API72_2`, `API189_1`, `API9_1`, 그리고 soft source 저장본이다.
- 실전 운영용 핵심 가공 필드는 출전표 직접 파생, 누적 통계 파생, 과거 히스토리 파생, 변동 snapshot 기반 컨텍스트 파생이다.
- `winOdds`, `plcOdds`, `odds_rank` 는 실측 검증 전까지 보류 상태를 유지한다.
- 결과/배당/구간 순위 계열은 모두 `L+1` 로 고정하고 라벨 또는 감사 용도로만 사용한다.
