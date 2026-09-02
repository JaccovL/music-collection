/**
 * Music Collection — Shared JS for Collection and Wantlist pages
 * All JS is loaded from collection.js (no inline scripts)
 */
var CollectionApp = {
    config: {
        view: 'table',
        perPage: 48,
        currentPage: 1,
        totalPages: 1,
        sort: 'artist',
        order: 'asc',
        search: '',
        formatFilter: '',
        styleFilter: '',
        labelFilter: '',
        yearFrom: '',
        yearTo: '',
        columns: {},
        selectedColumns: new Set()
    },

    init: function() {
        this.loadPreferences();
        this.bindEvents();
        this.updateView();
        this.updateColumnToggles();
    },

    loadPreferences: function() {
        var saved = localStorage.getItem('collection_prefs');
        if (saved) {
            try {
                var prefs = JSON.parse(saved);
                Object.assign(this.config, prefs);
                if (prefs.selectedColumns) {
                    this.config.selectedColumns = new Set(prefs.selectedColumns);
                }
            } catch (e) {}
        }
    },

    savePreferences: function() {
        var toSave = Object.assign({}, this.config);
        toSave.selectedColumns = Array.from(this.config.selectedColumns);
        localStorage.setItem('collection_prefs', JSON.stringify(toSave));
    },

    bindEvents: function() {
        document.addEventListener('keydown', this.handleKeyboard.bind(this));
        document.addEventListener('click', function(e) {
            var menu = document.getElementById('column-menu');
            var toggle = e.target.closest('.column-toggle');
            if (menu && !menu.contains(e.target) && !toggle) {
                menu.classList.remove('open');
            }
        });
        var self = this;
        document.querySelectorAll('#column-menu input[type="checkbox"]').forEach(function(cb) {
            cb.addEventListener('change', function() {
                var col = cb.dataset.col;
                if (cb.checked) {
                    self.config.selectedColumns.add(col);
                } else {
                    self.config.selectedColumns.delete(col);
                }
                self.updateColumnVisibility();
                self.savePreferences();
            });
        });
    },

    handleKeyboard: function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            var search = document.getElementById('global-search');
            if (search) search.focus();
        }
        if (e.key === 'Escape') {
            var modal = document.getElementById('release-modal');
            if (modal && modal.classList.contains('open')) {
                closeModal();
            }
            var menu = document.getElementById('column-menu');
            if (menu) menu.classList.remove('open');
        }
        if (e.key === 't' && !e.ctrlKey && !e.metaKey && !e.altKey) {
            var tag = document.activeElement.tagName;
            if (tag !== 'INPUT' && tag !== 'TEXTAREA' && tag !== 'SELECT') {
                toggleTheme();
            }
        }
        if (e.key === 'v' && !e.ctrlKey && !e.metaKey && !e.altKey) {
            var tag = document.activeElement.tagName;
            if (tag !== 'INPUT' && tag !== 'TEXTAREA' && tag !== 'SELECT') {
                this.setView(this.config.view === 'table' ? 'cards' : 'table');
            }
        }
        if (e.key === 'ArrowLeft' && this.config.currentPage > 1) {
            this.goToPage(this.config.currentPage - 1);
        }
        if (e.key === 'ArrowRight' && this.config.currentPage < this.config.totalPages) {
            this.goToPage(this.config.currentPage + 1);
        }
    },

    setView: function(view) {
        this.config.view = view;
        localStorage.setItem('collection_view', view);
        this.updateView();
    },

    updateView: function() {
        document.querySelectorAll('.view-btn').forEach(function(btn) { btn.classList.remove('active'); });
        var activeBtn = document.getElementById('view-' + this.config.view);
        if (activeBtn) activeBtn.classList.add('active');

        var tableView = document.getElementById('table-view');
        var cardsView = document.getElementById('cards-view');
        if (tableView) tableView.style.display = this.config.view === 'table' ? '' : 'none';
        if (cardsView) cardsView.style.display = this.config.view === 'cards' ? '' : 'none';
    },

    updateColumnToggles: function() {
        var self = this;
        document.querySelectorAll('#column-menu input[type="checkbox"]').forEach(function(cb) {
            cb.checked = self.config.selectedColumns.has(cb.dataset.col);
        });
        this.updateColumnVisibility();
    },

    updateColumnVisibility: function() {
        var self = this;
        document.querySelectorAll('#column-menu input[type="checkbox"]').forEach(function(cb) {
            var col = cb.dataset.col;
            var visible = cb.checked;
            document.querySelectorAll('.col-' + col).forEach(function(el) {
                el.style.display = visible ? '' : 'none';
            });
        });
    },

    applyFilters: function() {
        var q = document.getElementById('global-search').value;
        var format = document.getElementById('filter-format').value;
        var style = document.getElementById('filter-style').value;
        var label = document.getElementById('filter-label').value;
        var yearFrom = document.getElementById('filter-year-from').value;
        var yearTo = document.getElementById('filter-year-to').value;
        var tracksMin = document.getElementById('filter-tracks-min').value;
        var tracksMax = document.getElementById('filter-tracks-max').value;
        var dateFrom = document.getElementById('filter-date-from').value;
        var dateTo = document.getElementById('filter-date-to').value;
        var hasNotes = document.getElementById('filter-has-notes').value;
        
        var params = new URLSearchParams({q:q, format:format, style:style, label:label, year_from:yearFrom, year_to:yearTo, per_page:this.config.perPage});
        if (tracksMin) params.set('tracks_min', tracksMin);
        if (tracksMax) params.set('tracks_max', tracksMax);
        if (dateFrom) params.set('date_from', dateFrom);
        if (dateTo) params.set('date_to', dateTo);
        if (hasNotes) params.set('has_notes', hasNotes);
        window.location.href = window.location.pathname + '?' + params.toString();
    },

    goToPage: function(page) {
        var params = new URLSearchParams(window.location.search);
        params.set('page', page);
        window.location.href = window.location.pathname + '?' + params.toString();
    }
};

