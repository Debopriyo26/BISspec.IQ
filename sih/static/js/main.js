/* StandardMatch AI - "Ledger & Marigold" Theme JS Logic
   (Same behaviour as before — only a single hardcoded accent colour below
   was retuned to match the new warm palette; every other function,
   id, and endpoint is untouched so your Flask routes keep working.) */
// ==============================================================================
// 1. REGISTERED USER SEARCH HISTORY SYSTEM
// Tracks, marks, and renders what was previously searched by the logged-in user.
// Synchronizes with backend /api/user/history and client-side storage.
// ==============================================================================
// Bulletproof JSON fetch helper that shields against raw HTML parse errors (e.g. Unexpected token '<')
async function safeFetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const contentType = response.headers.get('content-type') || '';

    if (!contentType.includes('application/json')) {
        const text = await response.text();
        if (text.includes('<!DOCTYPE') || response.status === 401 || response.status === 302) {
            throw new Error("Authentication or session state refreshed. Please try again or sign in.");
        }
        throw new Error(`Server returned unexpected response (${response.status})`);
    }

    const data = await response.json();
    return { response, data };
}

let _userSearchHistoryList = [];

function getUserHistoryStorageKey() {
    const historyGroup = document.getElementById('user-history-group');
    const username = historyGroup ? (historyGroup.dataset.username || 'Officer') : 'Officer';
    return `bisspec_iq_history_${username.toLowerCase()}`;
}

async function initUserSearchHistory() {
    const historyGroup = document.getElementById('user-history-group');
    if (!historyGroup) return;

    const storageKey = getUserHistoryStorageKey();

    // 1. Try fetching from backend /api/user/history
    try {
        const { response, data } = await safeFetchJson('/api/user/history');
        if (response.ok && data.success && Array.isArray(data.history) && data.history.length > 0) {
            _userSearchHistoryList = data.history;
            localStorage.setItem(storageKey, JSON.stringify(_userSearchHistoryList));
            renderUserSearchHistory();
            return;
        }
    } catch (e) {
        console.warn("Could not fetch remote user history; falling back to local storage:", e);
    }

    // 2. Fallback to localStorage
    const saved = localStorage.getItem(storageKey);
    if (saved) {
        try {
            _userSearchHistoryList = JSON.parse(saved) || [];
        } catch (e) {
            _userSearchHistoryList = [];
        }
    }
    renderUserSearchHistory();
}

function renderUserSearchHistory() {
    const selectEl = document.getElementById('user-history-select');
    const countBadge = document.getElementById('user-history-count');
    const chipsContainer = document.getElementById('history-chips-container');
    if (!selectEl) return;

    const count = _userSearchHistoryList.length;
    if (countBadge) {
        countBadge.textContent = count === 1 ? '1 Search' : `${count} Searches`;
    }

    // Populate dropdown
    selectEl.innerHTML = '';
    if (count === 0) {
        selectEl.innerHTML = '<option value="">-- No Previous Searches Yet --</option>';
        if (chipsContainer) chipsContainer.style.display = 'none';
        return;
    }

    const defaultOpt = document.createElement('option');
    defaultOpt.value = '';
    defaultOpt.textContent = `-- Select from Previous Searches (${count}) --`;
    selectEl.appendChild(defaultOpt);

    _userSearchHistoryList.forEach((item, idx) => {
        const opt = document.createElement('option');
        opt.value = item.query;
        // Truncate for dropdown readability
        const qShort = item.query.length > 55 ? item.query.substring(0, 52) + '...' : item.query;
        const timeStr = item.timestamp ? ` [${item.timestamp.split(' ')[1] || item.timestamp}]` : '';
        opt.textContent = `${idx + 1}. ${qShort}${timeStr}`;
        selectEl.appendChild(opt);
    });

    // Populate interactive quick-chips (show up to 4 most recent searches)
    if (chipsContainer) {
        chipsContainer.innerHTML = '';
        chipsContainer.style.display = 'flex';
        const recentItems = _userSearchHistoryList.slice(0, 4);
        recentItems.forEach(item => {
            const chip = document.createElement('button');
            chip.type = 'button';
            chip.className = 'history-chip';
            const shortText = item.query.length > 25 ? item.query.substring(0, 22) + '...' : item.query;
            chip.innerHTML = `<i class="fa-solid fa-clock-rotate-left"></i> ${escapeHtml(shortText)}`;
            chip.title = item.query;
            chip.onclick = (e) => {
                e.preventDefault();
                handleHistorySelect(item.query);
            };
            chipsContainer.appendChild(chip);
        });
    }
}

