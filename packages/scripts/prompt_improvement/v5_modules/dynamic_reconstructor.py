"""
동적 프롬프트 재구성 시스템

파싱된 프롬프트 구조와 인사이트 분석 결과를 바탕으로
개선된 프롬프트를 동적으로 생성합니다.
"""

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime

from .common_types import Change
from .insight_analyzer import InsightAnalysis, Recommendation
from .prompt_parser import (
    AnalysisStepsEditor,
    PromptStructure,
    RequirementsEditor,
)


@dataclass
class ChangeRecord:
    """변경 기록을 표현하는 클래스"""
    timestamp: datetime
    version_from: str
    version_to: str
    changes: list[Change]
    performance_before: float
    performance_after: float | None = None
    rollback_available: bool = True


class WeightOptimizer:
    """가중치 최적화 엔진"""

    def optimize_weights(
        self,
        current_weights: dict[str, float],
        analysis_results: InsightAnalysis
    ) -> tuple[dict[str, float], list[Change]]:
        """분석 결과를 기반으로 가중치 최적화"""
        new_weights = current_weights.copy()
        changes = []

        # 상관관계 분석 결과 활용
        _correlations = analysis_results.correlations

        # 가장 높은 상관관계를 가진 특성 찾기
        _feature_map = {
            "win_odds_rank": "odds",
            "jockey_win_rate": "jockey",
            "horse_place_rate": "horse"
        }

        # 현재 가중치 합계가 1이 되도록 정규화
        total_weight = sum(current_weights.values())
        if total_weight > 0:
            for key in current_weights:
                current_weights[key] /= total_weight

        # 권고사항에서 가중치 조정 찾기
        for rec in analysis_results.get_recommendations():
            if rec.type == "weight_adjustment" and rec.target in new_weights:
                old_value = new_weights[rec.target]

                if rec.action == "increase":
                    adjustment = rec.value if rec.value else 0.1
                    new_weights[rec.target] = min(0.7, old_value + adjustment)
                elif rec.action == "decrease":
                    adjustment = rec.value if rec.value else 0.1
                    new_weights[rec.target] = max(0.1, old_value - adjustment)

                # 다른 가중치 조정 (합이 1이 되도록)
                remaining = 1.0 - new_weights[rec.target]
                other_keys = [k for k in new_weights if k != rec.target]
                if other_keys:
                    for key in other_keys:
                        new_weights[key] = remaining / len(other_keys)

                changes.append(Change(
                    change_type="modify",
                    target_section="analysis_steps",
                    description=f"{rec.target} 가중치 조정: {old_value:.0%} → {new_weights[rec.target]:.0%}",
                    old_value=str(old_value),
                    new_value=str(new_weights[rec.target])
                ))

        return new_weights, changes


class RuleEngine:
    """규칙 관리 엔진"""

    def process_rule_recommendations(
        self,
        structure: PromptStructure,
        recommendations: list[Recommendation]
    ) -> list[Change]:
        """권고사항을 기반으로 규칙 처리"""
        changes = []
        req_editor = RequirementsEditor(structure)

        for rec in recommendations:
            if rec.type == "add_rule" and rec.target == "requirements":
                # 새 규칙 추가
                current_reqs = req_editor.get_requirements()

                # 중복 확인
                if rec.value and rec.value not in current_reqs:
                    req_editor.add_requirement(rec.value)
                    changes.append(Change(
                        change_type="add",
                        target_section="requirements",
                        description=f"새 규칙 추가: {rec.value}",
                        new_value=rec.value
                    ))

            elif rec.type == "strategy_change":
                # 전략 변경은 보통 analysis_steps나 important_notes에 반영
                if "popular_ratio" in rec.action:
                    # 인기마 비율 조정 전략
                    steps_editor = AnalysisStepsEditor(structure)
                    steps = steps_editor.get_steps()

                    # "상위 3마리 선정" 단계 찾기
                    for i, step in enumerate(steps):
                        if "상위 3마리 선정" in step:
                            new_step = f"상위 3마리 선정 ({rec.value} 균형 선택)"
                            steps_editor.modify_step(i, new_step)
                            changes.append(Change(
                                change_type="modify",
                                target_section="analysis_steps",
                                description=f"선정 전략 변경: {rec.value}",
                                old_value=step,
                                new_value=new_step
                            ))
                            break

        return changes


