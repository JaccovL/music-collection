# Release v1.3.3

## What's New

### Export (CSV/PDF)
- **CSV Export** — Download filtered results as CSV (Excel-compatible)
- **PDF Export** — Download filtered results as formatted PDF (portrait, ~50 rows/page)
- **Collection & Wantlist** — Both pages support export with current filters
- **Filtered Export** — Only exports what you see (respects search, filters, year range)

### Collection Statistics Dashboard
- **Summary Cards** — Total releases, artists, tracks, year range, avg tracks/release, top genre
- **Genre Chart** — Doughnut chart showing releases by genre
- **Format Chart** — Pie chart showing releases by format
- **Decade Chart** — Bar chart showing releases by decade
- **Country Chart** — Horizontal bar chart showing releases by country
- **Label Chart** — Horizontal bar chart showing releases by label

### Country Data
- **Backfill Script** — Background job to fetch country data for all releases from Discogs API
- **Automatic Fetch** — Future syncs now automatically fetch country for new releases

### Bug Fixes
- **Year Range** — Excludes year=0 (unknown) from range calculation
- **Decade Chart** — Excludes year=0 from decade grouping
- **Pie Chart Labels** — Truncated to 30 chars with ellipsis to prevent overflow
- **Chart Card Overflow** — Added `overflow: hidden` to contain charts

### API Endpoints
- `GET /admin/statistics` — Statistics dashboard page
- `GET /admin/statistics-api/<type>` — Chart data JSON (summary, genre, format, decade, country, label)
- `GET /export/csv` — CSV export
- `GET /export/pdf` — PDF export

---

**Full Changelog**: https://github.com/JaccovL/music-collection/compare/v1.3.2...v1.3.3
