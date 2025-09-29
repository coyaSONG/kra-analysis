"""
Extended Thinking Mode 구현
프롬프트에 사고 확장 키워드를 추가하여 더 깊은 분석을 유도합니다.
"""

from dataclasses import dataclass

from .common_types import Change
from .prompt_parser import PromptStructure


@dataclass
class ThinkingLevel:
    """사고 레벨 정의"""

    keyword: str
    description: str
    priority: int  # 1-4 (높을수록 강함)


class ExtendedThinkingEngine:
    """Extended Thinking Mode 엔진"""

    def __init__(self):
        # 사고 레벨 정의
        self.thinking_levels = [
            ThinkingLevel("think", "기본 수준의 추가 사고 시간", 1),
            ThinkingLevel("think hard", "중간 수준의 추가 사고 시간", 2),
            ThinkingLevel("think harder", "높은 수준의 추가 사고 시간", 3),
            ThinkingLevel("ultrathink", "최대 수준의 추가 사고 시간", 4),
        ]

        # 성능별 권장 레벨
        self.performance_thresholds = {
            40: 4,  # 40% 미만: ultrathink
            50: 3,  # 40-50%: think harder
            60: 2,  # 50-60%: think hard
            70: 1,  # 60-70%: think
            100: 0,  # 70% 이상: 불필요
        }

    def determine_thinking_level(
        self, current_performance: float
    ) -> ThinkingLevel | None:
        """현재 성능에 따른 적절한 사고 레벨 결정"""
        for threshold, level_priority in sorted(self.performance_thresholds.items()):
            if current_performance < threshold:
                if level_priority > 0:
                    return self.thinking_levels[level_priority - 1]
                return None
        return None

    def apply_extended_thinking(
        self,
        structure: PromptStructure,
        current_performance: float,
        target_sections: list[str] = None,
    ) -> list[Change]:
        """프롬프트에 Extended Thinking 적용"""
        changes = []

        # 적용할 사고 레벨 결정
        thinking_level = self.determine_thinking_level(current_performance)
        if not thinking_level:
            return changes

        # 기본 대상 섹션
        if not target_sections:
            target_sections = ["task", "analysis_steps"]

        for section_name in target_sections:
            section = structure.get_section(section_name)
            if not section:
                continue

            # 이미 thinking 키워드가 있는지 확인
            if self._has_thinking_keyword(section.content):
                continue

            # 섹션별 적용 전략
            new_content = self._inject_thinking_keyword(
                section.content, section_name, thinking_level
            )

            if new_content != section.content:
                structure.update_section(section_name, new_content)
                changes.append(
                    Change(
                        change_type="modify",
                        target_section=section_name,
                        description=f"Extended Thinking Mode 적용: {thinking_level.keyword}",
                        old_value=section.content,
                        new_value=new_content,
                    )
                )

        return changes

    def _has_thinking_keyword(self, content: str) -> bool:
        """이미 thinking 키워드가 있는지 확인"""
        keywords = [level.keyword for level in self.thinking_levels]
        return any(keyword in content.lower() for keyword in keywords)

    def _inject_thinking_keyword(
        self, content: str, section_name: str, thinking_level: ThinkingLevel
    ) -> str:
        """섹션에 thinking 키워드 주입"""
        if section_name == "task":
            # 작업 설명에 추가
            lines = content.strip().split("\n")
            if lines:
                lines[
                    0
                ] += f" Please {thinking_level.keyword} about all aspects of this prediction task."
            return "\n".join(lines)

        elif section_name == "analysis_steps":
            # 분석 단계에 추가
            intro = f"Please {thinking_level.keyword} through each step carefully:\n\n"
            return intro + content

        elif section_name == "requirements":
            # 요구사항에 추가
            outro = f"\n\nWhen applying these requirements, {thinking_level.keyword} about edge cases and unusual patterns."
            return content + outro

        else:
            # 기타 섹션: 끝에 추가
            return (
                content
                + f"\n\n{thinking_level.keyword.capitalize()} deeply about this section."
            )

    def add_thinking_verification(self, structure: PromptStructure) -> list[Change]:
        """사고 과정 검증 단계 추가"""
        changes = []

        # 분석 단계에 검증 추가
        section = structure.get_section("analysis_steps")
        if section:
            verification_step = """
6. **사고 과정 검증**
   - 각 단계에서 놓친 부분이 없는지 재검토
   - 가정이나 추론의 논리적 오류 확인
   - 극단적 케이스나 예외 상황 고려
   - 최종 결정의 일관성 검증"""

            if "사고 과정 검증" not in section.content:
                new_content = section.content.rstrip() + "\n" + verification_step
                structure.update_section("analysis_steps", new_content)

                changes.append(
                    Change(
                        change_type="modify",
                        target_section="analysis_steps",
                        description="사고 과정 검증 단계 추가",
                        old_value=section.content,
                        new_value=new_content,
                    )
                )

        return changes

    def create_thinking_notes(self, current_performance: float) -> str:
        """성능에 따른 사고 노트 생성"""
        level = self.determine_thinking_level(current_performance)

        if not level:
            return ""

        notes = f"""<thinking_guidance>
현재 성능: {current_performance:.1f}%
권장 사고 수준: {level.keyword} ({level.description})

주의 사항:
- 배당률과 실력 지표 간의 미묘한 상관관계 파악
- 최근 성적 트렌드의 급격한 변화 감지
- 경주 거리와 날씨가 미치는 영향 고려
- 기수-말 궁합과 과거 협력 성과 분석
</thinking_guidance>"""

        return notes

    def optimize_for_performance(
        self, structure: PromptStructure, performance_history: list[float]
    ) -> list[Change]:
        """성능 이력을 기반으로 최적화"""
        changes = []

        if not performance_history:
            return changes

        # 성능 추세 분석
        recent_performance = (
            performance_history[-3:]
            if len(performance_history) >= 3
            else performance_history
        )
        avg_recent = sum(recent_performance) / len(recent_performance)

        # 성능이 정체되어 있으면 더 강한 사고 모드 적용
        if len(set(recent_performance)) == 1:  # 모두 같은 값
            # 정체 상태 - 한 단계 높은 사고 레벨 적용
            current_level = self.determine_thinking_level(avg_recent)
            if current_level and current_level.priority < 4:
                next_level = self.thinking_levels[current_level.priority]  # 다음 레벨

                # 특별 지시 추가
                special_instruction = f"\n\n<stagnation_breaker>\n성능이 {avg_recent:.1f}%에서 정체되어 있습니다.\n{next_level.keyword}를 통해 새로운 패턴과 인사이트를 발견하세요.\n</stagnation_breaker>"

                section = structure.get_section("task")
                if section:
                    new_content = section.content + special_instruction
                    structure.update_section("task", new_content)

                    changes.append(
                        Change(
                            change_type="modify",
                            target_section="task",
                            description=f"정체 돌파를 위한 {next_level.keyword} 적용",
                            old_value=section.content,
                            new_value=new_content,
                        )
                    )

        return changes
