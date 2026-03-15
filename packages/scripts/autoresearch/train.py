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


def _normalize(data: dict) -> dict:
    """파싱된 dict를 표준 스키마로 정규화"""
    raw_predicted = data.get("predicted", [])
    # LLM이 문자열로 반환할 수 있으므로 int로 캐스팅
    predicted = []
    for p in raw_predicted:
        try:
            predicted.append(int(p))
        except (TypeError, ValueError):
            predicted.append(p)

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
    features = select_features(race_data)
    system, user = build_prompt(features)
    response = call_llm(system, user)
    return parse_response(response)
