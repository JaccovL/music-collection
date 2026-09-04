# Release v2.2.1

## What's New

### Sync Optimization
- **`expire_all()` before commits** — Prevents SQLAlchemy from detecting stale objects modified in-memory, eliminating false conflicts
- **`no_autoflush` context manager** — Disables autoflush during batch commits to prevent automatic dirty-checks
- **Separate-thread verification** — Post-sync field verification runs in a new app context to avoid session conflicts
- **Lock conflict retry with backoff** — Exponential backoff (0.5s, 1.0s, 1.5s) on MySQL error 1020

### Files Modified
- `sync_service.py` — Full rewrite: expire_all, no_autoflush, thread-safe verification, batch commits every 50 releases

---

**Full Changelog**: https://github.com/JaccovL/music-collection/compare/v2.2.0...v2.2.1

---

# Release v2.2.0

## What's New

### Security (Phase 5)
- **Rate limiting** — Flask-Limiter with 200 req/min default
- **Password encryption** — Fernet-based encryption using SHA256-derived key
- **CSP headers** — Content Security Policy with nonce support
- **Security headers** — X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy
- **CSRF protection** — All POST forms and API calls protected

### Bug Fixes & Polish
- **Health Check endpoint** — Fixed `url_for` blueprint prefix
- **CSP for Chart.js** — Allows CDN scripts for statistics charts
- **Table width** — Container now 95% (was 1400px max)
- **Active page indicators** — Navbar highlights Collection/Wantlist
- **Collection = Wantlist layout** — Equal search, filters, bulk actions, columns
- **Sync CSRF** — All sync buttons now include CSRF token
- **Search join** — Fixed duplicate table alias error
- **FULLTEXT indexes** — Created missing indexes for search
- **Import fixes** — Added missing `import json` in blueprints

### Files Modified
- `app_factory.py` — Rate limiting, CSP, security headers
- `blueprints/auth.py` — Fernet password encryption
- `blueprints/collection.py` — Search fix, JSON import
- `blueprints/admin.py` — CSRF-protected endpoints
- `blueprints/api.py` — Track counts accepts POST
- `templates/base.html` — CSRF meta tag, active page CSS, url_for fixes
- `templates/search.html` — data-total-pages attribute
- `templates/wantlist.html` — Aligned with collection layout
- `templates/admin_sync_status.html` — CSRF in all fetch calls, url_for fixes
- `templates/admin_health.html` — url_for blueprint prefix
- `templates/admin_settings.html` — Password change section
- `static/js/collection.js` — Auto-init, selector fix
- `static/css/style.css` — Container width, active nav styling
- `models.py` — password_hash column
- `requirements.txt` — Flask-Limiter, cryptography

---

**Full Changelog**: https://github.com/JaccovL/music-collection/compare/v2.1.0...v2.2.0
