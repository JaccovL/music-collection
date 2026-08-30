# Release v2.0.1

## What's New

### Bug Fixes
- **Fixed flash message bug** — Success messages (like "Settings saved") were hidden due to `{% if category != 'success' %}` filter. Now all message types display correctly.
- **Fixed statistics dashboard** — Genre chart was broken (backend no longer served genre data). Replaced with Style chart and updated "Top Genre" → "Top Format" in summary cards.

### Code Optimization
- **Eliminated track sync duplication** — Extracted `_sync_tracks_for_releases()` helper in `sync_service.py`. Used by `sync_all`, `trigger_track_sync`, and `_scheduled_sync` (~50 lines removed).
- **Removed commented-out code** — Cleaned Qty suppression comments from `_update_format()`.
- **Removed genre references** — From statistics API and templates.

### Files Modified
- `app.py` — Track sync deduplication, style chart in statistics
- `sync_service.py` — Extracted `_sync_tracks_for_releases()` helper
- `templates/base.html` — Fixed flash message display
- `templates/admin_statistics.html` — Replaced genre chart with style chart
- `templates/release.html` — Removed genre display
- `README.md` — Version history
- `RELEASE_NOTES.md` — This file

---

**Full Changelog**: https://github.com/JaccovL/music-collection/compare/v2.0.0...v2.0.1