async function saveSearchToHistory(query, matchesCount = 0) {
    if (!query || !query.trim()) return;
    const cleanQ = query.trim();

    // Check if duplicate, remove from old position to bring to top
    _userSearchHistoryList = _userSearchHistoryList.filter(h => h.query.toLowerCase() !== cleanQ.toLowerCase());
    const newEntry = {
        id: 'hist_' + Date.now(),
        query: cleanQ,
        timestamp: new Date().toLocaleTimeString(),
        matches_count: matchesCount
    };
    _userSearchHistoryList.unshift(newEntry);
    if (_userSearchHistoryList.length > 30) {
        _userSearchHistoryList = _userSearchHistoryList.slice(0, 30);
    }

    // Save to localStorage
    const storageKey = getUserHistoryStorageKey();
    localStorage.setItem(storageKey, JSON.stringify(_userSearchHistoryList));

    renderUserSearchHistory();

    // Push to backend asynchronously
    try {
        await fetch('/api/user/history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: cleanQ, matches_count: matchesCount })
        });
    } catch (e) {
        // Silently tolerate if offline
    }
}

function handleHistorySelect(queryText) {
    if (!queryText) return;
    const queryInput = document.getElementById('query-input');
    if (!queryInput) return;

    queryInput.value = queryText;
    queryInput.focus();
    queryInput.classList.remove('spec-updated-anim');
    void queryInput.offsetWidth;
    queryInput.classList.add('spec-updated-anim');
    setTimeout(() => queryInput.classList.remove('spec-updated-anim'), 800);

    showToast(`Loaded previous search: "${queryText.substring(0, 40)}${queryText.length > 40 ? '...' : ''}"`);

    // Reset dropdown select to default placeholder
    const selectEl = document.getElementById('user-history-select');
    if (selectEl) selectEl.value = '';
}

async function clearUserSearchHistory() {
    if (_userSearchHistoryList.length === 0) {
        showToast("Search history is already empty.");
        return;
    }

    if (!confirm("Are you sure you want to clear your previous search history?")) {
        return;
    }

    _userSearchHistoryList = [];
    const storageKey = getUserHistoryStorageKey();
    localStorage.removeItem(storageKey);
    renderUserSearchHistory();

    try {
        await fetch('/api/user/history', { method: 'DELETE' });
    } catch (e) {
        console.warn("Backend clear history error:", e);
    }

    showToast("Previous search history cleared.");
}

function handleLanguageChange(selectedLang) {
    const lang = (selectedLang || 'ENGLISH').toUpperCase();
    showToast(`Language set to ${lang}. Recommendations will reflect regional text.`);
}

document.addEventListener('DOMContentLoaded', () => {
    fetchDatasetCount();
    loadGemTenders();
    setupDragAndDrop(); // Initialize Interactive Drag & Drop
    initUserSearchHistory(); // Initialize Registered User Search History
});

/**
 * Navigates directly to a platform feature section with smooth scrolling & focus animation.
 */
function navigateToTool(sectionId, event) {
    if (event) {
        event.preventDefault();
    }

    const heroSec = document.getElementById('hero-section');
    const dashSec = document.getElementById('dashboard-section');

    // Switch to Dashboard SPA view if currently on Hero
    if (dashSec && !dashSec.classList.contains('active')) {
        heroSec.classList.add('hidden');
        dashSec.classList.add('active');
        window.scrollTo({ top: 0, behavior: 'instant' });
    }

    // Scroll smoothly to target section with visual highlight feedback
    setTimeout(() => {
        const targetEl = document.getElementById(sectionId);
        if (targetEl) {
            targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });

            targetEl.classList.remove('panel-highlight');
            void targetEl.offsetWidth; // Trigger reflow for animation restart
            targetEl.classList.add('panel-highlight');
            setTimeout(() => targetEl.classList.remove('panel-highlight'), 1800);

            // Context-specific actions
            if (sectionId === 'section-gem-tenders') {
                loadGemTenders();
            } else if (sectionId === 'section-nlp-matcher') {
                const queryInput = document.getElementById('query-input');
                if (queryInput) setTimeout(() => queryInput.focus(), 350);
            }
        }
    }, 60);
}

