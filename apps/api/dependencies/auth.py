"""
인증 및 권한 관리 의존성
API 키 및 JWT 토큰 검증
"""

import re
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import Depends, Header, HTTPException, Request, status
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from infrastructure.database import get_db
from models.database_models import APIKey

logger = structlog.get_logger()


async def verify_api_key(api_key: str, db: AsyncSession) -> APIKey | None:
    """API 키 검증 및 정보 반환"""
    try:
        # API 키 형식 검증 (알파벳, 숫자, 하이픈, 언더스코어)
        if not re.match(r"^[a-zA-Z0-9\-_]{10,128}$", api_key):
            logger.warning("Invalid API key format", key_length=len(api_key))
            return None

        # 환경 변수에서 로드된 키 확인
        if api_key in settings.valid_api_keys:
            return APIKey(
                key=api_key,
                name="Environment Key",
                is_active=True,
                permissions=["read", "write"],
                rate_limit=100,
            )

        # 데이터베이스에서 키 조회 - 파라미터화된 쿼리 사용
        result = await db.execute(
            select(APIKey).where(APIKey.key == api_key, APIKey.is_active.is_(True))
        )
        api_key_obj = result.scalar_one_or_none()

        if not api_key_obj:
            return None

        # 만료 확인
        if api_key_obj.expires_at and api_key_obj.expires_at < datetime.now(UTC):
            return None

        # 마지막 사용 시간과 사용량 업데이트 (timezone-naive datetime 유지)
        current_time = datetime.now(UTC)
        previous_last_used = api_key_obj.last_used_at

        api_key_obj.last_used_at = current_time
        api_key_obj.total_requests = (api_key_obj.total_requests or 0) + 1

        # 일일 사용량 리셋 확인
        today_requests = api_key_obj.today_requests or 0
        if previous_last_used is None:
            api_key_obj.today_requests = 1
        else:
            today = current_time.date()
            if previous_last_used.date() < today:
                api_key_obj.today_requests = 1
            else:
                api_key_obj.today_requests = today_requests + 1

        await db.commit()

        return api_key_obj

    except Exception as e:
        logger.error(f"API key verification failed: {e}")
        return None


async def require_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    api_key: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> str:
    """API 키 필수 의존성"""
    # Missing header -> 401 with clear message
    provided_key = (
        x_api_key
        if isinstance(x_api_key, str)
        else (api_key if isinstance(api_key, str) else None)
    )
    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required"
        )

    api_key_obj = await verify_api_key(provided_key, db)

    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    # 일일 한도 확인
    if (
        api_key_obj.daily_limit
        and api_key_obj.today_requests
        and api_key_obj.today_requests > api_key_obj.daily_limit
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily request limit exceeded",
        )

    return provided_key


async def require_permissions(
    required_permissions: list[str],
    api_key_obj: APIKey = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> APIKey:
    """특정 권한 필요 의존성"""
    # api_key_obj is already validated by require_api_key dependency

    # 권한 확인
    user_permissions: list[str] = api_key_obj.permissions or []
    if not all(perm in user_permissions for perm in required_permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    return api_key_obj


# JWT 토큰 관련 (선택적 구현)
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def verify_token(token: str) -> dict | None:
    """JWT 토큰 검증"""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        return None


async def get_current_user(
    authorization: str | None = Header(None), db: AsyncSession = Depends(get_db)
) -> dict | None:
    """현재 사용자 정보 반환 (JWT 사용 시)"""
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ")[1]
    payload = verify_token(token)

    if not payload:
        return None

    return payload


# 권한 체크 데코레이터 (편의 함수)
async def _require_admin_permissions(
    api_key_obj: APIKey = Depends(require_api_key), db: AsyncSession = Depends(get_db)
) -> APIKey:
    """관리자 권한 확인"""
    return await require_permissions(["admin"], api_key_obj, db)


async def _require_write_permissions(
    api_key_obj: APIKey = Depends(require_api_key), db: AsyncSession = Depends(get_db)
) -> APIKey:
    """쓰기 권한 확인"""
    return await require_permissions(["write"], api_key_obj, db)


def require_admin(api_key_obj: APIKey = Depends(_require_admin_permissions)):
    """관리자 권한 필요"""
    return api_key_obj


def require_write(api_key_obj: APIKey = Depends(_require_write_permissions)):
    """쓰기 권한 필요"""
    return api_key_obj


async def check_resource_access(
    resource_type: str, resource_id: str, api_key: APIKey, db: AsyncSession
) -> bool:
    """
    리소스 접근 권한 확인

    Args:
        resource_type: 리소스 타입 (race, job, prediction 등)
        resource_id: 리소스 ID
        api_key: API 키 객체
        db: 데이터베이스 세션

    Returns:
        접근 가능 여부
    """
    # 관리자는 모든 리소스 접근 가능
    if "admin" in (api_key.permissions or []):
        return True

    # 리소스별 접근 권한 체크
    if resource_type == "race":
        # 경주 데이터는 읽기 권한만 있으면 접근 가능
        return "read" in (api_key.permissions or [])

    elif resource_type == "job":
        # 작업은 생성자만 접근 가능
        from models.database_models import Job

        result = await db.execute(
            select(Job).where(Job.job_id == resource_id, Job.created_by == api_key.name)
        )
        job = result.scalar_one_or_none()
        return job is not None

    elif resource_type == "prediction":
        # 예측은 API 키로 생성된 것만 접근 가능
        from models.database_models import Prediction

        result = await db.execute(
            select(Prediction).where(Prediction.prediction_id == resource_id)
        )
        prediction = result.scalar_one_or_none()
        # TODO: prediction에 created_by 필드 추가 필요
        return prediction is not None

    # 기본적으로 접근 거부
    return False


def require_resource_access(resource_type: str, resource_id_param: str = "resource_id"):
    """
    리소스 접근 권한 데코레이터

    Usage:
        @router.get("/jobs/{job_id}")
        async def get_job(
            job_id: str,
            auth: Depends(require_resource_access("job", "job_id"))
        ):
            ...
    """

    async def dependency(
        request: Request,
        api_key: APIKey = Depends(require_api_key),
        db: AsyncSession = Depends(get_db),
    ):
        # Get api_key_obj from require_api_key
        # Resolve API key object for permission checks
        api_key_value = request.headers.get("X-API-Key", "")
        api_key_obj = await verify_api_key(api_key_value, db)
        if not api_key_obj:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
            )

        resource_id = request.path_params.get(resource_id_param)

        if not resource_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Resource ID '{resource_id_param}' not found in path",
            )

        has_access = await check_resource_access(
            resource_type, resource_id, api_key_obj, db
        )

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to {resource_type} resource",
            )

        return api_key_obj

    return dependency
