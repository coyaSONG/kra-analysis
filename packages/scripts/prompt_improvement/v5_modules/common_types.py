"""
공통 타입 정의
순환 참조를 피하기 위해 공통으로 사용되는 타입들을 별도로 정의합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Change:
    """개별 변경사항을 표현하는 클래스"""
    change_type: str  # 'modify', 'add', 'remove'
    target_section: str
    description: str
    old_value: str | None = None
    new_value: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