function toggleSection(target) {
    const heroSec = document.getElementById('hero-section');
    const dashSec = document.getElementById('dashboard-section');

    if (target === 'dashboard') {
        heroSec.classList.add('hidden');
        dashSec.classList.add('active');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
        dashSec.classList.remove('active');
        heroSec.classList.remove('hidden');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function scrollToFeatures() {
    const featuresGrid = document.getElementById('features-grid');
    if (featuresGrid) {
        featuresGrid.scrollIntoView({ behavior: 'smooth' });
    }
}

function updateThresholdLabel(val) {
    const label = document.getElementById('threshold-val');
    if (label) {
        label.textContent = `${parseFloat(val).toFixed(1)}%`;
    }
}

function clearSearch() {
    document.getElementById('query-input').value = '';
    const container = document.getElementById('results-container');
    container.innerHTML = `
        <div class="empty-state">
            <div class="empty-icon"><i class="fa-solid fa-compass-drafting"></i></div>
            <div class="empty-title">Ready for Tender & GeM Analysis</div>
            <div class="empty-desc">
                BISspec.IQ automatically recommends official Bureau of Indian Standards matching your tender query or GeM Bid specifications.
            </div>
        </div>
    `;
    document.getElementById('results-title').textContent = 'Matched Standards';
    document.getElementById('results-subtitle').textContent = 'Enter procurement specifications on the left to find matching BIS standards.';
    document.getElementById('results-meta').innerHTML = '';
}

function quickSearch(presetText) {
    toggleSection('dashboard');
    const input = document.getElementById('query-input');
    input.value = presetText;

    setTimeout(() => {
        document.getElementById('recommend-form').dispatchEvent(new Event('submit'));
    }, 200);
}

function loadPresetQuery(val) {
    if (val) {
        document.getElementById('query-input').value = val;
    }
}

async function fetchDatasetCount() {
    try {
        const { data } = await safeFetchJson('/standards');
        if (data.success) {
            const counterEl = document.getElementById('dataset-counter');
            if (counterEl) {
                counterEl.innerHTML = `<i class="fa-solid fa-database"></i> Indexed Standards: ${data.count}`;
            }
        }
    } catch (err) {
        console.error("Failed to fetch dataset count:", err);
    }
}

async function loadGemTenders() {
    const listEl = document.getElementById('gem-tenders-list');
    if (!listEl) return;

    listEl.innerHTML = '<div style="text-align:center; padding:1.5rem 1rem; color:var(--text-muted);"><div class="spinner" style="border-top-color: var(--primary-blue); display:inline-block; margin-bottom: 0.5rem;"></div><div>Loading GeM Bids...</div></div>';

    try {
        const { data } = await safeFetchJson('/api/gem/tenders');

        if (!data.success || !data.tenders) {
            throw new Error(data.error || "Failed to load GeM tenders.");
        }

        let html = '';
        data.tenders.forEach(t => {
            html += `
                <div class="gem-mini-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span class="gem-bid-id"><i class="fa-solid fa-hashtag"></i> ${escapeHtml(t.gem_bid_id)}</span>
                        <span style="font-size:0.75rem; color:#8E3B16; font-weight:800;">${escapeHtml(t.quantity)}</span>
                    </div>
                    <div class="gem-item-title">${escapeHtml(t.item_name)}</div>
                    <div class="gem-ministry-text"><i class="fa-solid fa-building"></i> ${escapeHtml(t.ministry)}</div>
                    <button class="btn-gem-match" onclick="matchGemTender('${escapeHtml(t.gem_bid_id)}')">
                        <i class="fa-solid fa-wand-magic-sparkles"></i> Match BIS Standard
                    </button>
                </div>
            `;
        });
        listEl.innerHTML = html;
    } catch (err) {
        listEl.innerHTML = `<div style="color:#A23A24; font-size:0.85rem; padding:0.5rem;">Error loading GeM Bids: ${escapeHtml(err.message)}</div>`;
    }
}

async function matchGemTender(gemBidId) {
    showToast(`Analyzing GeM Bid "${gemBidId}" against BIS Database...`);

    try {
        const { response, data } = await safeFetchJson('/api/gem/match', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ gem_bid_id: gemBidId })
        });

        if (!response.ok || !data.success) {
            throw new Error(data.error || "GeM tender matching failed.");
        }

        const tender = data.gem_bid;
        document.getElementById('query-input').value = `${tender.item_name} ${tender.specifications}`;

        renderResults({
            success: true,
            query: `GeM Tender ${tender.gem_bid_id}: ${tender.item_name}`,
            total_standards: 12,
            execution_time_ms: 1.2,
            matches: data.matches
        });

        showToast(`Found matching BIS standards for GeM Tender ${gemBidId}!`);

    } catch (err) {
        showToast(`GeM Match Error: ${err.message}`);
    }
}

