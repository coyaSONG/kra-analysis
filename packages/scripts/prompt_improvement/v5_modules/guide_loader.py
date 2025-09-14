"""
프롬프트 엔지니어링 가이드 로더
docs/prompt-engineering-guide.md를 파싱하여 고급 기법들을 추출합니다.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from .utils import read_text_file, setup_logger


@dataclass
class GuideTechnique:
    """가이드의 개별 기법"""
    name: str
    category: str
    description: str
    usage_pattern: str | None = None
    example: str | None = None
    keywords: list[str] = None


class PromptEngineeringGuideLoader:
    """프롬프트 엔지니어링 가이드 로더"""

    def __init__(self):
        self.logger = setup_logger('guide_loader')
        self.guide_path = Path(__file__).parent.parent.parent.parent / 'docs' / 'prompt-engineering-guide.md'
        self.techniques: dict[str, GuideTechnique] = {}
        self.load_guide()

    def load_guide(self) -> None:
        """가이드 파일 로드 및 파싱"""
        if not self.guide_path.exists():
            self.logger.warning(f"가이드 파일이 없습니다: {self.guide_path}")
            return

        content = read_text_file(self.guide_path)
        self._parse_guide(content)
        self.logger.info(f"가이드에서 {len(self.techniques)}개의 기법을 로드했습니다")

    def _parse_guide(self, content: str) -> None:
        """가이드 내용 파싱"""
        # Extended Thinking Mode 파싱
        self._parse_extended_thinking(content)

        # 자가 검증 파싱
        self._parse_self_verification(content)

        # 토큰 최적화 파싱
        self._parse_token_optimization(content)

        # XML 태그 구조화 파싱
        self._parse_xml_structure(content)

        # Chain of Thought 파싱
        self._parse_chain_of_thought(content)

    def _parse_extended_thinking(self, content: str) -> None:
        """Extended Thinking Mode 파싱"""
        pattern = r'### 8\.1 Extended Thinking Mode.*?(?=###|\Z)'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            section = match.group(0)

            # 키워드 추출
            keywords = []
            keyword_pattern = r'\*\*"(think[^"]*?)"\*\* - ([^\n]+)'
            for keyword_match in re.finditer(keyword_pattern, section):
                keywords.append({
                    'keyword': keyword_match.group(1),
                    'level': keyword_match.group(2)
                })

            # 사용 예시 추출
            example_pattern = r'#### 예시\s*```(.*?)```'
            example_match = re.search(example_pattern, section, re.DOTALL)
            example = example_match.group(1).strip() if example_match else None

            self.techniques['extended_thinking'] = GuideTechnique(
                name='Extended Thinking Mode',
                category='advanced',
                description='Claude에게 더 많은 계산 시간을 부여하여 더 신중한 평가를 할 수 있도록 하는 기능',
                keywords=[k['keyword'] for k in keywords],
                example=example
            )

            # 키워드별 레벨 저장
            self.techniques['thinking_levels'] = keywords

    def _parse_self_verification(self, content: str) -> None:
        """자가 검증 파싱"""
        pattern = r'### 8\.3 자가 검증.*?(?=###|\Z)'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            section = match.group(0)

            # 검증 단계 추출
            steps = []
            step_pattern = r'- ([^\n]+)'
            for step_match in re.finditer(step_pattern, section):
                steps.append(step_match.group(1))

            self.techniques['self_verification'] = GuideTechnique(
                name='자가 검증',
                category='advanced',
                description='결과 생성 후 검증 단계를 추가하여 정확성을 높이는 기법',
                usage_pattern='\n'.join(steps)
            )

    def _parse_token_optimization(self, content: str) -> None:
        """토큰 최적화 파싱"""
        pattern = r'### 8\.4 토큰 최적화.*?(?=###|\Z)'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            section = match.group(0)

            # 최적화 방법 추출
            methods = []
            method_pattern = r'- ([^\n]+)'
            for method_match in re.finditer(method_pattern, section):
                methods.append(method_match.group(1))

            self.techniques['token_optimization'] = GuideTechnique(
                name='토큰 최적화',
                category='advanced',
                description='응답 효율성을 높이기 위한 토큰 사용 최적화',
                usage_pattern='\n'.join(methods)
            )

    def _parse_xml_structure(self, content: str) -> None:
        """XML 태그 구조화 파싱"""
        pattern = r'## 2\. XML 태그를 활용한 구조화.*?(?=##|\Z)'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            section = match.group(0)

            # 예시 추출
            example_pattern = r'### 예시\s*```xml(.*?)```'
            example_match = re.search(example_pattern, section, re.DOTALL)

            self.techniques['xml_structure'] = GuideTechnique(
                name='XML 태그 구조화',
                category='basic',
                description='입력과 출력을 명확히 구분하고 복잡한 정보를 체계적으로 조직화',
                example=example_match.group(1).strip() if example_match else None
            )

    def _parse_chain_of_thought(self, content: str) -> None:
        """Chain of Thought 파싱"""
        pattern = r'## 3\. Chain of Thought.*?(?=##|\Z)'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            section = match.group(0)

            # 예시 추출
            example_pattern = r'### 예시\s*```(.*?)```'
            example_match = re.search(example_pattern, section, re.DOTALL)

            self.techniques['chain_of_thought'] = GuideTechnique(
                name='Chain of Thought',
                category='basic',
                description='복잡한 작업을 단계별로 분해하여 추론 과정을 명시적으로 요청',
                example=example_match.group(1).strip() if example_match else None
            )

    def get_technique(self, name: str) -> GuideTechnique | None:
        """특정 기법 조회"""
        return self.techniques.get(name)

    def get_all_techniques(self) -> dict[str, GuideTechnique]:
        """모든 기법 조회"""
        return self.techniques

    def get_thinking_keywords(self) -> list[dict[str, str]]:
        """Extended Thinking 키워드 조회"""
        return self.techniques.get('thinking_levels', [])

    def should_apply_technique(self, technique_name: str, current_performance: float) -> bool:
        """특정 기법 적용 여부 결정"""
        # 성능에 따른 적용 전략
        if technique_name == 'extended_thinking':
            # 성능이 낮을 때 더 깊은 사고 필요
            return current_performance < 60
        elif technique_name == 'self_verification':
            # 중간 성능에서 검증 강화
            return 40 <= current_performance < 70
        elif technique_name == 'token_optimization':
            # 항상 적용
            return True

        return False
