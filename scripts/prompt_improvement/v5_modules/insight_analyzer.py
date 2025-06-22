"""
인사이트 분석 엔진

enriched 데이터를 심층 분석하여 실질적이고 구체적인 
프롬프트 개선 방향을 도출합니다.
"""

from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import statistics
import json


@dataclass
class Pattern:
    """발견된 패턴을 표현하는 클래스"""
    pattern_type: str  # 'success' or 'failure'
    description: str
    frequency: float  # 발생 빈도
    confidence: float  # 신뢰도
    examples: List[Dict] = field(default_factory=list)


@dataclass
class Recommendation:
    """개선 권고사항을 표현하는 클래스"""
    type: str  # 'weight_adjustment', 'add_rule', 'strategy_change' 등
    priority: str  # 'high', 'medium', 'low'
    description: str
    target: Optional[str] = None
    action: Optional[str] = None
    value: Optional[Any] = None
    reason: Optional[str] = None
    expected_improvement: Optional[str] = None


@dataclass
class InsightAnalysis:
    """전체 인사이트 분석 결과"""
    summary: Dict[str, Any] = field(default_factory=dict)
    detailed_analysis: Dict[str, Dict] = field(default_factory=dict)
    patterns: Dict[str, List[Pattern]] = field(default_factory=dict)
    correlations: Dict[str, float] = field(default_factory=dict)
    recommendations: List[Recommendation] = field(default_factory=list)
    
    def get_recommendations(self) -> List[Recommendation]:
        """우선순위별로 정렬된 권고사항 반환"""
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        return sorted(
            self.recommendations,
            key=lambda r: priority_order.get(r.priority, 3)
        )


class DataAnalyzer:
    """기본 데이터 분석기"""
    
    def prepare_analysis_data(self, evaluation_results: List[Dict]) -> Dict[str, List]:
        """평가 결과를 분석용 데이터로 준비"""
        prepared_data = {
            'successful_predictions': [],
            'failed_predictions': [],
            'partial_predictions': [],
            'all_races': []
        }
        
        for result in evaluation_results:
            if not result.get('actual') or not result.get('predicted'):
                continue
            
            race_data = {
                'race_id': result.get('race_id', ''),
                'predicted': result.get('predicted', []),
                'actual': result.get('actual', []),
                'correct_count': result.get('reward', {}).get('correct_count', 0),
                'race_data': result.get('race_data', {})
            }
            
            prepared_data['all_races'].append(race_data)
            
            if race_data['correct_count'] == 3:
                prepared_data['successful_predictions'].append(race_data)
            elif race_data['correct_count'] == 0:
                prepared_data['failed_predictions'].append(race_data)
            else:
                prepared_data['partial_predictions'].append(race_data)
        
        return prepared_data


