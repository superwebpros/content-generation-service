"""
Pytest configuration and fixtures
Mocks for external services to avoid API costs
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import os

# Set test environment
os.environ['NODE_ENV'] = 'test'


@pytest.fixture
def mock_fal_provider():
    """Mock fal.ai provider to avoid $6/training cost"""
    with patch('providers.fal_ai.create_fal_provider') as mock_create:
        mock_provider = Mock()
        mock_provider.train = Mock(return_value=Mock(
            lora_url='https://mock-fal-cdn.com/trained-lora.safetensors',
            config_url='https://mock-fal-cdn.com/config.json',
            model_name='mock_lora_model'
        ))
        mock_create.return_value = mock_provider
        yield mock_provider


@pytest.fixture
def mock_s3_storage():
    """Mock S3 operations"""
    with patch('s3_storage.s3_storage') as mock_s3:
        mock_s3.upload_file = Mock(return_value='https://mock-s3.com/uploaded-file.safetensors')
        mock_s3.upload_directory = Mock(return_value=['https://mock-s3.com/file1.jpg'])
        mock_s3.download_from_url = Mock()  # No-op for downloads
        mock_s3.get_file_size = Mock(return_value=125000000)  # 125MB
        yield mock_s3


@pytest.fixture
def mock_mongodb():
    """Mock MongoDB operations"""
    with patch('db.db') as mock_db:
        mock_db.update_job_status = AsyncMock()
        mock_db.add_version = AsyncMock()
        mock_db.get_job = AsyncMock(return_value={
            'jobId': 'test-job-123',
            'userId': 'test-user',
            'type': 'lora-training',
            'config': {'trigger': 'person'},
            'webhookUrl': None,
            'versions': []
        })
        yield mock_db


@pytest.fixture
def mock_video_processor():
    """Mock video processing"""
    with patch('core.video_processor.VideoProcessor') as mock_vp:
        mock_instance = Mock()
        mock_instance.process_video = Mock(return_value={
            "frames": [f"/tmp/frame_{i:04d}.jpg" for i in range(25)],
            "video_id": "test-video",
            "frame_count": 25
        })
        mock_vp.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_dataset_builder():
    """Mock dataset building"""
    with patch('core.dataset_builder.DatasetBuilder') as mock_db:
        mock_instance = Mock()
        mock_instance.build_dataset = Mock(return_value=Mock(
            dataset_dir='/tmp/mock-dataset',
            frame_count=25,
            caption_count=25
        ))
        mock_db.return_value = mock_instance
        yield mock_instance
