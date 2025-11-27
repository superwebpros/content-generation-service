"""
Video processing module for extracting frames from videos.

Handles:
- Video download from URLs
- Scene detection
- Keyframe extraction
- Frame metadata
"""

import subprocess
import requests
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from urllib.parse import urlparse

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Frame:
    """Metadata for an extracted frame."""
    scene_number: int
    file_path: Path
    timestamp_start: float
    timestamp_end: float
    duration: float
    midpoint: float
    width: int
    height: int


class VideoProcessingError(Exception):
    """Base exception for video processing errors."""
    pass


class VideoProcessor:
    """Process videos to extract frames for LoRA training."""

    def __init__(
        self,
        temp_dir: Path,
        extraction_mode: str = "scene",
        scene_threshold: float = 0.15,
        interval_seconds: float = 3.0
    ):
        """
        Initialize video processor.

        Args:
            temp_dir: Directory for temporary files
            extraction_mode: Extraction strategy ("scene" or "interval")
            scene_threshold: Scene detection threshold (0.0-1.0, lower = more scenes)
            interval_seconds: Extract frame every N seconds (for interval mode)
        """
        self.temp_dir = Path(temp_dir)
        self.extraction_mode = extraction_mode
        self.scene_threshold = scene_threshold
        self.interval_seconds = interval_seconds
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def download_video(self, video_url: str, output_path: Path) -> None:
        """
        Download video from URL or copy from local path.

        Args:
            video_url: URL to download from (http://, https://, s3://) or local file path
            output_path: Path to save video

        Raises:
            VideoProcessingError: If download/copy fails
        """
        try:
            logger.info(f"Loading video from: {video_url}")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Check if local file path
            local_path = Path(video_url)
            if local_path.exists() and local_path.is_file():
                # Copy local file
                import shutil
                logger.info(f"Copying local file: {local_path}")
                shutil.copy2(local_path, output_path)
                file_size = output_path.stat().st_size / 1024 / 1024
                logger.info(f"✓ Copied {file_size:.2f} MB to {output_path.name}")
                return

            # Parse URL
            parsed = urlparse(video_url)

            if parsed.scheme == "s3":
                # S3 download
                self._download_from_s3(video_url, output_path)
            elif parsed.scheme in ["http", "https"]:
                # HTTP/HTTPS download
                response = requests.get(video_url, stream=True, timeout=120)
                response.raise_for_status()

                downloaded = 0
                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                logger.info(f"✓ Downloaded {downloaded / 1024 / 1024:.2f} MB to {output_path.name}")
            else:
                raise VideoProcessingError(
                    f"Unsupported URL scheme: {parsed.scheme}. "
                    f"Use http://, https://, s3://, or a local file path."
                )

        except requests.exceptions.RequestException as e:
            raise VideoProcessingError(f"Failed to download video: {e}")
        except IOError as e:
            raise VideoProcessingError(f"Failed to copy/save video: {e}")

    def _download_from_s3(self, s3_url: str, output_path: Path) -> None:
        """
        Download video from S3.

        Args:
            s3_url: S3 URL (s3://bucket/key)
            output_path: Path to save video

        Raises:
            VideoProcessingError: If S3 download fails
        """
        try:
            import boto3
            from botocore.exceptions import ClientError

            # Parse S3 URL: s3://bucket/key
            parsed = urlparse(s3_url)
            bucket = parsed.netloc
            key = parsed.path.lstrip("/")

            logger.info(f"Downloading from S3: {bucket}/{key}")

            # Initialize S3 client
            s3 = boto3.client("s3")

            # Download file
            s3.download_file(bucket, key, str(output_path))

            file_size = output_path.stat().st_size / 1024 / 1024
            logger.info(f"✓ Downloaded {file_size:.2f} MB from S3 to {output_path.name}")

        except ImportError:
            raise VideoProcessingError(
                "boto3 not installed. Install with: pip install boto3"
            )
        except ClientError as e:
            raise VideoProcessingError(f"S3 download failed: {e}")
        except Exception as e:
            raise VideoProcessingError(f"Failed to download from S3: {e}")

    def detect_scenes(self, video_path: Path) -> List[Tuple[float, float]]:
        """
        Detect scene boundaries using ffmpeg.

        Args:
            video_path: Path to video file

        Returns:
            List of (start_time, end_time) tuples in seconds

        Raises:
            VideoProcessingError: If scene detection fails
        """
        try:
            logger.info(f"Detecting scenes (threshold: {self.scene_threshold})")

            # Use ffmpeg scene detection
            cmd = [
                "ffmpeg",
                "-i", str(video_path),
                "-filter:v", f"select='gt(scene,{self.scene_threshold})',showinfo",
                "-f", "null",
                "-"
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
                text=True
            )

            # Parse scene timestamps
            import re
            scene_times = []
            for line in result.stderr.split("\n"):
                if "Parsed_showinfo" in line and "pts_time:" in line:
                    match = re.search(r"pts_time:([\d.]+)", line)
                    if match:
                        scene_times.append(float(match.group(1)))

            # Get video duration
            duration = self._get_video_duration(video_path)

            # Build scene list
            if not scene_times:
                logger.warning("No scenes detected, treating entire video as one scene")
                return [(0.0, duration)]

            scenes = []
            start_time = 0.0
            for scene_time in scene_times:
                scenes.append((start_time, scene_time))
                start_time = scene_time
            scenes.append((start_time, duration))

            logger.info(f"✓ Detected {len(scenes)} scenes")
            return scenes

        except subprocess.TimeoutExpired:
            raise VideoProcessingError("Scene detection timed out")
        except Exception as e:
            raise VideoProcessingError(f"Failed to detect scenes: {e}")

    def extract_intervals(self, video_path: Path, interval_seconds: float) -> List[Tuple[float, float]]:
        """
        Extract frames at regular time intervals.

        Args:
            video_path: Path to video file
            interval_seconds: Extract a frame every N seconds

        Returns:
            List of (start_time, end_time) tuples in seconds

        Raises:
            VideoProcessingError: If interval extraction fails
        """
        try:
            logger.info(f"Creating intervals (every {interval_seconds}s)")

            # Get video duration
            duration = self._get_video_duration(video_path)

            # Create intervals
            intervals = []
            current_time = 0.0

            while current_time < duration:
                end_time = min(current_time + interval_seconds, duration)
                intervals.append((current_time, end_time))
                current_time = end_time

            logger.info(f"✓ Created {len(intervals)} intervals")
            return intervals

        except Exception as e:
            raise VideoProcessingError(f"Failed to create intervals: {e}")

    def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            text=True
        )

        try:
            return float(result.stdout.strip())
        except ValueError:
            logger.warning("Could not parse video duration, using default")
            return 30.0

    def extract_frames(
        self,
        video_path: Path,
        scenes: List[Tuple[float, float]],
        output_dir: Path
    ) -> List[Frame]:
        """
        Extract one keyframe per scene.

        Args:
            video_path: Path to video file
            scenes: List of (start_time, end_time) tuples
            output_dir: Directory to save frames

        Returns:
            List of Frame objects

        Raises:
            VideoProcessingError: If extraction fails
        """
        try:
            logger.info(f"Extracting keyframes to {output_dir}")
            output_dir.mkdir(parents=True, exist_ok=True)

            frames = []

            for i, (start_time, end_time) in enumerate(scenes, 1):
                midpoint = (start_time + end_time) / 2
                frame_path = output_dir / f"frame_{i:04d}.jpg"

                # Extract frame at midpoint
                if self._extract_single_frame(video_path, midpoint, frame_path):
                    # Get frame dimensions
                    width, height = self._get_frame_dimensions(frame_path)

                    frame = Frame(
                        scene_number=i,
                        file_path=frame_path,
                        timestamp_start=start_time,
                        timestamp_end=end_time,
                        duration=end_time - start_time,
                        midpoint=midpoint,
                        width=width,
                        height=height
                    )
                    frames.append(frame)
                    logger.info(f"  ✓ Frame {i}/{len(scenes)}: {frame_path.name} ({width}x{height})")
                else:
                    logger.warning(f"  ✗ Failed to extract frame {i}")

            logger.info(f"✓ Extracted {len(frames)}/{len(scenes)} frames")
            return frames

        except Exception as e:
            raise VideoProcessingError(f"Failed to extract frames: {e}")

    def _extract_single_frame(
        self,
        video_path: Path,
        timestamp: float,
        output_path: Path
    ) -> bool:
        """Extract a single frame at timestamp."""
        cmd = [
            "ffmpeg",
            "-ss", str(timestamp),
            "-i", str(video_path),
            "-frames:v", "1",
            "-q:v", "2",
            "-update", "1",
            str(output_path),
            "-y"
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )
            return result.returncode == 0 and output_path.exists()
        except subprocess.TimeoutExpired:
            return False

    def _get_frame_dimensions(self, frame_path: Path) -> Tuple[int, int]:
        """Get frame dimensions using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            str(frame_path)
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
                text=True
            )
            width, height = result.stdout.strip().split(",")
            return int(width), int(height)
        except Exception:
            return 0, 0

    def process_video(
        self,
        video_url: str,
        video_id: str,
        output_dir: Optional[Path] = None
    ) -> Dict:
        """
        Process video end-to-end: download → detect scenes → extract frames.

        Args:
            video_url: URL to download video from
            video_id: Unique identifier for this video
            output_dir: Optional output directory (default: temp_dir/frames/{video_id})

        Returns:
            Dict with processing results
        """
        try:
            logger.info("=" * 80)
            logger.info(f"Processing video: {video_id}")
            logger.info("=" * 80)

            # Setup paths
            video_path = self.temp_dir / f"video_{video_id}.mp4"
            frames_dir = output_dir or (self.temp_dir / "frames" / video_id)

            # Download video
            self.download_video(video_url, video_path)

            # Extract frames based on mode
            if self.extraction_mode == "interval":
                intervals = self.extract_intervals(video_path, self.interval_seconds)
                frames = self.extract_frames(video_path, intervals, frames_dir)
                extraction_count = len(intervals)
            else:  # default to scene detection
                scenes = self.detect_scenes(video_path)
                frames = self.extract_frames(video_path, scenes, frames_dir)
                extraction_count = len(scenes)

            # Cleanup video file
            video_path.unlink()
            logger.info(f"✓ Cleaned up video file")

            return {
                "success": True,
                "video_id": video_id,
                "video_url": video_url,
                "scenes_detected": extraction_count,
                "frames_extracted": len(frames),
                "frames": frames,
                "frames_dir": frames_dir,
                "error": None
            }

        except VideoProcessingError as e:
            logger.error(f"✗ Processing failed: {e}")
            return {
                "success": False,
                "video_id": video_id,
                "video_url": video_url,
                "scenes_detected": 0,
                "frames_extracted": 0,
                "frames": [],
                "frames_dir": None,
                "error": str(e)
            }
