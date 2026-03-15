# KRA Autoresearch 설계 스펙

karpathy/autoresearch 패턴을 KRA 경마 예측 시스템에 접합하는 설계 문서.

## 배경

### autoresearch란
- Andrej Karpathy가 만든 자율 AI 연구 시스템
- AI 에이전트가 `train.py` 하나만 수정하면서 반복 실험
- 파일 3개: `prepare.py`(고정), `train.py`(에이전트 수정), `program.md`(사람 수정)
- 단일 지표(`val_bpb`)로 개선 여부 판단, 개선 시 keep / 악화 시 revert

### 왜 접합하는가
- 기존 v5 재귀 개선 시스템(4000줄+, 10개 모듈)은 과도하게 복잡하며 아직 실전 검증 안 됨
- autoresearch의 극단적 단순함(파일 3개)을 그대로 카피하는 것이 더 신뢰도 높음
- v5는 참고 아이디어 저장소로 활용

## 파일 구조

```
packages/scripts/autoresearch/
├── prepare.py          # 고정 — 데이터 로딩, 평가 하네스, 스코어러
├── train.py            # 에이전트가 수정하는 유일한 파일
├── program.md          # 에이전트 지시서 (사람이 수정)
├── experiments.jsonl   # revert된 실험 기록
└── snapshots/          # prepare.py가 생성하는 고정 데이터 팩
    ├── mini_val.json   # 20경주 race_data 배열 (정답 미포함)
    ├── holdout.json    # 50경주 race_data 배열 (정답 미포함)
    └── answer_key.json # 정답 분리 저장 (leakage 방지)
```

### answer_key.json 형식

```json
{
  "meta": {"created_at": "2026-03-15", "sha256": "..."},
  "mini_val": {
    "race_id_1": [1, 5, 3],
    "race_id_2": [7, 2, 11]
  },
  "holdout": {
    "race_id_3": [4, 8, 1]
  }
}
```

- 키: `race_id` 문자열
- 값: `[1위chulNo, 2위chulNo, 3위chulNo]` (db_client.get_race_result() 반환값과 동일)
- train.py는 이 파일에 접근 불가 (import guard + convention)

## 1. prepare.py (수정 금지)

### 역할
- Supabase DB에서 2025년 경주 데이터를 읽어 **고정 snapshot** 생성
- `train.py`의 `predict()` 함수를 호출하여 평가 실행
- 결과 스코어를 한 줄로 출력

### 데이터 팩 생성 규칙

```python
# 1. 결과가 확정된 경주만 선택 (Codex 리뷰 반영)
WHERE collection_status = 'collected'
  AND result_status = 'collected'

# 2. 시간순 정렬 후 temporal split (walk-forward 방식)
#    뒤에서 50경주 → holdout (가장 최신, 과적합 검증)
#    holdout 직전 20경주 → mini_val (반복 평가)
#    즉: [...오래된 데이터...][mini_val 20][holdout 50]
#    이렇게 해야 mini_val과 holdout이 유사한 시기의 데이터를 사용하여
#    현실적인 평가가 됨 (오래된 데이터로 평가하는 문제 방지)

# 3. snapshot 파일로 저장 (매 실험마다 DB 재조회 안 함)

# 4. enriched 형식 적용
#    data_adapter.py의 snake→camelCase 변환 재사용
#    feature_engineering.py의 compute_race_features() 재사용
#    → odds_rank, rating_rank, win_rates 등 computed_features 포함
#    필수 필드: chulNo, hrName, age, sex, wgBudam, wgHr, winOdds,
#              ilsu, rcDist, hrDetail, jkDetail, trDetail 등
#    (전체 필드 목록은 evaluate_prompt_v3.py의 load_race_data() 참조)

# 5. leakage 방지: snapshot 저장 전 forbidden fields 제거
#    rank, ord, rcTime, result, resultTime, finish_position,
#    top3, actual_result, dividend, payout
#    정답(actual top-3)은 별도 answer_key에 분리 저장
#    answer_key 형식: {"race_id": [1위chulNo, 2위chulNo, 3위chulNo], ...}
#    (db_client.get_race_result() 반환값과 동일한 list[int] 형식)
```

### 평가 실행

```python
def evaluate(mode="mini_val"):
    """train.py를 import하여 predict() 호출, 스코어 계산"""
    races, answer_key = load_snapshot(mode)  # mini_val 또는 holdout

    results = []
    for race in races:
        try:
            # race 단위 timeout은 _call_llm 내부 subprocess.timeout으로 강제
            prediction = train.predict(race, call_llm=_call_llm)
            score = compute_score(prediction, answer_key[race["race_id"]])
        except Exception:
            score = {"json_ok": False, "deferred": False, "set_match": 0.0}
        results.append(score)

    # 한 줄 출력
    print_score_line(results)
```

