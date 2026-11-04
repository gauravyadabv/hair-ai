import cv2
import numpy as np
from PIL import Image, ImageOps
from pathlib import Path
from typing import Dict, Any, List, Tuple
from app.core.config import settings

class ImageQualityEngine:
    def __init__(
        self,
        min_dim: int = settings.MIN_IMAGE_DIMENSION,
        blur_threshold: float = settings.BLUR_THRESHOLD_LAPLACIAN,
        min_brightness: float = settings.BRIGHTNESS_MIN,
        max_brightness: float = settings.BRIGHTNESS_MAX,
        min_contrast: float = settings.CONTRAST_MIN
    ):
        self.min_dim = min_dim
        self.blur_threshold = blur_threshold
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_contrast = min_contrast

    def check_and_correct_orientation(self, pil_image: Image.Image) -> Image.Image:
        """Corrects image orientation based on EXIF tag and strips EXIF."""
        try:
            corrected = ImageOps.exif_transpose(pil_image)
            return corrected if corrected is not None else pil_image
        except Exception:
            return pil_image

    def evaluate_quality(
        self,
        image_path: Path | str,
        image_id: str,
        angle: str
    ) -> Dict[str, Any]:
        """
        Runs complete image quality diagnostics:
        1. Decode validation
        2. Resolution checks
        3. Laplacian blur variance
        4. Brightness & overexposure/underexposure
        5. Contrast variance
        6. Generates status: 'acceptable', 'needs_improvement', or 'rejected'
        """
        path_str = str(image_path)
        warnings: List[str] = []
        is_rejected = False

        # 1. Validation & Decoding
        try:
            # Load with PIL first to verify validity
            with Image.open(path_str) as img:
                img.verify()
        except Exception as e:
            return {
                "image_id": image_id,
                "angle": angle,
                "quality_status": "rejected",
                "blur_score": 0.0,
                "brightness_score": 0.0,
                "contrast_score": 0.0,
                "resolution": {"width": 0, "height": 0},
                "is_blurry": False,
                "is_dark": False,
                "is_overexposed": False,
                "is_low_contrast": False,
                "warnings": [f"Image file is corrupted or unreadable: {str(e)}"]
            }

        # Read into OpenCV
        cv_img = cv2.imread(path_str)
        if cv_img is None:
            return {
                "image_id": image_id,
                "angle": angle,
                "quality_status": "rejected",
                "blur_score": 0.0,
                "brightness_score": 0.0,
                "contrast_score": 0.0,
                "resolution": {"width": 0, "height": 0},
                "is_blurry": False,
                "is_dark": False,
                "is_overexposed": False,
                "is_low_contrast": False,
                "warnings": ["Failed to decode image pixels with OpenCV."]
            }

        height, width = cv_img.shape[:2]
        resolution = {"width": width, "height": height}

        # 2. Resolution check
        if width < self.min_dim or height < self.min_dim:
            warnings.append(
                f"Resolution {width}x{height} is below the minimum required {self.min_dim}x{self.min_dim} pixels."
            )
            is_rejected = True

        # Convert to Grayscale
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

        # 3. Blur detection (Laplacian variance)
        # Higher score = sharper, Lower score = blurry
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        is_blurry = laplacian_var < self.blur_threshold

        if laplacian_var < (self.blur_threshold * 0.4):
            # Extremely blurry -> reject
            warnings.append(
                f"Severe blur detected (score: {laplacian_var:.1f}, minimum threshold: {self.blur_threshold:.1f}). Focus is insufficient."
            )
            is_rejected = True
        elif is_blurry:
            warnings.append(
                f"Slight blur detected (score: {laplacian_var:.1f}). For optimal analysis, hold the camera steady."
            )

        # 4. Brightness measurement (mean grayscale intensity)
        mean_brightness = float(np.mean(gray))
        is_dark = mean_brightness < self.min_brightness
        is_overexposed = mean_brightness > self.max_brightness

        if mean_brightness < 20.0:
            warnings.append(
                f"Image is excessively dark (brightness: {mean_brightness:.1f}/255). Scalp details cannot be seen."
            )
            is_rejected = True
        elif is_dark:
            warnings.append(
                f"Image lighting is dim (brightness: {mean_brightness:.1f}/255). Brighter, even lighting recommended."
            )

        if mean_brightness > 240.0:
            warnings.append(
                f"Image is heavily overexposed/blown out (brightness: {mean_brightness:.1f}/255). Glare obscures hair."
            )
            is_rejected = True
        elif is_overexposed:
            warnings.append(
                f"High brightness or glare detected (brightness: {mean_brightness:.1f}/255). Avoid direct flash reflections."
            )

        # 5. Contrast measurement (standard deviation of grayscale intensity)
        contrast = float(np.std(gray))
        is_low_contrast = contrast < self.min_contrast
        if contrast < 12.0:
            warnings.append(
                f"Extremely low contrast ({contrast:.1f}). Hair strands cannot be differentiated."
            )
            is_rejected = True
        elif is_low_contrast:
            warnings.append(
                f"Low contrast ({contrast:.1f}). Consider clearer lighting distinction between scalp and hair."
            )

        # Determine overall quality status
        if is_rejected:
            status = "rejected"
        elif len(warnings) > 0:
            status = "needs_improvement"
        else:
            status = "acceptable"

        return {
            "image_id": image_id,
            "angle": angle,
            "quality_status": status,
            "blur_score": round(laplacian_var, 2),
            "brightness_score": round(mean_brightness, 2),
            "contrast_score": round(contrast, 2),
            "resolution": resolution,
            "is_blurry": is_blurry,
            "is_dark": is_dark,
            "is_overexposed": is_overexposed,
            "is_low_contrast": is_low_contrast,
            "warnings": warnings
        }

image_quality_engine = ImageQualityEngine()

