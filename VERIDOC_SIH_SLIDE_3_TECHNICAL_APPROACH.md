# SMART INDIA HACKATHON 2025 / 2026 — OFFICIAL IDEA SUBMISSION TEMPLATE
## SLIDE 3: TECHNICAL APPROACH & ARCHITECTURE (EXACT PPT COPY-PASTE)

---

### [TOP HEADER]
* **Top-Left Oval**: `VERIDOC`
* **Slide Title**: **TECHNICAL APPROACH**
* **Top-Right Logo**: Smart India Hackathon 2025 / 2026

---

### [COMPACT FLOWCHART (SMALL VERSION FOR PPT SLIDE 3)]

```
                       ┌──────────────────────────────────────────────┐
                       │          1. Citizen Document Ingress         │
                       │    (Kiosk Upload / Govt Web Portal API)      │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │      2. Quality Gate (Laplacian Filter)      │
                       │     (Rejects Blurry or Glare-Damaged Scans)  │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │        3. Parallel Edge Forensics Core       │
                       │ • Tamper ELA (8x8 DCT) • 1D/2D Barcodes & QR │
                       │ • Fast Local OCR (AI Fallback for Faded Text)│
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │       4. Mathematical Checksum Gate          │
                       │ (Verhoeff D5 for Aadhaar & ICAO for Passport)│
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │     5. API Setu Bridge (When Connected)      │
                       │ (Queries Parivahan Sarathi / CBDT / DigiLock)│
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │       6. Output: BSA 2023 Sec 63 PDF         │
                       │ (Certified Legal Proof + SHA-256 Hash Ledger)│
                       └──────────────────────────────────────────────┘
```

---

### [DETAILED SYSTEM ARCHITECTURE (FOR REPORT / DEEP DEFENSE)]

```
                       ┌──────────────────────────────────────────────┐
                       │          CITIZEN DOCUMENT INGRESS            │
                       │ • Govt Portals (ePass, eDistrict via API)    │
                       │ • Field Officers & Border Kiosks (Upload UI) │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                      LAYER 1: PREPROCESSING & QUALITY GATE                             │
 │  • PyMuPDF (fitz) Server-Side Vector Rasterization & Base64 Stream                     │
 │  • OpenCV Laplacian Variance Sharpness Filter (Rejects blurry/glare scans)             │
 │  • Multi-Scale CLAHE (Contrast Limiting) & 4-Point Homography Perspective Deskew       │
 └────────────────────────────────────┬───────────────────────────────────────────────────┘
                                      │
                                      ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                    LAYER 2: PARALLEL FORENSIC & ANALYSIS ENGINES                       │
 ├────────────────────────────┬────────────────────────────┬──────────────────────────────┤
 │  [ENGINE A: TAMPER CV]     │ [ENGINE B: DUAL SYMBOLOGY] │ [ENGINE C: TWO-TIER OCR]     │
 │ • 8x8 DCT Error Level      │ • zxing-cpp Multi-Barcode  │ • Tier 1: Fast Local OCR     │
 │   Analysis (ELA) Heatmap   │ • 1D Barcodes: Code 128/39 │   (<300ms on-device CPU)     │
 │ • Biometric Portrait Edge  │ • 2D Matrix: QR/DataMatrix │ • Tier 2: Local AI OCR       │
 │   Cut & Glue Detection     │ • UIDAI RSA-2048 Secure    │   (Qwen2-VL/TrOCR for faded  │
 │ • Circular Stamp Breakage  │   QR Decryption (Offline)  │   vernacular Hindi/Telugu)   │
 └─────────────┬──────────────┴─────────────┬──────────────┴──────────────┬───────────────┘
               │                            │                             │
               └──────────────────────┬─────┴─────────────────────────────┘
                                      │
                                      ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                 LAYER 3: DETERMINISTIC MATHEMATICAL VALIDATION                         │
 │  • Verhoeff Dihedral Group (D5) Algorithm: Validates 12-digit Aadhaar math offline     │
 │  • ICAO Doc 9303 Modulo-10 [7, 3, 1] Algorithm: Validates Passport Machine Readable Zone│
 │  • CBDT Alphanumeric Regex & Tax Entity Index Rules (Zero AI Guesswork)                │
 └────────────────────────────────────┬───────────────────────────────────────────────────┘
                                      │
                    Is Network / API Setu Gateway Available?
                          ├──► NO (Air-Gapped Border Post) ──► Finalize Local Evidence
                          │
                          └──► YES (Connected Kiosk / Portal)
                                      │
                                      ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │              LAYER 4: FEDERATED GOVERNMENT GATEWAY (API SETU BRIDGE)                   │
 │  • Secure TLS 1.3 Gateway to `api.apisetu.gov.in` (Digital India / MeitY / NIC)        │
 │  • Live Master Registry Cross-Referencing:                                             │
 │    - MoRTH Sarathi (Driving Licenses)    - CBDT / NSDL (PAN Cards)                     │
 │    - DigiLocker / NAD (Degrees/Marks)    - MoRTH Vahan (Vehicle RC)                    │
 │  • Jaro-Winkler String Distance Matching: Card Data vs Live Government Master Record   │
 └────────────────────────────────────┬───────────────────────────────────────────────────┘
                                      │
                                      ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │               LAYER 5: AUDIT SYNTHESIS & LEGAL EVIDENCE GENERATION                     │
 │  • Sovereign Multimodal AI Auditor: Synthesizes ELA score + OCR + Registry matches     │
 │  • Sequential Cryptographic Block Ledger: SHA-256 chained audit hashes (FIPS 140-3)    │
 │  • Section 63 Bharatiya Sakshya Adhiniyam (BSA) 2023 Electronic Evidence Certificate   │
 └────────────────────────────────────┬───────────────────────────────────────────────────┘
                                      │
                                      ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                              SYSTEM DELIVERABLES & OUTPUTS                             │
 ├────────────────────────────┬────────────────────────────┬──────────────────────────────┤
 │ 1. Tamper Anomaly Heatmap  │ 2. Extracted Structured    │ 3. Court-Admissible BSA 2023 │
 │    (Spliced Photo Flagged) │    Identity Data (JSON)    │    Section 63 Certificate    │
 └────────────────────────────┴────────────────────────────┴──────────────────────────────┘
```

