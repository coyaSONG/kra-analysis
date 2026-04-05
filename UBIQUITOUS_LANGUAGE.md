# Ubiquitous Language

## 경주 참여자 (Race Participants)

| Term | Definition | Aliases to avoid |
|------|-----------|-----------------|
| **Horse (말, hr)** | 경주에 출전하는 경주마 | steed, runner |
| **Jockey (기수, jk)** | 경주마를 타고 경주하는 기수 | rider |
| **Trainer (조교사, tr)** | 경주마를 관리하고 훈련하는 조교사 | coach, handler |
| **Sire (부마, fa_hr)** | 경주마의 아비 (수컷 부모) | father, stallion |
| **Dam (모마, mo_hr)** | 경주마의 어미 (암컷 부모) | mother, mare |

## 경주 구조 (Race Structure)

| Term | Definition | Aliases to avoid |
|------|-----------|-----------------|
| **Race (경주)** | 특정 날짜, 경마장, 경주번호로 식별되는 단일 경마 이벤트 | event, match, game |
| **Meet (경마장)** | 경주가 열리는 장소 (1=서울, 2=제주, 3=부산경남) | venue, racecourse, track |
| **Gate Number (출전번호, chul_no)** | 경주마의 출발 게이트 번호 | entry number, post position |
| **Finishing Position (착순, ord)** | 경주 완료 후 결승선 통과 순서 | position, place, rank |
| **Withdrawn Horse (기권마/제외마)** | 경주에서 제외된 말, `win_odds=0`으로 식별 | scratched, DNS |

## 배당 (Betting Pools)

| Term | Definition | Aliases to avoid |
|------|-----------|-----------------|
| **Trifecta (삼복연승, TLA)** | 1-3위를 순서 없이 맞추는 베팅 방식. 이 프로젝트의 핵심 예측 대상 | tri, 삼복승식(순서 있는 TRI와 혼동) |
| **Win Odds (단승 배당률, win_odds)** | 해당 말이 1위할 경우의 배당률 | odds |
| **Place Odds (복승 배당률, plc_odds)** | 해당 말이 1-2위 안에 들 경우의 배당률 | - |
| **WIN (단승식)** | 1위 맞추기 베팅 풀 | - |
| **PLC (연승식)** | 1-2위 안에 드는 말 맞추기 | - |
| **QNL (복승식)** | 1-2위 두 마리를 순서 없이 맞추기 | quinella |
| **EXA (쌍승식)** | 1-2위 두 마리를 순서대로 맞추기 | exacta |
| **TRI (삼쌍승식)** | 1-3위를 순서대로 맞추기 | trifecta straight |
| **Odd Rank (배당 순위)** | 배당률 기준 시장 선호 순위 (낮을수록 인기마) | market rank, favorite rank |

## 데이터 수집 파이프라인 (Data Collection Pipeline)

| Term | Definition | Aliases to avoid |
|------|-----------|-----------------|
| **Collection (수집)** | KRA API에서 경주 기본 데이터를 가져오는 행위 | gathering, fetching |
| **Enrichment (보강)** | 기본 수집 데이터에 말/기수/조교사 상세 정보를 추가하는 행위 | enhancement, augmentation |
| **Basic Data (기본 데이터)** | API214_1에서 수집한 경주 원시 데이터 | raw data |
| **Enriched Data (보강 데이터)** | hrDetail/jkDetail/trDetail이 추가된 경주 데이터 | enhanced data, augmented data |
| **Result Data (결과 데이터)** | 실제 경주 결과 (착순, 확정 배당) | outcome data |
| **Prerace Data (경주 전 데이터)** | 경주 시작 전 시점에 알 수 있는 모든 정보 | pre-race, input data |
| **Snapshot (스냅샷)** | 특정 시점에 고정된 데이터 캡처, 이후 갱신되지 않음 | freeze, point-in-time |

## 데이터 상태 (Data Status)

| Term | Definition | Aliases to avoid |
|------|-----------|-----------------|
| **PENDING** | 수집/보강 대기 중 | waiting |
| **COLLECTED** | 기본 데이터 수집 완료 | fetched |
| **ENRICHED** | 상세 정보 보강 완료 | enhanced |
| **FAILED** | 수집 또는 보강 실패 | error |

## 성과 지표 (Performance Metrics)

| Term | Definition | Aliases to avoid |
|------|-----------|-----------------|
| **Hit (적중)** | 예측이 실제 결과와 일치 | correct, match |
| **Full Hit (완전적중)** | 예측한 3마리 모두 실제 1-3위와 일치 | perfect hit |
| **Partial Hit (부분적중)** | 예측한 3마리 중 일부만 실제 1-3위와 일치 | partial match |
| **Hit Rate (적중률)** | 전체 경주 중 완전적중한 비율 | success rate, accuracy |
| **Set Match Score** | 예측 집합과 실제 결과 집합의 교집합 비율 (0.0-1.0) | overlap score |
| **Coverage** | 전체 경주 중 유효한 예측을 생산한 비율 | prediction rate |
| **Deferred Count** | 모델이 예측을 거부(보류)한 경주 수 | skip count |
| **ROI** | 예측 기반 베팅의 투자 수익률 | return |
| **Leakage (데이터 누출)** | 경주 전 예측에 경주 후 정보가 혼입되는 오류 | look-ahead bias |

