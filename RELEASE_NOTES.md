# Release v2.0.3

## What's New

### Cancel Sync Button
- **Cancel running syncs** — Stop collection, track, or wantlist syncs mid-flight
- **Smart visibility** — Cancel buttons appear only when a sync is active
- **Thread-safe** — Uses `threading.Event` for clean cancellation
- **Status tracking** — Cancelled syncs logged with "Cancelled by user" message

### Timezone Fix (CEST/CET)
- **UTC storage** — All timestamps now stored in UTC for consistency
- **Amsterdam display** — Converted to CEST/CET for all UI rendering
- **API consistency** — All ISO timestamps include `Z` suffix for correct JS parsing
- **Data migration** — Existing timestamps converted from Amsterdam time to UTC

### Reset Collection Fix
- **TRUNCATE TABLE** — Replaces ORM DELETE to avoid "Record has changed" errors
- **Foreign key handling** — Temporarily disables FK checks during truncation
- **Clean state** — Resets cancel events and health cache after reset

### Verification Status Bugfix
- **Stuck "verifying"** — Sync status now correctly updates to "success" after verification
- **Wantlist sync** — No longer appears to run indefinitely after completion

### Files Modified
- `app.py` — Cancel sync infrastructure (`/admin/cancel-sync`), `utc_to_amsterdam()` helper, `now_amsterdam()` returns UTC, cancel checks in sync routes, API returns `Z`-suffixed timestamps
- `sync_service.py` — `_now()` returns UTC, verification sets `status='success'` after passing
- `models.py` — `_now()` returns UTC, `utc_to_amsterdam()` helper, all `DateTime` defaults use `_now`
- `health.py` — Uses UTC for `last_check`
- `static/css/style.css` — `.btn-danger` style for cancel buttons
- `templates/admin_sync_status.html` — Cancel buttons, `cancelSync()` JS, auto-show/hide logic, `utc_to_amsterdam()` for display
- `templates/admin_health.html` — `utc_to_amsterdam()` for last check time
- `templates/export_pdf.html` — `utc_to_amsterdam()` for export timestamp
- `templates/export_pdf_wantlist.html` — `utc_to_amsterdam()` for export timestamp
- `templates/release.html` — `utc_to_amsterdam()` for date added
- `templates/wantlist_detail.html` — `utc_to_amsterdam()` for date added

---

**Full Changelog**: https://github.com/JaccovL/music-collection/compare/v2.0.2...v2.0.3
