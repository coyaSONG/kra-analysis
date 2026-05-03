# 출전표 확정 시점 표준 필드 카탈로그 v1

## 목적

이 문서는 다음 두 문서를 하나의 운영 기준으로 통합한다.

- 원천별 raw 필드 인벤토리: [discovery-2026-04-10-field-inventory.md](/Users/chsong/Developer/Personal/kra-analysis/docs/knowledge/discovery-2026-04-10-field-inventory.md)
- 필드 가용 시점 기준: [kra-race-lifecycle-timing-matrix.md](/Users/chsong/Developer/Personal/kra-analysis/docs/kra-race-lifecycle-timing-matrix.md)

목표는 표준 스키마 경로마다 아래 4가지를 한 번에 고정하는 것이다.

1. 표준 필드명
2. 원천 API와 raw 필드 매핑
3. 가용 시점
4. 운영 사용 가능 여부

코드 기준선은 [prerace_source_schema.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prerace_source_schema.py) 이다.

## 단일 기준 소스 선언

- 출전표 확정 시점 기준의 `가용 필드 목록`, `차단 대상 목록`, `운영 사용 상태`의 정본은 이 문서다.
- 기계 판독용 정규 저장 포맷은 [prerace_field_metadata_v1.csv](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/prerace_field_metadata_v1.csv) 이며, 이 CSV는 이 문서의 각 표준 필드 행을 그대로 반영해야 한다.
- 다른 문서와 코드가 충돌하면, 필드의 존재 여부와 허용/금지 분류는 먼저 이 카탈로그를 기준으로 맞춘다. 세부 근거와 예외 규칙은 링크된 보조 문서에서 추적한다.

원천 필드와 가공 필드를 함께 묶어 `최초 공개 시점`, `갱신 가능 여부`, `근거 출처`까지 확인하려면 [출전표 확정 시점 가용성 판정 규칙 v1](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-field-availability-judgment-rules.md) 를 함께 본다.

각 필드의 `가용 시점`, `공개 근거`, `예외 조건`, `검증 상태`를 행 단위로 저장하는 정규 포맷은 [출전표 확정 시점 필드 메타데이터 스키마 v1](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-field-metadata-schema.md) 를 따른다.

## 가용 필드 필수 메타데이터 요건

이 카탈로그에서 `필수`, `선택`, `보류` 로 분류된 모든 필드는 [prerace_field_metadata_v1.csv](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/prerace_field_metadata_v1.csv) 에 아래 필수 컬럼을 모두 가진 정확히 한 행으로 존재해야 한다.

| 컬럼 | 의미 |
| --- | --- |
| `field_path` | 이 문서의 표준 필드명과 동일한 canonical 경로 |
| `field_role` | `source`, `derived`, `metadata`, `label` 중 하나 |
| `source_api` | 원천 API 또는 `INTERNAL` |
| `source_field` | raw field 또는 내부 파생 기준 |
| `availability_stage` | `L-1`, `L0`, `L0 snapshot`, `?`, `L+1` |
| `publication_basis` | 공개 근거 한 줄 요약 |
| `publication_basis_refs` | 근거 문서/코드 참조 목록 |
| `exception_rule` | snapshot 고정, soft-fail, 재조회 금지 같은 예외 |
| `validation_status` | `documented`, `measured`, `pending_measurement`, `rejected` |
| `validation_evidence` | 검증 근거 또는 검증 대기 근거 |
| `operational_status` | `필수`, `선택`, `보류`, `금지`, `라벨 전용`, `메타 전용`, `허용`, `조건부 허용` |
| `train_inference_flag` | `ALLOW`, `ALLOW_SNAPSHOT_ONLY`, `ALLOW_STORED_ONLY`, `HOLD`, `BLOCK`, `LABEL_ONLY`, `META_ONLY` |

보조 컬럼(`join_key`, `value_type`, `mutable_after_publish`, `owner`, `last_verified_at`, `notes`)은 운영 자동화와 감사 품질을 위해 채우는 것을 권장한다.

## 판정 기준

