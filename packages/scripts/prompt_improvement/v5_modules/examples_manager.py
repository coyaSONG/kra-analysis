"""
예시 관리 시스템

Few-shot learning을 위한 예시들을 체계적으로 관리하고
최적의 예시를 선택하는 시스템입니다.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Example:
    """개별 예시를 표현하는 클래스"""

    example_id: str
    example_type: str  # "success" or "failure"
    race_id: str
    input_data: dict[str, Any]  # 입력 데이터 (경주 정보)
    predicted: list[int]  # 예측한 말 번호들
    actual: list[int]  # 실제 결과
    confidence: int  # 예측 신뢰도
    correct_count: int  # 맞춘 개수
    analysis_note: str  # 분석 노트 (실패 이유 등)
    created_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0  # 사용 횟수
    performance_score: float = 0.0  # 이 예시가 포함된 프롬프트의 평균 성능

    def to_prompt_format(self) -> str:
        """프롬프트에 사용할 형식으로 변환"""
        result_symbol = "✅" if self.correct_count == 3 else "❌"

        text = "입력: [경주 데이터]\n"
        text += f"출력: {{'predicted': {self.predicted}, 'confidence': {self.confidence}, 'brief_reason': ''}}\n"
        text += f"결과: {result_symbol} 정답 {self.actual}"

        if self.analysis_note:
            text += f" (분석: {self.analysis_note})"

        return text

    def get_pattern_features(self) -> dict[str, Any]:
        """예시의 패턴 특성 추출"""
        features = {
            "odds_ranks": [],  # 예측한 말들의 배당률 순위
            "jockey_winrates": [],  # 기수 승률
            "horse_placerates": [],  # 말 입상률
            "is_balanced": False,  # 균형 잡힌 선택인지
        }

        if self.input_data.get("entries"):
            entries = self.input_data["entries"]

            # 배당률 순위 계산
            sorted_entries = sorted(
                [e for e in entries if e.get("win_odds", 0) > 0],
                key=lambda x: x["win_odds"],
            )
            odds_ranks = {e["horse_no"]: i + 1 for i, e in enumerate(sorted_entries)}

            for horse_no in self.predicted:
                entry = next(
                    (e for e in entries if e.get("horse_no") == horse_no), None
                )
                if entry:
                    features["odds_ranks"].append(odds_ranks.get(horse_no, 99))

                    if entry.get("jkDetail"):
                        features["jockey_winrates"].append(
                            entry["jkDetail"].get("winRate", 0)
                        )

                    if entry.get("hrDetail"):
                        features["horse_placerates"].append(
                            entry["hrDetail"].get("placeRate", 0)
                        )

            # 균형 확인 (인기마와 비인기마 혼합)
            if features["odds_ranks"]:
                popular_count = sum(1 for r in features["odds_ranks"] if r <= 3)
                unpopular_count = sum(1 for r in features["odds_ranks"] if r > 6)
                features["is_balanced"] = popular_count > 0 and unpopular_count > 0

        return features


@dataclass
class ExamplePool:
    """예시 풀을 관리하는 클래스"""

    examples: dict[str, Example] = field(default_factory=dict)
    success_examples: list[str] = field(default_factory=list)  # 성공 예시 ID 목록
    failure_examples: list[str] = field(default_factory=list)  # 실패 예시 ID 목록

    def add_example(self, example: Example) -> None:
        """예시 추가"""
        self.examples[example.example_id] = example

        if example.example_type == "success":
            self.success_examples.append(example.example_id)
        else:
            self.failure_examples.append(example.example_id)

    def remove_example(self, example_id: str) -> bool:
        """예시 제거"""
        if example_id in self.examples:
            example = self.examples[example_id]
            del self.examples[example_id]

            if example.example_type == "success":
                self.success_examples.remove(example_id)
            else:
                self.failure_examples.remove(example_id)

            return True
        return False

    def get_example(self, example_id: str) -> Example | None:
        """예시 조회"""
        return self.examples.get(example_id)

    def get_success_examples(self, limit: int | None = None) -> list[Example]:
        """성공 예시 목록 반환"""
        examples = [
            self.examples[eid] for eid in self.success_examples if eid in self.examples
        ]
        if limit:
            examples = examples[:limit]
        return examples

    def get_failure_examples(self, limit: int | None = None) -> list[Example]:
        """실패 예시 목록 반환"""
        examples = [
            self.examples[eid] for eid in self.failure_examples if eid in self.examples
        ]
        if limit:
            examples = examples[:limit]
        return examples

    def get_top_performers(self, count: int = 5) -> list[Example]:
        """성과가 좋은 상위 예시들 반환"""
        all_examples = list(self.examples.values())
        sorted_examples = sorted(
            all_examples,
            key=lambda e: (e.performance_score, -e.usage_count),
            reverse=True,
        )
        return sorted_examples[:count]

    def get_diverse_examples(self, count: int = 4) -> list[Example]:
        """다양한 패턴의 예시들 반환"""
        selected = []
        used_patterns: set[str] = set()

        # 성공 예시 중에서 다양한 패턴 선택
        for example in self.get_success_examples():
            features = example.get_pattern_features()

            # 패턴 시그니처 생성
            odds_pattern = tuple(sorted(features["odds_ranks"]))

            if odds_pattern not in used_patterns:
                selected.append(example)
                used_patterns.add(odds_pattern)

                if len(selected) >= count - 1:  # 1개는 실패 예시를 위해 남김
                    break

        # 교훈적인 실패 예시 1개 추가
        failure_examples = self.get_failure_examples()
        if failure_examples:
            # 가장 최근의 실패 예시
            selected.append(failure_examples[0])

        return selected[:count]


class ExamplePerformanceTracker:
    """예시별 성과 추적"""

    def __init__(self):
        self.performance_history: dict[str, list[float]] = defaultdict(list)

    def track_performance(
        self, example_ids: list[str], evaluation_result: float
    ) -> None:
        """특정 예시들이 포함된 프롬프트의 성과 기록"""
        for example_id in example_ids:
            self.performance_history[example_id].append(evaluation_result)

    def get_average_performance(self, example_id: str) -> float:
        """예시의 평균 성과 반환"""
        history = self.performance_history.get(example_id, [])
        return sum(history) / len(history) if history else 0.0

    def get_consistency_score(self, example_id: str) -> float:
        """예시의 일관성 점수 (성과의 표준편차 기반)"""
        history = self.performance_history.get(example_id, [])
        if len(history) < 2:
            return 1.0  # 데이터 부족시 중립값

        avg = sum(history) / len(history)
        variance = sum((x - avg) ** 2 for x in history) / len(history)
        std_dev = variance**0.5

        # 표준편차가 낮을수록 일관성이 높음
        return 1.0 / (1.0 + std_dev)


class ExampleCurator:
    """최적의 예시 선택을 담당하는 큐레이터"""

    def __init__(
        self, example_pool: ExamplePool, performance_tracker: ExamplePerformanceTracker
    ):
        self.example_pool = example_pool
        self.performance_tracker = performance_tracker

    def select_optimal_examples(
        self, target_count: int = 4, strategy: str = "balanced"
    ) -> list[Example]:
        """최적의 예시 조합 선택"""

        if strategy == "balanced":
            return self._select_balanced_examples(target_count)
        elif strategy == "performance":
            return self._select_performance_based(target_count)
        elif strategy == "diverse":
            return self._select_diverse_examples(target_count)
        else:
            # 기본 전략
            return self._select_balanced_examples(target_count)

    def _select_balanced_examples(self, count: int) -> list[Example]:
        """균형 잡힌 예시 선택 (성공/실패, 인기/비인기)"""
        selected = []

        # 1. 최고 성과 성공 예시 2개
        top_success = []
        for example in self.example_pool.get_success_examples():
            example.performance_score = (
                self.performance_tracker.get_average_performance(example.example_id)
            )
            top_success.append(example)

        top_success.sort(key=lambda e: e.performance_score, reverse=True)
        selected.extend(top_success[:2])

        # 2. 경계 사례 (아슬아슬하게 성공한 경우)
        edge_cases = [
            e
            for e in self.example_pool.get_success_examples()
            if e.correct_count == 3
            and any(rank > 5 for rank in e.get_pattern_features()["odds_ranks"])
        ]
        if edge_cases:
            selected.append(edge_cases[0])

        # 3. 교훈적인 실패 사례
        failure_examples = self.example_pool.get_failure_examples()
        if failure_examples:
            # 가장 최근의 실패 중에서 분석 노트가 있는 것 우선
            educational_failures = [
                e
                for e in failure_examples
                if e.analysis_note and "인기마 무시" in e.analysis_note
            ]
            if educational_failures:
                selected.append(educational_failures[0])
            else:
                selected.append(failure_examples[0])

        return selected[:count]

    def _select_performance_based(self, count: int) -> list[Example]:
        """성과 기반 예시 선택"""
        # 모든 예시의 성과 점수 계산
        all_examples = []

        for example in self.example_pool.examples.values():
            example.performance_score = (
                self.performance_tracker.get_average_performance(example.example_id)
            )
            consistency = self.performance_tracker.get_consistency_score(
                example.example_id
            )

            # 종합 점수 = 성과 * 일관성
            combined_score = example.performance_score * consistency
            all_examples.append((example, combined_score))

        # 점수 순으로 정렬
        all_examples.sort(key=lambda x: x[1], reverse=True)

        # 상위 예시 선택 (단, 최소 1개는 실패 예시 포함)
        selected = []
        failure_included = False

        for example, _score in all_examples:
            if len(selected) >= count:
                break

            if example.example_type == "failure" and not failure_included:
                selected.append(example)
                failure_included = True
            elif example.example_type == "success":
                selected.append(example)

        # 실패 예시가 없으면 마지막 하나를 실패 예시로 교체
        if not failure_included and self.example_pool.failure_examples:
            selected[-1] = self.example_pool.get_failure_examples(1)[0]

        return selected

    def _select_diverse_examples(self, count: int) -> list[Example]:
        """다양성 기반 예시 선택"""
        return self.example_pool.get_diverse_examples(count)


class ExamplesManager:
    """통합 예시 관리 시스템"""

    def __init__(self):
        self.example_pool = ExamplePool()
        self.performance_tracker = ExamplePerformanceTracker()
        self.curator = ExampleCurator(self.example_pool, self.performance_tracker)

    def create_example_from_result(
        self, race_result: dict[str, Any], example_type: str | None = None
    ) -> Example:
        """평가 결과로부터 예시 생성"""
        # 타입 자동 결정
        if example_type is None:
            correct_count = race_result.get("reward", {}).get("correct_count", 0)
            example_type = "success" if correct_count == 3 else "failure"

        # 분석 노트 생성
        analysis_note = ""
        if example_type == "failure":
            # 실패 원인 분석
            predicted = race_result.get("predicted", [])
            if predicted and race_result.get("race_data", {}).get("entries"):
                entries = race_result["race_data"]["entries"]
                sorted_entries = sorted(
                    [e for e in entries if e.get("win_odds", 0) > 0],
                    key=lambda x: x["win_odds"],
                )
                odds_ranks = {
                    e["horse_no"]: i + 1 for i, e in enumerate(sorted_entries)
                }

                predicted_ranks = [odds_ranks.get(h, 99) for h in predicted]

                if all(r <= 3 for r in predicted_ranks):
                    analysis_note = "모두 인기마 선택"
                elif all(r >= 7 for r in predicted_ranks):
                    analysis_note = "인기마 무시"

        # 예시 생성
        example = Example(
            example_id=f"{race_result.get('race_id', 'unknown')}_{datetime.now().timestamp()}",
            example_type=example_type,
            race_id=race_result.get("race_id", ""),
            input_data=race_result.get("race_data", {}),
            predicted=race_result.get("predicted", []),
            actual=race_result.get("actual", []),
            confidence=race_result.get("confidence", 70),
            correct_count=race_result.get("reward", {}).get("correct_count", 0),
            analysis_note=analysis_note,
        )

        return example

    def add_examples_from_evaluation(
        self, evaluation_results: list[dict[str, Any]], limit: int | None = None
    ) -> int:
        """평가 결과에서 예시들 추가"""
        added_count = 0

        # 성공/실패 균형을 위해 각각 수집
        success_results = [
            r
            for r in evaluation_results
            if r.get("reward", {}).get("correct_count", 0) == 3
        ]
        failure_results = [
            r
            for r in evaluation_results
            if r.get("reward", {}).get("correct_count", 0) == 0
        ]

        # 성공 예시 추가
        for result in success_results[: limit // 2 if limit else None]:
            example = self.create_example_from_result(result, "success")
            self.example_pool.add_example(example)
            added_count += 1

        # 실패 예시 추가
        for result in failure_results[: limit // 2 if limit else None]:
            example = self.create_example_from_result(result, "failure")
            self.example_pool.add_example(example)
            added_count += 1

        return added_count

    def update_examples_section(
        self, prompt_structure, strategy: str = "balanced"
    ) -> list[str]:
        """프롬프트의 examples 섹션 업데이트"""
        # 최적 예시 선택
        selected_examples = self.curator.select_optimal_examples(
            target_count=4, strategy=strategy
        )

        # 섹션 내용 구성
        content_lines = []

        # 성공 사례
        success_examples = [e for e in selected_examples if e.example_type == "success"]
        if success_examples:
            content_lines.append("### 성공 사례\n")
            for example in success_examples:
                content_lines.append(example.to_prompt_format())
                content_lines.append("")

        # 실패 사례
        failure_examples = [e for e in selected_examples if e.example_type == "failure"]
        if failure_examples:
            content_lines.append("### 실패 사례 (피해야 할 패턴)\n")
            for example in failure_examples:
                content_lines.append(example.to_prompt_format())
                content_lines.append("")

        # 섹션 업데이트
        new_content = "\n".join(content_lines).strip()
        prompt_structure.update_section("examples", new_content)

        # 사용된 예시 ID 반환
        return [e.example_id for e in selected_examples]

    def track_usage_performance(
        self, example_ids: list[str], performance: float
    ) -> None:
        """예시 사용 성과 추적"""
        # 성과 기록
        self.performance_tracker.track_performance(example_ids, performance)

        # 예시별 점수 업데이트
        for example_id in example_ids:
            example = self.example_pool.get_example(example_id)
            if example:
                example.usage_count += 1
                example.performance_score = (
                    self.performance_tracker.get_average_performance(example_id)
                )

    def cleanup_low_performers(self, threshold: float = 0.3) -> int:
        """저성과 예시 정리"""
        removed_count = 0

        # 충분히 사용된 예시 중 저성과 찾기
        to_remove = []
        for example_id, example in self.example_pool.examples.items():
            if example.usage_count >= 3:  # 최소 3회 이상 사용
                avg_performance = self.performance_tracker.get_average_performance(
                    example_id
                )
                if avg_performance < threshold:
                    to_remove.append(example_id)

        # 제거
        for example_id in to_remove:
            if self.example_pool.remove_example(example_id):
                removed_count += 1

        return removed_count

    def get_statistics(self) -> dict[str, Any]:
        """예시 풀 통계"""
        return {
            "total_examples": len(self.example_pool.examples),
            "success_examples": len(self.example_pool.success_examples),
            "failure_examples": len(self.example_pool.failure_examples),
            "avg_performance": (
                sum(e.performance_score for e in self.example_pool.examples.values())
                / len(self.example_pool.examples)
                if self.example_pool.examples
                else 0
            ),
            "most_used": (
                max(
                    self.example_pool.examples.values(), key=lambda e: e.usage_count
                ).example_id
                if self.example_pool.examples
                else None
            ),
        }


# 테스트용 함수
if __name__ == "__main__":
    # 간단한 테스트
    manager = ExamplesManager()

    # 테스트 평가 결과
    test_results = [
        {
            "race_id": "test_1",
            "predicted": [1, 3, 5],
            "actual": [1, 3, 5],
            "confidence": 85,
            "reward": {"correct_count": 3},
            "race_data": {
                "entries": [
                    {"horse_no": 1, "win_odds": 2.5},
                    {"horse_no": 3, "win_odds": 4.2},
                    {"horse_no": 5, "win_odds": 8.1},
                ]
            },
        },
        {
            "race_id": "test_2",
            "predicted": [2, 4, 6],
            "actual": [1, 3, 5],
            "confidence": 70,
            "reward": {"correct_count": 0},
            "race_data": {
                "entries": [
                    {"horse_no": 2, "win_odds": 15.5},
                    {"horse_no": 4, "win_odds": 22.2},
                    {"horse_no": 6, "win_odds": 31.1},
                ]
            },
        },
    ]

    # 예시 추가
    added = manager.add_examples_from_evaluation(test_results)
    print(f"추가된 예시: {added}개")

    # 통계
    stats = manager.get_statistics()
    print(f"통계: {stats}")

    # 최적 예시 선택
    from prompt_parser import PromptStructure

    structure = PromptStructure()
    used_ids = manager.update_examples_section(structure, strategy="balanced")
    print(f"사용된 예시 ID: {used_ids}")
