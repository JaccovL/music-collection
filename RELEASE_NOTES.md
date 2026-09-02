# Release v2.1.0

## What's New

### Code Architecture (Phase 1)
- **Blueprint split** — `app.py` refactored from 1,194 lines to 5 blueprints (auth, collection, wantlist, admin, api, export)
- **App factory pattern** — `app_factory.py` with `create_app()` for testability
- **Shared JavaScript** — `static/js/collection.js` used by both Collection and Wantlist pages
- **Extensions module** — `extensions.py` centralizes Flask extensions
- **Cancel events module** — `cancel_events.py` breaks circular import

### Performance (Phase 2)
- **FULLTEXT search** — MySQL FULLTEXT indexes + `MATCH ... AGAINST` for fast search
- **Batch track count API** — `/api/track-counts` returns all counts in single query (N+1 → 1)
- **Filter cache invalidation** — Cache auto-clears after sync completes

### Security
- **CSRF protection** — Flask-WTF CSRFProtect on all forms (login, settings)
- **Thread-safe sync tracking** — `_active_syncs_lock` prevents race conditions

### Bug Fixes
- **Circular import** — Fixed `sync_service.py` ↔ `app.py` circular dependency
- **Search join** — Explicit `Artist` join in `apply_common_filters()`
- **Duplicate flash** — Fixed "All data verified complete" appearing twice
- **Private API usage** — Replaced `scheduler._jobstore` with public `get_jobs()`

### Files Modified
- `app_factory.py` — New: App factory pattern
- `app_utils.py` — New: Shared utilities (filters, health, export, cache)
- `cancel_events.py` — New: Sync cancel management
- `extensions.py` — New: Flask extensions
- `blueprints/auth.py` — New: Login, logout
- `blueprints/collection.py` — New: Search, release detail, artist detail
- `blueprints/wantlist.py` — New: Wantlist page, detail
- `blueprints/admin.py` — New: Settings, sync, reset, db stats
- `blueprints/api.py` — New: All API endpoints
- `blueprints/export.py` — New: CSV, PDF export
- `static/js/collection.js` — New: Shared JS with keyboard shortcuts
- `migrations/add_fulltext_indexes.py` — New: FULLTEXT index migration
- `templates/search.html` — Refactored to use shared JS
- `templates/wantlist.html` — Refactored to use shared JS
- `templates/login.html` — CSRF token added
- `templates/admin_settings.html` — CSRF token added
- `templates/admin_sync_status.html` — Duplicate flash fix
- `sync_service.py` — Cancel checks, module-level imports
- `requirements.txt` — Added cryptography

---

**Full Changelog**: https://github.com/JaccovL/music-collection/compare/v2.0.5...v2.1.0