| 컬럼 | 의미 |
| --- | --- |
| `가용 시점` | `L-1`, `L0`, `L+1` 중 실제 사용 가능한 가장 이른 단계. `L0 snapshot`은 출전표 확정 시점에 캡처한 값만 허용함을 뜻한다 |
| `운영 사용` | `필수`, `선택`, `보류`, `금지`, `라벨 전용` |
| `필수` | 모든 KRA 경주에 대해 예측을 생성하려면 채워져야 하는 필드 |
| `선택` | 성능 고도화용 또는 soft-fail 허용 필드. 값이 없어도 예측은 계속 생성해야 한다 |
| `보류` | 출전표 확정 시점 가용성이 실측으로 검증되지 않아 연구 저장은 가능해도 성공 판정용 feature에는 넣지 않는 필드 |
| `금지` | 사후 정보이거나 누수 위험이 있어 feature 입력으로 사용할 수 없는 필드 |

## 표준 카탈로그

### 1. 경주 식별 및 원본 보존

| 표준 필드명 | 원천 매핑 | 가용 시점 | 운영 사용 | 메모 |
| --- | --- | --- | --- | --- |
| `schema_version` | 내부 파생 | `L0` | `필수` | 현재 값 `prerace-source-v1` |
| `race_date` | `API214_1.rcDate` | `L0` | `필수` | 모든 item에서 동일해야 함 |
| `race_no` | `API214_1.rcNo` | `L0` | `필수` | 경주번호 |
| `meet` | `API214_1.meet` | `L0` | `필수` | 경마장 코드 |
| `date` | 내부 파생 (`race_date`) | `L0` | `필수` | 하위 호환용 파생 필드 |
| `race_number` | 내부 파생 (`race_no`) | `L0` | `필수` | 하위 호환용 파생 필드 |
| `race_info.response.body.items.item[]` | `API214_1.response.body.items.item[]` | `L0` | `필수` | 원본 보존은 허용하지만 모델 입력 변환 시 `L+1` 필드 제거 필요 |
| `collected_at` | 내부 메타데이터 | `L0` | `필수` | cutoff 감사 기준 |
| `status` | 내부 메타데이터 | `L0` | `필수` | 수집 성공/실패 상태 |
| `failed_horses[]` | 내부 메타데이터 | `L0` | `선택` | soft-fail 감사용 |

### 2. 경주 조건

| 표준 필드명 | 원천 매핑 | 가용 시점 | 운영 사용 | 메모 |
| --- | --- | --- | --- | --- |
| `race_plan.rank` | `API72_2.rank` | `L-1` | `필수` | 경주 등급 |
| `race_plan.budam` | `API72_2.budam` | `L-1` | `필수` | 부담 조건 |
| `race_plan.rc_dist` | `API72_2.rcDist` | `L-1` | `필수` | 거리 |
| `race_plan.age_cond` | `API72_2.ageCond` | `L-1` | `필수` | 연령 조건 |
| `race_plan.sex_cond` | `API72_2.sexCond` | `L-1` | `선택` | 성별 조건 |
| `race_plan.sch_st_time` | `API72_2.schStTime` | `L0 snapshot` | `선택` | 확정 후 바뀔 수 있어 `L0` 값만 허용 |
| `race_plan.chaksun1` | `API72_2.chaksun1` | `L-1` | `선택` | 1착 상금 |
| `race_plan.chaksun2` | `API72_2.chaksun2` | `L-1` | `선택` | 2착 상금 |
| `race_plan.chaksun3` | `API72_2.chaksun3` | `L-1` | `선택` | 3착 상금 |
| `race_plan.chaksun4` | `API72_2.chaksun4` | `L-1` | `선택` | 4착 상금 |
| `race_plan.chaksun5` | `API72_2.chaksun5` | `L-1` | `선택` | 5착 상금 |

### 3. 주로 및 경주 당일 상태