### 출력 형식

```
set_match=0.450 | avg_correct=1.35 | json_ok=95% | coverage=85% | latency=45s
```

### 지표 정의

| 지표 | 계산 | 역할 |
|------|------|------|
| `set_match` | `len(predicted[:3] ∩ actual[:3]) / 3` 평균 (기존 metrics.py의 `set_match_rate`에 대응) | **주 지표** (높을수록 좋음) |
| `avg_correct` | 경주당 맞춘 말 수 평균 (0~3) | 보조 지표 |
| `json_ok` | JSON 파싱 성공률 | Hard gate >= 90% |
| `coverage` | (전체 경주 - defer 건수) / 전체 경주 수 (**prepare.py 자체 계산**, metrics.py의 coverage와 분모 정의가 다르므로 재사용하지 않음) | Hard gate >= 80% |
| `latency` | 전체 소요 시간 | 참고용 |

### Hard Gate (하나라도 실패 시 실험 자동 fail)
- `json_ok >= 90%`
- `coverage >= 80%` (confidence < 0.3인 예측은 defer 처리)
- leakage 없음 (forbidden fields 미참조)
- experiment wall-clock <= 30분 (20경주 기준)
- race 단위 timeout <= 120초

### 재사용하는 기존 코드
- `packages/scripts/shared/db_client.py` — DB 접근 (단, `find_races()`에 `result_status` 필터 추가 필요 — 새 메서드 `find_races_with_results()` 추가)
- `packages/scripts/shared/data_adapter.py` — enriched 형식 변환
- `packages/scripts/evaluation/metrics.py` — `_set_match_score()` 로직 재사용 (prepare.py 내에서 동일 로직 직접 구현: `len(set(pred[:3]) & set(actual[:3])) / 3`). coverage는 metrics.py와 분모 정의가 다르므로 prepare.py에서 자체 계산
- `packages/scripts/evaluation/leakage_checks.py` — forbidden fields 검사
- `packages/scripts/feature_engineering.py` — computed_features 생성

### 데이터 변환 파이프라인 (evaluate_prompt_v3.py에서 추출)

`data_adapter.py`는 중첩 API 형식(`{response: {body: {items: {item: [...]}}}}`)을 반환한다.
`prepare.py`는 이 중첩 구조에서 flat 형식으로 변환하는 글루 로직을 포함해야 한다:

```python
# evaluate_prompt_v3.py의 load_race_data()에서 추출할 로직:
# 1. 중첩 response에서 items 추출
# 2. winOdds == 0인 말 필터링 (기권/제외마)
# 3. 말별 필드 선택 및 정리
# 4. raceInfo dict 구성
# 5. compute_race_features() 적용
#
# 주의: evaluate_prompt_v3.py의 로더는 wgHr, ilsu 등을 말 단위로
# 직접 넣지 않는 경우가 있다. 반면 feature_engineering.py는 이 필드가
# 있어야 burden_ratio, rest_days 등 추가 피처를 계산한다.
# prepare.py는 raw item에서 wgHr, ilsu, wgBudam, age, sex 등을
# 말 단위로 명시적으로 포함해야 computed_features가 완전해진다.
# (evaluate_prompt_v3.py의 로더를 그대로 복사하지 말고, raw item의
#  전체 필드를 보존한 뒤 forbidden fields만 제거하는 방식이 안전)
```

## 2. train.py (에이전트만 수정)

### 핵심 원칙: 좁은 프롬프트 모듈

Codex 리뷰에서 지적된 label leakage 위험을 방지하기 위해, `train.py`는 **자유 Python이 아닌 좁은 프롬프트 모듈**로 제한한다.

- DB 접근 코드 금지 (import db_client 금지)
- 파일 I/O 금지 (snapshot 파일 직접 읽기 금지)
- `prepare.py`가 전달하는 `race_data` dict만 사용 가능

### 파일 구조

