// Theme toggle - works from dropdown menu
function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    updateThemeUI(next);
}

function updateThemeUI(theme) {
    const toggle = document.getElementById('theme-toggle');
    if (toggle) {
        toggle.textContent = (theme === 'dark' ? '🌙 Dark' : '☀️ Light');
    }
}

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
    fetch('/admin/sync-status-api')
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

// Load saved theme on page load
document.addEventListener('DOMContentLoaded', function() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeUI(savedTheme);
});
