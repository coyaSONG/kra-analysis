"""
KRA 경마 예측 시스템 - 재귀 프롬프트 개선 v5 모듈

이 패키지는 v5 재귀 개선 시스템의 핵심 모듈들을 포함합니다:
- prompt_parser: 프롬프트 파싱 및 구조화
- insight_analyzer: 인사이트 분석 엔진
- dynamic_reconstructor: 동적 프롬프트 재구성
- examples_manager: 예시 관리 시스템
- guide_loader: 프롬프트 엔지니어링 가이드 로더
- extended_thinking: Extended Thinking Mode 구현
- self_verification: 강화된 자가 검증 시스템
- token_optimizer: 토큰 최적화 엔진
- utils: 공통 유틸리티
"""

__version__ = "5.0.0"
__author__ = "KRA Racing Prediction System"

# 모듈 임포트
from .dynamic_reconstructor import DynamicReconstructor
from .examples_manager import ExamplesManager
from .extended_thinking import ExtendedThinkingEngine
from .guide_loader import PromptEngineeringGuideLoader
from .insight_analyzer import InsightAnalysis, InsightAnalyzer
from .prompt_parser import PromptParser, PromptSection, PromptStructure
from .self_verification import SelfVerificationEngine
from .token_optimizer import TokenOptimizationEngine

__all__ = [
    'PromptParser',
    'PromptStructure',
    'PromptSection',
    'InsightAnalyzer',
    'InsightAnalysis',
    'DynamicReconstructor',
    'ExamplesManager',
    'PromptEngineeringGuideLoader',
    'ExtendedThinkingEngine',
    'SelfVerificationEngine',
    'TokenOptimizationEngine'
]