```python
"""KRA 삼복연승 예측 전략 — 에이전트가 수정하는 유일한 파일"""

# ============================================================
# 1. 프롬프트 템플릿 (~80%)
# ============================================================

SYSTEM_PROMPT = """
당신은 한국 경마 분석 전문가입니다.
주어진 경주 데이터를 분석하여 1~3위 말을 예측하세요.
...
"""

USER_PROMPT_TEMPLATE = """
## 경주 정보
{race_info}

## 출전마 데이터
{horse_data}

## 분석 요청
위 데이터를 기반으로 1~3위를 예측하세요.
반드시 아래 JSON 형식으로 응답하세요:
{output_schema}
"""

# ============================================================
# 2. 전략 함수 (~20%)
# ============================================================

def select_features(race_data: dict) -> dict:
    """race_data에서 프롬프트에 포함할 필드 선택"""
    ...

def format_race_info(features: dict) -> str:
    """경주 정보를 프롬프트용 텍스트로 포맷"""
    ...

def format_horse_data(horses: list[dict]) -> str:
    """말 데이터를 프롬프트용 텍스트로 포맷"""
    ...

def build_prompt(features: dict) -> tuple[str, str]:
    """SYSTEM_PROMPT와 USER_PROMPT_TEMPLATE를 조립하여 (system, user) 반환"""
    race_info = format_race_info(features)
    horse_data = format_horse_data(features["horses"])
    user = USER_PROMPT_TEMPLATE.format(
        race_info=race_info,
        horse_data=horse_data,
        output_schema=json.dumps(OUTPUT_SCHEMA, ensure_ascii=False),
    )
    return SYSTEM_PROMPT, user

def parse_response(llm_output: str) -> dict:
    """LLM 응답을 파싱하여 표준 형식으로 변환"""
    ...

# ============================================================
# 3. 엔트리포인트 (prepare.py가 호출)
# ============================================================

OUTPUT_SCHEMA = {
    "predicted": [0, 0, 0],       # 1~3위 예측 chulNo
    "confidence": 0.0,            # 0.0 ~ 1.0
    "reasoning": ""               # 예측 근거 (1~2문장)
}

def predict(race_data: dict, call_llm) -> dict:
    """
    prepare.py가 호출하는 유일한 인터페이스.

    Args:
        race_data: enriched 형식의 경주 데이터
                   (computed_features 포함, 정답 미포함)
        call_llm: prepare.py가 주입하는 LLM 호출 콜백
                  시그니처: (system: str, user: str) -> str

    Returns:
        {"predicted": [1, 5, 3], "confidence": 0.72, "reasoning": "..."}
    """
    features = select_features(race_data)
    system, user = build_prompt(features)
    response = call_llm(system, user)
    return parse_response(response)
```

### 출력 계약 (고정, 수정 불가)

```json
{
    "predicted": [1, 5, 3],
    "confidence": 0.72,
    "reasoning": "1번마 최근 3연승 + 5번마 거리 적성 우수"
}
```

- `predicted`: 정확히 3개의 chulNo (int)
- `confidence`: 0.0 ~ 1.0 (float)
- `reasoning`: 예측 근거 문자열
- **v1.7의 복잡한 중첩 스키마(`predictions[]`, `trifecta_picks`)는 사용하지 않음**

### LLM 호출 방식

`predict()` 함수는 두 번째 인자로 `call_llm` 콜백을 받는다. `prepare.py`가 이를 주입한다.

```python
# prepare.py 측 (고정):
from train import predict

def _call_llm(system: str, user: str) -> str:
    """Claude CLI 호출. 내부에서 system+user를 단일 prompt로 합쳐서 호출."""
    # 기존 ClaudeClient.predict_sync_compat()와 동일한 계약:
    # - 단일 prompt 문자열로 전달 (-p)
    # - --output-format json, --max-turns 1 고정
    combined_prompt = f"[System]\n{system}\n\n[User]\n{user}"
    result = subprocess.run(
        ["claude", "--model", MODEL, "--max-tokens", str(MAX_TOKENS),
         "--output-format", "json", "--max-turns", "1",
         "-p", combined_prompt],
        capture_output=True, text=True, timeout=RACE_TIMEOUT
    )
    return result.stdout

for race in races:
    prediction = predict(race, call_llm=_call_llm)

# train.py 측 (에이전트 수정 가능):
def predict(race_data: dict, call_llm) -> dict:
    features = select_features(race_data)
    system, user = build_prompt(features)
    response = call_llm(system, user)
    return parse_response(response)
```

**`call_llm` 시그니처**: `(system: str, user: str) -> str`
- `system`: 시스템 프롬프트 (SYSTEM_PROMPT)
- `user`: 유저 프롬프트 (조립된 경주 데이터 + 지시)
- 반환: LLM 원문 응답 문자열

에이전트는 `call_llm`의 구현을 수정할 수 없음. 프롬프트와 전략 함수만 수정 가능.

### 에러 처리 계약

`predict()`가 실패할 경우의 동작:

