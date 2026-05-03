# KRA 경주 라이프사이클 시점 매트릭스 v1

## 목적

이 문서는 KRA 전 경주 top-3 무순서 예측 시스템에서 "각 필드가 실제로 언제 가용한지"를 공통 기준으로 판정하기 위한 시점 매트릭스다. 목표는 다음 3가지다.

- 출전표 확정 시점까지만 허용되는 입력과 확정 후에 생기거나 변동하는 입력을 분리한다.
- 같은 API 안에 사전/사후 필드가 섞여 있어도 필드 단위로 판정한다.
- 자동 수집·재학습·예측 파이프라인이 미래 운영 조건을 위반하지 않도록 예외 규칙을 문서로 고정한다.

기준 증거는 현재 수집/결과 파이프라인과 필드 인벤토리다.

- [race_processing_workflow.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/race_processing_workflow.py)
- [result_collection_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/result_collection_service.py)
- [prerace_source_schema.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prerace_source_schema.py)
- [discovery-2026-04-10-field-inventory.md](/Users/chsong/Developer/Personal/kra-analysis/docs/knowledge/discovery-2026-04-10-field-inventory.md)

## 라이프사이클 단계 정의

| 단계 | 정의 | 운영 해석 |
| --- | --- | --- |
| `L-1 출전표 확정 전` | 경주일/경주번호는 알려졌지만 최종 출전마, 부담중량, 취소마 상태가 아직 고정되지 않은 구간 | 마스터/누적 통계 조회는 가능할 수 있으나, 이 단계 정보만으로 최종 예측 스냅샷을 만들면 안 된다 |
| `L0 출전표 확정 시점` | 공식 출전표가 고정되고 해당 경주의 예측 입력을 얼릴 수 있는 기준 시점 | 최종 성공 판정용 입력은 이 시점 이하에서만 생성해야 한다 |
| `L+1 출전표 확정 후` | 출전표 확정 이후부터 결과 확정 이후까지 전체 | 주로, 취소, 배당, 결과 등 변동/사후 정보가 섞인다. `L0` 스냅샷을 덮어쓰면 안 된다 |

## 판정 기준

1. 필드 단위 판정을 우선한다. 같은 API라도 어떤 필드는 `L0` 허용이고 어떤 필드는 `L+1` 금지일 수 있다.
2. 현재 코드에서 결과 수집 경로에서만 호출되는 원천은 기본적으로 `L+1`로 본다.
3. 값이 `L0`에도 존재할 수 있지만 확정 후 계속 변하는 필드는 "`L0` 스냅샷으로 고정했을 때만 허용"으로 판정한다.
4. 실제 공개 시점이 실측으로 검증되지 않은 필드는 보수적으로 `허용 보류`로 둔다.
5. 파생 피처는 원천 입력 중 가장 늦은 시점을 상속한다. 원천 하나라도 `L+1`이면 파생 피처도 `L+1`이다.

## 시점 매트릭스

판정 기호:

- `Y`: 해당 단계에서 가용
- `N`: 해당 단계에서 가용하지 않음
- `?`: 문서/샘플만으로 확정 불가, 실측 검증 필요

