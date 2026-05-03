# KRA 출전마 단위 원천 필드 데이터 품질 기준

**Date:** 2026-04-10  
**Category:** discovery  
**Status:** active  
**Related files:** `examples/api214_response.json`, `examples/api8_2_response.json`, `examples/api12_response.json`, `examples/api19_1_response.json`, `apps/api/adapters/kra_response_adapter.py`, `apps/api/services/prerace_postprocessing.py`, `apps/api/services/collection_preprocessing.py`, `docs/prerace-standard-field-catalog.md`

## 목적

출전표 확정 시점 원천 데이터에서 `출전마 단위`로 들어오는 필드에 대해 다음 세 가지를 한 번에 고정한다.

1. 누락값 유형 분류
2. 형식 불일치 패턴 분류
3. 전처리 대상 컬럼별 데이터 품질 기준

이 문서는 raw 저장 규칙과 모델 입력 전처리 규칙을 구분한다. 원칙은 다음과 같다.

- raw 저장은 원문 보존을 우선한다.
- 전처리는 `모든 KRA 경주에 대해 예측을 반드시 생성`해야 하므로, soft-fail 가능한 컬럼은 결측 플래그와 함께 보존한다.
- 사후 정보 차단 규칙은 별도 문서 [출전표 확정 시점 표준 필드 카탈로그 v1](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-standard-field-catalog.md)를 따른다.
- 필드별 `보정 > 대체 > 제외` 우선순위 체인은 기계판독용 계약 파일 [prerace_entry_preprocessing_rules_v1.csv](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/prerace_entry_preprocessing_rules_v1.csv)에 고정한다.

## 근거

### 샘플 근거

- `examples/api214_response.json`
  - `winOdds`, `plcOdds`가 `int`/`float` 혼합
  - `wgBudamBigo`, `ordBigo`가 `"-"` sentinel 사용
  - `meet`는 `"부경"` 문자열
  - `owNo`는 숫자형이지만 실제 코드/테스트는 문자열 조인도 허용
- `examples/api8_2_response.json`
  - `rating = 0`
  - `hrLastAmt`가 `"30,000천원(경매)"` 같은 복합 문자열
- `examples/api12_response.json`
  - `spDate = "-"` sentinel
- `examples/api19_1_response.json`
  - `age = "-"`, `birthday = "-"` sentinel

### 구현 근거

- `KRAResponseAdapter`는 출전마 핵심 필드에 alias를 허용하고, ID는 문자열로 정규화하며, `wgHr`에서 body weight를 파생한다.
- `normalize_prerace_payload()` / `validate_prerace_payload()`는 핵심 카드 필드의 타입 계약과 필수 여부를 고정한다.
- `collection_preprocessing.py`의 legacy helper는 `win_odds <= 0` 말을 제외한다. 이는 `모든 경주 모든 출전마에 대해 예측 생성` 제약과 충돌할 수 있으므로, 향후 운영 전처리는 본 문서 기준을 우선한다.

## 누락값 유형 분류

| 코드 | 유형 | 대표 예시 | 처리 원칙 |
| --- | --- | --- | --- |
| `M1` | 구조적 누락 | key 자체 없음, `None` | 핵심 카드 필드에서는 hard-fail. 확장 블록은 `{}`로 강등 |
| `M2` | 공백 문자열 | `""`, `"   "` | trim 후 `None` 처리 |
| `M3` | sentinel 문자열 | `"-"` | 의미 미상/해당 없음으로 간주. raw 보존, feature는 `None` + sentinel flag |
| `M4` | 도메인상 0값 | `rating = 0`, `winOdds = 0` | 숫자 0과 결측을 분리 저장. 컬럼별 규칙에 따라 valid zero 또는 unknown으로 해석 |
| `M5` | 조인 누락 | `hrDetail = {}`, `training = {}` | 예측은 계속 생성. `detail_missing_flag`를 남김 |
| `M6` | 파싱 누락 | `wgHr` 형식 파손, 날짜 8자리 실패 | raw 문자열은 보존하고 파생 컬럼만 `None` 처리 |

## 형식 불일치 패턴 분류

