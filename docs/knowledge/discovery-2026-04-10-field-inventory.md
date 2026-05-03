# KRA 데이터 원천 필드 인벤토리

**Date:** 2026-04-10  
**Category:** discovery  
**Status:** active  
**Related files:** `apps/api/services/kra_api_service.py`, `apps/api/services/race_processing_workflow.py`, `apps/api/services/collection_service.py`, `apps/api/services/result_collection_service.py`, `packages/scripts/shared/db_client.py`, `examples/`

## 목적

출전표 확정 시점 정보만으로 KRA 전 경주 top3 무순서 예측 시스템을 운영하기 위해, 현재 저장소가 의존하는 데이터 원천을 식별하고 원천별 raw 필드, 타입, 의미, 추출 경로를 한 문서에 고정한다.

이 문서는 두 가지를 함께 다룬다.

1. **외부 원천**: KRA 공공 API
2. **내부 지속 원천**: PostgreSQL 적재 지점

주의:

- 본 문서의 **raw field** 는 API 응답의 `response.body.items.item[*]` 기준이다.
- 신규 6개 API 중 일부는 저장소에 실샘플 JSON이 없으므로, **코드에서 실제 참조하는 키**와 **설계/테스트에 등장하는 키**를 기준으로 적었다.
- `API214_1`, `API160_1`, `API301`에는 사후 정보가 섞일 수 있으므로, **연구용 feature 입력 허용 여부**를 별도 표기했다.

## 공통 응답 envelope

모든 KRA API는 현재 코드에서 아래 표준 구조로 읽는다.

| 경로 | 타입 | 의미 | 추출 경로 |
|---|---|---|---|
| `response.header.resultCode` | string | 성공/실패 코드 (`00` 성공) | `KRAResponseAdapter.is_successful_response()` |
| `response.header.resultMsg` | string | 응답 메시지 | `KRAResponseAdapter.get_error_message()` |
| `response.body.items.item` | object or array | 실제 레코드 payload | `KRAResponseAdapter.extract_items()` |
| `response.body.numOfRows` | int | 요청 row 수 | adapter 직접 미사용, raw 보존 |
| `response.body.pageNo` | int | 페이지 번호 | adapter 직접 미사용, raw 보존 |
| `response.body.totalCount` | int | 총 건수 | adapter 직접 미사용, raw 보존 |

## 원천 요약

| 원천 | 엔드포인트 | grain | 시점 성격 | 현재 저장 위치 | 연구 입력 허용 |
|---|---|---|---|---|---|
| API214_1 | `API214_1/RaceDetailResult_1` | 경주-출전마 | 혼합, 사전/사후 필드 동시 노출 가능 | `races.basic_data.race_info`, `races.basic_data.horses[]`, `races.result_data` | 조건부 허용 |
| API8_2 | `API8_2/raceHorseInfo_2` | 말 | 사전 마스터 | `horses[].hrDetail` | 허용 |
| API12_1 | `API12_1/jockeyInfo_1` | 기수 | 사전 마스터 | `horses[].jkDetail` | 허용 |
| API19_1 | `API19_1/trainerInfo_1` | 조교사 | 사전 마스터 | `horses[].trDetail` | 허용 |
| API72_2 | `API72_2/racePlan_2` | 경주 | 사전 확정 | `races.basic_data.race_plan` | 허용 |
| API189_1 | `API189_1/Track_1` | 경주 | 사전 변동 | `races.basic_data.track` | 허용 |
| API9_1 | `API9_1/raceHorseCancelInfo_1` | 경주-취소마 | 사전 변동 | `races.basic_data.cancelled_horses[]` | 허용 |
| API11_1 | `API11_1/jockeyResult_1` | 기수 | 사전 누적 통계 | `horses[].jkStats` | 허용 |
| API14_1 | `API14_1/horseOwnerInfo_1` | 마주 | 사전 마스터 | `horses[].owDetail` | 허용 |
| API329 | `API329/textDataSeGtscol` | 말(이름 매칭) | 사전 조교 현황 | `horses[].training` | 허용 |
| API160_1 | `API160_1/integratedInfo_1` | 경주-배당 row | 사후 확정 가능성 높음 | `race_odds`, 결과 수집 직후 | 기본 비허용 |
| API301 | `API301/Dividend_rate_total` | 경주-배당 row | 사후 확정 | `race_odds` 백필 | 비허용 |
| PostgreSQL `races` | 내부 | 경주 | 적재본 | 평가/학습 로더 입력 | 허용(사전 컬럼만) |
| PostgreSQL `race_odds` | 내부 | 경주-배당 row | 사후 적재본 | 분석/감사 | 비허용 |

## 추출 경로 맵

### 외부 API 진입점

- `apps/api/services/kra_api_service.py`
  - `get_race_info()`
  - `get_horse_info()`
  - `get_jockey_info()`
  - `get_trainer_info()`
  - `get_race_plan()`
  - `get_track_info()`
  - `get_cancelled_horses()`
  - `get_jockey_stats()`
  - `get_owner_info()`
  - `get_training_status()`
  - `get_final_odds()`
  - `get_final_odds_total()`

### 수집 파이프라인 진입점

- `apps/api/services/race_processing_workflow.py`
  - `KraRaceSourceAdapter.fetch_race_card()`
  - `fetch_race_plan()`
  - `fetch_track()`
  - `fetch_cancelled_horses()`
  - `fetch_training_map()`
  - `fetch_horse_bundle()`
  - `fetch_final_odds()`
- `apps/api/services/collection_service.py`
  - `collect_race_data()`
  - `_collect_horse_details()`
  - `collect_race_odds()`
