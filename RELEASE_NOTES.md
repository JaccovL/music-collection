# Release v2.0.2

## What's New

### Post-Sync Verification
- **Automatic verification** — After every sync completes, checks for missing country, tracks, and cover images
- **Auto-fix missing data** — If missing fields detected, automatically fetches from Discogs API
- **Flash notifications** — Warning when missing data detected, success when all verified
- **Manual trigger** — `POST /admin/verify-sync` endpoint for on-demand verification
- **Sync status alerts** — Real-time alerts on Sync Status page during verification/fixes

### Database Changes
- Added `verification_status` column to `update_log` (pending, passed, failed, retrying)
- Added `missing_fields` column to `update_log` (JSON: `{"country": 4835, "tracks": 123}`)

### Files Modified
- `app.py` — Added `/admin/verify-sync` endpoint, flash alerts, verification triggers on all sync buttons
- `sync_service.py` — Added `_verify_sync()` and `_fix_missing_fields()` helpers, post-sync verification hooks
- `models.py` — Added `verification_status` and `missing_fields` columns to `UpdateLog`
- `templates/admin_sync_status.html` — Verification alerts, JS polling for verification status

---

**Full Changelog**: https://github.com/JaccovL/music-collection/compare/v2.0.1...v2.0.2
