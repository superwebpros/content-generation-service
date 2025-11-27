"""
LoRA storage and versioning module.

Handles:
- Downloading trained LoRAs
- Versioning and metadata
- Listing and retrieving LoRAs
"""

import json
import requests
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from utils.logger import get_logger

logger = get_logger(__name__)


class LoRAStorage:
    """Manage LoRA storage and versioning."""

    def __init__(self, output_dir: Path):
        """
        Initialize LoRA storage.

        Args:
            output_dir: Base directory for storing LoRAs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_lora(
        self,
        lora_name: str,
        lora_url: str,
        config_url: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Download and save a trained LoRA.

        Args:
            lora_name: Name for this LoRA
            lora_url: URL to download LoRA from
            config_url: Optional config file URL
            metadata: Optional metadata dict

        Returns:
            Dict with save info

        Raises:
            Exception: If download or save fails
        """
        try:
            logger.info(f"Saving LoRA: {lora_name}")

            # Create LoRA directory
            lora_dir = self.output_dir / lora_name
            lora_dir.mkdir(parents=True, exist_ok=True)

            # Download LoRA file
            lora_path = lora_dir / f"{lora_name}.safetensors"
            self._download_file(lora_url, lora_path)
            logger.info(f"✓ Downloaded LoRA: {lora_path}")

            # Download config if available
            config_path = None
            if config_url:
                config_path = lora_dir / f"{lora_name}_config.json"
                self._download_file(config_url, config_path)
                logger.info(f"✓ Downloaded config: {config_path}")

            # Save metadata
            metadata = metadata or {}
            metadata.update({
                "lora_name": lora_name,
                "lora_url": lora_url,
                "config_url": config_url,
                "saved_at": datetime.now().isoformat(),
                "lora_path": str(lora_path),
                "config_path": str(config_path) if config_path else None
            })

            metadata_path = lora_dir / "metadata.json"
            metadata_path.write_text(json.dumps(metadata, indent=2))
            logger.info(f"✓ Saved metadata: {metadata_path}")

            return {
                "lora_name": lora_name,
                "lora_path": lora_path,
                "config_path": config_path,
                "metadata_path": metadata_path,
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"Failed to save LoRA: {e}")
            raise

    def _download_file(self, url: str, output_path: Path) -> None:
        """Download file from URL."""
        logger.info(f"Downloading: {url}")

        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

        logger.info(f"  Downloaded {downloaded / 1024 / 1024:.2f} MB")

    def list_loras(self) -> List[Dict]:
        """
        List all stored LoRAs.

        Returns:
            List of LoRA metadata dicts
        """
        loras = []

        for lora_dir in self.output_dir.iterdir():
            if not lora_dir.is_dir():
                continue

            metadata_path = lora_dir / "metadata.json"
            if not metadata_path.exists():
                continue

            try:
                metadata = json.loads(metadata_path.read_text())
                loras.append(metadata)
            except Exception as e:
                logger.warning(f"Could not load metadata for {lora_dir.name}: {e}")

        # Sort by saved_at (newest first)
        loras.sort(key=lambda x: x.get("saved_at", ""), reverse=True)
        return loras

    def get_lora(self, lora_name: str) -> Optional[Dict]:
        """
        Get LoRA metadata by name.

        Args:
            lora_name: Name of LoRA

        Returns:
            Metadata dict or None if not found
        """
        lora_dir = self.output_dir / lora_name
        metadata_path = lora_dir / "metadata.json"

        if not metadata_path.exists():
            return None

        try:
            return json.loads(metadata_path.read_text())
        except Exception as e:
            logger.error(f"Could not load LoRA metadata: {e}")
            return None

    def get_lora_path(self, lora_name: str) -> Optional[Path]:
        """
        Get path to LoRA file.

        Args:
            lora_name: Name of LoRA

        Returns:
            Path to .safetensors file or None if not found
        """
        lora_dir = self.output_dir / lora_name
        lora_path = lora_dir / f"{lora_name}.safetensors"

        if lora_path.exists():
            return lora_path
        return None

    def delete_lora(self, lora_name: str) -> bool:
        """
        Delete a LoRA.

        Args:
            lora_name: Name of LoRA to delete

        Returns:
            True if deleted, False if not found
        """
        lora_dir = self.output_dir / lora_name

        if not lora_dir.exists():
            logger.warning(f"LoRA not found: {lora_name}")
            return False

        try:
            import shutil
            shutil.rmtree(lora_dir)
            logger.info(f"✓ Deleted LoRA: {lora_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete LoRA: {e}")
            return False