- `apps/api/services/result_collection_service.py`
  - `collect_result()`
  - `_collect_odds_after_result()`

### 내부 소비 경로

- `packages/scripts/shared/db_client.py`
  - `find_races_with_results()`
  - `load_race_basic_data()`
  - `get_race_result()`
  - `get_past_top3_stats_for_race()`
- `packages/scripts/evaluation/data_loading.py`
  - `RaceEvaluationDataLoader.load_race_data()`
- `packages/scripts/autoresearch/prepare.py`
  - `create_snapshot()`
  - `_extract_race_data()`

## 조인 그래프 및 키

현재 저장소는 **별도 정규화 마스터 테이블을 만들어 SQL join 하는 구조가 아니라**, 수집 시점에 외부 원천을 `races.basic_data` 안으로 **선조인(materialized join)** 해 둔다.  
즉 운영상 핵심 join은 대부분 API 응답 간 join이며, DB 단계에서는 `races` 1행이 한 경주의 완결 스냅샷 역할을 한다.

### 조인 매트릭스

| 단계 | 기준 grain | source -> target | join key | 생성 방식 |
|---|---|---|---|---|
| 경주 식별 고정 | race | `API214_1` -> `basic_data.{race_date,race_no,date,meet,race_number}` | `rcDate + rcNo + meet` | `KRAResponseAdapter.extract_race_metadata()` |
| 출전마 카드 생성 | race-entry | `API214_1.item[]` -> `basic_data.horses[]` | `chulNo` | `extract_race_entries()` + `normalize_prerace_horse_entry()` |
| 경주 계획 조인 | race | `API72_2` -> `basic_data.race_plan` | `rcDate + rcNo + meet` | `select_matching_race_item()` 후 snake_case 변환 |
| 주로/날씨 조인 | race | `API189_1` -> `basic_data.track` | `rcDate + rcNo + meet` | `select_matching_race_item()` 후 snake_case 변환 |
| 취소마 조인 | race-entry | `API9_1` -> `basic_data.cancelled_horses[]` | `rcDate + rcNo + meet`, 보조키 `chulNo` | `select_matching_race_items()` 후 row 전체 저장 |
| 말 상세 조인 | horse | `API8_2` -> `horses[].hrDetail` | `hrNo` | `fetch_horse_info()` 결과 첫 row를 snake_case dict로 저장 |
| 기수 상세 조인 | jockey | `API12_1` -> `horses[].jkDetail` | `jkNo` | `fetch_jockey_info()` 결과 첫 row 저장 |
| 조교사 상세 조인 | trainer | `API19_1` -> `horses[].trDetail` | `trNo` | `fetch_trainer_info()` 결과 첫 row 저장 |
| 기수 성적 조인 | jockey | `API11_1` -> `horses[].jkStats` | `jkNo`, 요청 시 `meet` 포함 | `fetch_jockey_stats()` 결과 첫 row 저장 |
| 마주 상세 조인 | owner | `API14_1` -> `horses[].owDetail` | `owNo`, fallback `hrDetail.ow_no` | `fetch_owner_info()` 결과 첫 row 저장 |
| 조교 현황 조인 | horse-name | `API329` -> `horses[].training` | 현재 `hrName` 문자열 매칭 | `fetch_training_map()` 이 `hrnm -> row` map 생성 후 horse row에 부착 |
| 결과 배당 저장 | race-odds row | `API160_1/API301` -> `race_odds` | `race_id + pool + chul_no + chul_no2 + chul_no3 + source` | odds row를 정규 컬럼으로 upsert |

### 설계상 중요한 해석

- `horses[].chul_no` 는 한 경주 안에서만 유효한 **행 anchor key** 다.
- `hr_no`, `jk_no`, `tr_no`, `ow_no` 는 외부 상세 API를 붙일 때 쓰는 **개체 식별 key** 다.
- `API329` 만 안정적인 숫자 key가 없어 현재 `hrName` string join을 쓴다.
- DB 안에는 `horses`, `jockeys`, `trainers`, `owners` 같은 별도 차원 테이블이 없다. 조인 결과는 모두 `races.basic_data.horses[]` 안에 비정규화 저장된다.

## 원천별 raw 필드 인벤토리

## 1. API214_1 `RaceDetailResult_1`

### 요청 파라미터

| 파라미터 | 타입 | 의미 |
|---|---|---|
| `meet` | string | 경마장 코드 (`1` 서울, `2` 제주, `3` 부경) |
| `rc_date` | string | 경주일 `YYYYMMDD` |
| `rc_no` | int | 경주 번호 |
| `numOfRows` | int | row 수 |
| `pageNo` | int | 페이지 |

### 현재 코드상 용도

- 기본 경주 카드 수집
- 결과 수집 시 top3 라벨 추출 (`ord`)
- 과거 성적 조회용 내부 적재본 생성

### 시점 주의

- `ord` 는 명백한 사후 결과다.
- `winOdds`, `plcOdds` 는 API 설명상 시점 검증이 더 필요하다.
- 따라서 **출전표 확정 시점 연구 입력에서는 `ord` 금지**, odds 도 snapshot 시점 검증 전에는 보수적으로 취급해야 한다.

### raw 필드

#### 1-1. 경주 식별/일정

| 필드 | 타입 | 의미 |
|---|---|---|
| `rcDate` | int/string | 경주일 |
| `rcNo` | int | 경주 번호 |
| `meet` | string | 경마장 |
| `rcDay` | string | 요일 |
| `rcTime` | int/string | 경주 시각 |
| `ilsu` | int | 시행 회차/일수 식별자 |
| `rcName` | string | 경주명 |
| `rcDist` | int | 거리 |

