"""
Full training pipeline implementation
Orchestrates: video processing → dataset building → training → S3 upload → MongoDB update
"""

import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from config import Config
from core.video_processor import VideoProcessor
from core.dataset_builder import DatasetBuilder
from providers.fal_ai import create_fal_provider
from providers.base import TrainingConfig
from db import db
from s3_storage import s3_storage
from webhook_notifier import send_webhook, create_completion_payload, create_failure_payload


class TrainingPipeline:
    """End-to-end LoRA training pipeline"""

    def __init__(self):
        self.config = Config.from_env()
        self.video_processor = VideoProcessor(temp_dir=self.config.temp_dir)
        self.dataset_builder = DatasetBuilder(output_dir=self.config.dataset_dir)
        self.provider = create_fal_provider()

    async def process_training_job(
        self,
        job_id: str,
        user_id: str,
        video_url: str,
        lora_name: str,
        trigger: str = "person",
        steps: int = 2500,
        learning_rate: float = 0.00009
    ) -> Dict[str, Any]:
        """
        Process full training pipeline

        Returns:
            Dictionary with modelUrl, s3Key, sizeBytes
        """
        temp_job_dir = None

        try:
            # Update status: processing
            await db.update_job_status(job_id, "processing", progress=0)
            print(f"🚀 Starting training for job {job_id}")

            # Create temporary directory for this job
            temp_job_dir = tempfile.mkdtemp(prefix=f"lora_job_{job_id}_")
            temp_video_path = os.path.join(temp_job_dir, "source_video.mp4")

            # Step 1: Download video
            print(f"📥 Downloading video from {video_url}")
            await db.update_job_status(job_id, "processing", progress=10)
            s3_storage.download_from_url(video_url, temp_video_path)

            # Step 2: Extract frames
            print(f"🎬 Extracting frames from video")
            await db.update_job_status(job_id, "processing", progress=20)
            video_result = self.video_processor.process_video(
                video_url=temp_video_path,
                video_id=job_id
            )

            # Step 3: Build dataset with quality filtering
            print(f"📦 Building training dataset")
            await db.update_job_status(job_id, "processing", progress=35)
            dataset = self.dataset_builder.build_dataset(
                frames=video_result["frames"],
                dataset_name=lora_name,
                trigger_phrase=trigger,
                filter_quality=True
            )

            if dataset.frame_count < self.config.min_frames:
                raise ValueError(
                    f"Insufficient frames after filtering: {dataset.frame_count} "
                    f"(minimum: {self.config.min_frames})"
                )

            print(f"✅ Dataset ready: {dataset.frame_count} frames")

            # Step 4: Upload dataset to S3
            print(f"☁️  Uploading dataset to S3")
            await db.update_job_status(job_id, "processing", progress=50)
            dataset_s3_prefix = f"datasets/{user_id}/{job_id}"
            dataset_urls = s3_storage.upload_directory(
                dataset.dataset_dir,
                dataset_s3_prefix
            )
            print(f"✅ Uploaded {len(dataset_urls)} files to S3")

            # Step 5: Train LoRA via fal.ai
            print(f"🧠 Starting LoRA training ({steps} steps)")
            await db.update_job_status(job_id, "processing", progress=60)

            training_config = TrainingConfig(
                steps=steps,
                learning_rate=learning_rate,
                trigger_phrase=trigger
            )

            training_result = self.provider.train(
                dataset_path=dataset.dataset_dir,
                config=training_config,
                dataset_name=lora_name
            )

            print(f"✅ Training complete! LoRA URL: {training_result.lora_url}")

            # Step 6: Download trained LoRA
            print(f"📥 Downloading trained LoRA model")
            await db.update_job_status(job_id, "processing", progress=85)
            temp_lora_path = os.path.join(temp_job_dir, f"{lora_name}.safetensors")
            s3_storage.download_from_url(training_result.lora_url, temp_lora_path)

            # Step 7: Upload to our S3 bucket (versioned)
            print(f"☁️  Uploading LoRA to S3")
            await db.update_job_status(job_id, "processing", progress=95)

            # Get current version number
            job = await db.get_job(job_id)
            version = len(job.get('versions', [])) + 1

            lora_s3_key = f"loras/{user_id}/{job_id}/v{version}/model.safetensors"
            lora_public_url = s3_storage.upload_file(temp_lora_path, lora_s3_key)

            # Also upload config
            config_s3_key = f"loras/{user_id}/{job_id}/v{version}/config.json"
            config_local_path = os.path.join(temp_job_dir, "config.json")

            import json
            with open(config_local_path, 'w') as f:
                json.dump({
                    "lora_name": lora_name,
                    "trigger": trigger,
                    "steps": steps,
                    "learning_rate": learning_rate,
                    "frame_count": dataset.frame_count,
                    "trained_at": datetime.utcnow().isoformat()
                }, f, indent=2)

            config_url = s3_storage.upload_file(config_local_path, config_s3_key)

            # Get file size
            lora_size = os.path.getsize(temp_lora_path)

            print(f"✅ LoRA uploaded to S3: {lora_public_url}")

            # Step 8: Update MongoDB with version
            version_data = {
                "version": version,
                "modelUrl": lora_public_url,
                "s3Key": lora_s3_key,
                "sizeBytes": lora_size,
                "createdAt": datetime.utcnow(),
                "config": {
                    "trigger": trigger,
                    "steps": steps,
                    "learning_rate": learning_rate,
                    "frame_count": dataset.frame_count
                }
            }

            await db.add_version(job_id, version_data)

            # Step 9: Mark job as completed
            await db.update_job_status(job_id, "completed", progress=100)

            print(f"🎉 Job {job_id} completed successfully!")

            result = {
                "modelUrl": lora_public_url,
                "s3Key": lora_s3_key,
                "sizeBytes": lora_size,
                "version": version
            }

            # Step 10: Send webhook notification if configured
            job = await db.get_job(job_id)
            if job and job.get('webhookUrl'):
                print(f"📞 Sending completion webhook...")
                webhook_result = await send_webhook(
                    job['webhookUrl'],
                    create_completion_payload(job, result)
                )

                # Update webhook status in MongoDB
                await db.jobs.update_one(
                    {"jobId": job_id},
                    {
                        "$set": {
                            "webhookAttempts": webhook_result.get("attempts", 0),
                            "webhookLastError": webhook_result.get("error") if not webhook_result["success"] else None
                        }
                    }
                )

            return result

        except Exception as e:
            print(f"❌ Training failed: {e}")
            await db.update_job_status(job_id, "failed", error=str(e))

            # Send failure webhook if configured
            job = await db.get_job(job_id)
            if job and job.get('webhookUrl'):
                print(f"📞 Sending failure webhook...")
                await send_webhook(
                    job['webhookUrl'],
                    create_failure_payload(job, str(e))
                )

            raise

        finally:
            # Cleanup temporary directory
            if temp_job_dir and os.path.exists(temp_job_dir):
                print(f"🧹 Cleaning up temporary files")
                shutil.rmtree(temp_job_dir, ignore_errors=True)

# Global pipeline instance
pipeline = TrainingPipeline()
