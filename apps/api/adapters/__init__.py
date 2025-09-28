"""
Adapters 패키지
외부 API 응답을 내부 도메인 객체로 변환하는 어댑터들
"""

from .kra_response_adapter import KRAResponseAdapter

__all__ = ["KRAResponseAdapter"]