#### 1-2. 경주 조건/상금

| 필드 | 타입 | 의미 |
|---|---|---|
| `ageCond` | string | 연령 조건 |
| `prizeCond` | string | 상금 조건 |
| `budam` | string | 부담중량 조건 |
| `chaksun1` | int | 1착 상금 |
| `chaksun2` | int | 2착 상금 |
| `chaksun3` | int | 3착 상금 |
| `chaksun4` | int | 4착 상금 |
| `chaksun5` | int | 5착 상금 |

#### 1-3. 출전마/사람 식별

| 필드 | 타입 | 의미 |
|---|---|---|
| `chulNo` | int | 출전번호 |
| `hrNo` | string | 말 번호 |
| `hrName` | string | 말 이름 |
| `name` | string | 국적/분류명으로 보이는 필드 |
| `sex` | string | 성별 |
| `age` | int | 말 나이 |
| `birthday` | int/string | 출생일 |
| `jkNo` | string | 기수 번호 |
| `jkName` | string | 기수 이름 |
| `trNo` | string | 조교사 번호 |
| `trName` | string | 조교사 이름 |
| `owNo` | int/string | 마주 번호 |
| `owName` | string | 마주 이름 |

#### 1-4. 등급/능력/장구/체중

| 필드 | 타입 | 의미 |
|---|---|---|
| `rank` | string | 경주 등급/말 등급 표기 |
| `rating` | int | 레이팅 |
| `wgBudam` | int/float | 부담중량 |
| `wgBudamBigo` | string | 부담중량 비고 |
| `wgHr` | string | 마체중 및 증감 |
| `wgJk` | int/float | 기수 중량 관련 값 |
| `hrTool` | string | 장구 |
| `buga1` | int | 추가 조건 값 1 |
| `buga2` | int | 추가 조건 값 2 |
| `buga3` | int | 추가 조건 값 3 |

#### 1-5. 주로/날씨/시장

| 필드 | 타입 | 의미 |
|---|---|---|
| `track` | string | 주로 상태 |
| `weather` | string | 날씨 |
| `winOdds` | float | 단승 계열 odds |
| `plcOdds` | float | 연승/복승 계열 odds |

#### 1-6. 결과/사후 지표

| 필드 | 타입 | 의미 |
|---|---|---|
| `ord` | int | 최종 착순 |
| `ordBigo` | string | 착순 비고 |
| `rankRise` | int | 순위 상승/변동 |
| `diffUnit` | string/float | 마신 차이 |

#### 1-7. 구간 순위

| 필드 | 타입 | 의미 |
|---|---|---|
| `buG1fOrd` | int | 부산 1f 지점 순위 |
| `buG2fOrd` | int | 부산 2f 지점 순위 |
| `buG3fOrd` | int | 부산 3f 지점 순위 |
| `buG4fOrd` | int | 부산 4f 지점 순위 |
| `buG6fOrd` | int | 부산 6f 지점 순위 |
| `buG8fOrd` | int | 부산 8f 지점 순위 |
| `buS1fOrd` | int | 부산 결승 전 1f 순위 |
| `sjG1fOrd` | int | 제주/서울 계열 구간 순위 1 |
| `sjG3fOrd` | int | 제주/서울 계열 구간 순위 3 |
| `sjS1fOrd` | int | 제주/서울 결승 전 1f 순위 |
| `sj_1cOrd` | int | 코너 통과 순위 1 |
| `sj_2cOrd` | int | 코너 통과 순위 2 |
| `sj_3cOrd` | int | 코너 통과 순위 3 |
| `sj_4cOrd` | int | 코너 통과 순위 4 |

#### 1-8. 구간 누적/분할 시간

| 필드 | 타입 | 의미 |
|---|---|---|
| `buG1fAccTime` | float | 부산 1f 누적 시간 |
| `buG2fAccTime` | float | 부산 2f 누적 시간 |
| `buG3fAccTime` | float | 부산 3f 누적 시간 |
| `buG4fAccTime` | float | 부산 4f 누적 시간 |
| `buG6fAccTime` | float | 부산 6f 누적 시간 |
| `buG8fAccTime` | float | 부산 8f 누적 시간 |
| `buS1fAccTime` | float | 부산 결승 전 1f 누적 시간 |
| `buS1fTime` | float | 부산 결승 전 1f 분할 시간 |
| `bu_1fGTime` | float | 부산 1f 게이트 시간 |
| `bu_2fGTime` | float | 부산 2f 게이트 시간 |
| `bu_3fGTime` | float | 부산 3f 게이트 시간 |
| `bu_4_2fTime` | float | 부산 4-2f 구간 시간 |
| `bu_6_4fTime` | float | 부산 6-4f 구간 시간 |
| `bu_8_6fTime` | float | 부산 8-6f 구간 시간 |
| `bu_10_8fTime` | float | 부산 10-8f 구간 시간 |
| `jeG1fTime` | float | 제주 1f 시간 |
| `jeG3fTime` | float | 제주 3f 시간 |
| `jeS1fTime` | float | 제주 결승 전 1f 시간 |
| `je_1cTime` | float | 제주 코너 1 통과 시간 |
| `je_2cTime` | float | 제주 코너 2 통과 시간 |
| `je_3cTime` | float | 제주 코너 3 통과 시간 |
| `je_4cTime` | float | 제주 코너 4 통과 시간 |
| `seG1fAccTime` | float | 서울 1f 누적 시간 |
| `seG3fAccTime` | float | 서울 3f 누적 시간 |
| `seS1fAccTime` | float | 서울 결승 전 1f 누적 시간 |
| `se_1cAccTime` | float | 서울 코너 1 누적 시간 |
| `se_2cAccTime` | float | 서울 코너 2 누적 시간 |
| `se_3cAccTime` | float | 서울 코너 3 누적 시간 |
| `se_4cAccTime` | float | 서울 코너 4 누적 시간 |

