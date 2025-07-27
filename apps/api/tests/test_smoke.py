"""
Smoke tests to verify basic test infrastructure
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient


class TestSmoke:
    """Basic smoke tests"""
    
    @pytest.mark.smoke
    def test_pytest_works(self):
        """Test that pytest is working"""
        assert True
    
    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_async_works(self):
        """Test that async tests work"""
        import asyncio
        await asyncio.sleep(0.001)
        assert True
    
    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_client_fixture_works(self, client: AsyncClient):
        """Test that client fixture works"""
        assert client is not None
        assert client.base_url == "http://test"
    
    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        """Test basic health endpoint"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"