class OddsAnalyzer:
    """배당률 분석기"""
    
    def analyze_odds_distribution(self, races: List[Dict]) -> Dict[str, Any]:
        """배당률 분포 및 성공 패턴 분석"""
        analysis = {
            'odds_rank_success_rate': {},
            'popular_vs_unpopular': {},
            'odds_correlation': 0.0,
            'insights': []
        }
        
        # 인기순위별 적중률 계산
        rank_hits = defaultdict(lambda: {'total': 0, 'hits': 0})
        
        for race in races:
            if not race.get('race_data', {}).get('entries'):
                continue
                
            entries = race['race_data']['entries']
            # 배당률 기준으로 정렬 (낮은 배당률 = 인기마)
            sorted_entries = sorted(
                [e for e in entries if e.get('win_odds', 0) > 0],
                key=lambda x: x['win_odds']
            )
            
            # 순위 매기기
            odds_ranks = {e['horse_no']: i+1 for i, e in enumerate(sorted_entries)}
            
            # 예측과 실제 결과의 인기순위 확인
            for horse_no in race['predicted']:
                rank = odds_ranks.get(horse_no, 99)
                rank_hits[rank]['total'] += 1
                if horse_no in race['actual']:
                    rank_hits[rank]['hits'] += 1
        
        # 적중률 계산
        for rank, data in rank_hits.items():
            if data['total'] > 0:
                analysis['odds_rank_success_rate'][rank] = {
                    'success_rate': data['hits'] / data['total'],
                    'total_picks': data['total']
                }
        
        # 인기마(1-3위) vs 비인기마 분석
        popular_picks = sum(
            data['total'] for rank, data in rank_hits.items() if rank <= 3
        )
        unpopular_picks = sum(
            data['total'] for rank, data in rank_hits.items() if rank > 3
        )
        
        if popular_picks + unpopular_picks > 0:
            analysis['popular_vs_unpopular'] = {
                'popular_ratio': popular_picks / (popular_picks + unpopular_picks),
                'unpopular_ratio': unpopular_picks / (popular_picks + unpopular_picks)
            }
        
        # 인사이트 도출
        if analysis['popular_vs_unpopular'].get('popular_ratio', 0) < 0.3:
            analysis['insights'].append("인기마(배당률 1-3위)를 과도하게 회피하는 경향")
        elif analysis['popular_vs_unpopular'].get('popular_ratio', 0) > 0.7:
            analysis['insights'].append("인기마에 과도하게 의존하는 경향")
        
        return analysis


class JockeyAnalyzer:
    """기수 분석기"""
    
    def analyze_jockey_performance(self, races: List[Dict]) -> Dict[str, Any]:
        """기수 성적과 예측 성공률의 관계 분석"""
        analysis = {
            'jockey_winrate_correlation': {},
            'high_winrate_success': 0.0,
            'insights': []
        }
        
        # 기수 승률별 성공률 분석
        winrate_groups = {
            'high': {'threshold': 15, 'total': 0, 'hits': 0},
            'medium': {'threshold': 10, 'total': 0, 'hits': 0},
            'low': {'threshold': 0, 'total': 0, 'hits': 0}
        }
        
        for race in races:
            if not race.get('race_data', {}).get('entries'):
                continue
            
            for horse_no in race['predicted']:
                # 해당 말의 기수 정보 찾기
                entry = next(
                    (e for e in race['race_data']['entries'] 
                     if e.get('horse_no') == horse_no),
                    None
                )
                
                if entry and entry.get('jkDetail'):
                    win_rate = entry['jkDetail'].get('winRate', 0)
                    
                    # 승률 그룹 분류
                    if win_rate >= 15:
                        group = 'high'
                    elif win_rate >= 10:
                        group = 'medium'
                    else:
                        group = 'low'
                    
                    winrate_groups[group]['total'] += 1
                    if horse_no in race['actual']:
                        winrate_groups[group]['hits'] += 1
        
        # 승률별 성공률 계산
        for group, data in winrate_groups.items():
            if data['total'] > 0:
                success_rate = data['hits'] / data['total']
                analysis['jockey_winrate_correlation'][group] = {
                    'success_rate': success_rate,
                    'total_picks': data['total']
                }
        
        # 고승률 기수 성공률
        high_group = winrate_groups['high']
        if high_group['total'] > 0:
            analysis['high_winrate_success'] = high_group['hits'] / high_group['total']
        
        # 인사이트 도출
        if analysis['high_winrate_success'] < 0.3:
            analysis['insights'].append("고승률(15%+) 기수를 충분히 활용하지 못함")
        
        return analysis


