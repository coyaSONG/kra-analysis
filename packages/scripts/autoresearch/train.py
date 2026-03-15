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
삼복연승(1-3위) 예측을 수행합니다. 순서는 중요하지 않습니다.

핵심 발견: 입상률(horse_place_rate)이 가장 강력한 예측 변수입니다.

분석 우선순위 (중요도 순):
1. horse_place_rate (입상률) — 가장 중요. 높을수록 3위 이내 확률 높음
2. jockey_place_rate (기수 입상률) — 두 번째로 중요
3. winOdds (배당률) — 시장 합의. 낮을수록 인기마
4. horse_win_rate (마필 승률) — 보조 지표
5. rest_risk — high이면 감점
6. 핸디캡 경주: 부담중량 높은 말 감점

절차:
1. horse_place_rate 상위 5마를 후보로 선정
2. 후보 중 jockey_place_rate와 odds_rank를 종합 평가
3. 최종 3마 선택

반드시 JSON만 출력하세요. 다른 텍스트 없이."""

USER_PROMPT_TEMPLATE = """\
## 경주 정보
{race_info}

## 출전마 데이터
{horse_data}

## 통계 기반 추천 (참고)
입상률+기수입상률 기반 상위 3마: {heuristic_hint}
이 추천은 통계 모델의 출력입니다. 당신은 경주 조건, 휴양 상태, 핸디캡 등을 고려하여 이 추천을 수정할 수 있습니다.

## 지시사항
위 데이터와 통계 추천을 참고하여 1~3위에 들어올 말의 출전번호(chulNo)를 예측하세요.
추천을 그대로 따라도 되고, 근거가 있으면 수정해도 됩니다.

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


def _safe_int(val) -> int:
    """안전한 int 변환"""
    try:
        return int(val or 0)
    except (TypeError, ValueError):
        return 0


def _compute_heuristic_score(horse: dict) -> float:
    """raw 성적에서 Laplace smoothed place rate 직접 계산"""
    k = 2  # Laplace smoothing parameter

    hd = horse.get("hrDetail", {})
    h_starts = _safe_int(hd.get("rcCntT"))
    h_place = (
        _safe_int(hd.get("ord1CntT"))
        + _safe_int(hd.get("ord2CntT"))
        + _safe_int(hd.get("ord3CntT"))
    )
    h_spr = h_place / (h_starts + k) if (h_starts + k) > 0 else 0

    jd = horse.get("jkDetail", {})
    j_starts = _safe_int(jd.get("rcCntT"))
    j_place = (
        _safe_int(jd.get("ord1CntT"))
        + _safe_int(jd.get("ord2CntT"))
        + _safe_int(jd.get("ord3CntT"))
    )
    j_spr = j_place / (j_starts + k) if (j_starts + k) > 0 else 0

    score = h_spr + j_spr * 0.2

    # odds_rank 보너스: 1번 인기마 입상률 70-76%, 2번도 60%+
    cf = horse.get("computed_features", {})
    odds_rank = cf.get("odds_rank", 99)
    if odds_rank == 1:
        score += 0.08
    elif odds_rank == 2:
        score += 0.02

    return score


def select_features(race_data: dict) -> dict:
    """race_data에서 프롬프트에 포함할 필드 선택 + 휴리스틱 pre-ranking 추가"""
    horses = race_data.get("horses", [])
    # 휴리스틱 점수로 정렬
    scored = [(h, _compute_heuristic_score(h)) for h in horses]
    scored.sort(key=lambda x: -x[1])
    # 상위 3마를 힌트로 추가
    hint_top3 = [h.get("chulNo") for h, _ in scored[:3]]
    result = dict(race_data)
    result["heuristic_hint"] = hint_top3
    return result


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
    heuristic_hint = features.get("heuristic_hint", [])
    user = USER_PROMPT_TEMPLATE.format(
        race_info=race_info,
        horse_data=horse_data,
        heuristic_hint=heuristic_hint,
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


def _heuristic_predict(race_data: dict) -> dict:
    """순수 휴리스틱 예측 (LLM 미사용). 더 빠르고 안정적."""
    horses = race_data.get("horses", [])
    if len(horses) < 3:
        return {"predicted": [], "confidence": 0.0, "reasoning": "too_few_horses"}

    scored = [(h, _compute_heuristic_score(h)) for h in horses]
    scored.sort(key=lambda x: -x[1])
    top3 = scored[:3]

    predicted = [h.get("chulNo") for h, _ in top3]
    reasons = [
        f"{h.get('chulNo')}번 {h.get('hrName', '?')} "
        f"(입상률={h.get('computed_features', {}).get('horse_place_rate', 0):.0f}%)"
        for h, _ in top3
    ]
    return {
        "predicted": predicted,
        "confidence": 0.7,
        "reasoning": ", ".join(reasons),
    }


def predict(race_data: dict, call_llm) -> dict:
    """prepare.py가 호출하는 유일한 인터페이스.

    Args:
        race_data: enriched 형식의 경주 데이터
        call_llm: (system: str, user: str) -> str 콜백

    Returns:
        {"predicted": [1, 5, 3], "confidence": 0.72, "reasoning": "..."}
    """
    # 휴리스틱 우선, LLM은 사용하지 않음 (실험 6)
    return _heuristic_predict(race_data)
