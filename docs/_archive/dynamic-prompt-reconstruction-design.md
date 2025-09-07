# 동적 프롬프트 재구성 시스템 설계

## 개요
v5 재귀 개선 시스템의 핵심 컴포넌트로, 파싱된 프롬프트 구조와 인사이트 분석 결과를 바탕으로 개선된 프롬프트를 동적으로 생성하는 시스템입니다.

## 설계 목표

1. **인사이트 기반 개선**: 분석 결과를 프롬프트에 정확히 반영
2. **구조 보존**: 원본 프롬프트의 형식과 가독성 유지
3. **추적 가능성**: 모든 변경사항 기록 및 롤백 가능
4. **점진적 개선**: 급격한 변화보다 안정적인 개선

## 시스템 아키텍처

### 1. 핵심 컴포넌트

```python
class DynamicPromptReconstructor:
    - PromptModifier: 섹션별 수정 엔진
    - WeightOptimizer: 가중치 최적화
    - RuleEngine: 규칙 추가/수정/삭제
    - ExampleCurator: 예시 관리 및 선택
    - ChangeTracker: 변경사항 추적
    - VersionController: 버전 관리
```

### 2. 재구성 전략

#### 2.1 섹션별 수정 전략
```python
class SectionModificationStrategy:
    strategies = {
        'context': ContextModifier(),
        'requirements': RequirementsModifier(),
        'analysis_steps': AnalysisStepsModifier(),
        'examples': ExamplesModifier(),
        'important_notes': NotesModifier()
    }
    
    def apply_modifications(self, section: PromptSection, 
                          recommendations: List[Recommendation]) -> PromptSection:
        # 섹션 타입에 맞는 수정 전략 적용
```

#### 2.2 가중치 최적화
```python
class WeightOptimizer:
    def optimize_weights(self, current_weights: Dict[str, float], 
                        analysis_results: Dict) -> Dict[str, float]:
        # 현재 가중치
        weights = {
            'odds': 0.4,
            'jockey': 0.3,
            'horse': 0.3
        }
        
        # 분석 결과 기반 조정
        if analysis_results['odds_correlation'] > 0.7:
            weights['odds'] += 0.1
            weights['jockey'] -= 0.05
            weights['horse'] -= 0.05
        
        return self.normalize_weights(weights)
```

#### 2.3 규칙 엔진
```python
class RuleEngine:
    def process_rule_recommendations(self, 
                                    current_rules: List[str],
                                    recommendations: List[Recommendation]) -> List[str]:
        rules = current_rules.copy()
        
        for rec in recommendations:
            if rec['type'] == 'add_rule':
                rules.append(rec['rule'])
            elif rec['type'] == 'modify_rule':
                rules[rec['index']] = rec['new_rule']
            elif rec['type'] == 'remove_rule':
                rules.pop(rec['index'])
        
        return self.prioritize_rules(rules)
```

### 3. 예시 관리 시스템

#### 3.1 예시 큐레이션
```python
class ExampleCurator:
    def __init__(self):
        self.example_pool = ExamplePool()
        self.performance_tracker = PerformanceTracker()
    
    def select_optimal_examples(self, 
                               current_performance: float,
                               target_count: int = 4) -> List[Example]:
        # 다양성 확보
        examples = []
        
        # 1. 최고 성과 사례
        examples.extend(self.example_pool.get_top_performers(2))
        
        # 2. 경계 사례 (아슬아슬하게 성공한 경우)
        examples.append(self.example_pool.get_edge_case())
        
        # 3. 최근 실패에서 배운 교훈
        examples.append(self.example_pool.get_learning_example())
        
        return examples
```

#### 3.2 예시 성과 추적
```python
class ExamplePerformanceTracker:
    def track_example_effectiveness(self, 
                                   example: Example,
                                   evaluation_results: List[Dict]):
        # 해당 예시가 포함된 프롬프트의 성과 추적
        # 예시별 기여도 계산
        # 저성과 예시 자동 제거
```

### 4. 변경사항 적용 로직

#### 4.1 점진적 적용
```python
class GradualChangeApplier:
    def apply_changes(self, 
                     current_prompt: PromptStructure,
                     recommendations: List[Recommendation],
                     aggressiveness: float = 0.3) -> PromptStructure:
        # 권고사항 우선순위화
        prioritized = self.prioritize_recommendations(recommendations)
        
        # 상위 N개만 적용 (aggressiveness에 따라)
        to_apply = prioritized[:int(len(prioritized) * aggressiveness)]
        
        # 변경 적용
        modified_prompt = current_prompt.copy()
        for rec in to_apply:
            modified_prompt = self.apply_single_change(modified_prompt, rec)
        
        return modified_prompt
```