class HorseAnalyzer:
    """말 분석기"""
    
    def analyze_horse_factors(self, races: List[Dict]) -> Dict[str, Any]:
        """말의 특성과 예측 성공률의 관계 분석"""
        analysis = {
            'place_rate_correlation': {},
            'recent_form_impact': {},
            'insights': []
        }
        
        # 입상률별 성공률 분석
        place_rate_groups = defaultdict(lambda: {'total': 0, 'hits': 0})
        
        for race in races:
            if not race.get('race_data', {}).get('entries'):
                continue
            
            for horse_no in race['predicted']:
                entry = next(
                    (e for e in race['race_data']['entries'] 
                     if e.get('horse_no') == horse_no),
                    None
                )
                
                if entry and entry.get('hrDetail'):
                    place_rate = entry['hrDetail'].get('placeRate', 0)
                    
                    # 10% 단위로 그룹화
                    group = f"{int(place_rate // 10) * 10}-{int(place_rate // 10) * 10 + 10}%"
                    place_rate_groups[group]['total'] += 1
                    
                    if horse_no in race['actual']:
                        place_rate_groups[group]['hits'] += 1
        
        # 입상률별 성공률 계산
        for group, data in place_rate_groups.items():
            if data['total'] > 0:
                analysis['place_rate_correlation'][group] = {
                    'success_rate': data['hits'] / data['total'],
                    'total_picks': data['total']
                }
        
        return analysis


class PatternMiner:
    """패턴 마이닝 엔진"""
    
    def mine_success_patterns(self, successful_predictions: List[Dict]) -> List[Pattern]:
        """성공 사례에서 패턴 추출"""
        patterns = []
        
        # 1. 배당률 순위 조합 패턴
        odds_rank_combinations = []
        
        for race in successful_predictions:
            if not race.get('race_data', {}).get('entries'):
                continue
            
            entries = race['race_data']['entries']
            sorted_entries = sorted(
                [e for e in entries if e.get('win_odds', 0) > 0],
                key=lambda x: x['win_odds']
            )
            
            odds_ranks = {e['horse_no']: i+1 for i, e in enumerate(sorted_entries)}
            
            # 예측한 말들의 인기순위 조합
            combination = sorted([
                odds_ranks.get(horse_no, 99) 
                for horse_no in race['predicted']
            ])
            odds_rank_combinations.append(tuple(combination))
        
        # 빈도 계산
        combo_counter = Counter(odds_rank_combinations)
        for combo, count in combo_counter.most_common(5):
            if count >= 2:  # 최소 2회 이상 나타난 패턴
                patterns.append(Pattern(
                    pattern_type='success',
                    description=f"인기순위 조합 {combo}",
                    frequency=count / len(successful_predictions),
                    confidence=0.7,
                    examples=[]
                ))
        
        # 2. 기수 승률 패턴
        high_winrate_count = 0
        for race in successful_predictions:
            if not race.get('race_data', {}).get('entries'):
                continue
            
            high_winrate_jockeys = 0
            for horse_no in race['predicted']:
                entry = next(
                    (e for e in race['race_data']['entries'] 
                     if e.get('horse_no') == horse_no),
                    None
                )
                
                if entry and entry.get('jkDetail', {}).get('winRate', 0) >= 15:
                    high_winrate_jockeys += 1
            
            if high_winrate_jockeys >= 2:
                high_winrate_count += 1
        
        if high_winrate_count / len(successful_predictions) > 0.3:
            patterns.append(Pattern(
                pattern_type='success',
                description="고승률(15%+) 기수 2명 이상 포함",
                frequency=high_winrate_count / len(successful_predictions),
                confidence=0.8,
                examples=[]
            ))
        
        return patterns
    
    def analyze_failure_patterns(self, failed_predictions: List[Dict]) -> List[Pattern]:
        """실패 사례에서 패턴 분석"""
        patterns = []
        
        # 1. 극단적 선택 패턴
        extreme_popular = 0  # 모두 인기마
        extreme_unpopular = 0  # 모두 비인기마
        
        for race in failed_predictions:
            if not race.get('race_data', {}).get('entries'):
                continue
            
            entries = race['race_data']['entries']
            sorted_entries = sorted(
                [e for e in entries if e.get('win_odds', 0) > 0],
                key=lambda x: x['win_odds']
            )
            
            odds_ranks = {e['horse_no']: i+1 for i, e in enumerate(sorted_entries)}
            
            predicted_ranks = [
                odds_ranks.get(horse_no, 99) 
                for horse_no in race['predicted']
            ]
            
            if all(rank <= 3 for rank in predicted_ranks):
                extreme_popular += 1
            elif all(rank >= 7 for rank in predicted_ranks):
                extreme_unpopular += 1
        
        if extreme_popular / len(failed_predictions) > 0.2:
            patterns.append(Pattern(
                pattern_type='failure',
                description="모든 선택이 인기마(1-3위)",
                frequency=extreme_popular / len(failed_predictions),
                confidence=0.7,
                examples=[]
            ))
        
        if extreme_unpopular / len(failed_predictions) > 0.2:
            patterns.append(Pattern(
                pattern_type='failure',
                description="모든 선택이 비인기마(7위 이하)",
                frequency=extreme_unpopular / len(failed_predictions),
                confidence=0.7,
                examples=[]
            ))
        
        return patterns