```python
# prepare.py가 처리하는 에러 케이스:
# 1. predict()가 예외 발생 → json_ok 실패로 카운트
# 2. call_llm timeout (120초) → subprocess.TimeoutExpired → predict()에 전파
# 3. 반환값이 스키마 불일치 → json_ok 실패로 카운트
# 4. confidence < 0.3 → defer (coverage 계산에서 제외)

# train.py의 predict()는 예외를 잡지 않아도 됨.
# prepare.py가 try/except로 감싸서 처리함.
```

### 초깃값 시드
- `prediction-template-v1.7.md`의 분석 로직과 도메인 지식을 참고
- 단, 출력 스키마는 위의 flat 형식으로 새로 정의
- v5 모듈의 아이디어(failure taxonomy, extended thinking 등)도 자유롭게 차용 가능

## 3. program.md (사람이 수정)

autoresearch 원본의 program.md 구조를 따름.

```markdown
# KRA Autoresearch Program

## Setup
1. Run tag 합의: `autoresearch/{tag}` (예: `autoresearch/mar15`)
2. 브랜치 생성: `git checkout -b autoresearch/{tag}`
3. 파일 읽기:
   - `prepare.py` — 고정. 수정 금지.
   - `train.py` — 수정 대상. 프롬프트와 전략 함수.
   - 이 파일(program.md) — 실험 프로토콜.

## Constraints
- `train.py`만 수정할 것
- DB 접근, 파일 I/O, 외부 import 금지
- 출력 스키마 변경 금지: {"predicted", "confidence", "reasoning"}

## Protocol
1. Baseline 먼저 실행: `uv run prepare.py`
   - 현재 점수 기록
2. 가설 수립
   - 무엇을 바꿀지, 왜 나아질 것으로 예상하는지 기록
3. train.py 수정
4. 실행: `uv run prepare.py`
5. 판정:
   - Hard gate 통과 + set_match 개선 → `git commit` (keep)
   - Hard gate 실패 또는 set_match 악화 → `git checkout -- train.py` (revert)
6. 5회 keep마다: `uv run prepare.py --holdout`으로 과적합 검증
   - holdout에서 mini_val 대비 set_match가 5%p 이상 하락 시 경고
7. 반복

## Metrics (참고)
- 주 지표: set_match (0.0~1.0, 높을수록 좋음)
- 보조: avg_correct (0.0~3.0)
- Hard gate: json_ok >= 90%, coverage >= 80%
- 목표: set_match >= 0.50 (경주당 평균 1.5마리 적중)

## Tips
- 프롬프트의 분석 단계(analysis steps)를 체계화하면 효과적
- 말 데이터 중 computed_features(odds_rank, win_rates 등)를 적극 활용
- 너무 많은 정보는 오히려 방해 — 핵심 피처만 선별
- confidence threshold 0.3 미만은 자동 defer 처리됨
```

## Snapshot 관리

- snapshot은 `uv run prepare.py --create-snapshot`으로 최초 1회 생성
- 생성된 `snapshots/mini_val.json`, `snapshots/holdout.json`은 **git에 커밋**하여 불변성 보장
- snapshot 파일에 메타데이터 포함: `{"created_at": "...", "sha256": "...", "race_count": 20, "db_query": "..."}`
- snapshot 재생성이 필요한 경우(DB 업데이트 등): `--force-recreate` 플래그 사용, 새 커밋으로 기록

## 실험 기록

- **keep된 실험**: git commit 메시지에 스코어 포함 (`set_match=0.48 avg_correct=1.44`)
- **revert된 실험**: `experiments.jsonl`에 한 줄씩 기록 (git history에 안 남기 때문)

```json
{"ts": "2026-03-15T10:30:00", "hypothesis": "odds_rank 가중치 추가", "set_match": 0.35, "reverted": true, "reason": "hard_gate_fail:json_ok=80%"}
```

- 이 파일은 `.gitignore`에 추가하지 않음 — 실패 기록도 연구 자산

## 운영 환경

| 항목 | 값 |
|------|-----|
| LLM | Claude (Max 20x 구독) |
| 에이전트 | Claude Code 또는 Codex (종류 무관) |
| 데이터 | 2025년 전체 경기 (Supabase DB) |
| mini_val | 20경주 (고정 snapshot) |
| holdout | 50경주 (고정 snapshot) |
| race timeout | 120초 |
| experiment wall-clock cap | 30분 |
| defer threshold | confidence < 0.3 |

## 기존 시스템과의 관계