## 2. API8_2 `raceHorseInfo_2`

### 요청 파라미터

| 파라미터 | 타입 | 의미 |
|---|---|---|
| `hr_no` | string | 말 번호 |
| `pageNo` | int | 페이지 |
| `numOfRows` | int | row 수 |

### 저장 위치

- `horses[].hrDetail`

### raw 필드

| 필드 | 타입 | 의미 |
|---|---|---|
| `hrNo` | string | 말 번호 |
| `hrName` | string | 말 이름 |
| `sex` | string | 성별 |
| `birthday` | int/string | 출생일 |
| `meet` | string | 소속 경마장 |
| `name` | string | 국적/분류 |
| `rank` | string | 등급 |
| `rating` | int | 레이팅 |
| `owNo` | int/string | 마주 번호 |
| `owName` | string | 마주 이름 |
| `trNo` | string | 조교사 번호 |
| `trName` | string | 조교사 이름 |
| `faHrNo` | string | 부마 번호 |
| `faHrName` | string | 부마 이름 |
| `moHrNo` | string/int | 모마 번호 |
| `moHrName` | string | 모마 이름 |
| `rcCntT` | int | 통산 출전 수 |
| `rcCntY` | int | 올해 출전 수 |
| `ord1CntT` | int | 통산 1착 수 |
| `ord1CntY` | int | 올해 1착 수 |
| `ord2CntT` | int | 통산 2착 수 |
| `ord2CntY` | int | 올해 2착 수 |
| `ord3CntT` | int | 통산 3착 수 |
| `ord3CntY` | int | 올해 3착 수 |
| `chaksunT` | int | 통산 상금 |
| `hrLastAmt` | string | 최근 거래가/구입가 |

## 3. API12_1 `jockeyInfo_1`

### 요청 파라미터

| 파라미터 | 타입 | 의미 |
|---|---|---|
| `jk_no` | string | 기수 번호 |
| `pageNo` | int | 페이지 |
| `numOfRows` | int | row 수 |

### 저장 위치

- `horses[].jkDetail`

### raw 필드

| 필드 | 타입 | 의미 |
|---|---|---|
| `jkNo` | string | 기수 번호 |
| `jkName` | string | 기수 이름 |
| `age` | int | 나이 |
| `birthday` | int/string | 생년월일 |
| `debut` | int/string | 데뷔일 |
| `meet` | string | 소속 경마장 |
| `part` | string | 기수 구분 |
| `spDate` | string | 정지/특이일자 계열 필드 |
| `wgPart` | int/float | 허용 감량/체중 구분값 |
| `wgOther` | int/float | 기타 중량값 |
| `rcCntT` | int | 통산 출전 수 |
| `rcCntY` | int | 올해 출전 수 |
| `ord1CntT` | int | 통산 1착 수 |
| `ord1CntY` | int | 올해 1착 수 |
| `ord2CntT` | int | 통산 2착 수 |
| `ord2CntY` | int | 올해 2착 수 |
| `ord3CntT` | int | 통산 3착 수 |
| `ord3CntY` | int | 올해 3착 수 |

## 4. API19_1 `trainerInfo_1`

### 요청 파라미터

| 파라미터 | 타입 | 의미 |
|---|---|---|
| `tr_no` | string | 조교사 번호 |
| `pageNo` | int | 페이지 |
| `numOfRows` | int | row 수 |

### 저장 위치

- `horses[].trDetail`

### raw 필드

| 필드 | 타입 | 의미 |
|---|---|---|
| `trNo` | string | 조교사 번호 |
| `trName` | string | 조교사 이름 |
| `age` | string/int | 나이 또는 미상 |
| `birthday` | string/int | 생년월일 또는 미상 |
| `meet` | string | 소속 경마장 |
| `part` | int | 소속 조 |
| `stDate` | int/string | 개업/등록일 |
| `rcCntT` | int | 통산 출전 수 |
| `rcCntY` | int | 올해 출전 수 |
| `ord1CntT` | int | 통산 1착 수 |
| `ord1CntY` | int | 올해 1착 수 |
| `ord2CntT` | int | 통산 2착 수 |
| `ord2CntY` | int | 올해 2착 수 |
| `ord3CntT` | int | 통산 3착 수 |
| `ord3CntY` | int | 올해 3착 수 |
| `winRateT` | int/float | 통산 승률 |
| `winRateY` | int/float | 올해 승률 |
| `plcRateT` | int/float | 통산 복승률 |
| `plcRateY` | int/float | 올해 복승률 |
| `qnlRateT` | int/float | 통산 연승률 |
| `qnlRateY` | int/float | 올해 연승률 |

## 5. API72_2 `racePlan_2`

### 요청 파라미터

| 파라미터 | 타입 | 의미 |
|---|---|---|
| `meet` | string | 경마장 코드 |
| `rc_date` | string | 경주일 |
| `pageNo` | int | 페이지 |
| `numOfRows` | int | row 수 |

### 저장 위치

- `races.basic_data.race_plan`

### raw 필드

현재 저장소에서 확인된 키:

