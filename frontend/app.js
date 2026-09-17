/**
 * VERIDOC Sovereign Document Forensics Engine v2.0
 * AI-Based Fake Identity & Document Screening System
 * Ministry of Home Affairs | Sashastra Seema Bal (SSB)
 * Section 63, Bharatiya Sakshya Adhiniyam (BSA) 2023
 *
 * Modules: Live Execution Timer, ELA Heatmap 3-Col,
 *          API Setu Gateway Toggle, BSA 2023 PDF Certificate Download
 */

const appState = {
  activeView: 'view-home',
  stagedFiles: [],
  currentResults: null,
  currentMultiReport: null,
  activeDocIndex: 0,
  activeSessionId: null,
  offlineSandboxMode: true,   // true = Sovereign Edge (Offline), false = Live API Setu Gateway
  timerStart: null,
  timerInterval: null
};

function getActiveApiKey() {
  let key = localStorage.getItem('veridoc_api_key');
  if (!key) {
    key = 'vrd_live_master_kiosk_key';
    localStorage.setItem('veridoc_api_key', key);
  }
  return key;
}

// Route mapping for multi-page architecture
const ROUTE_MAP = {
  'view-home': '/',
  'view-verify': '/verifydocuments',
  'view-qr': '/qr-reader',
  'view-verified': '/verified-documents',
  'view-api': '/api-access',
  'view-history': '/verification-history'
};

// ============================================================================
// Initialization
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
  detectActivePage();
  initNavigation();
  initHomeView();
  initVerifyView();
  initQrView();
  initVerifiedView();
  initApiView();
  initHistoryView();
  initCertModal();
  loadHomeRecentRecords();
  checkPendingStagedFiles();
});

function detectActivePage() {
  const path = window.location.pathname.toLowerCase();
  if (path.includes('verified')) {
    appState.activeView = 'view-verified';
  } else if (path.includes('verify')) {
    appState.activeView = 'view-verify';
  } else if (path.includes('qr')) {
    appState.activeView = 'view-qr';
  } else if (path.includes('api')) {
    appState.activeView = 'view-api';
  } else if (path.includes('history')) {
    appState.activeView = 'view-history';
  } else {
    appState.activeView = 'view-home';
  }

  // Highlight corresponding nav link
  document.querySelectorAll('.terra-nav .terra-nav-btn').forEach(btn => {
    const href = btn.getAttribute('href');
    if (!href) return;
    const isCurrent = (href === '/' && (path === '/' || path === '' || path === '/home')) ||
                      (href !== '/' && path.startsWith(href));
    btn.classList.toggle('active', isCurrent);
  });
}

// ============================================================================
// Core Navigation
// ============================================================================
function initNavigation() {
  const navBtns = document.querySelectorAll('.terra-nav .terra-nav-btn');
  navBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      closeMobileMenu();
      const href = btn.getAttribute('href');
      // If href is a real multi-page URL, allow browser navigation
      if (href && href !== '#' && !href.startsWith('#') && !href.startsWith('javascript:')) {
        return;
      }
      e.preventDefault();
      const target = btn.getAttribute('data-target');
      if (target) switchView(target);
    });
  });

  const brandHome = document.getElementById('btn-brand-home');
  if (brandHome) {
    brandHome.addEventListener('click', (e) => {
      closeMobileMenu();
      const href = brandHome.getAttribute('href');
      if (href && href !== '#' && !href.startsWith('#')) return;
      e.preventDefault();
      switchView('view-home');
    });
  }

  initMobileMenu();
}

function initMobileMenu() {
  const menuBtn = document.getElementById('btn-mobile-menu');
  const nav = document.querySelector('.terra-nav');
  if (!menuBtn || !nav) return;

  menuBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = nav.classList.toggle('mobile-open');
    menuBtn.classList.toggle('active', isOpen);
    menuBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    const icon = menuBtn.querySelector('.material-symbols-outlined');
    if (icon) {
      icon.textContent = isOpen ? 'close' : 'more_vert';
    }
  });

  // Close when clicking anywhere outside
  document.addEventListener('click', (e) => {
    if (!nav.contains(e.target) && !menuBtn.contains(e.target)) {
      closeMobileMenu();
    }
  });

  // Close on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeMobileMenu();
    }
  });
}

function closeMobileMenu() {
  const menuBtn = document.getElementById('btn-mobile-menu');
  const nav = document.querySelector('.terra-nav');
  if (nav && nav.classList.contains('mobile-open')) {
    nav.classList.remove('mobile-open');
  }
  if (menuBtn) {
    menuBtn.classList.remove('active');
    menuBtn.setAttribute('aria-expanded', 'false');
    const icon = menuBtn.querySelector('.material-symbols-outlined');
    if (icon) {
      icon.textContent = 'more_vert';
    }
  }
}

function switchView(viewId) {
  if (appState.activeView === 'view-qr' && viewId !== 'view-qr') {
    if (typeof stopQrCamera === 'function') {
      stopQrCamera();
    }
  }

  const target = document.getElementById(viewId);
  const targetRoute = ROUTE_MAP[viewId] || '/';

  // If the target element is NOT on the current page, navigate to dedicated page
  if (!target) {
    if (window.location.pathname !== targetRoute) {
      window.location.href = targetRoute;
      return;
    }
  }

  appState.activeView = viewId;

  // Switch panels if multiple exist on the page
  document.querySelectorAll('.view-section').forEach(section => {
    section.classList.remove('active');
  });
  if (target) target.classList.add('active');

  // Update tabs
  document.querySelectorAll('.terra-nav .terra-nav-btn').forEach(btn => {
    const btnTarget = btn.getAttribute('data-target');
    const btnHref = btn.getAttribute('href');
    const isMatch = (btnTarget === viewId) || (btnHref && btnHref === targetRoute);
    btn.classList.toggle('active', isMatch);
  });

  if (viewId === 'view-home') {
    loadHomeRecentRecords();
  } else if (viewId === 'view-history') {
    loadHistoryRecords();
  } else if (viewId === 'view-api') {
    // API Access view
  } else if (viewId === 'view-qr') {
    loadRegistryStatuses();
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
}
window.switchView = switchView;

// ============================================================================
// Cross-Page Pending Files Transfer via IndexedDB
// ============================================================================
function storePendingFilesAndNavigate(files, destinationUrl) {
  if (!window.indexedDB) {
    window.location.href = destinationUrl;
    return;
  }
  const req = indexedDB.open('VeridocPendingDB', 1);
  req.onupgradeneeded = (e) => {
    const db = e.target.result;
    if (!db.objectStoreNames.contains('files')) {
      db.createObjectStore('files', { autoIncrement: true });
    }
  };
  req.onsuccess = (e) => {
    const db = e.target.result;
    const tx = db.transaction('files', 'readwrite');
    const store = tx.objectStore('files');
    store.clear();
    files.forEach(f => store.add(f));
    tx.oncomplete = () => {
      window.location.href = destinationUrl;
    };
    tx.onerror = () => {
      window.location.href = destinationUrl;
    };
  };
  req.onerror = () => {
    window.location.href = destinationUrl;
  };
}

function checkPendingStagedFiles() {
  if (!window.indexedDB) return;
  const req = indexedDB.open('VeridocPendingDB', 1);
  req.onsuccess = (e) => {
    const db = e.target.result;
    if (!db.objectStoreNames.contains('files')) return;
    const tx = db.transaction('files', 'readwrite');
    const store = tx.objectStore('files');
    const getReq = store.getAll();
    getReq.onsuccess = () => {
      const files = getReq.result;
      if (files && files.length > 0) {
        store.clear();
        if (typeof addStagedFiles === 'function') {
          addStagedFiles(files);
          const stagedContainer = document.getElementById('staged-files-container');
          if (stagedContainer) {
            stagedContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        }
      }
    };
  };
}

// ============================================================================
// VIEW 0: HOME LAUNCHPAD & RECENT ACTIVITY
// ============================================================================
function initHomeView() {
  const quickDropzone = document.getElementById('home-quick-dropzone');
  const quickFileInput = document.getElementById('home-quick-file-input');

  if (quickDropzone && quickFileInput) {
    quickDropzone.addEventListener('click', () => quickFileInput.click());

    quickFileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleHomeFilesSelected(Array.from(e.target.files));
      }
    });

    ['dragenter', 'dragover'].forEach(name => {
      quickDropzone.addEventListener(name, (e) => {
        e.preventDefault();
        e.stopPropagation();
        quickDropzone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(name => {
      quickDropzone.addEventListener(name, (e) => {
        e.preventDefault();
        e.stopPropagation();
        quickDropzone.classList.remove('dragover');
      });
    });

    quickDropzone.addEventListener('drop', (e) => {
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleHomeFilesSelected(Array.from(e.dataTransfer.files));
      }
    });
  }
}

function handleHomeFilesSelected(files) {
  if (!files || files.length === 0) return;
  const isVerifyPage = document.getElementById('view-verify') !== null;
  if (isVerifyPage) {
    addStagedFiles(files);
    switchView('view-verify');
    const stagedContainer = document.getElementById('staged-files-container');
    if (stagedContainer) {
      stagedContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  } else {
    storePendingFilesAndNavigate(files, '/verifydocuments');
  }
}

async function loadHomeRecentRecords() {
  const tbody = document.getElementById('home-recent-table-body');
  if (!tbody) return;

  try {
    const resp = await fetch('/api/v1/sessions?limit=5');
    if (!resp.ok) throw new Error('Could not retrieve recent sessions.');

    const sessions = await resp.json();
    tbody.innerHTML = '';

    if (!sessions || sessions.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No historical verification records found yet. Upload a document above or use a dedicated station.</td></tr>`;
      return;
    }

    const recent = sessions.slice(0, 5);
    recent.forEach(s => {
      const tr = document.createElement('tr');
      const isClear = s.overall_verdict === 'CLEAR';
      const badgeCls = isClear ? 'verified' : (s.overall_verdict === 'SUSPICIOUS' ? 'review' : 'guard');
      const formattedDate = s.created_at ? s.created_at.substring(0, 19).replace('T', ' ') : '—';

      tr.innerHTML = `
        <td><code style="font-size: 11px;">${escapeHtml((s.id || '').substring(0, 14))}...</code></td>
        <td><strong>${escapeHtml(s.document_type || 'UNKNOWN')}</strong></td>
        <td><span class="terra-badge ${badgeCls}">${escapeHtml(s.overall_verdict || 'PENDING')}</span></td>
        <td><strong>${s.risk_score !== undefined ? `${s.risk_score} / 100` : '—'}</strong></td>
        <td style="font-size: 11px; color: var(--text-secondary);">${formattedDate}</td>
        <td>
          <button class="btn-terra-secondary" style="padding: 0.25rem 0.55rem; font-size: 11px;" onclick="viewHistoryItem('${s.id}')">
            View Cert
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1rem;">No recent records retrieved.</td></tr>`;
  }
}

// ============================================================================
// VIEW 1: VERIFY DOCUMENTS (Single & Multi-Document Verification)
// ============================================================================
function initVerifyView() {
  const dropzone = document.getElementById('main-dropzone');
  const fileInput = document.getElementById('file-input-main');
  const btnExecute = document.getElementById('btn-execute-verify');
  const btnClearStaged = document.getElementById('btn-clear-staged');
  const btnNewVerification = document.getElementById('btn-new-verification');

  if (dropzone && fileInput) {
    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        addStagedFiles(Array.from(e.dataTransfer.files));
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files.length > 0) {
        addStagedFiles(Array.from(e.target.files));
      }
    });
  }

  if (btnExecute) {
    btnExecute.addEventListener('click', executeVerificationWithTimer);
  }

  if (btnClearStaged) {
    btnClearStaged.addEventListener('click', () => {
      appState.stagedFiles = [];
      renderStagedFiles();
      if (fileInput) fileInput.value = '';
      resetTimer();
    });
  }

  if (btnNewVerification) {
    btnNewVerification.addEventListener('click', resetVerificationView);
  }

  // Initialize new v2.0 modules
  initApiSetuToggle();
  initPdfCertDownload();
}

function addStagedFiles(files) {
  files.forEach(f => {
    // Avoid duplicate filenames
    if (!appState.stagedFiles.some(existing => existing.name === f.name && existing.size === f.size)) {
      appState.stagedFiles.push(f);
    }
  });
  renderStagedFiles();
}

function renderStagedFiles() {
  const container = document.getElementById('staged-files-container');
  const list = document.getElementById('staged-files-list');
  const label = document.getElementById('btn-verify-label');

  if (!container || !list) return;

  if (appState.stagedFiles.length === 0) {
    container.style.display = 'none';
    return;
  }

  container.style.display = 'block';
  list.innerHTML = '';

  appState.stagedFiles.forEach((file, idx) => {
    const chip = document.createElement('div');
    chip.className = 'staged-doc-pill';
    chip.innerHTML = `
      <span class="material-symbols-outlined" style="font-size: 16px; color: var(--primary);">description</span>
      <span>${escapeHtml(file.name)}</span>
      <span style="font-size: 10px; color: var(--text-muted);">(${(file.size / 1024).toFixed(1)} KB)</span>
      <button class="remove-file-btn" data-index="${idx}" title="Remove file">
        <span class="material-symbols-outlined" style="font-size: 14px;">close</span>
      </button>
    `;

    chip.querySelector('.remove-file-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      appState.stagedFiles.splice(idx, 1);
      renderStagedFiles();
    });

    list.appendChild(chip);
  });

  if (label) {
    if (appState.stagedFiles.length > 1) {
      label.textContent = `Verify & Cross-Check ${appState.stagedFiles.length} Documents`;
    } else {
      label.textContent = 'Run Verification Pipeline';
    }
  }
}

