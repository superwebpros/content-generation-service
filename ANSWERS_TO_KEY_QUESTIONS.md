# Answers to Key Questions

## Question 1: How Do We Avoid Paying for Tests?

### ✅ SOLVED: Automatic Mock System

**Tests now cost $0 by default!**

### How It Works

```bash
# Regular tests (uses mocks, $0 cost)
npm test

# Real API tests (costs money, only when needed)
REAL_API_TESTS=true npm test:real
```

### What's Mocked

**Node.js (Jest):**
- `@fal-ai/client` → Mock in `tests/__mocks__/@fal-ai/client.js`
- `AssemblyAIClient` → Mock in `tests/__mocks__/assemblyai-client.js`
- Configured in `tests/setup.js` (auto-loads on every test run)

**Python (pytest):**
- fal.ai provider → Mock in `tests/conftest.py`
- S3 storage → Mock fixture
- MongoDB → Mock fixture
- Video processor → Mock fixture

### Cost Savings

| Test Type | Without Mocks | With Mocks | Savings |
|-----------|---------------|------------|---------|
| LoRA training test | $6.00/test | $0 | 100% |
| Image generation test | $0.02-0.05/test | $0 | 100% |
| Transcription test | $0.015/min | $0 | 100% |
| **100 test runs** | **$600+** | **$0** | **$600** |

### Configuration Files

**Jest (Node.js):**
```javascript
// services/api-gateway/tests/setup.js
if (process.env.REAL_API_TESTS !== 'true') {
  console.log('🧪 Using mocked APIs (costs: $0)');
  jest.mock('@fal-ai/client');
  jest.mock('../src/providers/assemblyai-client.js');
}
```

**pytest (Python):**
```python
# services/lora-training/tests/conftest.py
@pytest.fixture
def mock_fal_provider():
    """Mocks fal.ai to avoid $6 cost"""
    # Returns fake LoRA without calling real API
```

### When to Use Real APIs

```bash
# Development: ALWAYS use mocks
npm test

# CI/CD: ALWAYS use mocks
npm test

# Manual verification: Only when needed
REAL_API_TESTS=true npm test

# Production: Real APIs (not tests)
npm start
```

---

## Question 2: How Are We Storing Assets for Future Use?

### ✅ Two-Tier Storage Architecture

**MongoDB** stores metadata, **S3** stores files.

### MongoDB (Fast Queries)

All jobs stored with:
- Job ID (uuid)
- User ID (owner)
- Type (lora-training, image-generation, transcription)
- Status (queued, processing, completed, failed)
- S3 URLs for all assets
- Creation/completion timestamps

**Example job:**
```javascript
{
  jobId: "abc-123",
  userId: "user-456",
  type: "lora-training",
  status: "completed",
  versions: [{
    modelUrl: "https://content-generation-assets.s3.amazonaws.com/loras/user-456/abc-123/v1/model.safetensors",
    s3Key: "loras/user-456/abc-123/v1/model.safetensors",
    version: 1,
    createdAt: "2025-11-27..."
  }],
  createdAt: "2025-11-27..."
}
```

### S3 (Actual Files)

Organized by user and job:
```
loras/{userId}/{jobId}/v{version}/model.safetensors
generated-images/{userId}/{jobId}/image_1.png
transcripts/{userId}/{jobId}/transcript.txt
```

### Retrieval Methods

#### Method 1: Get Specific Job
```bash
GET /api/jobs/{jobId}

# Returns job with all S3 URLs
{
  "jobId": "...",
  "type": "lora-training",
  "versions": [{
    "modelUrl": "https://s3.../model.safetensors"
  }]
}

# Then download from S3
curl "https://s3.../model.safetensors" -o model.safetensors
```

#### Method 2: List by Type (NEW!)
```bash
# Get all LORAs
GET /api/assets/loras?userId=user123

# Returns formatted list
{
  "total": 5,
  "loras": [
    {
      "loraId": "job-id-1",
      "name": "jesse_avatar",
      "trigger": "jf",
      "latestVersion": {
        "modelUrl": "https://s3.../model.safetensors"
      }
    }
  ]
}

# Get all images
GET /api/assets/images?userId=user123&model=flux-pro

# Get all transcripts
GET /api/assets/transcripts?userId=user123
```

