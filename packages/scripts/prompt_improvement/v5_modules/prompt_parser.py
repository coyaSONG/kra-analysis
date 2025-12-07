"""
프롬프트 파싱 및 구조화 시스템

XML 태그 기반으로 프롬프트를 파싱하고 구조화하여
각 섹션을 독립적으로 수정할 수 있게 합니다.
"""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PromptSection:
    """프롬프트의 개별 섹션을 표현하는 클래스"""

    tag: str  # "context", "role", "task" 등
    content: str  # 섹션 내용
    attributes: dict[str, Any] = field(default_factory=dict)  # 추가 속성
    order: int = 0  # 원본에서의 순서

    def __str__(self):
        return f"<{self.tag}>\n{self.content}\n</{self.tag}>"


@dataclass
class PromptStructure:
    """파싱된 프롬프트 전체 구조를 표현하는 클래스"""

    title: str = ""  # 프롬프트 제목
    version: str = ""  # 버전 정보
    sections: dict[str, PromptSection] = field(default_factory=dict)  # 태그별 섹션
    metadata: dict[str, Any] = field(default_factory=dict)  # 메타데이터

    def get_section(self, tag: str) -> PromptSection | None:
        """특정 태그의 섹션 반환"""
        return self.sections.get(tag)

    def update_section(self, tag: str, content: str) -> None:
        """특정 섹션의 내용 업데이트"""
        if tag in self.sections:
            self.sections[tag].content = content
        else:
            # 새 섹션 추가
            order = len(self.sections)
            self.sections[tag] = PromptSection(tag=tag, content=content, order=order)

    def add_section(self, tag: str, content: str, order: int | None = None) -> None:
        """새 섹션 추가"""
        if order is None:
            order = len(self.sections)
        self.sections[tag] = PromptSection(tag=tag, content=content, order=order)

    def remove_section(self, tag: str) -> bool:
        """섹션 제거"""
        if tag in self.sections:
            del self.sections[tag]
            return True
        return False

    def to_prompt(self) -> str:
        """구조를 다시 프롬프트 텍스트로 변환"""
        # 제목과 버전
        lines = []
        if self.title:
            lines.append(f"# {self.title}")
            lines.append("")

        # 섹션들을 순서대로 정렬
        sorted_sections = sorted(self.sections.values(), key=lambda s: s.order)

        # 각 섹션 추가
        for section in sorted_sections:
            lines.append(str(section))
            lines.append("")

        return "\n".join(lines).strip()


class PromptParser:
    """프롬프트 파싱 엔진"""

    # 인식 가능한 XML 태그들 (실제 프롬프트에서 사용되는 태그 포함)
    RECOGNIZED_TAGS = [
        # 기존 태그
        "context",
        "role",
        "task",
        "requirements",
        "analysis_steps",
        "output_format",
        "examples",
        "important_notes",
        # 실제 프롬프트에서 사용되는 태그
        "system_role",
        "data_spec",
        "analysis_protocol",
        "reasoning_rules",
        "scoring_caps",
        "few_shot_example",
        "user_input_placeholder",
    ]

    def __init__(self):
        self.tag_pattern = re.compile(r"<(\w+)>(.*?)</\1>", re.DOTALL)
        self.title_pattern = re.compile(r"^#\s+(.+?)(?:\s+v([\d.]+))?$", re.MULTILINE)

    def parse(self, content: str) -> PromptStructure:
        """프롬프트 텍스트를 구조화된 형태로 파싱"""
        structure = PromptStructure()

        # 1. 제목과 버전 추출
        title_match = self.title_pattern.search(content)
        if title_match:
            structure.title = title_match.group(1)
            if title_match.group(2):
                structure.version = f"v{title_match.group(2)}"

        # 2. XML 태그 기반 섹션 파싱
        for i, match in enumerate(self.tag_pattern.finditer(content)):
            tag = match.group(1)
            section_content = match.group(2).strip()

            if tag in self.RECOGNIZED_TAGS:
                # 특수 섹션 처리
                if tag == "examples":
                    section_content = self._parse_examples(section_content)
                elif tag == "requirements":
                    section_content = self._parse_requirements(section_content)
                elif tag == "analysis_steps":
                    section_content = self._parse_analysis_steps(section_content)

                structure.add_section(tag, section_content, order=i)

        # 3. 메타데이터 추출
        structure.metadata = self._extract_metadata(content)

        return structure

    def _parse_examples(self, content: str) -> str:
        """examples 섹션을 구조화된 형태로 파싱"""
        # 성공/실패 사례를 분리하여 저장
        # 현재는 원본 텍스트를 그대로 유지
        return content

    def _parse_requirements(self, content: str) -> str:
        """requirements 섹션을 구조화된 형태로 파싱"""
        # 번호 목록을 개별 항목으로 분리 가능
        # 현재는 원본 텍스트를 그대로 유지
        return content

    def _parse_analysis_steps(self, content: str) -> str:
        """analysis_steps 섹션을 구조화된 형태로 파싱"""
        # 단계별 프로세스를 리스트로 관리 가능
        # 현재는 원본 텍스트를 그대로 유지
        return content

    def _extract_metadata(self, content: str) -> dict[str, Any]:
        """프롬프트에서 메타데이터 추출"""
        metadata = {}

        # 성능 정보 추출 (예: "평균 적중 1.1마리, 완전 적중률 5.1%")
        perf_pattern = r"평균 적중 ([\d.]+)마리.*?완전 적중률 ([\d.]+)%"
        perf_match = re.search(perf_pattern, content)
        if perf_match:
            metadata["avg_correct"] = float(perf_match.group(1))
            metadata["success_rate"] = float(perf_match.group(2))

        # 가중치 정보 추출
        weight_pattern = r"배당률.*?(\d+)%.*?기수.*?(\d+)%.*?말.*?(\d+)%"
        weight_match = re.search(weight_pattern, content, re.DOTALL)
        if weight_match:
            metadata["weights"] = {
                "odds": int(weight_match.group(1)) / 100,
                "jockey": int(weight_match.group(2)) / 100,
                "horse": int(weight_match.group(3)) / 100,
            }

        return metadata