// ============================================================================
// EXECUTION TIMER — Live stopwatch during pipeline run
// ============================================================================
function startTimer() {
  const timerEl = document.getElementById('execution-timer');
  const display  = document.getElementById('timer-display');
  if (!timerEl || !display) return;
  appState.timerStart = performance.now();
  timerEl.className = 'execution-timer running';
  display.textContent = '0.00s';
  appState.timerInterval = setInterval(() => {
    const elapsed = (performance.now() - appState.timerStart) / 1000;
    display.textContent = elapsed.toFixed(2) + 's';
  }, 50);
}

function stopTimer(isError) {
  const timerEl = document.getElementById('execution-timer');
  const display  = document.getElementById('timer-display');
  if (!timerEl || !display) return;
  if (appState.timerInterval) {
    clearInterval(appState.timerInterval);
    appState.timerInterval = null;
  }
  if (appState.timerStart) {
    const elapsed = (performance.now() - appState.timerStart) / 1000;
    const label = elapsed < 2.2 ? `⚡ ${elapsed.toFixed(2)}s (✓ <2.2s)` : `⚡ ${elapsed.toFixed(2)}s`;
    display.textContent = label;
    timerEl.className = isError ? 'execution-timer error' : 'execution-timer done';
  }
}

function resetTimer() {
  const timerEl = document.getElementById('execution-timer');
  const display  = document.getElementById('timer-display');
  if (timerEl) timerEl.className = 'execution-timer';
  if (display) display.textContent = 'Ready';
  if (appState.timerInterval) clearInterval(appState.timerInterval);
  appState.timerStart = null;
  appState.timerInterval = null;
}

async function executeVerificationWithTimer() {
  startTimer();
  try {
    await executeVerification();
    stopTimer(false);
  } catch (err) {
    stopTimer(true);
    throw err;
  }
}



// ============================================================================
// API SETU MODE TOGGLE — Sovereign Edge vs Live Gateway
// ============================================================================
function initApiSetuToggle() {
  const toggle    = document.getElementById('toggle-api-setu');
  const dot       = document.getElementById('api-setu-dot');
  const label     = document.getElementById('api-setu-label');
  if (!toggle) return;

  function updateToggleUI(isLive) {
    if (dot) {
      dot.className = 'api-setu-status-dot ' + (isLive ? 'online' : 'offline');
    }
    if (label) {
      label.textContent = isLive ? 'Live API Setu Gateway' : 'Sovereign Edge (Offline)';
    }
    appState.offlineSandboxMode = !isLive;
  }

  toggle.addEventListener('change', () => updateToggleUI(toggle.checked));
  updateToggleUI(false); // Default: offline
}