| 코드 | 패턴 | 대표 예시 | 정규화 규칙 |
| --- | --- | --- | --- |
| `F1` | identifier의 숫자/문자 혼합 | `owNo = 118011`, 테스트에서는 `"065126"` | 조인 키는 항상 문자열화하고 선행 0 보존 |
| `F2` | 수치형 `int`/`float` 혼합 | `winOdds = 3` vs `1.7`, `plcOdds = 2` vs `2.1` | 실수형 컬럼은 모두 `float`로 통일 |
| `F3` | alias 이름 불일치 | `name` vs `country`, `rank` vs `class_rank` | canonical 컬럼 하나로 합치고 원문 alias는 입력만 허용 |
| `F4` | 복합 문자열 인코딩 | `wgHr = "511(+2)"`, `hrLastAmt = "30,000천원(경매)"` | raw 문자열 유지 + 파생 숫자 컬럼 별도 생성 |
| `F5` | 코드값 alias | `meet = "부경"`, `"부산경남"`, `"3"` | alias dictionary로 canonical code로 통합 |
| `F6` | 날짜형 숫자/문자 혼합 | `rcDate = 20250523`, `birthday = "19820212"` | 숫자만 추출한 8자리 문자열로 통일 |
| `F7` | singleton/list envelope 차이 | `item` 한 건일 때 object | entry row 추출 전 list로 정규화 |

## 전처리 품질 기준

## 정규 규칙표 계약

출전마 단위 전처리 규칙의 기준 저장소는 아래 CSV다.

- 경로: [prerace_entry_preprocessing_rules_v1.csv](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/prerace_entry_preprocessing_rules_v1.csv)
- 저장 계약 코드: [prerace_entry_preprocessing_schema.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prerace_entry_preprocessing_schema.py)
- 검증 테스트: [test_prerace_entry_preprocessing_schema.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/tests/test_prerace_entry_preprocessing_schema.py)

CSV 각 행은 `horses[]` 기준 단일 컬럼 하나를 나타내며 아래 4가지를 함께 고정한다.

1. `allowed_range`: 허용 값 범위와 최소 형식 계약
2. `correction_priority`: alias 선택, trim, cast, 정규화 순서
3. `replacement_priority`: sentinel, 공백, 파싱 실패에 대한 대체 순서
4. `exclusion_priority`: 필드 null 처리, 출전마 제외, snapshot 격리 순서

우선순위 체인은 모두 `A > B > C` 형태로 기록하며 왼쪽에서 오른쪽 순서로 읽는다.

- `correction_priority`: 먼저 시도할 보정 순서
- `replacement_priority`: 보정 후에도 값이 비정상이면 적용할 대체 순서
- `exclusion_priority`: 그래도 운영 계약을 만족하지 못하면 적용할 차단 순서

핵심 해석은 다음과 같다.

- `entry_drop_from_operational_snapshot`: 해당 말 row는 운영 snapshot 승격 대상에서 제외한다.
- `race_quarantine`: 해당 경주는 예측용 snapshot으로 자동 승격하지 않고 검토 큐로 보낸다.
- `field_null_only`: 출전마는 유지하고 문제 필드만 `None` 처리한다.
- `never_drop_entry`: soft-fail 필드이므로 출전마 삭제를 금지한다.
- `keep_empty_dict`: 확장 블록은 `{}` 로 정규화하고 말 row는 유지한다.

### 1. 핵심 카드 컬럼

