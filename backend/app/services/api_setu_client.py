"""
api_setu_client.py — Government Master Registry Bridge
=======================================================
Modular async HTTP client for API Setu (apisetu.gov.in).

Supports:
  • MoRTH Parivahan Sarathi  → Driving Licence national register
  • CBDT / Income Tax Dept   → PAN card registry
  • University Registries     → Degree / Marksheet verification

Offline Sandbox Mode (OFFLINE_SANDBOX_MODE=true):
  All calls return realistic mock responses that match the live API schema.
  Enable this for offline demonstrations when no live VPN/production credentials are available.
"""

import hashlib
import json
import os
import asyncio
from datetime import datetime, timezone, date
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings


# ──────────────────────────────────────────────────────────────────────────────
# Sandbox mock data — realistic but entirely fabricated for demo purposes
# ──────────────────────────────────────────────────────────────────────────────

_SANDBOX_DL = {
    "dlNumber": "MH0120210012345",
    "name": "RAJESH KUMAR SHARMA",
    "dob": "1992-07-15",
    "gender": "M",
    "fatherName": "ANIL KUMAR SHARMA",
    "address": "Flat 4B, Surya Apartment, Andheri East, Mumbai, Maharashtra - 400069",
    "validity": {
        "from": "2021-06-10",
        "to": "2041-06-09"
    },
    "vehicleClasses": ["MCWG", "LMV"],
    "bloodGroup": "B+",
    "issueDate": "2021-06-10",
    "issuingAuthority": "RTO Mumbai East (MH01)",
    "status": "ACTIVE",
    "registrySource": "MoRTH Sarathi National Register",
    "verifiedAt": datetime.now(timezone.utc).isoformat()
}

_SANDBOX_PAN = {
    "panNumber": "ABCPK1234F",
    "name": "RAJESH KUMAR SHARMA",
    "dob": "15/07/1992",
    "status": "EXISTING AND VALID",
    "panType": "Individual",
    "aadhaarSeeded": True,
    "registrySource": "CBDT / Income Tax Department India",
    "verifiedAt": datetime.now(timezone.utc).isoformat()
}

_SANDBOX_DEGREE = {
    "enrollmentNumber": "2018CS056789",
    "studentName": "RAJESH KUMAR SHARMA",
    "fatherName": "ANIL KUMAR SHARMA",
    "programName": "Bachelor of Technology (B.Tech) — Computer Science & Engineering",
    "university": "Dr. APJ Abdul Kalam Technical University, Lucknow",
    "board": "AKTU",
    "yearOfPassing": 2022,
    "result": "FIRST DIVISION WITH DISTINCTION",
    "cgpa": "8.74 / 10",
    "registrationStatus": "VERIFIED",
    "registrySource": "National Academic Depository (NAD) — University Registry",
    "verifiedAt": datetime.now(timezone.utc).isoformat()
}


# ──────────────────────────────────────────────────────────────────────────────
# API Setu Client
# ──────────────────────────────────────────────────────────────────────────────

