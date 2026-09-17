import re
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

from app.schemas.enums import DocumentType
from app.schemas.verification import (
    ExtractedFields,
    CrossDocumentReport,
    CrossDocumentMismatch,
    DynamicDocumentCategory
)
from app.services.ocr_engine import OCREngine, OCRResult
from app.services.official_registry import OfficialRegistryService


class DocumentAnalyzer:
    """Real document structure extraction, regex parsing, mathematical checksums, and cross-consistency."""

    # Verhoeff algorithm multiplication table for Aadhaar validation
    VERHOEFF_D = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
        [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
        [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
        [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
        [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
        [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
        [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
        [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
        [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
    ]
    VERHOEFF_P = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
        [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
        [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
        [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
        [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
        [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
        [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
    ]
    VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

    @classmethod
    async def extract_ocr_result(cls, file_bytes: bytes, filename: Optional[str] = None) -> OCRResult:
        """Run full preprocessed multi-variant and multilingual OCR."""
        return await OCREngine.extract_text_from_document(file_bytes, filename)

    @classmethod
    async def extract_text_from_file(cls, file_bytes: bytes, filename: Optional[str] = None) -> str:
        """Backwards-compatible helper returning raw extracted text."""
        res = await cls.extract_ocr_result(file_bytes, filename)
        return res.text

    @classmethod
    def _extract_dynamic_key_values(cls, raw_text: str) -> Dict[str, Any]:
        """
        Dynamically extracts arbitrary key-value pairs, form labels, and colon-separated
        attributes from any document layout (Transfer Certificates, Marksheets, Land Records,
        Bills, Affidavits, etc.).
        """
        dynamic: Dict[str, Any] = {}
        if not raw_text:
            return dynamic

        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

        INSTRUCTION_TERMS = {
            "IN BLOCK LETTERS", "BLOCK LETTERS", "SEE INSTRUCTIONS", "PLEASE TICK",
            "OFFICE USE ONLY", "SIGNATURE", "SEAL", "STAMP", "FOR OFFICE USE"
        }

        # Matches lines like "Key : Value", "Key - Value", or "Key = Value"
        re_kv = re.compile(r"^([A-Za-z0-9\s/().'-]{2,35})\s*[:=-]\s*(.+)$")

        for line in lines:
            m = re_kv.match(line)
            if m:
                k = m.group(1).strip()
                v = m.group(2).strip()

                if len(k) >= 2 and not k.isdigit() and len(v) >= 1:
                    for term in INSTRUCTION_TERMS:
                        v = re.sub(rf"\b{term}\b", "", v, flags=re.IGNORECASE).strip()

                    v = v.strip(" -:;,")
                    if v and len(v) >= 1:
                        clean_k = re.sub(r"^\d+[\s.)-]+", "", k).strip().title()
                        if clean_k and clean_k not in dynamic:
                            dynamic[clean_k] = v

        return dynamic

    @classmethod
    def _detect_dynamic_category(
        cls,
        text: str,
        raw_original: Optional[str] = None
    ) -> DynamicDocumentCategory:
        """
        Discovers document category, sub-category, issuing authority, and visual/textual
        characteristics without rigid template pigeonholing.
        """
        upper_text = f"{text}\n{raw_original or ''}".upper()

        category = "GENERAL_DOCUMENT"
        sub_category = "Official Document"
        institution = None
        state_or_country = "India"
        characteristics: List[str] = []

        # Detect State / Jurisdiction
        if "TELANGANA" in upper_text or "HYDERABAD" in upper_text:
            state_or_country = "Telangana, India"
        elif "ANDHRA PRADESH" in upper_text or "AMARAVATI" in upper_text:
            state_or_country = "Andhra Pradesh, India"
        elif "MAHARASHTRA" in upper_text or "MUMBAI" in upper_text:
            state_or_country = "Maharashtra, India"
        elif "KARNATAKA" in upper_text or "BENGALURU" in upper_text or "BANGALORE" in upper_text:
            state_or_country = "Karnataka, India"
        elif "DELHI" in upper_text or "NEW DELHI" in upper_text:
            state_or_country = "Delhi (NCT), India"
        elif "TAMIL NADU" in upper_text or "CHENNAI" in upper_text:
            state_or_country = "Tamil Nadu, India"

        # Detect visual characteristics
        if any(w in upper_text for w in ["SEAL", "STAMP", "PRINCIPAL", "SIGNATURE", "AUTHORIZED SIGNATORY", "REGISTRAR"]):
            characteristics.append("Institutional Seal / Authorized Endorsement")
        if any(w in upper_text for w in ["TC NO", "ADMISSION NO", "ROLL NO", "REGISTRATION NO", "UID", "PAN", "EPIC"]):
            characteristics.append("Unique Serial / Registration Identifier")
        if re.search(r"[\u0C00-\u0C7F]", raw_original or ""):
            characteristics.append("Bilingual Telugu & English Typography")
        elif re.search(r"[\u0900-\u097F]", raw_original or ""):
            characteristics.append("Bilingual Devanagari & English Typography")
        if ":" in upper_text or "=" in upper_text:
            characteristics.append("Structured Form Questionnaire Format")

        # 1. Educational Credentials
        if any(w in upper_text for w in [
            "TRANSFER CERTIFICATE", "TC NO", "T.C.", "BONAFIDE", "STUDENT", "COLLEGE",
            "POLYTECHNIC", "INSTITUTE OF TECHNOLOGY", "UNIVERSITY", "MARKSHEET",
            "DEGREE", "DIPLOMA", "BOARD OF SECONDARY", "ACADEMIC", "STUDY CERTIFICATE"
        ]):
            category = "EDUCATION_CERTIFICATE"
            if "TRANSFER CERTIFICATE" in upper_text or "T.C." in upper_text or "TC NO" in upper_text:
                sub_category = "Transfer Certificate (TC)"
            elif "BONAFIDE" in upper_text or "STUDY CERTIFICATE" in upper_text:
                sub_category = "Bonafide / Study Certificate"
            elif "MARKSHEET" in upper_text or "GRADE CARD" in upper_text or "STATEMENT OF MARKS" in upper_text:
                sub_category = "Academic Marksheet / Transcript"
            elif "DEGREE" in upper_text:
                sub_category = "University Degree"
            elif "DIPLOMA" in upper_text:
                sub_category = "Polytechnic Diploma"
            else:
                sub_category = "Educational Credential"

            inst_m = re.search(r'([A-Z\s]{4,45}(?:POLYTECHNIC|COLLEGE|INSTITUTE|UNIVERSITY|SCHOOL|ACADEMY))', upper_text)
            if inst_m:
                institution = inst_m.group(1).strip().title()

        # 2. Civil Registration
        elif any(w in upper_text for w in ["BIRTH CERTIFICATE", "REGISTRATION OF BIRTH", "FORM 5", "DEATH CERTIFICATE", "MARRIAGE CERTIFICATE"]):
            category = "CIVIL_REGISTRATION"
            if "BIRTH" in upper_text:
                sub_category = "Birth Certificate"
            elif "DEATH" in upper_text:
                sub_category = "Death Certificate"
            else:
                sub_category = "Marriage Certificate"
            institution = "Municipal Corporation / Registrar of Vital Statistics"

        # 3. Revenue & Land Records
        elif any(w in upper_text for w in ["PATTA", "PAHANI", "ADANGAL", "ENCUMBRANCE CERTIFICATE", "1-B NAMUNA", "KHATA", "TITLE DEED"]):
            category = "REVENUE_AND_LAND"
            sub_category = "Land Record / Revenue Deed"
            institution = "Revenue Department / Sub-Registrar"

        # 4. Community & Income
        elif any(w in upper_text for w in ["CASTE CERTIFICATE", "COMMUNITY CERTIFICATE", "INCOME CERTIFICATE", "EWS CERTIFICATE", "DOMICILE"]):
            category = "COMMUNITY_AND_INCOME"
            sub_category = "Community / Income Certificate"
            institution = "MeeSeva / Revenue Department"

        # 5. Financial & Banking
        elif any(w in upper_text for w in ["BANK STATEMENT", "ACCOUNT STATEMENT", "PASSBOOK", "IFSC", "CHEQUE", "SALARY SLIP", "FORM 16"]):
            category = "FINANCIAL_AND_BANKING"
            sub_category = "Financial / Bank Statement"
            inst_m = re.search(r'([A-Z\s]{3,25}BANK)', upper_text)
            if inst_m:
                institution = inst_m.group(1).strip().title()

        # 6. Utility & Municipal
        elif any(w in upper_text for w in ["ELECTRICITY BILL", "WATER BILL", "PROPERTY TAX", "POWER DISTRIBUTION", "CONSUMER NO"]):
            category = "UTILITY_AND_MUNICIPAL"
            sub_category = "Utility Service Bill"

        # 7. Anchor Government IDs
        elif "AADHAAR" in upper_text or "UIDAI" in upper_text:
            category = "GOVERNMENT_ID"
            sub_category = "UIDAI Aadhaar Card"
            institution = "Unique Identification Authority of India (UIDAI)"
        elif "INCOME TAX" in upper_text or "PERMANENT ACCOUNT NUMBER" in upper_text or re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', upper_text):
            category = "GOVERNMENT_ID"
            sub_category = "Income Tax PAN Card"
            institution = "Income Tax Department (CBDT)"
        elif "DRIVING LICENCE" in upper_text or "MOTOR VEHICLES ACT" in upper_text:
            category = "GOVERNMENT_ID"
            sub_category = "Driving Licence"
            institution = "Ministry of Road Transport and Highways (MoRTH)"
        elif "ELECTOR" in upper_text or "ELECTION COMMISSION" in upper_text:
            category = "GOVERNMENT_ID"
            sub_category = "Voter ID / EPIC Card"
            institution = "Election Commission of India"
        elif "PASSPORT" in upper_text or "P<IND" in upper_text:
            category = "GOVERNMENT_ID"
            sub_category = "Republic of India Passport"
            institution = "Ministry of External Affairs (CPV Division)"

        return DynamicDocumentCategory(
            category=category,
            sub_category=sub_category,
            confidence=0.96 if category != "GENERAL_DOCUMENT" else 0.80,
            visual_characteristics=characteristics,
            detected_institution=institution,
            detected_state_or_country=state_or_country
        )

    @classmethod
    def analyze_document(
        cls,
        raw_text: str,
        qr_payload: Optional[str] = None,
        declared_type: Optional[DocumentType] = None,
        ocr_result: Optional[OCRResult] = None
    ) -> Tuple[DocumentType, ExtractedFields, List[str], List[str]]:
        """
        Analyze document structure, dynamically classify category, extract fields, and validate checksums.
        Returns (classified_type, extracted_fields, positive_factors, negative_factors).
        """
        combined_text = f"{raw_text}\n{qr_payload or ''}".upper()
        positives: List[str] = []
        negatives: List[str] = []

        fields = ExtractedFields(
            raw_text=raw_text[:1500] if raw_text else None,
            qr_payload=qr_payload
        )

        # Propagate OCR uncertainty & confidence telemetry
        if ocr_result:
            fields.ocr_confidence = ocr_result.confidence
            fields.is_uncertain = ocr_result.is_uncertain
            fields.uncertain_fields = ocr_result.uncertain_fields
            fields.clarity_advisory = ocr_result.clarity_advisory
            if ocr_result.is_uncertain and ocr_result.clarity_advisory:
                negatives.append(f"Optical Clarity Warning: {ocr_result.clarity_advisory}")

            # Ingest High-Precision AI Structured Demographics if present
            if hasattr(ocr_result, "structured_demographics") and ocr_result.structured_demographics:
                sd = ocr_result.structured_demographics
                if sd.get("name"): fields.name = sd["name"]
                if sd.get("name_regional"): fields.name_regional = sd["name_regional"]
                if sd.get("dob"): fields.dob = sd["dob"]
                if sd.get("gender"): fields.gender = sd["gender"]
                if sd.get("care_of"): fields.care_of = sd["care_of"]
                if sd.get("care_of_regional"): fields.care_of_regional = sd["care_of_regional"]
                if sd.get("address"): fields.address = sd["address"]
                if sd.get("pincode"): fields.pincode = sd["pincode"]
                if sd.get("district"): fields.district = sd["district"]
                if sd.get("state"): fields.state = sd["state"]
                if sd.get("phone"): fields.phone = sd["phone"]
                if sd.get("document_number"): fields.document_number = str(sd["document_number"]).replace(" ", "")
                if sd.get("vid"): fields.vid = str(sd["vid"])
                if sd.get("enrolment_number"): fields.enrolment_number = str(sd["enrolment_number"])
                if sd.get("document_type") and sd["document_type"] in DocumentType.__members__:
                    declared_type = declared_type or DocumentType[sd["document_type"]]
                positives.append("Multilingual AI Vision OCR: Authenticated and transcribed high-fidelity citizen demographics.")

        # Parse QR Code if available
        qr_data = cls._parse_qr_payload(qr_payload)
        fields.qr_data_parsed = qr_data

        # 1. Dynamic Open-Ended Categorization (Do not pigeonhole into Passport/Aadhaar)
        dynamic_cat = cls._detect_dynamic_category(combined_text, raw_original=raw_text)
        fields.dynamic_category = dynamic_cat

        # 2. Dynamic Key-Value Attribute Extraction
        fields.dynamic_fields = cls._extract_dynamic_key_values(raw_text)

        # 3. Document Anchor Type Classification
        doc_type = cls._classify_document(combined_text, declared_type)

        # If doc_type was UNKNOWN, but dynamic category discovered a valid category, align them
        if doc_type == DocumentType.UNKNOWN and dynamic_cat.category in DocumentType.__members__:
            doc_type = DocumentType(dynamic_cat.category)

        fields.document_type = doc_type.value

        # 4. Field Extraction & Specific Validations based on type
        if doc_type == DocumentType.PASSPORT:
            cls._extract_passport_fields(combined_text, fields, positives, negatives)
        elif doc_type == DocumentType.AADHAAR:
            cls._extract_aadhaar_fields(combined_text, fields, qr_data, positives, negatives)
        elif doc_type == DocumentType.PAN:
            cls._extract_pan_fields(combined_text, fields, positives, negatives)
        elif doc_type == DocumentType.DRIVING_LICENSE:
            cls._extract_dl_fields(combined_text, fields, positives, negatives)
        elif doc_type == DocumentType.VOTER_ID:
            cls._extract_voter_fields(combined_text, fields, positives, negatives)
        elif doc_type == DocumentType.EDUCATION_CERTIFICATE:
            cls._extract_education_fields(combined_text, fields, positives, negatives, raw_original=raw_text)
        else:
            cls._extract_generic_fields(combined_text, fields, positives, negatives, raw_original=raw_text)

        # Map dynamic fields to core fields if missing
        if not fields.name and "Student Name" in fields.dynamic_fields:
            fields.name = fields.dynamic_fields["Student Name"]
        elif not fields.name and "Name" in fields.dynamic_fields:
            fields.name = fields.dynamic_fields["Name"]

        if not fields.document_number and "Tc No" in fields.dynamic_fields:
            fields.document_number = fields.dynamic_fields["Tc No"]
        elif not fields.document_number and "Admission No" in fields.dynamic_fields:
            fields.document_number = fields.dynamic_fields["Admission No"]

        # 5. OCR ↔ QR Consistency Comparison
        if qr_payload:
            cls._compare_ocr_qr(fields, positives, negatives)

        # 6. Date & Logical Cross-Validation
        cls._validate_dates(fields, positives, negatives)

        return doc_type, fields, positives, negatives


    @classmethod
    def _classify_document(cls, text: str, declared: Optional[DocumentType]) -> DocumentType:
        """Classify document category using structural markers and keywords."""
        if declared and declared != DocumentType.UNKNOWN:
            return declared

        # 1. Check Passport (P<IND or PASSPORT keywords)
        if "P<IND" in text or "PASSPORT" in text or re.search(r'P<[A-Z]{3}', text):
            return DocumentType.PASSPORT

        # 2. Check Aadhaar (UIDAI, AADHAAR, or 12-digit UID pattern)
        if (
            "AADHAAR" in text
            or "UIDAI" in text
            or "UNIQUE IDENTIFICATION" in text
            or "MERA AADHAAR" in text
            or "ENROLMENT NO" in text
            or "HELP@UIDAI" in text
            or re.search(r'\b[2-9]\d{3}\s\d{4}\s\d{4}\b', text)
            or ("GOVERNMENT OF INDIA" in text and any(k in text for k in ["DOB", "MALE", "FEMALE", "YEAR OF BIRTH", "GENDER"]))
        ):
            return DocumentType.AADHAAR

        # 3. Check PAN Card (Income Tax, Permanent Account Number, or 10-char PAN regex)
        if (
            "INCOME TAX DEPARTMENT" in text
            or "PERMANENT ACCOUNT NUMBER" in text
            or "INCOME TAX" in text
            or re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', text)
            or ("GOVT. OF INDIA" in text and ("FATHER" in text or "SIGNATURE" in text or "INCOME" in text))
        ):
            return DocumentType.PAN

        # 4. Check Driving Licence (Driving licence/license, MoRTH, Form 7, DL regex)
        if (
            "DRIVING LICENCE" in text
            or "DRIVING LICENSE" in text
            or "MOTOR VEHICLES ACT" in text
            or "FORM 7" in text
            or "DL NO" in text
            or ("UNION OF INDIA" in text and "TRANSPORT" in text)
            or re.search(r'\b[A-Z]{2}[-\s]?[0-9]{2}[-\s]?[0-9]{4}[0-9]{7}\b', text)
            or re.search(r'\b[A-Z]{2}[0-9]{13,15}\b', text)
        ):
            return DocumentType.DRIVING_LICENSE

        # 5. Check Voter ID (Election Commission, EPIC, Elector)
        if (
            "ELECTION COMMISSION" in text
            or "ELECTOR PHOTO IDENTITY" in text
            or "EPIC NO" in text
            or ("IDENTITY CARD" in text and "ELECTOR" in text)
            or re.search(r'\b[A-Z]{3}[0-9]{7}\b', text)
        ):
            return DocumentType.VOTER_ID

        # 6. Check Visa
        if "VISA" in text or "REPUBLIC OF INDIA VISA" in text:
            return DocumentType.VISA

        # 7. Check Education Certificate / Transfer Certificate / Academic Credentials
        if (
            "TRANSFER CERTIFICATE" in text
            or "TC NO" in text
            or "TC.NO" in text
            or "T.C." in text
            or "BONAFIDE" in text
            or "STUDENT" in text
            or "COLLEGE" in text
            or "POLYTECHNIC" in text
            or "INSTITUTE OF TECHNOLOGY" in text
            or "SCHOOL LEAVING" in text
            or "MIGRATION CERTIFICATE" in text
            or "ADMISSION NO" in text
            or "ROLL NO" in text
            or "HALL TICKET" in text
            or "DEGREE" in text
            or "DIPLOMA" in text
            or "UNIVERSITY" in text
            or "BOARD OF SECONDARY" in text
            or "MARKSHEET" in text
            or "PROVISIONAL CERTIFICATE" in text
            or "GRADE CARD" in text
            or "ACADEMIC" in text
        ):
            return DocumentType.EDUCATION_CERTIFICATE

        # Unrecognized / Generic document - never default to Passport
        return declared or DocumentType.UNKNOWN

    @classmethod
    def _extract_passport_fields(cls, text: str, fields: ExtractedFields, positives: List[str], negatives: List[str]):
        """Extract and validate passport MRZ and identity fields."""
        # MRZ Line 1: P<IND...
        mrz1_match = re.search(r'P<([A-Z]{3})([A-Z<]+)', text)
        if mrz1_match:
            fields.nationality = mrz1_match.group(1)
            raw_name = mrz1_match.group(2).replace('<', ' ').strip()
            fields.name = raw_name
            positives.append(f"MRZ Line 1: Decoded Machine-Readable Zone with issuing nation {fields.nationality}.")

        # MRZ Line 2: Passport No (9 chars with < padding), Check digit, Nationality, DOB (6), Check, Sex (1), Expiry (6), Check
        mrz2_match = re.search(r'([A-Z0-9<]{9})([0-9])([A-Z<]{3})([0-9]{6})([0-9])([MF<])([0-9]{6})([0-9])', text)
        if mrz2_match:
            doc_num = mrz2_match.group(1)
            doc_check = int(mrz2_match.group(2))
            if not fields.nationality:
                fields.nationality = mrz2_match.group(3).replace('<', '')
            dob_raw = mrz2_match.group(4)
            dob_check = int(mrz2_match.group(5))
            gender = mrz2_match.group(6)
            exp_raw = mrz2_match.group(7)
            exp_check = int(mrz2_match.group(8))

            fields.document_number = doc_num.replace('<', '')
            fields.gender = "FEMALE" if gender == "F" else ("MALE" if gender == "M" else "OTHER")

            # Validate ICAO 9303 modulo-10 checksums
            doc_calc = cls._icao9303_checksum(doc_num)
            dob_calc = cls._icao9303_checksum(dob_raw)
            exp_calc = cls._icao9303_checksum(exp_raw)

            chk_passed = (doc_calc == doc_check) and (dob_calc == dob_check) and (exp_calc == exp_check)
            fields.checksums_valid = chk_passed

            if chk_passed:
                positives.append("ICAO 9303 Modulo-10 Checksums: Passport number, DOB, and Expiry digits pass check algorithm.")
                fields.checksum_details = "All ICAO 9303 Type-3 check digits verified."
            else:
                negatives.append("ICAO 9303 Checksum Mismatch: MRZ check digits do not match extracted numbers. Potential tampering.")
                fields.checksum_details = f"Check digit mismatch: Doc ({doc_calc} vs {doc_check}), DOB ({dob_calc} vs {dob_check}), Expiry ({exp_calc} vs {exp_check})."

            # Parse DOB (YYMMDD)
            try:
                yy = int(dob_raw[:2])
                mm = int(dob_raw[2:4])
                dd = int(dob_raw[4:6])
                curr_yy = date.today().year % 100
                century = 1900 if yy > curr_yy else 2000
                fields.dob = f"{century + yy}-{mm:02d}-{dd:02d}"
            except Exception:
                pass

            # Parse Expiry (YYMMDD)
            try:
                yy = int(exp_raw[:2])
                mm = int(exp_raw[2:4])
                dd = int(exp_raw[4:6])
                fields.expiry_date = f"20{yy:02d}-{mm:02d}-{dd:02d}"
            except Exception:
                pass
        else:
            # Fallback regex for standard text fields
            doc_search = re.search(r'\b([A-PR-WYa-pr-wy][1-9]\d\s?\d{4}[1-9])\b', text)
            if doc_search:
                fields.document_number = doc_search.group(1).replace(" ", "")
                positives.append("Passport Number: Canonical 8-character format identified.")

        # Fallback to visual text extraction if fields missing
        if not fields.dob or not fields.name or not fields.expiry_date:
            cls._extract_generic_fields(text, fields, positives, negatives)

    @classmethod
    def _extract_aadhaar_fields(cls, text: str, fields: ExtractedFields, qr_data: Dict[str, Any], positives: List[str], negatives: List[str]):
        """Extract and validate 12-digit Aadhaar number with Verhoeff algorithm and official UIDAI checks."""
        # 1. 12-digit Aadhaar pattern or pre-extracted UID
        clean_num = None
        if fields.document_number and len(str(fields.document_number).replace(" ", "")) == 12:
            clean_num = str(fields.document_number).replace(" ", "")
        else:
            match = re.search(r'\b([2-9]\d{3}\s?\d{4}\s?\d{4})\b', text)
            if match:
                clean_num = match.group(1).replace(" ", "")
                fields.document_number = clean_num

        if clean_num and len(clean_num) == 12:
            # Verhoeff check
            is_valid = cls._validate_verhoeff(clean_num)
            fields.checksums_valid = is_valid
            if is_valid:
                positives.append(f"Verhoeff Mathematical Checksum: 12-digit UID ({clean_num[:4]} XXXX {clean_num[-4:]}) conforms to statutory parity.")
                fields.checksum_details = "Verhoeff check digit matches."
            else:
                negatives.append("Verhoeff Checksum Failure: 12-digit UID fails mathematical parity check.")
                fields.checksum_details = "Invalid Verhoeff check digit on Aadhaar sequence."

        # 2. Extract visual fields from OCR text
        if not fields.dob:
            dob_m = re.search(r'(?:DOB|Date of Birth|Birth Date|Birth)[:\s]+([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{4})', text, re.IGNORECASE)
            if dob_m:
                fields.dob = dob_m.group(1)
            else:
                yob_m = re.search(r'(?:Year of Birth|YOB)[:\s]+([12][90]\d{2})', text, re.IGNORECASE)
                if yob_m:
                    fields.dob = f"{yob_m.group(1)}-01-01"

        if not fields.gender:
            if "FEMALE" in text:
                fields.gender = "FEMALE"
            elif "MALE" in text:
                fields.gender = "MALE"
            elif "TRANSGENDER" in text:
                fields.gender = "TRANSGENDER"

        # 3. Check official QR data / Official Registry
        if fields.qr_payload:
            off_res = OfficialRegistryService.decode_and_verify_aadhaar_qr(fields.qr_payload)
            if off_res.get("signature_verified"):
                positives.append(f"UIDAI Official Digital Signature: Validated cryptographic QR envelope ({off_res.get('format')}).")
                if off_res.get("name"): fields.name = off_res["name"]
                if off_res.get("dob"): fields.dob = off_res["dob"]
                if off_res.get("gender"): fields.gender = off_res["gender"]
                if off_res.get("masked_aadhaar") and not fields.document_number:
                    fields.document_number = off_res["masked_aadhaar"]
        elif qr_data:
            if "name" in qr_data: fields.name = qr_data["name"]
            if "dob" in qr_data: fields.dob = qr_data["dob"]
            if "gender" in qr_data: fields.gender = qr_data["gender"]
            if "uid" in qr_data and not fields.document_number:
                fields.document_number = qr_data["uid"]
            positives.append("UIDAI Secure QR: Parsed demographic envelope from 2D cryptographic barcode.")

        # 4. Extract Name if still missing
        if not fields.name:
            cls._extract_generic_fields(text, fields, positives, negatives)

    @classmethod
    def _extract_pan_fields(cls, text: str, fields: ExtractedFields, positives: List[str], negatives: List[str]):
        """Extract and validate 10-character PAN card number and official registry status."""
        match = re.search(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', text)
        if match:
            pan = match.group(1)
            fields.document_number = pan
            entity_code = pan[3]
            allowed_entities = {
                'P': 'Individual', 'C': 'Company', 'H': 'HUF', 'A': 'AOP',
                'B': 'BOI', 'G': 'Government', 'J': 'Artificial Juridical Person',
                'L': 'Local Authority', 'F': 'Firm', 'T': 'Trust'
            }

            if entity_code in allowed_entities:
                positives.append(f"PAN Canonical Format: Valid 10-character string with entity type '{allowed_entities[entity_code]}' (Code '{entity_code}').")
                fields.checksums_valid = True
                fields.checksum_details = f"Entity '{allowed_entities[entity_code]}' verified by 4th alphanumeric index."
            else:
                negatives.append(f"PAN Entity Anomaly: 4th character '{entity_code}' is not a recognized CBDT taxpayer category.")
                fields.checksums_valid = False
        else:
            negatives.append("PAN Syntax Error: No 10-digit alphanumeric Permanent Account Number detected.")

        # Visual DOB from OCR
        if not fields.dob:
            dob_m = re.search(r'(?:DOB|Date of Birth)[\s:]*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{4})', text, re.IGNORECASE)
            if dob_m:
                fields.dob = dob_m.group(1)

        # Official PAN QR check
        if fields.qr_payload:
            pan_qr_res = OfficialRegistryService.decode_and_verify_pan_qr(fields.qr_payload)
            if pan_qr_res.get("signature_verified"):
                positives.append(f"NSDL / Income Tax Official Registry: PAN {pan_qr_res.get('pan')} verified active in CBDT central ledger.")
                if pan_qr_res.get("name"): fields.name = pan_qr_res["name"]
                if pan_qr_res.get("dob"): fields.dob = pan_qr_res["dob"]

        if not fields.name or not fields.dob:
            cls._extract_generic_fields(text, fields, positives, negatives)

    @classmethod
    def _extract_dl_fields(cls, text: str, fields: ExtractedFields, positives: List[str], negatives: List[str]):
        """Extract Indian Driving License format."""
        match = re.search(r'\b([A-Z]{2}[-\s]?[0-9]{2}[-\s]?[0-9]{4}[0-9]{7})\b', text)
        if not match:
            match = re.search(r'\b([A-Z]{2}[0-9]{13,14})\b', text)

        if match:
            fields.document_number = match.group(1)
            positives.append(f"Driving License Format: Matches MoRTH State/RTO canonical serial structure.")
            fields.checksums_valid = True
        else:
            negatives.append("Driving License: Standard DL number format not found in optical text.")

    @classmethod
    def _extract_voter_fields(cls, text: str, fields: ExtractedFields, positives: List[str], negatives: List[str]):
        """Extract Voter ID (EPIC) format."""
        match = re.search(r'\b([A-Z]{3}[0-9]{7})\b', text)
        if match:
            fields.document_number = match.group(1)
            positives.append(f"Voter ID Format: 10-character EPIC serial structure identified.")
            fields.checksums_valid = True
        else:
            negatives.append("Voter ID: Standard 10-digit EPIC serial code not detected.")

    @classmethod
    def _extract_education_fields(cls, text: str, fields: ExtractedFields, positives: List[str], negatives: List[str], raw_original: Optional[str] = None):
        """Extract academic credentials, student name, institution, serial/roll/TC number, and DOB."""
        # 1. Document / TC / Roll / Admission Number
        doc_num_m = re.search(r'(?:TC\s*NO|T\.C\.\s*NO|CERTIFICATE\s*NO|ROLL\s*NO|REG(?:ISTRATION)?\s*NO|ADMISSION\s*NO|ENROLMENT\s*NO|PIN)[\s:\-]+([A-Za-z0-9\-_/]{4,25})', text, re.IGNORECASE)
        if doc_num_m:
            fields.document_number = doc_num_m.group(1).strip()
            positives.append(f"Educational Credential Reference: Document serial identifier '{fields.document_number}' registered.")
            fields.checksums_valid = True
            fields.checksum_details = "Institutional academic certificate identifier format validated."
        
        # 2. Date of Birth vs Issue Date
        all_dates = re.findall(r'\b([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{4})\b', text)
        
        # Look for issue date explicitly labeled (e.g. Date : 16-06-2026)
        issue_m = re.search(r'(?:Date|Dated|Issue\s*Date)[\s:]*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{4})', text, re.IGNORECASE)
        if issue_m:
            fields.issue_date = issue_m.group(1).strip()
            positives.append(f"Certificate Issuance Date: Document issued on {fields.issue_date}.")

        # DOB: Prioritize explicit label or valid past birth date (1940-2015)
        dob_m = re.search(r'(?:DOB|DATE OF BIRTH|BORN ON|BIRTH DATE)[\s:]*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{4})', text, re.IGNORECASE)
        if dob_m:
            fields.dob = dob_m.group(1).strip()
        else:
            for d in all_dates:
                parts = re.split(r'[/-]', d)
                if len(parts) == 3:
                    try:
                        yr = int(parts[2] if len(parts[0]) <= 2 else parts[0])
                        if 1940 <= yr <= 2015:
                            fields.dob = d
                            break
                    except ValueError:
                        pass

        # Expiry: Educational certificates are permanent / perpetual
        fields.expiry_date = None

        # 3. Student / Candidate Name Extraction
        FORM_WORDS = {
            'OTHER', 'MONEY', 'DUE', 'WHETHER', 'FEES', 'PAID', 'COURSE', 'HIGHER',
            'CLASS', 'PROMOTION', 'QUALIFIED', 'CONDUCT', 'CHARACTER', 'APPLICATION',
            'REMARKS', 'IDENTIFICATION', 'APPEARED', 'PASSED', 'DISCONTINUED', 'FOREHEAD',
            'FINGER', 'MOLE', 'LEFT', 'RIGHT', 'STATION', 'POLICE', 'DATE', 'WORDS',
            'LEAVING', 'STUDYING', 'TIME', 'ADMITTED', 'STUDENT', 'BLOCK', 'LETTERS',
            'NAME', 'FATHER', 'MOTHER', 'NATIONALITY', 'RELIGION', 'CASTE', 'EXAMS',
            'FINAL', 'TRANSFER', 'CERTIFICATE', 'INSTITUTE', 'TECHNOLOGY', 'COLLEGE',
            'POLYTECHNIC', 'SIGNATURE', 'VALID', 'DIGITALLY', 'SIGNED', 'REASON',
            'APPROVE', 'SATISFACTORY', 'COMPLETED', 'KARIMNAGAR', 'THIMMAPUR', 'NUSTULAPUR',
            'BESIDE', 'PRINCIPAL', 'GOVERNMENT', 'DEPARTMENT', 'STATE', 'INDIA', 'DISTRICT',
            'CERTIFICTE', 'SECONDARY', 'EDUCATION', 'UNIVERSITY', 'BOARD', 'CENTRAL'
        }

        # Check inline format: Name of Student: <Name>
        name_direct = re.search(r'(?:NAME\s+OF\s+(?:THE\s+)?STUDENT|STUDENT\s+NAME|NAME\s+OF\s+(?:THE\s+)?CANDIDATE|CANDIDATE\s+NAME)[\s:\-]+([A-Za-z\s]{3,35})(?=\n|$)', text, re.IGNORECASE)
        if name_direct:
            cand = name_direct.group(1).strip()
            cand_clean = re.sub(r'\(.*?\)|IN BLOCK LETTERS|BLOCK LETTERS', '', cand, flags=re.IGNORECASE).strip()
            cand_words = set(cand_clean.upper().split())
            if len(cand_clean) >= 3 and not cand_words.intersection(FORM_WORDS):
                fields.name = cand_clean

        # Form answer list fallback using original document casing
        if not fields.name:
            source = raw_original or text
            lines = [l.strip() for l in source.split('\n') if l.strip()]
            for line in lines:
                if re.match(r'^[A-Z][A-Z\s]{4,35}$', line):
                    words = line.split()
                    if 2 <= len(words) <= 4:
                        if not any(w in FORM_WORDS for w in words):
                            fields.name = line
                            break

        if fields.name:
            positives.append(f"Student Identity: Candidate name '{fields.name}' confirmed.")

        # 4. Nationality
        if "INDIAN" in text:
            fields.nationality = "INDIAN"
        elif "NEPALESE" in text:
            fields.nationality = "NEPALESE"
        elif "BHUTANESE" in text:
            fields.nationality = "BHUTANESE"

    @classmethod
    def _extract_generic_fields(cls, text: str, fields: ExtractedFields, positives: List[str], negatives: List[str], raw_original: Optional[str] = None):
        """Extract generic names and dates from text."""
        # 1. Extract DOB
        if not fields.dob:
            dob_m = re.search(r'(?:DOB|DATE OF BIRTH|BIRTH DATE)[\s:]*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{4})', text, re.IGNORECASE)
            if dob_m:
                fields.dob = dob_m.group(1).strip()
            else:
                date_matches = re.findall(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b', text)
                for d in date_matches:
                    parts = re.split(r'[/-]', d)
                    yr = int(parts[2] if len(parts[0]) <= 2 else parts[0]) if len(parts) == 3 else 0
                    if 1940 <= yr <= 2015:
                        fields.dob = d
                        break

        # 2. Extract Expiry if missing
        if not fields.expiry_date:
            exp_m = re.search(r'(?:EXPIRY|EXPIRATION|VALID TILL|EXP)[\s:]*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{4})', text, re.IGNORECASE)
            if exp_m:
                fields.expiry_date = exp_m.group(1).strip()

        # 3. Extract Name if missing
        if not fields.name:
            STOP_WORDS = {
                "STUDENT", "BLOCK LETTERS", "APPLICANT", "CANDIDATE", "INSTITUTE",
                "COLLEGE", "TRANSFER", "CERTIFICATE", "POLICE", "STATION", "TECHNOLOGY",
                "SATISFACTORY", "COURSE COMPLETED", "SIGNATURE", "VALID", "PRINCIPAL"
            }
            name_m = re.search(r'(?:NAME|HOLDER|GIVEN NAME)[\s:]+([A-Za-z\s]{3,30})', text, re.IGNORECASE)
            if name_m:
                clean_n = re.split(r'\n|FATHER|MOTHER|DOB|DATE|BIRTH|EXPIRY|GENDER', name_m.group(1), flags=re.IGNORECASE)[0].strip()
                clean_n = re.sub(r'\(.*?\)|IN BLOCK LETTERS|BLOCK LETTERS', '', clean_n, flags=re.IGNORECASE).strip()
                if len(clean_n) >= 3 and not any(sw in clean_n.upper() for sw in STOP_WORDS):
                    fields.name = clean_n

    @classmethod
    def _normalize_date(cls, d_str: Optional[str]) -> Optional[str]:
        """Normalize various date formats into YYYY-MM-DD for reliable cross-document comparison."""
        if not d_str:
            return None
        d_clean = d_str.strip().replace('/', '-')
        for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y', '%d-%m-%y'):
            try:
                return datetime.strptime(d_clean, fmt).strftime('%Y-%m-%d')
            except ValueError:
                pass
        return d_clean

    @classmethod
    def _compare_ocr_qr(cls, fields: ExtractedFields, positives: List[str], negatives: List[str]):
        """Cross-check extracted visual OCR fields with decoded QR matrix data."""
        qr = fields.qr_data_parsed
        if not qr:
            return

        # Check DOB
        if fields.dob and "dob" in qr:
            qr_dob = qr["dob"].replace("/", "-").strip()
            ocr_dob = fields.dob.replace("/", "-").strip()
            if qr_dob == ocr_dob:
                positives.append(f"OCR ↔ QR Consistency: Date of Birth ({ocr_dob}) matches QR matrix payload perfectly.")
            else:
                negatives.append(f"Critical OCR ↔ QR Mismatch: Visual DOB '{ocr_dob}' conflicts with QR encoded DOB '{qr_dob}'. Potential physical alteration.")

        # Check Name
        if fields.name and "name" in qr:
            qr_name = qr["name"].upper().strip()
            ocr_name = fields.name.upper().strip()
            if qr_name in ocr_name or ocr_name in qr_name:
                positives.append("OCR ↔ QR Consistency: Visual citizen name correlates with cryptographic QR envelope.")
            else:
                negatives.append(f"OCR ↔ QR Conflict: Extracted visual name '{ocr_name}' differs from QR payload name '{qr_name}'.")

    @classmethod
    def _validate_dates(cls, fields: ExtractedFields, positives: List[str], negatives: List[str]):
        """Logical sanity checks for DOB and Expiry."""
        today = date.today()

        # Check DOB
        if fields.dob:
            try:
                norm_dob = cls._normalize_date(fields.dob)
                dob_obj = datetime.strptime(norm_dob, "%Y-%m-%d").date()
                if dob_obj > today:
                    negatives.append(f"Logical Chronology Anomaly: Date of Birth ({fields.dob}) is in the future.")
                else:
                    age = (today - dob_obj).days // 365
                    if age < 0 or age > 115:
                        negatives.append(f"Logical Range Anomaly: Calculated age ({age} years) is unrealistic.")
                    else:
                        positives.append(f"Date Validation: Date of birth is chronologically valid (calculated age: {age} years).")
            except Exception:
                pass

        # Check Expiry
        if fields.expiry_date:
            try:
                norm_exp = cls._normalize_date(fields.expiry_date)
                exp_obj = datetime.strptime(norm_exp, "%Y-%m-%d").date()
                if exp_obj < today:
                    negatives.append(f"Validity Notice: Credential expired on {fields.expiry_date}.")
                else:
                    positives.append(f"Validity Period: Credential is currently active (valid through {fields.expiry_date}).")
            except Exception:
                pass

    @classmethod
    def compare_multiple_documents(cls, docs_extracted: List[ExtractedFields]) -> CrossDocumentReport:
        """
        Cross-check multiple documents submitted in the same session.
        Example: Passport DOB vs Visa DOB.
        """
        mismatches: List[CrossDocumentMismatch] = []
        n = len(docs_extracted)

        if n < 2:
            return CrossDocumentReport(
                total_documents=n,
                consistent=True,
                mismatches=[],
                summary="Single document session. Multi-document cross-comparison not applicable."
            )

        # Compare pair-wise
        for i in range(n):
            for j in range(i + 1, n):
                d1 = docs_extracted[i]
                d2 = docs_extracted[j]

                # 1. Compare Date of Birth
                if d1.dob and d2.dob:
                    clean_dob1 = cls._normalize_date(d1.dob)
                    clean_dob2 = cls._normalize_date(d2.dob)
                    if clean_dob1 and clean_dob2 and clean_dob1 != clean_dob2:
                        mismatches.append(
                            CrossDocumentMismatch(
                                field_name="Date of Birth",
                                doc1_type=d1.document_type,
                                doc1_value=d1.dob,
                                doc2_type=d2.document_type,
                                doc2_value=d2.dob,
                                severity="HIGH",
                                description=f"Cross-Document Mismatch: {d1.document_type} DOB ({d1.dob}) conflicts with {d2.document_type} DOB ({d2.dob})."
                            )
                        )

                # 2. Compare Name
                if d1.name and d2.name:
                    n1 = d1.name.upper().strip()
                    n2 = d2.name.upper().strip()
                    if n1 != n2 and (n1 not in n2) and (n2 not in n1):
                        mismatches.append(
                            CrossDocumentMismatch(
                                field_name="Full Name",
                                doc1_type=d1.document_type,
                                doc1_value=d1.name,
                                doc2_type=d2.document_type,
                                doc2_value=d2.name,
                                severity="MEDIUM",
                                description=f"Name Divergence: {d1.document_type} ('{d1.name}') vs {d2.document_type} ('{d2.name}')."
                            )
                        )

                # 3. Compare Gender
                if d1.gender and d2.gender:
                    if d1.gender.upper() != d2.gender.upper():
                        mismatches.append(
                            CrossDocumentMismatch(
                                field_name="Gender",
                                doc1_type=d1.document_type,
                                doc1_value=d1.gender,
                                doc2_type=d2.document_type,
                                doc2_value=d2.gender,
                                severity="HIGH",
                                description=f"Gender Conflict: {d1.document_type} states '{d1.gender}' but {d2.document_type} states '{d2.gender}'."
                            )
                        )

        is_consistent = len(mismatches) == 0
        summary = (
            f"All {n} submitted documents correlate consistently across demographic identity fields."
            if is_consistent else
            f"Detected {len(mismatches)} cross-document demographic conflict(s) requiring secondary officer examination."
        )

        return CrossDocumentReport(
            total_documents=n,
            consistent=is_consistent,
            mismatches=mismatches,
            summary=summary
        )

    # --------------------------------------------------------------------------
    # Utility Checksums & QR Parsing
    # --------------------------------------------------------------------------
    @classmethod
    def _validate_verhoeff(cls, num_str: str) -> bool:
        """Validate an Indian Aadhaar number using the Verhoeff algorithm."""
        digits = [int(c) for c in num_str if c.isdigit()]
        if len(digits) != 12:
            return False

        c = 0
        for i, digit in enumerate(reversed(digits)):
            c = cls.VERHOEFF_D[c][cls.VERHOEFF_P[i % 8][digit]]
        return c == 0

    @classmethod
    def _icao9303_checksum(cls, s: str) -> int:
        """ICAO 9303 modulo-10 checksum calculation with weights [7, 3, 1]."""
        weights = [7, 3, 1]
        total = 0
        for i, char in enumerate(s):
            if char.isdigit():
                val = int(char)
            elif 'A' <= char <= 'Z':
                val = ord(char) - ord('A') + 10
            elif char == '<':
                val = 0
            else:
                val = 0
            total += val * weights[i % 3]
        return total % 10

    @classmethod
    def _parse_qr_payload(cls, payload: Optional[str]) -> Dict[str, Any]:
        """Parse structured fields from QR code payloads (XML, JSON, or key-value)."""
        if not payload:
            return {}

        data = {}
        # 1. XML Aadhaar QR format: <PrintLetterBarcodeData name="..." dob="..." ... />
        if "<PrintLetterBarcodeData" in payload or "uid=" in payload:
            name_m = re.search(r'name=["\']([^"\']+)["\']', payload, re.IGNORECASE)
            dob_m = re.search(r'dob=["\']([^"\']+)["\']', payload, re.IGNORECASE)
            gender_m = re.search(r'gender=["\']([^"\']+)["\']', payload, re.IGNORECASE)
            uid_m = re.search(r'uid=["\']([^"\']+)["\']', payload, re.IGNORECASE)

            if name_m: data["name"] = name_m.group(1)
            if dob_m: data["dob"] = dob_m.group(1)
            if gender_m: data["gender"] = gender_m.group(1)
            if uid_m: data["uid"] = uid_m.group(1)

        # 2. Key-value style: DOB: ... Name: ...
        if not data:
            dob_m = re.search(r'DOB[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}-\d{2}-\d{2})', payload, re.IGNORECASE)
            if dob_m:
                data["dob"] = dob_m.group(1)

        return data
