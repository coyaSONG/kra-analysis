# 출전표 확정 시점 필드 메타데이터 스키마 v1

## 목적

이 문서는 표준 필드 카탈로그의 각 필드에 대해 아래 네 가지를 행 단위 메타데이터로 저장하는 기준을 고정한다.

1. 가용 시점
2. 공개 근거
3. 예외 조건
4. 검증 상태

이 스키마는 사람이 읽는 기준 문서를 대체하지 않는다. 역할은 다음과 같다.

- [출전표 확정 시점 표준 필드 카탈로그 v1](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-standard-field-catalog.md)의 행 단위 저장 계약을 제공한다.
- [출전표 확정 시점 가용성 판정 규칙 v1](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-field-availability-judgment-rules.md)의 판정을 기계 판독 가능하게 고정한다.
- 향후 화이트리스트 생성, 누수 검사, snapshot 감사, 자동 재학습 검증이 같은 필드 메타데이터를 참조하게 한다.

코드 기준선은 [prerace_field_metadata_schema.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prerace_field_metadata_schema.py) 이다.

## 정규 저장 포맷

- 파일 경로: [data/contracts/prerace_field_metadata_v1.csv](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/prerace_field_metadata_v1.csv)
- 인코딩: `UTF-8`
- 포맷: 헤더 포함 CSV
- 행 단위: `field_path` 하나당 정확히 한 행
- 기본 키: `field_path`
- 다중 참조 값: `publication_basis_refs`, `validation_evidence` 는 JSON array 문자열을 사용한다

CSV를 기준 포맷으로 고정한 이유는 다음과 같다.

- Git diff 리뷰가 쉽다.
- 필드 카탈로그와 1:1 대조가 쉽다.
- 이후 DuckDB/Polars/Pandas 로 바로 읽을 수 있다.

## 필수 컬럼

| 컬럼 | 의미 | 예시 |
| --- | --- | --- |
| `metadata_schema_version` | 메타데이터 저장 계약 버전 | `prerace-field-metadata-v1` |
| `field_path` | 표준 필드 경로 | `horses[].training` |
| `field_role` | `source`, `derived`, `metadata`, `label` 중 하나 | `source` |
| `source_api` | 원천 API 또는 `INTERNAL` | `API214_1` |
| `source_field` | raw field 또는 내부 파생 기준 | `winOdds` |
| `availability_stage` | `L-1`, `L0`, `L0 snapshot`, `?`, `L+1` | `L0 snapshot` |
| `publication_basis` | 공개 근거 한 줄 요약 | `공식 엔드포인트 문서 + 런타임 수집 경로` |
| `publication_basis_refs` | 근거 문서/코드 참조 목록 JSON array | `["docs/kra-race-lifecycle-timing-matrix.md"]` |
| `exception_rule` | snapshot 고정, soft-fail, 재조회 금지 등 예외 규칙 | `cutoff 이전 최초 정상 snapshot만 허용` |
| `validation_status` | `documented`, `measured`, `pending_measurement`, `rejected` | `pending_measurement` |
| `validation_evidence` | 검증 근거 요약 또는 참조 목록 | `["docs/prerace-field-availability-judgment-rules.md"]` |
| `operational_status` | `필수`, `선택`, `보류`, `금지`, `라벨 전용`, `메타 전용`, `허용`, `조건부 허용` | `보류` |
| `train_inference_flag` | `ALLOW`, `ALLOW_SNAPSHOT_ONLY`, `ALLOW_STORED_ONLY`, `HOLD`, `BLOCK`, `LABEL_ONLY`, `META_ONLY` | `ALLOW_SNAPSHOT_ONLY` |

이 13개 컬럼이 없으면 해당 CSV는 운영 기준선 메타데이터로 인정하지 않는다.

## `train_inference_flag` 값 정의

| 값 | 학습/추론 공통 해석 |
| --- | --- |
| `ALLOW` | 출전표 확정 시점 기준으로 바로 입력 허용 |
| `ALLOW_SNAPSHOT_ONLY` | cutoff 이전에 잠긴 snapshot 값만 입력 허용 |
| `ALLOW_STORED_ONLY` | 사전 정보이지만 과거 재조회 오염 방지를 위해 당시 저장본만 허용 |
| `HOLD` | raw 저장과 연구는 가능하지만 최종 학습/추론 입력에서는 제외 |
| `BLOCK` | 사후/누수 필드이므로 입력 금지 |
| `LABEL_ONLY` | 라벨/정답 전용 |
| `META_ONLY` | 감사/운영 메타데이터 전용 |

## 선택 컬럼

| 컬럼 | 용도 |
| --- | --- |
| `join_key` | row 조인 키 고정 |
| `value_type` | scalar/object/array/mixed 등 값 형태 메모 |
| `mutable_after_publish` | `불변`, `가변`, `재조회 의존`, `사후 전용` 등 갱신 성격 |
| `owner` | 담당 모듈 또는 책임자 |
| `last_verified_at` | 마지막 검증 시각 |
| `notes` | 보충 메모 |