class ApiSetuClient:
    """
    Async HTTP client for API Setu government master registries.
    Automatically falls back to Offline Sandbox Mode when
    OFFLINE_SANDBOX_MODE=true or credentials are not configured.
    """

    BASE_URL = settings.API_SETU_BASE_URL
    CLIENT_ID = settings.API_SETU_CLIENT_ID
    CLIENT_SECRET = settings.API_SETU_CLIENT_SECRET
    SANDBOX = settings.OFFLINE_SANDBOX_MODE
    TIMEOUT = 8.0  # seconds — must stay within 2.2s total pipeline budget

    # API Setu endpoint paths
    _ENDPOINTS = {
        "sarathi_dl":   "/morth/sarathi/rc/v3/search",
        "cbdt_pan":     "/cbdt/pan/v3/search",
        "nad_degree":   "/nad/certificate/v2/verify",
    }

    @classmethod
    def _sandbox_mode(cls) -> bool:
        """Return True if offline sandbox should be used."""
        return cls.SANDBOX or not cls.CLIENT_ID or not cls.CLIENT_SECRET

    @classmethod
    def _build_headers(cls) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-APISETU-CLIENTID": cls.CLIENT_ID,
            "X-APISETU-APIKEY": cls.CLIENT_SECRET,
            "Accept": "application/json"
        }

    @classmethod
    def _sha256_mask(cls, value: str, keep_last: int = 4) -> str:
        """Mask sensitive identifiers, keeping only last N chars for display."""
        if not value or len(value) <= keep_last:
            return value
        return "X" * (len(value) - keep_last) + value[-keep_last:]

    # ─────────────────────────────────────────────────────────────────────────
    # 1. MoRTH Sarathi — Driving Licence Verification
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    async def verify_driving_licence(
        cls,
        dl_number: str,
        dob: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query MoRTH Parivahan Sarathi national register for a Driving Licence.

        Args:
            dl_number: DL number string (e.g. "MH0120210012345")
            dob: Date of birth in YYYY-MM-DD format (required by Sarathi API)

        Returns:
            Dict with DL details or sandbox mock response.
        """
        if cls._sandbox_mode():
            return cls._sandbox_response("DRIVING_LICENCE", dl_number, _SANDBOX_DL)

        try:
            payload = {"dlNumber": dl_number.upper().strip()}
            if dob:
                payload["dob"] = dob

            async with httpx.AsyncClient(timeout=cls.TIMEOUT) as client:
                resp = await client.post(
                    f"{cls.BASE_URL}{cls._ENDPOINTS['sarathi_dl']}",
                    headers=cls._build_headers(),
                    json=payload
                )
                resp.raise_for_status()
                data = resp.json()
                data["registrySource"] = "MoRTH Sarathi National Register (Live)"
                data["verifiedAt"] = datetime.now(timezone.utc).isoformat()
                data["sandboxMode"] = False
                return data

        except httpx.HTTPStatusError as e:
            return cls._error_response("DRIVING_LICENCE", dl_number, str(e))
        except Exception as e:
            return cls._error_response("DRIVING_LICENCE", dl_number, str(e))

    # ─────────────────────────────────────────────────────────────────────────
    # 2. CBDT / Income Tax — PAN Card Verification
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    async def verify_pan(
        cls,
        pan_number: str,
        name: Optional[str] = None,
        dob: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query CBDT / Income Tax Department PAN registry.

        Args:
            pan_number: 10-char alphanumeric PAN (e.g. "ABCPK1234F")
            name:       Taxpayer name for cross-check (optional)
            dob:        Date of birth DD/MM/YYYY (optional)

        Returns:
            Dict with PAN status, name match, and Aadhaar-seeded flag.
        """
        if cls._sandbox_mode():
            mock = dict(_SANDBOX_PAN)
            mock["panNumber"] = pan_number.upper()
            return cls._sandbox_response("PAN_CARD", pan_number, mock)

        try:
            payload = {"panNumber": pan_number.upper().strip()}
            if name:
                payload["name"] = name
            if dob:
                payload["dob"] = dob

            async with httpx.AsyncClient(timeout=cls.TIMEOUT) as client:
                resp = await client.post(
                    f"{cls.BASE_URL}{cls._ENDPOINTS['cbdt_pan']}",
                    headers=cls._build_headers(),
                    json=payload
                )
                resp.raise_for_status()
                data = resp.json()
                data["registrySource"] = "CBDT / Income Tax Department India (Live)"
                data["verifiedAt"] = datetime.now(timezone.utc).isoformat()
                data["sandboxMode"] = False
                return data

        except httpx.HTTPStatusError as e:
            return cls._error_response("PAN_CARD", pan_number, str(e))
        except Exception as e:
            return cls._error_response("PAN_CARD", pan_number, str(e))

    # ─────────────────────────────────────────────────────────────────────────
    # 3. National Academic Depository — University Degree / Marksheet
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    async def verify_degree(
        cls,
        enrollment_number: str,
        university_name: Optional[str] = None,
        year_of_passing: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Query National Academic Depository / University Registry for a degree.

        Args:
            enrollment_number: Student enrolment / roll number
            university_name:   Institution name for filtering (optional)
            year_of_passing:   Graduation year (optional)

        Returns:
            Dict with degree details, CGPA, result, and registry verification status.
        """
        if cls._sandbox_mode():
            mock = dict(_SANDBOX_DEGREE)
            mock["enrollmentNumber"] = enrollment_number
            if university_name:
                mock["university"] = university_name
            if year_of_passing:
                mock["yearOfPassing"] = year_of_passing
            return cls._sandbox_response("DEGREE_CERTIFICATE", enrollment_number, mock)

        try:
            payload = {"enrollmentNumber": enrollment_number.strip()}
            if university_name:
                payload["universityName"] = university_name
            if year_of_passing:
                payload["yearOfPassing"] = year_of_passing

            async with httpx.AsyncClient(timeout=cls.TIMEOUT) as client:
                resp = await client.post(
                    f"{cls.BASE_URL}{cls._ENDPOINTS['nad_degree']}",
                    headers=cls._build_headers(),
                    json=payload
                )
                resp.raise_for_status()
                data = resp.json()
                data["registrySource"] = "National Academic Depository / University Registry (Live)"
                data["verifiedAt"] = datetime.now(timezone.utc).isoformat()
                data["sandboxMode"] = False
                return data

        except httpx.HTTPStatusError as e:
            return cls._error_response("DEGREE_CERTIFICATE", enrollment_number, str(e))
        except Exception as e:
            return cls._error_response("DEGREE_CERTIFICATE", enrollment_number, str(e))

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def _sandbox_response(
        cls,
        doc_type: str,
        identifier: str,
        mock_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Wrap mock data with sandbox metadata envelope."""
        response = dict(mock_data)
        response["_meta"] = {
            "sandboxMode": True,
            "mode": "OFFLINE_SANDBOX",
            "documentType": doc_type,
            "queriedIdentifier": cls._sha256_mask(identifier, keep_last=4),
            "notice": (
                "SANDBOX MODE — Realistic mock data for offline demonstration. "
                "Set OFFLINE_SANDBOX_MODE=false and configure API Setu credentials "
                "in .env to enable live government registry queries."
            ),
            "apiSetuEndpoint": "apisetu.gov.in",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "verificationStatus": "SANDBOX_VERIFIED",
            "matchScore": 1.0,
        }
        response["verificationStatus"] = "SANDBOX_VERIFIED"
        response["sandboxMode"] = True
        return response

    @classmethod
    def _error_response(
        cls,
        doc_type: str,
        identifier: str,
        error_msg: str
    ) -> Dict[str, Any]:
        """Return structured error when live gateway fails."""
        return {
            "verificationStatus": "GATEWAY_ERROR",
            "sandboxMode": False,
            "documentType": doc_type,
            "queriedIdentifier": cls._sha256_mask(identifier, keep_last=4),
            "error": error_msg,
            "notice": (
                "Live API Setu gateway returned an error. "
                "Enable OFFLINE_SANDBOX_MODE=true in .env for local demo mode."
            ),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
