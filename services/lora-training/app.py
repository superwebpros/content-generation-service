"""
FastAPI service for LoRA training worker
Processes training jobs from the API Gateway
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
import os
from datetime import datetime
from dotenv import load_dotenv
import asyncio

from db import db
from training_pipeline import pipeline

# Load environment from root
load_dotenv(dotenv_path='../../.env')

app = FastAPI(
    title="LoRA Training Service",
    description="Worker service for processing LoRA training jobs",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.on_event("startup")
async def startup_event():
    """Connect to MongoDB on startup"""
    await db.connect()
    print("✅ LoRA Training Worker started")

@app.on_event("shutdown")
async def shutdown_event():
    """Close connections on shutdown"""
    await db.close()
    print("👋 LoRA Training Worker shutting down")

# Pydantic models for request/response
class TrainRequest(BaseModel):
    """Request model for training a LoRA"""
    job_id: str = Field(..., description="Job ID from MongoDB")
    user_id: str = Field(..., description="User ID")
    video_url: str = Field(..., description="Source video URL (HTTP/HTTPS or S3)")
    lora_name: str = Field(..., description="Name for the LoRA model")
    trigger: str = Field(default="person", description="Trigger phrase")
    steps: int = Field(default=2500, ge=1000, le=10000, description="Training steps")
    learning_rate: float = Field(default=0.00009, description="Learning rate")

class TrainResponse(BaseModel):
    """Response model for training request"""
    job_id: str
    status: str
    message: str

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str
    timestamp: str

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "lora-training-worker",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/train", response_model=TrainResponse, tags=["Training"])
async def train_lora(request: TrainRequest, background_tasks: BackgroundTasks):
    """
    Process a LoRA training job

    This endpoint receives a training request and processes it in the background.
    Updates MongoDB job status as training progresses.
    Uploads final model to S3.
    """
    try:
        # Add training task to background
        background_tasks.add_task(process_training_job, request)

        return {
            "job_id": request.job_id,
            "status": "processing",
            "message": "Training started in background"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_training_job(request: TrainRequest):
    """
    Background task to process training job

    Steps:
    1. Update MongoDB status to 'processing'
    2. Download video from URL/S3
    3. Extract frames using existing pipeline
    4. Build dataset
    5. Upload dataset to S3
    6. Train via fal.ai
    7. Download trained model
    8. Upload to S3
    9. Update MongoDB with results
    """
    try:
        print(f"🚀 Starting training pipeline for job {request.job_id}")

        result = await pipeline.process_training_job(
            job_id=request.job_id,
            user_id=request.user_id,
            video_url=request.video_url,
            lora_name=request.lora_name,
            trigger=request.trigger,
            steps=request.steps,
            learning_rate=request.learning_rate
        )

        print(f"✅ Training complete! Model URL: {result['modelUrl']}")

    except Exception as e:
        print(f"❌ Training failed for job {request.job_id}: {e}")
        # Error already logged to MongoDB in pipeline
        raise

# Development server
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("LORA_TRAINING_PORT", 5001))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
