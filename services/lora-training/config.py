"""
Configuration management for LoRA extraction pipeline.

Centralizes environment variables, validation, and defaults.
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Config:
    """Configuration for LoRA extraction pipeline."""

    # API Keys
    fal_api_key: Optional[str] = None
    replicate_api_token: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Provider settings
    training_provider: str = "fal_ai"  # "fal_ai" or "runpod"

    # Training defaults (aligned with fal.ai API defaults)
    default_steps: int = 2500
    default_learning_rate: float = 0.00009
    default_trigger_phrase: str = "person"

    # Paths
    temp_dir: Path = Path("/tmp/lora-extraction")
    output_dir: Path = Path("./lora-output")
    dataset_dir: Path = Path("./datasets")

    # Video processing
    extraction_mode: str = "scene"  # "scene" or "interval"
    scene_threshold: float = 0.03  # Lower = more scenes (testing for more granular detection)
    interval_seconds: float = 3.0  # Extract frame every N seconds (for interval mode)
    target_fps: float = 2.0
    min_frames: int = 10  # Lower for manual curation workflow
    max_frames: int = 50

    # Dataset quality control
    min_face_confidence: float = 0.8
    min_image_quality: float = 0.6
    blur_threshold: float = 100.0

    # Captioning
    caption_template: str = "a portrait of {trigger} {phrase}"
    use_auto_captions: bool = False

    def __post_init__(self):
        """Load and validate configuration."""
        # Load API keys from environment
        self.fal_api_key = os.getenv("FAL_KEY") or os.getenv("FAL_API_KEY")
        self.replicate_api_token = os.getenv("REPLICATE_API_TOKEN")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        # Load provider from environment
        self.training_provider = os.getenv("TRAINING_PROVIDER", "fal_ai")

        # Convert string paths to Path objects if needed
        self.temp_dir = Path(self.temp_dir)
        self.output_dir = Path(self.output_dir)
        self.dataset_dir = Path(self.dataset_dir)

        # Create directories if they don't exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dataset_dir.mkdir(parents=True, exist_ok=True)

    def validate_provider(self, provider: Optional[str] = None) -> None:
        """
        Validate that required API keys are present for the provider.

        Args:
            provider: Provider to validate (defaults to self.training_provider)

        Raises:
            ValueError: If required API keys are missing
        """
        provider = provider or self.training_provider

        if provider == "fal_ai":
            if not self.fal_api_key:
                raise ValueError(
                    "FAL_API_KEY not found. Set FAL_KEY or FAL_API_KEY in .env"
                )
        elif provider == "runpod":
            # RunPod will need different validation
            pass
        else:
            raise ValueError(
                f"Unknown provider: {provider}. Use 'fal_ai' or 'runpod'"
            )

    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables."""
        return cls()

    def get_training_params(self) -> dict:
        """Get default training parameters as dict."""
        return {
            "steps": self.default_steps,
            "learning_rate": self.default_learning_rate,
            "trigger_phrase": self.default_trigger_phrase,
        }


# Global config instance
config = Config.from_env()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config