class RequirementsEditor:
    """Requirements 섹션 편집 도구"""

    def __init__(self, structure: PromptStructure):
        self.structure = structure

    def get_requirements(self) -> list[str]:
        """요구사항 목록 반환"""
        section = self.structure.get_section("requirements")
        if not section:
            return []

        # 번호가 있는 항목들 추출
        pattern = r"^\d+\.\s+(.+?)$"
        requirements = re.findall(pattern, section.content, re.MULTILINE)
        return requirements

    def add_requirement(self, requirement: str, position: int | None = None) -> None:
        """새 요구사항 추가"""
        requirements = self.get_requirements()

        if position is None:
            requirements.append(requirement)
        else:
            requirements.insert(position, requirement)

        # 다시 번호를 매겨서 저장
        new_content = "\n".join(f"{i+1}. {req}" for i, req in enumerate(requirements))
        self.structure.update_section("requirements", new_content)

    def remove_requirement(self, index: int) -> bool:
        """요구사항 제거"""
        requirements = self.get_requirements()
        if 0 <= index < len(requirements):
            requirements.pop(index)
            new_content = "\n".join(
                f"{i+1}. {req}" for i, req in enumerate(requirements)
            )
            self.structure.update_section("requirements", new_content)
            return True
        return False

    def update_requirement(self, index: int, new_text: str) -> bool:
        """요구사항 수정"""
        requirements = self.get_requirements()
        if 0 <= index < len(requirements):
            requirements[index] = new_text
            new_content = "\n".join(
                f"{i+1}. {req}" for i, req in enumerate(requirements)
            )
            self.structure.update_section("requirements", new_content)
            return True
        return False


class AnalysisStepsEditor:
    """Analysis Steps 섹션 편집 도구"""

    def __init__(self, structure: PromptStructure):
        self.structure = structure

    def get_steps(self) -> list[str]:
        """분석 단계 목록 반환"""
        section = self.structure.get_section("analysis_steps")
        if not section:
            return []

        # 번호가 있는 단계들 추출
        pattern = r"^\d+\.\s+(.+?)(?=^\d+\.|$)"
        steps = re.findall(pattern, section.content, re.MULTILINE | re.DOTALL)
        return [step.strip() for step in steps]

    def insert_step(self, position: int, step: str) -> None:
        """새 분석 단계 삽입"""
        steps = self.get_steps()
        steps.insert(position, step)

        # 다시 번호를 매겨서 저장
        new_content = "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps))
        self.structure.update_section("analysis_steps", new_content)

    def modify_step(self, index: int, new_step: str) -> bool:
        """분석 단계 수정"""
        steps = self.get_steps()
        if 0 <= index < len(steps):
            steps[index] = new_step
            new_content = "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps))
            self.structure.update_section("analysis_steps", new_content)
            return True
        return False


# 테스트용 함수
if __name__ == "__main__":
    # 간단한 테스트
    test_prompt = """# 경마 삼복연승 예측 프롬프트 v2.1

<context>
한국 경마 데이터를 분석하여 1-3위에 들어올 3마리를 예측하는 작업입니다.
이전 버전 성능: 평균 적중 1.1마리, 완전 적중률 5.1%
</context>

<role>
당신은 10년 이상의 경험을 가진 한국 경마 예측 전문가입니다.
</role>

<task>
제공된 경주 데이터를 분석하여 1-3위에 들어올 가능성이 가장 높은 3마리를 예측하세요.
</task>

<requirements>
1. 기권/제외(win_odds=0) 말은 반드시 제외
2. enriched 데이터의 모든 정보 활용
3. 다음 요소들을 종합적으로 고려
</requirements>
"""

    parser = PromptParser()
    structure = parser.parse(test_prompt)

    print(f"Title: {structure.title}")
    print(f"Version: {structure.version}")
    print(f"Sections: {list(structure.sections.keys())}")
    print(f"Metadata: {structure.metadata}")

    # 섹션 수정 테스트
    structure.update_section("context", "수정된 컨텍스트 내용")
    print("\n재구성된 프롬프트:")
    print(structure.to_prompt())
