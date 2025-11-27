"""
Dataset builder for LoRA training.

Handles:
- Frame quality control (face detection, blur detection)
- Dataset organization
- Caption generation
- Training-ready dataset creation
"""

from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

from core.video_processor import Frame
from utils.face_detection import FaceDetector, ImageQuality
from utils.captioning import CaptionGenerator
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TrainingDataset:
    """Represents a prepared training dataset."""
    dataset_dir: Path
    images_dir: Path
    captions_dir: Path
    image_count: int
    trigger_phrase: str
    metadata: Dict


class DatasetBuildError(Exception):
    """Exception raised when dataset building fails."""
    pass


class DatasetBuilder:
    """Build training-ready datasets from extracted frames."""

    def __init__(
        self,
        output_dir: Path,
        min_face_confidence: float = 0.8,
        blur_threshold: float = 100.0,
        min_frames: int = 15,
        max_frames: int = 50
    ):
        """
        Initialize dataset builder.

        Args:
            output_dir: Base directory for datasets
            min_face_confidence: Minimum face detection confidence
            blur_threshold: Minimum blur score (higher = sharper)
            min_frames: Minimum frames required for training
            max_frames: Maximum frames to include
        """
        self.output_dir = Path(output_dir)
        self.min_frames = min_frames
        self.max_frames = max_frames

        # Initialize utilities
        self.face_detector = FaceDetector(
            min_face_confidence=min_face_confidence,
            blur_threshold=blur_threshold
        )

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def filter_frames(
        self,
        frames: List[Frame],
        verbose: bool = True
    ) -> tuple[List[Frame], List[ImageQuality]]:
        """
        Filter frames based on quality criteria.

        Args:
            frames: List of Frame objects
            verbose: Log detailed results

        Returns:
            Tuple of (accepted_frames, quality_assessments)
        """
        logger.info(f"Filtering {len(frames)} frames for quality...")

        frame_paths = [frame.file_path for frame in frames]
        accepted_paths, qualities = self.face_detector.filter_quality_frames(
            frame_paths,
            verbose=verbose
        )

        # Map back to Frame objects
        accepted_frames = [
            frame for frame in frames
            if frame.file_path in accepted_paths
        ]

        return accepted_frames, qualities

    def build_dataset(
        self,
        frames: List[Frame],
        dataset_name: str,
        trigger_phrase: str = "person",
        use_caption_variations: bool = True,
        filter_quality: bool = True
    ) -> TrainingDataset:
        """
        Build a training-ready dataset from frames.

        Args:
            frames: List of Frame objects
            dataset_name: Name for this dataset
            trigger_phrase: LoRA trigger phrase
            use_caption_variations: Use varied caption templates
            filter_quality: Apply quality filtering

        Returns:
            TrainingDataset object

        Raises:
            DatasetBuildError: If dataset creation fails
        """
        try:
            logger.info("=" * 80)
            logger.info(f"Building dataset: {dataset_name}")
            logger.info("=" * 80)

            # Filter frames if requested
            if filter_quality:
                frames, qualities = self.filter_frames(frames, verbose=True)
            else:
                qualities = []

            # Check minimum frame count
            if len(frames) < self.min_frames:
                raise DatasetBuildError(
                    f"Insufficient frames: {len(frames)} < {self.min_frames} required"
                )

            # Limit to max_frames
            if len(frames) > self.max_frames:
                logger.warning(f"Limiting to {self.max_frames} frames (had {len(frames)})")
                frames = frames[:self.max_frames]

            logger.info(f"Using {len(frames)} frames for training")

            # Create dataset directory
            dataset_dir = self.output_dir / dataset_name
            images_dir = dataset_dir / "images"
            captions_dir = dataset_dir / "captions"

            images_dir.mkdir(parents=True, exist_ok=True)
            captions_dir.mkdir(parents=True, exist_ok=True)

            # Initialize caption generator
            caption_gen = CaptionGenerator(trigger_phrase=trigger_phrase)

            # Copy images and generate captions
            import shutil

            for i, frame in enumerate(frames, 1):
                # Copy image
                dest_image = images_dir / f"{i:04d}.jpg"
                shutil.copy2(frame.file_path, dest_image)

                # Generate caption
                caption = caption_gen.generate_caption(
                    frame.file_path,
                    use_variations=use_caption_variations
                )
                caption_path = captions_dir / f"{i:04d}.txt"
                caption_path.write_text(caption)

                logger.info(f"  {i}/{len(frames)}: {dest_image.name} → '{caption}'")

            # Save metadata
            metadata = {
                "dataset_name": dataset_name,
                "trigger_phrase": trigger_phrase,
                "image_count": len(frames),
                "filter_quality": filter_quality,
                "use_caption_variations": use_caption_variations,
                "frames": [
                    {
                        "scene_number": frame.scene_number,
                        "timestamp": frame.midpoint,
                        "duration": frame.duration,
                        "resolution": f"{frame.width}x{frame.height}"
                    }
                    for frame in frames
                ]
            }

            if qualities:
                metadata["quality_stats"] = {
                    "total_assessed": len(qualities),
                    "accepted": len(frames),
                    "rejected": len(qualities) - len(frames),
                    "avg_face_confidence": sum(q.face_confidence for q in qualities) / len(qualities),
                    "avg_blur_score": sum(q.blur_score for q in qualities) / len(qualities)
                }

            # Save metadata JSON
            import json
            metadata_path = dataset_dir / "metadata.json"
            metadata_path.write_text(json.dumps(metadata, indent=2))

            logger.info("=" * 80)
            logger.info("Dataset created successfully")
            logger.info("=" * 80)
            logger.info(f"Dataset: {dataset_dir}")
            logger.info(f"Images: {len(frames)}")
            logger.info(f"Trigger: {trigger_phrase}")

            return TrainingDataset(
                dataset_dir=dataset_dir,
                images_dir=images_dir,
                captions_dir=captions_dir,
                image_count=len(frames),
                trigger_phrase=trigger_phrase,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Failed to build dataset: {e}")
            raise DatasetBuildError(f"Dataset build failed: {e}")

    def build_from_directory(
        self,
        source_dir: Path,
        dataset_name: str,
        trigger_phrase: str = "person",
        **kwargs
    ) -> TrainingDataset:
        """
        Build dataset from a directory of images.

        Args:
            source_dir: Directory containing images
            dataset_name: Name for dataset
            trigger_phrase: LoRA trigger phrase
            **kwargs: Additional arguments for build_dataset

        Returns:
            TrainingDataset object
        """
        # Convert images to Frame-like objects
        from core.video_processor import Frame

        image_paths = sorted(source_dir.glob("*.jpg")) + sorted(source_dir.glob("*.png"))

        if not image_paths:
            raise DatasetBuildError(f"No images found in {source_dir}")

        frames = []
        for i, img_path in enumerate(image_paths, 1):
            # Create minimal Frame object
            frame = Frame(
                scene_number=i,
                file_path=img_path,
                timestamp_start=0.0,
                timestamp_end=0.0,
                duration=0.0,
                midpoint=0.0,
                width=0,
                height=0
            )
            frames.append(frame)

        return self.build_dataset(
            frames=frames,
            dataset_name=dataset_name,
            trigger_phrase=trigger_phrase,
            **kwargs
        )