---

### [RIGHT COLUMN (35% WIDTH) — TECH STACK FOR SLIDE]

#### **Tech Stack (Logos / Icons to place in grid):**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                               TECH STACK                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  CORE LANGUAGES & RUNTIME:                                                  │
│  • Python 3.11          • JavaScript (ES6+)                                 │
│  • HTML5                • CSS3 (Vanilla Institutional UI)                   │
│                                                                             │
│  BACKEND & MICROSERVICES:                                                   │
│  • FastAPI              • Uvicorn (Asynchronous ASGI Server)                │
│  • Pydantic v2          • Python httpx (TLS 1.3 Client)                     │
│                                                                             │
│  COMPUTER VISION & IMAGE FORENSICS:                                         │
│  • OpenCV (cv2)         • PyMuPDF (fitz Vector Rasterizer)                  │
│  • NumPy                • SciPy (DCT-II Quantization)                       │
│                                                                             │
│  SYMBOLOGY & SCANNING:                                                      │
│  • zxing-cpp            • pyzbar                                            │
│  • UIDAI RSA Decompressor                                                   │
│                                                                             │
│  ON-PREMISE AI & OCR ENGINES:                                               │
│  • Windows Media OCR    • Microsoft TrOCR (Indic OCR)                       │
│  • Qwen2-VL (Local INT4)• ONNX Runtime / Ollama                             │
│                                                                             │
│  SOVEREIGN DPI & GOVERNMENT INTEGRATION:                                    │
│  • API Setu Gateway     • DigiLocker / NAD                                  │
│  • MoRTH Sarathi        • CBDT Income Tax Portal                            │
│                                                                             │
│  DATABASE, SECURITY & LEGAL:                                                │
│  • SQLite (Edge Ledger) • hashlib (SHA-256 FIPS 140-3)                      │
│  • BSA 2023 Section 63  • Docker / Standalone Launcher                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### [HOW TO EXPLAIN SLIDE 3 TO THE JURY (PITCH SCRIPT)]:

1. **Start with the Ingress**:  
   *"Judges, our technical approach is designed as a modular 5-layer pipeline. It supports dual ingress: citizen documents can arrive programmatically via government portals like e-Pass using our REST API, or manually via border kiosks."*
2. **Explain the Processing (Layers 1 to 3)**:  
   *"In Layer 1 and 2, we execute edge forensics entirely on standard CPU. PyMuPDF renders vector pages without UI blackouts; OpenCV Laplacian filters reject blurry scans early; our 8×8 DCT Error Level Analysis isolates spliced photos and altered fonts in under 50 milliseconds; while native zxing handles 1D barcodes and 2D QR codes simultaneously.*
   *In Layer 3, we execute zero-guesswork mathematical check digits—the official UIDAI Verhoeff D5 dihedral group for Aadhaar and ICAO 9303 for Passports."*
3. **Highlight the Sovereign Cloud Bridge & Legal Output (Layers 4 and 5)**:  
   *"When connectivity is present, Layer 4 reaches out to MeitY's API Setu (apisetu.gov.in) to cross-reference with live Parivahan Sarathi and CBDT master records, defeating the Stolen Identity Trap.*
   *Finally, Layer 5 synthesizes all findings and signs an automated SHA-256 electronic evidence certificate under Section 63 of Bharatiya Sakshya Adhiniyam, 2023, making the verdict immediately admissible in court."*
4. **Point to the Tech Stack**:  
   *"Our entire stack is built on proven open-source technologies: Python 3.11, FastAPI, OpenCV, PyMuPDF, zxing-cpp, SQLite, and ONNX Runtime—ensuring ₹0.00 license costs, complete data sovereignty, and sub-2.5-second execution."*