class SectionModifier:
    """섹션별 수정 전략"""

    def __init__(self):
        self.weight_optimizer = WeightOptimizer()
        self.rule_engine = RuleEngine()

    def modify_context(
        self,
        structure: PromptStructure,
        new_performance: dict[str, float]
    ) -> list[Change]:
        """context 섹션 수정"""
        changes = []
        section = structure.get_section("context")

        if section:
            # 성능 정보 업데이트
            pattern = r"평균 적중 [\d.]+마리.*?완전 적중률 [\d.]+%"
            new_text = f"평균 적중 {new_performance["avg_correct"]:.1f}마리, 완전 적중률 {new_performance["success_rate"]:.1f}%"

            new_content = re.sub(pattern, new_text, section.content)

            if new_content != section.content:
                structure.update_section("context", new_content)
                changes.append(Change(
                    change_type="modify",
                    target_section="context",
                    description="성능 정보 업데이트",
                    old_value=section.content,
                    new_value=new_content
                ))

        return changes

    def modify_analysis_steps(
        self,
        structure: PromptStructure,
        new_weights: dict[str, float]
    ) -> list[Change]:
        """analysis_steps 섹션의 가중치 업데이트"""
        changes = []
        section = structure.get_section("analysis_steps")

        if section:
            # 가중치 부분 찾아서 업데이트
            weight_pattern = r"(배당률.*?:)\s*(\d+)%(.*?기수.*?:)\s*(\d+)%(.*?말.*?:)\s*(\d+)%"

            replacement = (
                f"\\1 {int(new_weights.get("odds", 0.4) * 100)}%"
                f"\\3 {int(new_weights.get("jockey", 0.3) * 100)}%"
                f"\\5 {int(new_weights.get("horse", 0.3) * 100)}%"
            )

            new_content = re.sub(weight_pattern, replacement, section.content, flags=re.DOTALL)

            if new_content != section.content:
                structure.update_section("analysis_steps", new_content)
                changes.append(Change(
                    change_type="modify",
                    target_section="analysis_steps",
                    description="가중치 업데이트",
                    old_value=section.content,
                    new_value=new_content
                ))

        return changes


class ConflictResolver:
    """권고사항 충돌 해결"""

    def resolve_conflicts(self, recommendations: list[Recommendation]) -> list[Recommendation]:
        """상충되는 권고사항 해결"""
        resolved = []
        processed_targets = set()

        # 우선순위와 타입별로 정렬
        priority_order = {"high": 0, "medium": 1, "low": 2}
        sorted_recs = sorted(
            recommendations,
            key=lambda r: (priority_order.get(r.priority, 3), r.type)
        )

        for rec in sorted_recs:
            # 같은 대상에 대한 중복 권고 방지
            target_key = f"{rec.type}:{rec.target}"

            if target_key not in processed_targets:
                resolved.append(rec)
                processed_targets.add(target_key)
            else:
                # 충돌 발생 - 더 높은 우선순위의 권고가 이미 처리됨
                pass

        return resolved


class ChangeTracker:
    """변경사항 추적 시스템"""

    def __init__(self):
        self.history: list[ChangeRecord] = []

    def record_changes(
        self,
        version_from: str,
        version_to: str,
        changes: list[Change],
        performance_before: float
    ) -> ChangeRecord:
        """변경사항 기록"""
        record = ChangeRecord(
            timestamp=datetime.now(),
            version_from=version_from,
            version_to=version_to,
            changes=changes,
            performance_before=performance_before
        )

        self.history.append(record)
        return record

    def get_change_summary(self, record: ChangeRecord) -> str:
        """변경사항 요약"""
        summary = []
        summary.append(f"## 변경사항 요약 ({record.version_from} → {record.version_to})")
        summary.append(f"- 변경 시각: {record.timestamp.strftime("%Y-%m-%d %H:%M:%S")}")
        summary.append(f"- 이전 성능: {record.performance_before:.1f}%")
        if record.performance_after:
            summary.append(f"- 이후 성능: {record.performance_after:.1f}%")

        summary.append(f"\n### 변경 내역 ({len(record.changes)}건)")
        for change in record.changes:
            summary.append(f"- [{change.change_type}] {change.target_section}: {change.description}")

        return "\n".join(summary)


