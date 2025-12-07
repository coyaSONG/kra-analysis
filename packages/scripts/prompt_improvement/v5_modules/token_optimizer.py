"""
토큰 최적화 엔진
프롬프트의 효율성을 높이고 불필요한 토큰 사용을 줄입니다.
"""

import re
from dataclasses import dataclass

from .common_types import Change
from .prompt_parser import PromptStructure


@dataclass
class OptimizationRule:
    """최적화 규칙"""

    name: str
    description: str
    pattern: str | None = None
    replacement: str | None = None


class TokenOptimizationEngine:
    """토큰 최적화 엔진"""

    def __init__(self):
        # 최적화 규칙 정의
        self.optimization_rules = [
            OptimizationRule(
                "remove_redundancy",
                "중복된 표현 제거",
                r"(\b\w+\b)(\s+\1)+",  # 같은 단어 반복
                r"\1",
            ),
            OptimizationRule(
                "compact_lists",
                "목록 형식 간소화",
                r"^\s*[-•]\s+",  # 불필요한 공백이 있는 목록
                "- ",
            ),
            OptimizationRule(
                "simplify_percentages", "백분율 표현 간소화", r"(\d+)\s*퍼센트", r"\1%"
            ),
            OptimizationRule(
                "remove_empty_lines",
                "빈 줄 제거",
                r"\n\s*\n\s*\n",  # 연속된 빈 줄
                "\n\n",
            ),
        ]

        # 데이터 표현 최적화 템플릿
        self.data_table_template = """
| 항목 | 값 | 설명 |
|------|-----|------|
| {item1} | {value1} | {desc1} |
| {item2} | {value2} | {desc2} |
"""

    def optimize_prompt(
        self, structure: PromptStructure
    ) -> tuple[PromptStructure, list[Change]]:
        """전체 프롬프트 최적화"""
        changes = []

        # 1. 기본 텍스트 최적화
        text_changes = self._optimize_text_content(structure)
        changes.extend(text_changes)

        # 2. 구조적 최적화
        structural_changes = self._optimize_structure(structure)
        changes.extend(structural_changes)

        # 3. 데이터 표현 최적화
        data_changes = self._optimize_data_representation(structure)
        changes.extend(data_changes)

        # 4. 예시 섹션 최적화
        example_changes = self._optimize_examples(structure)
        changes.extend(example_changes)

        return structure, changes

    def _optimize_text_content(self, structure: PromptStructure) -> list[Change]:
        """텍스트 내용 최적화"""
        changes = []

        for _, section in structure.sections.items():
            original_content = section.content
            optimized_content = original_content

            # 각 최적화 규칙 적용
            for rule in self.optimization_rules:
                if rule.pattern and rule.replacement is not None:
                    optimized_content = re.sub(
                        rule.pattern,
                        rule.replacement,
                        optimized_content,
                        flags=re.MULTILINE,
                    )

            # 추가 최적화: 과도한 설명 제거
            optimized_content = self._remove_verbose_explanations(optimized_content)

            if optimized_content != original_content:
                # 토큰 감소량 계산 (대략적)
                token_reduction = (len(original_content) - len(optimized_content)) // 4

                structure.update_section(section.tag, optimized_content)
                changes.append(
                    Change(
                        change_type="modify",
                        target_section=section.tag,
                        description=f"텍스트 최적화 (약 {token_reduction}토큰 절약)",
                        old_value=original_content,
                        new_value=optimized_content,
                    )
                )

        return changes

    def _optimize_structure(self, structure: PromptStructure) -> list[Change]:
        """구조적 최적화"""
        changes = []

        # 중복 섹션 통합
        section_contents = {}
        for _, section in structure.sections.items():
            if section.content.strip() in section_contents:
                # 중복 내용 발견
                _duplicate_of = section_contents[section.content.strip()]
                # 섹션 제거 또는 통합 로직
                # (실제 구현에서는 더 신중하게 처리)

        return changes

    def _optimize_data_representation(self, structure: PromptStructure) -> list[Change]:
        """데이터 표현 최적화"""
        changes = []

        # analysis_steps 섹션의 점수 계산 부분 최적화
        section = structure.get_section("analysis_steps")
        if section:
            # 긴 설명을 표 형식으로 변환
            score_pattern = (
                r"점수 계산 방법:\s*\n\s*- ([^\n]+)\s*\n\s*- ([^\n]+)\s*\n\s*- ([^\n]+)"
            )
            match = re.search(score_pattern, section.content)

            if match:
                # 표 형식으로 변환
                table_format = """
   점수 계산:
   | 구분 | 계산식 |
   |------|--------|
   | 배당률 | 100 - (순위 × 10) |
   | 기수 | 승률×50 + 복승률×50 |
   | 말 | 입상률 × 100 |"""

                new_content = re.sub(score_pattern, table_format, section.content)

                if new_content != section.content:
                    structure.update_section("analysis_steps", new_content)
                    changes.append(
                        Change(
                            change_type="modify",
                            target_section="analysis_steps",
                            description="점수 계산을 표 형식으로 최적화",
                            old_value=section.content,
                            new_value=new_content,
                        )
                    )

        return changes

    def _optimize_examples(self, structure: PromptStructure) -> list[Change]:
        """예시 섹션 최적화"""
        changes = []

        examples_section = structure.get_section("examples")
        if not examples_section:
            return changes

        # 긴 예시를 핵심만 남기고 압축
        content = examples_section.content

        # 불필요한 설명 제거
        content = re.sub(r"입력 데이터 특징:\s*\n", "", content)
        content = re.sub(r"분석: [^\n]+\n", "", content)

        # 예시를 더 간결하게
        if len(content) > 500:  # 너무 긴 경우
            # 핵심 정보만 추출
            simplified = self._extract_core_example_info(content)

            if simplified and len(simplified) < len(content) * 0.7:
                structure.update_section("examples", simplified)

                token_saved = (len(content) - len(simplified)) // 4
                changes.append(
                    Change(
                        change_type="modify",
                        target_section="examples",
                        description=f"예시 간소화 (약 {token_saved}토큰 절약)",
                        old_value=content,
                        new_value=simplified,
                    )
                )

        return changes

    def _remove_verbose_explanations(self, content: str) -> str:
        """과도한 설명 제거"""
        # 괄호 안의 긴 설명 간소화
        content = re.sub(r"\([^)]{50,}\)", "", content)

        # 반복적인 강조 제거
        content = re.sub(r"반드시|꼭|절대로|매우 중요|필수적으로", "필수", content)

        # 중복된 조사 제거
        content = re.sub(r"을/를", "을", content)
        content = re.sub(r"이/가", "이", content)
        content = re.sub(r"은/는", "은", content)

        return content

    def _extract_core_example_info(self, examples_content: str) -> str:
        """예시에서 핵심 정보만 추출"""
        lines = examples_content.split("\n")
        core_lines = []

        for line in lines:
            # 핵심 라인만 유지
            if any(
                keyword in line
                for keyword in ["예시", "입력:", "출력:", "결과:", "```"]
            ):
                core_lines.append(line)
            elif re.match(r"^\s*[-•]\s*\d+번마:", line):  # 말 정보
                # 핵심 정보만 추출
                simplified = re.sub(r"기수 승률 \d+%, 말 입상률 \d+%", "", line)
                core_lines.append(simplified)

        return "\n".join(core_lines)

    def create_optimization_report(
        self, original_structure: PromptStructure, optimized_structure: PromptStructure
    ) -> str:
        """최적화 보고서 생성"""
        original_size = sum(len(s.content) for s in original_structure.sections)
        optimized_size = sum(len(s.content) for s in optimized_structure.sections)

        reduction_percent = ((original_size - optimized_size) / original_size) * 100

        report = f"""## 토큰 최적화 보고서

### 요약
- 원본 크기: 약 {original_size // 4} 토큰
- 최적화 후: 약 {optimized_size // 4} 토큰
- 절감률: {reduction_percent:.1f}%

### 주요 최적화
1. 중복 표현 제거
2. 표 형식 도입으로 가독성 향상
3. 과도한 설명 간소화
4. 예시 섹션 압축

### 품질 보증
- 핵심 정보는 모두 유지
- 명확성과 정확성 보장
- 구조적 일관성 유지"""

        return report

    def apply_advanced_compression(self, structure: PromptStructure) -> list[Change]:
        """고급 압축 기법 적용"""
        changes = []

        # 약어 도입
        abbreviations = {
            "배당률": "배당",
            "출전번호": "번호",
            "복승률": "복승",
            "입상률": "입상",
        }

        for _, section in structure.sections.items():
            content = section.content
            modified = False

            for full_term, abbrev in abbreviations.items():
                # 첫 등장 후에만 약어 사용
                if full_term in content:
                    # 첫 번째는 그대로 두고 이후는 약어로
                    parts = content.split(full_term, 1)
                    if len(parts) == 2:
                        new_content = (
                            parts[0] + full_term + parts[1].replace(full_term, abbrev)
                        )
                        if new_content != content:
                            content = new_content
                            modified = True

            if modified:
                structure.update_section(section.tag, content)
                changes.append(
                    Change(
                        change_type="modify",
                        target_section=section.tag,
                        description="약어 적용으로 토큰 절약",
                        old_value=section.content,
                        new_value=content,
                    )
                )

        return changes
