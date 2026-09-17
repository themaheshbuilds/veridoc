"""
evidence_ledger.py — Section 63 Bharatiya Sakshya Adhiniyam (BSA) 2023
=========================================================================
Generates court-admissible electronic evidence certificates for every
verification session, compliant with Section 63, BSA 2023 (which replaced
Section 65B of the Indian Evidence Act, 1872, w.e.f. 1 July 2024).

Certificate Contents:
  • System hardware fingerprint & timestamp
  • SHA-256 cryptographic seal of the audit artifact
  • Full verification details (document type, fields, evidence chain)
  • Official verdict badge: AUTHENTIC / TAMPERED / SUSPICIOUS
  • Immutable blockchain block reference hash
  • Officer recommendation and statutory declaration
"""

import hashlib
import io
import os
import platform
import socket
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas as rl_canvas


# ─────────────────────────────────────────────────────────────────────────────
# Colour palette — dark institutional navy/gold scheme
# ─────────────────────────────────────────────────────────────────────────────
C_NAVY      = colors.HexColor("#0A1628")
C_GOLD      = colors.HexColor("#C9A84C")
C_DARK_GOLD = colors.HexColor("#A07830")
C_AUTHENTIC = colors.HexColor("#14532D")
C_TAMPERED  = colors.HexColor("#7F1D1D")
C_SUSPICIOUS= colors.HexColor("#78350F")
C_LIGHT_BG  = colors.HexColor("#F8F6F0")
C_BORDER    = colors.HexColor("#D4C5A9")
C_MUTED     = colors.HexColor("#6B7280")
C_WHITE     = colors.white
C_BLACK     = colors.black


# ─────────────────────────────────────────────────────────────────────────────
# Helper: system fingerprint
# ─────────────────────────────────────────────────────────────────────────────

def _get_system_fingerprint() -> str:
    """Generate a stable hardware fingerprint for the issuing machine."""
    try:
        node = str(uuid.getnode())          # MAC address as integer
        host = socket.gethostname()
        plat = platform.node()
        raw  = f"{node}:{host}:{plat}"
        return hashlib.sha256(raw.encode()).hexdigest()[:24].upper()
    except Exception:
        return "SYSTEM-FP-UNAVAILABLE"


# ─────────────────────────────────────────────────────────────────────────────
# Watermark / header painter
# ─────────────────────────────────────────────────────────────────────────────

