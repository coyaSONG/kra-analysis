# 프롬프트 파싱 및 구조화 시스템 설계

## 개요
v5 재귀 개선 시스템을 위한 프롬프트 파싱 및 구조화 시스템 설계입니다. 이 시스템은 프롬프트를 구조적으로 분석하고, 각 섹션을 독립적으로 수정할 수 있게 합니다.

## 설계 목표

1. **구조적 파싱**: XML 태그 기반 프롬프트를 섹션별로 분해
2. **독립적 수정**: 각 섹션을 개별적으로 수정 가능
3. **구조 보존**: 원본 프롬프트의 형식과 순서 유지
4. **확장성**: 새로운 섹션 타입 추가 용이

## 시스템 아키텍처

### 1. 핵심 컴포넌트

```python
class PromptParsingSystem:
    - PromptParser: 프롬프트 파싱 엔진
    - PromptStructure: 파싱된 프롬프트 구조체
    - PromptSection: 개별 섹션 클래스
    - PromptBuilder: 프롬프트 재구성 엔진
```

### 2. 데이터 구조

#### PromptSection
```python
@dataclass
class PromptSection:
    tag: str  # 'context', 'role', 'task' 등
    content: str  # 섹션 내용
    attributes: Dict[str, Any]  # 추가 속성
    order: int  # 원본에서의 순서
```

#### PromptStructure
```python
@dataclass
class PromptStructure:
    title: str  # 프롬프트 제목
    version: str  # 버전 정보
    sections: Dict[str, PromptSection]  # 태그별 섹션
    metadata: Dict[str, Any]  # 메타데이터
```

### 3. 파싱 프로세스

#### 3.1 XML 태그 인식
```python
RECOGNIZED_TAGS = [
    'context',
    'role', 
    'task',
    'requirements',
    'analysis_steps',
    'output_format',
    'examples',
    'important_notes'
]
```

#### 3.2 특수 섹션 처리
- **examples**: 성공/실패 사례를 구조화된 형태로 파싱
- **requirements**: 번호 목록을 개별 항목으로 분리
- **analysis_steps**: 단계별 프로세스를 리스트로 관리

### 4. 파싱 알고리즘

```python
def parse_prompt(content: str) -> PromptStructure:
    1. 제목과 버전 추출
    2. XML 태그 기반 섹션 분리
    3. 각 섹션 내용 파싱
    4. 특수 섹션 추가 처리
    5. 구조체 생성 및 반환
```

## 주요 기능

### 1. 섹션별 접근 및 수정

```python
# 특정 섹션 읽기
context = prompt_structure.get_section('context')

# 섹션 내용 수정
prompt_structure.update_section('context', new_content)

# 새 섹션 추가
prompt_structure.add_section('custom_rules', content)
```

### 2. Examples 관리

```python
class ExamplesManager:
    def add_success_example(self, example: Dict)
    def add_failure_example(self, example: Dict)
    def get_balanced_examples(self, count: int)
    def remove_outdated_examples(self)
```

### 3. Requirements 조작

```python
class RequirementsEditor:
    def add_requirement(self, requirement: str)
    def remove_requirement(self, index: int)
    def reorder_requirements(self, new_order: List[int])
    def update_requirement(self, index: int, new_text: str)
```

### 4. 분석 단계 수정

```python
class AnalysisStepsEditor:
    def insert_step(self, position: int, step: str)
    def modify_step(self, index: int, new_step: str)
    def reorder_steps(self, new_order: List[int])
```

## 프롬프트 재구성

### 1. Builder 패턴 활용

```python
class PromptBuilder:
    def __init__(self, structure: PromptStructure):
        self.structure = structure
    
    def with_updated_context(self, context: str) -> 'PromptBuilder':
        # 컨텍스트 업데이트
        
    def with_new_examples(self, examples: List[Dict]) -> 'PromptBuilder':
        # 예시 교체
        
    def with_modified_requirements(self, modifier: Callable) -> 'PromptBuilder':
        # 요구사항 수정
        
    def build(self) -> str:
        # 최종 프롬프트 생성
```

### 2. 템플릿 시스템

```python
SECTION_TEMPLATES = {
    'context': '<context>\n{content}\n</context>',
    'role': '<role>\n{content}\n</role>',
    'examples': '<examples>\n{formatted_examples}\n</examples>'
}
```

## 검증 시스템

### 1. 구조 검증

```python
class PromptValidator:
    def validate_structure(self, structure: PromptStructure) -> List[str]:
        # 필수 섹션 확인
        # 섹션 순서 검증
        # 내용 형식 검증
```

### 2. 내용 검증

```python
def validate_content(self, structure: PromptStructure) -> List[str]:
    # JSON 형식 검증 (output_format)
    # 예시 형식 검증
    # 번호 목록 일관성
```

## 통합 예시

```python
# 1. 기존 프롬프트 파싱
parser = PromptParser()
structure = parser.parse(prompt_content)

# 2. 분석 및 수정
structure.update_section('context', f"... 이전 성능: {new_performance}")
examples_manager = ExamplesManager(structure)
examples_manager.add_success_example(new_success_case)

# 3. 요구사항 개선
requirements_editor = RequirementsEditor(structure)
requirements_editor.add_requirement("6. 새로운 패턴 고려")

# 4. 프롬프트 재구성
builder = PromptBuilder(structure)
improved_prompt = builder.with_updated_performance(metrics).build()
```

## 구현 우선순위

1. **Phase 1**: 기본 파싱 시스템
   - PromptParser
   - PromptStructure
   - 기본 섹션 파싱

2. **Phase 2**: 섹션별 편집기
   - ExamplesManager
   - RequirementsEditor
   - AnalysisStepsEditor

3. **Phase 3**: 재구성 및 검증
   - PromptBuilder
   - PromptValidator
   - 통합 테스트

## 기대 효과

1. **정밀한 수정**: 프롬프트의 특정 부분만 수정 가능
2. **구조 보존**: 원본 형식 유지하면서 내용 개선
3. **자동화 가능**: 인사이트 기반 자동 수정 구현 용이
4. **추적 가능**: 변경 사항을 섹션별로 추적 가능

## 다음 단계

1. 프로토타입 구현
2. 기존 v4 프롬프트로 테스트
3. 인사이트 분석 엔진과 통합
4. 동적 재구성 시스템 연동

---
*작성일: 2025-06-22*
*작성자: Claude Code*
*파일 위치: docs/prompt-parsing-system-design.md*
