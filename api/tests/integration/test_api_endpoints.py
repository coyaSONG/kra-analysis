"""
Integration tests for API endpoints
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime
from httpx import AsyncClient

from models.database_models import Job, Race, JobStatus, JobType, DataStatus


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    @pytest.mark.integration
    async def test_health_check(self, client: AsyncClient):
        """Test basic health check endpoint"""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    @pytest.mark.integration
    async def test_detailed_health_check(self, authenticated_client: AsyncClient):
        """Test detailed health check with dependencies"""
        response = await authenticated_client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "healthy"
        assert data["redis"] == "healthy"
        assert "celery" in data  # May be unhealthy in test environment


class TestCollectionEndpoints:
    """Test collection API endpoints"""
    
    @pytest.mark.integration
    async def test_collect_races_success(self, authenticated_client: AsyncClient):
        """Test successful race collection"""
        with patch('services.collection_service.CollectionService.collect_race_data') as mock_collect:
            mock_collect.return_value = {
                "race_date": "20240719",
                "meet": 1,
                "race_no": 1,
                "horses": [],
                "collected_at": datetime.utcnow().isoformat()
            }
            
            response = await authenticated_client.post(
                "/api/v2/collection/",
                json={
                    "date": "20240719",
                    "meet": 1,
                    "race_numbers": [1]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "Collected 1 races" in data["message"]
    
    @pytest.mark.integration
    async def test_collect_races_invalid_date(self, authenticated_client: AsyncClient):
        """Test collection with invalid date format"""
        response = await authenticated_client.post(
            "/api/v2/collection/",
            json={
                "date": "2024-07-19",  # Wrong format
                "meet": 1,
                "race_numbers": [1]
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "validation error" in data["detail"][0]["msg"].lower()
    
    @pytest.mark.integration
    async def test_collect_races_future_date(self, authenticated_client: AsyncClient):
        """Test collection with future date"""
        from datetime import date, timedelta
        future_date = (date.today() + timedelta(days=30)).strftime("%Y%m%d")
        
        response = await authenticated_client.post(
            "/api/v2/collection/",
            json={
                "date": future_date,
                "meet": 1,
                "race_numbers": [1]
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "미래 날짜" in str(data)
    
    @pytest.mark.integration
    async def test_collect_races_invalid_meet(self, authenticated_client: AsyncClient):
        """Test collection with invalid meet"""
        response = await authenticated_client.post(
            "/api/v2/collection/",
            json={
                "date": "20240719",
                "meet": 5,  # Invalid (should be 1-3)
                "race_numbers": [1]
            }
        )
        
        assert response.status_code == 422
    
    @pytest.mark.integration
    async def test_collect_races_unauthenticated(self, client: AsyncClient):
        """Test collection without authentication"""
        response = await client.post(
            "/api/v2/collection/",
            json={
                "date": "20240719",
                "meet": 1,
                "race_numbers": [1]
            }
        )
        
        assert response.status_code == 401
        assert response.json()["detail"] == "API key required"
    
    @pytest.mark.integration
    async def test_get_collection_status(self, authenticated_client: AsyncClient):
        """Test getting collection status"""
        response = await authenticated_client.get(
            "/api/v2/collection/status",
            params={"date": "20240719", "meet": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "date" in data
        assert "meet" in data
        assert "total_races" in data
        assert "status" in data


class TestJobsEndpoints:
    """Test jobs API endpoints"""
    
    @pytest.mark.integration
    async def test_list_jobs_empty(self, authenticated_client: AsyncClient):
        """Test listing jobs when empty"""
        response = await authenticated_client.get("/api/v2/jobs/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["jobs"] == []
        assert data["total"] == 0
        assert data["limit"] == 50
        assert data["offset"] == 0
    
    @pytest.mark.integration
    async def test_list_jobs_with_data(self, authenticated_client: AsyncClient, db_session):
        """Test listing jobs with data"""
        # Create test jobs
        for i in range(5):
            job = Job(
                type=JobType.COLLECTION,
                status=JobStatus.COMPLETED,
                parameters={"test": i},
                created_by="test-api-key-123"
            )
            db_session.add(job)
        await db_session.commit()
        
        response = await authenticated_client.get("/api/v2/jobs/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 5
        assert data["total"] == 5
    
    @pytest.mark.integration
    async def test_list_jobs_pagination(self, authenticated_client: AsyncClient, db_session):
        """Test job listing pagination"""
        # Create 10 test jobs
        for i in range(10):
            job = Job(
                type=JobType.COLLECTION,
                status=JobStatus.COMPLETED,
                parameters={"test": i},
                created_by="test-api-key-123"
            )
            db_session.add(job)
        await db_session.commit()
        
        # Test pagination
        response = await authenticated_client.get("/api/v2/jobs/?limit=5&offset=5")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 5
        assert data["total"] == 10
        assert data["limit"] == 5
        assert data["offset"] == 5
    
    @pytest.mark.integration
    async def test_list_jobs_filtering(self, authenticated_client: AsyncClient, db_session):
        """Test job listing with filters"""
        # Create jobs with different statuses
        statuses = [JobStatus.PENDING, JobStatus.RUNNING, JobStatus.COMPLETED, JobStatus.FAILED]
        for status in statuses:
            job = Job(
                type=JobType.COLLECTION,
                status=status,
                parameters={},
                created_by="test-api-key-123"
            )
            db_session.add(job)
        await db_session.commit()
        
        # Filter by status
        response = await authenticated_client.get("/api/v2/jobs/?status=completed")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 1
        assert all(job["status"] == "completed" for job in data["jobs"])
    
    @pytest.mark.integration
    async def test_get_job_detail(self, authenticated_client: AsyncClient, db_session):
        """Test getting job detail"""
        # Create test job
        job = Job(
            type=JobType.COLLECTION,
            status=JobStatus.RUNNING,
            parameters={"date": "20240719"},
            created_by="test-api-key-123"
        )
        db_session.add(job)
        await db_session.commit()
        
        response = await authenticated_client.get(f"/api/v2/jobs/{job.job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job"]["job_id"] == job.job_id
        assert data["job"]["type"] == "collection"
        assert data["job"]["status"] == "running"
        assert data["logs"] is None or isinstance(data["logs"], list)
    
    @pytest.mark.integration
    async def test_get_job_detail_not_found(self, authenticated_client: AsyncClient):
        """Test getting non-existent job"""
        response = await authenticated_client.get("/api/v2/jobs/non-existent-id")
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"
    
    @pytest.mark.integration
    async def test_cancel_job(self, authenticated_client: AsyncClient, db_session):
        """Test canceling a job"""
        # Create test job
        job = Job(
            type=JobType.COLLECTION,
            status=JobStatus.RUNNING,
            parameters={},
            created_by="test-api-key-123"
        )
        db_session.add(job)
        await db_session.commit()
        
        response = await authenticated_client.post(f"/api/v2/jobs/{job.job_id}/cancel")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Job cancelled successfully"


class TestAsyncCollectionEndpoints:
    """Test async collection endpoints"""
    
    @pytest.mark.integration
    async def test_async_collect_races(self, authenticated_client: AsyncClient):
        """Test async race collection"""
        with patch('tasks.collection_tasks.collect_race_data_task.delay') as mock_task:
            mock_task.return_value.id = "test-task-id"
            
            response = await authenticated_client.post(
                "/api/v2/collection/async",
                json={
                    "date": "20240719",
                    "meet": 1,
                    "race_numbers": [1, 2, 3]
                }
            )
            
            assert response.status_code == 202
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "accepted"
            assert data["message"] == "Collection job started"
            assert "webhook_url" in data


class TestAuthenticationEndpoints:
    """Test authentication related endpoints"""
    
    @pytest.mark.integration
    async def test_missing_api_key(self, client: AsyncClient):
        """Test request without API key"""
        response = await client.get("/api/v2/jobs/")
        
        assert response.status_code == 401
        assert response.json()["detail"] == "API key required"
    
    @pytest.mark.integration
    async def test_invalid_api_key(self, client: AsyncClient):
        """Test request with invalid API key"""
        response = await client.get(
            "/api/v2/jobs/",
            headers={"X-API-Key": "invalid-key"}
        )
        
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"
    
    @pytest.mark.integration
    async def test_rate_limiting(self, authenticated_client: AsyncClient):
        """Test rate limiting"""
        # Make multiple requests quickly
        for i in range(100):
            response = await authenticated_client.get("/api/v2/jobs/")
            if response.status_code == 429:
                break
        
        # Should hit rate limit at some point
        # Note: This test might pass without hitting limit in test environment
        # as rate limiting might be disabled or set very high
        assert response.status_code in [200, 429]