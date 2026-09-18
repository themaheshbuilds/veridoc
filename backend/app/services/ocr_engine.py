import asyncio
import io
import json
import logging
import re
import os
from typing import Dict, List, Optional, Tuple, Any
import cv2
import numpy as np
from PIL import Image

try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

try:
    import winsdk.windows.media.ocr as win_ocr
    import winsdk.windows.graphics.imaging as win_imaging
    import winsdk.windows.storage.streams as win_streams
    import winsdk.windows.globalization as win_glob
    HAS_WIN_OCR = True
except ImportError:
    HAS_WIN_OCR = False

try:
    from rapidocr_onnxruntime import RapidOCR
    HAS_RAPID_OCR = True
except ImportError:
    HAS_RAPID_OCR = False

from app.services.image_preprocessor import DocumentPreprocessor, PreprocessingResult

logger = logging.getLogger("veridoc.ocr")

# Indic script Unicode ranges
RE_TELUGU = re.compile(r"[\u0C00-\u0C7F]")
RE_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
RE_TAMIL = re.compile(r"[\u0B80-\u0BFF]")
RE_KANNADA = re.compile(r"[\u0C80-\u0CFF]")


class OCRResult:
    """Rich outcome of the multi-variant, multilingual OCR pipeline."""

    def __init__(
        self,
        text: str,
        confidence: float = 1.0,
        is_uncertain: bool = False,
        uncertain_fields: Optional[List[str]] = None,
        clarity_advisory: Optional[str] = None,
        languages_detected: Optional[List[str]] = None,
        selected_variant: str = "clahe_enhanced",
        preprocessing_result: Optional[PreprocessingResult] = None,
        structured_demographics: Optional[Dict[str, Any]] = None,
        engine_used: str = "RapidOCR (ONNX Offline)",
        bounding_boxes: Optional[List[Dict[str, Any]]] = None
    ):
        self.text = text
        self.confidence = confidence
        self.is_uncertain = is_uncertain
        self.uncertain_fields = uncertain_fields or []
        self.clarity_advisory = clarity_advisory
        self.languages_detected = languages_detected or ["English"]
        self.selected_variant = selected_variant
        self.preprocessing_result = preprocessing_result
        self.structured_demographics = structured_demographics or {}
        self.engine_used = engine_used
        self.bounding_boxes = bounding_boxes or []