function applyFilters() { CollectionApp.applyFilters(); }
function setView(view) { CollectionApp.setView(view); }
function toggleColumnMenu() {
    var menu = document.getElementById('column-menu');
    if (menu) menu.classList.toggle('open');
}
function goToPage(page) { CollectionApp.goToPage(page); }

function toggleTheme() {
    var html = document.documentElement;
    var current = html.getAttribute('data-theme') || 'dark';
    var next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    updateThemeUI(next);
}

function updateThemeUI(theme) {
    var toggle = document.getElementById('theme-toggle');
    if (toggle) {
        toggle.textContent = (theme === 'dark' ? '🌙 Dark' : '☀️ Light');
    }
}

var collectionItems = [];
var selectedIds = new Set();

function initCollection(options) {
    collectionItems = options.items || [];
    CollectionApp.config.totalPages = options.totalPages || 1;
    renderTable();
}

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function shortFormat(format, details) {
    if (!format) return '';
    var parts = String(format).split(',').map(function(s) { return s.trim(); });
    return parts.slice(0, 3).join(', ');
}

function renderTable() {
    var tbody = document.getElementById('table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    collectionItems.forEach(function(release) {
        var tr = document.createElement('tr');
        tr.className = 'release-row';
        
        var thumbHtml = release.thumb 
            ? '<a href="https://www.discogs.com/release/' + release.discogs_id + '" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()"><img src="' + escapeHtml(release.thumb) + '" alt="" loading="lazy"></a>'
            : '<a href="https://www.discogs.com/release/' + release.discogs_id + '" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()"><div class="no-cover-table">🎵</div></a>';
        
        tr.innerHTML = 
            '<td class="col-checkbox"><input type="checkbox" class="row-checkbox" data-id="' + release.id + '"></td>' +
            '<td class="col-thumb"><span class="cell-thumb">' + thumbHtml + '</span></td>' +
            '<td class="col-artist"><span class="cell-artist">' + escapeHtml(release.artist) + '</span></td>' +
            '<td class="col-title"><span class="cell-title"><a href="/release/' + release.id + '">' + escapeHtml(release.title) + '</a></span></td>' +
            '<td class="col-year">' + (release.year || '') + '</td>' +
            '<td class="col-format">' + escapeHtml(shortFormat(release.format, release.format_details)) + '</td>' +
            '<td class="col-style">' + escapeHtml(release.style || '') + '</td>' +
            '<td class="col-label">' + escapeHtml(release.label || '') + '</td>' +
            '<td class="col-catalog">' + escapeHtml(release.catalog || '') + '</td>' +
            '<td class="col-date_added">' + escapeHtml(release.date_added || '') + '</td>' +
            '<td class="col-tracks"><span class="track-count" data-id="' + release.id + '" data-discogs="' + release.discogs_id + '">...</span></td>' +
            '<td class="col-view"><button class="btn btn-sm" onclick="event.stopPropagation(); showDetail(' + release.id + ')">View</button></td>';
        
        tr.onclick = (function(id) { return function() { showDetail(id); }; })(release.id);
        tbody.appendChild(tr);
    });

    CollectionApp.updateColumnVisibility();
    loadTrackCounts();
}

