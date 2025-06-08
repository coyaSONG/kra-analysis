# 경마 예측 프롬프트 개선 분석

## 현재 프롬프트 (v1.0) 분석

### 강점
1. 명확한 가중치 시스템 (35%/25%/15%/15%/10%)
2. 구체적인 보정 요소 정의
3. 체계적인 출력 형식

### 약점 및 개선사항

## 1. 구조적 개선사항

### 1.1 XML 태그 활용 부족
**현재**: 일반 텍스트로만 구성
**개선**: XML 태그로 입력/출력 구조화
```xml
<race_data>
  <race_info>...</race_info>
  <horses>...</horses>
</race_data>

<analysis_steps>
  <step1>데이터 검증</step1>
  <step2>개별 평가</step2>
  <step3>종합 점수 계산</step3>
</analysis_steps>
```

### 1.2 Chain of Thought 미적용
**현재**: 단순 점수 계산 방식
**개선**: 단계별 추론 과정 명시
```xml
<reasoning>
  <data_validation>각 말의 데이터 완전성 확인</data_validation>
  <individual_analysis>각 말에 대한 상세 분석</individual_analysis>
  <comparative_analysis>말들 간 상대적 비교</comparative_analysis>
  <final_selection>최종 선택 근거</final_selection>
</reasoning>
```

## 2. 데이터 분석 개선사항

### 2.1 가중치 재조정
**문제점**: 시장 평가 10%는 너무 낮음 (1위 인기마 놓침)
**개선안**:
- 말의 최근 성적: 35% → 30%
- 기수 능력: 25% → 20%
- 조교사 성적: 15% → 15% (유지)
- 경주 조건: 15% → 15% (유지)
- 시장 평가: 10% → 20%

### 2.2 데이터 부족 상황 처리
**문제점**: 신마나 데이터 부족 말 과소평가
**개선안**:
```
<data_shortage_handling>
- 경주 기록 3회 미만: 시장 평가 가중치 2배 적용
- 신마의 경우: 혈통, 조교 상태, 배당률 중심 평가
- 불확실성 점수 별도 계산
</data_shortage_handling>
```

### 2.3 체중 변화 해석 개선
**문제점**: 일률적인 -5점 페널티
**개선안**:
```
<weight_change_analysis>
- 성장기 말(3-4세): ±10kg는 정상 범위
- 장거리 경주: 체중 감소가 유리할 수 있음
- 계절별 체중 변화 패턴 고려
- 체중 변화 + 컨디션 지표 종합 평가
</weight_change_analysis>
```

## 3. 예측 프로세스 개선

### 3.1 다단계 검증 추가
```xml
<verification_steps>
  <step1>상위 5마리 1차 선정</step1>
  <step2>상호 비교 분석</step2>
  <step3>리스크 평가</step3>
  <step4>최종 3마리 확정</step4>
  <step5>대안 조합 생성</step5>
</verification_steps>
```

### 3.2 자가 검증 요소
```
예측 완료 후 다음을 확인하세요:
1. 1위 인기마를 제외했다면 명확한 근거가 있는가?
2. 데이터 부족 말을 과소평가하지 않았는가?
3. 체중 변화를 맥락에 맞게 해석했는가?
```

## 4. Few-shot 예시 추가

### 4.1 성공 사례
```
입력: [데이터가 부족한 신마가 1위 인기]
분석: 
<reasoning>
- 신마이지만 1위 인기는 조교 상태가 우수함을 시사
- 혈통 분석: 부모마 모두 단거리 강자
- 배당률이 낮은 것은 내부 정보 반영 가능성
</reasoning>
결과: 1위 예상에 포함
실제: 1착
```

### 4.2 실패 사례
```
입력: [체중 -12kg 감소한 말]
분석:
<reasoning>
- 단순히 체중 감소로 페널티 부여
- 장거리 적응을 위한 의도적 감량 가능성 미고려
</reasoning>
결과: 예측에서 제외
실제: 3착 (실수를 인정하고 학습)
```

## 5. 출력 형식 개선

### 5.1 신뢰도 세분화
**현재**: 상/중/하
**개선**: 
- 전체 신뢰도: 85% (수치화)
- 개별 말 신뢰도: 1번말(90%), 2번말(85%), 3번말(75%)
- 불확실성 요인 정량화

### 5.2 대안 제시 강화
```xml
<alternatives>
  <primary>5-4-6 (신뢰도: 75%)</primary>
  <alternative1>
    <combination>5-4-2</combination>
    <rationale>1위 인기마 포함</rationale>
    <confidence>70%</confidence>
  </alternative1>
  <alternative2>
    <combination>10-4-6</combination>
    <rationale>다크호스 고려</rationale>
    <confidence>60%</confidence>
  </alternative2>
</alternatives>
```

## 6. 특수 상황 처리

### 6.1 우천 시 전략
```
<weather_adaptation>
- 불량 주로: 선행마 유리
- 다습 주로: 추입마 불리
- 체중이 무거운 말: 불량 주로에서 불리
</weather_adaptation>
```

### 6.2 경주 유형별 전략
```
<race_type_strategy>
- 단거리(1200m 이하): 선행력, 초반 스피드 중시
- 중거리(1400-1800m): 균형잡힌 능력 필요
- 장거리(2000m 이상): 지구력, 체중 관리 중요
</race_type_strategy>
```

## 개선 우선순위

1. **긴급 (v1.1)**
   - 시장 평가 가중치 상향 (10% → 20%)
   - 데이터 부족 말 처리 로직 추가
   - 체중 변화 해석 개선

2. **중요 (v2.0)**
   - XML 태그 구조화
   - Chain of Thought 적용
   - Few-shot 예시 추가

3. **향후 (v3.0)**
   - 기계학습 모델과 결합
   - 실시간 배당률 변화 반영
   - 과거 예측 결과 학습