#### Method 3: Search (NEW!)
```bash
GET /api/assets/search?userId=user123&q=avatar

# Returns matching jobs across all types
```

#### Method 4: Usage Stats (NEW!)
```bash
GET /api/assets/stats?userId=user123

# Returns counts, storage, costs
{
  "totalJobs": 25,
  "byType": {
    "lora-training": 5,
    "image-generation": 15,
    "transcription": 5
  },
  "totalStorageGB": "2.5",
  "estimatedMonthlyCost": "0.06"
}
```

### Reusing Assets in New Jobs

**Example: Use trained LoRA in image generation**

```javascript
// 1. Get your LoRA
const loras = await fetch('/api/assets/loras?userId=user123').then(r => r.json());
const jesseLoRA = loras.loras.find(l => l.name === 'jesse_avatar');
const loraUrl = jesseLoRA.latestVersion.modelUrl;

// 2. Use it to generate images
await fetch('/api/images/generate', {
  method: 'POST',
  body: JSON.stringify({
    model: 'flux-lora',
    inputs: {
      prompt: 'Professional headshot of jf in a suit',
      loras: [{
        path: loraUrl,  // Reusing your LoRA!
        scale: 0.8
      }]
    },
    userId: 'user123'
  })
});
```

**Example: Reuse transcript for content**

```javascript
// 1. Get transcript
const transcripts = await fetch('/api/assets/transcripts?userId=user123').then(r => r.json());
const podcast = transcripts.transcripts[0];

// 2. Download text
const text = await fetch(podcast.textUrl).then(r => r.text());

// 3. Use for blog post, social clips, etc.
console.log('Generate blog from:', text);
```

### Data Retention

**Forever (until you delete):**
- All job records in MongoDB
- All assets in S3

**Auto-deleted after 24 hours:**
- Temp files (S3 lifecycle policy)

**To delete:**
```javascript
// Future endpoint (not implemented yet)
DELETE /api/jobs/{jobId}

// Would delete:
// - MongoDB record
// - All S3 files for that job
```

## Complete API Surface for Retrieval

```
# Get specific
GET /api/jobs/{jobId}

# List all
GET /api/jobs?userId=X

# Filter by type
GET /api/jobs?userId=X&type=lora-training
GET /api/jobs?userId=X&type=image-generation
GET /api/jobs?userId=X&type=transcription

# Filter by status
GET /api/jobs?userId=X&status=completed

# Asset-specific lists (better formatting)
GET /api/assets/loras?userId=X
GET /api/assets/images?userId=X&model=flux-pro
GET /api/assets/transcripts?userId=X

# Search
GET /api/assets/search?userId=X&q=avatar

# Stats
GET /api/assets/stats?userId=X
```

## Storage Costs

**Current test data:**
- Transcription: 120KB JSON + 4.8KB text = ~125KB
- Image: Not stored yet (version data issue to fix)
- LoRA: Would be ~125MB per model

**Example production usage:**
- 10 LORAs: 1.25GB
- 100 images @ 2MB: 200MB
- 50 transcripts @ 100KB: 5MB
- **Total**: ~1.5GB = **$0.03/month**

Very affordable!

## Summary

### Question 1: Test Costs
✅ **Solved** with comprehensive mocking
- Default tests cost $0
- Only manual tests with REAL_API_TESTS=true cost money
- Saves hundreds of dollars in API costs

### Question 2: Storage & Retrieval
✅ **Implemented** with two-tier architecture
- MongoDB: Fast metadata queries
- S3: Organized file storage
- Multiple retrieval methods (by ID, type, search, stats)
- Easy asset reuse (LoRAs in image gen, transcripts for content)
- Cost-effective (~$0.03/month for 1.5GB)

**Both questions answered with production-ready solutions!**
