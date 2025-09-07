# 프롬프트 엔지니어링 가이드

본 문서는 Claude 공식 문서(docs.anthropic.com)를 기반으로 정리한 프롬프트 엔지니어링 모범 사례입니다.

## 1. 명확하고 구체적인 지시사항

### 원칙
- 모호한 표현을 피하고 구체적인 요구사항을 명시
- 원하는 출력 형식을 명확히 제시
- "무엇을 하지 말라"보다 "무엇을 하라"는 긍정적 지시 사용

### 예시
```
❌ 나쁜 예: "짧게 요약해주세요"
✅ 좋은 예: "3-5개의 핵심 포인트로 요약해주세요. 각 포인트는 한 문장으로 작성하세요."
```

## 2. XML 태그를 활용한 구조화

### 원칙
- 입력과 출력을 명확히 구분
- 복잡한 정보를 체계적으로 조직화
- Claude가 정보를 쉽게 파싱할 수 있도록 지원

### 예시
```xml
<documents>
  <document index="1">
    <source>file_name.txt</source>
    <content>{{DOCUMENT_CONTENT}}</content>
  </document>
</documents>

<task>
위 문서를 분석하고 다음 형식으로 결과를 제공하세요:
</task>

<output_format>
<analysis>
  <summary>요약 내용</summary>
  <key_points>
    <point>핵심 포인트 1</point>
    <point>핵심 포인트 2</point>
  </key_points>
</analysis>
</output_format>
```

## 3. Chain of Thought (사고의 연쇄)

### 원칙
- 복잡한 작업을 단계별로 분해
- 일반적인 "Think step-by-step"보다 구체적인 단계 안내 제공
- 추론 과정을 명시적으로 요청

### 예시
```
작업을 수행하기 전에 다음 단계를 따라 분석하세요:

1. 주어진 데이터에서 핵심 요소들을 식별하세요
2. 각 요소 간의 관계를 파악하세요
3. 가능한 해결 방법들을 나열하세요
4. 각 방법의 장단점을 평가하세요
5. 최적의 해결책을 선택하고 그 이유를 설명하세요

<reasoning>태그 안에 당신의 분석 과정을 작성하세요.
```

## 4. 시스템 프롬프트와 역할 정의

### 원칙
- AI의 전문성과 역할을 명확히 정의
- 작업의 맥락과 목적 제공
- 일관된 페르소나 유지

### 예시
```
You are an expert financial analyst with 15 years of experience in equity research. 
Your task is to analyze company financial statements and provide investment recommendations.
You should:
- Focus on fundamental analysis
- Consider both quantitative and qualitative factors
- Provide balanced, objective assessments
- Support conclusions with specific data points
```

## 5. Few-shot 예시 활용

### 원칙
- 원하는 출력 패턴을 명확히 보여주는 예시 제공
- 다양한 케이스를 포함하여 일반화 능력 향상
- 경계 사례나 특수 상황도 포함

### 예시
```
다음 예시와 같은 형식으로 분석을 제공하세요:

예시 1:
입력: "주가가 10% 상승했지만 거래량은 감소"
분석: 
<trend>약세 신호</trend>
<reasoning>가격 상승에도 불구하고 거래량 감소는 상승 동력 부족을 시사</reasoning>
<confidence>중간</confidence>

예시 2:
입력: "실적 발표 후 주가 5% 하락, 거래량 200% 증가"
분석:
<trend>강세 전환 가능</trend>
<reasoning>대량 거래는 매도 압력 해소 과정일 수 있음</reasoning>
<confidence>낮음</confidence>

이제 다음을 분석하세요:
입력: {{USER_INPUT}}
```

## 6. Prefill 기법

### 원칙
- Assistant의 응답 시작 부분을 미리 작성
- 원하는 형식이나 톤을 유도
- JSON이나 특정 포맷 출력 시 유용

### 예시
```python
messages = [
    {"role": "user", "content": "제품 정보를 JSON으로 추출하세요: SmartPhone X는 $999이며 검정, 흰색이 있습니다."},
    {"role": "assistant", "content": "```json\n{"}
]
```

## 7. 프롬프트 개선 프로세스

### 원칙
1. **초기 프롬프트 작성**: 기본 요구사항 포함
2. **테스트 실행**: 다양한 입력으로 테스트
3. **결과 분석**: 예상과 다른 출력 식별
4. **개선사항 도출**: 문제점 파악 및 해결 방안 마련
5. **프롬프트 수정**: 피드백 반영
6. **반복**: 만족할 때까지 2-5단계 반복

### 개선 체크리스트
- [ ] 지시사항이 명확하고 구체적인가?
- [ ] 출력 형식이 명시되어 있는가?
- [ ] 필요한 맥락 정보가 충분한가?
- [ ] 예시가 다양한 케이스를 포함하는가?
- [ ] 엣지 케이스 처리 방법이 명시되어 있는가?

## 8. 고급 기법

### 8.1 Extended Thinking Mode (확장 사고 모드)
Claude에게 더 많은 계산 시간을 부여하여 더 신중한 평가를 할 수 있도록 하는 기능입니다.

#### 사용 방법
프롬프트에 다음 키워드를 포함하면 점진적으로 더 많은 thinking budget이 할당됩니다:

1. **"think"** - 기본 수준의 추가 사고 시간
2. **"think hard"** - 중간 수준의 추가 사고 시간
3. **"think harder"** - 높은 수준의 추가 사고 시간
4. **"ultrathink"** - 최대 수준의 추가 사고 시간

#### 예시
```
이 복잡한 데이터를 분석하고 think hard about the patterns and correlations.

Please ultrathink through all possible edge cases before providing the solution.
```

#### 사용 시나리오
- 복잡한 문제 해결
- 여러 대안 비교 평가
- 엣지 케이스 고려
- 정확도가 중요한 작업

### 8.2 다중 문서 처리
- 문서별로 인덱스 부여
- 출처 명시 요구
- 인용 형식 지정

### 8.3 자가 검증
- 결과 생성 후 검증 단계 추가
- 테스트 케이스로 솔루션 확인
- 오류 발견 시 수정 요청

### 8.4 토큰 최적화
- 불필요한 반복 제거
- 간결하면서도 명확한 표현 사용
- 구조화된 데이터는 표 형식 활용

## 9. 프롬프트 템플릿

### 기본 템플릿
```
<context>
{{배경 정보}}
</context>

<task>
{{수행할 작업}}
</task>

<requirements>
- 요구사항 1
- 요구사항 2
- 요구사항 3
</requirements>

<output_format>
{{원하는 출력 형식}}
</output_format>

<examples>
{{예시들}}
</examples>
```

## 10. 일반적인 실수와 해결책

### 실수 1: 너무 일반적인 지시
- ❌ "분석해주세요"
- ✅ "다음 5가지 측면에서 분석해주세요: 재무, 시장, 경쟁, 리스크, 성장성"

### 실수 2: 모순되는 지시
- ❌ "간단하게 자세히 설명해주세요"
- ✅ "핵심 개념을 먼저 한 문장으로 요약한 후, 3-4문장으로 상세 설명하세요"

### 실수 3: 맥락 부족
- ❌ "이 데이터를 해석하세요"
- ✅ "이 데이터는 2023년 한국 주식시장 데이터입니다. 투자자 관점에서 해석하세요"

---

이 가이드는 지속적으로 업데이트됩니다. 
최신 Claude 기능과 모범 사례는 [docs.anthropic.com](https://docs.anthropic.com)을 참조하세요.