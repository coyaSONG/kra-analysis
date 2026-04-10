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

from shared.alternative_ranking import rank_race_entries
from shared.prerace_field_policy import filter_prerace_payload
from shared.runner_status import select_prediction_candidates

# ============================================================
# 1. 프롬프트 템플릿
# ============================================================

SYSTEM_PROMPT = """\
당신은 한국마사회(KRA) 경마 데이터 분석 전문가입니다.
삼복연승(1-3위) 예측을 수행합니다.

분석 원칙:
1. 출전표 확정 시점까지 확인 가능한 정보만 사용한다
2. 기수·조교사 승률(jockey_win_rate, trainer_win_rate)은 핵심 예측 변수다
3. 마필 승률·입상률(horse_win_rate, horse_place_rate)로 실력과 안정성을 판단한다
4. 부담중량(wgBudam) 대비 마체중(wgHr), 레이팅(rating), 휴양일수(rest_days)를 함께 본다
5. 장기휴양(rest_days > 90)은 감점 요인이다
6. 핸디캡 경주에서는 부담중량과 레이팅 균형을 더 엄격히 본다
7. 배당률, 사후 구간 순위/기록, 결과 확정 필드는 사용하지 않는다

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트 없이 JSON만 출력하세요."""

USER_PROMPT_TEMPLATE = """\
## 경주 정보
{race_info}

## 후보 필터 요약
{candidate_filter_summary}

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
    existing_candidate_filter = race_data.get("candidate_filter")
    if isinstance(existing_candidate_filter, dict) and race_data.get("horses"):
        candidate_filter = existing_candidate_filter
        eligible_runners = list(race_data.get("horses", []))
    else:
        candidate_selection = select_prediction_candidates(
            race_data.get("horses", []),
            cancelled_horses=race_data.get("cancelled_horses", []),
        )
        candidate_filter = candidate_selection.to_audit_dict()
        eligible_runners = candidate_selection.eligible_runners
    prerace_payload = dict(race_data)
    prerace_payload["horses"] = eligible_runners
    prerace_payload["candidate_filter"] = candidate_filter
    filtered, _policy = filter_prerace_payload(prerace_payload)
    return filtered


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
        age = h.get("age", "?")
        sex = h.get("sex", "?")
        wg_hr = h.get("wgHr", "?")
        wg_budam = h.get("wgBudam", "?")
        rating = h.get("rating", "?")
        class_rank = h.get("class_rank", "?")

        cf = h.get("computed_features", {})
        horse_wr = cf.get("horse_win_rate", "?")
        horse_pr = cf.get("horse_place_rate", "?")
        jk_wr = cf.get("jockey_win_rate", "?")
        tr_wr = cf.get("trainer_win_rate", "?")
        rest = cf.get("rest_days", "?")
        rest_risk = cf.get("rest_risk", "?")

        parts = [
            f"{chul}번 {name}",
            f"나이={age} 성별={sex}",
            f"체중={wg_hr} 부담={wg_budam}",
            f"등급={class_rank} 레이팅={rating}",
            f"마승률={horse_wr} 입상률={horse_pr}",
            f"기수승률={jk_wr} 조교사승률={tr_wr}",
            f"휴양={rest}일({rest_risk})",
        ]
        quality_flags = h.get("quality_flags") or h.get("candidate_filter", {}).get(
            "quality_flags", []
        )
        if quality_flags:
            parts.append(f"플래그={','.join(str(flag) for flag in quality_flags)}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def format_candidate_filter_summary(features: dict) -> str:
    candidate_filter = features.get("candidate_filter", {})
    if not isinstance(candidate_filter, dict) or not candidate_filter:
        return "- 필터 메타 없음"

    status_counts = candidate_filter.get("status_counts", {})
    exclusion_rule_counts = candidate_filter.get("exclusion_rule_counts", {})
    reinclusion_rule_counts = candidate_filter.get("reinclusion_rule_counts", {})
    flag_counts = candidate_filter.get("flag_counts", {})

    parts = [
        f"상태집계={json.dumps(status_counts, ensure_ascii=False, sort_keys=True)}",
        f"제외사유={json.dumps(exclusion_rule_counts, ensure_ascii=False, sort_keys=True)}",
        f"재편입사유={json.dumps(reinclusion_rule_counts, ensure_ascii=False, sort_keys=True)}",
        f"플래그집계={json.dumps(flag_counts, ensure_ascii=False, sort_keys=True)}",
    ]
    return "\n".join(f"- {part}" for part in parts)


def build_prompt(features: dict) -> tuple[str, str]:
    """프롬프트 조립. (system, user) 튜플 반환."""
    race_info = format_race_info(features)
    candidate_filter_summary = format_candidate_filter_summary(features)
    horse_data = format_horse_data(features.get("horses", []))
    user = USER_PROMPT_TEMPLATE.format(
        race_info=race_info,
        candidate_filter_summary=candidate_filter_summary,
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


def _normalize(data: dict, *, eligible_chul_nos: set[int] | None = None) -> dict:
    """파싱된 dict를 표준 스키마로 정규화"""
    raw_predicted = data.get("predicted", [])
    predicted: list[int] = []
    seen: set[int] = set()
    if isinstance(raw_predicted, list):
        for item in raw_predicted:
            chul_no = _coerce_chulno(item)
            if chul_no is None or chul_no in seen:
                continue
            if eligible_chul_nos is not None and chul_no not in eligible_chul_nos:
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


def _year_place_rate(horse: dict) -> float:
    hd = horse.get("hrDetail") or {}
    starts_y = _safe_int(hd.get("rcCntY"))
    places_y = (
        _safe_int(hd.get("ord1CntY"))
        + _safe_int(hd.get("ord2CntY"))
        + _safe_int(hd.get("ord3CntY"))
    )
    if starts_y > 0:
        return places_y / (starts_y + 2)
    return _total_place_rate(horse)


def _total_place_rate(horse: dict) -> float:
    hd = horse.get("hrDetail") or {}
    starts_t = _safe_int(hd.get("rcCntT"))
    places_t = (
        _safe_int(hd.get("ord1CntT"))
        + _safe_int(hd.get("ord2CntT"))
        + _safe_int(hd.get("ord3CntT"))
    )
    return places_t / (starts_t + 15) if starts_t >= 0 else 0.0


def _format_reason_value(value: object, digits: int = 3) -> str:
    number = _safe_float(value, default=float("nan"))
    if math.isfinite(number):
        return f"{number:.{digits}f}"
    return "-"


def _heuristic_prediction(race_data: dict) -> dict:
    horses = race_data.get("horses", [])
    if len(horses) < 3:
        return {"predicted": [], "confidence": 0.0, "reasoning": "insufficient_horses"}

    ranked_entries = rank_race_entries(horses)
    top3_entries = ranked_entries[:3]
    predicted = [entry.chul_no for entry in top3_entries if entry.chul_no is not None]

    avg_year_place = (
        sum(entry.rule_values.get("year_place_rate") or 0.0 for entry in top3_entries)
        / 3
    )
    confidence = min(0.88, max(0.55, 0.52 + avg_year_place * 0.40))

    reasons = []
    for entry in top3_entries:
        horse = entry.horse
        rule_values = entry.rule_values
        reasons.append(
            f"{horse.get('chulNo')}번 {horse.get('hrName', '?')} "
            f"(말스킬={_format_reason_value(rule_values.get('horse_top3_skill'))}, "
            f"연도입상률={_format_reason_value(rule_values.get('year_place_rate'))}, "
            f"레이팅={_format_reason_value(rule_values.get('rating'), digits=1)})"
        )

    prediction = {
        "predicted": predicted,
        "confidence": confidence,
        "reasoning": " | ".join(reasons),
    }
    return _append_candidate_filter_reasoning(
        prediction, race_data.get("candidate_filter")
    )


def _append_candidate_filter_reasoning(
    prediction: dict, candidate_filter: dict | None
) -> dict:
    if not candidate_filter or not isinstance(candidate_filter, dict):
        return prediction

    status_counts = candidate_filter.get("status_counts", {})
    exclusion_rule_counts = candidate_filter.get("exclusion_rule_counts", {})
    reinclusion_rule_counts = candidate_filter.get("reinclusion_rule_counts", {})
    flag_counts = candidate_filter.get("flag_counts", {})

    extras = []
    if exclusion_rule_counts:
        extras.append(
            "제외="
            + ",".join(
                f"{rule}:{count}"
                for rule, count in sorted(exclusion_rule_counts.items())
            )
        )
    if reinclusion_rule_counts:
        extras.append(
            "재편입="
            + ",".join(
                f"{rule}:{count}"
                for rule, count in sorted(reinclusion_rule_counts.items())
            )
        )
    if flag_counts:
        extras.append(
            "플래그="
            + ",".join(f"{rule}:{count}" for rule, count in sorted(flag_counts.items()))
        )
    if status_counts:
        extras.append(
            "상태="
            + ",".join(
                f"{status}:{count}" for status, count in sorted(status_counts.items())
            )
        )

    if not extras:
        return prediction

    reasoning = str(prediction.get("reasoning", "")).strip()
    prediction["reasoning"] = " | ".join(part for part in (reasoning, *extras) if part)
    return prediction


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
    existing_candidate_filter = race_data.get("candidate_filter")
    if isinstance(existing_candidate_filter, dict) and race_data.get("horses"):
        candidate_filter = existing_candidate_filter
        eligible_runners = list(race_data.get("horses", []))
    else:
        candidate_selection = select_prediction_candidates(
            race_data.get("horses", []),
            cancelled_horses=race_data.get("cancelled_horses", []),
        )
        candidate_filter = candidate_selection.to_audit_dict()
        eligible_runners = candidate_selection.eligible_runners
    features = select_features(race_data)
    features["candidate_filter"] = candidate_filter
    eligible_chul_nos = {
        horse.get("chulNo")
        for horse in eligible_runners
        if horse.get("chulNo") is not None
    }
    system, user = build_prompt(features)
    try:
        response = call_llm(system, user)
    except Exception:
        return _heuristic_prediction(features)

    parsed = parse_response(response)
    normalized = _normalize(parsed, eligible_chul_nos=eligible_chul_nos)
    if len(normalized.get("predicted", [])) == 3:
        return _append_candidate_filter_reasoning(
            normalized, features.get("candidate_filter")
        )

    if not str(response).strip():
        return _heuristic_prediction(features)

    if parsed.get("reasoning") == "parse_error":
        return _append_candidate_filter_reasoning(
            normalized, features.get("candidate_filter")
        )

    if len(eligible_chul_nos) >= 3:
        return _heuristic_prediction(features)

    return _append_candidate_filter_reasoning(
        normalized, features.get("candidate_filter")
    )
