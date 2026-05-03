# 출전표 확정 시점 공통 스키마 및 원천 필드 매핑

## 목적

이 문서는 `출전표 확정 시점까지 획득 가능한 정보만` 사용한다는 운영 제약을 저장 구조 수준에서 고정한다. 기준 저장 구조는 현재 수집 파이프라인이 DB `basic_data`에 저장하는 payload이며, 코드 기준선은 [packages/scripts/shared/prerace_source_schema.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prerace_source_schema.py)다.

화이트리스트/블랙리스트와 모델 입력 허용 범위의 최종 기준은 [출전표 확정 시점 데이터 화이트리스트·블랙리스트 정책](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-data-whitelist-blacklist-policy.md)을 우선한다. 이 문서는 저장 구조와 원천 매핑에 초점을 둔다.

필드별 실제 가용 시점과 예외 규칙은 별도 기준 문서 [kra-race-lifecycle-timing-matrix.md](/Users/chsong/Developer/Personal/kra-analysis/docs/kra-race-lifecycle-timing-matrix.md) 를 따른다. 이 문서는 "무슨 필드를 저장할지"를, 시점 매트릭스는 "그 필드를 언제까지 허용할지"를 정의한다.

DB 저장 단위에서 어떤 테이블·컬럼이 실제로 사전/사후/메타인지 판정하는 기준은 [DB 테이블·컬럼 가용 시점 매핑 v1](/Users/chsong/Developer/Personal/kra-analysis/docs/table-column-availability-map.md) 을 따른다.

원천 인벤토리와 시점 매트릭스를 통합한 운영용 기준표는 [prerace-standard-field-catalog.md](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-standard-field-catalog.md) 에서 관리한다. 구현/검증 단계에서는 스키마 정의보다 카탈로그의 `운영 사용` 판정을 우선 적용한다.

## 범위

- 포함: `API214_1`, `API72_2`, `API189_1`, `API9_1`, `API8_2`, `API12_1`, `API19_1`, `API11_1`, `API14_1`, `API329`
- 제외: 실제 착순, 결승 기록, 확정 배당금, 구간통과 순위/기록, 결과 테이블
- 목표: 모든 KRA 경주에 대해 예측 가능한 최소 입력을 보장하고, 성능 고도화용 확장 블록을 동일 스키마 안에 수용

## 공통 스키마

`schema_version = "prerace-source-v1"`

```json
{
  "schema_version": "prerace-source-v1",
  "race_date": "20260315",
  "race_no": 5,
  "date": "20260315",
  "meet": 1,
  "race_number": 5,
  "race_info": { "response": { "body": { "items": { "item": [] } } } },
  "race_plan": {
    "rank": "국6등급",
    "budam": "별정A",
    "rc_dist": 1200,
    "age_cond": "연령오픈"
  },
  "track": {
    "weather": "맑음",
    "track": "건조",
    "water_percent": 3
  },
  "cancelled_horses": [],
  "horses": [
    {
      "chul_no": 3,
      "hr_no": "0054782",
      "hr_name": "천년의질주",
      "jk_no": "090123",
      "jk_name": "문세영",
      "tr_no": "070123",
      "tr_name": "김영관",
      "ow_no": 110034,
      "ow_name": "(주)나스카",
      "age": 3,
      "sex": "수",
      "name": "한국",
      "rank": "국6등급",
      "rating": 0,
      "wg_budam": 57,
      "wg_budam_bigo": "-",
      "wg_hr": "488(-6)",
      "win_odds": 5.2,
      "plc_odds": 1.8,
      "hrDetail": {},
      "jkDetail": {},
      "trDetail": {},
      "jkStats": {},
      "owDetail": {},
      "training": {}
    }
  ],
  "collected_at": "2026-04-10T09:00:00+09:00",
  "status": "success",
  "failed_horses": []
}
```

## 필수 필드

### 1. 경주 단위 하드 필수

이 필드가 없으면 해당 경주는 "모든 경주 예측" 대상에 안전하게 포함할 수 없다.

| 스키마 경로 | 주 용도 | 원천 |
| --- | --- | --- |
| `race_date`, `race_no`, `meet` | 경주 식별자 | `API214_1` |
| `race_info.response.body.items.item[]` | 원본 출전표 보존 | `API214_1` |
| `race_plan.rank`, `race_plan.budam`, `race_plan.rc_dist`, `race_plan.age_cond` | 경주 조건 | `API72_2` |
| `track.weather`, `track.track`, `track.water_percent` | 날씨/주로 | `API189_1` |
| `cancelled_horses[]` | 취소마 반영 | `API9_1` |

### 2. 출전마 단위 하드 필수

모든 경주에 대해 top-3 예측을 생성하려면 각 출전마마다 아래 최소 필드가 필요하다.

| 스키마 경로 | 주 용도 | 원천 |
| --- | --- | --- |
| `horses[].chul_no` | 출전마 정렬/예측 출력 | `API214_1` |
| `horses[].hr_no`, `horses[].hr_name` | 말 식별 | `API214_1` |
| `horses[].jk_no`, `horses[].jk_name` | 기수 식별 | `API214_1` |
| `horses[].tr_no`, `horses[].tr_name` | 조교사 식별 | `API214_1` |
| `horses[].ow_no`, `horses[].ow_name` | 마주 식별 | `API214_1` |
| `horses[].age`, `horses[].sex`, `horses[].name` | 기초 개체 정보 | `API214_1` |
| `horses[].rank`, `horses[].rating` | 등급/레이팅 | `API214_1` |
| `horses[].wg_budam`, `horses[].wg_budam_bigo`, `horses[].wg_hr` | 부담중량/마체중 | `API214_1` |
| `horses[].win_odds`, `horses[].plc_odds` | 시장 신호 | `API214_1` |