class CorrelationAnalyzer:
    """상관관계 분석기"""
    
    def calculate_feature_importance(self, races: List[Dict]) -> Dict[str, float]:
        """각 특성의 예측력 계산"""
        feature_importance = {
            'win_odds_rank': 0.0,
            'jockey_win_rate': 0.0,
            'horse_place_rate': 0.0,
            'recent_performance': 0.0,
            'weight_change': 0.0
        }
        
        # 간단한 정보 이득 계산 (실제로는 더 정교한 방법 필요)
        # 여기서는 각 특성이 성공 예측에 기여한 정도를 대략적으로 계산
        
        total_predictions = 0
        feature_hits = defaultdict(int)
        
        for race in races:
            if not race.get('race_data', {}).get('entries'):
                continue
            
            for horse_no in race['predicted']:
                total_predictions += 1
                
                if horse_no in race['actual']:
                    # 성공한 예측의 특성 분석
                    entry = next(
                        (e for e in race['race_data']['entries'] 
                         if e.get('horse_no') == horse_no),
                        None
                    )
                    
                    if entry:
                        # 배당률 순위가 3위 이내면 기여
                        sorted_entries = sorted(
                            [e for e in race['race_data']['entries'] 
                             if e.get('win_odds', 0) > 0],
                            key=lambda x: x['win_odds']
                        )
                        rank = next(
                            (i+1 for i, e in enumerate(sorted_entries) 
                             if e.get('horse_no') == horse_no),
                            99
                        )
                        if rank <= 3:
                            feature_hits['win_odds_rank'] += 1
                        
                        # 기수 승률이 15% 이상이면 기여
                        if entry.get('jkDetail', {}).get('winRate', 0) >= 15:
                            feature_hits['jockey_win_rate'] += 1
                        
                        # 입상률이 30% 이상이면 기여
                        if entry.get('hrDetail', {}).get('placeRate', 0) >= 30:
                            feature_hits['horse_place_rate'] += 1
        
        # 정규화
        if total_predictions > 0:
            for feature in feature_importance:
                feature_importance[feature] = feature_hits[feature] / total_predictions
        
        return feature_importance


