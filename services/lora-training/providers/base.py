"""
Abstract base class for LoRA training providers.

Defines the interface that all training providers must implement.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TrainingResult:
    """Result of a LoRA training job."""
    success: bool
    lora_url: Optional[str]
    config_url: Optional[str]
    diffusers_url: Optional[str]
    training_id: Optional[str]
    provider: str
    error: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class TrainingConfig:
    """Configuration for LoRA training."""
    steps: int = 1000
    learning_rate: float = 0.0002
    trigger_phrase: str = "person"
    create_masks: bool = False
    subject_crop: bool = True
    multiresolution_training: bool = True


class TrainingProvider(ABC):
    """Abstract base class for LoRA training providers."""

    def __init__(self, api_key: str):
        """
        Initialize provider.

        Args:
            api_key: API key for the provider
        """
        self.api_key = api_key

    @abstractmethod
    def train(
        self,
        dataset_path: Path,
        config: TrainingConfig,
        dataset_name: str
    ) -> TrainingResult:
        """
        Train a LoRA model.

        Args:
            dataset_path: Path to dataset directory (with images/ and captions/)
            config: Training configuration
            dataset_name: Name for this training job

        Returns:
            TrainingResult object

        Raises:
            Exception: If training fails
        """
        pass

    @abstractmethod
    def upload_dataset(self, dataset_path: Path) -> str:
        """
        Upload dataset to provider storage.

        Args:
            dataset_path: Path to dataset directory

        Returns:
            URL to uploaded dataset

        Raises:
            Exception: If upload fails
        """
        pass

    def validate_dataset(self, dataset_path: Path) -> bool:
        """
        Validate that dataset has required structure.

        Args:
            dataset_path: Path to dataset directory

        Returns:
            True if valid, False otherwise
        """
        dataset_path = Path(dataset_path)

        # Check directory exists
        if not dataset_path.exists():
            logger.error(f"Dataset path does not exist: {dataset_path}")
            return False

        # Check for images directory
        images_dir = dataset_path / "images"
        if not images_dir.exists():
            logger.error(f"Images directory not found: {images_dir}")
            return False

        # Check for captions directory (optional for some providers)
        captions_dir = dataset_path / "captions"
        has_captions = captions_dir.exists()

        # Count images
        image_files = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png"))
        if not image_files:
            logger.error(f"No images found in {images_dir}")
            return False

        # Check captions if directory exists
        if has_captions:
            caption_files = list(captions_dir.glob("*.txt"))
            if len(caption_files) != len(image_files):
                logger.warning(
                    f"Caption count ({len(caption_files)}) != image count ({len(image_files)})"
                )

        logger.info(f"✓ Dataset validated: {len(image_files)} images")
        return True
