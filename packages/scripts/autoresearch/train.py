"""KRA 삼복연승 예측 전략 — 에이전트가 수정하는 유일한 파일

Rules:
  - DB 접근 금지 (import db_client 금지)
  - 파일 I/O 금지 (os, pathlib 등 금지)
  - predict(race_data, call_llm) 시그니처 유지
  - 출력 스키마 유지: {"predicted": [...], "confidence": float, "reasoning": str}
"""

import json
import math  # noqa: F401 — 허용 목록, 전략 함수에서 사용 가능
import re

# ============================================================
# 1. 프롬프트 템플릿
# ============================================================

SYSTEM_PROMPT = """\
당신은 한국마사회(KRA) 경마 데이터 분석 전문가입니다.
삼복연승(1-3위) 예측을 수행합니다.

분석 원칙:
1. 배당률(winOdds)이 낮을수록 인기마 — 시장 내재 확률 = 1/winOdds
2. 기수·조교사 승률(jockey_win_rate, trainer_win_rate)은 핵심 예측 변수
3. 마필 승률·입상률(horse_win_rate, horse_place_rate)로 실력 판단
4. 부담중량(wgBudam) 대비 마체중(wgHr) 비율이 높을수록 유리
5. 장기휴양(rest_days > 90)은 감점 요인
6. 핸디캡 경주에서는 저부담마가 유리
7. odds_rank 상위 3두가 기본 후보, 거기서 edge를 찾을 것

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트 없이 JSON만 출력하세요."""

USER_PROMPT_TEMPLATE = """\
## 경주 정보
{race_info}

## 출전마 데이터
{horse_data}

## 지시사항
위 데이터를 분석하여 1~3위에 들어올 말의 출전번호(chulNo)를 예측하세요.
순서는 중요하지 않습니다 (set match 기준 평가).

아래 JSON 형식으로만 응답하세요:
{output_schema}"""

OUTPUT_SCHEMA = {
    "predicted": ["1위 chulNo", "2위 chulNo", "3위 chulNo"],
    "confidence": "0.0~1.0 사이 실수",
    "reasoning": "핵심 판단 근거 1~3문장",
}

# ============================================================
# 2. 전략 함수
# ============================================================


def select_features(race_data: dict) -> dict:
    """race_data에서 프롬프트에 포함할 필드 선택"""
    return race_data


def format_race_info(features: dict) -> str:
    """경주 정보를 프롬프트용 텍스트로 포맷"""
    info = features.get("race_info", {})
    labels = {
        "rcDate": "경주일",
        "rcNo": "경주번호",
        "meet": "경마장",
        "rcDist": "거리(m)",
        "track": "주로상태",
        "weather": "날씨",
        "budam": "부담조건",
        "ageCond": "연령조건",
    }
    lines = []
    for key, label in labels.items():
        val = info.get(key, "")
        if val:
            lines.append(f"- {label}: {val}")
    return "\n".join(lines)


def format_horse_data(horses: list[dict]) -> str:
    """말 데이터를 프롬프트용 텍스트로 포맷"""
    lines = []
    for h in horses:
        chul = h.get("chulNo", "?")
        name = h.get("hrName", "?")
        odds = h.get("winOdds", "?")
        plc_odds = h.get("plcOdds", "?")
        age = h.get("age", "?")
        sex = h.get("sex", "?")
        wg_hr = h.get("wgHr", "?")
        wg_budam = h.get("wgBudam", "?")
        class_rank = h.get("class_rank", "?")

        cf = h.get("computed_features", {})
        odds_rank = cf.get("odds_rank", "?")
        horse_wr = cf.get("horse_win_rate", "?")
        horse_pr = cf.get("horse_place_rate", "?")
        jk_wr = cf.get("jockey_win_rate", "?")
        tr_wr = cf.get("trainer_win_rate", "?")
        rest = cf.get("rest_days", "?")
        rest_risk = cf.get("rest_risk", "?")

        line = (
            f"  {chul}번 {name} | 배당={odds}(복={plc_odds}) 인기순위={odds_rank} | "
            f"나이={age} 성별={sex} 체중={wg_hr} 부담={wg_budam} 등급={class_rank} | "
            f"마승률={horse_wr} 입상률={horse_pr} 기수승률={jk_wr} 조교사승률={tr_wr} | "
            f"휴양={rest}일({rest_risk})"
        )
        lines.append(line)
    return "\n".join(lines)


def build_prompt(features: dict) -> tuple[str, str]:
    """프롬프트 조립. (system, user) 튜플 반환."""
    race_info = format_race_info(features)
    horse_data = format_horse_data(features.get("horses", []))
    user = USER_PROMPT_TEMPLATE.format(
        race_info=race_info,
        horse_data=horse_data,
        output_schema=json.dumps(OUTPUT_SCHEMA, ensure_ascii=False, indent=2),
    )
    return SYSTEM_PROMPT, user