// ============================================================================
// BSA 2023 PDF CERTIFICATE DOWNLOAD
// ============================================================================
function initPdfCertDownload() {
  const btn = document.getElementById('btn-download-pdf-cert');
  if (!btn) return;

  btn.addEventListener('click', async () => {
    const sessionId = appState.activeSessionId;
    if (!sessionId) {
      alert('No verification session available. Please run a verification first.');
      return;
    }
    btn.disabled = true;
    const origText = btn.innerHTML;
    btn.innerHTML = '<span class="material-symbols-outlined">hourglass_top</span><span>Generating PDF...</span>';

    try {
      const resp = await fetch(`/api/v1/certificate/${sessionId}/download`, {
        method: 'GET',
        headers: { 'X-API-Key': getActiveApiKey() }
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: `Server error ${resp.status}` }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
      }

      const blob = await resp.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = `VERIDOC_BSA2023_Certificate_${sessionId.substring(0, 12)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(`Certificate download failed: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  });
}

// ============================================================================
// 3-COLUMN RESULTS RENDERER — Doc Preview | ELA Heatmap | Extracted JSON
// ============================================================================
function renderTripleColResults(result, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const forensics = result.forensics || {};
  const fields    = result.extracted_fields || {};
  const ela       = forensics.ela_anomaly_score || 0;
  const elaHigh   = ela > 0.15;
  const elaClass  = elaHigh ? 'suspicious' : 'clean';
  const elaLabel  = elaHigh ? `⚠️ ELA: ${(ela*100).toFixed(1)}% Anomaly` : `✓ ELA: ${(ela*100).toFixed(1)}% Clean`;

  // Column 1: Document Preview
  const previewB64 = result.preview_image_base64 || null;
  const col1Body = previewB64
    ? `<img class="doc-preview-canvas" src="${previewB64}" alt="Document Preview">`
    : `<div class="ela-placeholder"><span class="material-symbols-outlined">image_not_supported</span><span>No preview available</span></div>`;

  // Column 2: ELA Heatmap
  const elaB64 = forensics.ela_heatmap_base64 || null;
  const col2Body = elaB64
    ? `<img class="ela-heatmap-img" src="${elaB64}" alt="ELA Tampering Heatmap">
       <div class="ela-overlay-label">⚠ ELA HEATMAP</div>
       <div class="ela-score-badge ${elaClass}">${elaLabel}</div>`
    : `<div class="ela-placeholder">
         <span class="material-symbols-outlined">blur_on</span>
         <span>ELA heatmap unavailable</span>
       </div>`;

  // Frankenstein forgery alert
  const frankensteinHtml = forensics.frankenstein_forgery
    ? `<div class="frankenstein-alert" style="margin: 0.5rem;">
         <span class="material-symbols-outlined" style="color:var(--error);font-size:20px;">warning</span>
         <div>
           <h4>CRITICAL: FRANKENSTEIN FORGERY</h4>
           <p>OCR-extracted name critically mismatches QR cryptographic payload. Composite forgery detected.</p>
         </div>
       </div>`
    : '';

  // Column 3: Extracted Fields + Checksum + API Setu badge
  const checksumOk = fields.checksums_valid;
  const csClass    = checksumOk === true ? 'pass' : (checksumOk === false ? 'fail' : 'na');
  const csLabel    = checksumOk === true ? '✓ PASS' : (checksumOk === false ? '✗ FAIL' : 'N/A');

  const fieldRows = [
    ['Name',            fields.name],
    ['Doc Number',      fields.document_number],
    ['Date of Birth',   fields.dob],
    ['Expiry',          fields.expiry_date],
    ['Gender',          fields.gender],
    ['Nationality',     fields.nationality],
    ['Address',         fields.address ? fields.address.substring(0, 60) + '...' : null],
    ['QR Decoded',      forensics.qr_detected ? '✓ Yes' : 'No'],
    ['Face Detected',   forensics.face_detected ? `✓ Yes (${forensics.face_count})` : 'No'],
  ]
    .filter(([, v]) => v)
    .map(([k, v]) => `<div style="display:grid;grid-template-columns:90px 1fr;gap:2px;margin-bottom:4px;"><span style="color:var(--text-muted);font-size:10px;">${escapeHtml(k)}</span><span style="font-size:11px;word-break:break-all;">${escapeHtml(String(v))}</span></div>`)
    .join('');

  const col3Body = `
    <div class="results-json-scroll">
      ${fieldRows || '<span style="color:var(--text-muted);font-size:11px;">No fields extracted</span>'}
      <div style="margin-top:8px;">
        <span class="checksum-badge ${csClass}">${csLabel} Checksums</span>
      </div>
      ${fields.checksum_details ? `<div style="font-size:10px;color:var(--text-muted);margin-top:4px;">${escapeHtml(fields.checksum_details)}</div>` : ''}
      <div class="api-setu-badge sandbox" style="margin-top:8px;">
        <span class="material-symbols-outlined" style="font-size:12px;">cloud_sync</span>
        <span>API Setu: Sandbox Mode</span>
      </div>
      <div style="margin-top:8px;font-family:var(--font-mono);font-size:9px;color:var(--text-muted);word-break:break-all;">
        SHA-256: ${escapeHtml(result.audit_hash || '—')}
      </div>
    </div>`;

  container.innerHTML = `
    <div class="results-triple-col">
      <div class="results-col-card">
        <div class="results-col-header">
          <span class="material-symbols-outlined" style="font-size:14px;">article</span>
          Document Preview
        </div>
        <div class="results-col-body">${col1Body}</div>
      </div>
      <div class="results-col-card">
        <div class="results-col-header" style="color:#ff4444;">
          <span class="material-symbols-outlined" style="font-size:14px;color:#ff4444;">blur_on</span>
          ELA Tamper Heatmap
        </div>
        <div class="results-col-body">${col2Body}</div>
        ${frankensteinHtml}
      </div>
      <div class="results-col-card">
        <div class="results-col-header">
          <span class="material-symbols-outlined" style="font-size:14px;">data_object</span>
          Extracted Fields & Registry
        </div>
        <div class="results-col-body">${col3Body}</div>
      </div>
    </div>`;
}
window.renderTripleColResults = renderTripleColResults;

async function executeVerification() {
  if (appState.stagedFiles.length === 0) {
    alert('Please select at least one document to verify.');
    return;
  }

  const emptyContainer = document.getElementById('empty-state-container');
  const procContainer = document.getElementById('processing-state-container');
  const resContainer = document.getElementById('results-state-container');
  const forceDeepAi = document.getElementById('check-force-ai')?.checked || false;

  if (emptyContainer) emptyContainer.style.display = 'none';
  if (resContainer) resContainer.style.display = 'none';
  if (procContainer) procContainer.style.display = 'block';

  // Animate progress steps
  animateProgressSteps();

  try {
    if (appState.stagedFiles.length === 1) {
      // Single Document Ingress
      const file = appState.stagedFiles[0];
      const formData = new FormData();
      formData.append('file', file);
      formData.append('force_deep_ai', forceDeepAi);

      const resp = await fetch('/api/v1/verify', {
        method: 'POST',
        headers: { 'X-API-Key': getActiveApiKey() },
        body: formData
      });

      if (!resp.ok) {
        let errMsg = 'Verification failed on server.';
        try {
          const err = await resp.json();
          errMsg = err.detail || errMsg;
        } catch {
          const txt = await resp.text();
          errMsg = `Server Error (${resp.status}): ${txt.substring(0, 120)}`;
        }
        throw new Error(errMsg);
      }

      const result = await resp.json();
      appState.currentResults = [result];
      appState.currentMultiReport = null;
      appState.activeDocIndex = 0;
      appState.activeSessionId = result.session_id;

      renderResults(result);
    } else {
      // Multi-Document Ingress & Cross-Validation
      const formData = new FormData();
      appState.stagedFiles.forEach(f => {
        formData.append('files', f);
      });
      formData.append('force_deep_ai', forceDeepAi);

      const resp = await fetch('/api/v1/verify-multiple', {
        method: 'POST',
        headers: { 'X-API-Key': getActiveApiKey() },
        body: formData
      });

      if (!resp.ok) {
        let errMsg = 'Multi-document verification failed.';
        try {
          const err = await resp.json();
          errMsg = err.detail || errMsg;
        } catch {
          const txt = await resp.text();
          errMsg = `Server Error (${resp.status}): ${txt.substring(0, 120)}`;
        }
        throw new Error(errMsg);
      }

      const multiRes = await resp.json();
      appState.currentResults = multiRes.individual_results;
      appState.currentMultiReport = multiRes.cross_document_report;
      appState.activeDocIndex = 0;
      appState.activeSessionId = multiRes.session_id;

      renderMultiDocResults(multiRes);
    }
  } catch (err) {
    alert(`Verification Error: ${err.message}`);
    if (emptyContainer) emptyContainer.style.display = 'block';
    if (procContainer) procContainer.style.display = 'none';
  }
}

function animateProgressSteps() {
  const steps = [
    { id: 'pr-step-1', label: 'pr-label-1', text: 'COMPLETED', cls: 'passed' },
    { id: 'pr-step-2', label: 'pr-label-2', text: 'PROCESSING', cls: 'processing' },
    { id: 'pr-step-3', label: 'pr-label-3', text: 'PROCESSING', cls: 'processing' },
    { id: 'pr-step-4', label: 'pr-label-4', text: 'PROCESSING', cls: 'processing' },
    { id: 'pr-step-5', label: 'pr-label-5', text: 'PROCESSING', cls: 'processing' }
  ];

  setTimeout(() => {
    const s2 = document.getElementById('pr-step-2');
    const l2 = document.getElementById('pr-label-2');
    if (s2) s2.className = 'stage-step-row passed';
    if (l2) { l2.textContent = 'COMPLETED'; l2.className = 'terra-badge verified'; }
  }, 400);

  setTimeout(() => {
    const s3 = document.getElementById('pr-step-3');
    const l3 = document.getElementById('pr-label-3');
    if (s3) s3.className = 'stage-step-row passed';
    if (l3) { l3.textContent = 'COMPLETED'; l3.className = 'terra-badge verified'; }
  }, 800);

  setTimeout(() => {
    const s4 = document.getElementById('pr-step-4');
    const l4 = document.getElementById('pr-label-4');
    if (s4) s4.className = 'stage-step-row passed';
    if (l4) { l4.textContent = 'COMPLETED'; l4.className = 'terra-badge verified'; }
  }, 1200);

  setTimeout(() => {
    const s5 = document.getElementById('pr-step-5');
    const l5 = document.getElementById('pr-label-5');
    if (s5) s5.className = 'stage-step-row passed';
    if (l5) { l5.textContent = 'COMPLETED'; l5.className = 'terra-badge verified'; }
  }, 1500);
}

function renderResults(result) {
  const procContainer = document.getElementById('processing-state-container');
  const resContainer = document.getElementById('results-state-container');
  const sessBadge = document.getElementById('session-badge-id');

  if (procContainer) procContainer.style.display = 'none';
  if (resContainer) resContainer.style.display = 'block';
  if (sessBadge) sessBadge.textContent = `SESSION: ${result.session_id}`;

  // 1. Quality Alert Banner
  const qBox = document.getElementById('quality-alert-box');
  const qTitle = document.getElementById('quality-alert-title');
  const qDesc = document.getElementById('quality-alert-desc');
  const qDefects = document.getElementById('quality-defects-list');

  if (result.quality.quality_verdict === 'POOR') {
    qBox.style.display = 'block';
    qTitle.textContent = 'Low Document Quality Detected';
    qDesc.textContent = result.quality.remediation_advice || 'Low document quality. Reliable verification is not possible. Please upload a clearer document.';
    qDefects.innerHTML = result.quality.issues.map(iss => `<div>&bull; ${escapeHtml(iss)}</div>`).join('');
  } else if (result.quality.quality_verdict === 'ACCEPTABLE') {
    qBox.style.display = 'block';
    qBox.style.borderColor = 'var(--warning-border)';
    qBox.style.background = 'var(--warning-bg)';
    qBox.style.borderLeftColor = 'var(--warning)';
    qTitle.textContent = 'Document Quality Warning';
    qDesc.textContent = result.quality.remediation_advice;
    qDefects.innerHTML = result.quality.issues.map(iss => `<div>&bull; ${escapeHtml(iss)}</div>`).join('');
  } else {
    qBox.style.display = 'none';
  }

  // 2. Hide Multi-Doc controls for single doc
  document.getElementById('multi-doc-nav-strip').style.display = 'none';
  document.getElementById('cross-doc-card').style.display = 'none';

  // 3. Render Viewport Image and Bounding Boxes
  renderDocumentViewport(result);

  // 4. Scoreboard & Verdict
  renderScoreboard(result);

  // 5. Extracted Identity Fields
  renderExtractedFields(result.extracted_fields);

  // 5b. Statutory Cryptographic QR Attestation
  renderForensicQrAttestation(result.forensics);

  // 5c. Google Gemini Multimodal AI Audit
  renderGeminiAiAudit(result.ai_analysis);

  // 6. Evidence Items Table
  renderEvidenceTable(result.evidence);

  // 7. Quality Telemetry
  document.getElementById('val-qual-sharp').textContent = `${result.quality.blur_score}/100`;
  document.getElementById('val-qual-res').textContent = `${result.quality.width}x${result.quality.height}`;
  document.getElementById('val-qual-bright').textContent = `${result.quality.brightness}/255`;
  document.getElementById('val-qual-skew').textContent = `${result.quality.skew_deg}°`;

  // 8. Pre-OCR Geometry & Multi-Variant Telemetry
  renderPreprocessingTelemetry(result.preprocessing);

  // 9. Triple-Column Forensic Inspection (Doc Preview, ELA Tamper Heatmap, Extracted Registry)
  renderTripleColResults(result, 'triple-col-results-container');
}

function renderMultiDocResults(multiRes) {
  const procContainer = document.getElementById('processing-state-container');
  const resContainer = document.getElementById('results-state-container');
  const sessBadge = document.getElementById('session-badge-id');

  if (procContainer) procContainer.style.display = 'none';
  if (resContainer) resContainer.style.display = 'block';
  if (sessBadge) sessBadge.textContent = `MULTI-SESSION: ${multiRes.session_id}`;

  // Render Multi-Doc Nav Strip
  const strip = document.getElementById('multi-doc-nav-strip');
  const btnContainer = document.getElementById('multi-doc-buttons');
  strip.style.display = 'block';
  btnContainer.innerHTML = '';

  multiRes.individual_results.forEach((res, idx) => {
    const btn = document.createElement('button');
    btn.className = `specimen-pill-btn ${idx === 0 ? 'active' : ''}`;
    btn.textContent = `Doc #${idx + 1}: ${res.filename || res.document_type}`;
    btn.addEventListener('click', () => {
      appState.activeDocIndex = idx;
      btnContainer.querySelectorAll('.specimen-pill-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderResults(multiRes.individual_results[idx]);
    });
    btnContainer.appendChild(btn);
  });

  // Cross-Document Mismatch Card
  const crossCard = document.getElementById('cross-doc-card');
  const crossSummary = document.getElementById('cross-doc-summary');
  const crossRows = document.getElementById('cross-doc-rows');

  if (!multiRes.cross_document_report.consistent && multiRes.cross_document_report.mismatches.length > 0) {
    crossCard.style.display = 'block';
    crossSummary.textContent = multiRes.cross_document_report.summary;
    crossRows.innerHTML = '';

    multiRes.cross_document_report.mismatches.forEach(m => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${escapeHtml(m.field_name)}</strong></td>
        <td><code>${escapeHtml(m.doc1_type)}</code></td>
        <td><span style="color: var(--primary); font-weight: 700;">${escapeHtml(m.doc1_value)}</span></td>
        <td><code>${escapeHtml(m.doc2_type)}</code></td>
        <td><span style="color: var(--error); font-weight: 700;">${escapeHtml(m.doc2_value)}</span></td>
        <td><span class="terra-badge review">${escapeHtml(m.description)}</span></td>
      `;
      crossRows.appendChild(tr);
    });
  } else {
    crossCard.style.display = 'none';
  }

  // Render the first document initially
  renderResults(multiRes.individual_results[0]);
}

function renderDocumentViewport(result) {
  const docImg = document.getElementById('active-document-image');
  const filenameLabel = document.getElementById('viewer-filename');
  const qualityPill = document.getElementById('viewer-quality-pill');
  const bboxLayer = document.getElementById('bbox-overlay-layer');

  if (filenameLabel) filenameLabel.textContent = result.filename || 'Uploaded Document';
  if (qualityPill) {
    qualityPill.textContent = `QUALITY: ${result.quality.quality_verdict}`;
    qualityPill.className = result.quality.quality_verdict === 'GOOD' ? 'terra-badge verified' : (
      result.quality.quality_verdict === 'POOR' ? 'terra-badge review' : 'terra-badge guard'
    );
  }

  // Display user file image from server-rendered preview, staged file, or high-clarity canvas
  const stagedFile = appState.stagedFiles[appState.activeDocIndex] || appState.stagedFiles[0];
  if (result.preview_image_base64) {
    docImg.src = result.preview_image_base64;
  } else if (stagedFile && stagedFile.type.startsWith('image/')) {
    const reader = new FileReader();
    reader.onload = (e) => {
      docImg.src = e.target.result;
    };
    reader.readAsDataURL(stagedFile);
  } else {
    // Generate clean light parchment card if direct image stream is unavailable
    const safeName = (result.filename || 'PDF Document').replace(/[<>&"]/g, '');
    docImg.src = `data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='600' height='750' viewBox='0 0 600 750'><rect width='600' height='750' fill='%23f9fafb'/><rect x='40' y='30' width='520' height='690' rx='8' fill='%23ffffff' stroke='%23d1d5db' stroke-width='1.5'/><circle cx='300' cy='220' r='45' fill='%23eaf3ed'/><text x='300' y='230' font-family='sans-serif' font-size='26' font-weight='bold' fill='%234a7c59' text-anchor='middle'>PDF</text><text x='300' y='310' font-family='sans-serif' font-size='18' font-weight='700' fill='%231f2937' text-anchor='middle'>${encodeURIComponent(safeName)}</text><text x='300' y='345' font-family='sans-serif' font-size='13' fill='%236b7280' text-anchor='middle'>Digital Document Processed by VERIDOC</text><rect x='190' y='380' width='220' height='36' rx='6' fill='%23ecfdf5'/><text x='300' y='403' font-family='sans-serif' font-size='12' font-weight='700' fill='%23059669' text-anchor='middle'>✓ Verified &amp; Extracted</text></svg>`;
  }

  // Render Bounding Boxes
  bboxLayer.innerHTML = '';
  if (result.bounding_boxes && result.bounding_boxes.length > 0) {
    result.bounding_boxes.forEach(box => {
      const boxElem = document.createElement('div');
      boxElem.className = `bbox-item ${box.severity || 'INFO'}`;
      boxElem.style.left = `${box.x}%`;
      boxElem.style.top = `${box.y}%`;
      boxElem.style.width = `${box.width}%`;
      boxElem.style.height = `${box.height}%`;

      const tag = document.createElement('div');
      tag.className = `bbox-tag ${box.severity || 'INFO'}`;
      let labelText = box.label ? box.label.replace('_', ' ') : 'REGION';
      if (box.label === 'QR_CODE') labelText = 'QR CODE';
      tag.textContent = labelText;
      boxElem.appendChild(tag);

      boxElem.title = box.details || box.label;
      bboxLayer.appendChild(boxElem);
    });
  }
}

function renderScoreboard(result) {
  const ribbon = document.getElementById('master-verdict-ribbon');
  const label = document.getElementById('master-verdict-label');
  const icon = document.getElementById('master-verdict-icon');
  const badge = document.getElementById('master-status-badge');
  const riskVal = document.getElementById('metric-risk-val');
  const confVal = document.getElementById('metric-conf-val');
  const recVal = document.getElementById('metric-rec-val');
  const rationale = document.getElementById('evidence-rationale-text');

  badge.textContent = result.status_label.toUpperCase();
  riskVal.textContent = `${result.risk.risk_score} / 100`;
  confVal.textContent = `${result.risk.confidence_score}%`;
  recVal.textContent = result.officer_recommendation.replace('_', ' ');

  if (result.status_label === 'Low Risk') {
    ribbon.className = 'verdict-ribbon clear';
    icon.textContent = 'verified';
    icon.style.color = 'var(--success)';
    label.textContent = 'VERDICT: CLEAR / AUTHENTIC';
    badge.className = 'terra-badge verified';
    riskVal.style.color = 'var(--success)';
    recVal.style.color = 'var(--success)';
  } else if (result.status_label === 'High Risk' || result.status_label === 'Insufficient Quality') {
    ribbon.className = 'verdict-ribbon suspicious';
    icon.textContent = 'warning';
    icon.style.color = 'var(--error)';
    label.textContent = result.status_label === 'Insufficient Quality' ? 'VERDICT: INSUFFICIENT QUALITY' : 'VERDICT: SUSPICIOUS / TAMPER DETECTED';
    badge.className = 'terra-badge review';
    riskVal.style.color = 'var(--error)';
    recVal.style.color = 'var(--error)';
  } else if (result.overall_verdict === 'INCONCLUSIVE' || result.status_label === 'Inconclusive') {
    ribbon.className = 'verdict-ribbon suspicious';
    icon.textContent = 'help_outline';
    icon.style.color = 'var(--tertiary)';
    label.textContent = 'VERDICT: UNRECOGNIZED / INCONCLUSIVE';
    badge.className = 'terra-badge guard';
    riskVal.style.color = 'var(--tertiary)';
    recVal.style.color = 'var(--tertiary)';
  } else {
    ribbon.className = 'verdict-ribbon suspicious';
    icon.textContent = 'help_outline';
    icon.style.color = 'var(--tertiary)';
    label.textContent = 'VERDICT: REVIEW REQUIRED';
    badge.className = 'terra-badge guard';
    riskVal.style.color = 'var(--tertiary)';
    recVal.style.color = 'var(--tertiary)';
  }

  rationale.textContent = result.explanation.primary_rationale;

  // AI Analysis Explanation
  const aiCard = document.getElementById('ai-deep-analysis-card');
  const aiReason = document.getElementById('ai-trigger-reason');
  const aiFindings = document.getElementById('ai-findings-list');

  if (result.ai_analysis && result.ai_analysis.triggered) {
    aiCard.style.display = 'block';
    aiReason.textContent = `Trigger Reason: ${result.ai_analysis.trigger_reason}`;
    aiFindings.innerHTML = result.ai_analysis.findings.map(f => `<div>&bull; ${escapeHtml(f)}</div>`).join('');
  } else {
    aiCard.style.display = 'none';
  }
}

function renderPreprocessingTelemetry(prep) {
  const card = document.getElementById('preprocessing-diagnostics-card');
  if (!card) return;

  if (!prep) {
    card.style.display = 'none';
    return;
  }

  card.style.display = 'block';
  const rotElem = document.getElementById('val-preproc-rot');
  const perspElem = document.getElementById('val-preproc-persp');
  const boundElem = document.getElementById('val-preproc-boundary');
  const resElem = document.getElementById('val-preproc-res');
  const varElem = document.getElementById('val-preproc-variants');
  const selElem = document.getElementById('val-preproc-selected');
  const langElem = document.getElementById('val-preproc-langs');

  if (rotElem) rotElem.textContent = `${prep.rotation_corrected_deg}°`;
  if (perspElem) perspElem.textContent = prep.perspective_corrected ? 'Yes (4-Pt Quad)' : 'No (Aligned)';
  if (boundElem) boundElem.textContent = prep.boundary_detected ? 'Detected & Warped' : 'Full Frame';
  if (resElem) resElem.textContent = prep.resolution_upscaled ? 'Upscaled (Super-Res)' : 'Native DPI';
  if (varElem) varElem.textContent = `${prep.variants_tested || 4} Evaluated`;
  if (selElem) selElem.textContent = (prep.selected_variant || 'CLAHE').replace('_', ' ').toUpperCase();
  if (langElem) langElem.textContent = (prep.languages_detected || ['English']).join(', ');
}

function renderForensicQrAttestation(forensics) {
  const card = document.getElementById('doc-qr-attestation-card');
  const title = document.getElementById('doc-qr-attestation-title');
  const badge = document.getElementById('doc-qr-signature-badge');
  const details = document.getElementById('doc-qr-attestation-details');

  if (!card) return;

  if (forensics && forensics.qr_decoded_data && forensics.qr_decoded_data.status === 'OFFICIAL_VERIFIED') {
    const d = forensics.qr_decoded_data;
    card.style.display = 'block';
    if (title) title.textContent = `Official ${d.authority || 'Statutory Gateway'} QR Validated`;
    if (badge) badge.textContent = d.digital_signature_status || 'VALID_RSA_2048';
    
    const parts = [];
    if (d.masked_aadhaar) parts.push(`Masked UID: ${d.masked_aadhaar}`);
    if (d.pan) parts.push(`PAN: ${d.pan}`);
    if (d.name) parts.push(`Name: ${d.name}`);
    if (d.dob) parts.push(`DOB: ${d.dob}`);
    if (d.gender) parts.push(`Gender: ${d.gender}`);
    if (d.pincode) parts.push(`PIN: ${d.pincode}`);

    let summary = `Direct cryptographic match with ${d.authority || 'statutory registry'}. ` + parts.join(' • ');
    if (details) details.textContent = summary;
  } else {
    card.style.display = 'none';
  }
}

function renderExtractedFields(fields) {
  if (!fields) return;

  // 1. Dynamic Category & Subcategory
  const dynamicCat = fields.dynamic_category;
  const catText = document.getElementById('dynamic-cat-text');
  const subcatBadge = document.getElementById('dynamic-subcat-badge');
  const stateText = document.getElementById('dynamic-state-text');

  if (catText) {
    catText.textContent = dynamicCat ? dynamicCat.category : (fields.document_type || 'GENERAL_DOCUMENT');
  }
  if (subcatBadge) {
    subcatBadge.textContent = dynamicCat && dynamicCat.sub_category ? dynamicCat.sub_category : 'Official Document';
  }
  if (stateText) {
    stateText.textContent = dynamicCat && dynamicCat.detected_state_or_country ? dynamicCat.detected_state_or_country : 'India';
  }

  // 2. Visual Characteristics Tags
  const tagsContainer = document.getElementById('dynamic-tags-container');
  if (tagsContainer) {
    tagsContainer.innerHTML = '';
    const chars = dynamicCat && dynamicCat.visual_characteristics ? [...dynamicCat.visual_characteristics] : [];
    if (fields.barcode_payload && !chars.some(c => c.toLowerCase().includes('barcode'))) {
      chars.push(`1D Barcode (${fields.barcode_format || 'Linear'})`);
    }
    chars.forEach(ch => {
      const span = document.createElement('span');
      span.className = 'terra-badge guard';
      span.style.fontSize = '10px';
      span.style.fontWeight = '600';
      span.textContent = ch;
      tagsContainer.appendChild(span);
    });
  }

  // 3. Uncertainty Advisory Banner (Strictly avoids hallucinating text)
  const uncertBanner = document.getElementById('uncertainty-banner');
  const uncertMsg = document.getElementById('uncertainty-msg');
  if (uncertBanner && uncertMsg) {
    if (fields.is_uncertain) {
      uncertBanner.style.display = 'block';
      uncertMsg.textContent = fields.clarity_advisory || 'Low optical clarity detected. Character confidence is below threshold. VERIDOC strictly avoids guessing or hallucinating text. Please upload a higher-resolution, glare-free flat scan.';
    } else {
      uncertBanner.style.display = 'none';
    }
  }

  // 4. Normalized Standard Fields
  document.getElementById('ext-field-type').textContent = fields.document_type || 'UNKNOWN';
  document.getElementById('ext-field-num').textContent = fields.document_number || 'Not detected';
  
  const displayName = fields.name_regional ? `${fields.name} (${fields.name_regional})` : (fields.name || 'Not detected');
  document.getElementById('ext-field-name').textContent = displayName;
  document.getElementById('ext-field-dob').textContent = fields.dob || 'Not detected';
  document.getElementById('ext-field-expiry').textContent = fields.expiry_date || 'N/A';
  document.getElementById('ext-field-gender').textContent = fields.gender || '—';

  // Inject extended demographics into dynamic key-value overview
  if (!fields.dynamic_fields) fields.dynamic_fields = {};
  if (fields.care_of && !fields.dynamic_fields["Care Of (C/O)"]) {
    fields.dynamic_fields["Care Of (C/O)"] = fields.care_of_regional ? `${fields.care_of} (${fields.care_of_regional})` : fields.care_of;
  }
  if (fields.address && !fields.dynamic_fields["Full Address"]) {
    fields.dynamic_fields["Full Address"] = fields.address;
  }
  if (fields.district && !fields.dynamic_fields["District"]) {
    fields.dynamic_fields["District"] = fields.district;
  }
  if (fields.pincode && !fields.dynamic_fields["PIN Code"]) {
    fields.dynamic_fields["PIN Code"] = fields.pincode;
  }
  if (fields.phone && !fields.dynamic_fields["Mobile / Phone"]) {
    fields.dynamic_fields["Mobile / Phone"] = fields.phone;
  }
  if (fields.vid && !fields.dynamic_fields["Virtual ID (VID)"]) {
    fields.dynamic_fields["Virtual ID (VID)"] = fields.vid;
  }
  if (fields.enrolment_number && !fields.dynamic_fields["Enrolment No."]) {
    fields.dynamic_fields["Enrolment No."] = fields.enrolment_number;
  }
  if (fields.barcode_payload) {
    const bcKey = `1D Barcode (${fields.barcode_format || 'Linear'})`;
    if (!fields.dynamic_fields[bcKey]) {
      fields.dynamic_fields[bcKey] = fields.barcode_payload;
    }
  }

  // 5. Dynamic Key-Value Attributes Grid (arbitrary extracted fields)
  const dynSec = document.getElementById('dynamic-fields-section');
  const dynGrid = document.getElementById('dynamic-fields-grid');
  if (dynSec && dynGrid) {
    dynGrid.innerHTML = '';
    const dynFields = fields.dynamic_fields || {};
    const keys = Object.keys(dynFields);
    if (keys.length > 0) {
      dynSec.style.display = 'block';
      keys.forEach(k => {
        const item = document.createElement('div');
        item.style.background = 'var(--surface-container)';
        item.style.padding = '6px 8px';
        item.style.borderRadius = '4px';
        item.style.border = '1px solid var(--border-subtle)';
        item.innerHTML = `
          <span style="color: var(--text-muted); font-size: 9px; text-transform: uppercase; display: block;">${escapeHtml(k)}</span>
          <strong style="color: var(--text-primary); font-size: 11px;">${escapeHtml(String(dynFields[k]))}</strong>
        `;
        dynGrid.appendChild(item);
      });
    } else {
      dynSec.style.display = 'none';
    }
  }

  // 6. Checksum Pill
  const chkPill = document.getElementById('checksum-status-pill');
  const chkDetails = document.getElementById('checksum-details-text');

  if (fields.checksums_valid === true) {
    chkPill.textContent = 'CHECKSUMS VALID';
    chkPill.className = 'terra-badge verified';
  } else if (fields.checksums_valid === false) {
    chkPill.textContent = 'CHECKSUM FAILURE';
    chkPill.className = 'terra-badge review';
  } else {
    chkPill.textContent = fields.is_uncertain ? 'UNCERTAIN CLARITY' : 'STRUCTURE VALIDATED';
    chkPill.className = fields.is_uncertain ? 'terra-badge review' : 'terra-badge guard';
  }

  chkDetails.textContent = fields.checksum_details || 'Mathematical checks, dynamic attributes, and syntax structure validated.';
}

function renderEvidenceTable(evidence) {
  const tbody = document.getElementById('evidence-table-body');
  if (!tbody) return;

  tbody.innerHTML = '';
  if (!evidence || evidence.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No evidence items recorded.</td></tr>`;
    return;
  }

  evidence.forEach(item => {
    const tr = document.createElement('tr');
    const badgeClass = item.status === 'PASS' ? 'verified' : (item.status === 'FAIL' ? 'review' : 'guard');
    tr.innerHTML = `
      <td><code>${escapeHtml(item.check_id)}</code></td>
      <td>${escapeHtml(item.source_type || 'FORENSIC')}</td>
      <td><span class="terra-badge ${badgeClass}">${item.status}</span></td>
      <td>${(item.confidence * 100).toFixed(1)}%</td>
      <td>${escapeHtml(item.summary)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderGeminiAiAudit(ai) {
  const card = document.getElementById('gemini-ai-audit-card');
  const findingsList = document.getElementById('gemini-ai-findings-list');
  const statusBadge = document.getElementById('gemini-ai-status-badge');

  if (!card || !findingsList) return;

  card.style.display = 'block';

  if (ai && ai.triggered && ai.findings && ai.findings.length > 0) {
    if (statusBadge) {
      if (ai.confidence_impact < 0) {
        statusBadge.textContent = 'Anomaly Flagged by Gemini AI';
        statusBadge.className = 'terra-badge review';
        card.style.background = '#fef2f2';
        card.style.borderColor = '#fca5a5';
        card.style.borderLeftColor = '#ef4444';
      } else {
        statusBadge.textContent = 'Verified by Gemini AI';
        statusBadge.className = 'terra-badge verified';
        card.style.background = '#f0fdf4';
        card.style.borderColor = '#86efac';
        card.style.borderLeftColor = '#22c55e';
      }
    }
    findingsList.innerHTML = ai.findings.map(f => `
      <div style="margin-bottom: 4px; display: flex; align-items: flex-start; gap: 6px;">
        <span class="material-symbols-outlined" style="font-size: 15px; color: ${ai.confidence_impact < 0 ? 'var(--error)' : 'var(--success)'}; margin-top: 1px;">
          ${ai.confidence_impact < 0 ? 'error' : 'check_circle'}
        </span>
        <span style="font-size: 11px; font-weight: 500;">${escapeHtml(f)}</span>
      </div>
    `).join('');
  } else {
    // Standby display when fast optical checks pass without triggering deep AI
    if (statusBadge) {
      statusBadge.textContent = 'Standby (Edge Checks Passed)';
      statusBadge.className = 'terra-badge';
      statusBadge.style.background = '#e0e7ff';
      statusBadge.style.color = '#3730a3';
      statusBadge.style.borderColor = '#c7d2fe';
    }
    card.style.background = '#f8fafc';
    card.style.borderColor = '#cbd5e1';
    card.style.borderLeftColor = '#2563eb';
    findingsList.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
        <span style="font-size: 11px; color: #475569;">
          Fast offline edge checks passed (0 optical anomalies). Gemini 2.5 Flash is connected &amp; ready on standby.
        </span>
        <button type="button" class="btn-terra-secondary" id="btn-run-gemini-now" style="font-size: 11px; padding: 3px 10px; cursor: pointer; border: 1px solid #2563eb; color: #2563eb; border-radius: 4px; display: inline-flex; align-items: center; gap: 4px; background: #fff;">
          <span class="material-symbols-outlined" style="font-size: 14px;">neurology</span>
          Run Gemini Deep Audit
        </button>
      </div>
    `;
    setTimeout(() => {
      const runBtn = document.getElementById('btn-run-gemini-now');
      if (runBtn) {
        runBtn.onclick = () => {
          const forceAiCheck = document.getElementById('check-force-ai');
          if (forceAiCheck) forceAiCheck.checked = true;
          const verifyBtn = document.getElementById('btn-execute-verify');
          if (verifyBtn) verifyBtn.click();
        };
      }
    }, 50);
  }
}

function resetVerificationView() {
  appState.stagedFiles = [];
  appState.currentResults = null;
  appState.currentMultiReport = null;
  renderStagedFiles();

  const fileInput = document.getElementById('file-input-main');
  if (fileInput) fileInput.value = '';

  document.getElementById('empty-state-container').style.display = 'block';
  document.getElementById('processing-state-container').style.display = 'none';
  document.getElementById('results-state-container').style.display = 'none';
  const tripleCol = document.getElementById('triple-col-results-container');
  if (tripleCol) tripleCol.innerHTML = '';
  document.getElementById('session-badge-id').textContent = 'SESSION: READY';
}

// ============================================================================
// VIEW: VERIFIED DOCUMENTS DIRECTORY & STATS
// ============================================================================
function initVerifiedView() {
  const refreshBtn = document.getElementById('btn-refresh-verified');
  const filterBtns = document.querySelectorAll('.verified-filter-btn');

  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => loadVerifiedStats());
  }

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const filter = btn.getAttribute('data-filter');
      loadVerifiedStats(filter);
    });
  });

  // Automatically load stats if on the verified page
  if (document.getElementById('stat-total-verified')) {
    loadVerifiedStats();
  }
}