## 통계 접미사 (Statistics Suffixes)

| Term | Definition | Aliases to avoid |
|------|-----------|-----------------|
| **_T (통산)** | 전체 경력에 걸친 통산 통계 | career, total, all-time |
| **_Y (올해)** | 당해 연도 통계 | YTD, current year, recent |
| **rcCnt** | 출전 횟수 | starts, races |
| **ord1Cnt** | 1착 횟수 | wins |
| **ord2Cnt** | 2착 횟수 | places |
| **ord3Cnt** | 3착 횟수 | shows |
| **winRate** | 승률 (%) | win percentage |
| **plcRate** | 복승률 (%) — 1-2위 비율 | place rate |
| **qnlRate** | 연승률 (%) — 1-3위 비율 | show rate |

## 작업 관리 (Job Management)

| Term | Definition | Aliases to avoid |
|------|-----------|-----------------|
| **Job** | 비동기로 실행되는 수집/보강/분석 작업 단위 | task, process |
| **CollectionModule** | 수집 관련 작업의 public facade (queries, commands, jobs) | CollectionService (내부 구현) |

## 프롬프트 개선 시스템 (Prompt Improvement)

| Term | Definition | Aliases to avoid |
|------|-----------|-----------------|
| **Evaluation (평가)** | 프롬프트의 예측 성능을 실제 결과와 비교 측정하는 과정 | testing, benchmarking |
| **Recursive Improvement (재귀 개선)** | 평가 결과를 분석하여 프롬프트를 자동으로 개선하는 반복 프로세스 | auto-improvement |
| **Ultrathink** | 저성과 시 활성화되는 Extended Thinking Mode | deep thinking |

## Relationships

- 하나의 **Race**는 특정 날짜, **Meet**, 경주번호의 조합으로 유일하게 식별된다
- 하나의 **Race**에 여러 **Horse**가 출전하며, 각 말은 **Gate Number**를 부여받는다
- 각 **Horse**에는 한 명의 **Jockey**와 한 명의 **Trainer**가 배정된다
- **Enriched Data**는 **Basic Data**에 hrDetail, jkDetail, trDetail **Snapshot**을 추가한 것이다
- **Trifecta** 예측은 **Prerace Data**만을 입력으로 사용해야 한다 (**Leakage** 방지)
- **Withdrawn Horse**는 `win_odds=0`으로 식별하며, 예측에서 반드시 제외해야 한다

## Example dialogue

> **Dev:** "**Enriched Data**에 있는 hrDetail의 winRateY는 최신 정보인가요?"
> **Domain expert:** "아닙니다. hrDetail은 최초 **Enrichment** 시점의 **Snapshot**입니다. 이후 말이 더 뛰어도 갱신되지 않아요."
> **Dev:** "그러면 **Prerace Data**에서 최근 폼을 판단할 때 hrDetail의 올해 통계를 그대로 쓰면 안 되겠네요?"
> **Domain expert:** "맞습니다. 특히 시즌 초반에 수집한 **Snapshot**은 연말 기준으로 보면 많이 오래된 데이터입니다. **Leakage**는 아니지만 정확도 문제가 있죠."
> **Dev:** "**Trifecta** 예측에서 **Odd Rank**를 쓰는 건 괜찮나요?"
> **Domain expert:** "**Prerace Data** 시점의 배당률 기반이면 괜찮습니다. 단, 확정 배당(final_odds)은 경주 후 데이터이므로 **Leakage**에 해당합니다."

## Flagged ambiguities

- **"odds"** 가 단독으로 쓰일 때 **Win Odds**인지 **Place Odds**인지 불명확 — 항상 `win_odds` 또는 `plc_odds`로 명시할 것
- **"삼복연승"과 "삼복승식(TLA)" vs "삼쌍승식(TRI)"** — 삼복연승은 순서 없이(TLA), 삼쌍승식은 순서대로(TRI). 이 프로젝트의 예측 대상은 **순서 없는 삼복연승(TLA)**
- **"enriched"의 이중 의미** — DataStatus.ENRICHED는 "보강 완료" 상태를 나타내지만, hrDetail 내부 데이터는 수집 시점 **Snapshot**으로 최신이 아닐 수 있음. "enriched = 최신"이라는 암묵적 가정 주의
- **"rating" 필드** — 현재 모든 값이 0으로 실질적으로 미사용. 정렬에 사용하면 삽입 순서로 정렬되어 **Leakage** 위험
- **Meet 타입 불일치** — 코드에서 때로 문자열("1"), 때로 정수(1)로 사용됨. 정수로 통일 권장
- **JobType vocabulary 분열** — DTO와 DB 모델 사이에서 작업 타입 명칭이 불일치. `normalize_lifecycle_status()`로 변환 중이나 근본 통일 필요
