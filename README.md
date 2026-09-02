# Music Collection — Discogs Web App

A web application for browsing and managing a personal music collection synced from [Discogs](https://www.discogs.com/). Features full-text search, advanced filtering, multiple views, keyboard shortcuts, and automatic daily syncs with Discogs.

## Features

### Collection Management
- **Collection Sync** — Import your Discogs collection (releases, artists, tracks) via Discogs API
- **Wantlist** — Separate page for your Discogs wantlist with sync, search, and filters
- **Wishlist → Collection Detection** — Auto-detects when wantlist items appear in your collection after sync
- **Daily Auto-Update** — Scheduler pulls new additions automatically every 24 hours (configurable)
- **Manual Sync** — Trigger sync from the web UI anytime

### Search & Filter
- **Full-Text Search** — Search across titles, artists, labels, and track titles
- **Advanced Filters** — Filter by Format, Style, Label, Year range, Track count (min/max), Date added, Has notes
- **Sortable Columns** — Click any column header to sort with visual indicators
- **Dual Views** — Table view (spreadsheet-like) or Card view (grid of covers)

### User Experience
- **Keyboard Shortcuts** — Ctrl+K (search), Esc (close modal), Arrow keys (pagination), T (theme), V (view toggle)
- **Bulk Actions** — Select multiple releases and add notes or export to CSV
- **Detail Modal** — Click any release for full info: cover image, tracklist, metadata
- **Open on Discogs** — Direct link from detail modal to Discogs release page
- **Responsive Design** — Works on desktop, tablet, and mobile
- **Dark/Light Theme** — Toggle with one click or follow system preference

### Administration
- **LDAP Auth Ready** — Settings page configured for LDAP integration
- **Local Admin Login** — Fallback login when LDAP is unavailable
- **Health Checks** — MariaDB and LDAP connectivity monitoring
- **Database Stats** — Modern dashboard with table sizes and visual bar chart
- **Collection Statistics** — Visual breakdowns: pie/bar charts by decade, format, country, label
- **Settings Panel** — Configure Discogs token, update interval, database connection, features
- **Sync Status** — Real-time progress with cancel support, CEST/CET timestamps

## Version History

### v2.1.0 (2026-09-02)
- **Blueprint Architecture** — app.py refactored to 6 blueprints (auth, collection, wantlist, admin, api, export)
- **App Factory Pattern** — Clean separation of concerns with app_factory.py
- **Shared JavaScript** — Single collection.js for both Collection and Wantlist pages
- **Keyboard Shortcuts** — Ctrl+K, Esc, Arrow keys, T, V
- **Loading States** — Spinners, disabled buttons, skeleton loading, progress bars
- **Sort Indicators** — Visual indicators on sortable columns
- **Modal Improvements** — Loading spinner, error handling, Discogs link, body scroll lock
- **Pagination** — First/Last page buttons, Go-to-page input
- **Responsive Design** — Mobile breakpoints, stacked filters, card view default
- **Empty States** — Helpful messages for no results / no releases
- **Wishlist Detection** — Auto-detects when wantlist items appear in collection
- **Advanced Search** — Filter by track count, date added range, has notes
- **CEST/CET Timestamps** — All sync status times in Amsterdam timezone
- **Wantlist Sync Buttons** — Always visible in sync status page

### v2.0.4 (2026-09-01)
- Track Sync Fixes, Missing Credentials Fix, Collection Sync Logging, Startup Recovery

### v2.0.3 (2026-08-30)
- Cancel Sync Button, Timezone Fix (CEST/CET), Reset Collection Fix, Verification Status Bugfix

### v2.0.2 (2026-08-30)
- Post-Sync Verification, Auto-fix missing data

### v2.0.1 (2026-08-30)
- Bug Fixes, Code Optimization

### v2.0.0 (2026-08-30)
- Random Release Picker, Missing Tracks Indicator, Sync All, Reset Collection, Sync Lock, Progress Bar

### v1.x.x — Earlier releases
See git history for earlier version details.