async function handleSearch(e) {
    e.preventDefault();

    const queryInput = document.getElementById('query-input').value.trim();
    const thresholdVal = parseFloat(document.getElementById('threshold-slider').value) / 100;
    const topNVal = parseInt(document.getElementById('top-n-select').value, 10);

    if (!queryInput) {
        showToast("Please enter a procurement specification or tender query.");
        return;
    }

    const btnSubmit = document.getElementById('btn-search-submit');
    const btnText = document.getElementById('btn-search-text');
    const originalText = btnText.textContent;

    const langSelect = document.getElementById('language-select');
    const selectedLanguage = langSelect ? langSelect.value : 'ENGLISH';

    btnSubmit.disabled = true;
    btnText.innerHTML = '<div class="spinner"></div> Finding Matching Standards...';

    try {
        const { response, data } = await safeFetchJson('/recommend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: queryInput,
                threshold: thresholdVal,
                top_n: topNVal,
                language: selectedLanguage
            })
        });

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to fetch recommendations');
        }

        renderResults(data);
        saveSearchToHistory(queryInput, (data.matches || []).length);

    } catch (error) {
        console.error("Search Error:", error);
        showToast(`Error: ${error.message}`);
        renderErrorState(error.message);
    } finally {
        btnSubmit.disabled = false;
        btnText.textContent = originalText;
    }
}

