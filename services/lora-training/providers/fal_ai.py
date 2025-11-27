"""
fal.ai training provider implementation.

Handles LoRA training using fal.ai's API.
"""

import os
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, Optional

from providers.base import TrainingProvider, TrainingResult, TrainingConfig
from utils.logger import get_logger

logger = get_logger(__name__)


class FalAIProvider(TrainingProvider):
    """fal.ai training provider."""

    def __init__(self, api_key: str):
        """
        Initialize fal.ai provider.

        Args:
            api_key: fal.ai API key
        """
        super().__init__(api_key)

        # Set environment variable for fal client
        os.environ["FAL_KEY"] = api_key

        # Import fal client
        try:
            from fal_client import subscribe
            self.fal_subscribe = subscribe
        except ImportError:
            raise ImportError(
                "fal-client not installed. Install with: pip install fal-client"
            )

    def upload_dataset(self, dataset_path: Path) -> str:
        """
        Upload dataset to fal.ai storage as zip file.

        Args:
            dataset_path: Path to dataset directory

        Returns:
            URL to uploaded zip file

        Raises:
            Exception: If upload fails
        """
        try:
            from fal_client import upload_file

            logger.info(f"Packaging dataset for upload: {dataset_path}")

            # Create temporary zip file
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
                zip_path = Path(tmp_zip.name)

            # Zip the images directory
            images_dir = dataset_path / "images"
            if not images_dir.exists():
                raise ValueError(f"Images directory not found: {images_dir}")

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for image_file in images_dir.glob("*"):
                    if image_file.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                        # Add to zip root (not in subdirectory)
                        zipf.write(image_file, image_file.name)

            logger.info(f"Created zip archive: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.2f} MB)")

            # Upload to fal.ai
            logger.info("Uploading to fal.ai...")
            url = upload_file(zip_path)

            # Cleanup
            zip_path.unlink()

            logger.info(f"✓ Dataset uploaded: {url}")
            return url

        except Exception as e:
            logger.error(f"Failed to upload dataset: {e}")
            raise

    def train(
        self,
        dataset_path: Path,
        config: TrainingConfig,
        dataset_name: str
    ) -> TrainingResult:
        """
        Train a LoRA model using fal.ai.

        Args:
            dataset_path: Path to dataset directory
            config: Training configuration
            dataset_name: Name for this training job

        Returns:
            TrainingResult object

        Raises:
            Exception: If training fails
        """
        try:
            logger.info("=" * 80)
            logger.info(f"Starting fal.ai training: {dataset_name}")
            logger.info("=" * 80)

            # Validate dataset
            if not self.validate_dataset(dataset_path):
                raise ValueError("Dataset validation failed")

            # Upload dataset
            dataset_url = self.upload_dataset(dataset_path)

            # Prepare training arguments
            training_args = {
                "steps": config.steps,
                "learning_rate": config.learning_rate,
                "trigger_phrase": config.trigger_phrase,
                "images_data_url": dataset_url,
                "create_masks": config.create_masks,
                "subject_crop": config.subject_crop,
                "multiresolution_training": config.multiresolution_training,
            }

            logger.info("Training configuration:")
            for key, value in training_args.items():
                if key != "images_data_url":
                    logger.info(f"  {key}: {value}")

            # Submit training job
            logger.info("Submitting training job to fal.ai...")

            # Callback for queue updates
            def on_queue_update(update):
                """Handle queue update events."""
                try:
                    import fal_client
                    if isinstance(update, fal_client.InProgress):
                        for log in update.logs:
                            if isinstance(log, dict) and "message" in log:
                                logger.info(f"  [fal.ai] {log['message']}")
                            else:
                                logger.info(f"  [fal.ai] {log}")
                except Exception as e:
                    logger.debug(f"Log parsing error: {e}")

            # Use subscribe() as per fal.ai API documentation
            result = self.fal_subscribe(
                "fal-ai/flux-lora-portrait-trainer",
                arguments=training_args,
                with_logs=True,
                on_queue_update=on_queue_update
            )

            logger.info("=" * 80)
            logger.info("Training complete!")
            logger.info("=" * 80)

            # Extract URLs from result (subscribe() returns result with .data and .requestId)
            result_data = result.get("data", result) if isinstance(result, dict) else result.data
            request_id = result.get("requestId") if isinstance(result, dict) else result.requestId

            lora_url = result_data.get("diffusers_lora_file", {}).get("url")
            config_url = result_data.get("config_file", {}).get("url")
            diffusers_url = result_data.get("diffusers_lora_file", {}).get("url")

            logger.info(f"LoRA URL: {lora_url}")
            logger.info(f"Config URL: {config_url}")

            return TrainingResult(
                success=True,
                lora_url=lora_url,
                config_url=config_url,
                diffusers_url=diffusers_url,
                training_id=request_id,
                provider="fal_ai",
                metadata={
                    "dataset_url": dataset_url,
                    "config": training_args,
                    "result": result_data
                }
            )

        except Exception as e:
            logger.error(f"✗ Training failed: {e}")
            return TrainingResult(
                success=False,
                lora_url=None,
                config_url=None,
                diffusers_url=None,
                training_id=None,
                provider="fal_ai",
                error=str(e)
            )


def create_fal_provider(api_key: Optional[str] = None) -> FalAIProvider:
    """
    Create a fal.ai provider instance.

    Args:
        api_key: Optional API key (uses FAL_KEY env var if not provided)

    Returns:
        FalAIProvider instance

    Raises:
        ValueError: If no API key is available
    """
    if not api_key:
        api_key = os.getenv("FAL_KEY") or os.getenv("FAL_API_KEY")

    if not api_key:
        raise ValueError(
            "No fal.ai API key provided. Set FAL_KEY environment variable or pass api_key argument."
        )

    return FalAIProvider(api_key)