| 원천/필드군 | 확정 전 | 확정 시점 | 확정 후 | 판정 | 예외/메모 |
| --- | --- | --- | --- | --- | --- |
| `API214_1` 핵심 출전표 필드: `rcDate`, `rcNo`, `meet`, `chulNo`, `hrNo`, `hrName`, `jkNo`, `jkName`, `trNo`, `trName`, `owNo`, `owName`, `age`, `sex`, `name`, `rank`, `rating`, `wgBudam`, `wgBudamBigo`, `wgHr`, `ilsu`, `hrTool` | N | Y | Y | `L0 허용` | 최종 성공 판정에서는 `L0`에 수집한 스냅샷만 사용한다. `rank`는 결과 순위가 아니라 등급 문자열이므로 입력 변환 시 `class_rank`로 rename 한다 |
| `API72_2` 경주 계획 필드: `rank`, `budam`, `rcDist`, `ageCond`, `sexCond`, `schStTime`, `chaksun1..5` | Y | Y | Y | `L0 허용` | `schStTime`은 확정 후 변경될 수 있으므로 `L0` 값만 사용한다 |
| `API8_2` 말 상세, `API12_1` 기수 상세, `API19_1` 조교사 상세, `API11_1` 기수 누적 통계, `API14_1` 마주 누적 통계 | Y | Y | Y | `L0 허용` | 과거 snapshot 복원 시에는 결과 확정 후 재조회하지 말고, 당시 저장본만 사용한다 |
| `API329` 조교 현황: `horses[].training` | Y | Y | Y | `L0 조건부 허용` | 현재 구현은 `hrnm` 이름 매칭이라 동명이마 충돌 위험이 있다. `L0` 이전 수집본만 허용하고, 매칭 실패는 빈 블록으로 둔다 |
| `API189_1` 주로/날씨: `weather`, `track`, `waterPercent`, `temperature`, `humidity`, `windDirection`, `windSpeed` | ? | Y | Y | `L0 snapshot 허용` | 같은 날에도 변동 가능하므로 `L0`에 캡처한 값만 사용한다. `L0` 이전 row 부재 시 null 허용 |
| `API9_1` 취소마: `cancelled_horses[]` | ? | Y | Y | `L0 snapshot 허용` | 확정 후 추가 취소가 생길 수 있다. 예측 입력은 `L0` 상태로 얼리고, 이후 취소는 운영 로그/평가 제외 사유로만 반영한다 |
| `API214_1` 시장 필드: `winOdds`, `plcOdds` | ? | ? | Y | `허용 보류` | 현재 저장소는 활성 출전마 판정에 `winOdds > 0`을 사용하지만, "출전표 확정 시점에 이미 공개되는 값"인지 실측 검증이 끝나지 않았다. 성공 판정용 feature로는 사용 보류가 안전하다 |
| `API160_1`, `API301`, 내부 `race_odds` | N | N | Y | `금지` | 현재 구현도 결과 수집 직후 또는 별도 odds 수집에서만 저장한다 |
| `API214_1` 결과 필드: `ord`, `ordBigo`, `rankRise`, `diffUnit`, `rcTime` | N | N | Y | `금지` | [result_collection_service.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/result_collection_service.py) 가 같은 `API214_1`로 결과를 읽는다 |
| `API214_1` 구간 순위/기록: `sj*`, `bu*`, `se*` 의 `Ord`, `AccTime`, `GTime` 패턴 | N | N | Y | `금지` | [leakage_checks.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/evaluation/leakage_checks.py) 의 사후 필드 차단 대상 |
| 내부 `result_data` 와 그 파생 top-3 라벨 | N | N | Y | `라벨 전용` | 학습/평가 정답으로만 사용하고 feature 입력에는 절대 넣지 않는다 |

## 스키마 경로 기준 요약

| 스키마 경로 | 시점 판정 | 정책 |
| --- | --- | --- |
| `race_date`, `race_no`, `meet`, `race_number` | `L0 허용` | 경주 식별자 |
| `race_info.response.body.items.item[]` | `혼합` | 원본 보존은 허용하되, 모델 입력 변환 시 `L+1` 금지 필드를 제거해야 한다 |
| `race_plan.*` | `L0 허용` | 계획/조건 정보 |
| `track.*` | `L0 snapshot 허용` | 캡처 시각이 cutoff 이하여야 함 |
| `cancelled_horses[]` | `L0 snapshot 허용` | cutoff 이후 변경분은 기존 입력을 덮어쓰지 말 것 |
| `horses[].{chul_no, hr_no, hr_name, jk_no, jk_name, tr_no, tr_name, ow_no, ow_name, age, sex, name, rank, rating, wg_budam, wg_budam_bigo, wg_hr, ilsu, hr_tool}` | `L0 허용` | 출전표 핵심 정보 |
| `horses[].win_odds`, `horses[].plc_odds` | `허용 보류` | cutoff 실측 검증 전에는 성공 판정 feature에서 제외 권고 |
| `horses[].hrDetail`, `horses[].jkDetail`, `horses[].trDetail`, `horses[].jkStats`, `horses[].owDetail`, `horses[].training` | `L0 조건부 허용` | 조회 시각이 cutoff 이하여야 하며 soft-fail 허용 |
| `collected_at`, `status`, `failed_horses[]` | `내부 메타데이터` | 시점 감사용으로만 사용 |

