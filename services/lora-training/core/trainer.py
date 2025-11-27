"""
Training orchestration module.

Coordinates the end-to-end LoRA training process:
1. Video processing
2. Dataset building
3. Training provider execution
4. Result storage
"""

from pathlib import Path
from typing import Optional, Dict

from config import Config
from core.video_processor import VideoProcessor
from core.dataset_builder import DatasetBuilder, TrainingDataset
from core.storage import LoRAStorage
from providers.base import TrainingProvider, TrainingConfig, TrainingResult
from providers.fal_ai import create_fal_provider
from utils.logger import get_logger

logger = get_logger(__name__)


class TrainingOrchestrator:
    """Orchestrate the complete LoRA training pipeline."""

    def __init__(self, config: Config):
        """
        Initialize training orchestrator.

        Args:
            config: Configuration object
        """
        self.config = config

        # Initialize components
        self.video_processor = VideoProcessor(
            temp_dir=config.temp_dir,
            scene_threshold=config.scene_threshold
        )

        self.dataset_builder = DatasetBuilder(
            output_dir=config.dataset_dir,
            min_face_confidence=config.min_face_confidence,
            blur_threshold=config.blur_threshold,
            min_frames=config.min_frames,
            max_frames=config.max_frames
        )

        self.storage = LoRAStorage(output_dir=config.output_dir)

        # Initialize provider
        self.provider = self._get_provider()

    def _get_provider(self) -> TrainingProvider:
        """Get training provider based on config."""
        if self.config.training_provider == "fal_ai":
            self.config.validate_provider("fal_ai")
            return create_fal_provider(self.config.fal_api_key)
        # Add more providers here
        else:
            raise ValueError(f"Unknown provider: {self.config.training_provider}")

    def train_from_video(
        self,
        video_url: str,
        lora_name: str,
        trigger_phrase: Optional[str] = None,
        steps: Optional[int] = None,
        learning_rate: Optional[float] = None,
        filter_quality: bool = True
    ) -> Dict:
        """
        Train a LoRA from a video URL (end-to-end).

        Args:
            video_url: URL to video file
            lora_name: Name for this LoRA
            trigger_phrase: LoRA trigger phrase (default from config)
            steps: Training steps (default from config)
            learning_rate: Learning rate (default from config)
            filter_quality: Apply quality filtering to frames

        Returns:
            Dict with training results and LoRA info
        """
        try:
            logger.info("=" * 80)
            logger.info(f"TRAINING LORA: {lora_name}")
            logger.info("=" * 80)

            # Step 1: Process video
            logger.info("Step 1/4: Processing video...")
            video_result = self.video_processor.process_video(
                video_url=video_url,
                video_id=lora_name
            )

            if not video_result["success"]:
                raise Exception(f"Video processing failed: {video_result['error']}")

            frames = video_result["frames"]
            logger.info(f"✓ Extracted {len(frames)} frames")

            # Step 2: Build dataset
            logger.info("Step 2/4: Building training dataset...")
            trigger = trigger_phrase or self.config.default_trigger_phrase
            dataset = self.dataset_builder.build_dataset(
                frames=frames,
                dataset_name=lora_name,
                trigger_phrase=trigger,
                filter_quality=filter_quality
            )
            logger.info(f"✓ Dataset ready: {dataset.image_count} images")

            # Step 3: Train LoRA
            logger.info("Step 3/4: Training LoRA...")
            training_config = TrainingConfig(
                steps=steps or self.config.default_steps,
                learning_rate=learning_rate or self.config.default_learning_rate,
                trigger_phrase=trigger
            )

            training_result = self.provider.train(
                dataset_path=dataset.dataset_dir,
                config=training_config,
                dataset_name=lora_name
            )

            if not training_result.success:
                raise Exception(f"Training failed: {training_result.error}")

            logger.info(f"✓ Training complete")

            # Step 4: Store LoRA
            logger.info("Step 4/4: Storing LoRA...")
            lora_info = self.storage.save_lora(
                lora_name=lora_name,
                lora_url=training_result.lora_url,
                config_url=training_result.config_url,
                metadata={
                    "video_url": video_url,
                    "trigger_phrase": trigger,
                    "training_config": {
                        "steps": training_config.steps,
                        "learning_rate": training_config.learning_rate,
                    },
                    "dataset": dataset.metadata,
                    "training_result": training_result.metadata,
                    "provider": training_result.provider
                }
            )
            logger.info(f"✓ LoRA saved: {lora_info['lora_path']}")

            logger.info("=" * 80)
            logger.info("TRAINING COMPLETE!")
            logger.info("=" * 80)
            logger.info(f"LoRA: {lora_info['lora_path']}")
            logger.info(f"Trigger: {trigger}")

            return {
                "success": True,
                "lora_name": lora_name,
                "lora_path": lora_info["lora_path"],
                "trigger_phrase": trigger,
                "video_result": video_result,
                "dataset": dataset,
                "training_result": training_result,
                "lora_info": lora_info
            }

        except Exception as e:
            logger.error(f"✗ Training pipeline failed: {e}")
            return {
                "success": False,
                "lora_name": lora_name,
                "error": str(e)
            }

    def train_from_dataset(
        self,
        dataset_path: Path,
        lora_name: str,
        trigger_phrase: Optional[str] = None,
        steps: Optional[int] = None,
        learning_rate: Optional[float] = None
    ) -> Dict:
        """
        Train a LoRA from an existing dataset.

        Args:
            dataset_path: Path to dataset directory
            lora_name: Name for this LoRA
            trigger_phrase: LoRA trigger phrase
            steps: Training steps
            learning_rate: Learning rate

        Returns:
            Dict with training results
        """
        try:
            logger.info("=" * 80)
            logger.info(f"TRAINING LORA FROM DATASET: {lora_name}")
            logger.info("=" * 80)

            trigger = trigger_phrase or self.config.default_trigger_phrase

            # Train LoRA
            logger.info("Training LoRA...")
            training_config = TrainingConfig(
                steps=steps or self.config.default_steps,
                learning_rate=learning_rate or self.config.default_learning_rate,
                trigger_phrase=trigger
            )

            training_result = self.provider.train(
                dataset_path=dataset_path,
                config=training_config,
                dataset_name=lora_name
            )

            if not training_result.success:
                raise Exception(f"Training failed: {training_result.error}")

            # Store LoRA
            logger.info("Storing LoRA...")
            lora_info = self.storage.save_lora(
                lora_name=lora_name,
                lora_url=training_result.lora_url,
                config_url=training_result.config_url,
                metadata={
                    "trigger_phrase": trigger,
                    "training_config": {
                        "steps": training_config.steps,
                        "learning_rate": training_config.learning_rate,
                    },
                    "training_result": training_result.metadata,
                    "provider": training_result.provider
                }
            )

            logger.info("=" * 80)
            logger.info("TRAINING COMPLETE!")
            logger.info("=" * 80)

            return {
                "success": True,
                "lora_name": lora_name,
                "lora_path": lora_info["lora_path"],
                "training_result": training_result,
                "lora_info": lora_info
            }

        except Exception as e:
            logger.error(f"✗ Training failed: {e}")
            return {
                "success": False,
                "lora_name": lora_name,
                "error": str(e)
            }