| 표준 필드명 | 원천 매핑 | 가용 시점 | 운영 사용 | 메모 |
| --- | --- | --- | --- | --- |
| `track.weather` | `API189_1.weather` | `L0 snapshot` | `필수` | 당일 변동 가능 |
| `track.track` | `API189_1.track` | `L0 snapshot` | `필수` | 주로 상태 |
| `track.water_percent` | `API189_1.waterPercent` | `L0 snapshot` | `필수` | 수분율 |
| `track.temperature` | `API189_1.temperature` | `L0 snapshot` | `선택` | 변동 가능 |
| `track.humidity` | `API189_1.humidity` | `L0 snapshot` | `선택` | 변동 가능 |
| `track.wind_direction` | `API189_1.windDirection` | `L0 snapshot` | `선택` | 변동 가능 |
| `track.wind_speed` | `API189_1.windSpeed` | `L0 snapshot` | `선택` | 변동 가능 |
| `cancelled_horses[]` | `API9_1.*` | `L0 snapshot` | `필수` | cutoff 이후 취소분으로 기존 snapshot 덮어쓰기 금지 |

### 4. 출전마 핵심 카드

| 표준 필드명 | 원천 매핑 | 가용 시점 | 운영 사용 | 메모 |
| --- | --- | --- | --- | --- |
| `horses[].chul_no` | `API214_1.chulNo` | `L0` | `필수` | 말 배열 정렬 기준 |
| `horses[].hr_no` | `API214_1.hrNo` | `L0` | `필수` | 말 식별자 |
| `horses[].hr_name` | `API214_1.hrName` | `L0` | `필수` | 말 이름 |
| `horses[].jk_no` | `API214_1.jkNo` | `L0` | `필수` | 기수 조인키 |
| `horses[].jk_name` | `API214_1.jkName` | `L0` | `필수` | 기수명 |
| `horses[].tr_no` | `API214_1.trNo` | `L0` | `필수` | 조교사 조인키 |
| `horses[].tr_name` | `API214_1.trName` | `L0` | `필수` | 조교사명 |
| `horses[].ow_no` | `API214_1.owNo` | `L0` | `필수` | 마주 조인키 |
| `horses[].ow_name` | `API214_1.owName` | `L0` | `필수` | 마주명 |
| `horses[].age` | `API214_1.age` | `L0` | `필수` | 나이 |
| `horses[].sex` | `API214_1.sex` | `L0` | `필수` | 성별 |
| `horses[].name` | `API214_1.name` | `L0` | `필수` | 산지/국적 원문 |
| `horses[].country` | 내부 파생 (`name`/`country` alias 정규화) | `L0` | `선택` | 산지/국적 canonical 필드 |
| `horses[].rank` | `API214_1.rank` | `L0` | `필수` | 저장은 `rank`, 모델 입력 변환 시 `class_rank`로 rename |
| `horses[].rating` | `API214_1.rating` | `L0` | `필수` | 레이팅 |
| `horses[].wg_budam` | `API214_1.wgBudam` | `L0` | `필수` | 부담중량 |
| `horses[].wg_budam_bigo` | `API214_1.wgBudamBigo` | `L0` | `필수` | 부담중량 비고 |
| `horses[].wg_hr` | `API214_1.wgHr` | `L0` | `필수` | 마체중 및 증감 |
| `horses[].weight` | 내부 파생 (`wgHr`/명시 weight 정규화) | `L0` | `선택` | 정수 마체중 |
| `horses[].weight_delta` | 내부 파생 (`wgHr` 증감 파싱) | `L0` | `선택` | 정수 증감치 |
| `horses[].ilsu` | `API214_1.ilsu` | `L0` | `선택` | 보조 피처 |
| `horses[].hr_tool` | `API214_1.hrTool` | `L0` | `선택` | 장구 정보 |
| `horses[].normalization_flags` | 내부 파생 (정규화 audit 플래그) | `L0` | `선택` | 파싱 실패·결측·보정 이력 |

### 5. 출전마 확장 블록

