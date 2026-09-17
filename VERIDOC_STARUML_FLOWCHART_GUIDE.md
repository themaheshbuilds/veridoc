# VERIDOC — StarUML Technical Activity Diagram (Flowchart)
## Official UML Process Flow for Slide 2 & Slide 3 (Smart India Hackathon)

> **Diagram Type**: UML Activity Diagram (Standard Engineering Flowchart with Swimlanes)  
> **Tool Compatibility**: StarUML, PlantUML, Visual Paradigm, Enterprise Architect, Mermaid.js  
> **Source Code**: [`VERIDOC_ACTIVITY_FLOWCHART.puml`](file:///c:/Users/vilas/Desktop/SIH26188/VERIDOC/VERIDOC_ACTIVITY_FLOWCHART.puml)  

---

## 1. Interactive Mermaid Activity Flowchart

```mermaid
graph TD
    %% Initial Node
    StartNode((●)) --> Ingress["Document Ingress<br/><i>(Kiosk Upload or Govt Web Portal REST API)</i>"]

    %% Preprocessing & Quality
    Ingress --> Rasterize["PyMuPDF Vector Rasterization<br/>& Laplacian Sharpness Filter"]
    Rasterize --> QualityDecision{"Is Image Blurry<br/>or Glare-Damaged?"}

    QualityDecision -- "Yes (Degraded)" --> RejectScan["❌ Reject Scan & Prompt User to Rescan"]
    RejectScan --> EndNode1(((◉)))

    QualityDecision -- "No (Legible)" --> ForkBar[["═══════ FORK: PARALLEL EDGE FORENSICS ═══════"]]

    %% Parallel Processing Branches
    ForkBar --> TamperBranch["<b>Engine A: Tamper Forensics</b><br/>• 8x8 DCT Compression ELA<br/>• Biometric Face Cut & Glue Check<br/>• Circular Stamp Discontinuity"]
    ForkBar --> SymbologyBranch["<b>Engine B: Dual Symbology</b><br/>• 1D Barcodes: Code 128 / 39<br/>• 2D Matrix: QR Code & DataMatrix<br/>• UIDAI Offline RSA-2048 Decrypt"]
    ForkBar --> OCRBranch["<b>Engine C: Two-Tier OCR</b><br/>• Fast Local OCR (<300ms)<br/>• Fallback to Local Multimodal AI<br/>  <i>(Qwen2-VL/TrOCR for Faded Text)</i>"]

    TamperBranch --> JoinBar[["═══════ JOIN: CONVERGENCE ═══════"]]
    SymbologyBranch --> JoinBar
    OCRBranch --> JoinBar

    %% Deterministic Mathematical Check
    JoinBar --> ChecksumGate["<b>Mathematical Checksum Gate</b><br/>• Verhoeff D5 Dihedral Group (Aadhaar)<br/>• ICAO 9303 Modulo-10 [7,3,1] (Passport)"]

    ChecksumGate --> MathDecision{"Are Checkdigits<br/>Valid?"}
    MathDecision -- "No (Altered/Fake)" --> FlagCounterfeit["⚠️ Flag Document as Forged / Altered"]
    FlagCounterfeit --> FinalVerdict

    MathDecision -- "Yes (Authentic)" --> OnlineDecision{"Is Network & API Setu<br/>Gateway Available?"}

    %% DPI Cloud Bridge
    OnlineDecision -- "Yes (Connected)" --> APISetuQuery["<b>🏛️ API Setu National Gateway</b><br/>• Query MoRTH Sarathi (Driving License)<br/>• Query CBDT / NSDL (PAN Cards)<br/>• Query DigiLocker / NAD (Degrees)<br/>• Jaro-Winkler String Cross-Matching"]
    OnlineDecision -- "No (Air-Gapped)" --> OfflineProceed["<b>🔒 100% Offline Air-Gapped Mode</b><br/>Finalize Local Forensic Ledger"]

    APISetuQuery --> FinalVerdict
    OfflineProceed --> FinalVerdict

    %% Output Synthesis
    FinalVerdict["<b>Sovereign Forensic Synthesis</b><br/>• Generate Tamper Heatmap & Anomaly Overlays<br/>• Synthesize Executive Plain-English Reasoning<br/>• Generate SHA-256 Hashed BSA 2023 Sec 63 Certificate<br/>• Append Block to Local Immutable SQLite Ledger"]

    FinalVerdict --> DeliverResults["Deliver Structured JSON & PDF Certificate<br/><i>(To Officer Screen / Web Portal / Court)</i>"]
    DeliverResults --> EndNode2(((◉)))

    %% Styling
    classDef startEnd fill:#0f172a,stroke:#0f172a,color:#ffffff;
    classDef quality fill:#fef08a,stroke:#ca8a04,stroke-width:2px,color:#0f172a;
    classDef reject fill:#fee2e2,stroke:#ef4444,stroke-width:2px,color:#991b1b;
    classDef success fill:#dcfce7,stroke:#22c55e,stroke-width:2px,color:#166534;
    classDef forkJoin fill:#0284c7,stroke:#0369a1,stroke-width:3px,color:#ffffff;
    classDef proc fill:#f0f9ff,stroke:#0284c7,stroke-width:1.5px,color:#0f172a;

    class StartNode,EndNode1,EndNode2 startEnd;
    class QualityDecision,MathDecision,OnlineDecision quality;
    class RejectScan,FlagCounterfeit reject;
    class ForkBar,JoinBar forkJoin;
    class Ingress,Rasterize,TamperBranch,SymbologyBranch,OCRBranch,ChecksumGate,APISetuQuery,OfflineProceed,FinalVerdict,DeliverResults proc;
```

---

## 2. ASCII Representation of the StarUML Activity Flowchart

```
(●) START
 │
 ▼
[ Document Ingress: Kiosk Upload OR Govt Portal REST API (/api/verify) ]
 │
 ▼
[ PyMuPDF Vector Page Rasterization & Laplacian Variance Sharpness Check ]
 │
 ├──► < Is Image Blurry or Glare-Damaged? >
 │        ├── (Yes) ──► [ ❌ Reject Scan & Prompt Rescan ] ──► (◉) STOP
 │        └── (No)
 │
 ▼
═══════════════════════ FORK: PARALLEL EDGE FORENSICS ═══════════════════════
 │                             │                             │
 ▼                             ▼                             ▼
[ ENGINE A: TAMPER CV ]       [ ENGINE B: SYMBOLOGY ]       [ ENGINE C: TWO-TIER OCR ]
• 8x8 DCT Compression ELA     • 1D Barcodes (Code 128)      • Tier 1: Local Fast OCR
• Portrait Edge Cut/Glue      • 2D Matrix (QR/DataMatrix)   • Tier 2: Local AI OCR
• Stamp Circle Discontinuity  • UIDAI RSA-2048 Decrypt        (Qwen2-VL / TrOCR)
 │                             │                             │
 └─────────────────────────────┼─────────────────────────────┘
                               │
                               ▼
═══════════════════════ JOIN: CONVERGENCE ═══════════════════════════════════
                               │
                               ▼
[ Deterministic Checksums: Verhoeff D5 (Aadhaar) & ICAO 9303 (Passport) ]
                               │
 ├──► < Are Checkdigits Mathematically Valid? >
 │        ├── (No) ──► [ ⚠️ Flag as Counterfeit / Altered ID ] ──┐
 │        └── (Yes)                                             │
 │                                                              │
 ▼                                                              │
 ├──► < Is Network & API Setu Connected? >                       │
 │        ├── (Yes: Online)                                     │
 │        │     ▼                                               │
 │        │   [ Query api.apisetu.gov.in: MoRTH / CBDT / NAD ]  │
 │        │   [ Jaro-Winkler Matching: Card vs Live Registry ]  │
 │        │     │                                               │
 │        └── (No: Air-Gapped) ─────────────────────────────────┤
 │              ▼                                               │
 │            [ Finalize Local Offline Sovereign Ledger ]       │
 │              │                                               │
 └──────────────┴───────────────────────────────────────────────┘
                               │
                               ▼
[ Sovereign Forensic Synthesis & Executive Anomaly Report ]
[ Generate SHA-256 Hashed Section 63 BSA 2023 Court Certificate ]
[ Append Cryptographic Digest to Local Immutable SQLite Ledger ]
 │
 ▼
[ Deliver Output: Structured JSON Payload & Tamper-Evident Court PDF ]
 │
 ▼
(◉) STOP
```

---

## 3. How to Import and Open this Flowchart in StarUML

1. Open **StarUML**.
2. Click **Tools $\longrightarrow$ PlantUML $\longrightarrow$ Import PlantUML...**
3. Browse and select: [`VERIDOC_ACTIVITY_FLOWCHART.puml`](file:///c:/Users/vilas/Desktop/SIH26188/VERIDOC/VERIDOC_ACTIVITY_FLOWCHART.puml).
4. StarUML will automatically create an **Activity Diagram** with:
   - Initial & Final Nodes (black circle and bullseye).
   - Swimlane partitions (`User Layer`, `VERIDOC Edge Core`, `Government DPI`, `Judicial Ledger`).
   - Fork and Join horizontal bars representing parallel execution.
   - Decision diamonds for quality gates and checksum checks.
   - Beautiful rounded action states with transition arrows.
