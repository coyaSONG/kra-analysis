"""
Unit tests for authentication and authorization
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
from fastapi import HTTPException, status

from dependencies.auth import verify_api_key, require_api_key, create_access_token
from models.database_models import APIKey
from infrastructure.redis_client import CacheService


class TestAuthentication:
    """Test authentication functions"""
    
    @pytest.mark.unit
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_verify_api_key_valid(self, db_session):
        """Test verifying a valid API key"""
        # Create test API key
        api_key = APIKey(
            key="valid-api-key-123456",
            name="Test Key",
            is_active=True,
            created_at=datetime.utcnow()
        )
        db_session.add(api_key)
        await db_session.commit()
        
        # Verify the key
        result = await verify_api_key("valid-api-key-123456", db_session)
        
        assert result is not None
        assert result.key == "valid-api-key-123456"
        assert result.is_active is True
    
    @pytest.mark.unit
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_verify_api_key_invalid_format(self, db_session):
        """Test verifying API key with invalid format"""
        # Test too short key
        result = await verify_api_key("short", db_session)
        assert result is None
        
        # Test invalid characters
        result = await verify_api_key("invalid@key#123", db_session)
        assert result is None
    
    @pytest.mark.unit
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_verify_api_key_not_found(self, db_session):
        """Test verifying non-existent API key"""
        result = await verify_api_key("non-existent-key-123456", db_session)
        assert result is None
    
    @pytest.mark.unit
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_verify_api_key_inactive(self, db_session):
        """Test verifying inactive API key"""
        # Create inactive API key
        api_key = APIKey(
            key="inactive-api-key-123456",
            name="Inactive Key",
            is_active=False,
            created_at=datetime.utcnow()
        )
        db_session.add(api_key)
        await db_session.commit()
        
        result = await verify_api_key("inactive-api-key-123456", db_session)
        assert result is None
    
    @pytest.mark.unit
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_verify_api_key_expired(self, db_session):
        """Test verifying expired API key"""
        # Create expired API key
        api_key = APIKey(
            key="expired-api-key-123456",
            name="Expired Key",
            is_active=True,
            expires_at=datetime.utcnow() - timedelta(days=1),
            created_at=datetime.utcnow() - timedelta(days=30)
        )
        db_session.add(api_key)
        await db_session.commit()
        
        result = await verify_api_key("expired-api-key-123456", db_session)
        assert result is None
    
    @pytest.mark.unit
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_require_api_key_valid(self, db_session):
        """Test require_api_key with valid key"""
        # Create test API key
        api_key = APIKey(
            key="valid-api-key-123456",
            name="Test Key",
            is_active=True,
            created_at=datetime.utcnow()
        )
        db_session.add(api_key)
        await db_session.commit()
        
        # Test the dependency
        result = await require_api_key(
            api_key="valid-api-key-123456",
            db=db_session
        )
        
        assert result == "valid-api-key-123456"
    
    @pytest.mark.unit
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_require_api_key_missing(self, db_session):
        """Test require_api_key with missing key"""
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(api_key=None, db=db_session)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "API key required"
    
    @pytest.mark.unit
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_require_api_key_invalid(self, db_session):
        """Test require_api_key with invalid key"""
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(
                api_key="invalid-key-123456",
                db=db_session
            )
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid API key"
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_create_access_token(self):
        """Test JWT token creation"""
        from unittest.mock import patch
        
        with patch('dependencies.auth.settings') as mock_settings:
            mock_settings.secret_key = "test-secret-key"
            mock_settings.algorithm = "HS256"
            mock_settings.access_token_expire_minutes = 30
            
            data = {"sub": "test-user", "role": "admin"}
            token = create_access_token(data)
            
            assert token is not None
            assert isinstance(token, str)
            assert len(token) > 0
    
    @pytest.mark.unit
    @pytest.mark.auth
    def test_create_access_token_with_expiry(self):
        """Test JWT token creation with custom expiry"""
        from unittest.mock import patch
        
        with patch('dependencies.auth.settings') as mock_settings:
            mock_settings.secret_key = "test-secret-key"
            mock_settings.algorithm = "HS256"
            
            data = {"sub": "test-user"}
            expires_delta = timedelta(minutes=15)
            token = create_access_token(data, expires_delta)
            
            assert token is not None
            assert isinstance(token, str)


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    @pytest.mark.unit
    @pytest.mark.auth
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="CacheService.check_rate_limit not implemented yet")
    async def test_rate_limit_check(self, redis_client):
        """Test rate limit checking"""
        cache_service = CacheService()
        cache_service.redis = redis_client
        
        # First request should pass
        key = "test-rate-limit"
        result = await cache_service.check_rate_limit(key, limit=5, window=60)
        assert result is True
        
        # Requests within limit should pass
        for _ in range(4):
            result = await cache_service.check_rate_limit(key, limit=5, window=60)
            assert result is True
        
        # Request exceeding limit should fail
        result = await cache_service.check_rate_limit(key, limit=5, window=60)
        assert result is False
    
    @pytest.mark.unit
    @pytest.mark.auth
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="CacheService.check_rate_limit not implemented yet")
    async def test_rate_limit_reset(self, redis_client):
        """Test rate limit reset after window"""
        cache_service = CacheService()
        cache_service.redis = redis_client
        
        key = "test-rate-limit-reset"
        
        # Use up the limit
        for _ in range(5):
            await cache_service.check_rate_limit(key, limit=5, window=1)
        
        # Should be blocked
        result = await cache_service.check_rate_limit(key, limit=5, window=1)
        assert result is False
        
        # Wait for window to expire
        import asyncio
        await asyncio.sleep(1.1)
        
        # Should be allowed again
        result = await cache_service.check_rate_limit(key, limit=5, window=1)
        assert result is True