"""
quality_assessor.py — Layer 1: Optical Quality Triage Gate
===========================================================
Implements the Laplacian Variance blur gate (σ² < 100 → reject),
CLAHE contrast enhancement, and 4-point contour perspective deskewing.
"""
import io
import math
from typing import List, Tuple, Optional
import numpy as np
import cv2
from PIL import Image

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

from app.schemas.verification import DocumentQualityReport


class DocumentQualityAssessor:
    """Real optical document quality assessment using OpenCV and NumPy."""

    # Layer 1 spec: σ² < 100 → IMAGE_BLURRY_RETAKE_REQUIRED
    BLUR_THRESHOLD_POOR   = 100.0   # Laplacian variance below this → POOR / reject
    BLUR_THRESHOLD_STRICT = 200.0   # Below this → ACCEPTABLE (warn but continue)
    MIN_DIMENSION_PX      = 500
    CRITICAL_MIN_DIMENSION_PX = 350
    MIN_CONTRAST          = 30.0
    MIN_BRIGHTNESS        = 45.0
    MAX_BRIGHTNESS        = 225.0

    # CLAHE parameters
    CLAHE_CLIP_LIMIT = 2.0
    CLAHE_TILE_GRID  = (8, 8)

    @classmethod
    def load_image_cv2(
        cls,
        file_bytes: bytes,
        filename: Optional[str] = None
    ) -> Tuple[Optional[np.ndarray], Optional[str]]:
        """Load image bytes (or first page of PDF) into an OpenCV BGR numpy array."""
        if not file_bytes:
            return None, "Empty file bytes provided."

        is_pdf = False
        if filename and filename.lower().endswith(".pdf"):
            is_pdf = True
        elif file_bytes[:4] == b"%PDF":
            is_pdf = True

        if is_pdf:
            if not HAS_FITZ:
                return None, "PyMuPDF (fitz) is not installed for PDF rendering."
            try:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                if len(doc) == 0:
                    return None, "PDF document contains 0 pages."
                page = doc[0]
                # Render at 2× resolution (144 DPI) for high-accuracy optical analysis
                zoom = 2.0
                mat  = fitz.Matrix(zoom, zoom)
                pix  = page.get_pixmap(matrix=mat)
                img  = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                return cv_img, None
            except Exception as e:
                return None, f"Failed to render PDF page: {str(e)}"

        # Standard image (JPEG, PNG, WEBP, TIFF)
        try:
            nparr  = np.frombuffer(file_bytes, np.uint8)
            cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if cv_img is None:
                pil_img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
                cv_img  = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            return cv_img, None
        except Exception as e:
            return None, f"Unable to decode image bytes: {str(e)}"

    # ─────────────────────────────────────────────────────────────────────────
    # CLAHE contrast enhancement
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def apply_clahe(cls, cv_img: np.ndarray) -> np.ndarray:
        """
        Apply CLAHE (Contrast-Limited Adaptive Histogram Equalization) to
        improve local contrast on low-visibility or glare-affected documents.
        Operates channel-wise on LAB colour space to avoid hue distortion.
        """
        try:
            lab   = cv2.cvtColor(cv_img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(
                clipLimit=cls.CLAHE_CLIP_LIMIT,
                tileGridSize=cls.CLAHE_TILE_GRID
            )
            l_enhanced = clahe.apply(l)
            enhanced_lab = cv2.merge([l_enhanced, a, b])
            return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        except Exception:
            return cv_img  # Return original on failure

    # ─────────────────────────────────────────────────────────────────────────
    # 4-point contour perspective deskewing
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def deskew_perspective(cls, cv_img: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Detect the largest 4-point quadrilateral contour (the document boundary)
        and apply a perspective warp to straighten it.

        Returns:
            (corrected_image, was_corrected: bool)
        """
        try:
            h, w = cv_img.shape[:2]
            gray    = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edged   = cv2.Canny(blurred, 50, 150)

            # Dilate to close gaps in document edge
            kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            dilated = cv2.dilate(edged, kernel, iterations=2)

            contours, _ = cv2.findContours(
                dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            if not contours:
                return cv_img, False

            # Sort by area descending; find the largest quad
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            doc_quad = None
            for cnt in contours[:5]:
                peri   = cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
                area   = cv2.contourArea(approx)
                # Require a reasonable 4-sided polygon covering > 20% of image
                if len(approx) == 4 and area > (0.20 * w * h):
                    doc_quad = approx
                    break

            if doc_quad is None:
                return cv_img, False

            # Order corners: top-left, top-right, bottom-right, bottom-left
            pts = doc_quad.reshape(4, 2).astype("float32")
            s   = pts.sum(axis=1)
            diff = np.diff(pts, axis=1)
            ordered = np.zeros((4, 2), dtype="float32")
            ordered[0] = pts[np.argmin(s)]     # top-left
            ordered[2] = pts[np.argmax(s)]     # bottom-right
            ordered[1] = pts[np.argmin(diff)]  # top-right
            ordered[3] = pts[np.argmax(diff)]  # bottom-left

            # Compute destination dimensions
            tl, tr, br, bl = ordered
            wA = np.linalg.norm(br - bl)
            wB = np.linalg.norm(tr - tl)
            hA = np.linalg.norm(tr - br)
            hB = np.linalg.norm(tl - bl)
            dst_w = max(int(wA), int(wB))
            dst_h = max(int(hA), int(hB))

            if dst_w < 200 or dst_h < 200:
                return cv_img, False  # Too small to warp

            dst = np.array([
                [0, 0], [dst_w - 1, 0],
                [dst_w - 1, dst_h - 1], [0, dst_h - 1]
            ], dtype="float32")

            M       = cv2.getPerspectiveTransform(ordered, dst)
            warped  = cv2.warpPerspective(cv_img, M, (dst_w, dst_h))
            return warped, True

        except Exception:
            return cv_img, False

    # ─────────────────────────────────────────────────────────────────────────
    # Main quality assessment
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def assess_quality(cls, cv_img: np.ndarray) -> DocumentQualityReport:
        """
        Run full optical quality checks:
          1. Laplacian Variance blur gate (σ² < 100 → reject)
          2. Brightness / contrast histogram
          3. Skew estimation (Hough lines)
          4. CLAHE + deskew applied internally for downstream pipeline
        """
        if cv_img is None:
            return DocumentQualityReport(
                quality_verdict="POOR",
                blur_score=0.0,
                is_blurry=True,
                brightness=0.0,
                contrast=0.0,
                width=0,
                height=0,
                skew_deg=0.0,
                issues=["IMAGE_BLURRY_RETAKE_REQUIRED — Image data could not be parsed."],
                remediation_advice=(
                    "IMAGE_BLURRY_RETAKE_REQUIRED: Image data could not be loaded. "
                    "Please upload a valid JPEG, PNG, TIFF, or PDF document."
                )
            )

        height, width = cv_img.shape[:2]
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

        # 1. Blur Detection — Laplacian Variance (σ²)
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        is_blurry     = laplacian_var < cls.BLUR_THRESHOLD_STRICT

        # 2. Brightness & Contrast
        brightness = float(np.mean(gray))
        contrast   = float(np.std(gray))

        # 3. Skew Estimation
        skew_deg = cls._estimate_skew_angle(gray)

        # 4. Synthesize defects
        issues:  List[str] = []
        is_poor: bool      = False

        if min(width, height) < cls.CRITICAL_MIN_DIMENSION_PX:
            issues.append(
                f"Critical: Image resolution is too low ({width}×{height}px; "
                f"minimum {cls.CRITICAL_MIN_DIMENSION_PX}px required)."
            )
            is_poor = True
        elif min(width, height) < cls.MIN_DIMENSION_PX:
            issues.append(
                f"Sub-optimal resolution ({width}×{height}px; recommended ≥ {cls.MIN_DIMENSION_PX}px)."
            )

        # BSA Spec Layer 1: σ² < 100 → IMAGE_BLURRY_RETAKE_REQUIRED
        if laplacian_var < cls.BLUR_THRESHOLD_POOR:
            issues.append(
                f"IMAGE_BLURRY_RETAKE_REQUIRED: Severe blur detected "
                f"(σ²={laplacian_var:.1f} < 100 threshold). Text is unreadable."
            )
            is_poor = True
        elif is_blurry:
            issues.append(
                f"Moderate blur (σ²={laplacian_var:.1f}; recommended ≥ {cls.BLUR_THRESHOLD_STRICT:.0f}). "
                "Verification will proceed but accuracy may be reduced."
            )

        if brightness < cls.MIN_BRIGHTNESS:
            issues.append(
                f"Underexposed: Image too dark (brightness={brightness:.1f}/255)."
            )
            if brightness < 25.0:
                is_poor = True
        elif brightness > 250.0 and laplacian_var < cls.BLUR_THRESHOLD_POOR:
            issues.append(
                f"Overexposed: Severe optical glare washing out text "
                f"(brightness={brightness:.1f}/255)."
            )
            is_poor = True

        if contrast < 15.0 and laplacian_var < cls.BLUR_THRESHOLD_POOR:
            issues.append(
                f"Low contrast ({contrast:.1f}); text lacks definition against background."
            )
            is_poor = True

        if abs(skew_deg) > 15.0:
            issues.append(
                f"High geometric skew ({skew_deg:.1f}°). "
                "CLAHE + 4-point deskew will be auto-applied before OCR."
            )

        # Verdict
        if is_poor:
            verdict = "POOR"
            advice  = (
                "IMAGE_BLURRY_RETAKE_REQUIRED — Laplacian variance (σ²) below mandatory "
                "threshold of 100. Forensic analysis cannot proceed. "
                "Please retake the document photograph with adequate lighting and focus."
            )
        elif len(issues) > 0:
            verdict = "ACCEPTABLE"
            advice  = (
                "Document quality is acceptable but suboptimal. "
                "CLAHE contrast enhancement has been applied automatically. "
                "Better results with improved lighting, focus, and alignment."
            )
        else:
            verdict = "GOOD"
            advice  = (
                "Optical clarity, illumination, and resolution meet "
                "statutory verification standards. σ² threshold passed."
            )

        return DocumentQualityReport(
            quality_verdict=verdict,
            blur_score=round(laplacian_var, 2),
            is_blurry=is_blurry,
            brightness=round(brightness, 2),
            contrast=round(contrast, 2),
            width=width,
            height=height,
            skew_deg=round(skew_deg, 2),
            issues=issues,
            remediation_advice=advice
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Skew estimation
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def _estimate_skew_angle(cls, gray: np.ndarray) -> float:
        """Estimate document skew angle using Hough line transform."""
        try:
            h, w  = gray.shape
            scale = 800.0 / max(h, w)
            small = cv2.resize(gray, (int(w * scale), int(h * scale))) if scale < 1.0 else gray

            edges = cv2.Canny(small, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(
                edges, 1, np.pi / 180,
                threshold=100, minLineLength=80, maxLineGap=10
            )
            if lines is None or len(lines) == 0:
                return 0.0

            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
                if abs(angle) < 45.0:
                    angles.append(angle)

            return float(np.median(angles)) if angles else 0.0
        except Exception:
            return 0.0
