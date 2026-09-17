# 🛡️ VERIDOC PROTOTYPE: Sovereign Document Forensics & Verification Suite

> **Smart India Hackathon (SIH26188)**  
> **Offline-First Multi-Modal Verification, Cryptographic PKI & Anti-Tampering Engine**  
> **Statutory Standards**: Section 65B of the Indian Evidence Act, 1872 & Section 63 of the Bharatiya Sakshya Adhiniyam, 2023 (BSA)

---

## 🚀 1-Click Quickstart

### Method 1: Windows Batch Launcher (Recommended)
Simply **double-click** `RUN_PROTOTYPE.bat` in this folder.
- Automatically verifies Python dependencies.
- Starts the sovereign FastAPI uvicorn engine on `http://127.0.0.1:8000`.
- Automatically opens your default web browser to the verification cockpit.

### Method 2: PowerShell Launcher
```powershell
.\RUN_PROTOTYPE.ps1
```

### Method 3: Manual Terminal Launch
```bash
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

---

## 📁 Prototype Structure

```
VERIDOC PROTOTYPE/
├── RUN_PROTOTYPE.bat                 # 1-Click Windows Batch Launcher
├── RUN_PROTOTYPE.ps1                 # PowerShell Launcher
├── START_OFFLINE_BROWSER.bat         # Direct browser preview launcher
├── README.md                         # This Quickstart & Demonstration Guide
├── document.md                       # Comprehensive Technical Architecture & Whitepaper
├── VERIDOC_JURY_DEFENSE_MANUAL.md    # 268-Question Exhaustive Defense Dossier
├── generate_dataset.py               # Deterministic benchmark dataset generator
│
├── frontend/                         # Zero-framework high-speed client cockpit
│   ├── index.html                    # Central Operations Hub & Launcher
│   ├── verify.html                   # Interactive Verification Cockpit
│   ├── verified.html                 # Analytics & Cryptographic Ledger
│   ├── api.html                      # API Access, Key Generator & Sandbox
│   ├── history.html                  # Searchable Audit Trail
│   ├── qr.html                       # Sovereign 2D Barcode Engine
│   ├── styles.css                    # Terra Organic Design System (Responsive & Touch)
│   ├── app.js                        # Client state machine, telemetry & forensics UI
│   └── favicon.svg                   # Vector brand seal
│
├── backend/                          # Asynchronous sovereign Python engine
│   ├── requirements.txt              # Core dependencies (FastAPI, OpenCV, Cryptography)
│   └── app/
│       ├── main.py                   # App entrypoint & static route mounting
│       ├── api/routes.py             # High-throughput REST API endpoints (/api/v1)
│       ├── core/config.py            # System configuration & environment settings
│       ├── db/                       # SQLite async ORM & Section 65B Merkle ledger
│       ├── schemas/                  # Strict Pydantic models & validation schemas
│       └── services/
│           ├── verifier.py           # Multi-modal orchestration & decision engine
│           ├── checksum_validator.py # Verhoeff Dihedral-5 & ICAO 9303 math
│           ├── forensics.py          # Error Level Analysis (ELA) recompression
│           ├── image_preprocessor.py # CLAHE, deskewing & 4-point quadrilateral warp
│           ├── ocr_engine.py         # Local morphological OCR & Gemini vision fallback
│           ├── qr_scanner.py         # zxing-cpp 2048-bit BigInteger & RSA PKI
│           └── quality_assessor.py   # Laplacian blur variance optical triage gate
│
└── dataset/                          # Controlled ground-truth adversarial specimens
    ├── specimen_genuine_aadhaar.png  # Authentic Aadhaar (Verhoeff check digit valid)
    ├── specimen_tampered_aadhaar.png # Frankenstein attack (spliced name vs signed QR)
    ├── specimen_genuine_pan.png      # Conforming CBDT structure [A-Z]{5}[0-9]{4}[A-Z]
    ├── specimen_tampered_pan.png     # Impossible date (31/02/1985) & invalid entity 'X'
    ├── specimen_genuine_passport.png # ICAO Doc 9303 Type-3 MRZ cyclic 7-3-1 checksums
    └── specimen_blurred_document.png # Degraded scan triggering optical quality halt
```

---

## 🧪 Testing with Benchmark Specimens (`dataset/`)

Once the web cockpit is running at **`http://127.0.0.1:8000/verifydocuments`**, test these specimens:

| Specimen File | Injected Forensic Vector | Expected System Verdict | Expected Risk Score |
| :--- | :--- | :--- | :--- |
| `specimen_genuine_aadhaar.png` | Statutorily valid Verhoeff parity, matching QR envelope | **`CLEAR / AUTHENTIC`** | **`0.0 / 100`** |
| `specimen_tampered_aadhaar.png` | **Frankenstein Splicing**: Name altered to "Vikram Malhotra", UID corrupted, QR belongs to "Ananya Sharma" | **`HIGH RISK / SUSPICIOUS`** | **`85.0 / 100`** |
| `specimen_genuine_pan.png` | Valid CBDT entity `P` (Individual), matching surname initial | **`CLEAR / AUTHENTIC`** | **`0.0 / 100`** |
| `specimen_tampered_pan.png` | Impossible calendar date (`31/02/1985`), illegal entity `X` | **`HIGH RISK / SUSPICIOUS`** | **`85.0 / 100`** |
| `specimen_genuine_passport.png` | Valid ICAO 9303 cyclic modulo-10 weights `[7, 3, 1]` | **`CLEAR / AUTHENTIC`** | **`0.0 / 100`** |
| `specimen_blurred_document.png` | Severe blur (variance < 25.0) | **`INCONCLUSIVE / REJECTED`** | **Gated Out** |

---

## 📱 Multi-Device & Mobile Responsiveness

- **Desktop (>= 992px)**: Full horizontal glass navigation pill deck.
- **Tablet & Mobile (<= 991px)**: Single compact top header with the **3-dots menu button (`more_vert`)**.
- **Touch Targets**: Minimum 44px x 44px touch targets compliant with WCAG 2.1 AAA for rugged field tablets and border kiosks.

---

## ⚖️ Legal Evidentiary Compliance

Every verification event computes a cryptographic SHA-256 Merkle block hash:
$$\text{Block Hash} = \text{SHA-256}(\text{Index} + \text{Timestamp} + \text{Payload Digest} + \text{Previous Hash})$$

Clicking **"Section 65B Certificate"** on any processed record renders a printable legal evidence certificate compliant with:
1. **Section 65B of the Indian Evidence Act, 1872**
2. **Section 63 of the Bharatiya Sakshya Adhiniyam, 2023 (BSA)**

---

## 📚 Essential Reading for Evaluators & Jury

1. **[`document.md`](document.md)**: The definitive 14-section Technical Whitepaper & Architectural Blueprint.
2. **[`VERIDOC_JURY_DEFENSE_MANUAL.md`](VERIDOC_JURY_DEFENSE_MANUAL.md)**: 268-Question Exhaustive Defense Dossier covering all 18 evaluation rounds and the 13 Final Psycho-Jury trap questions.
