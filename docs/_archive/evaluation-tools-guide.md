# 평가 도구 가이드

이 문서는 프로젝트에서 사용하는 다양한 평가 도구들의 사용법을 설명합니다.

## 1. evaluate_prompt_v3.py - 전체 평가 시스템

실제 경주 결과와 예측을 비교하여 성능을 평가합니다.

### 사용법
```bash
python3 scripts/evaluation/evaluate_prompt_v3.py [버전] [프롬프트파일] [경주수] [병렬수]
```

### 예시
```bash
# 30개 경주로 v10.3 프롬프트 평가 (3개 병렬 실행)
python3 scripts/evaluation/evaluate_prompt_v3.py v10.3 prompts/prediction-template-v10.3.md 30 3
```

### 출력
- 개별 경주 예측 결과
- 전체 통계 (평균 적중률, 완전 적중률, 오류율)
- JSON 형식 결과 파일 저장

## 2. predict_only_test.py - 예측 전용 테스트

경주 전 데이터만으로 예측을 수행합니다. 실제 결과와 비교하지 않습니다.

### 사용법
```bash
python3 scripts/evaluation/predict_only_test.py [프롬프트파일] [날짜필터] [제한수]
```

### 예시
```bash
# 모든 경주 예측
python3 scripts/evaluation/predict_only_test.py prompts/base-prompt-v1.0.md

# 특정 날짜 경주만 예측
python3 scripts/evaluation/predict_only_test.py prompts/base-prompt-v1.0.md 20250601

# 10개 경주만 예측
python3 scripts/evaluation/predict_only_test.py prompts/base-prompt-v1.0.md all 10
```

### 특징
- **목적**: 경주 전 실제 베팅 상황 시뮬레이션
- **데이터**: enriched 데이터 사용 (말/기수/조교사 상세정보 포함)
- **출력**: 
  - 예측 결과 (3마리)
  - 신뢰도 (60-90%)
  - 예측 전략 (인기마 중심/중간 배당/고배당 도전)
  - 각 말의 상세 정보

### 결과 저장
- 위치: `data/prediction_tests/`
- 형식: `prediction_test_[날짜필터]_[타임스탬프].json`

## 3. recursive_prompt_improvement_v4.py - 재귀적 개선

프롬프트를 자동으로 평가하고 개선하는 시스템입니다.

### 사용법
```bash
python3 scripts/prompt_improvement/recursive_prompt_improvement_v4.py [프롬프트] [날짜/all] [반복] [병렬]
```

### 예시
```bash
# 모든 날짜로 5번 반복 개선 (3개 병렬)
python3 scripts/prompt_improvement/recursive_prompt_improvement_v4.py prompts/base-prompt-v1.0.md all 5 3

# 특정 날짜로 3번 반복 개선
python3 scripts/prompt_improvement/recursive_prompt_improvement_v4.py prompts/base-prompt-v1.0.md 20250601 3 3
```

### 프로세스
1. 현재 프롬프트로 평가 수행
2. 개별 경주 결과 상세 분석
3. 전체 이터레이션 통합 복기
4. 인사이트 기반 프롬프트 개선
5. 개선된 프롬프트로 재평가

## 4. get_race_result.js - 경주 결과 수집

개별 경주의 실제 결과(1-2-3위 착순)를 KRA API에서 수집합니다.

### 사용법
```bash
node scripts/race_collector/get_race_result.js [날짜] [경마장] [경주번호]
```

### 예시
```bash
# 6월 22일 서울 1경주 결과 수집
node scripts/race_collector/get_race_result.js 20250622 서울 1

# 6월 22일 부산경남 3경주 결과 수집
node scripts/race_collector/get_race_result.js 20250622 부산경남 3
```

### 기능
- KRA API214_1을 통한 실제 경주 결과 조회
- 1-2-3위 출주번호 추출
- `data/cache/results/top3_날짜_경마장_경주번호.json` 형태로 저장
- 평가 시스템과 자동 연동

### 출력 파일 형태
```json
[6, 7, 1]  // 1위: 6번, 2위: 7번, 3위: 1번
```

### 주의사항
- 경주 완료 후에만 결과 수집 가능
- 기권/제외마는 자동으로 필터링
- 평가 도구들이 자동으로 호출하므로 수동 실행은 선택사항

## 5. analyze_enriched_patterns.py - 데이터 패턴 분석

enriched 데이터의 패턴을 분석하여 인사이트를 도출합니다.

### 사용법
```bash
python3 scripts/prompt_improvement/analyze_enriched_patterns.py
```

### 분석 내용
- 배당률 순위별 실제 입상률
- 기수 승률별 말의 입상률
- 말 과거 입상률별 실제 입상률
- 부담중량 변화의 영향
- 데이터 가용성 통계

### 출력
- 콘솔: 상세 분석 결과
- 파일: `data/enriched_pattern_analysis_[타임스탬프].json`

## 선택 가이드

### 상황별 도구 선택

1. **새 프롬프트 성능 측정**: `evaluate_prompt_v3.py`
   - 정확한 성능 지표가 필요할 때
   - 다른 프롬프트와 비교할 때

2. **실전 예측 시뮬레이션**: `predict_only_test.py`
   - 실제 베팅 전 테스트
   - 아직 결과가 나오지 않은 경주 예측

3. **프롬프트 자동 개선**: `recursive_prompt_improvement_v4.py`
   - 성능을 높이고 싶을 때
   - 여러 버전을 빠르게 테스트할 때

4. **경주 결과 수집**: `get_race_result.js`
   - 새로운 경주 결과 데이터가 필요할 때
   - 평가 시스템이 자동으로 호출

5. **데이터 이해**: `analyze_enriched_patterns.py`
   - 데이터 특성 파악
   - 새로운 전략 아이디어 도출

## 주의사항

1. **데이터 준비**: 모든 도구는 enriched 데이터를 필요로 합니다
2. **API 키**: `.env` 파일에 KRA_SERVICE_KEY가 설정되어 있어야 합니다
3. **실행 시간**: 많은 경주를 평가할 때는 충분한 시간이 필요합니다
4. **병렬 실행**: CPU 코어 수를 고려하여 병렬 수를 설정하세요
