# 프롬프트 재귀 개선 프로세스 가이드

## 개요

삼복연승 예측 프롬프트를 자동으로 평가하고 개선하는 재귀적 시스템입니다. Claude CLI를 활용하여 실제 경주 데이터로 테스트하고, 결과를 분석하여 프롬프트를 지속적으로 개선합니다.

## 시스템 구성

### 1. 핵심 스크립트

#### evaluate_prompt.py
- **역할**: 단일 프롬프트 버전 평가
- **기능**:
  - Claude CLI로 예측 실행
  - 실제 결과와 비교
  - 보상함수 기반 점수 계산
  - 실패 패턴 분석

#### recursive_prompt_improvement.py
- **역할**: 재귀적 개선 사이클 관리
- **기능**:
  - 평가 → 분석 → 개선 → 재평가 사이클
  - 자동 가중치 조정
  - 성능 추적 및 보고서 생성

### 2. 프로세스 플로우

```
[초기 프롬프트]
      ↓
[1. 예측 실행] ← Claude CLI
      ↓
[2. 결과 비교] ← 실제 경주 결과
      ↓
[3. 성능 평가] ← 보상함수
      ↓
[4. 패턴 분석] ← 실패 원인 분석
      ↓
[5. 개선안 도출] ← 자동 제안
      ↓
[6. 프롬프트 수정] → 다음 버전
      ↓
[반복] ← 목표 달성까지
```

## 사용법

### 1. 단일 프롬프트 평가

```bash
# 기본 평가 (10개 경주)
python scripts/evaluate_prompt.py v2.0 prompts/prediction-template-v2.0.md

# 더 많은 경주로 평가
python scripts/evaluate_prompt.py v2.0 prompts/prediction-template-v2.0.md 20
```

### 2. 재귀 개선 실행

```bash
# 기본 실행 (10개 경주, 5회 반복)
python scripts/recursive_prompt_improvement.py prompts/prediction-template-v2.0.md

# 커스텀 설정
python scripts/recursive_prompt_improvement.py prompts/prediction-template-v2.0.md 20 10
# (20개 경주로 테스트, 최대 10회 반복)
```

## 평가 메트릭

### 1. 보상함수
```python
기본 점수 = 적중 말 수 × 33.33
보너스 = 10 (3마리 모두 적중 시)
총점 = 기본 점수 + 보너스
```

### 2. 성공 기준
- **완전 적중**: 3마리 모두 적중
- **부분 적중**: 1-2마리 적중
- **목표**: 완전 적중률 30% 이상

### 3. 분석 지표
- 인기마 놓침 비율
- 데이터 부족 말 처리 성공률
- 체중 변화 해석 정확도

## 개선 메커니즘

### 1. 자동 가중치 조정
```
현재 실패 패턴 분석 → 가중치 조정 제안
예: 인기마 놓침 多 → 시장평가 가중치 상향
```

### 2. 로직 개선
- 데이터 부족 말 처리 강화
- 체중 변화 해석 규칙 수정
- 검증 단계 추가

### 3. 구조적 변경
- Chain of Thought 강화
- Few-shot 예시 추가
- 다단계 검증 프로세스

## 출력 및 보고서

### 1. 평가 결과
```
data/prompt_evaluation/
├── evaluation_v2.0_20250607_150000.json
├── evaluation_v2.1_20250607_151000.json
└── ...
```

### 2. 개선 이력
```
data/recursive_improvement/
├── prompt_v1.0.md
├── prompt_v2.1.md
├── prompt_v3.2.md
└── improvement_report_20250607_160000.md
```

### 3. 최종 보고서 내용
- 성능 변화 추이 그래프
- 각 iteration별 개선사항
- 최적 버전 및 성능
- 주요 인사이트

## 실행 예시

### 초기 실행
```bash
$ python scripts/recursive_prompt_improvement.py prompts/prediction-template-v2.0.md 10 5

재귀적 프롬프트 개선 시작
최대 반복: 5회
테스트 경주 수: 10개
============================================================

=== Iteration 1/5 ===
평가 실행: v1.0
[1/10] race_3_20250523_1 처리 중...
  예측: [5, 4, 6]
  실제: [10, 2, 11]
  적중: 0/3 (0.0%)
...

성능 요약:
  - 완전 적중률: 10.0%
  - 평균 적중 말: 0.8/3

개선사항 적용:
  - market_evaluation 가중치: 20% → 25%
  - c_group_handling 로직 개선: increase_market_weight_multiplier
```

### 최종 결과
```bash
=== Iteration 5/5 ===
성능 요약:
  - 완전 적중률: 30.0%
  - 평균 적중 말: 1.9/3
  - 적중률 변화: +5.0%p

목표 달성! (적중률 30% 이상)

최종 보고서 생성: data/recursive_improvement/improvement_report_20250607_160000.md
최적화된 프롬프트 저장: prompts/prediction-template-optimized.md
```

## 주의사항

1. **API 제한**: Claude CLI 호출 간 5초 대기
2. **데이터 요구**: 결과가 있는 경주만 테스트 가능
3. **시간 소요**: 10개 경주 × 5회 반복 ≈ 30분
4. **비용**: Claude API 사용량 고려

## 확장 가능성

1. **더 많은 메트릭**: 배당률 예측, ROI 계산
2. **A/B 테스트**: 여러 프롬프트 동시 비교
3. **시계열 분석**: 시즌별 성능 변화
4. **앙상블**: 여러 프롬프트 결과 조합

---

*최종 업데이트: 2025년 6월 7일*