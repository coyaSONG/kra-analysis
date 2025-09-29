"""
강화된 자가 검증 시스템
예측 결과의 정확성을 높이기 위한 다단계 검증 프로세스를 구현합니다.
"""

from dataclasses import dataclass

from .common_types import Change
from .prompt_parser import PromptSection, PromptStructure


@dataclass
class VerificationRule:
    """검증 규칙"""

    name: str
    description: str
    check_type: str  # "constraint", "consistency", "quality"
    error_message: str


class SelfVerificationEngine:
    """강화된 자가 검증 엔진"""

    def __init__(self):
        # 검증 규칙 정의
        self.verification_rules = [
            VerificationRule(
                "horse_count",
                "정확히 3마리 선택 확인",
                "constraint",
                "선택한 말이 3마리가 아닙니다",
            ),
            VerificationRule(
                "valid_horses",
                "모든 말의 winOdds > 0 확인",
                "constraint",
                "기권/제외 말이 포함되어 있습니다",
            ),
            VerificationRule(
                "popularity_balance",
                "인기도 균형 확인 (모두 인기마/비인기마 방지)",
                "quality",
                "극단적인 선택입니다",
            ),
            VerificationRule(
                "confidence_range",
                "confidence 값 60-90 범위 확인",
                "constraint",
                "confidence 값이 범위를 벗어났습니다",
            ),
            VerificationRule(
                "data_utilization",
                "enriched 데이터 활용 확인",
                "quality",
                "중요한 데이터를 놓쳤을 수 있습니다",
            ),
        ]

        # 검증 단계 템플릿
        self.verification_template = """
<verification_process>
예측 완료 후 다음 검증을 수행하세요:

1. **제약 조건 검증**
   - [ ] 정확히 3마리를 선택했는가?
   - [ ] 모든 선택 말의 winOdds > 0인가?
   - [ ] confidence가 60-90 범위인가?

2. **일관성 검증**
   - [ ] 선택 이유와 실제 선택이 일치하는가?
   - [ ] 분석 단계의 점수와 최종 선택이 일치하는가?

3. **품질 검증**
   - [ ] 배당률 1-3위 중 최소 1마리 포함되었는가?
   - [ ] 극단적 선택(모두 인기마/비인기마)을 피했는가?
   - [ ] 기수와 말의 주요 지표를 고려했는가?

검증 실패 시: 해당 단계로 돌아가 재분석하세요.
</verification_process>"""

    def add_verification_section(self, structure: PromptStructure) -> list[Change]:
        """검증 섹션 추가"""
        changes = []

        # 기존 검증 섹션 확인
        verification_section = structure.get_section("verification")

        if not verification_section:
            # 새 섹션 추가
            section = PromptSection(
                tag="verification", content=self.verification_template.strip()
            )
            structure.sections["verification"] = section

            changes.append(
                Change(
                    change_type="add",
                    target_section="verification",
                    description="강화된 자가 검증 섹션 추가",
                    new_value=self.verification_template.strip(),
                )
            )
        else:
            # 기존 섹션 업데이트
            if "verification_process" not in verification_section.content:
                new_content = (
                    verification_section.content + "\n\n" + self.verification_template
                )
                structure.update_section("verification", new_content)

                changes.append(
                    Change(
                        change_type="modify",
                        target_section="verification",
                        description="검증 프로세스 강화",
                        old_value=verification_section.content,
                        new_value=new_content,
                    )
                )

        return changes

    def add_verification_to_output_format(
        self, structure: PromptStructure
    ) -> list[Change]:
        """출력 형식에 검증 결과 추가"""
        changes = []

        output_section = structure.get_section("output_format")
        if not output_section:
            return changes

        # 검증 필드가 이미 있는지 확인
        if "verification_passed" in output_section.content:
            return changes

        # JSON 형식 찾기 및 수정
        import re

        json_pattern = r"```json\s*(\{[^`]+\})\s*```"
        match = re.search(json_pattern, output_section.content)

        if match:
            # 새로운 필드 추가
            enhanced_format = """반드시 아래 JSON 형식으로만 응답하세요:
```json
{
  "predicted": [출전번호1, 출전번호2, 출전번호3],
  "confidence": 75,
  "brief_reason": "인기마 중심, 기수 능력 우수",
  "verification_passed": true,
  "verification_notes": "모든 검증 통과"
}
```

필수 규칙:
- predicted: 정확히 3개의 출전번호(chulNo) 배열
- confidence: 60-90 사이의 정수
- brief_reason: 20자 이내 한글 설명
- verification_passed: 검증 통과 여부 (true/false)
- verification_notes: 검증 결과 요약 (10자 이내)"""

            structure.update_section("output_format", enhanced_format)

            changes.append(
                Change(
                    change_type="modify",
                    target_section="output_format",
                    description="출력 형식에 검증 필드 추가",
                    old_value=output_section.content,
                    new_value=enhanced_format,
                )
            )

        return changes

    def create_post_analysis_verification(
        self, structure: PromptStructure
    ) -> list[Change]:
        """분석 후 검증 단계 추가"""
        changes = []

        analysis_section = structure.get_section("analysis_steps")
        if not analysis_section:
            return changes

        # 이미 사후 검증이 있는지 확인
        if "사후 검증" in analysis_section.content:
            return changes

        # 검증 단계 추가
        post_verification = """

6. **사후 검증 (Post-Analysis Verification)**
   선택한 3마리에 대해:

   a) 논리적 일관성 확인
      - 분석 과정과 최종 선택이 일치하는가?
      - 선택 이유가 데이터로 뒷받침되는가?

   b) 위험 요소 재확인
      - 극단적 비인기마(10위 이하) 포함 시 명확한 근거가 있는가?
      - 모든 말이 한 가지 특성(예: 모두 선행마)에 치우치지 않았는가?

   c) 놓친 요소 점검
      - 중요한 enriched 데이터를 간과하지 않았는가?
      - 최근 급격한 성적 변화를 놓치지 않았는가?

   검증 실패 시: 3단계(복합 점수 계산)로 돌아가 재평가"""

        new_content = analysis_section.content.rstrip() + post_verification
        structure.update_section("analysis_steps", new_content)

        changes.append(
            Change(
                change_type="modify",
                target_section="analysis_steps",
                description="사후 검증 단계 추가",
                old_value=analysis_section.content,
                new_value=new_content,
            )
        )

        return changes

    def add_error_recovery_guidance(self, structure: PromptStructure) -> list[Change]:
        """오류 복구 가이드 추가"""
        changes = []

        # important_notes 섹션에 추가
        notes_section = structure.get_section("important_notes")
        if not notes_section:
            return changes

        error_recovery = """
- 검증 실패 시: 즉시 해당 분석 단계로 돌아가 재평가하세요
- 3번 이상 검증 실패 시: 보수적 접근(인기 1-5위 중심)으로 전환하세요
- 데이터 불일치 발견 시: enriched 데이터를 재확인하세요"""

        if "검증 실패 시" not in notes_section.content:
            new_content = notes_section.content.rstrip() + error_recovery
            structure.update_section("important_notes", new_content)

            changes.append(
                Change(
                    change_type="modify",
                    target_section="important_notes",
                    description="오류 복구 가이드 추가",
                    old_value=notes_section.content,
                    new_value=new_content,
                )
            )

        return changes

    def create_verification_checklist(self, performance_level: float) -> str:
        """성능 수준별 검증 체크리스트 생성"""
        if performance_level < 50:
            # 낮은 성능 - 엄격한 검증
            checklist = """<strict_verification>
낮은 성능 감지 - 강화된 검증 필요:
1. 배당률 1-3위 중 최소 2마리 포함 확인
2. 기수 승률 15% 이상인 말 우선 고려
3. 극단적 선택 절대 금지
4. 모든 enriched 데이터 필수 확인
</strict_verification>"""
        elif performance_level < 65:
            # 중간 성능 - 균형잡힌 검증
            checklist = """<balanced_verification>
중간 성능 - 균형잡힌 검증:
1. 인기마와 중위권 말의 적절한 조합
2. 특별한 강점이 있는 비인기마 1마리까지 허용
3. 기수-말 조합의 시너지 효과 확인
</balanced_verification>"""
        else:
            # 높은 성능 - 유연한 검증
            checklist = """<flexible_verification>
높은 성능 - 유연한 검증:
1. 현재 전략 유지하되 미세 조정
2. 새로운 패턴 탐색 허용
3. 데이터 기반 과감한 선택 가능
</flexible_verification>"""

        return checklist

    def integrate_with_analysis_flow(self, structure: PromptStructure) -> list[Change]:
        """분석 흐름에 검증 통합"""
        changes = []

        # 각 주요 단계에 미니 검증 추가
        sections_to_modify = ["requirements", "analysis_steps"]

        for section_name in sections_to_modify:
            section = structure.get_section(section_name)
            if not section:
                continue

            if section_name == "requirements":
                # 요구사항에 검증 관련 추가
                verification_req = "\n4. 각 분석 단계마다 중간 검증 수행"

                if "중간 검증" not in section.content:
                    new_content = section.content.rstrip() + verification_req
                    structure.update_section(section_name, new_content)

                    changes.append(
                        Change(
                            change_type="modify",
                            target_section=section_name,
                            description="중간 검증 요구사항 추가",
                            old_value=section.content,
                            new_value=new_content,
                        )
                    )

        return changes
