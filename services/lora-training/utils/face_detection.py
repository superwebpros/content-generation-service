"""
Face detection and image quality assessment utilities.

Uses OpenCV for face detection and blur detection.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional
from dataclasses import dataclass

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ImageQuality:
    """Image quality assessment results."""
    has_face: bool
    face_count: int
    face_confidence: float
    blur_score: float
    is_acceptable: bool
    width: int
    height: int


class FaceDetector:
    """Detect faces and assess image quality for LoRA training."""

    def __init__(
        self,
        min_face_confidence: float = 0.8,
        blur_threshold: float = 100.0,
        min_quality: float = 0.6
    ):
        """
        Initialize face detector.

        Args:
            min_face_confidence: Minimum confidence for face detection
            blur_threshold: Laplacian variance threshold (higher = less blur tolerance)
            min_quality: Minimum overall quality score (0-1)
        """
        self.min_face_confidence = min_face_confidence
        self.blur_threshold = blur_threshold
        self.min_quality = min_quality

        # Load OpenCV face detector (Haar Cascade)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

        if self.face_cascade.empty():
            logger.warning("Failed to load face cascade classifier")

    def detect_blur(self, image: np.ndarray) -> float:
        """
        Detect blur using Laplacian variance method.

        Args:
            image: Input image (BGR)

        Returns:
            Blur score (higher = sharper image)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        return float(laplacian_var)

    def detect_faces(self, image: np.ndarray) -> Tuple[int, float]:
        """
        Detect faces in image.

        Args:
            image: Input image (BGR)

        Returns:
            Tuple of (face_count, max_confidence)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        if len(faces) == 0:
            return 0, 0.0

        # For Haar cascades, we don't get confidence scores
        # Use face size as a proxy for confidence
        face_sizes = [w * h for (x, y, w, h) in faces]
        max_size = max(face_sizes)
        image_size = gray.shape[0] * gray.shape[1]

        # Normalize to 0-1 (assume faces >10% of image are good)
        confidence = min(1.0, (max_size / image_size) * 10)

        return len(faces), confidence

    def assess_quality(self, image_path: Path) -> Optional[ImageQuality]:
        """
        Assess image quality for LoRA training.

        Args:
            image_path: Path to image file

        Returns:
            ImageQuality object or None if image cannot be read
        """
        try:
            # Read image
            image = cv2.imread(str(image_path))
            if image is None:
                logger.warning(f"Could not read image: {image_path}")
                return None

            height, width = image.shape[:2]

            # Detect faces
            face_count, face_confidence = self.detect_faces(image)
            has_face = face_count > 0

            # Detect blur
            blur_score = self.detect_blur(image)

            # Calculate overall acceptability
            is_acceptable = (
                has_face and
                face_confidence >= self.min_face_confidence and
                blur_score >= self.blur_threshold
            )

            return ImageQuality(
                has_face=has_face,
                face_count=face_count,
                face_confidence=face_confidence,
                blur_score=blur_score,
                is_acceptable=is_acceptable,
                width=width,
                height=height
            )

        except Exception as e:
            logger.error(f"Error assessing image quality: {e}")
            return None

    def filter_quality_frames(
        self,
        frame_paths: list[Path],
        verbose: bool = True
    ) -> Tuple[list[Path], list[ImageQuality]]:
        """
        Filter frames based on quality criteria.

        Args:
            frame_paths: List of paths to frame images
            verbose: Log detailed results

        Returns:
            Tuple of (accepted_paths, quality_assessments)
        """
        accepted = []
        qualities = []

        logger.info(f"Assessing quality of {len(frame_paths)} frames...")

        for i, frame_path in enumerate(frame_paths, 1):
            quality = self.assess_quality(frame_path)

            if quality is None:
                continue

            qualities.append(quality)

            if quality.is_acceptable:
                accepted.append(frame_path)
                if verbose:
                    logger.info(
                        f"  ✓ Frame {i}: PASS "
                        f"(faces={quality.face_count}, "
                        f"conf={quality.face_confidence:.2f}, "
                        f"blur={quality.blur_score:.1f})"
                    )
            else:
                if verbose:
                    reasons = []
                    if not quality.has_face:
                        reasons.append("no face")
                    if quality.face_confidence < self.min_face_confidence:
                        reasons.append(f"low conf ({quality.face_confidence:.2f})")
                    if quality.blur_score < self.blur_threshold:
                        reasons.append(f"blurry ({quality.blur_score:.1f})")

                    logger.info(f"  ✗ Frame {i}: REJECT ({', '.join(reasons)})")

        logger.info(f"✓ Accepted {len(accepted)}/{len(frame_paths)} frames")
        return accepted, qualities
