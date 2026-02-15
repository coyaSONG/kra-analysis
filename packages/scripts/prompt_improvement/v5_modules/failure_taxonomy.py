"""
실패 패턴 분류 시스템
예측 실패를 7개 카테고리로 분류하여 표적 개선을 가능하게 합니다.
"""

from __future__ import annotations

from collections import defaultdict
from enum import Enum
from typing import Any


class FailureCategory(Enum):
    PARSING_ERROR = "parsing"
    FAVORITE_BIAS = "favorite_bias"
    DISTANCE_MISMATCH = "distance"
    FORM_CONFLICT = "form_conflict"
    FIELD_SIZE = "field_size"
    CONDITION_MISMATCH = "condition"
    DATA_INSUFFICIENT = "data_gap"


class FailureClassifier:
    """예측 실패를 카테고리로 분류"""

    def _get_odds_ranks(self, race_data: dict) -> dict[int, int]:
        """Build horse_no -> odds_rank mapping."""
        entries = race_data.get("horses", race_data.get("entries", []))
        valid = []
        for e in entries:
            horse_no = e.get("horse_no", e.get("chulNo"))
            odds = e.get("win_odds", e.get("winOdds", 0))
            try:
                horse_no = int(horse_no)
                odds = float(odds)
            except (TypeError, ValueError):
                continue
            if odds > 0:
                valid.append((horse_no, odds))
        valid.sort(key=lambda x: x[1])
        return {h: i + 1 for i, (h, _) in enumerate(valid)}

    def _get_entry_for_horse(self, horse_no: int, race_data: dict) -> dict | None:
        """Find entry dict for a specific horse number."""
        entries = race_data.get("horses", race_data.get("entries", []))
        for e in entries:
            hn = e.get("horse_no", e.get("chulNo"))
            try:
                if int(hn) == horse_no:
                    return e
            except (TypeError, ValueError):
                continue
        return None

    def classify(self, result: dict) -> FailureCategory:
        """Classify a single failed prediction result."""
        # 1. Parsing error
        error_type = result.get("error_type", "success")
        if error_type != "success" and error_type is not None:
            return FailureCategory.PARSING_ERROR

        predicted = result.get("predicted", [])
        actual = result.get("actual", [])
        race_data = result.get("race_data", {})

        if not predicted or not actual:
            return FailureCategory.PARSING_ERROR

        # Get odds ranks
        odds_ranks = self._get_odds_ranks(race_data)

        # 2. Favorite bias - all predicted are top-3 by odds
        predicted_ranks = [odds_ranks.get(int(h), 99) for h in predicted[:3]]
        if all(r <= 3 for r in predicted_ranks):
            return FailureCategory.FAVORITE_BIAS

        # 3. Distance mismatch - check winner's distance experience
        winner = actual[0] if actual else None
        if winner is not None:
            winner_entry = self._get_entry_for_horse(int(winner), race_data)
            if winner_entry:
                hr_detail = winner_entry.get("hrDetail", {})
                race_info = race_data.get("raceInfo", {})
                rc_dist = 0
                try:
                    rc_dist = int(race_info.get("rcDist", 0))
                except (TypeError, ValueError):
                    pass

                # Check if horse has distance experience
                # We check rcCntT (total race count) as proxy
                rc_cnt = hr_detail.get("rcCntT", 0)
                try:
                    rc_cnt = int(rc_cnt)
                except (TypeError, ValueError):
                    rc_cnt = 0

                # 6. Data insufficient - few races
                if rc_cnt < 5:
                    return FailureCategory.DATA_INSUFFICIENT

                # 4. Form conflict - high long-term ability but low recent form
                place_rate = float(hr_detail.get("placeRate", 0) or 0)
                # Check if horse is good long-term but possibly inconsistent
                win_rate = float(hr_detail.get("winRate", 0) or 0)

                # Use odds rank as proxy for current form assessment
                winner_odds_rank = odds_ranks.get(int(winner), 99)
                if place_rate >= 30 and winner_odds_rank > 6:
                    return FailureCategory.FORM_CONFLICT

        # 5. Field size - large fields are harder
        entries = race_data.get("horses", race_data.get("entries", []))
        if len(entries) > 12:
            return FailureCategory.FIELD_SIZE

        # 7. Default - condition mismatch
        return FailureCategory.CONDITION_MISMATCH

    def classify_batch(
        self, results: list[dict]
    ) -> dict[FailureCategory, list[dict]]:
        """Batch classify and group by category."""
        classified: dict[FailureCategory, list[dict]] = defaultdict(list)
        for result in results:
            category = self.classify(result)
            classified[category].append(result)
        return dict(classified)

    def generate_category_report(self, classified: dict[FailureCategory, list[dict]]) -> str:
        """Generate markdown report of failure distribution."""
        total = sum(len(v) for v in classified.values())
        if total == 0:
            return "실패 분류 데이터 없음"

        lines = ["## 실패 패턴 분류 보고서\n"]
        lines.append(f"총 실패 건수: {total}건\n")
        lines.append("| 카테고리 | 건수 | 비율 |")
        lines.append("|----------|------|------|")

        category_names = {
            FailureCategory.PARSING_ERROR: "파싱 오류",
            FailureCategory.FAVORITE_BIAS: "인기마 편향",
            FailureCategory.DISTANCE_MISMATCH: "거리 부적합",
            FailureCategory.FORM_CONFLICT: "폼 충돌",
            FailureCategory.FIELD_SIZE: "대규모 필드",
            FailureCategory.CONDITION_MISMATCH: "조건 불일치",
            FailureCategory.DATA_INSUFFICIENT: "데이터 부족",
        }

        for category in FailureCategory:
            items = classified.get(category, [])
            count = len(items)
            ratio = count / total * 100 if total > 0 else 0
            lines.append(f"| {category_names[category]} | {count} | {ratio:.1f}% |")

        # Representative examples for top categories
        sorted_cats = sorted(classified.items(), key=lambda x: len(x[1]), reverse=True)
        for cat, items in sorted_cats[:3]:
            if items:
                lines.append(f"\n### {category_names[cat]} 대표 사례")
                for item in items[:2]:
                    race_id = item.get("race_id", "unknown")
                    predicted = item.get("predicted", [])
                    actual = item.get("actual", [])
                    lines.append(f"- {race_id}: 예측={predicted}, 실제={actual}")

        return "\n".join(lines)