### `join_key` 작성 규칙

- 조인이 없는 순수 source/derived 필드는 빈 문자열을 허용한다.
- 결정적 ID 조인은 `horses[].hr_no -> hrDetail.hrNo` 처럼 `좌측 canonical key -> 우측 raw key` 형식으로 적는다.
- 이름/보조 키 fallback 조인은 `horses[].hr_name -> training.hrName (fallback)` 처럼 fallback 여부를 반드시 남긴다.
- 동일 경주 내부 집계/정렬 파생은 `same-race aggregate`, `race-relative rank` 같은 범위 표현을 `source_field` 에 적고, `join_key` 는 빈 값으로 둘 수 있다.
- `join_key` 가 문자열 정규화나 sentinel 보정에 의존하면 `notes` 또는 `exception_rule` 에 `id_normalized`, `strip_decimal_suffix`, `owner_id_string_cast` 같은 보정 근거를 함께 남긴다.

### `exception_rule` 작성 규칙

`exception_rule` 은 "문제가 생길 수 있다"는 설명이 아니라 운영 동작을 고정하는 규칙이어야 한다. 아래 표현을 우선 사용한다.

| 권장 표현 | 의미 |
| --- | --- |
| `cutoff 이전 최초 정상 snapshot만 허용` | 변동 가능한 사전 값은 최초 정상본으로 고정 |
| `당시 저장본만 허용` | 과거 재조회 최신값 사용 금지 |
| `soft-fail empty block` | 조인 실패 시 빈 dict/null 유지, 예측 계속 |
| `field_null_only` | 해당 값만 null 처리하고 엔트리는 유지 |
| `entry_drop_from_operational_snapshot` | 해당 출전마는 운영 snapshot 승격에서 제외 |
| `race_quarantine` | 경주 전체 strict replay 인증 제외 |
| `raw_store_only` | raw/shadow 저장만 허용, 모델 입력 차단 |
| `join mismatch warning only` | mismatch flag만 남기고 운영 계속 |

여러 규칙이 함께 필요하면 ` > ` 로 우선순위를 적는다. 예: `entry_drop_from_operational_snapshot > race_quarantine > raw_store_only`

## 행 작성 규칙

1. 표준 필드 카탈로그에 있는 모든 `field_path` 는 이 CSV에도 정확히 한 행이 있어야 한다.
2. 같은 원천 API 안에 허용 필드와 금지 필드가 섞여 있으면 `field_path` 별로 따로 행을 만든다.
3. `source`, `derived`, `metadata`, `label` 필드를 혼합 저장할 수 있지만 `field_role` 은 반드시 채운다.
4. `publication_basis_refs`, `validation_evidence` 가 복수일 때는 JSON array 문자열로 저장한다.
5. 검증이 끝나지 않은 필드는 `validation_status = pending_measurement` 로 유지하고 `operational_status` 를 더 보수적으로 둔다.
6. 학습·추론 파이프라인은 `train_inference_flag` 를 1차 판정값으로 사용하고, 세부 해석은 [prerace_field_policy.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prerace_field_policy.py) 에 고정한다.
7. 조인 블록이나 파생 컬럼은 `source_field` 에 부모 원천을 모두 적고, 조인이 있으면 `join_key`, 예외가 있으면 `exception_rule` 을 비우지 않는 것을 기본 원칙으로 한다.
8. 파생 컬럼의 `availability_stage` 와 `train_inference_flag` 는 부모 필드 중 가장 보수적인 값을 상속해야 한다.

## 현재 즉시 반영해야 할 상태 예시

| field_path | availability_stage | validation_status | operational_status | train_inference_flag | 이유 |
| --- | --- | --- | --- | --- | --- |
| `horses[].win_odds` | `?` | `pending_measurement` | `보류` | `HOLD` | 출전표 확정 시점 공개 로그 실측 전 |
| `horses[].plc_odds` | `?` | `pending_measurement` | `보류` | `HOLD` | 위와 동일 |
| `track.weather` | `L0 snapshot` | `documented` | `필수` | `ALLOW_SNAPSHOT_ONLY` | 변동 가능하지만 cutoff snapshot 허용 |
| `result_data.*` | `L+1` | `documented` | `라벨 전용` | `LABEL_ONLY` | 결과 확정 후만 의미가 생김 |

## 구현 기준선

- 코드 상수: [prerace_field_metadata_schema.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prerace_field_metadata_schema.py)
- CSV 헤더 템플릿: [prerace_field_metadata_v1.csv](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/prerace_field_metadata_v1.csv)
- 관련 기준 문서:
  - [prerace-standard-field-catalog.md](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-standard-field-catalog.md)
  - [prerace-field-availability-judgment-rules.md](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-field-availability-judgment-rules.md)
  - [prerace-data-whitelist-blacklist-policy.md](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-data-whitelist-blacklist-policy.md)
