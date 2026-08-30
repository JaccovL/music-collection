# Release v2.0.0

## What's New

### New Features
- **🎲 Random Release Picker** — Button in search bar picks a random release from your current filtered results and opens its detail modal
- **⚠️ Missing Tracks Indicator** — Releases without tracklists show ⚠️ instead of a track count, so you can see at a glance which need syncing
- **🔄 Sync All (Collection + Tracks)** — One button runs collection sync first, then automatically runs track sync for any releases without tracks
- **🗑️ Reset Collection** — Danger Zone section with double-confirmation to permanently delete all collection data and start fresh
- **🔒 Sync Lock** — All sync routes now use a lock to prevent concurrent syncs (only one sync at a time)
- **📊 Progress Bar** — Sync status page shows visual progress bar for track sync completion

### Theme Improvements
- **System preference detection** — On first visit, the theme follows your OS dark/light mode preference (`prefers-color-scheme`)
- After manually toggling, your choice is saved and takes priority over system preference

### Format Column Enhancements
- **"Qty: N" suppressed** — Removed quantity info from format display (was in `format_details`)
- Example: `Vinyl, 12", 45 RPM, Maxi-Single, Stereo, Qty: 1` → `Vinyl, 12", 45 RPM, Maxi-Single, Stereo`
- Existing data cleaned: 4,835 releases and 114 wantlist items updated

### Health Check Improvements
- **Two-level MariaDB check** — Socket check (port open) + Query check (actual `SELECT 1` execution)
- Catches real failures: corrupt tables, disk full, wrong credentials, database not responding
- Health page shows both checks separately

### Bug Fixes
- **Fixed duplicate route bug** — Two routes were both named `/admin/sync-status`; renamed one to `/admin/sync-status-api`
- **Fixed local_fallback setting** — Was `false` in database; corrected to `true` so local admin login works when LDAP is unavailable
- **Fixed cron track sync** — Scheduled job now runs track sync after collection sync automatically
- **Fixed stuck sync logs** — Added cleanup for stuck "running" state logs

### Code Optimization
- **Extracted `_run_in_background()` helper** — Single wrapper for all background threads
- **Extracted `_update_images()` and `_update_format()` helpers** in sync_service.py
- **Removed duplicate filter/export logic** between Collection and Wantlist
- **Consolidated settings POST handling** with a loop

### Files Modified
- `app.py` — Random release route, sync lock, reset collection, sync all, background helper
- `sync_service.py` — Image/format helpers, Qty suppression
- `health.py` — Query-level check added
- `static/js/app.js` — System theme preference detection
- `templates/search.html` — Random button, missing tracks indicator
- `templates/admin_sync_status.html` — Sync All button, Danger Zone with Reset, progress bar
- `templates/admin_health.html` — Shows both socket and query checks
- `README.md` — Version history
- `RELEASE_NOTES.md` — This file

---

**Full Changelog**: https://github.com/JaccovL/music-collection/compare/v1.4.0...v2.0.0