function renderResults(data) {
    const container = document.getElementById('results-container');
    const matches = data.matches || [];

    document.getElementById('results-title').textContent = `Top ${matches.length} Recommended BIS Standards`;

    let subtitleText = `Query: "${data.query.substring(0, 60)}${data.query.length > 60 ? '...' : ''}"`;
    if (data.is_multilingual && data.query_en && data.query_en !== data.query) {
        subtitleText += ` (English Spec: "${data.query_en.substring(0, 50)}${data.query_en.length > 50 ? '...' : ''}")`;
    }
    document.getElementById('results-subtitle').textContent = subtitleText;

    const metaContainer = document.getElementById('results-meta');
    let metaHtml = `
        <span><i class="fa-solid fa-bolt" style="color: var(--primary-blue);"></i> ${data.execution_time_ms} ms</span>
        <span><i class="fa-solid fa-list"></i> ${data.total_standards} Total Standards</span>
    `;

    if (data.is_multilingual && data.language_name) {
        metaHtml += `<span class="lang-badge-result"><i class="fa-solid fa-language"></i> Detected: ${escapeHtml(data.language_name)}</span>`;
    }

    metaContainer.innerHTML = metaHtml;

    if (matches.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon"><i class="fa-solid fa-magnifying-glass-minus"></i></div>
                <div class="empty-title">No Matching BIS Standards Found</div>
                <div class="empty-desc">
                    No standards matched your specification above the threshold score of ${(parseFloat(document.getElementById('threshold-slider').value)).toFixed(1)}%. Try lowering the threshold slider or adding more keywords.
                </div>
            </div>
        `;
        return;
    }

    const queryWords = (data.query_en || data.query).toLowerCase().split(/\s+/).filter(w => w.length > 3);

    let html = '';
    matches.forEach((item, index) => {
        const percentageScore = (item.score * 100).toFixed(1) + '%';

        let highlightedDesc = escapeHtml(item.description);
        queryWords.forEach(word => {
            const regex = new RegExp(`\\b(${escapeRegExp(word)})\\b`, 'gi');
            highlightedDesc = highlightedDesc.replace(regex, '<span class="kw-highlight">$1</span>');
        });

        // Dynamic GeM Product Search Redirection based on suggested standard's title or category
        const gemSearchTerm = item.title_en || item.title || item.category || item.standard_number;
        const gemProductSearchUrl = `https://mkp.gem.gov.in/search?q=${encodeURIComponent(gemSearchTerm)}`;
        const gemClauseText = item.gem_clause || `GeM MANDATORY COMPLIANCE CLAUSE: Item offered under this tender must strictly conform to BIS ${item.standard_number} - '${item.title_en || item.title}'.`;

        const hasDifferentEnglish = item.title_en && item.title_en !== item.title;

        html += `
            <div class="result-card" id="result-card-${index}" style="animation-delay: ${index * 0.1}s; opacity: 0;"
                 data-title-regional="${escapeHtml(item.title)}"
                 data-title-en="${escapeHtml(item.title_en || item.title)}"
                 data-desc-regional="${escapeHtml(item.description)}"
                 data-desc-en="${escapeHtml(item.description_en || item.description)}"
                 data-current-lang="regional">
                <div class="card-top-row">
                    <div class="card-std-no">
                        <i class="fa-solid fa-bookmark" style="color: var(--primary-blue);"></i>
                        ${escapeHtml(item.standard_number)}
                    </div>
                    <div class="badge-score">
                        <i class="fa-solid fa-bullseye"></i> ${percentageScore} Match
                    </div>
                </div>

                <div class="card-badges">
                    ${item.is_live || item.source === 'live_bis' ? `<span class="badge-live-portal"><span class="badge-live-pulse"></span> Live BIS Portal</span>` : ''}
                    <span class="badge-status">${escapeHtml(item.status)}</span>
                    <span class="badge-category">${escapeHtml(item.category)}</span>
                    <span class="badge-year">Year: ${escapeHtml(item.version_year)}</span>
                    ${data.is_multilingual ? `<span class="badge-status" style="background:#EEF2DA; color:#45601E; border-color:#C7D69B;"><i class="fa-solid fa-globe"></i> ${escapeHtml(data.language_name)}</span>` : ''}
                </div>

                <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:0.5rem;">
                    <h3 class="card-title" id="card-title-${index}">${escapeHtml(item.title)}</h3>
                    ${hasDifferentEnglish ? `
                        <button class="btn-toggle-lang" onclick="toggleCardLanguage(${index})" title="Toggle between English and Regional Translation">
                            <i class="fa-solid fa-language"></i> <span id="btn-toggle-text-${index}">Show English</span>
                        </button>
                    ` : ''}
                </div>

                <div class="card-description" id="card-desc-${index}">
                    ${highlightedDesc}
                </div>

                <div class="card-footer">
                    <div>
                        <span style="font-size: 0.78rem; color: var(--text-muted); font-weight: 500;">Standard ID: </span>
                        <span class="std-id-code">${escapeHtml(item.standard_id)}</span>
                    </div>

                    <div class="card-actions-group">
                        <button class="btn-card-action" onclick="copyToClipboard('${escapeHtml(item.standard_number)}', '${escapeHtml(item.title_en || item.title)}')">
                            <i class="fa-regular fa-copy"></i> Copy BIS
                        </button>

                        <a href="${gemProductSearchUrl}" target="_blank" rel="noopener noreferrer" class="btn-card-gem" title="Search matching products on GeM Marketplace for '${escapeHtml(gemSearchTerm)}'">
                            <i class="fa-solid fa-store"></i> GeM Portal
                        </a>

                        <button class="btn-card-gem" onclick="copyGemClause(\`${escapeJsString(gemClauseText)}\`)">
                            <i class="fa-solid fa-file-contract"></i> Copy GeM Clause
                        </button>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function toggleCardLanguage(index) {
    const card = document.getElementById(`result-card-${index}`);
    if (!card) return;

    const titleEl = document.getElementById(`card-title-${index}`);
    const descEl = document.getElementById(`card-desc-${index}`);
    const toggleBtnText = document.getElementById(`btn-toggle-text-${index}`);

    const currentLang = card.getAttribute('data-current-lang');
    if (currentLang === 'regional') {
        titleEl.textContent = card.getAttribute('data-title-en');
        descEl.textContent = card.getAttribute('data-desc-en');
        card.setAttribute('data-current-lang', 'en');
        if (toggleBtnText) toggleBtnText.textContent = "Show Regional";
    } else {
        titleEl.textContent = card.getAttribute('data-title-regional');
        descEl.textContent = card.getAttribute('data-desc-regional');
        card.setAttribute('data-current-lang', 'regional');
        if (toggleBtnText) toggleBtnText.textContent = "Show English";
    }
}

function copyGemClause(clauseText) {
    navigator.clipboard.writeText(clauseText).then(() => {
        showToast("GeM Mandatory Compliance Clause copied to clipboard!");
    }).catch(() => {
        showToast("Failed to copy GeM Clause.");
    });
}

function renderErrorState(msg) {
    const container = document.getElementById('results-container');
    container.innerHTML = `
        <div class="empty-state" style="border-color: #E5B6A0; background: #FBEAE5;">
            <div class="empty-icon" style="color: #A23A24;"><i class="fa-solid fa-triangle-exclamation"></i></div>
            <div class="empty-title" style="color: #7A2C1B;">Error Processing Recommendation</div>
            <div class="empty-desc" style="color: #A23A24;">
                ${escapeHtml(msg)}
            </div>
        </div>
    `;
}

// SETUP DRAG AND DROP FUNCTIONALITY FOR INTERACTIVE UI
function setupDragAndDrop() {
    const dropZone = document.querySelector('.pdf-upload-box');
    const fileInput = document.getElementById('pdf-file-input');

    if (!dropZone || !fileInput) return;

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    dropZone.addEventListener('drop', (e) => {
        let dt = e.dataTransfer;
        let files = dt.files;

        if (files && files.length > 0) {
            if (files[0].type === "application/pdf" || files[0].name.toLowerCase().endsWith('.pdf')) {
                fileInput.files = files;
                updatePdfFileName(fileInput);
            } else {
                showToast("Invalid format. Please drop a valid PDF file.");
            }
        }
    }, false);
}

async function handlePdfUpload(e) {
    e.preventDefault();

    const fileInput = document.getElementById('pdf-file-input');
    if (!fileInput.files || fileInput.files.length === 0) {
        showToast("Please select a PDF file first.");
        return;
    }

    const btnUpload = document.getElementById('btn-pdf-upload');
    const originalText = btnUpload.innerHTML;
    btnUpload.disabled = true;
    btnUpload.innerHTML = '<div class="spinner"></div> Reading PDF & Matching Standards...';

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const { response, data } = await safeFetchJson('/upload_pdf', {
            method: 'POST',
            body: formData
        });

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to upload PDF');
        }

        if (data.is_multilingual) {
            showToast(`PDF uploaded! Detected language: ${data.language_name}. Matching standards...`);
        } else {
            showToast("PDF uploaded and matched successfully!");
        }
        document.getElementById('pdf-upload-form').reset();
        const labelEl = document.getElementById('pdf-file-label');
        if (labelEl) {
            labelEl.textContent = "Drag & drop your PDF here, or click to browse";
            labelEl.title = "";
        }
        const subtextEl = document.getElementById('pdf-upload-subtext');
        if (subtextEl) {
            subtextEl.textContent = "Supports bilingual & regional tender specifications (.pdf)";
            subtextEl.style.color = "";
        }

        const extractedContainer = document.getElementById('pdf-extracted-container');
        const extractedTextEl = document.getElementById('pdf-extracted-text');
        if (extractedContainer && extractedTextEl && data.entry && data.entry.description) {
            extractedTextEl.textContent = data.entry.description;
            extractedContainer.style.display = 'block';
        }

        await fetchDatasetCount();
        if (data.matches && data.matches.length > 0) {
            renderResults({
                success: true,
                query: `${data.entry.standard_number}: ${data.entry.title}`,
                query_en: data.entry.title,
                is_multilingual: data.is_multilingual,
                detected_language: data.detected_language,
                language_name: data.language_name,
                total_standards: 12,
                execution_time_ms: 2.1,
                matches: data.matches
            });
        } else if (data.entry && data.entry.standard_number) {
            quickSearch(data.entry.standard_number + " " + data.entry.title);
        }

    } catch (err) {
        showToast(`PDF Upload Error: ${err.message}`);
    } finally {
        btnUpload.disabled = false;
        btnUpload.innerHTML = originalText;
    }
}

function updatePdfFileName(input) {
    const labelEl = document.getElementById('pdf-file-label');
    const subtextEl = document.getElementById('pdf-upload-subtext');
    if (!labelEl) return;

    if (input.files && input.files[0]) {
        const file = input.files[0];
        const fileName = file.name;
        const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);

        labelEl.innerHTML = `<i class="fa-solid fa-file-pdf" style="color:#d9534f; margin-right:6px;"></i> <span style="word-break: break-all; max-width: 100%; display: inline-block;">${escapeHtml(fileName)}</span>`;
        labelEl.title = fileName;
        if (subtextEl) {
            subtextEl.textContent = `Size: ${fileSizeMB} MB | Ready for tender extraction`;
            subtextEl.style.color = '#2e7d32';
        }
    } else {
        labelEl.textContent = "Drag & drop your PDF here, or click to browse";
        labelEl.title = "";
        if (subtextEl) {
            subtextEl.textContent = "Supports bilingual & regional tender specifications (.pdf)";
            subtextEl.style.color = "";
        }
    }
}

function copyExtractedPdfText() {
    const textEl = document.getElementById('pdf-extracted-text');
    if (textEl && textEl.textContent) {
        navigator.clipboard.writeText(textEl.textContent).then(() => {
            showToast("Copied parsed tender text to clipboard!");
        }).catch(() => {
            showToast("Failed to copy text.");
        });
    }
}

function copyToClipboard(stdNo, title) {
    const text = `${stdNo} - ${title}`;
    navigator.clipboard.writeText(text).then(() => {
        showToast(`Copied "${stdNo}" to clipboard!`);
    }).catch(() => {
        showToast(`Failed to copy`);
    });
}

function showToast(message) {
    const toast = document.getElementById('toast');
    const msgEl = document.getElementById('toast-message');
    msgEl.textContent = message;
    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3500);
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

function escapeJsString(str) {
    if (!str) return '';
    return String(str).replace(/\\/g, '\\\\').replace(/`/g, '\\`').replace(/\${/g, '\\${');
}

function escapeRegExp(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ==============================================================================
// 10. BHASINI CONVERSATIONAL CHATBOT CONTROLLER
// ==============================================================================
function toggleChatbot() {
    const chatWin = document.getElementById('chatbot-window');
    if (!chatWin) return;
    const isActive = chatWin.classList.contains('active');
    if (isActive) {
        chatWin.classList.remove('active');
    } else {
        chatWin.classList.add('active');
        const input = document.getElementById('chatbot-input');
        if (input) setTimeout(() => input.focus(), 250);
    }
}

function sendQuickPrompt(promptText) {
    const input = document.getElementById('chatbot-input');
    if (!input) return;
    input.value = promptText;
    const form = document.getElementById('chatbot-form');
    if (form) form.dispatchEvent(new Event('submit'));
}

async function handleChatSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('chatbot-input');
    const msg = input.value.trim();
    if (!msg) return;

    input.value = '';
    const messagesContainer = document.getElementById('chatbot-messages');

    // 1. Append User Message
    const userBubble = document.createElement('div');
    userBubble.className = 'chat-bubble chat-bubble-user';
    userBubble.textContent = msg;
    messagesContainer.appendChild(userBubble);

    // 2. Typing Indicator
    const typingBubble = document.createElement('div');
    typingBubble.className = 'chat-bubble chat-bubble-bot';
    typingBubble.id = 'chat-typing-indicator';
    typingBubble.innerHTML = '<div class="spinner" style="border-top-color: var(--primary-orange); width: 14px; height: 14px; margin-right: 0.4rem;"></div> Analyzing query & searching BIS...';
    messagesContainer.appendChild(typingBubble);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    const sendBtn = document.getElementById('btn-chat-send');
    if (sendBtn) sendBtn.disabled = true;

    try {
        const { response, data } = await safeFetchJson('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg })
        });

        const indicator = document.getElementById('chat-typing-indicator');
        if (indicator) indicator.remove();

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to process chat query.');
        }

        // 3. Render Assistant Response
        const botBubble = document.createElement('div');
        botBubble.className = 'chat-bubble chat-bubble-bot';

        function renderMarkdownChat(text) {
            if (!text) return '';
            let out = escapeHtml(text);
            // Bold
            out = out.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            // Italic
            out = out.replace(/\*(.*?)\*/g, '<em>$1</em>');
            // Blockquotes
            out = out.replace(/^&gt;\s*(.*)$/gm, '<blockquote>$1</blockquote>');
            // Bullet points
            out = out.replace(/^\s*-\s+(.*)$/gm, '<li>$1</li>');
            out = out.replace(/(<li>.*?<\/li>(\s*<li>.*?<\/li>)*)/gs, '<ul>$1</ul>');
            // Paragraphs and breaks
            out = out.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');
            return out;
        }

        let formattedReply = renderMarkdownChat(data.reply);
        let html = `<div class="chat-message-text">${formattedReply}</div>`;

        // Render rich standard cards inside chat if standards found
        if (data.standards && data.standards.length > 0) {
            data.standards.forEach(std => {
                const stdNo = escapeHtml(std.standard_number || 'IS Standard');
                const title = escapeHtml(std.title || '');
                const status = escapeHtml(std.status || 'Active');
                const isWithdrawn = status.toLowerCase().includes('withdrawn');
                const versionYear = escapeHtml(std.version_year || 'Current');
                const scorePct = (parseFloat(std.score || 0.8) * 100).toFixed(0) + '%';
                const gemUrl = std.gem_search_url || `https://mkp.gem.gov.in/search?q=${encodeURIComponent(stdNo)}`;
                const clauseText = escapeJsString(std.gem_clause || `Item must conform to BIS ${stdNo} (${title}).`);
                const isLive = std.is_live || std.source === 'live_bis';

                html += `
                    <div class="chat-std-card">
                        <div class="chat-std-top">
                            <span class="chat-std-number"><i class="fa-solid fa-bookmark" style="color:var(--primary-blue);"></i> ${stdNo}</span>
                            <span class="badge-score"><i class="fa-solid fa-bullseye"></i> ${scorePct} Match</span>
                        </div>
                        <div class="chat-std-badges">
                            ${isLive ? '<span class="badge-live-portal"><span class="badge-live-pulse"></span> Live BIS Portal</span>' : ''}
                            <span class="badge-status ${isWithdrawn ? 'badge-status-withdrawn' : ''}">${status}</span>
                            <span class="badge-year">Year: ${versionYear}</span>
                        </div>
                        <div class="chat-std-title">${title}</div>
                        ${std.description ? `<div class="chat-std-desc">${escapeHtml(std.description)}</div>` : ''}
                        <div class="chat-std-actions">
                            <button class="btn-chat-action" onclick="copyToClipboard('${escapeJsString(stdNo)}', '${escapeJsString(title)}')" title="Copy Standard Details">
                                <i class="fa-regular fa-copy"></i> Copy Info
                            </button>
                            <button class="btn-chat-action" onclick="copyGemClause(\`${clauseText}\`)" title="Copy Mandatory GeM Tender Clause">
                                <i class="fa-solid fa-file-contract"></i> GeM Clause
                            </button>
                            <button class="btn-chat-action btn-chat-primary" onclick="loadInMatcher('${escapeJsString(stdNo)} ${escapeJsString(title)}')" title="Load directly into Matcher Workspace">
                                <i class="fa-solid fa-bolt"></i> Launch Matcher
                            </button>
                            <a href="${gemUrl}" target="_blank" rel="noopener noreferrer" class="btn-chat-action btn-chat-gem" title="Search Products on GeM Marketplace">
                                <i class="fa-solid fa-store"></i> GeM Portal
                            </a>
                        </div>
                    </div>
                `;
            });

            // Automatically synchronize with main Matcher dashboard if results container exists
            try {
                const resultsContainer = document.getElementById('results-container');
                if (resultsContainer) {
                    renderResults({
                        query: data.search_term || msg,
                        query_en: data.search_term || msg,
                        matches: data.standards,
                        execution_time_ms: 180,
                        total_standards: data.standards.length,
                        is_multilingual: false
                    });
                }
            } catch (syncErr) {
                console.warn("Main matcher dashboard sync notice:", syncErr);
            }
        }

        // Render suggestion follow-up chips
        if (data.suggestions && data.suggestions.length > 0) {
            html += '<div class="chat-suggestions">';
            data.suggestions.forEach(s => {
                html += `<button class="chat-suggestion-chip" onclick="sendQuickPrompt('${escapeJsString(s)}')">${escapeHtml(s)}</button>`;
            });
            html += '</div>';
        }

        botBubble.innerHTML = html;
        messagesContainer.appendChild(botBubble);

    } catch (err) {
        const indicator = document.getElementById('chat-typing-indicator');
        if (indicator) indicator.remove();

        const errorBubble = document.createElement('div');
        errorBubble.className = 'chat-bubble chat-bubble-bot';
        errorBubble.style.borderColor = '#DC2626';
        errorBubble.innerHTML = `<span style="color: #DC2626;"><i class="fa-solid fa-circle-exclamation"></i> Error: ${escapeHtml(err.message)}</span>`;
        messagesContainer.appendChild(errorBubble);
    } finally {
        if (sendBtn) sendBtn.disabled = false;
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

function loadInMatcher(queryText) {
    const chatWin = document.getElementById('chatbot-window');
    if (chatWin && chatWin.classList.contains('active')) {
        chatWin.classList.remove('active');
    }
    toggleSection('dashboard');
    switchWorkspaceTab('nlp');
    const input = document.getElementById('query-input');
    if (input) {
        input.value = queryText;
        showToast(`Loaded "${queryText.substring(0, 30)}..." into Matcher!`);
        setTimeout(() => {
            const form = document.getElementById('recommend-form');
            if (form) form.dispatchEvent(new Event('submit'));
        }, 150);
    }
}