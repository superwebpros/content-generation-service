"""
Test training pipeline with mocks (no real API calls = $0 cost)
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from training_pipeline import TrainingPipeline


@pytest.mark.asyncio
async def test_training_pipeline_completes_successfully(
    mock_fal_provider,
    mock_s3_storage,
    mock_mongodb,
    mock_video_processor,
    mock_dataset_builder
):
    """
    Test full training pipeline without calling real APIs
    This test costs $0 instead of $6!
    """

    pipeline = TrainingPipeline()

    result = await pipeline.process_training_job(
        job_id='test-job-456',
        user_id='test-user',
        video_url='https://example.com/test-video.mp4',
        lora_name='test_avatar',
        trigger='person',
        steps=2500,
        learning_rate=0.00009
    )

    # Verify result
    assert result['modelUrl'] == 'https://mock-s3.com/uploaded-file.safetensors'
    assert 'version' in result
    assert result['sizeBytes'] == 125000000

    # Verify external services were called (but mocked)
    mock_fal_provider.train.assert_called_once()
    assert mock_s3_storage.upload_file.called
    assert mock_s3_storage.upload_directory.called
    mock_mongodb.update_job_status.assert_called()
    mock_mongodb.add_version.assert_called_once()


@pytest.mark.asyncio
async def test_training_pipeline_handles_insufficient_frames(
    mock_fal_provider,
    mock_s3_storage,
    mock_mongodb,
    mock_video_processor,
    mock_dataset_builder
):
    """Test that pipeline fails gracefully with insufficient frames"""

    # Mock dataset with too few frames
    mock_dataset_builder.build_dataset.return_value = Mock(
        dataset_dir='/tmp/mock',
        frame_count=5,  # Less than MIN_FRAMES (15)
        caption_count=5
    )

    pipeline = TrainingPipeline()

    with pytest.raises(ValueError, match="Insufficient frames"):
        await pipeline.process_training_job(
            job_id='test-job-789',
            user_id='test-user',
            video_url='https://example.com/short-video.mp4',
            lora_name='test_lora',
            trigger='person',
            steps=2500
        )

    # Verify job was marked as failed
    mock_mongodb.update_job_status.assert_called_with(
        'test-job-789',
        'failed',
        error=pytest.ANY
    )


@pytest.mark.asyncio
async def test_webhook_called_on_success(
    mock_fal_provider,
    mock_s3_storage,
    mock_mongodb,
    mock_video_processor,
    mock_dataset_builder
):
    """Test that webhook is called when job completes"""

    # Mock job with webhook URL
    mock_mongodb.get_job.return_value = {
        'jobId': 'test-job-webhook',
        'userId': 'test-user',
        'type': 'lora-training',
        'config': {'trigger': 'person'},
        'webhookUrl': 'https://example.com/webhook',
        'versions': []
    }

    with patch('webhook_notifier.send_webhook', new_callable=AsyncMock) as mock_webhook:
        mock_webhook.return_value = {"success": True, "attempts": 1}

        pipeline = TrainingPipeline()
        result = await pipeline.process_training_job(
            job_id='test-job-webhook',
            user_id='test-user',
            video_url='https://example.com/video.mp4',
            lora_name='test_lora',
            trigger='person',
            steps=2500
        )

        # Verify webhook was called
        mock_webhook.assert_called_once()
        call_args = mock_webhook.call_args
        assert call_args[0][0] == 'https://example.com/webhook'
        assert 'event' in call_args[0][1]
        assert call_args[0][1]['event'] == 'job.completed'


# Mark expensive tests as skippable
@pytest.mark.skipif(
    os.getenv('REAL_API_TESTS') != 'true',
    reason="Skipping expensive real API test (costs $6)"
)
@pytest.mark.asyncio
async def test_real_training_with_fal_ai():
    """
    Real training test with actual fal.ai call
    Only runs if REAL_API_TESTS=true
    WARNING: This costs $6 per run!
    """
    pipeline = TrainingPipeline()

    result = await pipeline.process_training_job(
        job_id='real-test-job',
        user_id='real-test-user',
        video_url='s3://your-bucket/test-video.mp4',
        lora_name='real_test_lora',
        trigger='person',
        steps=1000  # Minimum steps to reduce cost
    )

    assert result['modelUrl'].startswith('https://')
    assert result['sizeBytes'] > 1000000  # Should be > 1MB