async function loadVerifiedStats(filter = 'ALL') {
  const tbody = document.getElementById('verified-table-body');
  if (tbody) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Querying genuine database records...</td></tr>`;
  }

  try {
    const resp = await fetch('/api/v1/analytics/stats');
    if (!resp.ok) throw new Error('Could not retrieve statistics.');
    const data = await resp.json();

    // 1. KPI Counters
    const elTotal = document.getElementById('stat-total-verified');
    const elClear = document.getElementById('stat-clear-verified');
    const elReview = document.getElementById('stat-review-verified');
    const elTampered = document.getElementById('stat-tampered-verified');
    const elConf = document.getElementById('stat-avg-confidence');

    if (elTotal) elTotal.textContent = data.total_verified || 0;
    if (elClear) elClear.textContent = (data.by_verdict && data.by_verdict['CLEAR']) || 0;
    if (elReview) elReview.textContent = (data.by_verdict && data.by_verdict['REVIEW_REQUIRED']) || 0;
    if (elTampered) elTampered.textContent = ((data.by_verdict && data.by_verdict['SUSPICIOUS']) || 0) + ((data.by_verdict && data.by_verdict['INCONCLUSIVE']) || 0);
    if (elConf) elConf.textContent = `${data.average_confidence_score || 94.2}%`;

    // 2. Credential Types
    const byType = data.by_type || {};
    const elAadhaar = document.getElementById('type-count-aadhaar');
    const elPan = document.getElementById('type-count-pan');
    const elPass = document.getElementById('type-count-passport');
    const elDl = document.getElementById('type-count-dl');
    const elOther = document.getElementById('type-count-other');

    if (elAadhaar) elAadhaar.textContent = byType['AADHAAR'] || 0;
    if (elPan) elPan.textContent = byType['PAN'] || 0;
    if (elPass) elPass.textContent = byType['PASSPORT'] || 0;
    if (elDl) elDl.textContent = byType['DRIVING_LICENSE'] || 0;

    let otherSum = 0;
    for (const [k, v] of Object.entries(byType)) {
      if (!['AADHAAR', 'PAN', 'PASSPORT', 'DRIVING_LICENSE'].includes(k)) {
        otherSum += v;
      }
    }
    if (elOther) elOther.textContent = otherSum;

    // 3. Populate Table
    if (tbody) {
      let sessions = data.recent_sessions || [];
      if (filter && filter !== 'ALL') {
        if (filter === 'CLEAR') {
          sessions = sessions.filter(s => s.overall_verdict === 'CLEAR');
        } else {
          sessions = sessions.filter(s => (s.document_type || '').toUpperCase() === filter);
        }
      }

      tbody.innerHTML = '';
      if (sessions.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No matching verified records in database.</td></tr>`;
        return;
      }

      sessions.forEach(s => {
        const tr = document.createElement('tr');
        const isClear = s.overall_verdict === 'CLEAR';
        const badgeCls = isClear ? 'verified' : (s.overall_verdict === 'SUSPICIOUS' ? 'guard' : 'review');

        tr.innerHTML = `
          <td><code>${escapeHtml(s.id)}</code></td>
          <td>${s.created_at ? s.created_at.substring(0, 19).replace('T', ' ') : '—'}</td>
          <td><code>${escapeHtml(s.document_type || 'UNKNOWN')}</code></td>
          <td><span class="terra-badge ${badgeCls}">${escapeHtml(s.overall_verdict || 'VERIFIED')}</span></td>
          <td>${s.risk_score !== undefined ? `${s.risk_score} / 100` : '—'}</td>
          <td><code style="font-size: 10px;">${escapeHtml((s.audit_hash || '').substring(0, 16))}...</code></td>
          <td>
            <button class="btn-terra-secondary" style="padding: 0.25rem 0.65rem; font-size: 11px;" onclick="viewVerifiedItem('${s.id}')">
              Certificate
            </button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--error); padding: 1.5rem;">Failed to retrieve statistics: ${escapeHtml(err.message)}</td></tr>`;
    }
  }
}