| 필드 | 타입 | 의미 |
|---|---|---|
| `rcNo` | int | 경주 번호 |
| `rank` | string | 등급 |
| `budam` | string | 부담 조건 |
| `rcDist` | int | 거리 |
| `schStTime` | int/string | 예정 출발 시각 |
| `chaksun1` | int | 1착 상금 |
| `chaksun2` | int | 2착 상금 |
| `chaksun3` | int | 3착 상금 |
| `chaksun4` | int | 4착 상금 |
| `chaksun5` | int | 5착 상금 |
| `ageCond` | string | 연령 조건 |
| `sexCond` | string | 성별 조건 |
| `spRating` | int | 하한 레이팅 |
| `stRating` | int | 상한 레이팅 |

## 6. API189_1 `Track_1`

### 요청 파라미터

| 파라미터 | 타입 | 의미 |
|---|---|---|
| `meet` | string | 경마장 코드 |
| `rc_date_fr` | string | 시작일 |
| `rc_date_to` | string | 종료일 |
| `pageNo` | int | 페이지 |
| `numOfRows` | int | row 수 |

### 저장 위치

- `races.basic_data.track`

### raw 필드

현재 저장소에서 확인된 키:

| 필드 | 타입 | 의미 |
|---|---|---|
| `rcNo` | int | 경주 번호 |
| `weather` | string | 날씨 |
| `track` | string | 주로 상태 텍스트 |
| `waterPercent` | int/float | 함수율 |
| `trackCd` | string | 주로 코드 |
| `temperature` | string/float | 기온 |
| `humidity` | string/float | 습도 |
| `windDirection` | string | 풍향 |
| `windSpeed` | string/float | 풍속 |

## 7. API9_1 `raceHorseCancelInfo_1`

### 요청 파라미터

| 파라미터 | 타입 | 의미 |
|---|---|---|
| `meet` | string | 경마장 코드 |
| `rc_date` | string | 경주일 |
| `pageNo` | int | 페이지 |
| `numOfRows` | int | row 수 |

### 저장 위치

- `races.basic_data.cancelled_horses[]`

### raw 필드

현재 저장소에서 확인된 키:

| 필드 | 타입 | 의미 |
|---|---|---|
| `rcNo` | int | 경주 번호 |
| `chulNo` | int | 취소된 출전번호 |
| `hrNo` | string | 말 번호 |
| `hrName` | string | 말 이름 |
| `reason` | string | 취소 사유 |

## 8. API11_1 `jockeyResult_1`

### 요청 파라미터

| 파라미터 | 타입 | 의미 |
|---|---|---|
| `jk_no` | string | 기수 번호 |
| `meet` | string | 경마장 코드 |
| `pageNo` | int | 페이지 |
| `numOfRows` | int | row 수 |

### 저장 위치

- `horses[].jkStats`

### raw 필드

현재 저장소에서 확인된 키:

| 필드 | 타입 | 의미 |
|---|---|---|
| `jkNo` | string | 기수 번호 |
| `jkName` | string | 기수 이름 |
| `ord1CntT` | int | 통산 1착 수 |
| `ord1CntY` | int | 올해 1착 수 |
| `ord2CntT` | int | 통산 2착 수 |
| `ord2CntY` | int | 올해 2착 수 |
| `rcCntT` | int | 통산 출전 수 |
| `rcCntY` | int | 올해 출전 수 |
| `winRateT` | float | 통산 승률 |
| `winRateY` | float | 올해 승률 |
| `qnlRateT` | float | 통산 연승률 |
| `qnlRateY` | float | 올해 연승률 |

## 9. API14_1 `horseOwnerInfo_1`

### 요청 파라미터

| 파라미터 | 타입 | 의미 |
|---|---|---|
| `ow_no` | string | 마주 번호 |
| `meet` | string | 경마장 코드 |
| `pageNo` | int | 페이지 |
| `numOfRows` | int | row 수 |

### 저장 위치

- `horses[].owDetail`

### raw 필드

현재 저장소에서 확인된 키:

| 필드 | 타입 | 의미 |
|---|---|---|
| `owNo` | int/string | 마주 번호 |
| `owName` | string | 마주 이름 |
| `ord1CntT` | int | 통산 1착 수 |
| `ord1CntY` | int | 올해 1착 수 |
| `rcCntT` | int | 통산 출전 수 |
| `rcCntY` | int | 올해 출전 수 |
| `chaksunT` | int | 통산 상금 |
| `chaksunY` | int | 올해 상금 |
| `ownerHorses` | int | 현재 보유 말 수 |
| `totHorses` | int | 누적 보유 말 수 |

## 10. API329 `textDataSeGtscol`

### 요청 파라미터

| 파라미터 | 타입 | 의미 |
|---|---|---|
| `trng_dt` | string | 조교일 |
| `pageNo` | int | 페이지 |
| `numOfRows` | int | row 수 |

### 저장 위치

- 임시 맵: `training_map[hrnm]`
- 최종 적재: `horses[].training`

### raw 필드

현재 저장소에서 확인된 키:

| 필드 | 타입 | 의미 |
|---|---|---|
| `hrnm` | string | 말 이름 |
| `remkTxt` | string | 조교 상태/비고 |
| `trngDt` | int/string | 조교일 |
| `beloNo` | string | 조 번호 |
| `beloTrngNo` | int | 조교 번호 |
| `ridrNm` | string | 기승/기승자 표기 |

### 특이사항

- 현재 구현은 `hrNo` 가 아니라 `hrnm` 으로 매칭한다.
- 동명이마 충돌 가능성이 있어, 운영 문맥에서는 보조 검증 키가 추가로 필요하다.

## 11. API160_1 `integratedInfo_1`

### 요청 파라미터

| 파라미터 | 타입 | 의미 |
|---|---|---|
| `meet` | string | 경마장 코드 |
| `rc_date` | string | 경주일 |
| `pool` | string, optional | 배당식 종류 |
| `rc_no` | int, optional | 경주 번호 |
| `pageNo` | int | 페이지 |
| `numOfRows` | int | row 수 |

