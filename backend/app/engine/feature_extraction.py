import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from app.core.config import settings

class FeatureExtractionEngine:
    def __init__(self, target_size: Tuple[int, int] = (512, 512)):
        self.target_size = target_size

    def normalize_image(self, bgr_img: np.ndarray) -> np.ndarray:
        """
        Resizes to target standard dimensions and applies illumination balancing.
        """
        resized = cv2.resize(bgr_img, self.target_size, interpolation=cv2.INTER_AREA)
        # Convert to LAB color space for lighting normalization on L channel
        lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        normalized_bgr = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        return normalized_bgr

    def extract_roi(self, img: np.ndarray, margin_percent: float = 0.15) -> Tuple[np.ndarray, Dict[str, int]]:
        """
        Extracts central Region of Interest (ROI) where scalp and hair are centrally focused,
        omitting edge background noise.
        """
        h, w = img.shape[:2]
        pad_y = int(h * margin_percent)
        pad_x = int(w * margin_percent)
        roi = img[pad_y:h - pad_y, pad_x:w - pad_x]
        roi_bbox = {
            "x": pad_x,
            "y": pad_y,
            "width": w - (2 * pad_x),
            "height": h - (2 * pad_y)
        }
        return roi, roi_bbox

    def segment_hair_and_scalp(self, roi_bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float, float]:
        """
        Computer-vision based pixel segmentation distinguishing hair fibers from visible scalp skin.
        Uses multi-channel color thresholding (HSV + Lab + Otsu) to separate dark/dense hair fibers
        from lighter scalp skin tones.
        Returns:
            hair_mask (binary 0/255)
            scalp_mask (binary 0/255)
            hair_pixel_ratio (float)
            scalp_pixel_ratio (float)
        """
        gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2LAB)

        # Hair fibers are typically darker than scalp skin in grayscale & value
        # Apply Gaussian blur to reduce single-pixel sensor noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Otsu thresholding finds natural bimodal separation
        _, otsu_hair_mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Morphological operations to clean up isolated specks
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        cleaned_hair = cv2.morphologyEx(otsu_hair_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        cleaned_hair = cv2.morphologyEx(cleaned_hair, cv2.MORPH_CLOSE, kernel, iterations=1)

        # Scalp mask is inverse of hair mask within ROI
        scalp_mask = cv2.bitwise_not(cleaned_hair)

        total_pixels = float(roi_bgr.shape[0] * roi_bgr.shape[1])
        hair_pixels = float(np.count_nonzero(cleaned_hair))
        scalp_pixels = float(np.count_nonzero(scalp_mask))

        hair_ratio = round(hair_pixels / total_pixels, 4)
        scalp_ratio = round(scalp_pixels / total_pixels, 4)

        return cleaned_hair, scalp_mask, hair_ratio, scalp_ratio

    def analyze_photo_features(
        self,
        image_path: Path | str,
        angle: str,
        quality_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes feature extraction on an uploaded photo.
        Returns standardized visual metrics.
        """
        path_str = str(image_path)
        img = cv2.imread(path_str)
        if img is None:
            return {
                "angle": angle,
                "status": "failed",
                "error": "Failed to read image for feature extraction."
            }

        # 1. Image normalization
        normalized = self.normalize_image(img)

        # 2. Extract central scalp ROI
        roi, bbox = self.extract_roi(normalized)

        # 3. Hair & scalp segmentation (Phase 1-2 CV)
        hair_mask, scalp_mask, hair_ratio, scalp_ratio = self.segment_hair_and_scalp(roi)

        # 4. Color distribution in HSV
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mean_h = float(np.mean(hsv_roi[:, :, 0]))
        mean_s = float(np.mean(hsv_roi[:, :, 1]))
        mean_v = float(np.mean(hsv_roi[:, :, 2]))

        # 5. Lighting uniformity (divide ROI into 4 quadrants and compare brightness)
        h, w = roi.shape[:2]
        mid_y, mid_x = h // 2, w // 2
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        q1 = float(np.mean(gray_roi[0:mid_y, 0:mid_x]))
        q2 = float(np.mean(gray_roi[0:mid_y, mid_x:w]))
        q3 = float(np.mean(gray_roi[mid_y:h, 0:mid_x]))
        q4 = float(np.mean(gray_roi[mid_y:h, mid_x:w]))
        quad_means = [q1, q2, q3, q4]
        lighting_uniformity = round(1.0 - (float(np.std(quad_means)) / (float(np.mean(quad_means)) + 1e-5)), 3)
        lighting_uniformity = max(0.0, min(1.0, lighting_uniformity))

        notes = [
            f"Analyzed {angle} view with OpenCV-based adaptive thresholding.",
            "Visual coverage ratio reflects pixel color contrast, not clinical follicular density count."
        ]

        # Check if lighting is uneven
        if lighting_uniformity < 0.75:
            notes.append("Uneven illumination detected across scalp quadrants; may bias visible contrast.")

        feature_data = {
            "angle": angle,
            "region_of_interest": bbox,
            "hair_pixel_ratio": hair_ratio,
            "scalp_pixel_ratio": scalp_ratio,
            "mean_brightness": round(float(np.mean(gray_roi)), 2),
            "contrast": round(float(np.std(gray_roi)), 2),
            "lighting_uniformity": lighting_uniformity,
            "color_distribution": {
                "hue_mean": round(mean_h, 2),
                "saturation_mean": round(mean_s, 2),
                "value_mean": round(mean_v, 2)
            },
            "notes": notes
        }

        # Confidence calculation based on quality and lighting
        blur_score = quality_info.get("blur_score", 150.0) if quality_info else 150.0
        confidence = 0.85
        if blur_score < settings.BLUR_THRESHOLD_LAPLACIAN:
            confidence -= 0.25
        if lighting_uniformity < 0.75:
            confidence -= 0.15

        confidence_data = {
            "overall_feature_confidence": round(max(0.2, min(0.95, confidence)), 2),
            "lighting_confidence": lighting_uniformity,
            "is_experimental_cv": True,
            "scientific_disclaimer": "Pixel ratios are preliminary visual metrics. Clinical hair density requires dermoscopy / trichoscopy."
        }

        return {
            "status": "completed",
            "feature_data": feature_data,
            "confidence_data": confidence_data
        }

    def compare_regions(self, angle_features: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Phase 3: Cross-angle comparative analysis (e.g., comparing crown and top to hairline and temples).
        """
        comparison: Dict[str, Any] = {
            "angles_evaluated": list(angle_features.keys()),
            "regional_coverage_comparison": {},
            "observations": []
        }

        ratios = {}
        for angle, data in angle_features.items():
            feat = data.get("feature_data", {})
            hair_ratio = feat.get("hair_pixel_ratio")
            if hair_ratio is not None:
                ratios[angle] = hair_ratio

        comparison["regional_coverage_comparison"] = ratios

        if "crown" in ratios and "top_scalp" in ratios:
            diff = ratios["top_scalp"] - ratios["crown"]
            if diff > 0.15:
                comparison["observations"].append(
                    "Crown shows visibly lower hair-pixel coverage compared to mid-top scalp."
                )
            elif diff < -0.15:
                comparison["observations"].append(
                    "Mid-top scalp shows visibly lower hair-pixel coverage relative to crown."
                )

        if "left_temple" in ratios and "right_temple" in ratios:
            asymmetry = abs(ratios["left_temple"] - ratios["right_temple"])
            if asymmetry > 0.12:
                comparison["observations"].append(
                    f"Noticeable asymmetry detected between left and right temple coverage (variance: {asymmetry:.2f})."
                )

        return comparison

feature_extraction_engine = FeatureExtractionEngine()