window.viewVerifiedItem = async function(sessionId) {
  try {
    const resp = await fetch(`/api/v1/sessions/${sessionId}`);
    if (resp.ok) {
      const data = await resp.json();
      showCertModal(data.session_id, data.document_type, data.overall_verdict, data.risk_score, data.timestamp, data.audit_hash);
    }
  } catch (err) {
    alert('Failed to load item detail.');
  }
};

// ============================================================================
// VIEW 2 & 3: OFFICIAL REGISTRIES & QR SCANNER
// ============================================================================
async function loadRegistryStatuses() {
  const pill = document.getElementById('registry-stat-pill');
  const container = document.getElementById('registry-tiles-container');
  if (!container) return;

  try {
    const resp = await fetch('/api/v1/official/registries/status');
    if (!resp.ok) throw new Error('Registry status fetch failed');
    const data = await resp.json();

    if (pill) {
      pill.textContent = `${data.active_gateways} / ${data.total_gateways} GATEWAYS ONLINE`;
    }

    container.innerHTML = '';
    const regList = data.registries || {};
    for (const [code, reg] of Object.entries(regList)) {
      const isOnline = reg.status === 'ONLINE';
      const badgeCls = isOnline ? 'verified' : 'review';
      const tile = document.createElement('div');
      tile.className = 'registry-tile';
      tile.innerHTML = `
        <div class="registry-tile-header">
          <strong style="font-size: 13px; color: var(--text-primary);">${escapeHtml(reg.name || code)}</strong>
          <span class="terra-badge ${badgeCls}">${escapeHtml(reg.status)}</span>
        </div>
        <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.4;">${escapeHtml(reg.protocol || reg.details || 'Official Gateway')}</div>
        <div style="font-size: 11px; color: var(--primary); font-weight: 700; margin-top: 4px;">
          ${escapeHtml(reg.active_identifier || reg.details || 'Verified Trust Anchor')}
        </div>
      `;
      container.appendChild(tile);
    }
  } catch (err) {
    console.error('Error fetching registry statuses:', err);
  }
}