### 저장 위치

- `race_odds`
- 결과 수집 직후 `_collect_odds_after_result()`

### raw 필드

현재 코드가 읽는 키:

| 필드 | 타입 | 의미 |
|---|---|---|
| `pool` | string | 배당식 이름 (`단승식`, `연승식` 등) |
| `chulNo` | int | 1번 말 |
| `chulNo2` | int | 2번 말 |
| `chulNo3` | int | 3번 말 |
| `odds` | float | 배당률 |
| `rcDate` | int/string | 경주일 |
| `rcNo` | int | 경주 번호 |

### 시점 주의

- 현재 코드에서는 **결과 수집 직후** 저장한다.
- 따라서 연구/학습 input feature 에는 넣지 말고, 사후 감사/시장 비교용으로만 써야 한다.

## 12. API301 `Dividend_rate_total`

### 요청 파라미터

| 파라미터 | 타입 | 의미 |
|---|---|---|
| `meet` | string | 경마장 코드 |
| `rc_date` | string | 경주일 |
| `pool` | string, optional | 배당식 종류 |
| `rc_no` | int, optional | 경주 번호 |
| `pageNo` | int | 페이지 |
| `numOfRows` | int | row 수 |

### 저장 위치

- `race_odds`
- `CollectionService.collect_race_odds(..., source="API301")`

### raw 필드

현재 코드가 읽는 키:

| 필드 | 타입 | 의미 |
|---|---|---|
| `pool` | string | 배당식 이름 |
| `chulNo` | int | 1번 말 |
| `chulNo2` | int | 2번 말 |
| `chulNo3` | int | 3번 말 |
| `odds` | float | 배당률 |
| `rcDate` | int/string | 경주일 |
| `rcNo` | int | 경주 번호 |

### 시점 주의

- API 명칭 자체가 `확정배당율종합` 이므로 사후 확정 데이터로 취급한다.
- pre-race 모델 feature 금지.

## 내부 지속 원천

## 13. PostgreSQL `races`

### 적재 경로

- `CollectionService._save_race_data()`
- `ResultCollectionService.collect_result()`
- `RaceProcessingWorkflow.SQLAlchemyRaceRepository.save_collection()`

### 물리 컬럼 스키마

| 컬럼 | 타입 | 의미 | 생성 방식 | 조인/소비 키 |
|---|---|---|---|---|
| `race_id` | string | 경주 PK, `{date}_{meet}_{race_number}` | 수집 시 top-level 식별자를 문자열 조합으로 생성 | `race_odds.race_id`, `predictions.race_id` FK |
| `date` | string(8) | 경주일 `YYYYMMDD` | `basic_data.date`에서 복사 | `unique_race(date, meet, race_number)` |
| `meet` | int | 경마장 코드 | `basic_data.meet`에서 복사 | `unique_race(date, meet, race_number)` |
| `race_number` | int | 경주 번호 | `basic_data.race_number`에서 복사 | `unique_race(date, meet, race_number)` |
| `race_name` | string nullable | 정규화 컬럼 예비 슬롯 | 현재 pre-race 저장 경로에서는 거의 미사용 | 조회 편의용 |
| `distance` | int nullable | 정규화 컬럼 예비 슬롯 | 현재는 `basic_data.race_plan.rc_dist`를 주로 사용 | 조회 편의용 |
| `track` | string nullable | 정규화 컬럼 예비 슬롯 | 현재는 `basic_data.track.track`를 주로 사용 | 조회 편의용 |
| `weather` | string nullable | 정규화 컬럼 예비 슬롯 | 현재는 `basic_data.track.weather`를 주로 사용 | 조회 편의용 |
| `collection_status` | enum | pre-race 수집 상태 | `pending/collected/enriched/failed` | `find_races*()` 필터 |
| `enrichment_status` | enum | 후속 보강 상태 | enrichment 단계에서 갱신 | 연구 파이프라인 상태 |
| `result_status` | enum | 결과 수집 상태 | 결과 적재 시 갱신 | `find_races_with_results()` 필터 |
| `basic_data` | JSONB | pre-race 허용 필드의 canonical snapshot | `normalize_and_validate_prerace_payload()` + `split_prerace_payload_for_storage()` 결과 | 평가/학습 핵심 입력 |
| `raw_data` | JSONB | 차단/보류/메타 필드 shadow + 실패 payload | `split_prerace_payload_for_storage()` shadow 결과 또는 실패 정보 | 감사/누수 추적 |
| `enriched_data` | JSONB | 후속 feature 보강 결과 | 현재 일부 연구 경로만 사용 | 향후 확장 |
| `result_data` | JSONB | 경주 결과 projection | `ResultCollectionService.collect_result()` | 라벨 전용 |
| `collected_at` | timestamptz | pre-race snapshot 저장 시각 | 수집 커밋 시 기록 | snapshot timing 판정 |
| `enriched_at` | timestamptz | 보강 완료 시각 | enrichment 완료 시 기록 | 보강 감사 |
| `result_collected_at` | timestamptz | 결과 저장 시각 | 결과 수집 완료 시 기록 | 라벨 감사 |
| `updated_at` | timestamptz | 최근 수정 시각 | trigger + 코드 명시 갱신 | 변경 추적 |
| `horse_count` | int | 말 수 메타데이터 | 일부 legacy 경로에서 계산 | 품질 점검 보조 |
| `warnings` | JSONB | 수집 경고 목록 | 품질/검증 경로가 누적 가능 | 품질 감사 |

