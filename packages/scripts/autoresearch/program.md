# KRA Autoresearch Program

## Setup
1. Run tag 합의: `autoresearch/{tag}` (예: `autoresearch/mar15`)
2. 브랜치 생성: `git checkout -b autoresearch/{tag}`
3. 파일 읽기:
   - `prepare.py` — 고정. 수정 금지.
   - `train.py` — 수정 대상. 프롬프트와 전략 함수.
   - 이 파일(`program.md`) — 실험 프로토콜.
4. Snapshot 확인: `ls snapshots/` — mini_val.json, holdout.json, answer_key.json이 있어야 함
   - 없으면: `cd packages/scripts/autoresearch && uv run prepare.py --create-snapshot`

## Constraints
- `train.py`만 수정할 것
- DB 접근, 파일 I/O, 외부 import 금지 (os, pathlib, subprocess, requests 등)
- 출력 스키마 변경 금지: `{"predicted": [...], "confidence": float, "reasoning": str}`
- `predict(race_data, call_llm)` 시그니처 유지

## Protocol
1. **Baseline 실행**: `cd packages/scripts/autoresearch && uv run prepare.py`
   - 현재 점수 기록
2. **가설 수립**
   - 무엇을 바꿀지, 왜 나아질 것으로 예상하는지 명확히 기술
3. **train.py 수정**
4. **실행**: `cd packages/scripts/autoresearch && uv run prepare.py`
5. **판정**:
   - Hard gate 통과 + set_match 개선 → `git commit -m "experiment: {가설 요약} set_match={점수}"`
   - Hard gate 실패 또는 set_match 악화 → `git checkout -- train.py`
6. **5회 keep마다**: `uv run prepare.py --holdout`으로 과적합 검증
   - holdout에서 mini_val 대비 set_match가 5%p 이상 하락 시 경고 → 최근 keep revert 고려
7. **반복**

## Metrics
- 주 지표: `set_match` (0.0~1.0, 높을수록 좋음)
- 보조: `avg_correct` (0.0~3.0)
- Hard gate: `json_ok >= 90%`, `coverage >= 80%`
- 목표: `set_match >= 0.50`

## Tips
- 프롬프트의 분석 단계(analysis steps)를 체계화하면 효과적
- 말 데이터 중 `computed_features` (odds_rank, win_rates 등)를 적극 활용
- 너무 많은 정보는 오히려 방해 — 핵심 피처만 선별
- `confidence` < 0.3은 자동 defer 처리됨
- `prediction-template-v1.7.md`의 13단계 분석 프로토콜을 참고하면 좋음
- v5 모듈의 failure taxonomy, extended thinking 등 아이디어 차용 가능

## Data Schema
`race_data` dict에 포함된 주요 필드:

```
race_data = {
    "race_id": "...",
    "race_date": "YYYYMMDD",
    "meet": "서울|부산경남|제주",
    "race_info": {rcDate, rcNo, meet, rcDist, track, weather, budam, ageCond},
    "horses": [
        {
            "chulNo": int,
            "hrName": str,
            "winOdds": float,
            "plcOdds": float,
            "class_rank": str,     # 등급 (원래 "rank" → rename)
            "wgBudam": float,      # 부담중량
            "wgHr": str,           # 마체중
            "age": int,
            "sex": str,
            "hrDetail": {...},     # 마필 상세 (camelCase)
            "jkDetail": {...},     # 기수 상세
            "trDetail": {...},     # 조교사 상세
            "computed_features": {
                "odds_rank": int,
                "rating_rank": int,
                "burden_ratio": float,
                "horse_win_rate": float,
                "horse_place_rate": float,
                "jockey_win_rate": float,
                "jockey_place_rate": float,
                "trainer_win_rate": float,
                "rest_days": int,
                "rest_risk": "high|medium|low",
                "age_prime": bool,
            }
        }
    ]
}
```