| 기존 자산 | autoresearch에서의 역할 |
|-----------|----------------------|
| `evaluate_prompt_v3.py` | prepare.py가 핵심 로직(스코어링) 재사용 |
| `db_client.py` | prepare.py가 데이터 로딩에 재사용 |
| `data_adapter.py` | prepare.py가 enriched 변환에 재사용 |
| `metrics.py` | prepare.py가 set_match_rate 계산에 재사용 |
| `leakage_checks.py` | prepare.py가 snapshot 생성 시 재사용 |
| `feature_engineering.py` | prepare.py가 computed_features 생성에 재사용 |
| `prediction-template-v1.7.md` | train.py 초깃값의 아이디어 시드 (스키마 불포함) |
| `v5 모듈 (4000줄)` | 참고 아이디어 저장소. 직접 사용 안 함 |

## Codex(GPT-5.4) 리뷰 반영 사항

| 지적 | 반영 |
|------|------|
| train.py가 Python이면 label leakage 가능 | DB 접근/파일 I/O 금지 규칙, prepare.py가 race_data만 전달 |
| v1.7 출력 스키마 불일치 | flat 스키마로 새로 정의: `{predicted, confidence, reasoning}` |
| leakage 검사 false positive | snapshot 생성 시 forbidden fields 사전 제거 |
| find_races()가 result_status 안 봄 | result_status='collected' 조건 추가 |
| 시간 무제한 위험 | race timeout 120초 + experiment wall-clock 30분 |
| avg_correct 단독은 노이즈 큼 | set_match_rate를 주 지표로, avg_correct는 보조 |
| coverage gate에 defer threshold 필요 | confidence < 0.3은 defer 처리 |

### Codex 최종 리뷰 (2차) 반영 사항

| 지적 | 반영 |
|------|------|
| call_llm에 `--output-format json`, `--max-turns 1` 누락 | CLI 플래그 추가, ClaudeClient 계약과 동일하게 맞춤 |
| coverage 정의가 metrics.py와 다름 | prepare.py에서 자체 계산으로 명시, metrics.py 재사용하지 않음 |
| 입력 필드(wgHr, ilsu 등) evaluate_prompt_v3.py 로더에 미포함 | raw item 전체 보존 후 forbidden fields만 제거하는 방식으로 변경 |
| temporal split 방향 (앞쪽 = 오래된 데이터) | walk-forward 방식으로 수정: `[...][mini_val][holdout]` |
| train.py 제약이 convention만으로 부족 | AST 기반 import guard를 v1부터 적용 |

## 알려진 제약 및 향후 고려사항

### `rank` 필드 처리
KRA API의 `rank` 필드는 `basic_data`(경주 전 수집)에 포함되므로 **사전 등급(class rating)**이다. `result_status`와 별도로 `collection_status` 단계에서 이미 존재한다. snapshot 생성 시 `rank` → `class_rank`로 rename하여 leakage 검사 false positive를 방지하고, 유용한 사전 정보로 보존한다.

### train.py 제약 강제: import guard

DB 접근 / 파일 I/O 금지는 `program.md`의 규칙 + **prepare.py의 import guard**로 이중 강제한다.

```python
# prepare.py에서 train.py import 전에 실행:
import ast

FORBIDDEN_MODULES = {"db_client", "os", "pathlib", "subprocess", "shutil",
                     "urllib", "requests", "httpx", "supabase"}

def check_train_imports(filepath: str) -> list[str]:
    """train.py의 import문을 AST로 검사, 금지 모듈 사용 시 에러"""
    tree = ast.parse(open(filepath).read())
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_MODULES:
                    violations.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in FORBIDDEN_MODULES:
                violations.append(node.module)
    return violations

violations = check_train_imports("train.py")
if violations:
    print(f"BLOCKED: train.py uses forbidden imports: {violations}")
    sys.exit(1)
```

이 검사는 v1부터 적용한다. `open()`, `__import__()` 등 동적 접근까지 막지는 않지만, 일반적인 에이전트 실수/우회는 방지한다.

### program.md 실행 경로
`uv run prepare.py` 명령은 `packages/scripts/autoresearch/` 디렉토리에서 실행해야 한다. program.md에 `cd packages/scripts/autoresearch && uv run prepare.py` 또는 프로젝트 루트에서 `uv run packages/scripts/autoresearch/prepare.py`로 명시한다.

### prepare.py CLI 인터페이스

```
uv run prepare.py                     # mini_val 20경주 평가 (기본)
uv run prepare.py --holdout           # holdout 50경주 평가
uv run prepare.py --create-snapshot   # snapshot 최초 생성
uv run prepare.py --create-snapshot --force-recreate  # snapshot 재생성
```
