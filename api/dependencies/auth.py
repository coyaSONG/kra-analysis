"""
인증 및 권한 관리 의존성
API 키 및 JWT 토큰 검증
"""

from fastapi import Depends, HTTPException, Header, status
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import jwt
import structlog

from config import settings
from infrastructure.database import get_db
from models.database_models import APIKey

logger = structlog.get_logger()


async def verify_api_key(
    api_key: str,
    db: AsyncSession
) -> Optional[APIKey]:
    """API 키 검증 및 정보 반환"""
    try:
        # 데모/테스트 키 확인
        if api_key in settings.valid_api_keys:
            return APIKey(
                key=api_key,
                name="Demo Key",
                is_active=True,
                permissions=["read", "write"],
                rate_limit=100
            )
        
        # 데이터베이스에서 키 조회
        result = await db.execute(
            select(APIKey).where(
                APIKey.key == api_key,
                APIKey.is_active == True
            )
        )
        api_key_obj = result.scalar_one_or_none()
        
        if not api_key_obj:
            return None
        
        # 만료 확인
        if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
            return None
        
        # 마지막 사용 시간 업데이트
        api_key_obj.last_used_at = datetime.utcnow()
        api_key_obj.total_requests += 1
        
        # 일일 사용량 리셋 확인
        today = datetime.utcnow().date()
        if api_key_obj.last_used_at and api_key_obj.last_used_at.date() < today:
            api_key_obj.today_requests = 1
        else:
            api_key_obj.today_requests += 1
        
        await db.commit()
        
        return api_key_obj
        
    except Exception as e:
        logger.error(f"API key verification failed: {e}")
        return None


async def require_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db)
) -> str:
    """API 키 필수 의존성"""
    api_key_obj = await verify_api_key(x_api_key, db)
    
    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key"
        )
    
    # 일일 한도 확인
    if (api_key_obj.daily_limit and 
        hasattr(api_key_obj, 'today_requests') and 
        api_key_obj.today_requests > api_key_obj.daily_limit):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily request limit exceeded"
        )
    
    return x_api_key


async def require_permissions(
    required_permissions: List[str],
    api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db)
) -> APIKey:
    """특정 권한 필요 의존성"""
    api_key_obj = await verify_api_key(api_key, db)
    
    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # 권한 확인
    user_permissions = api_key_obj.permissions or []
    if not all(perm in user_permissions for perm in required_permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    return api_key_obj


# JWT 토큰 관련 (선택적 구현)
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.secret_key, 
        algorithm=settings.algorithm
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """JWT 토큰 검증"""
    try:
        payload = jwt.decode(
            token, 
            settings.secret_key, 
            algorithms=[settings.algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        return None


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[dict]:
    """현재 사용자 정보 반환 (JWT 사용 시)"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    if not payload:
        return None
    
    return payload


# 권한 체크 데코레이터 (편의 함수)
def require_admin(api_key_obj: APIKey = Depends(lambda: require_permissions(["admin"]))):
    """관리자 권한 필요"""
    return api_key_obj


def require_write(api_key_obj: APIKey = Depends(lambda: require_permissions(["write"]))):
    """쓰기 권한 필요"""
    return api_key_obj