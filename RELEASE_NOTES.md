# Release v2.0.4

## What's New

### Track Sync Fixes
- **Empty releases fix** — Track sync now correctly updates log status to "success" when there are no releases to process (instead of staying stuck as "running" forever)
- **Missing credentials fix** — Track sync now logs an error and releases the sync lock if Discogs credentials are missing (instead of blocking all future syncs)
- **Collection sync logging** — Collection sync now has proper error logging for debugging
- **Startup recovery** — On app restart, any sync logs stuck in "running" state are automatically marked as "error" (app was restarted mid-sync)

### Files Modified
- `app.py` — `trigger_track_sync()` handles missing credentials, `trigger_sync()` has error logging, `init_db()` recovers stuck logs
- `sync_service.py` — `_sync_tracks_for_releases()` updates log even when releases list is empty

---

**Full Changelog**: https://github.com/JaccovL/music-collection/compare/v2.0.3...v2.0.4