def parse_response(llm_output: str) -> dict:
    """LLM 응답을 파싱하여 표준 형식으로 변환.

    처리 순서:
    1. 코드블록(```json ... ```) 추출
    2. 순수 JSON 파싱
    3. regex fallback: "predicted" 키가 포함된 JSON 객체 추출
    """
    text = llm_output.strip()

    # 1) 코드블록 추출
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_block:
        text = code_block.group(1)

    # 2) JSON 파싱
    try:
        data = json.loads(text)
        return _normalize(data)
    except json.JSONDecodeError:
        pass

    # 3) regex fallback — "predicted" 포함 JSON 객체
    match = re.search(r'\{[^{}]*"predicted"\s*:\s*\[[^\]]*\][^{}]*\}', text)
    if match:
        try:
            data = json.loads(match.group(0))
            return _normalize(data)
        except json.JSONDecodeError:
            pass

    return {"predicted": [], "confidence": 0.0, "reasoning": "parse_error"}


def _coerce_chulno(value) -> int | None:
    """LLM/휴리스틱 출력값을 출전번호 int로 정규화"""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return None
    if isinstance(value, str):
        match = re.search(r"\d+", value)
        if match:
            return int(match.group(0))
    return None


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize(data: dict) -> dict:
    """파싱된 dict를 표준 스키마로 정규화"""
    raw_predicted = data.get("predicted", [])
    predicted: list[int] = []
    seen: set[int] = set()
    if isinstance(raw_predicted, list):
        for item in raw_predicted:
            chul_no = _coerce_chulno(item)
            if chul_no is None or chul_no in seen:
                continue
            predicted.append(chul_no)
            seen.add(chul_no)
            if len(predicted) == 3:
                break

    confidence = data.get("confidence", 0.0)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0

    return {
        "predicted": predicted,
        "confidence": confidence,
        "reasoning": str(data.get("reasoning", "")),
    }


def _horse_sort_key(horse: dict) -> tuple[float, ...]:
    hd = horse.get("hrDetail") or {}
    cf = horse.get("computed_features", {})

    # 최근 연도 입상률 (k=2, 700경주 cross-validated 최적)
    starts_y = _safe_int(hd.get("rcCntY"))
    places_y = (
        _safe_int(hd.get("ord1CntY"))
        + _safe_int(hd.get("ord2CntY"))
        + _safe_int(hd.get("ord3CntY"))
    )

    # 총 경력 보정입상률 (폴백용)
    starts_t = _safe_int(hd.get("rcCntT"))
    places_t = (
        _safe_int(hd.get("ord1CntT"))
        + _safe_int(hd.get("ord2CntT"))
        + _safe_int(hd.get("ord3CntT"))
    )
    total_place_rate = places_t / (starts_t + 15) if starts_t >= 0 else 0.0

    # 연도 통계 있으면 사용, 없으면 총 경력 폴백
    year_place_rate = places_y / (starts_y + 2) if starts_y > 0 else total_place_rate

    # 시장 내재 확률 (보정 신호)
    win_odds = _safe_float(horse.get("winOdds"), 99.0)
    odds_signal = 0.06 / max(win_odds, 1.01)

    # 이전 경주 1구간(200m) 순위: 선행력/스피드 지표
    # 서울·제주=sjG1fOrd, 부산=buG1fOrd (경마장별 상호배타)
    sj_pace = _safe_float(horse.get("sjG1fOrd"))
    bu_pace = _safe_float(horse.get("buG1fOrd"))
    pace_ord = sj_pace if sj_pace > 0 else bu_pace
    pace_penalty = 0.12 * pace_ord if pace_ord > 0 else 0.0

    return (
        year_place_rate + odds_signal - pace_penalty,
        total_place_rate,
        -_safe_float(cf.get("odds_rank"), 999.0),
    )


def _heuristic_prediction(race_data: dict) -> dict:
    horses = race_data.get("horses", [])
    ranked = sorted(horses, key=_horse_sort_key, reverse=True)
    top3 = ranked[:3]
    predicted = [
        horse.get("chulNo") for horse in top3 if horse.get("chulNo") is not None
    ]

    if len(predicted) != 3:
        return {"predicted": [], "confidence": 0.0, "reasoning": "insufficient_horses"}

    avg_place = sum(_horse_sort_key(horse)[0] for horse in top3) / 3
    confidence = min(0.88, max(0.55, 0.52 + avg_place * 0.45))

    reasons = []
    for horse in top3:
        cf = horse.get("computed_features", {})
        score = _horse_sort_key(horse)[0]
        reasons.append(
            f"{horse.get('chulNo')}번 {horse.get('hrName', '?')} "
            f"(연도입상률={score:.3f}, "
            f"인기순위={int(_safe_float(cf.get('odds_rank'), 99.0))})"
        )

    return {
        "predicted": predicted,
        "confidence": confidence,
        "reasoning": " | ".join(reasons),
    }


# ============================================================
# 3. 엔트리포인트
# ============================================================


def predict(race_data: dict, call_llm) -> dict:
    """prepare.py가 호출하는 유일한 인터페이스.

    Args:
        race_data: enriched 형식의 경주 데이터
        call_llm: (system: str, user: str) -> str 콜백

    Returns:
        {"predicted": [1, 5, 3], "confidence": 0.72, "reasoning": "..."}
    """
    heuristic = _heuristic_prediction(race_data)
    if len(heuristic["predicted"]) == 3:
        return heuristic

    features = select_features(race_data)
    system, user = build_prompt(features)
    response = call_llm(system, user)
    return parse_response(response)