### 3. 확장 블록

이 블록은 성능 고도화에는 중요하지만, 일시 실패해도 빈 dict 또는 null 허용이다.

- `horses[].hrDetail` from `API8_2`
- `horses[].jkDetail` from `API12_1`
- `horses[].trDetail` from `API19_1`
- `horses[].jkStats` from `API11_1`
- `horses[].owDetail` from `API14_1`
- `horses[].training` from `API329`

## 원천 필드 → 스키마 필드 매핑 규칙

### 공통 규칙

1. KRA 응답은 `response.body.items.item` 구조를 유지한다.
2. `API214_1`은 `race_info`에 원본 envelope 전체를 보존하고, 말별 최소 필드는 별도 `horses[]` 블록으로 정규화한다.
3. `API72_2`, `API189_1`, `API9_1`은 반드시 대상 `rcNo`와 일치하는 row만 사용한다.
4. 말 상세 계열은 `hrNo`, `jkNo`, `trNo`, `owNo`로 조인한다.
5. `API329` 조교 현황은 현재 구현 제약상 `hrName` 매칭을 사용하고 unmatched를 로그로 남긴다.
6. 키 이름은 저장 시 `snake_case`로 변환하되, `race_info` 원본 envelope 안의 `camelCase`는 보존한다.

### 파싱 구현 기준

- `KRAResponseAdapter.extract_race_metadata()`는 `response.body.items.item`이 list/singleton 어느 형태든 받아 `race_date`, `race_no`, `meet`를 추출한다.
- `race_date`는 숫자/문자 혼합 입력을 모두 `YYYYMMDD` 문자열로 정규화한다.
- `race_no`는 문자열 `"3"` 과 숫자 `3` 을 동일한 경주번호로 취급한다.
- `meet`는 `1/2/3`뿐 아니라 `서울`, `제주`, `부경`, `부산경남` alias를 각각 `1/2/3`으로 정규화한다.
- `KRAResponseAdapter.select_matching_race_item(s)`는 위 정규화 규칙으로 `API72_2`, `API189_1`, `API9_1` row를 대상 경주에 안정적으로 매칭한다.

### 핵심 매핑

| 원천 API | 원천 필드 | 스키마 경로 | 규칙 |
| --- | --- | --- | --- |
| `API214_1` | `rcDate` | `race_date` | 모든 row에서 동일해야 하며 `YYYYMMDD` 문자열로 고정 |
| `API214_1` | `rcNo` | `race_no` | 정수 경주번호 |
| `API214_1` | `chulNo` | `horses[].chul_no` | 출전번호 기준으로 말 배열 정렬 |
| `API214_1` | `hrNo`, `hrName` | `horses[].hr_no`, `horses[].hr_name` | 말 식별자/이름 |
| `API214_1` | `jkNo`, `jkName` | `horses[].jk_no`, `horses[].jk_name` | 기수 상세 조인 기준 |
| `API214_1` | `trNo`, `trName` | `horses[].tr_no`, `horses[].tr_name` | 조교사 상세 조인 기준 |
| `API214_1` | `owNo`, `owName` | `horses[].ow_no`, `horses[].ow_name` | 마주 상세 조인 기준 |
| `API214_1` | `wgBudam`, `wgBudamBigo`, `wgHr` | `horses[].wg_budam`, `horses[].wg_budam_bigo`, `horses[].wg_hr` | 숫자/원문 문자열 유지 |
| `API214_1` | `winOdds`, `plcOdds` | `horses[].win_odds`, `horses[].plc_odds` | `winOdds == 0`은 저장하되 모델 입력에서는 제외마 처리 |
| `API72_2` | `rank`, `budam`, `rcDist`, `ageCond` | `race_plan.*` | `rcNo` 일치 row만 채택 |
| `API189_1` | `weather`, `track`, `waterPercent` | `track.*` | `track.track`은 주로 상태 원문 |
| `API9_1` | row 전체 | `cancelled_horses[]` | `rcNo` 일치 row 전체를 snake_case 저장 |
| `API8_2` | row 전체 | `horses[].hrDetail` | `hrNo` 조인 |
| `API12_1` | row 전체 | `horses[].jkDetail` | `jkNo` 조인 |
| `API19_1` | row 전체 | `horses[].trDetail` | `trNo` 조인 |
| `API11_1` | row 전체 | `horses[].jkStats` | `jkNo` 조인, `jkDetail`와 병합 금지 |
| `API14_1` | row 전체 | `horses[].owDetail` | `owNo` 조인 |
| `API329` | row 전체 | `horses[].training` | 현재는 `hrName` 매칭 |

## 누수 방지 규칙

- `ord`, `rcTime`, `diffUnit`, `rankRise`, `top3`, 배당금, 결과/착순 관련 필드는 입력 스키마에서 금지한다.
- 구간통과 필드(`sj*`, `bu*`, `se*`의 `Ord/AccTime/GTime`)는 금지한다.
- 원천 `rank`는 결과 순위가 아니라 경주 등급/등급 문자열이라 저장 가능하지만, 모델 입력 변환 단계에서는 `class_rank`로 rename 해서 사후결과 필드와 이름 충돌을 제거한다.

## 구현 기준선

- 코드 명세: [prerace_source_schema.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prerace_source_schema.py)
- 현재 수집 구현: [race_processing_workflow.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/race_processing_workflow.py)
- 신규 API 배치 결정: [decision-2026-03-15-new-api-data-placement.md](/Users/chsong/Developer/Personal/kra-analysis/docs/knowledge/decision-2026-03-15-new-api-data-placement.md)