class RecommendationGenerator:
    """권고사항 생성기"""
    
    def generate_actionable_recommendations(
        self, 
        analysis_results: Dict[str, Any]
    ) -> List[Recommendation]:
        """분석 결과를 기반으로 구체적인 권고사항 생성"""
        recommendations = []
        
        # 1. 배당률 분석 기반 권고
        odds_analysis = analysis_results.get('odds_analysis', {})
        
        # 인기마 활용도 확인
        popular_ratio = odds_analysis.get('popular_vs_unpopular', {}).get('popular_ratio', 0.5)
        if popular_ratio < 0.3:
            recommendations.append(Recommendation(
                type='strategy_change',
                priority='high',
                description='인기마(배당률 1-3위) 선택 비율 증가',
                action='increase_popular_ratio',
                value='2:1',  # 인기마 2개, 중위권 1개
                reason='현재 인기마를 과도하게 회피하여 적중률 저하',
                expected_improvement='5-10% 적중률 향상'
            ))
        
        # 2. 기수 분석 기반 권고
        jockey_analysis = analysis_results.get('jockey_analysis', {})
        high_winrate_success = jockey_analysis.get('high_winrate_success', 0)
        
        if high_winrate_success > 0.5:
            recommendations.append(Recommendation(
                type='add_rule',
                priority='high',
                description='기수 승률 15% 이상인 말 우선 고려',
                target='requirements',
                action='add',
                value='기수 승률 15% 이상인 말은 특별한 결격 사유가 없는 한 포함',
                reason=f'고승률 기수의 성공률이 {high_winrate_success:.1%}로 높음',
                expected_improvement='3-5% 적중률 향상'
            ))
        
        # 3. 가중치 조정 권고
        correlations = analysis_results.get('correlations', {})
        
        # 가장 높은 상관관계를 가진 특성 찾기
        if correlations:
            top_feature = max(correlations.items(), key=lambda x: x[1])
            if top_feature[1] > 0.3:
                weight_map = {
                    'win_odds_rank': 'odds',
                    'jockey_win_rate': 'jockey',
                    'horse_place_rate': 'horse'
                }
                
                if top_feature[0] in weight_map:
                    recommendations.append(Recommendation(
                        type='weight_adjustment',
                        priority='medium',
                        description=f'{weight_map[top_feature[0]]} 가중치 상향 조정',
                        target=weight_map[top_feature[0]],
                        action='increase',
                        value=0.1,  # 10% 증가
                        reason=f'{top_feature[0]}의 예측 기여도가 {top_feature[1]:.1%}로 높음',
                        expected_improvement='2-3% 적중률 향상'
                    ))
        
        # 4. 패턴 기반 권고
        success_patterns = analysis_results.get('patterns', {}).get('success_patterns', [])
        for pattern in success_patterns[:2]:  # 상위 2개 패턴만
            if pattern.confidence > 0.7:
                recommendations.append(Recommendation(
                    type='strategy_change',
                    priority='medium',
                    description=f'성공 패턴 활용: {pattern.description}',
                    action='apply_pattern',
                    value=pattern.description,
                    reason=f'빈도 {pattern.frequency:.1%}, 신뢰도 {pattern.confidence:.1%}',
                    expected_improvement='1-2% 적중률 향상'
                ))
        
        return recommendations


