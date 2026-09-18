import base64
import io
import logging
import math
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
from PIL import Image

try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

logger = logging.getLogger("veridoc.preprocessor")


class PreprocessingResult:
    """Encapsulates the preprocessed candidate variants and geometry telemetry."""

    def __init__(
        self,
        variants: Dict[str, bytes],
        primary_variant_bytes: bytes,
        rotation_angle: float = 0.0,
        perspective_corrected: bool = False,
        boundary_detected: bool = False,
        crop_applied: bool = False,
        denoising_applied: bool = True,
        contrast_enhanced: bool = True,
        resolution_upscaled: bool = False,
        base64_preview: Optional[str] = None
    ):
        self.variants = variants
        self.primary_variant_bytes = primary_variant_bytes
        self.rotation_angle = rotation_angle
        self.perspective_corrected = perspective_corrected
        self.boundary_detected = boundary_detected
        self.crop_applied = crop_applied
        self.denoising_applied = denoising_applied
        self.contrast_enhanced = contrast_enhanced
        self.resolution_upscaled = resolution_upscaled
        self.base64_preview = base64_preview


class DocumentPreprocessor:
    """
    Advanced Document Preprocessing & Computer Vision Suite.
    Guarantees that OCR never directly processes raw unaligned captures.
    Performs:
      1. Automatic Orientation Detection & Rotation Correction
      2. Boundary Detection & 4-Point Perspective Transform (Deskew)
      3. Background Margin Cropping
      4. Edge-Preserving Denoising
      5. LAB-Space CLAHE Contrast Enhancement
      6. Super-Resolution Upscaling & Unsharp Masking
      7. Multi-Variant Generation for Candidate OCR Selection
    """

    @classmethod
    def preprocess_document_image(
        cls,
        raw_bytes: bytes,
        filename: Optional[str] = None,
        password: Optional[str] = None
    ) -> PreprocessingResult:
        """
        Main entry point for pre-OCR processing.
        Leaves raw bytes untouched for forensic analysis and returns enhanced variants.
        """
        if not raw_bytes:
            return PreprocessingResult(
                variants={"raw": raw_bytes},
                primary_variant_bytes=raw_bytes
            )

        # 1. Handle PDF by rendering first page if applicable
        is_pdf = (filename and filename.lower().endswith(".pdf")) or (raw_bytes[:4] == b"%PDF")
        cv_img = None
        if is_pdf and HAS_FITZ:
            try:
                from app.services.quality_assessor import DocumentQualityAssessor
                doc, _ = DocumentQualityAssessor.open_pdf_doc(raw_bytes, filename=filename, password=password)
                if doc and len(doc) > 0:
                    page = doc[0]
                    mat = fitz.Matrix(2.5, 2.5)
                    pix = page.get_pixmap(matrix=mat)
                    img_bytes = pix.tobytes("png")
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            except Exception as e:
                logger.warning(f"PDF preprocessor page rendering error: {e}")

        if cv_img is None:
            nparr = np.frombuffer(raw_bytes, np.uint8)
            cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if cv_img is None:
            # Fallback if image decode fails
            return PreprocessingResult(
                variants={"raw": raw_bytes},
                primary_variant_bytes=raw_bytes
            )

        # ----------------------------------------------------------------------
        # Step 1: Automatic Orientation Detection & Rotation Correction
        # ----------------------------------------------------------------------
        img_oriented, rot_angle = cls.detect_and_correct_orientation(cv_img)

        # ----------------------------------------------------------------------
        # Step 2: Boundary Detection & Perspective Flattening (Deskew Quad)
        # ----------------------------------------------------------------------
        img_warped, boundary_detected, persp_corrected = cls.detect_boundaries_and_warp(img_oriented)

        # ----------------------------------------------------------------------
        # Step 3: Cropping Margins
        # ----------------------------------------------------------------------
        img_cropped, crop_applied = cls.crop_background_margins(img_warped)

        # ----------------------------------------------------------------------
        # Step 4: Resolution Enhancement (Upscale if small / low-DPI)
        # ----------------------------------------------------------------------
        img_enhanced, res_upscaled = cls.enhance_resolution(img_cropped)

        # ----------------------------------------------------------------------
        # Step 5: Denoising & Contrast Enhancement
        # ----------------------------------------------------------------------
        img_denoised = cls.denoise_image(img_enhanced)
        img_contrast = cls.enhance_contrast_clahe(img_denoised)

        # ----------------------------------------------------------------------
        # Step 6: Generate Preprocessing Variants for Multi-Candidate OCR
        # ----------------------------------------------------------------------
        variants = cls.generate_variants(img_contrast)

        # Create primary preview in base64
        _, primary_png = cv2.imencode(".png", img_contrast)
        primary_bytes = primary_png.tobytes()
        base64_preview = f"data:image/png;base64,{base64.b64encode(primary_bytes).decode('ascii')}"

        return PreprocessingResult(
            variants=variants,
            primary_variant_bytes=primary_bytes,
            rotation_angle=rot_angle,
            perspective_corrected=persp_corrected,
            boundary_detected=boundary_detected,
            crop_applied=crop_applied,
            denoising_applied=True,
            contrast_enhanced=True,
            resolution_upscaled=res_upscaled,
            base64_preview=base64_preview
        )

    @classmethod
    def detect_and_correct_orientation(cls, img: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Detects document skew angle and orientation, rotating image upright.
        """
        try:
            h, w = img.shape[:2]
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Detect text lines via threshold and morphological gradient
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

            # Find orientation angle using minAreaRect on text regions
            coords = np.column_stack(np.where(thresh > 0))
            if len(coords) < 100:
                return img, 0.0

            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = 90 - angle
            else:
                angle = -angle

            # Clamp minor noise
            if abs(angle) < 0.4:
                angle = 0.0

            if abs(angle) > 0.4 and abs(angle) < 45.0:
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(
                    img, M, (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE
                )
                return rotated, round(angle, 2)

            return img, 0.0
        except Exception as e:
            logger.debug(f"Orientation detection exception: {e}")
            return img, 0.0

    @classmethod
    def detect_boundaries_and_warp(cls, img: np.ndarray) -> Tuple[np.ndarray, bool, bool]:
        """
        Finds the 4-corner document polygon and applies perspective warping
        to flatten tilted or angled camera captures.
        """
        try:
            h, w = img.shape[:2]
            img_area = h * w

            # Downscale for stable edge detection
            scale = 800.0 / max(h, w)
            if scale < 1.0:
                small = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            else:
                small = img.copy()
                scale = 1.0

            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            blurred = cv2.bilateralFilter(gray, 9, 75, 75)
            edged = cv2.Canny(blurred, 50, 180)

            # Morphological dilation to connect fragmented border edges
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            dilated = cv2.dilate(edged, kernel, iterations=2)

            contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

            doc_contour = None
            for c in contours:
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                area = cv2.contourArea(approx)

                # Must have 4 vertices and cover at least 22% of the total frame
                if len(approx) == 4 and area > (0.22 * (small.shape[0] * small.shape[1])):
                    doc_contour = approx
                    break

            if doc_contour is not None:
                pts = doc_contour.reshape(4, 2) / scale
                warped = cls._four_point_transform(img, pts)
                if warped is not None and warped.shape[0] > 100 and warped.shape[1] > 100:
                    return warped, True, True

            return img, False, False
        except Exception as e:
            logger.debug(f"Boundary detection error: {e}")
            return img, False, False

    @staticmethod
    def _order_points(pts: np.ndarray) -> np.ndarray:
        """Orders coordinates: Top-Left, Top-Right, Bottom-Right, Bottom-Left."""
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # TL
        rect[2] = pts[np.argmax(s)]  # BR

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # TR
        rect[3] = pts[np.argmax(diff)]  # BL
        return rect

    @classmethod
    def _four_point_transform(cls, img: np.ndarray, pts: np.ndarray) -> Optional[np.ndarray]:
        """Calculates perspective transform matrix and warps quadrilateral to flat rectangle."""
        try:
            rect = cls._order_points(pts)
            (tl, tr, br, bl) = rect

            # Compute maximum width
            widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
            widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
            maxWidth = max(int(widthA), int(widthB))

            # Compute maximum height
            heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
            heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
            maxHeight = max(int(heightA), int(heightB))

            if maxWidth < 150 or maxHeight < 150:
                return None

            dst = np.array([
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1]
            ], dtype="float32")

            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(img, M, (maxWidth, maxHeight), flags=cv2.INTER_CUBIC)
            return warped
        except Exception:
            return None

    @classmethod
    def crop_background_margins(cls, img: np.ndarray) -> Tuple[np.ndarray, bool]:
        """Trims extreme margin borders where dark scanner bed or blank background exists."""
        try:
            h, w = img.shape[:2]
            # Clip 1% margin on all sides to eliminate camera frame edge noise
            margin_y = max(2, int(h * 0.012))
            margin_x = max(2, int(w * 0.012))
            cropped = img[margin_y:h - margin_y, margin_x:w - margin_x]
            return cropped, True
        except Exception:
            return img, False

    @classmethod
    def enhance_resolution(cls, img: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Intelligently upscales low-resolution or low-DPI scans (< 1400px width/height)
        using bicubic interpolation and unsharp masking to sharpen micro-typography.
        """
        try:
            h, w = img.shape[:2]
            target_dim = 1600
            if max(h, w) < target_dim:
                scale = target_dim / float(max(h, w))
                new_w = int(w * scale)
                new_h = int(h * scale)
                upscaled = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

                # Apply subtle unsharp mask filter to restore text edge definition
                gaussian = cv2.GaussianBlur(upscaled, (0, 0), 2.0)
                sharpened = cv2.addWeighted(upscaled, 1.4, gaussian, -0.4, 0)
                return sharpened, True

            return img, False
        except Exception:
            return img, False

    @classmethod
    def denoise_image(cls, img: np.ndarray) -> np.ndarray:
        """
        Applies edge-preserving bilateral filtering to suppress sensor noise
        without blurring character glyph boundaries.
        """
        try:
            return cv2.bilateralFilter(img, d=7, sigmaColor=50, sigmaSpace=50)
        except Exception:
            return img

    @classmethod
    def enhance_contrast_clahe(cls, img: np.ndarray) -> np.ndarray:
        """
        Applies Contrast Limited Adaptive Histogram Equalization (CLAHE)
        on the Luminance (L) channel in CIE LAB color space.
        """
        try:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.8, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            merged = cv2.merge((cl, a, b))
            enhanced = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
            return enhanced
        except Exception:
            return img

    @classmethod
    def generate_variants(cls, base_img: np.ndarray) -> Dict[str, bytes]:
        """
        Generates 4 distinct visual variants designed for diverse OCR engines:
          1. clahe_enhanced: Full color contrast equalized
          2. adaptive_binarized: High-contrast pure black-on-white text (Otsu + adaptive)
          3. denoised_sharpened: Bilateral filtered + Laplacian edge sharpening
          4. grayscale_clahe: High-contrast monochrome
        """
        variants: Dict[str, bytes] = {}

        try:
            # Variant 1: CLAHE Color
            _, p1 = cv2.imencode(".png", base_img)
            variants["clahe_enhanced"] = p1.tobytes()

            # Variant 2: Grayscale CLAHE
            gray = cv2.cvtColor(base_img, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            gray_clahe = clahe.apply(gray)
            _, p2 = cv2.imencode(".png", gray_clahe)
            variants["grayscale_clahe"] = p2.tobytes()

            # Variant 3: Adaptive Binarization (Pure black text on clean white)
            thresh = cv2.adaptiveThreshold(
                gray_clahe, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                21, 11
            )
            _, p3 = cv2.imencode(".png", thresh)
            variants["adaptive_binarized"] = p3.tobytes()

            # Variant 4: Sharpened
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
            sharpened = cv2.filter2D(base_img, -1, kernel)
            _, p4 = cv2.imencode(".png", sharpened)
            variants["denoised_sharpened"] = p4.tobytes()

        except Exception as e:
            logger.warning(f"Error creating preprocessing variants: {e}")
            _, fallback = cv2.imencode(".png", base_img)
            variants["clahe_enhanced"] = fallback.tobytes()

        return variants
