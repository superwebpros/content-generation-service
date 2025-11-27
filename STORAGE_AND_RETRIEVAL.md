# Storage and Retrieval Architecture

## Current Storage Strategy

### Two-Tier Storage Model

**MongoDB** (Metadata & Relationships)
- Job records with status/progress
- User ownership
- Timestamps and versioning
- References to S3 assets

**S3** (Binary Assets)
- LoRA models (.safetensors files)
- Training datasets (images)
- Generated images
- Audio/video files
- Transcripts (JSON + TXT)

## S3 Bucket Structure

```
content-generation-assets/
├── loras/
│   └── {userId}/
│       └── {jobId}/
│           └── v{version}/
│               ├── model.safetensors (125MB)
│               └── config.json
│
├── datasets/
│   └── {userId}/
│       └── {jobId}/
│           ├── images/
│           │   ├── 0001.jpg
│           │   └── ...
│           └── captions/
│               ├── 0001.txt
│               └── ...
│
├── generated-images/
│   └── {userId}/
│       └── {jobId}/
│           └── image_1.png
│
├── transcripts/
│   └── {userId}/
│       └── {jobId}/
│           ├── transcript.json (full AssemblyAI response)
│           └── transcript.txt  (plain text)
│
└── temp/
    └── {jobId}/  # Auto-deleted after 24hrs
```

## MongoDB Schema

```javascript
{
  _id: ObjectId,
  jobId: "uuid",         // User-facing ID
  userId: "user-123",    // Owner
  type: "lora-training" | "image-generation" | "transcription",

  // Source reference
  sourceVideo: {
    url: "s3://... or https://...",
    filename: "video.mp4",
    sizeBytes: 150000000
  },

  // Job metadata
  config: {
    // Type-specific config
  },

  // Results (versioned)
  versions: [
    {
      version: 1,
      modelUrl: "https://s3.../model.safetensors",  // For LoRA
      images: [{url, s3Key, width, height}],         // For image-gen
      transcriptUrl: "https://s3.../transcript.json", // For transcription
      textUrl: "https://s3.../transcript.txt",
      createdAt: Date
    }
  ],

  // State
  status: "completed",
  progress: 100,
  createdAt: Date,
  completedAt: Date
}
```

## Retrieval Patterns

### Pattern 1: Get Specific Asset

**Current (works now):**
```bash
# Get any job by ID
GET /api/jobs/{jobId}

# Returns full job with S3 URLs
{
  "jobId": "...",
  "type": "transcription",
  "versions": [{
    "transcriptUrl": "https://s3.../transcript.json",
    "textUrl": "https://s3.../transcript.txt"
  }]
}

# Download from S3
curl "https://content-generation-assets.s3.amazonaws.com/transcripts/..."
```

### Pattern 2: List User's Assets

**Current (works now):**
```bash
# List all jobs
GET /api/jobs?userId=user123

# Filter by type
GET /api/jobs?userId=user123&type=lora-training
GET /api/jobs?userId=user123&type=image-generation
GET /api/jobs?userId=user123&type=transcription

# Filter by status
GET /api/jobs?userId=user123&status=completed
```

### Pattern 3: Search/Browse (NEEDS IMPLEMENTATION)

**Proposed:**
```bash
# Search by name/description
GET /api/assets/search?userId=user123&q=avatar

# Browse by type with metadata
GET /api/loras?userId=user123
GET /api/images?userId=user123
GET /api/transcripts?userId=user123

# Filter by date range
GET /api/jobs?userId=user123&from=2025-01-01&to=2025-12-31

# Sort by various fields
GET /api/jobs?userId=user123&sort=createdAt&order=desc
```

## Asset Lifecycle

### 1. Creation
```
Client → POST /api/{lora|images|transcribe}
         ↓
      MongoDB job created
         ↓
      Background processing
         ↓
      Results uploaded to S3
         ↓
      MongoDB updated with S3 URLs
```

### 2. Retrieval
```
Client → GET /api/jobs/{jobId}
         ↓
      MongoDB returns job with S3 URLs
         ↓
      Client downloads from S3 URLs
```

### 3. Reuse
```
# Example: Use trained LoRA in image generation

# 1. Get LoRA URL
GET /api/jobs/{loraJobId}
→ {versions: [{modelUrl: "s3://..."}]}

# 2. Use in image generation
POST /api/images/generate
{
  "model": "flux-lora",
  "inputs": {
    "prompt": "...",
    "loras": [{
      "path": "s3://..."  // From step 1
    }]
  }
}
```

## Proposed Retrieval Enhancements

### Add Asset-Specific Endpoints

```javascript
// services/api-gateway/src/routes/assets.js

// List LORAs with better formatting
GET /api/assets/loras?userId=X
→ [
  {
    loraId: "...",
    name: "jesse_avatar",
    trigger: "jf",
    versions: 3,
    latestVersion: {
      modelUrl: "...",
      createdAt: "..."
    },
    thumbnailUrl: "...",  // Could generate preview
    tags: ["avatar", "headshot"]
  }
]

// List generated images
GET /api/assets/images?userId=X
→ [
  {
    imageId: "...",
    model: "flux-pro",
    prompt: "...",
    imageUrl: "...",
    thumbnailUrl: "...",
    width: 1024,
    height: 1024,
    createdAt: "..."
  }
]

// List transcripts
GET /api/assets/transcripts?userId=X
→ [
  {
    transcriptId: "...",
    fileName: "podcast-ep-01.mp3",
    duration: 3600,
    wordCount: 5000,
    transcriptUrl: "...",
    textUrl: "...",
    speakers: 2,
    createdAt: "..."
  }
]
```

