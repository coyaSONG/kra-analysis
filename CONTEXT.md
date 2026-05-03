# KRA Analysis

한국마사회(KRA) 경주 데이터를 수집·저장·재사용 가능한 구조로 정리하고, 그 데이터로 **삼복연승(top-3 무순서) 예측의 holdout `set_match`를 0.70 이상으로 끌어올리는** brownfield 프로젝트. 운영 코어는 `apps/api`의 FastAPI 서버이며, 학습/실험은 별도 `autoresearch-pilot` worktree에서 수행한다.

## Language

### Race & betting

**Race**:
KRA 공식 경주 1건. 영구 식별자는 `race_id` (UUID); 자연키는 `(race_date, meet, race_number)`.
_Avoid_: 시합, 경기

**Meet**:
경마장 코드. 1=서울, 2=제주, 3=부경(부산경남).

**race_date / race_number**:
정규화된 컬럼명. `YYYYMMDD` 정수 문자열 + 1~12 정수.
_Avoid_: race_no, date (legacy ORM 호환 프로퍼티에서만 사용)

**삼복연승 (Sambok-yeonseung)**:
1~3위 마를 무순서로 맞추는 베팅 종목. 이 시스템의 핵심 예측 타겟. 배당 풀 코드 `TLA`.
_Avoid_: top-3 prediction (영문은 OK이지만 베팅 맥락에서는 삼복연승)

**Pool**:
배당 종류 코드. WIN(단승), PLC(연승), QNL(복승), EXA(쌍승), QPL(복연승), TLA(삼복승), TRI(삼쌍승), XLA(쌍복승).

**Horse / horse-in-race**:
경주 출전마. 1마리는 글로벌 `hr_no`(마번)을 갖고, *특정 경주 안에서는* `chul_no`(출전번호, 게이트)를 갖는다.

**chul_no / hr_no / jk_no / tr_no / ow_no**:
출전번호 / 마번 / 기수번호 / 조교사번호 / 마주번호. 모두 KRA 공식 식별자.

**win_odds / plc_odds**:
단승 / 연승 배당률. 양수가 정상. `win_odds == 0`은 출전취소(scratched) 신호이며, 보류(L0 timing 미검증) 상태로 모델 feature에 포함하지 않는다.

**scratched horse**:
이번 경주에 실제로 출전 안 한 말. 신호 2가지: `cancelled_horses[]` 등재 또는 `win_odds == 0`. 데이터 정제 단계에서 입력에서 제외.
_Avoid_: cancelled (한쪽 신호만), 기권 (애매)

**excluded horse**:
KRA는 출전시켰지만 우리 코드 정책으로 모델 입력에서 뺀 말. 보통 historical stats 부족이 사유.
_Avoid_: scratched (KRA의 출전 거부와 혼동)

**hrDetail / jkDetail / trDetail / jkStats / owDetail**:
말/기수/조교사/기수누적/마주의 상세 정보 블록. KRA의 별도 API에서 조회. **1회 수집 후 갱신 안 됨 — 동결 스냅샷**이라는 점을 기억해야 leakage 분석이 정확하다.

**rating**:
말의 능력 점수(KRA 부여). 정수.

**rank / class_rank**:
말의 등급(국1~국6, 신마). 저장은 `rank`, 모델 입력 변환 시 `class_rank`로 rename — 결과 순위(`ord`)와 혼동 방지.

**wgBudam / wgHr**:
부담중량 (핸디캡 kg) / 마체중 (kg). 둘은 별개. wg_budam은 경주별 부과, wg_hr는 마의 컨디션.

### Data lifecycle stages

**collection**:
KRA API에서 raw 경주 데이터를 받아오는 단계. 이 단계에서 hrDetail/jkDetail/trDetail까지 함께 조회되어 **`basic_data` 안에 합쳐 저장** — 설계 의도대로다.
_Avoid_: enrichment와 혼동. KRA detail 블록은 collection 산출물이지 enrichment 산출물이 아니다.

**preprocessing**:
collection 직후 정규화 (camelCase → snake_case, 필드 매핑). 별도 컬럼 없이 `basic_data` 안에 머문다.

**enrichment**:
basic_data 위에 derived feature(past_stats, weather_impact 등)를 더하는 후속 단계. **현재 의도적 보류** — A/B 효과 검증 후 활성화 예정.

**prerace data**:
경주 결과를 알기 전 사용 가능한 정보 일반. 시점/저장 단계에 따라 변형 — "L0 시점의 prerace 스냅샷", "canonical-v2로 변환된 prerace 입력" 같이 형용사로 수식한다.
_Avoid_: prerace를 변형별로 별도 용어로 쪼개기.