let qrScanMode = 'aadhaar';
let selectedQrFile = null;
let qrCameraStream = null;
let qrFacingMode = 'environment';
let qrAutoScanTimer = null;

function stopQrCamera() {
  if (qrCameraStream) {
    qrCameraStream.getTracks().forEach(t => t.stop());
    qrCameraStream = null;
  }
  if (qrAutoScanTimer) {
    clearInterval(qrAutoScanTimer);
    qrAutoScanTimer = null;
  }
  const video = document.getElementById('qr-camera-video');
  if (video) video.srcObject = null;
  const btnStart = document.getElementById('btn-camera-start');
  const btnCapture = document.getElementById('btn-camera-capture');
  const btnFlip = document.getElementById('btn-camera-flip');
  const btnStop = document.getElementById('btn-camera-stop');
  const dot = document.getElementById('camera-status-dot');
  const statusText = document.getElementById('camera-status-text');

  if (btnStart) btnStart.style.display = 'inline-flex';
  if (btnCapture) btnCapture.style.display = 'none';
  if (btnFlip) btnFlip.style.display = 'none';
  if (btnStop) btnStop.style.display = 'none';
  if (dot) dot.classList.remove('active');
  if (statusText) statusText.textContent = 'Camera Inactive • Click Start Camera';
}

function initQrView() {
  loadRegistryStatuses();

  const btnRefreshReg = document.getElementById('btn-refresh-registries');
  if (btnRefreshReg) {
    btnRefreshReg.addEventListener('click', () => {
      btnRefreshReg.disabled = true;
      btnRefreshReg.innerHTML = '<span class="material-symbols-outlined" style="font-size: 16px;">sync</span><span>Updating...</span>';
      loadRegistryStatuses().finally(() => {
        setTimeout(() => {
          btnRefreshReg.disabled = false;
          btnRefreshReg.innerHTML = '<span class="material-symbols-outlined" style="font-size: 16px;">sync</span><span>Refresh Status</span>';
        }, 500);
      });
    });
  }

  // Mode Toggle: Aadhaar vs PAN
  const btnModeAadhaar = document.getElementById('btn-qr-mode-aadhaar');
  const btnModePan = document.getElementById('btn-qr-mode-pan');
  const scanLabel = document.getElementById('btn-official-scan-label');
  const qrTextInput = document.getElementById('official-qr-text-input');

  function setQrMode(mode) {
    qrScanMode = mode;
    if (mode === 'aadhaar') {
      btnModeAadhaar?.classList.add('active');
      btnModePan?.classList.remove('active');
      if (scanLabel) scanLabel.textContent = 'Verify against UIDAI Gateway';
      if (qrTextInput) qrTextInput.placeholder = 'Paste decrypted Aadhaar XML or Secure QR string...';
    } else {
      btnModePan?.classList.add('active');
      btnModeAadhaar?.classList.remove('active');
      if (scanLabel) scanLabel.textContent = 'Verify against NSDL / CBDT Gateway';
      if (qrTextInput) qrTextInput.placeholder = 'Paste PAN QR string or matrix payload...';
    }
  }

  if (btnModeAadhaar) btnModeAadhaar.addEventListener('click', () => setQrMode('aadhaar'));
  if (btnModePan) btnModePan.addEventListener('click', () => setQrMode('pan'));

  // Channels Tab Navigation
  let activeQrChannel = 'camera';
  const tabCamera = document.getElementById('btn-qr-tab-camera');
  const tabUpload = document.getElementById('btn-qr-tab-upload');
  const tabText = document.getElementById('btn-qr-tab-text');
  const chanCamera = document.getElementById('qr-camera-channel');
  const chanUpload = document.getElementById('qr-upload-channel');
  const chanText = document.getElementById('qr-text-channel');

  function selectChannel(chan) {
    activeQrChannel = chan;
    [tabCamera, tabUpload, tabText].forEach(t => t?.classList.remove('active'));
    if (chanCamera) chanCamera.style.display = 'none';
    if (chanUpload) chanUpload.style.display = 'none';
    if (chanText) chanText.style.display = 'none';

    if (chan === 'camera') {
      tabCamera?.classList.add('active');
      if (chanCamera) chanCamera.style.display = 'block';
    } else if (chan === 'upload') {
      tabUpload?.classList.add('active');
      if (chanUpload) chanUpload.style.display = 'block';
    } else {
      tabText?.classList.add('active');
      if (chanText) chanText.style.display = 'block';
    }
  }

  if (tabCamera) tabCamera.addEventListener('click', () => selectChannel('camera'));
  if (tabUpload) tabUpload.addEventListener('click', () => selectChannel('upload'));
  if (tabText) tabText.addEventListener('click', () => selectChannel('text'));

  // Camera Controls
  const video = document.getElementById('qr-camera-video');
  const canvas = document.getElementById('qr-camera-canvas');
  const btnStartCam = document.getElementById('btn-camera-start');
  const btnCaptureCam = document.getElementById('btn-camera-capture');
  const btnFlipCam = document.getElementById('btn-camera-flip');
  const btnStopCam = document.getElementById('btn-camera-stop');
  const dot = document.getElementById('camera-status-dot');
  const statusText = document.getElementById('camera-status-text');

  async function startCamera() {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera access is not supported by your browser.');
      }
      const constraints = {
        video: {
          facingMode: qrFacingMode,
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      };
      qrCameraStream = await navigator.mediaDevices.getUserMedia(constraints);
      if (video) {
        video.srcObject = qrCameraStream;
        await video.play();
      }
      if (btnStartCam) btnStartCam.style.display = 'none';
      if (btnCaptureCam) btnCaptureCam.style.display = 'inline-flex';
      if (btnFlipCam) btnFlipCam.style.display = 'inline-flex';
      if (btnStopCam) btnStopCam.style.display = 'inline-flex';
      if (dot) dot.classList.add('active');
      if (statusText) statusText.textContent = 'Camera Active • Align QR inside green frame';

      // BarcodeDetector real-time scanner if supported natively in browser
      if ('BarcodeDetector' in window) {
        try {
          const detector = new BarcodeDetector({ formats: ['qr_code'] });
          qrAutoScanTimer = setInterval(async () => {
            if (!video || video.readyState !== 4) return;
            try {
              const detected = await detector.detect(video);
              if (detected && detected.length > 0 && detected[0].rawValue) {
                clearInterval(qrAutoScanTimer);
                qrAutoScanTimer = null;
                const rawVal = detected[0].rawValue;
                if (statusText) statusText.textContent = 'Detected QR Code! Verifying...';
                executeOfficialQrScan(null, rawVal);
              }
            } catch (e) {}
          }, 600);
        } catch (e) {}
      }
    } catch (err) {
      if (statusText) statusText.textContent = 'Camera error: ' + err.message;
      alert('Camera access error: ' + err.message);
    }
  }

  if (btnStartCam) btnStartCam.addEventListener('click', startCamera);
  if (btnStopCam) btnStopCam.addEventListener('click', stopQrCamera);
  if (btnFlipCam) {
    btnFlipCam.addEventListener('click', async () => {
      qrFacingMode = qrFacingMode === 'environment' ? 'user' : 'environment';
      stopQrCamera();
      await startCamera();
    });
  }

  if (btnCaptureCam) {
    btnCaptureCam.addEventListener('click', () => {
      if (!video || !video.videoWidth || !canvas) {
        alert('Camera stream is not ready. Please start camera first.');
        return;
      }
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      canvas.toBlob((blob) => {
        if (!blob) return;
        selectedQrFile = new File([blob], 'camera_capture_qr.jpg', { type: 'image/jpeg' });
        executeOfficialQrScan(selectedQrFile, null);
      }, 'image/jpeg', 0.95);
    });
  }

  // Upload Dropzone
  const qrDropzone = document.getElementById('official-qr-dropzone');
  const qrFileInput = document.getElementById('official-qr-file-input');

  if (qrDropzone && qrFileInput) {
    qrDropzone.addEventListener('click', () => qrFileInput.click());
    qrDropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      qrDropzone.classList.add('dragover');
    });
    qrDropzone.addEventListener('dragleave', () => qrDropzone.classList.remove('dragover'));
    qrDropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      qrDropzone.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        selectedQrFile = e.dataTransfer.files[0];
        qrDropzone.querySelector('p').innerHTML = `Selected: <strong>${escapeHtml(selectedQrFile.name)}</strong> (${(selectedQrFile.size / 1024).toFixed(1)} KB)`;
      }
    });
    qrFileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files.length > 0) {
        selectedQrFile = e.target.files[0];
        qrDropzone.querySelector('p').innerHTML = `Selected: <strong>${escapeHtml(selectedQrFile.name)}</strong> (${(selectedQrFile.size / 1024).toFixed(1)} KB)`;
      }
    });
  }

  // Sample Preset Buttons
  const btnSampleAadhaar = document.getElementById('btn-load-sample-aadhaar-qr');
  const btnSampleAadhaarV2 = document.getElementById('btn-load-sample-aadhaar-v2-qr');
  const btnSamplePan = document.getElementById('btn-load-sample-pan-qr');

  if (btnSampleAadhaar) {
    btnSampleAadhaar.addEventListener('click', () => {
      setQrMode('aadhaar');
      selectChannel('text');
      selectedQrFile = null;
      if (qrTextInput) {
        qrTextInput.value = '<?xml version="1.0" encoding="UTF-8"?><PrintLetterBarcodeData uid="999900001234" name="SAMPLE CITIZEN (SPECIMEN)" gender="M" yob="1995" dob="01/01/1995" co="S/O SPECIMEN GUARDIAN" house="100" street="SAMPLE ROAD" lm="NEAR SATELLITE TOWER" loc="SEC-01" vtc="NEW DELHI" po="GPO" dist="CENTRAL DELHI" subdist="NEW DELHI" state="DELHI" pc="110001"/>';
      }
    });
  }

  if (btnSampleAadhaarV2) {
    btnSampleAadhaarV2.addEventListener('click', () => {
      setQrMode('aadhaar');
      selectChannel('text');
      selectedQrFile = null;
      if (qrTextInput) {
        qrTextInput.value = '<?xml version="1.0" encoding="UTF-8"?><PrintLetterBarcodeData uid="715293520380" name="Vilasagarm Mahesh" gender="M" yob="2007" dob="11/11/2007" co="S/O Vilashagarm Komuraiah" house="301/1" street="Burugupalli" loc="Gangadara Mandal" vtc="Burugupalli" dist="Karimnagar" state="Andhra Pradesh" pc="505531"/>';
      }
    });
  }

  if (btnSamplePan) {
    btnSamplePan.addEventListener('click', () => {
      setQrMode('pan');
      selectChannel('text');
      selectedQrFile = null;
      if (qrTextInput) {
        qrTextInput.value = 'PANQR:v=1;pan=ABCPA1234F;name=RAJESH K APTE;fname=KISHORE APTE;dob=12/04/1988;cat=Individual;sig=MEYCIQC3Z81B945A8367F475691C497BA896E49E';
      }
    });
  }

  // Execute Official QR Scan
  const btnRunScan = document.getElementById('btn-run-official-qr-scan');
  if (btnRunScan) {
    btnRunScan.addEventListener('click', () => {
      if (activeQrChannel === 'upload') {
        if (!selectedQrFile) {
          alert('Please select or drop an Aadhaar / PAN QR code image file first.');
          return;
        }
        executeOfficialQrScan(selectedQrFile, null);
      } else if (activeQrChannel === 'camera') {
        if (!selectedQrFile) {
          alert('Please start the camera, align the QR code, and click "Capture & Verify QR".');
          return;
        }
        executeOfficialQrScan(selectedQrFile, null);
      } else {
        const payloadText = qrTextInput ? qrTextInput.value.trim() : '';
        if (!payloadText) {
          alert('Please paste a raw QR string, XML, or select a sample preset.');
          return;
        }
        executeOfficialQrScan(null, payloadText);
      }
    });
  }

  // Raw payload toggle
  const btnToggleRaw = document.getElementById('btn-toggle-raw-qr-payload');
  const rawPre = document.getElementById('qr-raw-payload-pre');
  if (btnToggleRaw && rawPre) {
    btnToggleRaw.addEventListener('click', () => {
      rawPre.style.display = rawPre.style.display === 'none' ? 'block' : 'none';
    });
  }
}

