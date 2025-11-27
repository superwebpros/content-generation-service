# Testing Strategy - Avoiding Real API Costs

## Problem

- LoRA training via fal.ai costs **$6 per training**
- Image generation costs **$0.02-$0.05 per image**
- Running tests would rack up costs quickly

## Solution: Test Levels

### Level 1: Unit Tests (No API Calls)

**Mock external services** - Fast, free, always pass

```javascript
// services/api-gateway/tests/unit/fal-client.test.js
import { jest } from '@jest/globals';

// Mock fal.ai client
jest.mock('@fal-ai/client', () => ({
  fal: {
    config: jest.fn(),
    subscribe: jest.fn().mockResolvedValue({
      images: [{
        url: 'https://fake-url.com/image.png',
        width: 1024,
        height: 1024,
        content_type: 'image/png'
      }]
    }),
    storage: {
      upload: jest.fn().mockResolvedValue('https://fake-storage-url.com/image.jpg')
    }
  }
}));

test('should generate image without calling real API', async () => {
  const result = await generateImage({...});
  expect(result.images).toBeDefined();
  // fal.ai was never actually called!
});
```

**Python equivalent:**

```python
# services/lora-training/test_training_pipeline.py
from unittest.mock import Mock, patch
import pytest

@patch('providers.fal_ai.fal.subscribe')
@patch('s3_storage.s3_storage.upload_file')
@patch('db.db.update_job_status')
async def test_training_pipeline_without_real_api(mock_db, mock_s3, mock_fal):
    # Mock fal.ai response
    mock_fal.return_value = Mock(
        lora_url='https://fake-lora-url.com/model.safetensors',
        config_url='https://fake-config.json'
    )

    # Mock S3 upload
    mock_s3.return_value = 's3://fake-bucket/fake-key'

    # Run pipeline
    result = await pipeline.process_training_job(...)

    # Assert it worked without spending $6!
    assert result['modelUrl'] == 's3://fake-bucket/fake-key'
    mock_fal.assert_called_once()  # Verify it would have called fal.ai
```

### Level 2: Integration Tests (Mock Only External APIs)

**Mock fal.ai, use real MongoDB/S3**

```javascript
// Mock only the expensive external call
beforeEach(() => {
  jest.spyOn(fal, 'subscribe').mockResolvedValue({
    images: [{ url: 'https://mock.com/image.png', ... }]
  });
});

test('should save job to MongoDB', async () => {
  await request(app)
    .post('/api/images/generate')
    .send({...});

  // Real MongoDB query
  const job = await Job.findOne({...});
  expect(job.status).toBe('completed');

  // But fal.ai was mocked (no cost!)
});
```

### Level 3: E2E Tests (Real APIs, Manual Only)

**Only run manually when needed** - add flag to control:

```bash
# Normal tests (mocked, free)
npm test

# E2E with real APIs (costs money, use sparingly)
REAL_API_TESTS=true npm test:e2e
```

```python
# In test
@pytest.mark.skipif(
    os.getenv('REAL_API_TESTS') != 'true',
    reason="Skipping expensive API tests"
)
async def test_real_lora_training():
    # This only runs if REAL_API_TESTS=true
    result = await pipeline.process_training_job(...)
    # Costs $6 - only run when you really need to verify
```

## Recommended Test Commands

```json
// package.json
{
  "scripts": {
    "test": "jest --testPathIgnorePatterns=e2e",  // No API calls
    "test:unit": "jest tests/unit",               // Mocked
    "test:integration": "jest tests/integration", // Mocked external APIs
    "test:e2e": "REAL_API_TESTS=true jest tests/e2e",  // Real APIs (manual)
    "test:watch": "jest --watch"
  }
}
```

## Current Tests Status

**Right now** your integration test is using a **real video** and **real fal.ai training** ($6 cost).

**We should:**
1. Let this one finish (already started)
2. Mock fal.ai in future automated tests
3. Only use real APIs for manual verification

## Mock Implementation Example

Let me create a proper mock for the training pipeline:

```python
# services/lora-training/tests/test_with_mocks.py

import pytest
from unittest.mock import Mock, patch, AsyncMock
from training_pipeline import TrainingPipeline

@pytest.fixture
def mock_fal_provider():
    """Mock fal.ai provider to avoid costs"""
    with patch('providers.fal_ai.create_fal_provider') as mock:
        mock_provider = Mock()
        mock_provider.train.return_value = Mock(
            lora_url='https://fal-cdn.com/fake-lora.safetensors',
            config_url='https://fal-cdn.com/fake-config.json',
            model_name='fake_model'
        )
        mock.return_value = mock_provider
        yield mock_provider

@pytest.mark.asyncio
async def test_training_pipeline_success(mock_fal_provider):
    """Test full pipeline without calling fal.ai"""

    # Mock S3 downloads/uploads
    with patch('s3_storage.s3_storage.download_from_url'):
        with patch('s3_storage.s3_storage.upload_file') as mock_upload:
            mock_upload.return_value = 's3://bucket/loras/user/job/v1/model.safetensors'

            # Mock MongoDB
            with patch('db.db.update_job_status', new_callable=AsyncMock):
                with patch('db.db.add_version', new_callable=AsyncMock):

                    pipeline = TrainingPipeline()
                    result = await pipeline.process_training_job(
                        job_id='test-job',
                        user_id='test-user',
                        video_url='https://example.com/video.mp4',
                        lora_name='test_lora',
                        trigger='person',
                        steps=2500
                    )

                    # Verify result without spending $6
                    assert result['modelUrl'].startswith('s3://')
                    assert 'v1' in result['s3Key']

                    # Verify fal.ai would have been called
                    mock_fal_provider.train.assert_called_once()
```

## Cost Control in CI/CD

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests (mocked, no API costs)
        run: npm test
        env:
          REAL_API_TESTS: false  # Never use real APIs in CI
```

## When to Use Real APIs

**Only for:**
- Manual verification after major changes
- Pre-production smoke tests
- Debugging specific fal.ai issues

**Never for:**
- Automated test suites
- CI/CD pipelines
- Development iterations