### `basic_data` top-level 스키마

| 경로 | 타입 | 의미 | 생성 방식 | 조인 키/기준 |
|---|---|---|---|---|
| `schema_version` | string | canonical schema 버전 | 상수 `prerace-source-v1` | - |
| `race_date` | string(8) | 경주일 | `API214_1.rcDate` 정규화 | race identity |
| `race_no` | int | 경주 번호 | `API214_1.rcNo` 정수화 | race identity |
| `date` | string(8) | 하위호환용 경주일 | `race_date` 복제 | race identity |
| `meet` | int | 경마장 코드 | `API214_1.meet` 정규화 | race identity |
| `race_number` | int | 하위호환용 경주 번호 | `race_no` 복제 | race identity |
| `race_info` | object | `API214_1` 원본 envelope | camelCase 원본 보존 | `response.body.items.item[]` |
| `race_plan` | object | 경주 조건 블록 | `API72_2` 대상 row를 snake_case 정규화 | `rcDate + rcNo + meet` |
| `track` | object | 날씨/주로 블록 | `API189_1` 대상 row 정규화 | `rcDate + rcNo + meet` |
| `cancelled_horses` | array<object> | 취소/제외 행 목록 | `API9_1` 대상 row 전체 저장 | race key, 보조 `chul_no` |
| `horses` | array<object> | 경주 출전마 canonical rows | `API214_1` rows + 상세 API 조인 결과 | `chul_no` anchor |
| `failed_horses` | array<object> | 부분 실패 horse audit | 수집 중 개별 horse fetch 실패 기록 | `horse_no`, `horse_name` |
| `status` | string | `success` / `partial_failure` | horse 상세 수집 결과 집계 | - |
| `collected_at` | ISO datetime | snapshot 생성 시각 | post-processing 시 주입 | timing cutoff |

### `basic_data.race_plan` 스키마

| 컬럼 | 의미 | 생성 방식 |
|---|---|---|
| `rank` | 경주 등급 | `API72_2.rank` |
| `budam` | 부담 조건 | `API72_2.budam` |
| `rc_dist` | 거리 | `API72_2.rcDist` |
| `age_cond` | 연령 조건 | `API72_2.ageCond` |
| `sex_cond` | 성별 조건 | `API72_2.sexCond` optional |
| `sch_st_time` | 예정 발주 시각 | `API72_2.schStTime` optional |
| `chaksun1`~`chaksun5` | 1~5착 상금 | `API72_2.chaksun*` optional |

### `basic_data.track` 스키마

| 컬럼 | 의미 | 생성 방식 |
|---|---|---|
| `weather` | 날씨 | `API189_1.weather` |
| `track` | 주로 상태 | `API189_1.track` |
| `water_percent` | 수분율 | `API189_1.waterPercent` |
| `temperature` | 기온 | `API189_1.temperature` optional |
| `humidity` | 습도 | `API189_1.humidity` optional |
| `wind_direction` | 풍향 | `API189_1.windDirection` optional |
| `wind_speed` | 풍속 | `API189_1.windSpeed` optional |

### `basic_data.horses[]` canonical 스키마

| 컬럼 | 타입 | 의미 | 생성 방식 | 조인 키/소비 키 |
|---|---|---|---|---|
| `chul_no` | int | 해당 경주 출전번호 | `API214_1.chulNo` 정규화 | 경주 내 anchor key |
| `hr_no` | string | 말 번호 | `API214_1.hrNo` | `API8_2`, 과거통계 self-join |
| `hr_name` | string | 말 이름 | `API214_1.hrName` | `API329` 현재 조인 키 |
| `jk_no` | string | 기수 번호 | `API214_1.jkNo` | `API12_1`, `API11_1` |
| `jk_name` | string | 기수명 | `API214_1.jkName` | 설명용 |
| `tr_no` | string | 조교사 번호 | `API214_1.trNo` | `API19_1` |
| `tr_name` | string | 조교사명 | `API214_1.trName` | 설명용 |
| `ow_no` | string | 마주 번호 | `API214_1.owNo` | `API14_1` |
| `ow_name` | string | 마주명 | `API214_1.owName` | 설명용 |
| `age` | int | 나이 | `API214_1.age` 정수화 | feature |
| `sex` | string | 성별 | `API214_1.sex` bucket 정규화 | feature |
| `name` | string | 산지/국적 원문 | `API214_1.name` | feature |
| `country` | string nullable | canonical 산지/국적 | `name` alias 파생 | feature |
| `rank` | string | 등급 원문 | `API214_1.rank` | 모델 입력 시 `class_rank` rename |
| `rating` | int nullable | 레이팅 | `API214_1.rating` 파싱 | feature |
| `wg_budam` | float | 부담중량 | `API214_1.wgBudam` 파싱 | feature |
| `wg_budam_bigo` | string nullable | 부담중량 비고 | `API214_1.wgBudamBigo` | feature |
| `wg_hr` | string nullable | 마체중/증감 원문 | `API214_1.wgHr` | 원문 감사 |
| `weight` | int nullable | 마체중 | `wg_hr` 파생 또는 explicit weight | feature |
| `weight_delta` | int nullable | 증감 | `wg_hr` 파싱 | feature |
| `win_odds` | float nullable | 단승 odds | `API214_1.winOdds` | 현재 운영 `보류` |
| `plc_odds` | float nullable | 연승 odds | `API214_1.plcOdds` | 현재 운영 `보류` |
| `ilsu` | int nullable | 시행 일수/회차 보조값 | `API214_1.ilsu` | 선택 feature |
| `hr_tool` | string nullable | 장구 정보 | `API214_1.hrTool` | 선택 feature |
| `hrDetail` | object | 말 상세 블록 | `API8_2` 첫 row 전체 저장 | `hr_no` join 결과 |
| `jkDetail` | object | 기수 상세 블록 | `API12_1` 첫 row 저장 | `jk_no` join 결과 |
| `trDetail` | object | 조교사 상세 블록 | `API19_1` 첫 row 저장 | `tr_no` join 결과 |
| `jkStats` | object | 기수 성적 블록 | `API11_1` 첫 row 저장 | `jk_no` join 결과 |
| `owDetail` | object | 마주 상세 블록 | `API14_1` 첫 row 저장 | `ow_no` join 결과 |
| `training` | object | 조교 현황 블록 | `API329` name-based match | `hr_name` join 결과 |
| `normalization_flags` | array<string> | 파싱/결측/보정 audit | `normalize_prerace_horse_entry()` 파생 | 품질 감사 |