class DynamicReconstructor:
    """통합 동적 재구성 엔진"""

    def __init__(self):
        self.section_modifier = SectionModifier()
        self.conflict_resolver = ConflictResolver()
        self.change_tracker = ChangeTracker()
        self.aggressiveness = 0.3  # 한 번에 적용할 변경의 비율

        # 고급 기법 엔진 초기화 (lazy import to avoid circular dependency)
        from .extended_thinking import ExtendedThinkingEngine
        from .guide_loader import PromptEngineeringGuideLoader
        from .self_verification import SelfVerificationEngine
        from .token_optimizer import TokenOptimizationEngine

        self.guide_loader = PromptEngineeringGuideLoader()
        self.extended_thinking = ExtendedThinkingEngine()
        self.self_verification = SelfVerificationEngine()
        self.token_optimizer = TokenOptimizationEngine()

    def reconstruct_prompt(
        self,
        current_structure: PromptStructure,
        analysis_results: InsightAnalysis,
        new_version: str,
        current_performance: dict[str, float]
    ) -> tuple[PromptStructure, list[Change]]:
        """프롬프트 재구성 수행"""
        # 구조 복사 (원본 보존)
        modified_structure = deepcopy(current_structure)
        all_changes = []

        # 1. 권고사항 추출 및 충돌 해결
        recommendations = analysis_results.get_recommendations()
        resolved_recommendations = self.conflict_resolver.resolve_conflicts(recommendations)

        # 2. 점진적 적용 (상위 N개만 적용)
        to_apply = resolved_recommendations[:int(len(resolved_recommendations) * self.aggressiveness) + 1]

        # 3. 성능 정보 업데이트 (항상 적용)
        context_changes = self.section_modifier.modify_context(
            modified_structure,
            current_performance
        )
        all_changes.extend(context_changes)

        # 4. 가중치 최적화
        current_weights = self._extract_current_weights(modified_structure)
        new_weights, weight_changes = self.section_modifier.weight_optimizer.optimize_weights(
            current_weights,
            analysis_results
        )

        if weight_changes:
            steps_changes = self.section_modifier.modify_analysis_steps(
                modified_structure,
                new_weights
            )
            all_changes.extend(steps_changes)
            all_changes.extend(weight_changes)

        # 5. 규칙 처리
        rule_changes = self.section_modifier.rule_engine.process_rule_recommendations(
            modified_structure,
            to_apply
        )
        all_changes.extend(rule_changes)

        # 6. 고급 기법 적용
        current_success_rate = current_performance.get("success_rate", 0)

        # 6.1 Extended Thinking Mode
        if self.guide_loader.should_apply_technique("extended_thinking", current_success_rate):
            thinking_changes = self.extended_thinking.apply_extended_thinking(
                modified_structure,
                current_success_rate
            )
            all_changes.extend(thinking_changes)

            # 사고 검증 추가
            verification_changes = self.extended_thinking.add_thinking_verification(modified_structure)
            all_changes.extend(verification_changes)

        # 6.2 강화된 자가 검증
        if self.guide_loader.should_apply_technique("self_verification", current_success_rate):
            # 검증 섹션 추가
            verification_changes = self.self_verification.add_verification_section(modified_structure)
            all_changes.extend(verification_changes)

            # 출력 형식에 검증 필드 추가
            output_changes = self.self_verification.add_verification_to_output_format(modified_structure)
            all_changes.extend(output_changes)

            # 사후 검증 단계 추가
            post_verification_changes = self.self_verification.create_post_analysis_verification(modified_structure)
            all_changes.extend(post_verification_changes)

            # 오류 복구 가이드 추가
            recovery_changes = self.self_verification.add_error_recovery_guidance(modified_structure)
            all_changes.extend(recovery_changes)

        # 6.3 토큰 최적화 (항상 적용)
        if self.guide_loader.should_apply_technique("token_optimization", current_success_rate):
            # 기본 최적화
            _, token_changes = self.token_optimizer.optimize_prompt(modified_structure)
            all_changes.extend(token_changes)

            # 고급 압축 (성능이 안정적일 때만)
            if current_success_rate >= 65:
                compression_changes = self.token_optimizer.apply_advanced_compression(modified_structure)
                all_changes.extend(compression_changes)

        # 7. 버전 업데이트
        modified_structure.version = new_version

        # 8. 변경사항 기록
        if all_changes:
            self.change_tracker.record_changes(
                version_from=current_structure.version,
                version_to=new_version,
                changes=all_changes,
                performance_before=current_performance.get("success_rate", 0)
            )

        return modified_structure, all_changes

    def _extract_current_weights(self, structure: PromptStructure) -> dict[str, float]:
        """현재 가중치 추출"""
        weights = {"odds": 0.4, "jockey": 0.3, "horse": 0.3}  # 기본값

        section = structure.get_section("analysis_steps")
        if section:
            # 가중치 패턴 찾기
            pattern = r"배당률.*?(\d+)%.*?기수.*?(\d+)%.*?말.*?(\d+)%"
            match = re.search(pattern, section.content, re.DOTALL)

            if match:
                weights["odds"] = int(match.group(1)) / 100
                weights["jockey"] = int(match.group(2)) / 100
                weights["horse"] = int(match.group(3)) / 100

        return weights

    def validate_changes(self, structure: PromptStructure) -> list[str]:
        """변경사항 검증"""
        issues = []

        # 필수 섹션 확인
        required_sections = ["context", "role", "task", "requirements", "analysis_steps", "output_format"]
        for section in required_sections:
            if not structure.get_section(section):
                issues.append(f"필수 섹션 누락: {section}")

        # 가중치 합계 확인
        weights = self._extract_current_weights(structure)
        weight_sum = sum(weights.values())
        if abs(weight_sum - 1.0) > 0.01:
            issues.append(f"가중치 합계 오류: {weight_sum:.2f} (1.0이어야 함)")

        # JSON 형식 확인 (output_format)
        output_section = structure.get_section("output_format")
        if output_section:
            try:
                # JSON 블록 추출
                json_match = re.search(r"```json\n(.*?)\n```", output_section.content, re.DOTALL)
                if json_match:
                    json.loads(json_match.group(1))
            except json.JSONDecodeError:
                issues.append("output_format의 JSON 형식 오류")

        return issues

    def get_advanced_techniques_status(self, current_performance: float) -> dict[str, bool]:
        """고급 기법 적용 상태 조회"""
        return {
            "extended_thinking": self.guide_loader.should_apply_technique("extended_thinking", current_performance),
            "self_verification": self.guide_loader.should_apply_technique("self_verification", current_performance),
            "token_optimization": self.guide_loader.should_apply_technique("token_optimization", current_performance)
        }

    def generate_change_report(self) -> str:
        """전체 변경 이력 보고서 생성"""
        if not self.change_tracker.history:
            return "변경 이력이 없습니다."

        report = ["# 프롬프트 변경 이력\n"]

        for record in reversed(self.change_tracker.history):
            report.append(self.change_tracker.get_change_summary(record))
            report.append("\n---\n")

        return "\n".join(report)