| 표준 필드명 | 원천 매핑 | 가용 시점 | 운영 사용 | 메모 |
| --- | --- | --- | --- | --- |
| `horses[].hrDetail` | `API8_2.*` | `L-1` | `선택` | `hrNo` 조인, 없으면 빈 dict |
| `horses[].jkDetail` | `API12_1.*` | `L-1` | `선택` | `jkNo` 조인, 없으면 빈 dict |
| `horses[].trDetail` | `API19_1.*` | `L-1` | `선택` | `trNo` 조인, 없으면 빈 dict |
| `horses[].jkStats` | `API11_1.*` | `L-1` | `선택` | `jkNo` 조인, 누적 통계 |
| `horses[].owDetail` | `API14_1.*` | `L-1` | `선택` | `owNo` 조인 |
| `horses[].training` | `API329.*` | `L0 snapshot` | `선택` | 현재 `hrName` 매칭. 동명이마 충돌과 누락은 soft-fail 처리 |

### 6. 시장 신호 및 운영 보류 항목

| 표준 필드명 | 원천 매핑 | 가용 시점 | 운영 사용 | 메모 |
| --- | --- | --- | --- | --- |
| `horses[].win_odds` | `API214_1.winOdds` | `?` | `보류` | 저장은 가능하지만 `L0` 공개 여부 실측 전까지 성공 판정 feature 금지 |
| `horses[].plc_odds` | `API214_1.plcOdds` | `?` | `보류` | 위와 동일 |

### 7. 운영 금지 및 라벨 전용 항목

| 표준 필드명/필드군 | 원천 매핑 | 가용 시점 | 운영 사용 | 메모 |
| --- | --- | --- | --- | --- |
| `result_data.*` | 내부 결과 적재본 | `L+1` | `라벨 전용` | 학습/평가 정답으로만 사용 |
| `top3`, `is_top3`, `label.*` 파생값 | 내부 파생 | `L+1` | `라벨 전용` | 입력 금지 |
| `ord`, `ordBigo`, `rankRise`, `diffUnit` | `API214_1` 결과 필드 | `L+1` | `금지` | 사후 결과 |
| `rcTime` | `API214_1.rcTime` | `L+1` | `금지` | 결과 수집 경로와 겹침 |
| `result`, `resultTime`, `finish_position` | 결과 상태/결승 순위 계열 | `L+1` | `금지` | 결과 확정 후만 의미가 생김 |
| `dividend`, `payout` | 확정 배당/환급 계열 | `L+1` | `금지` | 사후 배당 정보 |
| `sj*`, `bu*`, `se*` + `Ord/AccTime/GTime` 패턴 | `API214_1` 구간 순위/기록 | `L+1` | `금지` | 누수 차단 대상 |
| `API160_1.*`, `API301.*`, `race_odds.*` | 배당/오즈 계열 원천 | `L+1` | `금지` | 결과 이후 확정값 |

## 운영 적용 규칙

1. `필수`와 `선택` 중 `L0` 또는 `L0 snapshot` 판정만 최종 운영 feature 후보가 된다.
2. `보류` 필드는 raw 저장과 연구용 분석은 가능하지만, 최근 기간 홀드아웃 성공 판정용 feature 세트에는 포함하지 않는다.
3. `금지`와 `라벨 전용` 필드는 feature store, snapshot export, 모델 입력 생성 단계에서 모두 차단한다.
4. `snapshot` 판정 필드는 동일 `race_id` 재수집 시에도 cutoff 이전 최초 정상본을 불변 기준값으로 유지해야 한다.
5. `선택` 필드가 비어도 경주 예측은 반드시 생성해야 하므로 null/빈 dict 정책을 유지한다.

## 현재 운영 기준 요약

- 하드 입력 경계는 `L0 출전표 확정 시점`이다.
- `API214_1`은 혼합 원천이므로 허용 필드와 금지 필드를 반드시 분리해 다뤄야 한다.
- `win_odds`, `plc_odds`는 현재 표준 스키마에는 남겨두되 운영 사용은 `보류` 상태다.
- 이 카탈로그는 이후 feature whitelist, snapshot immutability, 자동 재학습 파이프라인 검증의 기준 문서로 사용한다.