| canonical 컬럼 | 원천 alias | 기대 정규형 | 허용 raw 예외 | 전처리 기준 | 장애 등급 |
| --- | --- | --- | --- | --- | --- |
| `chul_no` | `chulNo`, `chul_no`, `horse_no` | 양의 정수 | 문자열 숫자 | `int` 변환 실패 시 hard-fail | `P0` |
| `hr_no` | `hrNo`, `hr_no` | 비어 있지 않은 문자열 | 숫자형 ID | `str` 변환 후 trim, `.0` 제거, 빈값 금지 | `P0` |
| `hr_name` | `hrName`, `hr_name`, `horse_name` | 비어 있지 않은 문자열 | 없음 | trim 후 빈값 금지 | `P0` |
| `jk_no` | `jkNo`, `jk_no` | 비어 있지 않은 문자열 | 숫자형 ID | `str` 변환 후 trim, `.0` 제거 | `P0` |
| `jk_name` | `jkName`, `jk_name` | 비어 있지 않은 문자열 | 없음 | trim 후 빈값 금지 | `P0` |
| `tr_no` | `trNo`, `tr_no` | 비어 있지 않은 문자열 | 숫자형 ID | `str` 변환 후 trim, `.0` 제거 | `P0` |
| `tr_name` | `trName`, `tr_name` | 비어 있지 않은 문자열 | 없음 | trim 후 빈값 금지 | `P0` |
| `ow_no` | `owNo`, `ow_no` | 비어 있지 않은 문자열 | 숫자형 ID | `str` 변환 후 trim, `.0` 제거 | `P0` |
| `ow_name` | `owName`, `ow_name` | 비어 있지 않은 문자열 | 없음 | trim 후 빈값 금지 | `P0` |
| `age` | `age` | 양의 정수 | 문자열 숫자 | `int` 변환, `<= 0` 금지 | `P0` |
| `sex` | `sex`, `gender` | 비어 있지 않은 문자열 | 영문 코드 `M/F/G` 가능 | raw 보존, feature에서는 `{수, 암, 거, 기타}`로 recode | `P0` |
| `name` | `name`, `country` | 비어 있지 않은 문자열 | 없음 | raw는 `name`, feature alias `country` 동시 생성 | `P0` |
| `rank` | `rank`, `class_rank` | 비어 있지 않은 문자열 | 없음 | raw는 `rank`, feature에서는 `class_rank`로 rename | `P0` |
| `rating` | `rating` | 0 이상 정수 | `"0"` | `int` 변환. `0`은 valid raw이지만 `rating_known = 0` flag 생성 권장 | `P1` |
| `wg_budam` | `wgBudam`, `wg_budam`, `burden_weight` | 양수 실수 | 정수형 입력 | `float` 변환, `<= 0` 금지 | `P0` |
| `wg_budam_bigo` | `wgBudamBigo`, `wg_budam_bigo` | 문자열 | `"-"` sentinel | raw 보존. feature에서는 `"-"`를 `None`으로 치환하고 `has_budam_note` 생성 | `P1` |
| `wg_hr` | `wgHr`, `wg_hr` | 문자열 | `"-"` 또는 형식 파손 가능 | raw 보존. `^\d+\([+-]?\d+\)$` 우선, 파생 `weight`/`weight_delta` 생성 실패 시 soft-fail | `P1` |
| `win_odds` | `winOdds`, `win_odds` | 0 이상 실수 | `int`/`float` 혼합, `0` | 저장은 `float`. `0` 또는 파싱 실패는 `market_signal_missing`으로 처리하고 말 자체는 제거 금지 | `P1` |
| `plc_odds` | `plcOdds`, `plc_odds` | 0 이상 실수 | `int`/`float` 혼합, `0` | 저장은 `float`. `0` 또는 파싱 실패는 `market_signal_missing`으로 처리 | `P1` |
| `ilsu` | `ilsu` | 0 이상 정수 또는 `None` | 문자열 숫자 | optional. 실패 시 `None` | `P2` |
| `hr_tool` | `hrTool`, `hr_tool` | 문자열 또는 `None` | 공백 문자열 | trim 후 빈값은 `None` | `P2` |
| `weight` | `wg_hr` 파생 | 양수 정수 또는 `None` | `wg_hr` 파싱 실패 | 첫 번째 숫자 블록만 추출. 실패 시 `None` | `P1` |
| `country` | `name` 파생 | 문자열 | 없음 | `name` 복제 alias. 직접 raw source로 취급하지 않음 | `P2` |

### 1-1. 후보 생성 핵심 숫자형 필드의 운영 경계값

저장소 내 `packages/scripts/data/races/**/*_prerace.json` 샘플 10,285건을 기준으로 확인한 관측 범위는 아래와 같다.

- `rating`: `0..117`
- `wgBudam`: `50..60`
- `wgHr` 파생 체중: 서울/부경 `387..579`, 제주 `241..316`
- `wgHr` 파생 증감: `-34..39`
- `winOdds`: `0..187`
- `plcOdds`: `0..54.4`

운영 전처리는 이 분포보다 넓은 보수적 guardrail 을 두고, hard field 와 soft field 를 다르게 처리한다.

| canonical 컬럼 | 후보 생성 용도 | 허용 범위 | 결측/이상치 처리 | 비고 |
| --- | --- | --- | --- | --- |
| `rating` | 능력치 원천 | `0 <= x <= 140` | 파싱 실패/140 초과는 `None`, `rating_parse_failed` 또는 `rating_outlier` | `0`은 미상 레이팅으로 유지 |
| `wg_budam` | 부담중량 및 상대순위 | `40 <= x <= 65` | 범위 이탈은 `wg_budam_outlier`로 보고 말 row 자체를 운영 snapshot 에서 제외 | `P0` hard field |
| `weight` | `burden_ratio`, 체중 레벨 | `200 <= x <= 650` | 범위 이탈은 `None`, `weight_outlier` | `wg_hr` raw 는 보존 |
| `weight_delta` | 체중 증감 신호 | `-40 <= x <= 40` | 괄호 미존재/파싱 실패/범위 이탈은 `None`, `weight_delta_missing/parse_failed/outlier` | `wg_hr` 괄호 내부 값만 사용 |
| `win_odds` | 시장 신호, 인기도 proxy | `0 < x <= 300` | `0`/파싱 실패/범위 이탈은 `None`, `market_signal_missing`; 추가로 `popularity_unusable` | downstream `odds_rank` 산출 불가 표시 |
| `plc_odds` | 보조 시장 신호 | `0 < x <= 100` | `0`/파싱 실패/범위 이탈은 `None`, `market_signal_missing` | 말 row 유지 |

