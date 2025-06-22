# 인사이트 분석 엔진 개선 설계

## 개요
v5 재귀 개선 시스템을 위한 고도화된 인사이트 분석 엔진 설계입니다. 이 엔진은 enriched 데이터를 심층 분석하여 실질적이고 구체적인 프롬프트 개선 방향을 도출합니다.

## 현재 시스템의 문제점

1. **부실한 패턴 인식**: 단순 문자열 매칭에 의존
2. **데이터 미활용**: enriched 데이터의 풍부한 정보 무시
3. **표면적 분석**: 성공/실패 여부만 확인
4. **추상적 권고사항**: 구체적인 개선 방법 제시 못함

## 설계 목표

1. **다차원 분석**: 모든 데이터 차원을 종합적으로 분석
2. **패턴 마이닝**: 숨겨진 성공/실패 패턴 발견
3. **상관관계 파악**: 성과와 가장 관련 높은 요소 식별
4. **실행 가능한 인사이트**: 구체적인 개선 방안 제시

## 시스템 아키텍처

### 1. 핵심 컴포넌트

```python
class InsightAnalysisEngine:
    - DataAnalyzer: 다차원 데이터 분석
    - PatternMiner: 패턴 발견 및 추출
    - CorrelationAnalyzer: 상관관계 분석
    - FailureAnalyzer: 실패 원인 심층 분석
    - RecommendationGenerator: 구체적 개선안 생성
```

### 2. 분석 차원

#### 2.1 배당률 분석
```python
class OddsAnalyzer:
    def analyze_odds_distribution(self, races: List[Dict]) -> Dict:
        - 인기순위별 적중률
        - 배당률 구간별 성공률
        - 인기마 vs 비인기마 균형
        - 배당률 변동성과 결과의 상관관계
```

#### 2.2 기수 분석
```python
class JockeyAnalyzer:
    def analyze_jockey_performance(self, races: List[Dict]) -> Dict:
        - 기수 승률별 적중률
        - 최근 성적 트렌드의 영향
        - 특정 기수의 과대/과소 평가 패턴
        - 기수-말 조합의 시너지
```

#### 2.3 말 분석
```python
class HorseAnalyzer:
    def analyze_horse_factors(self, races: List[Dict]) -> Dict:
        - 최근 입상률과 실제 성과
        - 나이별 성공 패턴
        - 부담중량 변화의 영향
        - 출주 간격과 성과 관계
```

#### 2.4 조교사 분석
```python
class TrainerAnalyzer:
    def analyze_trainer_impact(self, races: List[Dict]) -> Dict:
        - 조교사 성적과 말 성과의 상관관계
        - 특정 조교사의 전략 패턴
        - 조교사-기수 조합 효과
```

### 3. 패턴 마이닝

#### 3.1 성공 패턴 추출
```python
def mine_success_patterns(self, successful_predictions: List[Dict]) -> List[Pattern]:
    # 공통 특징 추출
    - 배당률 순위 조합 (예: [1위, 3위, 5위])
    - 기수 승률 범위 (예: 15% 이상 2명 + 10% 이하 1명)
    - 최근 성적 패턴 (예: 상승세 말 2개 이상)
    
    # 빈도 분석
    - 가장 자주 나타나는 조합
    - 특정 조건에서의 성공률
```

#### 3.2 실패 패턴 분석
```python
def analyze_failure_patterns(self, failed_predictions: List[Dict]) -> List[Pattern]:
    # 공통 실패 원인
    - 극단적 선택 (모두 인기마 or 모두 비인기마)
    - 특정 데이터 과신 (배당률만 or 기수만)
    - 최근 성적 무시
    
    # 예측 편향 분석
    - 시스템적 편향 (항상 인기마 선호 등)
    - 특정 조건에서의 실패 집중
```

### 4. 상관관계 분석

```python
class CorrelationAnalyzer:
    def calculate_feature_importance(self, races: List[Dict]) -> Dict[str, float]:
        # 각 요소의 예측력 계산
        features = {
            'win_odds_rank': 0.0,
            'jockey_win_rate': 0.0,
            'horse_place_rate': 0.0,
            'recent_performance': 0.0,
            'trainer_success_rate': 0.0,
            'weight_change': 0.0
        }
        
        # 정보 이득(Information Gain) 계산
        # 상관계수 분석
        # 다중공선성 확인
```

### 5. 실패 원인 심층 분석

