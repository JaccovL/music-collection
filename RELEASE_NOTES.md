# Release v1.4.0

## What's New

### Enhanced Health Checks
- **Two-level MariaDB check** — Socket check (port open) + Query check (actual `SELECT 1` execution)
- Catches real failures: corrupt tables, disk full, wrong credentials, database not responding
- Health page shows both checks separately

### Code Optimization
- **Extracted `_run_in_background()` helper** — Single wrapper for all background threads (was 3 identical blocks)
- **Extracted `_update_images()` and `_update_format()` helpers** in sync_service.py — Eliminates duplicated image/format handling
- **Removed duplicate route bug** — Two routes both named `/admin/sync-status`, renamed one to `/admin/sync-status-api`
- **Cleaned statistics API** — Removed `genre` chart type (no longer in UI)

### Documentation Fixes
- **API table** — Added 6 missing endpoints (`/export/csv`, `/export/pdf`, `/admin/statistics`, etc.)
- **Project structure** — Added missing templates (`admin_statistics.html`, `export_pdf.html`, `export_pdf_wantlist.html`)
- **Configuration table** — Added 8 missing LDAP variables + `TZ`, corrected `DATABASE_URL` default
- **Removed "genre" references** — From README, Wiki, and statistics reference file

### Files Modified
- `app.py` — Background thread helper, route fix, statistics cleanup
- `sync_service.py` — Image and format helpers extracted
- `health.py` — Query-level check added
- `templates/admin_health.html` — Shows both socket and query checks
- `templates/search.html`, `templates/wantlist.html` — Format filtering
- `README.md` — API docs, project structure, configuration
- `RELEASE_NOTES.md` — This file

---

**Full Changelog**: https://github.com/JaccovL/music-collection/compare/v1.3.5...v1.4.0