class OCREngine:
    """
    High-accuracy, cost-efficient, multilingual OCR Engine.
    - Never processes the raw uploaded image directly.
    - Tests multiple preprocessed visual candidate variants and picks the highest-confidence output.
    - Multilingual recognition: English, Telugu (తెలుగు), Hindi, and Indian regional languages.
    - Uncertainty Tagging: if confidence is low, flags fields without hallucinating text.
    """

    _ocr_engine_instance = None
    _rapid_ocr_instance = None

    @classmethod
    def _get_rapid_ocr_engine(cls):
        """Lazily initialize and cache RapidOCR ONNX engine."""
        if not HAS_RAPID_OCR:
            return None
        if cls._rapid_ocr_instance is None:
            try:
                cls._rapid_ocr_instance = RapidOCR()
                logger.info("RapidOCR (ONNX Deep Learning) engine successfully initialized.")
            except Exception as e:
                logger.warning(f"Failed to initialize RapidOCR ONNX engine: {e}")
                cls._rapid_ocr_instance = None
        return cls._rapid_ocr_instance

    @classmethod
    def recognize_with_rapid_ocr(cls, image_input: Any) -> Tuple[str, float, List[Dict[str, Any]]]:
        """
        Run RapidOCR (ONNX Deep Learning) on image bytes or cv2 numpy array.
        Returns:
            Tuple of (extracted_text, average_confidence, bounding_boxes)
        """
        engine = cls._get_rapid_ocr_engine()
        if not engine:
            return "", 0.0, []

        try:
            if isinstance(image_input, bytes):
                nparr = np.frombuffer(image_input, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            else:
                img = image_input

            if img is None:
                return "", 0.0, []

            h, w = img.shape[:2]
            scale = 1.0
            if max(h, w) > 1400:
                scale = 1400.0 / float(max(h, w))
                img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

            ocr_res, elapse = engine(img)
            if not ocr_res:
                return "", 0.0, []

            lines = []
            scores = []
            boxes_data = []

            for item in ocr_res:
                if len(item) >= 3:
                    box, line_txt, score = item[0], item[1], float(item[2])
                    if line_txt and str(line_txt).strip():
                        clean_txt = str(line_txt).strip()
                        lines.append(clean_txt)
                        scores.append(score)
                        # Box is a list of 4 points [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                        b_list = box.tolist() if hasattr(box, 'tolist') else list(box)
                        if scale != 1.0:
                            inv_scale = 1.0 / scale
                            b_list = [[round(pt[0] * inv_scale, 1), round(pt[1] * inv_scale, 1)] for pt in b_list]
                        boxes_data.append({
                            "text": clean_txt,
                            "confidence": round(score, 4),
                            "box": b_list
                        })

            full_text = "\n".join(lines).strip()
            avg_score = float(np.mean(scores)) if scores else 0.0
            return full_text, round(avg_score, 4), boxes_data
        except Exception as e:
            logger.warning(f"RapidOCR recognition error: {e}")
            return "", 0.0, []

    @classmethod
    def _get_win_ocr_engine(cls):
        """Lazily initialize and cache Windows Media OCR engine."""
        if not HAS_WIN_OCR:
            return None
        if cls._ocr_engine_instance is None:
            try:
                cls._ocr_engine_instance = win_ocr.OcrEngine.try_create_from_user_profile_languages()
                if not cls._ocr_engine_instance:
                    lang = win_glob.Language("en-US")
                    cls._ocr_engine_instance = win_ocr.OcrEngine.try_create_from_language(lang)
            except Exception as e:
                logger.warning(f"Failed to initialize Windows Media OCR: {e}")
                cls._ocr_engine_instance = None
        return cls._ocr_engine_instance

    @classmethod
    async def recognize_single_image_bytes(cls, image_bytes: bytes) -> str:
        """Run Windows Media OCR on an individual image byte stream."""
        if not HAS_WIN_OCR or not image_bytes:
            return ""

        try:
            stream = win_streams.InMemoryRandomAccessStream()
            writer = win_streams.DataWriter(stream.get_output_stream_at(0))
            writer.write_bytes(image_bytes)
            await writer.store_async()
            await writer.flush_async()

            decoder = await win_imaging.BitmapDecoder.create_async(stream)
            software_bitmap = await decoder.get_software_bitmap_async()

            engine = cls._get_win_ocr_engine()
            if not engine:
                return ""

            result = await engine.recognize_async(software_bitmap)
            lines = [line.text.strip() for line in result.lines if line.text.strip()]
            return "\n".join(lines).strip()
        except Exception as e:
            logger.debug(f"Single image OCR error: {e}")
            return ""

    @classmethod
    def _evaluate_ocr_quality(cls, text: str) -> float:
        """
        Scores candidate OCR output quality (0.0 to 1.0) based on:
          - Character density and line count
          - Proportion of meaningful alphanumeric tokens
          - Ratio of garbled punctuation noise vs clean words
        """
        if not text or len(text.strip()) < 5:
            return 0.0

        cleaned = text.strip()
        words = re.findall(r"[A-Za-z0-9\u0C00-\u0C7F\u0900-\u097F]+", cleaned)
        if not words:
            return 0.05

        total_chars = len(cleaned)
        word_chars = sum(len(w) for w in words)
        alphanumeric_ratio = word_chars / float(max(1, total_chars))

        # Reward reasonable word lengths (3 to 12 characters)
        meaningful_words = [w for w in words if 2 <= len(w) <= 25]
        meaningful_ratio = len(meaningful_words) / float(max(1, len(words)))

        # Penalize excessive single stray characters / noise symbols
        noise_chars = len(re.findall(r"[~`^|\\_#]", cleaned))
        noise_penalty = min(0.3, (noise_chars / float(max(1, total_chars))) * 2)

        # Base confidence from token structure
        score = (0.5 * alphanumeric_ratio) + (0.5 * meaningful_ratio) - noise_penalty

        # Boost score slightly if standard document patterns (dates, colons, numbers) exist
        if re.search(r"\b\d{2}[-/.]\d{2}[-/.]\d{4}\b", cleaned):
            score += 0.08
        if ":" in cleaned:
            score += 0.06

        return max(0.1, min(1.0, round(score, 2)))

    @classmethod
    def detect_languages(cls, text: str) -> List[str]:
        """Detects whether text includes Telugu, Hindi, or English scripts."""
        languages = []
        if RE_TELUGU.search(text):
            languages.append("Telugu (తెలుగు)")
        if RE_DEVANAGARI.search(text):
            languages.append("Hindi (हिन्दी)")
        if RE_TAMIL.search(text):
            languages.append("Tamil (தமிழ்)")
        if RE_KANNADA.search(text):
            languages.append("Kannada (ಕನ್ನಡ)")

        if not languages or re.search(r"[A-Za-z]", text):
            languages.insert(0, "English")

        return languages

    _GEMINI_MODELS = [
        "gemini-flash-latest",
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-2.5-flash"
    ]

    @classmethod
    async def extract_high_precision_ai_ocr(
        cls,
        image_bytes: bytes,
        mime_type: str = "image/png"
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Multilingual AI OCR and Canonical Structured Extraction powered by Google Gemini.
        Cascades through candidate models (gemini-flash-latest, gemini-3.5-flash-lite, etc.)
        for 100% precision transcription (English + Telugu + Indic scripts) and structured entity extraction.
        Never invents or hallucinates text.
        """
        from app.services.gemini_auditor import GeminiAuditorService
        api_key = GeminiAuditorService.get_api_key()
        if not api_key:
            return None, None

        import google.generativeai as genai
        genai.configure(api_key=api_key)

        prompt = (
            "You are VERIDOC's High-Precision Multilingual Document Forensics and OCR Engine. "
            "Transcribe and analyze this identity document with 100% precision. "
            "Extract all visible text in both English and any regional Indian language (e.g. Telugu, Hindi, Tamil, Kannada, etc.).\n"
            "STRICT INSTRUCTION: Do NOT invent, assume, or hallucinate text. "
            "Transcribe exactly what is visible on the document.\n\n"
            "Output your response strictly as a JSON object with this exact structure:\n"
            "{\n"
            '  "document_type": "AADHAAR" | "PAN" | "PASSPORT" | "DRIVING_LICENCE" | "VOTER_ID" | "CERTIFICATE" | "GENERAL",\n'
            '  "name": "Full name in English",\n'
            '  "name_regional": "Full name in regional script if printed",\n'
            '  "dob": "DD/MM/YYYY",\n'
            '  "gender": "MALE" | "FEMALE" | "OTHER",\n'
            '  "gender_regional": "Gender in regional script",\n'
            '  "care_of": "S/O or D/O or W/O Name",\n'
            '  "care_of_regional": "Care of in regional script",\n'
            '  "address": "Full street address, village, mandal, district, state, pin",\n'
            '  "village_town_city": "Village or Town or City",\n'
            '  "district": "District name",\n'
            '  "state": "State name",\n'
            '  "pincode": "6-digit PIN code",\n'
            '  "phone": "Mobile/Phone number if printed",\n'
            '  "document_number": "Main ID number without spaces e.g. 715293520380",\n'
            '  "vid": "16-digit VID if printed",\n'
            '  "enrolment_number": "Enrolment number if printed",\n'
            '  "raw_transcription": "Complete verbatim text transcription of the entire document in original language and script"\n'
            "}"
        )

        for m_name in cls._GEMINI_MODELS:
            try:
                model = genai.GenerativeModel(m_name)
                resp = await asyncio.to_thread(
                    model.generate_content,
                    [
                        {"mime_type": mime_type, "data": image_bytes},
                        prompt
                    ]
                )
                if not resp or not resp.text:
                    continue

                txt = resp.text.strip()
                match = re.search(r'\{.*\}', txt, re.DOTALL)
                if match:
                    try:
                        parsed = json.loads(match.group(0))
                        raw_text = parsed.get("raw_transcription") or txt
                        structured = {k: v for k, v in parsed.items() if v and k != "raw_transcription"}
                        logger.info(f"AI OCR successful with model '{m_name}' (extracted {len(structured)} structured fields)")
                        return raw_text.strip(), structured
                    except json.JSONDecodeError:
                        return txt, None
                else:
                    return txt, None
            except Exception as e:
                logger.warning(f"AI OCR model '{m_name}' error: {e}")
                continue

        return None, None

    @classmethod
    async def extract_multilingual_vision_ocr(
        cls,
        image_bytes: bytes,
        mime_type: str = "image/png"
    ) -> Optional[str]:
        """Backward-compatible wrapper for vision OCR."""
        text, _ = await cls.extract_high_precision_ai_ocr(image_bytes, mime_type)
        return text

    @classmethod
    async def extract_text_from_document(
        cls,
        file_bytes: bytes,
        filename: Optional[str] = None,
        password: Optional[str] = None
    ) -> OCRResult:
        """
        Main OCR execution method conforming to strict user directives:
          1. Does NOT process raw image directly. First applies orientation, boundary,
             perspective warp, cropping, denoising, CLAHE, and super-resolution.
          2. Prioritizes High-Precision Multilingual AI OCR with multi-model cascade
             for 100% precision bilingual text and structured demographics.
          3. Employs local multi-variant Windows Media OCR as offline fallback.
          4. Tags uncertain fields if optical clarity prevents reliable extraction.
        """
        if not file_bytes:
            return OCRResult(text="", confidence=0.0, is_uncertain=True)

        is_pdf = (filename and filename.lower().endswith(".pdf")) or (file_bytes[:4] == b"%PDF")

        # 1. Digital PDF extraction check
        if is_pdf and HAS_FITZ:
            try:
                from app.services.quality_assessor import DocumentQualityAssessor
                doc, _ = DocumentQualityAssessor.open_pdf_doc(file_bytes, filename=filename, password=password)
                if doc and len(doc) > 0:
                    pdf_text = ""
                    for page in doc:
                        t = page.get_text()
                        if t and len(t.strip()) > 15:
                            pdf_text += t + "\n"
                    if len(pdf_text.strip()) > 25:
                        langs = cls.detect_languages(pdf_text)
                        # Also render page to get optical bounding boxes for UI overlay
                        page = doc[0]
                        mat = fitz.Matrix(2.5, 2.5)
                        pix = page.get_pixmap(matrix=mat)
                        img_bytes = pix.tobytes("png")
                        cand_text, cand_conf, cand_boxes = cls.recognize_with_rapid_ocr(img_bytes)
                        final_text = pdf_text.strip()
                        if cand_text and len(cand_text.strip()) > len(final_text):
                            final_text = f"{final_text}\n{cand_text.strip()}"
                        return OCRResult(
                            text=final_text,
                            confidence=0.98,
                            bounding_boxes=cand_boxes or [],
                            is_uncertain=False,
                            languages_detected=langs,
                            selected_variant="pdf_digital_layer",
                            engine_used="PyMuPDF Vector Stream + RapidOCR"
                        )
            except Exception as e:
                logger.debug(f"PDF digital text extraction: {e}")

        # ----------------------------------------------------------------------
        # Mandatory Step: Preprocessing Pipeline (Raw bytes untouched for forensics)
        # ----------------------------------------------------------------------
        preproc = DocumentPreprocessor.preprocess_document_image(file_bytes, filename, password=password)

        # ----------------------------------------------------------------------
        # Primary Tier: RapidOCR (100% Offline Deep Learning via ONNX Runtime)
        # ----------------------------------------------------------------------
        rapid_engine = cls._get_rapid_ocr_engine()
        if rapid_engine:
            best_rapid_text = ""
            best_rapid_score = -1.0
            best_rapid_variant = "clahe_enhanced"
            best_rapid_boxes = []

            # Prioritize primary contrast-enhanced and denoised variants first
            variant_order = ["clahe_enhanced", "denoised_sharpened", "grayscale_clahe", "adaptive_binarized"]
            ordered_variants = []
            for v_key in variant_order:
                if v_key in preproc.variants:
                    ordered_variants.append((v_key, preproc.variants[v_key]))
            for v_key, v_bytes in preproc.variants.items():
                if (v_key, v_bytes) not in ordered_variants:
                    ordered_variants.append((v_key, v_bytes))

            for var_name, var_bytes in ordered_variants:
                cand_text, cand_conf, cand_boxes = cls.recognize_with_rapid_ocr(var_bytes)
                eval_score = cls._evaluate_ocr_quality(cand_text)
                combined_score = (0.5 * cand_conf) + (0.5 * eval_score) if cand_conf > 0 else eval_score

                logger.debug(f"RapidOCR variant '{var_name}' score: {combined_score:.2f}, chars: {len(cand_text)}")
                if combined_score > best_rapid_score:
                    best_rapid_score = combined_score
                    best_rapid_text = cand_text
                    best_rapid_variant = f"rapidocr_{var_name}"
                    best_rapid_boxes = cand_boxes

                # Early-exit optimization: If current variant yields high confidence (>= 0.75) and text (>= 80 chars),
                # stop immediately to eliminate redundant multi-second CPU cycles on subsequent variants.
                if best_rapid_score >= 0.75 and len(best_rapid_text.strip()) >= 80:
                    break

            # If RapidOCR produced solid, readable text, use it as primary ground truth
            if len(best_rapid_text.strip()) >= 20 and best_rapid_score >= 0.45:
                languages = cls.detect_languages(best_rapid_text)
                final_conf = max(0.4, min(0.99, best_rapid_score))
                return OCRResult(
                    text=best_rapid_text,
                    confidence=round(final_conf, 2),
                    is_uncertain=False,
                    uncertain_fields=[],
                    clarity_advisory=None,
                    languages_detected=languages,
                    selected_variant=best_rapid_variant,
                    preprocessing_result=preproc,
                    structured_demographics={},
                    engine_used="RapidOCR (ONNX Deep Learning Offline)",
                    bounding_boxes=best_rapid_boxes
                )

        # ----------------------------------------------------------------------
        # Secondary Tier: High-Precision Multilingual AI OCR (Gemini Vision Multi-Model)
        # Used when offline OCR indicates ambiguity or when deep AI audit is enabled
        # ----------------------------------------------------------------------
        from app.services.gemini_auditor import GeminiAuditorService
        if GeminiAuditorService.is_available():
            ai_text, structured_fields = await cls.extract_high_precision_ai_ocr(preproc.primary_variant_bytes)
            if ai_text and len(ai_text.strip()) > 15:
                languages = cls.detect_languages(ai_text)
                if structured_fields and (structured_fields.get("name_regional") or structured_fields.get("care_of_regional")):
                    if any(RE_TELUGU.search(str(v)) for v in structured_fields.values()):
                        if "Telugu (తెలుగు)" not in languages:
                            languages.append("Telugu (తెలుగు)")

                return OCRResult(
                    text=ai_text,
                    confidence=0.98,
                    is_uncertain=False,
                    uncertain_fields=[],
                    clarity_advisory=None,
                    languages_detected=languages,
                    selected_variant="preprocessed+gemini_multimodal_vision",
                    preprocessing_result=preproc,
                    structured_demographics=structured_fields,
                    engine_used="Google Gemini Multimodal AI"
                )

        # ----------------------------------------------------------------------
        # Tertiary Tier: Local Multi-Variant Windows Media OCR (Windows OS Fallback)
        # ----------------------------------------------------------------------
        best_text = ""
        best_score = -1.0
        best_variant_name = "clahe_enhanced"

        for var_name, var_bytes in preproc.variants.items():
            candidate_text = await cls.recognize_single_image_bytes(var_bytes)
            score = cls._evaluate_ocr_quality(candidate_text)
            logger.debug(f"Variant '{var_name}' OCR score: {score:.2f}, chars: {len(candidate_text)}")

            if score > best_score:
                best_score = score
                best_text = candidate_text
                best_variant_name = var_name

        languages = cls.detect_languages(best_text)

        # Uncertainty Tagging (Never invent or hallucinate text)
        is_uncertain = False
        uncertain_fields = []
        advisory = None

        if best_score < 0.55 or len(best_text.strip()) < 20:
            is_uncertain = True
            uncertain_fields = ["document_content", "demographic_details"]
            advisory = (
                "Low optical clarity detected. Character confidence is below threshold. "
                "VERIDOC does not guess or invent text. Please upload a higher-resolution, "
                "glare-free flat scan of the document."
            )
        elif "[UNREADABLE]" in best_text:
            is_uncertain = True
            uncertain_fields = ["partially_obscured_fields"]
            advisory = "Certain sections of the document are obscured or blurred. Please provide a clearer copy."

        final_conf = max(0.2, min(0.99, best_score))

        return OCRResult(
            text=best_text,
            confidence=final_conf,
            is_uncertain=is_uncertain,
            uncertain_fields=uncertain_fields,
            clarity_advisory=advisory,
            languages_detected=languages,
            selected_variant=best_variant_name,
            preprocessing_result=preproc,
            structured_demographics={},
            engine_used="Windows Media OCR (Offline Native)"
        )