```python
class FailureAnalyzer:
    def deep_dive_failures(self, failed_races: List[Dict]) -> Dict:
        # 실패 유형 분류
        failure_types = {
            'complete_miss': [],  # 3마리 모두 실패
            'partial_hit': [],    # 1-2마리만 적중
            'wrong_order': []     # 말은 맞췄지만 순서 틀림
        }
        
        # 각 유형별 원인 분석
        - complete_miss: 전략적 오류, 데이터 해석 실패
        - partial_hit: 세부 조정 필요, 가중치 문제
        - wrong_order: 순위 예측 로직 개선 필요
```

### 6. 구체적 권고사항 생성

```python
class RecommendationGenerator:
    def generate_actionable_recommendations(self, analysis_results: Dict) -> List[Recommendation]:
        recommendations = []
        
        # 가중치 조정 권고
        if analysis_results['odds_correlation'] > 0.7:
            recommendations.append({
                'type': 'weight_adjustment',
                'target': 'win_odds',
                'action': 'increase',
                'value': 0.5,
                'reason': '배당률이 높은 예측력 보임'
            })
        
        # 새로운 규칙 추가
        if analysis_results['jockey_15plus_success'] > 0.6:
            recommendations.append({
                'type': 'add_rule',
                'rule': '기수 승률 15% 이상인 말 우선 고려',
                'confidence': 0.8
            })
        
        # 전략 변경
        if analysis_results['extreme_selection_failure'] > 0.5:
            recommendations.append({
                'type': 'strategy_change',
                'change': '인기마와 비인기마 균형 선택',
                'ratio': '2:1'
            })
```

## 통합 분석 프로세스

### 1. 데이터 준비
```python
def prepare_analysis_data(self, evaluation_results: List[Dict]) -> AnalysisDataset:
    # enriched 데이터 정규화
    # 성공/실패 라벨링
    # 특징 추출
```

### 2. 다차원 분석 실행
```python
def run_comprehensive_analysis(self, dataset: AnalysisDataset) -> AnalysisResults:
    # 각 분석기 실행
    odds_insights = self.odds_analyzer.analyze(dataset)
    jockey_insights = self.jockey_analyzer.analyze(dataset)
    horse_insights = self.horse_analyzer.analyze(dataset)
    
    # 통합 및 교차 분석
    combined_insights = self.combine_insights([
        odds_insights, jockey_insights, horse_insights
    ])
```

### 3. 인사이트 우선순위화
```python
def prioritize_insights(self, insights: List[Insight]) -> List[Insight]:
    # 영향도 기준 정렬
    # 실행 가능성 고려
    # 예상 개선 효과 계산
```

## 출력 형식

### 분석 보고서 구조
```json
{
    "summary": {
        "total_races_analyzed": 180,
        "success_rate": 10.9,
        "key_findings": ["배당률 1-3위 무시 경향", "기수 승률 미활용"]
    },
    "detailed_analysis": {
        "odds_analysis": {...},
        "jockey_analysis": {...},
        "horse_analysis": {...},
        "trainer_analysis": {...}
    },
    "patterns": {
        "success_patterns": [...],
        "failure_patterns": [...]
    },
    "correlations": {
        "feature_importance": {...},
        "interaction_effects": {...}
    },
    "recommendations": [
        {
            "priority": "high",
            "type": "weight_adjustment",
            "description": "배당률 가중치를 40%에서 50%로 상향",
            "expected_improvement": "3-5% 적중률 향상"
        }
    ]
}
```

## 구현 우선순위

1. **Phase 1**: 기본 분석 프레임워크
   - DataAnalyzer 기본 구조
   - 데이터 준비 파이프라인

2. **Phase 2**: 개별 분석기 구현
   - OddsAnalyzer
   - JockeyAnalyzer
   - HorseAnalyzer

3. **Phase 3**: 고급 분석 기능
   - PatternMiner
   - CorrelationAnalyzer
   - RecommendationGenerator

## 기대 효과

1. **구체적 개선안**: 추상적 권고가 아닌 실행 가능한 개선 방법
2. **데이터 기반 의사결정**: 직관이 아닌 통계적 근거
3. **지속적 학습**: 새로운 패턴 자동 발견
4. **성능 예측**: 개선안 적용 시 예상 효과 제시

---
*작성일: 2025-06-22*
*작성자: Claude Code*
*파일 위치: docs/insight-analysis-engine-design.md*