function renderCards() {
    var container = document.getElementById('cards-view');
    if (!container) return;
    container.innerHTML = '';
    
    collectionItems.forEach(function(release) {
        var card = document.createElement('div');
        card.className = 'card';
        
        var thumbHtml = release.thumb 
            ? '<a href="https://www.discogs.com/release/' + release.discogs_id + '" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()"><img src="' + escapeHtml(release.thumb) + '" alt="" loading="lazy"></a>'
            : '<a href="https://www.discogs.com/release/' + release.discogs_id + '" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()"><div class="no-cover-card">🎵</div></a>';
        
        var metaHtml = '';
        if (release.year) metaHtml += '<span>' + release.year + '</span>';
        if (release.format) metaHtml += '<span>' + escapeHtml(shortFormat(release.format, release.format_details)) + '</span>';
        
        card.innerHTML = 
            '<div class="card-cover">' + thumbHtml + '</div>' +
            '<div class="card-info">' +
                '<div class="card-artist">' + escapeHtml(release.artist) + '</div>' +
                '<div class="card-title">' + escapeHtml(release.title) + '</div>' +
                '<div class="card-meta">' + metaHtml + '</div>' +
            '</div>';
        
        card.onclick = (function(id) { return function() { showDetail(id); }; })(release.id);
        container.appendChild(card);
    });
}

function showDetail(releaseId) {
    if (releaseId && releaseId.target) return;
    
    var modal = document.getElementById('release-modal');
    var title = document.getElementById('modal-title');
    var body = document.getElementById('modal-body');
    
    body.innerHTML = '<div class="modal-loading"><div class="spinner"></div><p>Loading release details...</p></div>';
    modal.classList.add('open');
    document.body.classList.add('modal-open');
    
    fetch('/api/release-detail/' + releaseId)
        .then(function(r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(function(data) {
            title.textContent = data.artist + ' - ' + data.title;
            
            var fields = [
                ['Discogs ID', data.discogs_id],
                ['Year', data.year],
                ['Format', shortFormat(data.format, data.format_details)],
                ['Style', data.style],
                ['Label', data.label],
                ['Date Added', data.date_added],
                ['Notes', data.notes]
            ];
            
            var html = '';
            var coverUrl = data.cover_image_url || data.thumb_url;
            if (coverUrl) {
                html += '<img class="release-detail-cover" src="' + escapeHtml(coverUrl) + '" alt="Cover">';
            }
            html += '<div class="modal-details">';
            fields.forEach(function(field) {
                html += '<div class="detail-row"><dt>' + field[0] + '</dt><dd>' + escapeHtml(field[1]) + '</dd></div>';
            });
            html += '</div>';
            
            if (data.tracks && data.tracks.length > 0) {
                html += '<div class="release-detail-tracks"><h3>Tracklist</h3>';
                data.tracks.forEach(function(t) {
                    html += '<div class="track-row"><span class="track-position">' + escapeHtml(t.position || '') + '</span><span class="track-title">' + escapeHtml(t.title) + '</span><span class="track-duration">' + escapeHtml(t.duration || '') + '</span></div>';
                });
                html += '</div>';
            }
            
            html += '<a href="https://www.discogs.com/release/' + data.discogs_id + '" target="_blank" rel="noopener noreferrer" class="modal-discogs-link">Open on Discogs →</a>';
            
            body.innerHTML = html;
        })
        .catch(function(err) {
            body.innerHTML = '<div class="modal-error"><p>Failed to load release details</p><p style="font-size:12px;color:var(--text-muted)">' + escapeHtml(err.message) + '</p></div>';
        });
}

function closeModal(event) {
    if (!event || event.target === document.getElementById('release-modal') || event.target.closest('.modal-close')) {
        document.getElementById('release-modal').classList.remove('open');
        document.body.classList.remove('modal-open');
    }
}

function loadTrackCounts() {
    var ids = collectionItems.map(function(i) { return i.id; });
    if (!ids.length) return;

    fetch('/api/track-counts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: ids })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        document.querySelectorAll('.track-count[data-id]').forEach(function(el) {
            var id = parseInt(el.dataset.id);
            var count = data[id];
            if (count !== undefined) {
                el.textContent = count;
            } else {
                el.textContent = '0';
            }
        });
    })
    .catch(function() {});
}

