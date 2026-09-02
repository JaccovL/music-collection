# Release v2.0.5

## What's New

### High Priority Fixes
- **Search join fix** — Explicitly join Artist table in `apply_common_filters()` (was relying on implicit relationship)
- **Batch track count API** — New `/api/track-counts` endpoint returns all track counts in single query (N+1 → 1)
- **CSRF protection** — Added Flask-WTF CSRFProtect to all forms (login, settings)

### Files Modified
- `app.py` — Explicit Artist join in `apply_common_filters()`, new `/api/track-counts` batch endpoint, CSRFProtect initialization
- `sync_service.py` — Collection sync checks cancel flag between folders and releases
- `search.html` — `loadTrackCounts()` uses batch endpoint instead of individual API calls
- `login.html` — CSRF token added
- `admin_settings.html` — CSRF token added
- `admin_sync_status.html` — Duplicate flash message fix (`.verification-alert` class)

---

**Full Changelog**: https://github.com/JaccovL/music-collection/compare/v2.0.4...v2.0.5
