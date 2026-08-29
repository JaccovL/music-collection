# Release v1.5.2

## What's New

### Bug Fixes
- **Fixed Sync All button** — Was using `threading.Thread` directly without app context, causing database errors. Now uses `_run_in_background()` helper.
- **Removed Quick Add button** — Discogs is the leading source for what's in the collection; manual additions are not desired.

### Files Modified
- `app.py` — Fixed sync_all to use `_run_in_background()`, removed quick_add route
- `templates/search.html` — Removed Quick Add button and modal
- `README.md` — Version history
- `RELEASE_NOTES.md` — This file

---

**Full Changelog**: https://github.com/JaccovL/music-collection/compare/v1.5.1...v1.5.2
