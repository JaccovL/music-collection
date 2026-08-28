# Release v1.3.0

## What's New

### Wantlist
- **Separate Wantlist page** — Synced from your Discogs wantlist
- **Same layout as Collection** — Table view and Card view with sortable columns
- **Search & Filters** — Search by title, artist, label; filter by Format, Genre, Style, Label, Year range
- **Detail Modal** — Cover image, metadata, and tracklist (fetched from Discogs API)
- **Separate Sync Process** — Independent sync with status on Sync Status page
- **Toggle in Settings** — Enable/disable Wantlist via Settings → Features

### Navigation
- **Renamed "Search" → "Collection"** — Clearer naming
- **Added "Wantlist" link** — Visible in navbar when enabled
- **White nav links** — Better visibility on dark navbar
- **Active page indicator** — Underline under current page

### Filter Bar Improvements
- **Removed Country dropdown** — Frees up space
- **All filters on one line** — Format, Genre, Style, Label, Year (From/To)
- **Compact year inputs** — 65px wide, enough for 4-digit years
- **No scrollbar** — `overflow: hidden` prevents unwanted scrollbars

### Thumbnail Links
- **Clicking thumbnail opens Discogs** — In a new tab (`target="_blank"`)
- **Other clicks open local detail** — Artist, title, or row click opens detail modal
- **Works on both Collection and Wantlist pages**

### UI Improvements
- **Table view** — `overflow-y: hidden` prevents vertical scrollbar
- **Compact filter inputs** — Smaller padding and font size
- **Nav layout** — `justify-content: space-between` with left/right sections

### API Endpoints
- `GET /api/discogs-release/<id>` — Fetch release details from Discogs API (for wantlist items)
- `POST /admin/sync-wantlist` — Trigger wantlist sync
- `GET /admin/sync-wantlist-status` — Wantlist sync status JSON

### Files Added
- `templates/wantlist.html` — Wantlist page
- `templates/wantlist_detail.html` — Wantlist item detail page
- `RELEASE_NOTES.md` — This file

### Files Modified
- `app.py` — Added wantlist routes, API endpoint, settings
- `models.py` — Added Wantlist model
- `discogs_client.py` — Added get_wantlist() method
- `sync_service.py` — Added sync_wantlist() and _process_wantlist_item()
- `templates/base.html` — Navbar with Collection/Wantlist links
- `templates/search.html` — Thumbnail links to Discogs, removed Country
- `templates/admin_settings.html` — Features section with Wantlist toggle
- `templates/admin_sync_status.html` — Wantlist sync section
- `static/css/style.css` — Nav layout, filter bar, table view styles

---

**Full Changelog**: https://github.com/JaccovL/music-collection/compare/v1.2.3...v1.3.0
