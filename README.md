# Content Generation Service

Multi-language microservice for AI-powered content generation, including LoRA training, image generation, and video processing.

## Architecture

```
content-generation-service/
├── services/
│   ├── api-gateway/         # Node.js - Main REST API (Port 5000)
│   └── lora-training/       # Python - LoRA extraction & training (Port 5001)
├── shared/                  # Shared utilities
│   ├── schemas/            # MongoDB schemas
│   └── storage/            # S3 client utilities
└── config/                 # Deployment configs
    ├── nginx/
    └── pm2/
```

## Services

### API Gateway (Node.js)
- **Port**: 5000
- **Purpose**: Main entry point for all content generation requests
- **Endpoints**:
  - `POST /api/lora/train` - Start LoRA training job
  - `GET /api/lora/status/:jobId` - Get training job status
  - `GET /api/lora/list` - List user's LORAs
  - `POST /api/images/generate` - Generate images (future)

### LoRA Training Service (Python)
- **Port**: 5001 (internal)
- **Purpose**: Process LoRA training jobs
- **Communication**: Called by API Gateway via HTTP or message queue

## Storage

- **MongoDB**: Job metadata, user data, usage tracking
- **S3**: LoRA models, training datasets, generated assets

### S3 Bucket Structure
```
content-generation-assets/
├── loras/{userId}/{jobId}/v{version}/model.safetensors
├── datasets/{userId}/{jobId}/images/
├── generated-images/{userId}/{jobId}/
└── temp/{jobId}/  (auto-delete after 24hrs)
```

## Setup

### Prerequisites
- Node.js 20+
- Python 3.10+
- MongoDB (Digital Ocean managed)
- AWS S3 bucket
- fal.ai API key

### Installation

```bash
# Install Node dependencies
cd services/api-gateway
npm install

# Install Python dependencies
cd services/lora-training
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and configure:
- MongoDB connection string
- AWS S3 credentials
- fal.ai API key

### Development

```bash
# Start API Gateway
cd services/api-gateway
npm run dev

# Start LoRA Training Service
cd services/lora-training
python app.py
```

### Production Deployment

```bash
# Use PM2 for process management
pm2 start config/pm2/ecosystem.config.js
```

## API Usage

### Train a LoRA

```bash
curl -X POST https://content.superwebpros.com/api/lora/train \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "user123",
    "videoUrl": "https://example.com/video.mp4",
    "loraName": "my_avatar",
    "trigger": "person",
    "steps": 2500
  }'
```

Response:
```json
{
  "jobId": "uuid-here",
  "status": "queued",
  "message": "Training job started"
}
```

### Check Status

```bash
curl https://content.superwebpros.com/api/lora/status/uuid-here
```

Response:
```json
{
  "jobId": "uuid-here",
  "status": "completed",
  "progress": 100,
  "modelUrl": "https://s3.amazonaws.com/.../model.safetensors"
}
```

## Tech Stack

- **API Gateway**: Express.js, MongoDB (Mongoose), AWS SDK
- **LoRA Training**: FastAPI, fal.ai SDK, OpenCV, boto3
- **Storage**: MongoDB, AWS S3
- **Process Management**: PM2
- **Reverse Proxy**: Nginx

## Port Registry

- 5000: API Gateway (public via nginx)
- 5001: LoRA Training Service (internal only)

## License

Private - SuperWebPros Internal