function searchDiscogs() {
    var q = document.getElementById('global-search').value;
    if (q) window.open('https://www.discogs.com/search/?q=' + encodeURIComponent(q) + '&type=release', '_blank');
}

function randomRelease() {
    fetch('/api/random-release')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.id) window.location.href = '/release/' + data.id;
        });
}

function exportCSV() {
    window.location.href = '/export/csv?source=collection';
}

function exportPDF() {
    window.location.href = '/export/pdf?source=collection';
}

function gotoPage() {
    var page = document.getElementById('goto-page').value;
    if (page) {
        var params = new URLSearchParams(window.location.search);
        params.set('page', page);
        window.location.href = window.location.pathname + '?' + params.toString();
    }
}

function changePerPage() {
    var perPage = document.getElementById('per-page').value;
    var params = new URLSearchParams(window.location.search);
    params.set('per_page', perPage);
    params.set('page', 1);
    window.location.href = window.location.pathname + '?' + params.toString();
}

function toggleSelectAllVisible() {
    var checkboxes = document.querySelectorAll('.row-checkbox');
    var selectAll = document.getElementById('select-all-visible').checked;
    checkboxes.forEach(function(cb) {
        cb.checked = selectAll;
        var id = parseInt(cb.dataset.id);
        if (selectAll) {
            selectedIds.add(id);
        } else {
            selectedIds.delete(id);
        }
    });
    updateBulkBar();
}

function toggleRowCheckbox(id, checked) {
    if (checked) {
        selectedIds.add(id);
    } else {
        selectedIds.delete(id);
    }
    updateBulkBar();
}

function updateBulkBar() {
    var bar = document.getElementById('bulk-actions-bar');
    var count = document.getElementById('selected-count');
    if (selectedIds.size > 0) {
        bar.style.display = 'flex';
        count.textContent = selectedIds.size + ' selected';
    } else {
        bar.style.display = 'none';
    }
}

function clearSelection() {
    selectedIds.clear();
    document.querySelectorAll('.row-checkbox').forEach(function(cb) { cb.checked = false; });
    document.getElementById('select-all-visible').checked = false;
    document.getElementById('select-all-visible-th').checked = false;
    updateBulkBar();
}

function bulkAddNotes() {
    if (selectedIds.size === 0) return;
    var csrfToken = document.querySelector('meta[name="csrf_token"]').getAttribute('content');
    var notes = prompt('Add notes to ' + selectedIds.size + ' selected releases:');
    if (!notes) return;
    
    fetch('/api/bulk/add-notes', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
        body: JSON.stringify({ids: Array.from(selectedIds), notes: notes})
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        alert(data.message || 'Notes added to ' + data.updated + ' releases');
        clearSelection();
    })
    .catch(function(err) { alert('Error: ' + err); });
}

function bulkExportCSV() {
    if (selectedIds.size === 0) return;
    var params = new URLSearchParams(window.location.search);
    params.set('ids', Array.from(selectedIds).join(','));
    window.location.href = '/export/csv?' + params.toString() + '&source=collection';
}

function updateSortIndicators() {
    var urlParams = new URLSearchParams(window.location.search);
    var currentSort = urlParams.get('sort') || 'artist';
    var currentOrder = urlParams.get('order') || 'asc';
    
    document.querySelectorAll('.sortable').forEach(function(th) {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    
    var activeTh = document.querySelector('.sortable[data-sort="' + currentSort + '"]');
    if (activeTh) {
        activeTh.classList.add(currentOrder === 'asc' ? 'sort-asc' : 'sort-desc');
    }
}

// ===== AUTO-INITIALIZATION =====
// Parse collection data from JSON script tag (no inline scripts needed)
(function() {
    var dataEl = document.getElementById('collection-data');
    if (dataEl) {
        try {
            var data = JSON.parse(dataEl.textContent);
            var totalPages = parseInt(dataEl.getAttribute('data-total-pages') || '1');
            initCollection({items: data, totalPages: totalPages});
        } catch(e) {
            console.error('Failed to parse collection data:', e);
        }
    }
})();