### `raw_data` 스키마

| 경로 | 의미 | 생성 방식 |
|---|---|---|
| `storage_policy_version` | shadow 저장 정책 버전 | 상수 |
| `source_field_tags` | 필드별 허용/차단 태그 | `build_source_field_tags()` |
| `storage_summary.blocked_from_basic_count` | `basic_data`에서 제외된 필드 수 | split 시 집계 |
| `storage_summary.copied_to_shadow_count` | shadow에 복사된 필드 수 | split 시 집계 |
| `tagged_field_shadow.*` | 차단/보류/메타 필드 원본 | `split_prerace_payload_for_storage()` 결과 |

### `result_data` 스키마

| 경로 | 타입 | 의미 | 생성 방식 | 조인 키 |
|---|---|---|---|---|
| `top3` 또는 list payload | list<int> | 1~3위 출전번호 | `API214_1` 결과 row에서 projection | `horses[].chul_no` 와 membership 비교 |

### 주의

- 평가/학습은 실제로 `basic_data` 를 읽어 feature를 만든다.
- 따라서 **외부 raw API의 시점 누수는 DB 적재 후에도 그대로 남는다**.
- `RaceDBClient.get_past_top3_stats_for_race()` 는 별도 테이블이 아니라 `races.basic_data->horses[]` 를 다시 펼쳐 `elem->>'hr_no'` 로 self-join 성격의 과거 통계를 계산한다.

## 14. PostgreSQL `race_odds`

### 적재 경로

- `RaceProcessingWorkflow.collect_odds()`
- `ResultCollectionService._collect_odds_after_result()`

### 컬럼

| 컬럼 | 타입 | 의미 | 생성 방식 | 조인 키 |
|---|---|---|---|---|
| `id` | serial | surrogate PK | DB autoincrement | - |
| `race_id` | string | 경주 식별자 | `{date}_{meet}_{race_number}` 로 결정된 `races.race_id` | `races.race_id` FK |
| `pool` | string | 배당식 코드 (`WIN`, `PLC`, `QNL`, `EXA`, `QPL`, `TLA`, `TRI`, `XLA`) | API row `pool` 정규화 | unique key 일부 |
| `chul_no` | int | 1번 말 | API row `chulNo` | unique key 일부 |
| `chul_no2` | int | 2번 말 | API row `chulNo2`, 없으면 0 | unique key 일부 |
| `chul_no3` | int | 3번 말 | API row `chulNo3`, 없으면 0 | unique key 일부 |
| `odds` | numeric | 배당률 | API row `odds` 파싱 | 분석 값 |
| `rc_date` | string | 경주일 | API row `rcDate` | 날짜 파티셔닝 보조 |
| `source` | string | `API160_1` 또는 `API301` | 수집 호출 인자 | unique key 일부 |
| `collected_at` | timestamp | 적재 시각 | upsert 시 DB now() | 감사 |

### 제약과 해석

- unique constraint는 `(race_id, pool, chul_no, chul_no2, chul_no3, source)` 이다.
- 즉 동일 경주/동일 배당식/동일 조합/동일 원천은 한 행만 유지되고, 재수집 시 `odds` 와 `collected_at` 만 갱신된다.
- `race_odds` 는 pre-race feature join 대상이 아니라 **사후 감사/시장 분석용 side table** 이다.

## 운영 해석 메모

### 출전표 확정 시점에 바로 사용할 수 있는 원천

- API8_2
- API12_1
- API19_1
- API72_2
- API189_1
- API9_1
- API11_1
- API14_1
- API329

### 시점 검증 없이는 입력 금지할 원천/필드

- API214_1의 `ord`
- API160_1 전체
- API301 전체
- `races.result_data`
- `race_odds`

### 추가 검증 과제

1. API214_1의 `winOdds`/`plcOdds` 가 정확히 어느 시점 snapshot 인지 실측 필요
2. API329 는 `hrnm` 이름 매칭 대신 더 안정적인 key 확보 필요
3. API72_2/API189_1/API9_1/API11_1/API14_1/API329 실샘플 JSON을 `examples/` 에 보강해 문서를 샘플 기반으로 승격할 필요가 있음

## 결론

현재 저장소의 실운영 데이터 원천은 **KRA 공공 API 12종 + PostgreSQL 적재본 2종**으로 정리된다.  
이 중 **pre-race 입력으로 안전한 핵심 원천은 9종(API8_2, 12_1, 19_1, 72_2, 189_1, 9_1, 11_1, 14_1, 329)** 이고, **결과/확정배당 계열은 라벨·사후감사용으로만 분리**해야 한다.  
향후 무인 운영 안정화를 위해서는 신규 API 실샘플 보관과 API214 odds 시점 검증이 다음 필수 작업이다.