class InsightAnalyzer:
    """통합 인사이트 분석 엔진"""
    
    def __init__(self):
        self.data_analyzer = DataAnalyzer()
        self.odds_analyzer = OddsAnalyzer()
        self.jockey_analyzer = JockeyAnalyzer()
        self.horse_analyzer = HorseAnalyzer()
        self.pattern_miner = PatternMiner()
        self.correlation_analyzer = CorrelationAnalyzer()
        self.recommendation_generator = RecommendationGenerator()
    
    def analyze(self, evaluation_results: List[Dict]) -> InsightAnalysis:
        """종합적인 인사이트 분석 수행"""
        # 1. 데이터 준비
        prepared_data = self.data_analyzer.prepare_analysis_data(evaluation_results)
        
        # 2. 요약 정보
        total_races = len(prepared_data['all_races'])
        successful_races = len(prepared_data['successful_predictions'])
        
        analysis = InsightAnalysis()
        analysis.summary = {
            'total_races_analyzed': total_races,
            'success_rate': (successful_races / total_races * 100) if total_races > 0 else 0,
            'key_findings': []
        }
        
        # 3. 세부 분석
        analysis.detailed_analysis['odds_analysis'] = self.odds_analyzer.analyze_odds_distribution(
            prepared_data['all_races']
        )
        analysis.detailed_analysis['jockey_analysis'] = self.jockey_analyzer.analyze_jockey_performance(
            prepared_data['all_races']
        )
        analysis.detailed_analysis['horse_analysis'] = self.horse_analyzer.analyze_horse_factors(
            prepared_data['all_races']
        )
        
        # 4. 패턴 마이닝
        if prepared_data['successful_predictions']:
            analysis.patterns['success_patterns'] = self.pattern_miner.mine_success_patterns(
                prepared_data['successful_predictions']
            )
        
        if prepared_data['failed_predictions']:
            analysis.patterns['failure_patterns'] = self.pattern_miner.analyze_failure_patterns(
                prepared_data['failed_predictions']
            )
        
        # 5. 상관관계 분석
        analysis.correlations = self.correlation_analyzer.calculate_feature_importance(
            prepared_data['all_races']
        )
        
        # 6. 주요 발견사항 정리
        for key, sub_analysis in analysis.detailed_analysis.items():
            if 'insights' in sub_analysis:
                analysis.summary['key_findings'].extend(sub_analysis['insights'])
        
        # 7. 권고사항 생성
        all_analysis_results = {
            **analysis.detailed_analysis,
            'patterns': analysis.patterns,
            'correlations': analysis.correlations
        }
        
        analysis.recommendations = self.recommendation_generator.generate_actionable_recommendations(
            all_analysis_results
        )
        
        return analysis
    
    def generate_report(self, analysis: InsightAnalysis) -> str:
        """분석 결과를 보고서 형태로 생성"""
        report = []
        
        # 요약
        report.append("## 인사이트 분석 보고서\n")
        report.append(f"### 요약")
        report.append(f"- 분석 경주 수: {analysis.summary['total_races_analyzed']}개")
        report.append(f"- 성공률: {analysis.summary['success_rate']:.1f}%")
        report.append(f"- 주요 발견사항:")
        for finding in analysis.summary['key_findings']:
            report.append(f"  - {finding}")
        
        # 권고사항
        report.append(f"\n### 권고사항")
        for i, rec in enumerate(analysis.get_recommendations(), 1):
            report.append(f"\n{i}. **{rec.description}** (우선순위: {rec.priority})")
            if rec.reason:
                report.append(f"   - 이유: {rec.reason}")
            if rec.expected_improvement:
                report.append(f"   - 예상 효과: {rec.expected_improvement}")
        
        # 세부 분석
        report.append(f"\n### 세부 분석")
        
        # 배당률 분석
        odds = analysis.detailed_analysis.get('odds_analysis', {})
        if odds.get('popular_vs_unpopular'):
            report.append(f"\n#### 배당률 분석")
            report.append(f"- 인기마 선택 비율: {odds['popular_vs_unpopular']['popular_ratio']:.1%}")
            report.append(f"- 비인기마 선택 비율: {odds['popular_vs_unpopular']['unpopular_ratio']:.1%}")
        
        # 기수 분석
        jockey = analysis.detailed_analysis.get('jockey_analysis', {})
        if jockey.get('high_winrate_success'):
            report.append(f"\n#### 기수 분석")
            report.append(f"- 고승률(15%+) 기수 성공률: {jockey['high_winrate_success']:.1%}")
        
        # 패턴 분석
        if analysis.patterns.get('success_patterns'):
            report.append(f"\n#### 성공 패턴")
            for pattern in analysis.patterns['success_patterns'][:3]:
                report.append(f"- {pattern.description} (빈도: {pattern.frequency:.1%})")
        
        return "\n".join(report)


# 테스트용 함수
if __name__ == "__main__":
    # 간단한 테스트
    test_results = [
        {
            'race_id': 'test_1',
            'predicted': [1, 3, 5],
            'actual': [1, 2, 3],
            'reward': {'correct_count': 2},
            'race_data': {
                'entries': [
                    {
                        'horse_no': 1,
                        'win_odds': 2.5,
                        'jkDetail': {'winRate': 18.5},
                        'hrDetail': {'placeRate': 45.2}
                    },
                    {
                        'horse_no': 3,
                        'win_odds': 4.2,
                        'jkDetail': {'winRate': 12.3},
                        'hrDetail': {'placeRate': 32.1}
                    }
                ]
            }
        }
    ]
    
    analyzer = InsightAnalyzer()
    analysis = analyzer.analyze(test_results)
    report = analyzer.generate_report(analysis)
    print(report)