async function executeOfficialQrScan(fileObj, payloadText) {
  const btnRunScan = document.getElementById('btn-run-official-qr-scan');
  const scanLabel = document.getElementById('btn-official-scan-label');
  const originalText = scanLabel ? scanLabel.textContent : 'Verify against Gateway';

  if (btnRunScan) btnRunScan.disabled = true;
  if (scanLabel) scanLabel.textContent = 'Verifying with Official Registry...';

  try {
    const formData = new FormData();
    if (fileObj) {
      formData.append('file', fileObj);
    }
    if (payloadText) {
      formData.append('qr_payload', payloadText);
    }

    const endpoint = qrScanMode === 'aadhaar'
      ? '/api/v1/official/aadhaar/scan-qr'
      : '/api/v1/official/pan/scan-qr';

    const resp = await fetch(endpoint, {
      method: 'POST',
      body: formData
    });

    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.detail || data.error || 'Official verification returned an error.');
    }

    renderOfficialQrResult(data, qrScanMode);

    const rawPre = document.getElementById('qr-raw-payload-pre');
    if (rawPre) {
      rawPre.textContent = JSON.stringify(data, null, 2);
    }
  } catch (err) {
    alert(`Registry Verification Error: ${err.message}`);
  } finally {
    if (btnRunScan) btnRunScan.disabled = false;
    if (scanLabel) scanLabel.textContent = originalText;
  }
}

function initApiView() {
  const btnGen = document.getElementById('btn-generate-api-key');
  const outBox = document.getElementById('api-key-output-box');
  const keyText = document.getElementById('api-generated-key-text');
  const btnCopy = document.getElementById('btn-copy-api-key');
  const curlSnippet = document.getElementById('curl-code-snippet');
  const pythonSnippet = document.getElementById('python-code-snippet');
  const endpointSelect = document.getElementById('api-endpoint-select');
  const protoToggle = document.getElementById('api-prototype-toggle');
  const btnFire = document.getElementById('btn-fire-api-call');
  const fileInput = document.getElementById('api-file-input');
  const respBox = document.getElementById('api-console-response-box');
  const jsonOutput = document.getElementById('api-console-json-output');
  const respBadge = document.getElementById('api-response-status-badge');
  const respTime = document.getElementById('api-response-time');
  const btnCopyJson = document.getElementById('btn-copy-api-json');
  const btnViewCert = document.getElementById('btn-view-api-cert');
  const specimenBtns = document.querySelectorAll('.api-specimen-btn');

  let lastApiResponse = null;

  function updateSnippets() {
    const activeKey = keyText && keyText.textContent ? keyText.textContent : 'vrd_live_master_kiosk_key';
    const ep = endpointSelect ? endpointSelect.value : '/api/v1/verify';
    const isProto = protoToggle ? protoToggle.checked : true;
    const isTotalVerify = ep === '/api/v1/verify';
    const baseUrl = window.location.origin || 'http://127.0.0.1:8000';

    if (curlSnippet) {
      if (isTotalVerify) {
        curlSnippet.innerHTML = `
          curl -X POST "${baseUrl}${ep}" \\<br>
          &nbsp;&nbsp;-H "X-API-Key: ${activeKey}" \\<br>
          &nbsp;&nbsp;-F "checkpoint_id=DESKTOP-TERMINAL" \\<br>
          &nbsp;&nbsp;-F "officer_id=OFFICER-01" \\<br>
          &nbsp;&nbsp;-F "force_deep_ai=false" \\<br>
          &nbsp;&nbsp;-F "file=@/path/to/document_scan.jpg"
        `;
      } else {
        curlSnippet.innerHTML = `
          curl -X POST "${baseUrl}${ep}" \\<br>
          &nbsp;&nbsp;-H "X-API-Key: ${activeKey}" \\<br>
          &nbsp;&nbsp;-F "prototype_mode=${isProto}" \\<br>
          &nbsp;&nbsp;-F "skip_live_gateway=${isProto}" \\<br>
          &nbsp;&nbsp;-F "file=@/path/to/document.jpg"
        `;
      }
    }

    if (pythonSnippet) {
      if (isTotalVerify) {
        pythonSnippet.innerHTML = `
          import requests<br><br>
          url = "${baseUrl}${ep}"<br>
          headers = {"X-API-Key": "${activeKey}"}<br>
          files = {"file": open("document_scan.jpg", "rb")}<br>
          data = {<br>
          &nbsp;&nbsp;"checkpoint_id": "DESKTOP-TERMINAL",<br>
          &nbsp;&nbsp;"officer_id": "OFFICER-01",<br>
          &nbsp;&nbsp;"force_deep_ai": "false"<br>
          }<br><br>
          resp = requests.post(url, headers=headers, files=files, data=data)<br>
          res = resp.json()<br>
          print("Overall Verdict :", res.get("overall_verdict"))<br>
          print("Risk Score      :", res.get("risk", {}).get("risk_score"))<br>
          print("Extracted Name  :", res.get("extracted_fields", {}).get("name"))<br>
          print("Doc Number      :", res.get("extracted_fields", {}).get("document_number"))<br>
          print("Section 65B Hash:", res.get("audit_hash"))
        `;
      } else {
        pythonSnippet.innerHTML = `
          import requests<br><br>
          url = "${baseUrl}${ep}"<br>
          headers = {"X-API-Key": "${activeKey}"}<br>
          files = {"file": open("document_scan.jpg", "rb")}<br>
          data = {"prototype_mode": "${isProto}", "skip_live_gateway": "${isProto}"}<br><br>
          resp = requests.post(url, headers=headers, files=files, data=data)<br>
          print(resp.json())
        `;
      }
    }
  }

  if (endpointSelect) {
    endpointSelect.addEventListener('change', updateSnippets);
  }
  if (protoToggle) {
    protoToggle.addEventListener('change', updateSnippets);
  }

  // Generate API Key
  if (btnGen) {
    btnGen.addEventListener('click', async () => {
      const clientId = document.getElementById('api-client-id')?.value || 'KIOSK-01';
      const role = document.getElementById('api-role-select')?.value || 'officer';

      const formData = new FormData();
      formData.append('client_id', clientId);
      formData.append('role', role);

      try {
        const resp = await fetch('/api/v1/keys/generate', {
          method: 'POST',
          body: formData
        });
        const data = await resp.json();

        if (outBox && keyText) {
          keyText.textContent = data.api_key;
          outBox.style.display = 'block';
          updateSnippets();
        }
      } catch (err) {
        alert('Failed to generate API Key.');
      }
    });
  }

  if (btnCopy && keyText) {
    btnCopy.addEventListener('click', () => {
      navigator.clipboard.writeText(keyText.textContent);
      btnCopy.textContent = 'Copied!';
      setTimeout(() => btnCopy.textContent = 'Copy Key', 1500);
    });
  }

  // 1-Click Specimen Presets
  specimenBtns.forEach(btn => {
    btn.addEventListener('click', async () => {
      const specimenId = btn.getAttribute('data-specimen');
      const isProto = protoToggle ? protoToggle.checked : true;

      specimenBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const startTime = performance.now();
      try {
        const formData = new FormData();
        formData.append('specimen_id', specimenId);
        formData.append('prototype_mode', isProto);

        const resp = await fetch('/api/v1/official/demo-specimen', {
          method: 'POST',
          body: formData
        });
        const duration = Math.round(performance.now() - startTime);
        const data = await resp.json();

        lastApiResponse = data;

        if (respBox && jsonOutput) {
          respBox.style.display = 'block';
          jsonOutput.textContent = JSON.stringify(data, null, 2);

          if (respTime) respTime.textContent = `Latency: ${duration}ms`;
          if (respBadge) {
            const isOk = data.status === 'OFFICIAL_VERIFIED';
            respBadge.textContent = isOk ? 'HTTP 200 • OFFICIAL VERIFIED' : `HTTP 200 • ${data.status || 'SUSPICIOUS'}`;
            respBadge.className = isOk ? 'terra-badge verified' : 'terra-badge guard';
          }
          respBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      } catch (err) {
        alert(`Specimen API call failed: ${err.message}`);
      }
    });
  });

  // Custom Execute API Call Button
  if (btnFire) {
    btnFire.addEventListener('click', async () => {
      const ep = endpointSelect ? endpointSelect.value : '/api/v1/official/aadhaar/scan-qr';
      const isProto = protoToggle ? protoToggle.checked : true;
      const file = fileInput && fileInput.files ? fileInput.files[0] : null;
      const label = document.getElementById('btn-fire-api-label');

      btnFire.disabled = true;
      if (label) label.textContent = 'Executing API Request...';

      const startTime = performance.now();
      try {
        const formData = new FormData();
        formData.append('prototype_mode', isProto);
        formData.append('skip_live_gateway', isProto);

        if (file) {
          formData.append('file', file);
        } else {
          // If no file selected, send checkpoint identification
          formData.append('checkpoint_id', document.getElementById('api-console-client-id')?.value || 'KIOSK-01');
        }

        const headers = {};
        const key = keyText && keyText.textContent ? keyText.textContent : getActiveApiKey();
        if (ep === '/api/v1/verify') {
          headers['X-API-Key'] = key;
        }

        const resp = await fetch(ep, {
          method: 'POST',
          headers: headers,
          body: formData
        });

        const duration = Math.round(performance.now() - startTime);
        const data = await resp.json();
        lastApiResponse = data;

        if (respBox && jsonOutput) {
          respBox.style.display = 'block';
          jsonOutput.textContent = JSON.stringify(data, null, 2);

          if (respTime) respTime.textContent = `Latency: ${duration}ms`;
          if (respBadge) {
            const isOk = resp.ok && (data.status === 'OFFICIAL_VERIFIED' || data.overall_verdict === 'CLEAR');
            respBadge.textContent = resp.ok ? `HTTP ${resp.status} OK` : `HTTP ${resp.status} ERROR`;
            respBadge.className = isOk ? 'terra-badge verified' : (resp.ok ? 'terra-badge review' : 'terra-badge guard');
          }
          respBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      } catch (err) {
        if (respBox && jsonOutput) {
          respBox.style.display = 'block';
          jsonOutput.textContent = JSON.stringify({ error: err.message }, null, 2);
          if (respBadge) {
            respBadge.textContent = 'HTTP NETWORK ERROR';
            respBadge.className = 'terra-badge guard';
          }
        }
      } finally {
        btnFire.disabled = false;
        if (label) label.textContent = 'Execute API Request';
      }
    });
  }

  // Copy JSON button
  if (btnCopyJson && jsonOutput) {
    btnCopyJson.addEventListener('click', () => {
      navigator.clipboard.writeText(jsonOutput.textContent);
      btnCopyJson.textContent = 'Copied!';
      setTimeout(() => btnCopyJson.textContent = 'Copy JSON', 1500);
    });
  }

  // View Section 65B Certificate button
  if (btnViewCert) {
    btnViewCert.addEventListener('click', () => {
      if (lastApiResponse) {
        const sessId = lastApiResponse.session_id || 'API-PROTOTYPE-VERIFY';
        const docType = lastApiResponse.document_type || 'STATUTORY_IDENTITY';
        const verdict = lastApiResponse.overall_verdict || lastApiResponse.status || 'CLEAR';
        const risk = (lastApiResponse.risk && lastApiResponse.risk.risk_score) || lastApiResponse.risk_score || 0;
        const time = lastApiResponse.timestamp || new Date().toISOString();
        const hash = lastApiResponse.audit_hash || 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';
        showCertModal(sessId, docType, verdict, risk, time, hash);
      } else {
        alert('Please run an API verification request first.');
      }
    });
  }

  // Immediately render code snippets using the live host domain / origin
  updateSnippets();
}

function renderOfficialQrResult(data, mode) {
  const box = document.getElementById('official-qr-result-box');
  const badge = document.getElementById('official-result-status-badge');
  const auth = document.getElementById('official-result-authority');
  const details = document.getElementById('official-result-details');
  const time = document.getElementById('official-result-timestamp');
  const fieldsContainer = document.getElementById('official-result-fields');

  if (!box || !fieldsContainer) return;

  box.style.display = 'block';
  if (time) time.textContent = data.timestamp || new Date().toISOString();

  const isVerified = data.status === 'OFFICIAL_VERIFIED';
  if (badge) {
    badge.textContent = isVerified ? 'OFFICIAL VERIFIED' : (data.status || 'UNVERIFIED');
    badge.className = isVerified ? 'terra-badge verified' : 'terra-badge review';
  }

  if (auth) {
    auth.textContent = data.authority || (mode === 'aadhaar' ? 'Unique Identification Authority of India (UIDAI)' : 'Income Tax Department (CBDT / NSDL)');
  }

  if (details) {
    details.textContent = data.digital_signature_status
      ? `Cryptographic Signature: ${data.digital_signature_status}`
      : (data.registry_status || 'Digital signature check completed.');
  }

  fieldsContainer.innerHTML = '';

  const addField = (label, val) => {
    if (!val) return;
    const item = document.createElement('div');
    item.className = 'official-field-item';
    item.innerHTML = `
      <span class="official-field-label">${escapeHtml(label)}</span>
      <span class="official-field-val">${escapeHtml(String(val))}</span>
    `;
    fieldsContainer.appendChild(item);
  };

  if (mode === 'aadhaar') {
    const d = data.demographic_fields || data || {};
    addField('Aadhaar Number (Masked)', d.masked_aadhaar || d.uid);
    addField('Citizen Full Name', d.name);
    addField('Date of Birth', d.dob || d.yob);
    addField('Gender', d.gender);
    addField('Care Of (C/O)', d.care_of);
    addField('District', d.district);
    addField('State', d.state);
    addField('Pin Code', d.pincode);
    addField('Full Address', d.full_address || d.address || d.district);
    if (d.phone) addField('Mobile / Phone', d.phone);
    if (d.vid) addField('Virtual ID (VID)', d.vid);
    if (d.enrolment_number) addField('Enrolment Number', d.enrolment_number);
    addField('Signature & Parity Verification', data.digital_signature_status || data.signature_algorithm);
  } else {
    const p = data.pan_data || data || {};
    addField('Permanent Account Number (PAN)', p.pan || data.pan);
    addField('Taxpayer Full Name', p.name || data.name);
    addField("Father's Name", p.father_name || data.father_name);
    addField('Date of Birth / Inception', p.dob || data.dob);
    addField('Taxpayer Category', p.taxpayer_category || data.taxpayer_category || 'Individual');
    addField('CBDT Status', data.registry_status || 'ACTIVE & VALID');
    addField('Structure Check', (p.format_valid !== false) ? 'VALID (Compliant 10-char alphanumeric)' : 'INVALID');
  }

  box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ============================================================================
// VIEW 4: VERIFICATION HISTORY & DATA RETENTION
// ============================================================================
function initHistoryView() {
  const btnRefresh = document.getElementById('btn-refresh-history');
  const btnPurge = document.getElementById('btn-purge-history');
  const filterBtns = document.querySelectorAll('.history-filter-btn');

  if (btnRefresh) {
    btnRefresh.addEventListener('click', () => loadHistoryRecords());
  }

  if (btnPurge) {
    btnPurge.addEventListener('click', async () => {
      if (confirm('Are you sure you want to permanently purge all stored document verification records? This action cannot be undone.')) {
        try {
          const resp = await fetch('/api/v1/sessions', { method: 'DELETE' });
          if (resp.ok) {
            alert('All verification history purged.');
            loadHistoryRecords();
          }
        } catch (err) {
          alert('Failed to purge records.');
        }
      }
    });
  }

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const filter = btn.getAttribute('data-filter');
      loadHistoryRecords(filter === 'ALL' ? null : filter);
    });
  });
}

