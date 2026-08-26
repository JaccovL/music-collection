// Theme toggle
document.addEventListener('DOMContentLoaded', function() {
    const toggle = document.getElementById('theme-toggle');
    const html = document.documentElement;
    
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    html.setAttribute('data-theme', savedTheme);
    updateToggleIcon(savedTheme);
    
    if (toggle) {
        toggle.addEventListener('click', function() {
            const current = html.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
            updateToggleIcon(next);
        });
    }
    
    function updateToggleIcon(theme) {
        if (toggle) {
            toggle.textContent = theme === 'dark' ? '☀️' : '🌙';
        }
    }
});

// Dropdown toggle
function toggleDropdown() {
    const dropdown = document.getElementById('settings-dropdown');
    dropdown.classList.toggle('open');
}

// Close dropdown when clicking outside
document.addEventListener('click', function(e) {
    const dropdown = document.getElementById('settings-dropdown');
    if (dropdown && !dropdown.contains(e.target)) {
        dropdown.classList.remove('open');
    }
});

// Sync status polling for navbar badge
function updateSyncBadge() {
    fetch('/admin/sync-status')
        .then(r => r.json())
        .then(data => {
            const dot = document.getElementById('sync-dot');
            const label = document.getElementById('sync-label');
            if (!dot || !label) return;
            
            if (data.status === 'never_run') {
                dot.className = 'sync-dot idle';
                label.textContent = 'Sync';
            } else if (data.status === 'running') {
                dot.className = 'sync-dot running';
                label.textContent = 'Syncing';
            } else if (data.status === 'success') {
                dot.className = 'sync-dot success';
                label.textContent = 'Synced';
            } else if (data.status === 'error') {
                dot.className = 'sync-dot error';
                label.textContent = 'Failed';
            }
        })
        .catch(() => {});
}

// Initial poll and interval
updateSyncBadge();
setInterval(updateSyncBadge, 30000);