**postrace data**:
경주 완료 후에만 알 수 있는 정보. `ord`, `ordBigo`, `rcTime`, 구간 기록(sj*/bu*/se*), 확정 배당. 모델 입력에 *반드시 차단*.

**basic_data** (column on `races`):
DB에 저장되는 기본 수집 산출물. raw 응답 + 정규화 + KRA detail 블록 포함. 활성 컬럼.

**raw_data** (column on `races`):
shadow audit 컬럼. 차단 필드까지 포함한 원본 보존본. 새 prerace 파이프라인 도입 후 정책 분할 저장에서 활성화.

**enriched_data** (column on `races`):
후속 보강 산출물용. **현재 NULL이 정상**. enrichment 단계 보류로 인해 채워지지 않음.

**canonical-v2 payload**:
모델 추론에 입력되는 정규화 포맷. 28개 feature (PR #7 기준; autoresearch-pilot은 30 features). enriched 데이터에서 메모리상 on-the-fly 변환되며 **DB에 저장되지 않는다**.
_Avoid_: enriched_data 컬럼과 혼동.

**result_data** (column on `races`):
경주 결과 (top3 마번 배열). 학습/평가 라벨로만 사용, feature 입력 금지.

### Time & cutoff vocabulary

**L-1 / L0 / L0 snapshot / L+1 (availability stage)**:
필드별 가용 시점. L-1=출전표 확정 전, L0=확정 시점, L0 snapshot=L0에 캡처한 immutable 값, L+1=경주 후. **L+1은 입력 금지.**

**scheduled_start_at**:
`race_date + race_plan.sch_st_time`로 계산된 공식 출발 예정 시각 (Asia/Seoul).

**operational_cutoff_at**:
`scheduled_start_at - 10분`. 운영상 예측 입력을 잠그는 기준 시각.

**entry_finalized_at**:
선택된 prerace 스냅샷 리비전이 사용 가능해진 시각. `operational_cutoff_at` 이하여야 한다. holdout 재현·평가의 anchor.

**replay_status**:
holdout 경주의 재현 가능성. `strict` / `degraded` / `partial_snapshot` / `unrecoverable_post_cutoff_reissue`.

### Architecture concepts

**Job**:
DB row로 영구 추적되는 비동기 작업 단위. 외부 API(`/api/v2/jobs`)로 조회/취소 가능. 종류는 `job_kind_v2`, 상태는 `lifecycle_state_v2`.
_Avoid_: type / status enum (legacy 컬럼명, cutover 후 폐기 예정).

**DispatchAction**:
Job이 실행하는 구체 명령. 값: `COLLECT_RACE`, `PREPROCESS_RACE`, `ENRICH_RACE`, `ANALYSIS`, `PREDICTION`, `IMPROVEMENT`, `BATCH_COLLECT`, `FULL_PIPELINE`. Command Pattern의 Command에 해당.

**Task** (구현 세부):
Job을 실행하는 in-process `asyncio.Task`. 현재 durable queue 미도입이라 서버 재시작 시 사라진다. CONTEXT 어휘 아님 — Job의 *실행 메커니즘*으로만 언급.

**KRA API source**:
KRA 공공 데이터 포털 endpoint. 코드: `API214_1`(출전표), `API72_2`(경주계획), `API189_1`(주로/날씨), `API9_1`(취소마), `API8_2`(말 상세), `API12_1`(기수 상세), `API19_1`(조교사 상세), `API11_1`(기수 누적), `API14_1`(마주), `API329`(조교현황), `API160_1`(라이브 배당), `API301`(확정 배당), `API299`(결과).

**source_field_tag**:
필드별 가용성 메타데이터. 값: `pre_entry_allowed`, `hold`, `snapshot_only`, `post_entry_only`. 새 prerace storage policy의 분류 기준.

**join_timing_audit**:
`entry_finalized_at` 이후 추가/변경된 필드를 명시 추적하는 가드. L0 cutoff의 코드 enforcement.

**migration**:
DB 스키마 변경 SQL 파일 (`apps/api/migrations/*.sql`). **Schema source of truth** — ORM `create_all()`은 test/dev 부트스트랩 전용.

**migration manifest**:
활성 마이그레이션 목록 (`ACTIVE_MIGRATIONS`). startup 검증으로 manifest와 파일 시스템 정합성 확인.

**autoresearch-pilot worktree**:
`~/Developer/Personal/kra-analysis-autoresearch-pilot/`. **영구 분리된** 학습/실험 sandbox. main repo는 추론 인프라만 보유, 학습 데이터(57M+)는 여기에만.

**champion model**:
autoresearch에서 선정된 leakage-free 예측 모델 (`champion_clean.joblib`). main은 lazy-load, 부재 시 `/predict` 503.

**iter N**:
champion 모델의 버전 식별자 (예: iter 56). autoresearch 실험 keep 시점.

**Principal / UsageEvent**:
요청자 식별 단위(`principal_id`)와 append-only 사용 이벤트(`usage_events` 테이블). 인증·인가·쿼터의 기준.

### Evaluation & experimentation

**holdout**:
최종 성능 평가용 고정 테스트 세트. 출전표 확정 시점 스냅샷으로 얼림. 데이터 누수 방지.

**strict / degraded** (holdout subset):
holdout 경주의 품질 분류. strict는 운영 인증 기준, degraded는 회귀 감시용 참고.

**set_match**:
예측 3마리 집합과 실제 top3 집합의 정확 일치 비율 (0.0~1.0). **이 시스템의 north star metric** (목표: holdout set_match ≥ 0.70 — `docs/adr/0001-target-metric-set-match`).

**correct_count / accuracy_score**:
예측 3마리 중 실제 top3에 포함된 수 (0~3) / 그 비율 (0~1). set_match보다 부드러운 부분 적중 메트릭.

**autoresearch**:
프롬프트/모델을 자동으로 평가·분석·개선하는 실험 루프. autoresearch-pilot worktree에서 실행.

**recursive prompt improvement (v5)**:
프롬프트를 재귀적으로 개선하는 시스템. v5 활성, v1~v4는 superseded.

**jury ensemble / ranked voting**:
여러 프롬프트 결과를 투표/통합하는 기법. NDCG@3, ranked voting 등 사용.

**walk-forward / sliding window / embargo / purged CV**:
시계열 데이터 누수 방지를 위한 교차검증 변형들.

**leakage / data leakage**:
모델이 미래 정보를 부정 접근하는 현상. look-ahead, target, LLM memorization 등 유형. 평가 단계에서 명시적으로 검증.

## Relationships

- A **Race** has many **horses-in-race**; each carries 1 `chul_no` (in-race) and 1 `hr_no` (global).
- Each **horse-in-race** has 1 **jockey** and 1 **trainer**.
- A **Race** can produce 0..N **Predictions** (one per prompt version × run).
- A **Prediction** is compared against the **result_data** of its Race for `correct_count` and `set_match`.
- A **Job** runs 0 or 1 **DispatchAction** (e.g., `COLLECT_RACE`, `FULL_PIPELINE`) and may track 1 implementation-level **Task** (asyncio).
- **basic_data** is filled by `collection`. **enriched_data** would be filled by `enrichment` (currently NULL by design).
- A **prerace snapshot** at L0 is the immutable input for both holdout replay and live operation.
- The **canonical-v2 payload** is derived on-demand from enriched data; it is never stored.
- The **champion model** lives in autoresearch-pilot worktree; main repo lazy-loads it for `/predict`.
- A **Race** carries three independent state machines: `collection_status`, `enrichment_status`, `result_status`.

## Currently deferred (read this before assuming)

운영상 의도적으로 미루고 있는 것들 — 신규 기여자가 코드를 읽다 "왜 안 돌아가지?"라고 오해하지 않도록 명시:

- **enrichment 파이프라인**: A/B 효과 검증 후 활성화 (`docs/adr/0002-enriched-data-on-hold`; `docs/knowledge/decision-2026-03-15-skip-pipeline-overhaul`). `enriched_data` 컬럼이 NULL인 게 정상.
- **live 환경 prediction**: 라이브 Supabase에 historical stats 부재로 모든 출주마가 `excluded` 처리됨. **offline holdout 우선**이라 후순위 (`gotcha-2026-05-03-live-enrichment-data-starvation`).
- **autoresearch-pilot 통합**: 영구 분리. main으로 합치지 않음.
- **새 prerace storage pipeline**: rule engine 완성됨, integration 진행 중 (별도 작업).
- **Job 어휘 v2 cutover**: 현재 dual-write, read cutover 대기 (`docs/adr/0004-job-dispatchaction-task-model`, `docs/adr/0005-v2-suffix-policy`).
- **Alembic 도입**: 장기 계획. 단기는 자체 manifest 검증 강화 (`docs/adr/0003-migration-source-of-truth`).