# 테스트용 함수
if __name__ == "__main__":
    from .insight_analyzer import InsightAnalysis, Recommendation
    from .prompt_parser import PromptParser

    # 테스트 프롬프트
    test_prompt = """# 경마 삼복연승 예측 프롬프트 v2.1

<context>
한국 경마 데이터를 분석하여 1-3위에 들어올 3마리를 예측하는 작업입니다.
이전 버전 성능: 평균 적중 1.1마리, 완전 적중률 5.1%
</context>

<analysis_steps>
3. 복합 점수 계산:
   - 배당률 점수: 40%
   - 기수 성적: 30%
   - 말 성적: 30%
</analysis_steps>
"""

    # 파싱
    parser = PromptParser()
    structure = parser.parse(test_prompt)

    # 가짜 분석 결과
    analysis = InsightAnalysis()
    analysis.recommendations = [
        Recommendation(
            type="weight_adjustment",
            priority="high",
            description="배당률 가중치 상향",
            target="odds",
            action="increase",
            value=0.1
        )
    ]

    # 재구성
    reconstructor = DynamicReconstructor()
    new_structure, changes = reconstructor.reconstruct_prompt(
        structure,
        analysis,
        "v2.2",
        {"avg_correct": 1.5, "success_rate": 7.5}
    )

    print("변경사항:")
    for change in changes:
        print(f"- {change.description}")

    print("\n재구성된 프롬프트:")
    print(new_structure.to_prompt())