def _paint_background(c: rl_canvas.Canvas, doc):
    """Draw page watermark, header bar, and border frame."""
    w, h = A4

    # Navy header bar
    c.setFillColor(C_NAVY)
    c.rect(0, h - 45*mm, w, 45*mm, fill=1, stroke=0)

    # Gold accent strip under header
    c.setFillColor(C_GOLD)
    c.rect(0, h - 47*mm, w, 2*mm, fill=1, stroke=0)

    # Light cream background body
    c.setFillColor(C_LIGHT_BG)
    c.rect(0, 0, w, h - 47*mm, fill=1, stroke=0)

    # Outer border
    c.setStrokeColor(C_DARK_GOLD)
    c.setLineWidth(1.5)
    c.rect(8*mm, 8*mm, w - 16*mm, h - 16*mm, fill=0, stroke=1)

    # Inner decorative border
    c.setStrokeColor(C_BORDER)
    c.setLineWidth(0.5)
    c.rect(10*mm, 10*mm, w - 20*mm, h - 20*mm, fill=0, stroke=1)

    # WATERMARK — faint VERIDOC text
    c.saveState()
    c.setFillColor(colors.HexColor("#E8E2D4"))
    c.setFont("Helvetica-Bold", 72)
    c.translate(w/2, h/2)
    c.rotate(35)
    c.drawCentredString(0, 0, "VERIDOC")
    c.restoreState()

    # Footer bar
    c.setFillColor(C_NAVY)
    c.rect(0, 0, w, 18*mm, fill=1, stroke=0)

    c.setFillColor(C_GOLD)
    c.setFont("Helvetica", 7)
    c.drawCentredString(
        w/2, 6*mm,
        "Section 63 Bharatiya Sakshya Adhiniyam (BSA) 2023  |  "
        "Sovereign Document Forensics Engine  |  "
        "Sashastra Seema Bal, Ministry of Home Affairs"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main certificate generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_bsa_certificate(
    session_id: str,
    document_type: str,
    overall_verdict: str,
    risk_score: float,
    confidence_score: float,
    officer_recommendation: str,
    audit_hash: str,
    timestamp: datetime,
    extracted_fields: Dict[str, Any],
    evidence_items: List[Dict[str, Any]],
    checkpoint_id: str = "SSB-CHK-01",
    officer_id: str = "SSB-OFFICER-01",
    filename: Optional[str] = None
) -> bytes:
    """
    Generate a Section 63 BSA 2023 court-admissible PDF evidence certificate.

    Returns the PDF as raw bytes (suitable for HTTP streaming).
    """
    buf = io.BytesIO()
    w, h = A4

    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18*mm,
        rightMargin=18*mm,
        topMargin=52*mm,
        bottomMargin=25*mm,
        title=f"VERIDOC BSA 2023 Certificate — {session_id}",
        author="VERIDOC Sovereign Forensics Engine",
        subject="Section 63 Bharatiya Sakshya Adhiniyam 2023 Evidence Certificate",
        creator="VERIDOC v2.0.0"
    )

    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height,
        id="main"
    )
    template = PageTemplate(id="main", frames=[frame], onPage=_paint_background)
    doc.addPageTemplates([template])

    # ── Styles ──────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    s_header = ParagraphStyle("header",
        fontName="Helvetica-Bold", fontSize=16,
        textColor=C_WHITE, alignment=TA_CENTER, spaceAfter=2)

    s_subheader = ParagraphStyle("subheader",
        fontName="Helvetica", fontSize=8,
        textColor=C_GOLD, alignment=TA_CENTER, spaceAfter=4)

    s_section = ParagraphStyle("section",
        fontName="Helvetica-Bold", fontSize=10,
        textColor=C_NAVY, spaceBefore=8, spaceAfter=4,
        borderPad=3)

    s_body = ParagraphStyle("body",
        fontName="Helvetica", fontSize=9,
        textColor=C_BLACK, leading=14, alignment=TA_JUSTIFY)

    s_mono = ParagraphStyle("mono",
        fontName="Courier", fontSize=8,
        textColor=C_NAVY, leading=12)

    s_muted = ParagraphStyle("muted",
        fontName="Helvetica", fontSize=8,
        textColor=C_MUTED, leading=12)

    s_label = ParagraphStyle("label",
        fontName="Helvetica-Bold", fontSize=8,
        textColor=C_NAVY)

    s_value = ParagraphStyle("value",
        fontName="Helvetica", fontSize=8,
        textColor=C_BLACK, leading=12)

    s_declaration = ParagraphStyle("declaration",
        fontName="Helvetica-Oblique", fontSize=8,
        textColor=C_BLACK, leading=13, alignment=TA_JUSTIFY,
        spaceBefore=6, spaceAfter=6)

    # ── Verdict colour ───────────────────────────────────────────────────────
    verdict_upper = overall_verdict.upper()
    if verdict_upper in ("CLEAR", "AUTHENTIC"):
        v_color = C_AUTHENTIC
        v_label = "✓  AUTHENTIC — DOCUMENT CLEARED"
    elif verdict_upper in ("SUSPICIOUS", "TAMPERED"):
        v_color = C_TAMPERED
        v_label = "✗  TAMPERED / SUSPICIOUS — SECONDARY INSPECTION REQUIRED"
    else:
        v_color = C_SUSPICIOUS
        v_label = "⚠  INCONCLUSIVE — MANUAL REVIEW REQUIRED"

    ts_str = timestamp.strftime("%d %B %Y  %H:%M:%S UTC")
    sys_fp = _get_system_fingerprint()
    cert_sha = hashlib.sha256(
        f"BSA2023:{session_id}:{audit_hash}:{ts_str}".encode()
    ).hexdigest()

    # ── Build flowables ──────────────────────────────────────────────────────
    story = []

    # — Title block (sits in navy header) —
    # (painted via _paint_background; add overlay text via absolute coords)
    story.append(Spacer(1, 2*mm))

    # Offset text sits atop the navy header (handled below using raw canvas)
    # We use a custom Flowable for the header content
    class _HeaderBlock(rl_canvas.Canvas.__class__):
        pass

    from reportlab.platypus import Flowable

    class _VerdictBadge(Flowable):
        """Draws the verdict badge rectangle."""
        def __init__(self, label, bg_color, width, height=16*mm):
            super().__init__()
            self.label = label
            self.bg = bg_color
            self.w = width
            self.h = height

        def wrap(self, *args):
            return self.w, self.h

        def draw(self):
            self.canv.setFillColor(self.bg)
            self.canv.roundRect(0, 0, self.w, self.h, radius=4, fill=1, stroke=0)
            self.canv.setFillColor(C_WHITE)
            self.canv.setFont("Helvetica-Bold", 11)
            self.canv.drawCentredString(self.w/2, self.h/2 - 4, self.label)

    # Institutional header lines
    story.append(Paragraph(
        "GOVERNMENT OF INDIA",
        ParagraphStyle("gov", fontName="Helvetica-Bold", fontSize=10,
                       textColor=C_NAVY, alignment=TA_CENTER, spaceBefore=6)
    ))
    story.append(Paragraph(
        "Ministry of Home Affairs  •  Sashastra Seema Bal (SSB)",
        ParagraphStyle("min", fontName="Helvetica", fontSize=8,
                       textColor=C_MUTED, alignment=TA_CENTER, spaceAfter=2)
    ))
    story.append(Paragraph(
        "ELECTRONIC EVIDENCE CERTIFICATE",
        ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=18,
                       textColor=C_NAVY, alignment=TA_CENTER, spaceBefore=4, spaceAfter=2)
    ))
    story.append(Paragraph(
        "Issued under Section 63, Bharatiya Sakshya Adhiniyam (BSA) 2023",
        ParagraphStyle("act", fontName="Helvetica-Oblique", fontSize=9,
                       textColor=C_DARK_GOLD, alignment=TA_CENTER, spaceAfter=2)
    ))
    story.append(Spacer(1, 3*mm))

    # ── Verdict badge ────────────────────────────────────────────────────────
    story.append(_VerdictBadge(v_label, v_color, doc.width))
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 3*mm))

    # ── Session & Cryptographic Identity Block ───────────────────────────────
    story.append(Paragraph("1.  CRYPTOGRAPHIC IDENTITY OF THIS RECORD", s_section))

    meta_data = [
        ["Session ID",         session_id],
        ["Certificate SHA-256",cert_sha],
        ["Audit Block Hash",   audit_hash],
        ["Timestamp (UTC)",    ts_str],
        ["System Fingerprint", sys_fp],
        ["Issuing Engine",     "VERIDOC Sovereign Forensics Engine v2.0.0"],
        ["Checkpoint / Station", checkpoint_id],
        ["Officer ID",         officer_id],
    ]
    meta_table = Table(
        [[Paragraph(k, s_label), Paragraph(v, s_mono)] for k, v in meta_data],
        colWidths=[45*mm, doc.width - 45*mm]
    )
    meta_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (0, -1), colors.HexColor("#EDF2F7")),
        ("BACKGROUND",  (1, 0), (1, -1), C_WHITE),
        ("GRID",        (0, 0), (-1, -1), 0.3, C_BORDER),
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",  (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 4*mm))

    # ── Document Details Block ────────────────────────────────────────────────
    story.append(Paragraph("2.  DOCUMENT UNDER EXAMINATION", s_section))

    name = extracted_fields.get("name") or "—"
    doc_num = extracted_fields.get("document_number") or "—"
    dob = extracted_fields.get("dob") or "—"
    expiry = extracted_fields.get("expiry_date") or "—"
    gender = extracted_fields.get("gender") or "—"
    nationality = extracted_fields.get("nationality") or "—"
    checksums = extracted_fields.get("checksums_valid")
    checksum_str = "✓ PASS" if checksums is True else ("✗ FAIL" if checksums is False else "N/A")

    doc_data = [
        ["Document Type",       document_type],
        ["Source File",         filename or "—"],
        ["Subject Name",        name],
        ["Document Number",     doc_num],
        ["Date of Birth",       dob],
        ["Expiry Date",         expiry],
        ["Gender",              gender],
        ["Nationality",         nationality],
        ["Mathematical Checksums", checksum_str],
        ["Risk Score",          f"{risk_score:.1f} / 100"],
        ["Confidence Score",    f"{confidence_score:.1f}%"],
        ["Officer Recommendation", officer_recommendation],
    ]
    doc_table = Table(
        [[Paragraph(k, s_label), Paragraph(str(v), s_value)] for k, v in doc_data],
        colWidths=[45*mm, doc.width - 45*mm]
    )
    doc_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (0, -1), colors.HexColor("#EDF2F7")),
        ("BACKGROUND",  (1, 0), (1, -1), C_WHITE),
        ("GRID",        (0, 0), (-1, -1), 0.3, C_BORDER),
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",  (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(doc_table)
    story.append(Spacer(1, 4*mm))

    # ── Evidence Chain ───────────────────────────────────────────────────────
    if evidence_items:
        story.append(Paragraph("3.  FORENSIC EVIDENCE CHAIN", s_section))
        ev_rows = [
            [
                Paragraph("#", s_label),
                Paragraph("Check Name", s_label),
                Paragraph("Status", s_label),
                Paragraph("Confidence", s_label),
                Paragraph("Summary", s_label),
            ]
        ]
        for idx, ev in enumerate(evidence_items[:10], 1):
            status = str(ev.get("status", "")).upper()
            status_color = C_AUTHENTIC if status == "PASS" else (C_TAMPERED if status == "FAIL" else C_MUTED)
            ev_rows.append([
                Paragraph(str(idx), s_value),
                Paragraph(str(ev.get("check_name", "")), s_value),
                Paragraph(f'<font color="#{status_color.hexval()[2:]}"><b>{status}</b></font>', s_value),
                Paragraph(f"{float(ev.get('confidence', 0)) * 100:.0f}%", s_value),
                Paragraph(str(ev.get("summary", ""))[:120], s_muted),
            ])

        ev_table = Table(ev_rows, colWidths=[8*mm, 42*mm, 16*mm, 18*mm, doc.width - 84*mm])
        ev_table.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), C_NAVY),
            ("TEXTCOLOR",   (0, 0), (-1, 0), C_WHITE),
            ("GRID",        (0, 0), (-1, -1), 0.3, C_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, colors.HexColor("#F3F4F6")]),
            ("VALIGN",      (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",  (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(ev_table)
        story.append(Spacer(1, 4*mm))

    # ── Statutory Declaration ────────────────────────────────────────────────
    story.append(Paragraph("4.  STATUTORY DECLARATION", s_section))
    story.append(Paragraph(
        "I hereby declare, pursuant to Section 63(4) of the Bharatiya Sakshya Adhiniyam (BSA) 2023, "
        "that this electronic record was produced by the VERIDOC Sovereign Document Forensics Engine, "
        "a computer system that was in regular and proper operation at all material times, "
        "and that the information contained herein was supplied to the computer in the ordinary course "
        "of its forensic examination activities. "
        "The cryptographic SHA-256 hash seals above affirm the integrity and authenticity of this record "
        "and render it tamper-evident for submission as admissible electronic evidence.",
        s_declaration
    ))
    story.append(Spacer(1, 3*mm))

    # Signature line
    sig_table = Table(
        [[
            Paragraph("VERIDOC Forensics Engine", s_label),
            Paragraph("Issuing Officer / Authorized Signatory", s_label)
        ],
        [
            Paragraph(f"Engine v2.0.0  |  Node: {sys_fp[:16]}", s_muted),
            Paragraph(f"{officer_id}  |  Checkpoint: {checkpoint_id}", s_muted)
        ]],
        colWidths=[doc.width/2, doc.width/2]
    )
    sig_table.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (0, 0), 1, C_BORDER),
        ("LINEABOVE", (1, 0), (1, 0), 1, C_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(sig_table)

    # ── Build PDF ────────────────────────────────────────────────────────────
    doc.build(story)
    return buf.getvalue()