## 예외 규칙

### 1. `API214_1` 혼합 응답 예외

- 이 엔드포인트는 출전표 핵심 정보와 사후 결과 필드를 함께 노출할 수 있다.
- 따라서 `API214_1`은 "API 전체 허용/금지"가 아니라 필드군 단위로 분리 판정해야 한다.
- 특히 `result_collection_service.collect_result()` 가 같은 엔드포인트에서 `ord`를 읽으므로, `API214_1` raw 원본을 모델 입력에 그대로 넣으면 누수 위험이 즉시 발생한다.

### 2. `winOdds` / `plcOdds` 예외

- 현재 저장소는 활성 출전마 판정과 일부 연구 코드에서 `winOdds`를 사용한다.
- 그러나 필드 인벤토리 문서 기준으로 이 값이 정확히 언제 공개되는지 아직 실측되지 않았다.
- 따라서 운영 성공 판정에서는 다음처럼 분리한다.
  - `winOdds == 0`를 과거 데이터 정리용 scratch 보조 신호로 쓰는 것은 허용 가능
  - `winOdds`, `plcOdds` 수치 자체를 `L0` 준수 feature로 주장하는 것은 보류

### 3. 변동 필드 예외

- `track.*`, `cancelled_horses[]`, `training`, `schStTime`은 `L0`에도 존재할 수 있지만 확정 후 갱신될 수 있다.
- 이 필드들은 "해당 경주의 예측 cutoff 이전에 수집한 첫 정상 snapshot"을 기준값으로 고정해야 한다.
- cutoff 이후 재수집 값으로 기존 snapshot을 덮어쓰면 `L+1` 누수가 된다.

### 4. soft-fail 예외

- `hrDetail`, `jkDetail`, `trDetail`, `jkStats`, `owDetail`, `training`은 성능 고도화용 soft feature다.
- 일부 누락 때문에 경주 전체 예측을 포기하면 "모든 KRA 경주 예측" 제약을 위반하므로, 값이 없으면 빈 dict/null로 유지하고 경주는 계속 예측한다.

## 구현상 주의

- 현재 [race_processing_workflow.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/services/race_processing_workflow.py) 의 `save_collection()`은 동일 `race_id` 재수집 시 `basic_data`를 덮어쓴다.
- 따라서 이 매트릭스를 운영에서 지키려면 "`L0` cutoff 이전 snapshot은 불변 보관" 규칙이 별도로 필요하다.
- 문서상 시점 판정만 맞고 저장 전략이 불변이 아니면, 사후 재수집으로 `basic_data`가 오염될 수 있다.

## 결론

- 최종 예측 입력의 기준 시점은 `L0 출전표 확정 시점`이다.
- `API214_1`은 필드 혼합 원천이므로 핵심 출전표 필드만 허용하고 결과/구간 필드는 항상 제거해야 한다.
- `API189_1`, `API9_1`, `API329`, `winOdds/plcOdds` 같은 변동 필드는 cutoff 스냅샷 고정 또는 허용 보류 규칙이 필요하다.
- 이 매트릭스는 이후 홀드아웃 생성, 재학습, 운영 snapshot immutability 설계의 기준 문서로 사용한다.
