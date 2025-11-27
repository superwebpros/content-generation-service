"""
Tests for LoRA Training Service
TDD approach - tests written first
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app import app

@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "lora-training-worker"
        assert "timestamp" in data

@pytest.mark.asyncio
async def test_train_endpoint_accepts_valid_request():
    """Test that train endpoint accepts valid training request"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "job_id": "test-job-123",
            "user_id": "test-user",
            "video_url": "https://example.com/video.mp4",
            "lora_name": "test_lora",
            "trigger": "person",
            "steps": 2500,
            "learning_rate": 0.00009
        }

        response = await client.post("/train", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "test-job-123"
        assert data["status"] in ["processing", "queued"]

@pytest.mark.asyncio
async def test_train_endpoint_uses_defaults():
    """Test that optional parameters use defaults"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "job_id": "test-job-456",
            "user_id": "test-user",
            "video_url": "https://example.com/video.mp4",
            "lora_name": "test_lora"
            # No trigger, steps, learning_rate
        }

        response = await client.post("/train", json=payload)

        assert response.status_code == 200

@pytest.mark.asyncio
async def test_train_endpoint_validates_required_fields():
    """Test that missing required fields return 422"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "job_id": "test-job-789",
            "user_id": "test-user"
            # Missing video_url and lora_name
        }

        response = await client.post("/train", json=payload)

        assert response.status_code == 422  # FastAPI validation error

@pytest.mark.asyncio
async def test_train_endpoint_validates_steps_range():
    """Test that steps are validated (1000-10000)"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "job_id": "test-job-999",
            "user_id": "test-user",
            "video_url": "https://example.com/video.mp4",
            "lora_name": "test_lora",
            "steps": 100  # Too low
        }

        response = await client.post("/train", json=payload)

        assert response.status_code == 422

# TODO: Add integration tests that:
# - Mock MongoDB updates
# - Mock S3 uploads
# - Mock fal.ai API calls
# - Test full training pipeline
# - Test error handling and retries
