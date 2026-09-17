"""
================================================================================
VERIDOC Desktop Python API Client
================================================================================
This script demonstrates how to interact with the VERIDOC REST API programmatically
from your desktop environment using Python.

Requirements:
    pip install requests

Usage:
    python api_client_example.py [optional_path_to_image_or_pdf]
"""

import sys
import os
import json
import requests

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
BASE_URL = "http://127.0.0.1:8000"
API_KEY = "vrd_live_master_kiosk_key"  # Default master key (or any key starting with 'vrd_live_')

HEADERS = {
    "X-API-Key": API_KEY
}


def check_server_health():
    """Verify that the local VERIDOC server is running."""
    url = f"{BASE_URL}/api/v1/health"
    try:
        resp = requests.get(url, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            print("Server Status     : [ONLINE]")
            print(f"Service           : {data.get('service')}")
            print(f"Version           : {data.get('version')}")
            print(f"Compliance        : {data.get('statutory_compliance')}")
            return True
        else:
            print(f"Server returned HTTP {resp.status_code}: {resp.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to VERIDOC server at http://127.0.0.1:8000.")
        print("Please ensure RUN_PROTOTYPE.bat or uvicorn is running.")
        return False


def verify_document(file_path: str, force_deep_ai: bool = False):
    """
    Submit a document for complete verification:
    - Optical Quality Assessment (blur, resolution, illumination)
    - Error Level Analysis (ELA) for image tampering & splicing
    - Biometric Portrait Verification
    - Deep Learning OCR & Font Consistency
    - Intra-Document Cross-Verification
    - Checksum Validations (Verhoeff D5, ICAO 9303, CBDT)
    - Cryptographic QR Triangulation
    - Google Gemini Multimodal Vision AI Audit
    - Section 65B Legal Evidence Chain
    """
    url = f"{BASE_URL}/api/v1/verify"

    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return None

    filename = os.path.basename(file_path)
    print(f"\nSubmitting document '{filename}' for forensic verification...")

    with open(file_path, "rb") as f:
        files = {
            "file": (filename, f, "application/octet-stream")
        }
        data = {
            "checkpoint_id": "DESKTOP-CLIENT-01",
            "officer_id": "OFFICER-DESKTOP",
            "force_deep_ai": "true" if force_deep_ai else "false",
            "skip_live_gateway": "true",
            "prototype_mode": "true"
        }

        resp = requests.post(url, headers=HEADERS, files=files, data=data)

    if resp.status_code != 200:
        print(f"API Error ({resp.status_code}): {resp.text}")
        return None

    result = resp.json()

    print("\n" + "=" * 65)
    print("                VERIDOC VERIFICATION REPORT")
    print("=" * 65)
    print(f"Session ID           : {result.get('session_id')}")
    print(f"Document Type        : {result.get('document_type')}")
    print(f"Overall Verdict      : {result.get('overall_verdict')}")
    print(f"Officer Action       : {result.get('officer_recommendation')}")
    
    risk = result.get("risk", {})
    print(f"Risk Level           : {risk.get('risk_level')} (Score: {risk.get('risk_score')}/100)")
    print(f"Confidence Score     : {risk.get('confidence_score')}%")

    # Extracted fields
    ext = result.get("extracted_fields", {})
    print("-" * 65)
    print("EXTRACTED IDENTITY ATTRIBUTES:")
    print(f"  • Full Name        : {ext.get('name') or 'N/A'}")
    print(f"  • Document Number  : {ext.get('document_number') or 'N/A'}")
    print(f"  • Date of Birth    : {ext.get('dob') or 'N/A'}")
    print(f"  • Gender           : {ext.get('gender') or 'N/A'}")
    print(f"  • Checksums Valid  : {ext.get('checksums_valid')}")

    # Forensics & ELA
    forensics = result.get("forensics", {})
    print("-" * 65)
    print("FORENSIC COMPRESSION & BIOMETRIC ANALYSIS:")
    print(f"  • ELA Anomaly Score: {forensics.get('ela_anomaly_score') * 100:.1f}%")
    print(f"  • Tampering Flagged: {forensics.get('tampering_detected')}")
    print(f"  • Faces Detected   : {forensics.get('face_count')}")
    print(f"  • QR Code Detected : {forensics.get('qr_detected')}")

    # Gemini Multimodal AI Audit
    ai = result.get("ai_analysis", {})
    if ai.get("triggered"):
        print("-" * 65)
        print("GOOGLE GEMINI MULTIMODAL AI FINDINGS:")
        for finding in ai.get("findings", []):
            print(f"  [AI] {finding}")

    # Explanation factors
    exp = result.get("explanation", {})
    if exp.get("negative_factors"):
        print("-" * 65)
        print("RISK FACTORS DETECTED:")
        for nf in exp.get("negative_factors"):
            print(f"  [!] {nf}")

    # Legal Audit Hash
    print("-" * 65)
    print(f"Section 65B Audit SHA-256 : {result.get('audit_hash')}")
    print("=" * 65 + "\n")

    return result


if __name__ == "__main__":
    print("=" * 65)
    print("      VERIDOC Sovereign Document Verification API Client")
    print("=" * 65)

    if not check_server_health():
        sys.exit(1)

    # Determine specimen path from argument or default sample
    if len(sys.argv) > 1:
        target_doc = sys.argv[1]
    else:
        # Check standard sample locations
        candidates = [
            "dataset/AADHAAR0380.jpg",
            "dataset/specimen_genuine_aadhaar.png",
            "dataset/specimen_tampered_aadhaar.png"
        ]
        target_doc = next((c for c in candidates if os.path.exists(c)), None)

    if target_doc and os.path.exists(target_doc):
        verify_document(target_doc, force_deep_ai=False)
    else:
        print("\nNo default document found. Run:")
        print("  python api_client_example.py <path_to_image_or_pdf>")
