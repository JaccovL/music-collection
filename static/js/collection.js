/**
 * Shared collection JavaScript — used by both Collection and Wantlist pages
 * 
 * Usage:
 *   <script src="/static/js/collection.js"></script>
 *   <script>
 *     const config = {
 *       items: itemsData,
 *       totalPages: pages,
 *       apiPrefix: '/api',  // or '/wantlist/api'
 *       hasRating: false
 *     };
 *     initCollection(config);
 *   </script>
 */

// ===== STATE =====
let config = {};
let currentView = 'table';
let currentPage = 1;
let columnVisibility = {};

// ===== INIT =====
function initCollection(cfg) {
    config = cfg;
    const savedView = localStorage.getItem('view');
    if (savedView) currentView = savedView;
    
    const savedCols = localStorage.getItem('columns');
    if (savedCols) columnVisibility = JSON.parse(savedCols);
    
    render();
    setView(currentView);
}

// ===== RENDER =====
function render() {
    if (currentView === 'table') {
        renderTable();
    } else {
        renderCards();
    }
    updateColumnVisibility();
}

// ===== TABLE =====
function renderTable() {
    const tbody = document.getElementById('table-body');
    if (!tbody) return;
    tbody.innerHTML = '';
    
    config.items.forEach(item => {
        const tr = document.createElement('tr');
        tr.innerHTML = renderTableRow(item);
        tr.onclick = () => showDetail(item.id);
        tbody.appendChild(tr);
    });
}

function renderTableRow(item) {
    const thumbHtml = item.thumb 
        ? `<a href="https://www.discogs.com/release/${item.discogs_id}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()"><img src="${escapeHtml(item.thumb)}" alt="" loading="lazy"></a>`
        : `<a href="https://www.discogs.com/release/${item.discogs_id}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()"><div class="no-cover-table">🎵</div></a>`;
    
    const ratingHtml = (config.hasRating && item.rating) 
        ? `<span class="rating-stars">${'★'.repeat(item.rating)}${'☆'.repeat(5 - item.rating)}</span>` 
        : '';
    
    return `
        <td class="col-thumb"><span class="cell-thumb">${thumbHtml}</span></td>
        <td class="col-artist"><span class="cell-artist">${escapeHtml(item.artist)}</span></td>
        <td class="col-title"><span class="cell-title">${escapeHtml(item.title)}</span></td>
        <td class="col-year">${item.year || ''}</td>
        <td class="col-format">${escapeHtml(shortFormat(item.format, item.format_details))}</td>
        <td class="col-style">${escapeHtml(item.style)}</td>
        <td class="col-label">${escapeHtml(item.label)}</td>
        <td class="col-catalog">${escapeHtml(item.catalog)}</td>
        ${config.hasRating ? `<td class="col-rating">${ratingHtml}</td>` : ''}
        <td class="col-date_added">${item.date_added || ''}</td>
    `;
}

// ===== CARDS =====
function renderCards() {
    const container = document.getElementById('cards-view');
    if (!container) return;
    container.innerHTML = '';
    
    config.items.forEach(item => {
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = renderCard(item);
        card.onclick = () => showDetail(item.id);
        container.appendChild(card);
    });
}

function renderCard(item) {
    const thumbHtml = item.thumb 
        ? `<a href="https://www.discogs.com/release/${item.discogs_id}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()"><img src="${escapeHtml(item.thumb)}" alt="" loading="lazy"></a>`
        : `<a href="https://www.discogs.com/release/${item.discogs_id}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()"><div class="no-cover-card">🎵</div></a>`;
    
    return `
        <div class="card-cover">${thumbHtml}</div>
        <div class="card-info">
            <div class="card-artist">${escapeHtml(item.artist)}</div>
            <div class="card-title">${escapeHtml(item.title)}</div>
            <div class="card-meta">
                ${item.year ? `<span>${item.year}</span>` : ''}
                ${item.format ? `<span>${escapeHtml(shortFormat(item.format, item.format_details))}</span>` : ''}
            </div>
        </div>
    `;
}

// ===== VIEW TOGGLE =====
function setView(view) {
    currentView = view;
    const tableView = document.getElementById('table-view');
    const cardsView = document.getElementById('cards-view');
    
    if (tableView) tableView.style.display = view === 'table' ? 'block' : 'none';
    if (cardsView) cardsView.style.display = view === 'cards' ? 'grid' : 'none';
    
    const tableBtn = document.getElementById('view-table');
    const cardsBtn = document.getElementById('view-cards');
    if (tableBtn) tableBtn.classList.toggle('active', view === 'table');
    if (cardsBtn) cardsBtn.classList.toggle('active', view === 'cards');
    
    localStorage.setItem('view', view);
}