### 2. 확장 블록 컬럼

| canonical 컬럼 | 조인 키 | 기대 정규형 | 허용 raw 예외 | 전처리 기준 | 장애 등급 |
| --- | --- | --- | --- | --- | --- |
| `hrDetail` | `hr_no` | dict | API 실패, row 없음 | 항상 dict 보장. `{}` 허용. 채워진 경우 `hrNo`/`hrName` 일치 검사 | `P2` |
| `jkDetail` | `jk_no` | dict | `spDate = "-"` | 항상 dict 보장. `birthday`, `debut`, `spDate`는 8자리 문자열 또는 `None`으로 정규화 | `P2` |
| `trDetail` | `tr_no` | dict | `age = "-"`, `birthday = "-"` | 항상 dict 보장. sentinel `"-"`는 `None` 처리 | `P2` |
| `jkStats` | `jk_no` | dict | row 없음 | 항상 dict 보장. count/rate 필드는 0 이상 정수로 정규화 | `P2` |
| `owDetail` | `ow_no` | dict | row 없음 | 항상 dict 보장. owner ID는 문자열로 정규화 | `P2` |
| `training` | `hr_name` | dict | 이름 매칭 실패 | 항상 dict 보장. 미일치 시 `{}` + unmatched warning, 예측 중단 금지 | `P2` |

## 운영용 판정 규칙

### hard-fail (`P0`)

- `chul_no` 중복 또는 파싱 실패
- 핵심 식별자 `hr_no`, `jk_no`, `tr_no`, `ow_no` 누락
- 핵심 이름 `hr_name`, `jk_name`, `tr_name`, `ow_name` 누락
- `age <= 0`
- `wg_budam <= 0`

위 조건은 entry row 자체의 신뢰성이 깨진 경우다. raw 저장은 가능하지만, 운영용 snapshot 승격 전 반드시 수동 검토 대상이다.

### soft-fail (`P1`)

- `rating = 0`
- `wg_budam_bigo = "-"`, `spDate = "-"`, `trDetail.age = "-"`, `trDetail.birthday = "-"` 같은 sentinel 값
- `wg_hr` 파싱 실패
- `win_odds`/`plc_odds` 파싱 실패 또는 0

이 경우 예측은 계속 생성해야 하며, 컬럼별 missing flag를 추가하는 쪽이 원칙이다.

### non-blocking (`P2`)

- `ilsu`, `hr_tool` 누락
- `hrDetail`, `jkDetail`, `trDetail`, `jkStats`, `owDetail`, `training` 빈 dict
- `training` 이름 매칭 실패

이 경우 경주 예측과 재학습을 중단하지 않는다.

## 즉시 반영할 운영 메모

1. `win_odds <= 0` 말을 제거하는 legacy 전처리는 더 이상 운영 기준으로 사용하면 안 된다. 출전마 삭제가 아니라 `market_signal_missing`으로 처리해야 한다.
2. ID 계열은 원천이 숫자로 오더라도 조인과 선행 0 보존 때문에 canonical 단계에서 문자열로 고정해야 한다.
3. `wg_hr`, `hrLastAmt` 같은 복합 문자열은 raw와 parsed 컬럼을 분리해 보존해야 한다.
4. 확장 블록은 `None`이 아니라 빈 dict로 정규화해야 downstream schema와 테스트 계약을 유지할 수 있다.

## 후속 작업 제안

1. `data/contracts/prerace_field_metadata_v1.csv`의 `notes` 컬럼에 본 규칙표의 `priority_grade`와 soft-fail 플래그를 연결한다.
2. examples에 `API11_1`, `API14_1`, `API329`, `API72_2`, `API189_1`, `API9_1` 실샘플을 보강해 현재 문서의 `P2` 가정을 샘플 기반으로 승격한다.
3. `collection_preprocessing.py`의 zero-odds exclusion을 canonical prereace 전처리와 분리한다.