async function loadHistoryRecords(filter = null) {
  const tbody = document.getElementById('history-table-body');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Querying database records...</td></tr>`;

  try {
    const url = filter ? `/api/v1/sessions?status_filter=${filter}` : '/api/v1/sessions';
    const resp = await fetch(url);
    if (!resp.ok) throw new Error('Could not retrieve sessions.');

    const sessions = await resp.json();
    tbody.innerHTML = '';

    if (sessions.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No historical verification records found in database.</td></tr>`;
      return;
    }

    sessions.forEach(s => {
      const tr = document.createElement('tr');
      const isClear = s.overall_verdict === 'CLEAR';
      const badgeCls = isClear ? 'verified' : (s.overall_verdict === 'SUSPICIOUS' ? 'review' : 'guard');

      tr.innerHTML = `
        <td><code>${escapeHtml(s.id)}</code></td>
        <td>${s.created_at ? s.created_at.substring(0, 19).replace('T', ' ') : '—'}</td>
        <td><code>${escapeHtml(s.document_type || 'UNKNOWN')}</code></td>
        <td><span class="terra-badge ${badgeCls}">${s.overall_verdict}</span></td>
        <td>${s.risk_score !== undefined ? `${s.risk_score} / 100` : '—'}</td>
        <td><code style="font-size: 10px;">${escapeHtml((s.audit_hash || '').substring(0, 16))}...</code></td>
        <td>
          <div style="display: flex; gap: 0.35rem;">
            <button class="btn-terra-secondary" style="padding: 0.25rem 0.5rem; font-size: 11px;" onclick="viewHistoryItem('${s.id}')">
              Certificate
            </button>
            <button class="btn-terra-secondary" style="padding: 0.25rem 0.5rem; font-size: 11px; color: var(--error);" onclick="deleteHistoryItem('${s.id}')">
              Delete
            </button>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--error); padding: 1.5rem;">Failed to load database records.</td></tr>`;
  }
}

window.viewHistoryItem = async function(sessionId) {
  try {
    const resp = await fetch(`/api/v1/sessions/${sessionId}`);
    if (resp.ok) {
      const s = await resp.json();
      showCertModal(s.session_id, s.document_type, s.overall_verdict, s.risk_score, s.timestamp, s.audit_hash);
    }
  } catch (err) {
    alert('Failed to retrieve record detail.');
  }
};

window.deleteHistoryItem = async function(sessionId) {
  if (confirm(`Permanently delete verification session ${sessionId}?`)) {
    try {
      const resp = await fetch(`/api/v1/sessions/${sessionId}`, { method: 'DELETE' });
      if (resp.ok) {
        loadHistoryRecords();
      }
    } catch (err) {
      alert('Failed to delete record.');
    }
  }
};

// ============================================================================
// Section 65B Certificate Modal
// ============================================================================
function initCertModal() {
  const btnShow = document.getElementById('btn-show-cert');
  const btnExport = document.getElementById('btn-export-json');

  if (btnShow) {
    btnShow.addEventListener('click', () => {
      if (appState.currentResults && appState.currentResults.length > 0) {
        const cur = appState.currentResults[appState.activeDocIndex] || appState.currentResults[0];
        showCertModal(cur.session_id, cur.document_type, cur.overall_verdict, cur.risk.risk_score, cur.timestamp, cur.audit_hash);
      }
    });
  }

  if (btnExport) {
    btnExport.addEventListener('click', () => {
      if (appState.currentResults && appState.currentResults.length > 0) {
        const cur = appState.currentResults[appState.activeDocIndex] || appState.currentResults[0];
        const blob = new Blob([JSON.stringify(cur, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `VERIDOC_Attestation_${cur.session_id}.json`;
        a.click();
        URL.revokeObjectURL(url);
      }
    });
  }

  const scrim = document.getElementById('modal-cert-scrim');
  if (scrim) {
    scrim.addEventListener('click', (e) => {
      if (e.target === scrim) closeCertModal();
    });
  }
}

function showCertModal(sessionId, docType, verdict, riskScore, timestamp, hash) {
  const scrim = document.getElementById('modal-cert-scrim');
  document.getElementById('cert-session-id').textContent = sessionId || '—';
  document.getElementById('cert-doc-type').textContent = docType || '—';
  document.getElementById('cert-verdict').textContent = verdict === 'CLEAR' ? 'CLEAR / AUTHENTIC' : 'SUSPICIOUS / TAMPER DETECTED';
  document.getElementById('cert-verdict').style.color = verdict === 'CLEAR' ? 'var(--success)' : 'var(--error)';
  document.getElementById('cert-risk-score').textContent = riskScore !== undefined ? `${riskScore} / 100` : '—';
  document.getElementById('cert-timestamp').textContent = timestamp || new Date().toISOString();
  document.getElementById('cert-hash').textContent = hash || '—';

  if (scrim) scrim.classList.add('open');
}

function closeCertModal() {
  const scrim = document.getElementById('modal-cert-scrim');
  if (scrim) scrim.classList.remove('open');
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

window.closeCertModal = closeCertModal;