#### 4.2 충돌 해결
```python
class ConflictResolver:
    def resolve_conflicts(self, recommendations: List[Recommendation]) -> List[Recommendation]:
        # 상충되는 권고사항 식별
        conflicts = self.identify_conflicts(recommendations)
        
        # 우선순위 기반 해결
        resolved = []
        for conflict_group in conflicts:
            winner = self.select_best_recommendation(conflict_group)
            resolved.append(winner)
        
        return resolved
```

### 5. 재구성 프로세스

#### 5.1 전체 워크플로우
```python
def reconstruct_prompt(self, 
                      current_prompt: PromptStructure,
                      analysis_results: InsightAnalysis,
                      version: str) -> ImprovedPrompt:
    # 1. 권고사항 추출
    recommendations = analysis_results.get_recommendations()
    
    # 2. 충돌 해결
    recommendations = self.conflict_resolver.resolve(recommendations)
    
    # 3. 섹션별 수정 계획
    modification_plan = self.plan_modifications(current_prompt, recommendations)
    
    # 4. 변경 적용
    modified_structure = self.apply_modifications(current_prompt, modification_plan)
    
    # 5. 예시 업데이트
    modified_structure = self.update_examples(modified_structure, analysis_results)
    
    # 6. 검증
    validation_results = self.validate_changes(modified_structure)
    
    # 7. 최종 프롬프트 생성
    return self.build_final_prompt(modified_structure, version)
```

### 6. 변경 추적 및 버전 관리

#### 6.1 변경 기록
```python
@dataclass
class ChangeRecord:
    timestamp: datetime
    version_from: str
    version_to: str
    changes: List[Change]
    performance_before: float
    performance_after: Optional[float]
    rollback_available: bool
```

#### 6.2 롤백 메커니즘
```python
class VersionController:
    def rollback(self, to_version: str) -> PromptStructure:
        # 지정된 버전으로 롤백
        # 중간 변경사항 역적용
        # 성능 메트릭 복원
```

## 구체적 수정 예시

### 1. 가중치 수정
```python
# Before
"3. 복합 점수 계산:
   - 배당률 점수: 40%
   - 기수 성적: 30%
   - 말 성적: 30%"

# After (배당률 상관관계가 높은 경우)
"3. 복합 점수 계산:
   - 배당률 점수: 50% (시장 평가의 높은 예측력 반영)
   - 기수 성적: 25%
   - 말 성적: 25%"
```

### 2. 규칙 추가
```python
# Before
"3. 다음 요소들을 종합적으로 고려:
   - 배당률 (시장 평가)
   - 기수 승률 및 최근 성적
   - 말의 최근 입상률"

# After
"3. 다음 요소들을 종합적으로 고려:
   - 배당률 (시장 평가)
   - 기수 승률 및 최근 성적
   - 말의 최근 입상률
   - 기수 승률 15% 이상인 말 우선 고려 (신규)"
```

### 3. 전략 변경
```python
# Before
"4. 상위 3마리 선정"

# After
"4. 상위 3마리 선정 (인기마 2개 + 중위권 1개 균형 선택)"
```

## 안전장치

### 1. 변경 제한
- 한 번에 최대 3개 주요 변경
- 가중치는 최대 ±20% 조정
- 핵심 구조는 유지

### 2. 성능 모니터링
- 변경 후 즉시 평가
- 성능 하락 시 자동 롤백
- A/B 테스트 지원

### 3. 인간 검토
- 주요 변경사항 플래그
- 승인 프로세스 옵션
- 변경 이유 문서화

## 기대 효과

1. **실질적 개선**: 분석 기반의 구체적 변경
2. **안정성**: 점진적 개선으로 리스크 최소화
3. **투명성**: 모든 변경 추적 가능
4. **적응성**: 새로운 패턴에 빠르게 대응

## 구현 우선순위

1. **Phase 1**: 기본 재구성 엔진
   - PromptModifier
   - 기본 변경 적용 로직

2. **Phase 2**: 고급 기능
   - WeightOptimizer
   - ExampleCurator
   - ConflictResolver

3. **Phase 3**: 관리 기능
   - ChangeTracker
   - VersionController
   - 롤백 시스템

---
*작성일: 2025-06-22*
*작성자: Claude Code*
*파일 위치: docs/dynamic-prompt-reconstruction-design.md*
