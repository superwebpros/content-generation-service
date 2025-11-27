"""
Image captioning utilities for LoRA training datasets.

Generates captions for training images using templates or auto-captioning.
"""

from pathlib import Path
from typing import List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class CaptionGenerator:
    """Generate captions for LoRA training images."""

    def __init__(
        self,
        trigger_phrase: str = "person",
        template: str = "a portrait of {trigger}",
        variation_templates: Optional[List[str]] = None
    ):
        """
        Initialize caption generator.

        Args:
            trigger_phrase: Trigger word for LoRA activation
            template: Default caption template
            variation_templates: Optional list of template variations
        """
        self.trigger_phrase = trigger_phrase
        self.template = template
        self.variation_templates = variation_templates or [
            "a portrait of {trigger}",
            "a photo of {trigger}",
            "{trigger} looking at camera",
            "a professional photo of {trigger}",
            "a headshot of {trigger}",
        ]

    def generate_caption(self, image_path: Path, use_variations: bool = True) -> str:
        """
        Generate caption for an image.

        Args:
            image_path: Path to image
            use_variations: Use template variations for diversity

        Returns:
            Generated caption string
        """
        if use_variations:
            # Cycle through variations based on image index
            # Extract number from filename (e.g., frame_0001.jpg -> 1)
            try:
                idx = int(image_path.stem.split("_")[-1])
                template_idx = idx % len(self.variation_templates)
                template = self.variation_templates[template_idx]
            except (ValueError, IndexError):
                template = self.template
        else:
            template = self.template

        caption = template.format(trigger=self.trigger_phrase)
        return caption

    def generate_captions_for_dataset(
        self,
        image_paths: List[Path],
        output_dir: Path,
        use_variations: bool = True
    ) -> List[Path]:
        """
        Generate caption files for a dataset.

        Args:
            image_paths: List of image paths
            output_dir: Directory to save caption files
            use_variations: Use template variations

        Returns:
            List of created caption file paths
        """
        logger.info(f"Generating captions for {len(image_paths)} images...")
        output_dir.mkdir(parents=True, exist_ok=True)

        caption_paths = []

        for image_path in image_paths:
            # Generate caption
            caption = self.generate_caption(image_path, use_variations)

            # Save caption file (same name as image, .txt extension)
            caption_path = output_dir / f"{image_path.stem}.txt"
            caption_path.write_text(caption)
            caption_paths.append(caption_path)

        logger.info(f"✓ Generated {len(caption_paths)} caption files")
        return caption_paths

    def create_training_dataset(
        self,
        image_paths: List[Path],
        dataset_dir: Path,
        use_variations: bool = True
    ) -> Path:
        """
        Create a complete training dataset with images and captions.

        Args:
            image_paths: List of source image paths
            dataset_dir: Base directory for dataset
            use_variations: Use caption variations

        Returns:
            Path to dataset directory
        """
        logger.info(f"Creating training dataset in {dataset_dir}")

        # Create subdirectories
        images_dir = dataset_dir / "images"
        captions_dir = dataset_dir / "captions"
        images_dir.mkdir(parents=True, exist_ok=True)
        captions_dir.mkdir(parents=True, exist_ok=True)

        # Copy images and generate captions
        import shutil

        copied_images = []
        for i, image_path in enumerate(image_paths, 1):
            # Copy image
            dest_image = images_dir / f"{i:04d}.jpg"
            shutil.copy2(image_path, dest_image)
            copied_images.append(dest_image)

            # Generate caption
            caption = self.generate_caption(image_path, use_variations)
            caption_path = captions_dir / f"{i:04d}.txt"
            caption_path.write_text(caption)

            logger.info(f"  {i}/{len(image_paths)}: {dest_image.name} → '{caption}'")

        logger.info(f"✓ Created dataset: {len(copied_images)} images + captions")
        return dataset_dir


def create_simple_captions(
    image_paths: List[Path],
    trigger_phrase: str = "person",
    output_dir: Optional[Path] = None
) -> None:
    """
    Create simple captions for images (convenience function).

    Args:
        image_paths: List of image paths
        trigger_phrase: Trigger phrase for LoRA
        output_dir: Output directory (default: same as images)
    """
    generator = CaptionGenerator(trigger_phrase=trigger_phrase)

    for image_path in image_paths:
        caption = generator.generate_caption(image_path, use_variations=False)
        out_dir = output_dir or image_path.parent
        caption_path = out_dir / f"{image_path.stem}.txt"
        caption_path.write_text(caption)