### Add Tagging/Metadata

```javascript
// Add tags when creating
POST /api/lora/train
{
  "userId": "...",
  "videoUrl": "...",
  "loraName": "jesse_avatar",
  "metadata": {
    "tags": ["avatar", "headshot", "professional"],
    "description": "Jesse professional headshot avatar",
    "isPublic": false
  }
}

// Search by tags
GET /api/assets/search?tags=avatar,headshot
```

### Add Collections/Folders

```javascript
// Group related assets
POST /api/collections
{
  "userId": "user123",
  "name": "SEO Workshop Campaign",
  "description": "All assets for Dec 2025 workshop",
  "assets": [
    {type: "lora-training", jobId: "..."},
    {type: "image-generation", jobId: "..."},
    {type: "image-generation", jobId: "..."}
  ]
}

GET /api/collections?userId=user123
→ List of collections with asset counts
```

## Current Retrieval Capabilities (Already Working)

### ✅ Get Any Job
```bash
curl http://localhost:5000/api/jobs/{jobId}
```

### ✅ List All Jobs for User
```bash
curl "http://localhost:5000/api/jobs?userId=user123"
```

### ✅ Filter by Type
```bash
curl "http://localhost:5000/api/jobs?userId=user123&type=lora-training"
```

### ✅ Filter by Status
```bash
curl "http://localhost:5000/api/jobs?userId=user123&status=completed"
```

### ✅ Real-time Monitoring
```bash
# SSE stream
curl -N "http://localhost:5000/api/stream/job/{jobId}"
```

### ✅ Download Assets from S3

All S3 URLs are public (or can be made signed):
```bash
# Download LoRA model
curl "https://content-generation-assets.s3.amazonaws.com/loras/..." -o model.safetensors

# Download transcript
curl "https://content-generation-assets.s3.amazonaws.com/transcripts/.../transcript.txt"

# Download generated image
curl "https://content-generation-assets.s3.amazonaws.com/generated-images/..."
```

## Future Storage Enhancements

### 1. Signed URLs for Private Assets

```javascript
// Generate temporary download URL
GET /api/assets/{jobId}/download?expires=3600

→ {
  "url": "https://s3.../model.safetensors?signature=...",
  "expiresAt": "2025-11-27T23:00:00Z"
}
```

### 2. Asset Thumbnails/Previews

```javascript
// For images: auto-generate thumbnails
generated-images/{userId}/{jobId}/
  ├── image_1.png (full size)
  └── image_1_thumb.png (256x256)

// For LoRA: generate example image
loras/{userId}/{jobId}/
  ├── model.safetensors
  ├── config.json
  └── preview.png  (sample generation)
```

### 3. Full-Text Search

```javascript
// Search transcripts content
GET /api/search/transcripts?userId=X&q=wildfires

// Returns jobs where transcript contains "wildfires"
```

### 4. Usage Analytics

```javascript
// Track asset usage
GET /api/assets/{jobId}/stats

→ {
  "downloads": 15,
  "lastAccessed": "...",
  "storageCost": 0.03,  // $/month
  "usedInJobs": [...]   // Other jobs using this asset
}
```

## Recommended Next Steps for Retrieval

### Immediate (Do This First)

Add these simple endpoints to make browsing easier:

```javascript
// GET /api/assets/loras?userId=X
// Returns formatted list of LORAs only

// GET /api/assets/images?userId=X
// Returns formatted list of images only

// GET /api/assets/transcripts?userId=X
// Returns formatted list of transcripts only
```

These are just MongoDB queries with better formatting.

### Short-term

- Add tags/metadata support
- Add asset preview generation
- Add signed URLs for private assets

### Long-term

- Full-text search with Typesense/Elasticsearch
- Collections/folders
- Asset sharing between users
- CDN for faster delivery

## Example Queries You Can Run NOW

```bash
# Get all completed LORAs
curl "http://localhost:5000/api/jobs?userId=user123&type=lora-training&status=completed" | jq '.jobs[] | {name: .config.loraName, modelUrl: .versions[-1].modelUrl}'

# Get all generated images
curl "http://localhost:5000/api/jobs?userId=user123&type=image-generation&status=completed" | jq '.jobs[] | {model: .config.model, images: .versions[0].images}'

# Get all transcripts
curl "http://localhost:5000/api/jobs?userId=user123&type=transcription&status=completed" | jq '.jobs[] | {file: .sourceVideo.filename, textUrl: .versions[0].textUrl}'

# Count assets by type
curl "http://localhost:5000/api/jobs?userId=user123" | jq '[.jobs[] | .type] | group_by(.) | map({type: .[0], count: length})'
```

## Storage Costs

**Current S3 usage** (example):
- 10 LORAs × 125MB = 1.25GB
- 100 images × 2MB = 200MB
- 20 transcripts × 100KB = 2MB
- **Total**: ~1.5GB

**Cost**: $1.50 × $0.023/GB/month = **$0.03/month**

Very cheap! S3 lifecycle policies auto-delete temp files.

## Summary

### ✅ What Works Now

- All assets stored in S3 with organized structure
- All jobs tracked in MongoDB with S3 references
- Retrieval via `/api/jobs` endpoint
- Filtering by type, status, user
- Real-time streaming for active jobs

### 🔨 Easy to Add

- Asset-specific list endpoints (better formatting)
- Search by name/tags
- Signed URLs for private assets
- Thumbnail generation

### 🚀 Future Enhancements

- Full-text search
- Collections/folders
- Asset sharing
- Usage analytics

**Your storage is well-organized and ready to scale!**