// ===== COLUMN VISIBILITY =====
function toggleColumnMenu() {
    const menu = document.getElementById('column-menu');
    if (menu) menu.classList.toggle('open');
}

function updateColumnVisibility() {
    document.querySelectorAll('.column-menu input[type="checkbox"]').forEach(cb => {
        const col = cb.dataset.col;
        const visible = columnVisibility[col] !== false;
        cb.checked = visible;
        
        document.querySelectorAll(`.col-${col}`).forEach(el => {
            el.style.display = visible ? '' : 'none';
        });
    });
}

function toggleColumn(col) {
    columnVisibility[col] = !columnVisibility[col];
    localStorage.setItem('columns', JSON.stringify(columnVisibility));
    updateColumnVisibility();
}

// ===== DETAIL MODAL =====
function showDetail(itemId) {
    if (itemId.target) return;
    const item = config.items.find(i => i.id === itemId);
    if (!item) return;
    
    const modal = document.getElementById('detail-modal');
    const title = document.getElementById('modal-title');
    const body = document.getElementById('modal-body');
    
    title.textContent = `${item.artist} - ${item.title}`;
    body.innerHTML = renderDetail(item);
    modal.classList.add('open');
    
    // Fetch tracks from Discogs API
    fetch(`${config.apiPrefix}/discogs-release/${item.discogs_id}`)
        .then(r => r.json())
        .then(data => {
            if (data.tracks && data.tracks.length > 0) {
                let trackHtml = '<h3>Tracklist</h3><table class="modal-tracks">';
                data.tracks.forEach(t => {
                    trackHtml += `<tr><td class="track-pos">${escapeHtml(t.position || '')}</td><td>${escapeHtml(t.title)}</td><td class="track-dur">${escapeHtml(t.duration || '')}</td></tr>`;
                });
                trackHtml += '</table>';
                body.innerHTML += trackHtml;
            }
        })
        .catch(() => {});
}

function renderDetail(item) {
    const fields = [
        ['Discogs ID', item.discogs_id],
        ['Year', item.year],
        ['Format', shortFormat(item.format, item.format_details)],
        ['Style', item.style],
        ['Label', item.label],
        ['Date Added', item.date_added],
        ['Notes', item.notes]
    ];
    
    let html = '';
    const coverUrl = item.cover_image_url || item.thumb;
    if (coverUrl) {
        html += '<div class="modal-cover"><img src="' + escapeHtml(coverUrl) + '" alt="Cover"></div>';
    }
    html += '<div class="modal-details">';
    fields.forEach(([label, value]) => {
        html += `<div class="detail-row"><dt>${label}</dt><dd>${escapeHtml(value) || '-'}</dd></div>`;
    });
    if (item.rating) {
        html += `<div class="detail-row"><dt>Rating</dt><dd>${'★'.repeat(item.rating)}${'☆'.repeat(5 - item.rating)}</dd></div>`;
    }
    html += '</div>';
    return html;
}

function closeModal(event) {
    if (event && event.target !== event.currentTarget) return;
    const modal = document.getElementById('detail-modal');
    if (modal) modal.classList.remove('open');
}

// ===== TRACK COUNTS =====
function loadTrackCounts() {
    fetch(`${config.apiPrefix}/track-counts`)
        .then(r => r.json())
        .then(counts => {
            for (const [releaseId, count] of Object.entries(counts)) {
                const el = document.querySelector(`.track-count[data-id="${releaseId}"]`);
                if (el) {
                    if (count === 0) {
                        el.innerHTML = '<span class="no-tracks" title="No tracks synced">⚠️</span>';
                    } else {
                        el.textContent = count;
                    }
                }
            }
        });
}

// ===== HELPERS =====
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function shortFormat(text, details) {
    if (!text && !details) return '';
    const combined = details ? (text + ', ' + details) : (text || '');
    const parts = combined.split(',').map(s => s.trim());
    if (parts.length <= 3) return combined;
    return parts.slice(0, 3).join(', ') + '…';
}

// ===== KEYBOARD SHORTCUTS =====
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd+K — focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const search = document.getElementById('global-search');
        if (search) search.focus();
    }
    // Esc — close modal
    if (e.key === 'Escape') {
        closeModal();
    }
    // ←/→ — pagination
    if (e.key === 'ArrowLeft' && currentPage > 1) {
        // gotoPage(currentPage - 1);
    }
    if (e.key === 'ArrowRight' && currentPage < config.totalPages) {
        // gotoPage(currentPage + 1);
    }
});
