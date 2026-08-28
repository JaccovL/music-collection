# Release v1.3.2

## What's New

### Collection Statistics Dashboard
- **Summary Cards** — Total releases, artists, tracks, year range, avg tracks/release, top genre
- **Genre Chart** — Doughnut chart showing releases by genre
- **Format Chart** — Pie chart showing releases by format
- **Decade Chart** — Bar chart showing releases by decade
- **Country Chart** — Horizontal bar chart showing releases by country
- **Label Chart** — Horizontal bar chart showing releases by label

### Country Data
- **Backfill Script** — Background job to fetch country data for all 4,835 releases from Discogs API
- **Automatic Fetch** — Future syncs now automatically fetch country for new releases
- **Year Range Fix** — Excludes year=0 (unknown) from range calculation
- **Decade Chart Fix** — Excludes year=0 from decade grouping

### Bug Fixes
- **Pie Chart Labels** — Truncated to 30 chars with ellipsis to prevent overflow
- **Chart Card Overflow** — Added `overflow: hidden` to contain charts

### API Endpoints
- `GET /admin/statistics` — Statistics dashboard page
- `GET /admin/statistics-api/summary` — Summary statistics JSON
- `GET /admin/statistics-api/genre` — Genre breakdown JSON
- `GET /admin/statistics-api/format` — Format breakdown JSON
- `GET /admin/statistics-api/decade` — Decade breakdown JSON
- `GET /admin/statistics-api/country` — Country breakdown JSON
- `GET /admin/statistics-api/label` — Label breakdown JSON

### Files Added
- `templates/admin_statistics.html` — Statistics dashboard template
- `static/css/statistics.css` — Statistics styles
- `backfill_country.py` — Country backfill script

### Files Modified
- `app.py` — Added statistics routes and API endpoints
- `sync_service.py` — Added country fetch for new releases
- `templates/base.html` — Added Statistics link to Settings dropdown
- `static/css/style.css` — Added statistics styles

---

**Full Changelog**: https://github.com/JaccovL/music-collection/compare/v1.3.1...v1.3.2
