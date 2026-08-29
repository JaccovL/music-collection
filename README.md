# Music Collection — Discogs Web App

A web application for browsing and managing a personal music collection synced from [Discogs](https://www.discogs.com/). Features full-text search, advanced filtering, multiple views, and automatic daily syncs with Discogs.

## Features

- **Collection Sync** — Import your Discogs collection (releases, artists, tracks) via Discogs API
- **Wantlist** — Separate page for your Discogs wantlist with sync, search, and filters
- **Daily Auto-Update** — Scheduler pulls new additions automatically every 24 hours (configurable)
- **Manual Sync** — Trigger sync from the web UI anytime
- **Full-Text Search** — Search across titles, artists, labels, and track titles
- **Advanced Filters** — Filter by Format, Style, Label, Year range
- **Sortable Columns** — Click any column header to sort
- **Dual Views** — Table view (spreadsheet-like) or Card view (grid of covers)
- **Detail Modal** — Click any release for full info: cover image, tracklist, metadata
- **Thumbnail Links** — Clicking thumbnail opens Discogs release in new tab
- **Responsive Design** — Works on desktop, tablet, and mobile
- **Dark/Light Theme** — Toggle with one click
- **LDAP Auth Ready** — Settings page configured for LDAP integration
- **Local Admin Login** — Fallback login when LDAP is unavailable
- **Health Checks** — MariaDB and LDAP connectivity monitoring
- **Database Stats** — Modern dashboard with table sizes and visual bar chart
- **Collection Statistics** — Visual breakdowns: pie/bar charts by genre, decade, format, country, label
- **Settings Panel** — Configure Discogs token, update interval, database connection, features
- **Search Discogs** — Search directly on Discogs.com without API key

## Version History

### v1.3.5 (2026-08-29)
- **Removed Genre column** — Genre filter and column removed from Collection and Wantlist pages
- **Format column filtering** — Format now shows only first 3 comma-separated values (combines format + format_details)
  - Example: `Vinyl, 12", 45 RPM, Maxi-Single, Stereo, Qty: 1` → `Vinyl, 12", 45 RPM…`
- **Backend cleanup** — Removed genre references from filters, API responses, and template context
- **Wantlist equality** — Both pages maintain identical column structure

### v1.3.4 (2026-08-29)
- **Code Cleanup** — Optimized and cleaned the codebase
  - Extracted reusable helpers (get_request_filters, apply_common_filters, export_to_csv, export_to_pdf)
  - Removed duplicate filter and export logic between Collection and Wantlist
  - Consolidated settings POST handling
  - Reduced app.py from 1,141 to 900 lines (-21%)

### v1.3.3 (2026-08-28)
- **Export (CSV/PDF)** — Export filtered results from Collection and Wantlist pages
  - CSV export with all relevant columns
  - PDF export in portrait format, ~50 rows per page
  - Great for insurance, sharing, or offline reference
- **Collection Statistics** — Renamed from "Statistics" in menu and docs
- **Country Backfill** — Background job to fetch country data for all releases
- **Country in Sync** — Future syncs automatically fetch country for new releases
- **Bug Fixes** — Year range excludes year=0 (unknown), decade chart fixed
- **Bug Fixes** — Pie chart labels truncated to prevent overflow
- **API** — `/export/csv` and `/export/pdf` endpoints

### v1.3.2 (2026-08-28)
- **Statistics Dashboard** — Visual breakdowns of your collection with pie/bar charts
  - Summary cards: releases, artists, tracks, year range, avg tracks, top genre
  - Genre chart (doughnut), Format chart (pie), Decade chart (bar)
  - Country chart (horizontal bar), Label chart (horizontal bar)
- **Country Backfill** — Background job to fetch country data for all releases (Discogs API)
- **Country in Sync** — Future syncs now automatically fetch country for new releases
- **Bug Fixes** — Year range now excludes year=0 (unknown), decade chart fixed
- **Bug Fixes** — Pie chart labels truncated to prevent overflow
- **API** — `/admin/statistics` page and `/admin/statistics-api/<type>` endpoint

### v1.3.1 (2026-08-28)
- **Settings Page** — More compact layout with reduced padding and margins
- **Settings Page** — Discogs Username and Token fields side by side
- **Settings Page** — Sync Schedule and Features sections moved to top
- **Settings Page** — Wantlist toggle hides/shows Wantlist nav link and sync options
- **Bug Fixes** — Filter box widths now explicit (100px) so they're identical on both pages
- **Bug Fixes** — Year filter placeholders show "1900" and "2024" for clarity
- **UI Improvements** — Help renamed to About in Settings dropdown

### v1.3.0 (2026-08-28)
- **Wantlist** — New Wantlist page synced from Discogs wantlist
  - Browse, search, and filter your wantlist items
  - Same layout as Collection page (table/card views, filters, pagination)
  - Detail modal with cover image and tracklist (fetched from Discogs API)
  - Separate sync process with status on Sync Status page
- **Navigation** — Renamed "Search" to "Collection", added "Wantlist" link
- **Filter Bar** — Removed Country dropdown, all filters on one line
- **Thumbnail Links** — Clicking thumbnail opens Discogs release in new tab
- **UI Improvements** — White nav links, compact year inputs, no filter scrollbar

### v1.2.3 (2026-08-28)
- **Code Optimization** — Refactored app.py to reduce duplication (get_health_status helper)
- **Help Button** — Added Help link in Settings dropdown to GitHub release notes
- **Bug Fixes** — Fixed Reset button alignment, search rendering on single page
- **Documentation** — Added database setup instructions, size estimates, password change guide
- **Security** — Added .gitignore, removed __pycache__, placeholder token in .env.example

### v1.2.2 (2026-08-28)
- **Search Discogs** — New button to search directly on Discogs.com (no API key needed)
- **Enter Key Support** — Press Enter in search bar to trigger search
- **Track Title Search** — Search now includes track titles

### v1.2.1 (2026-08-28)
- **Search Rendering Fix** — Fixed JS error preventing table from rendering
- **Cosmetic** — Reset button aligned with other buttons

### v1.2.0 (2026-08-28)
- **Health Checks** — MariaDB and LDAP connectivity monitoring
- **Database Statistics** — Modern dashboard redesign
- **Track Sync** — Mirrors Collection Sync with status and timestamp
- **Cover Image** — Shows in detail modal with thumb fallback
- **Local Admin Login** — Configurable fallback when LDAP unavailable

### v1.1.0 (2026-08-27)
- **Filter Cache** — 5-minute cache for filter options

### v1.0.1 (2026-08-26)
- **Cosmetic** — Theme toggle in dropdown, sync badge right aligned

### v1.0.0 (2026-08-26)
- **Initial Release** — Flask + MariaDB + Discogs API

## Architecture

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.13 + Flask |
| Database | MariaDB |
| Frontend | HTML/CSS/JavaScript (vanilla) |
| Task Scheduler | APScheduler (background sync) |
| Deployment | Docker + Gunicorn |
| Auth | Flask-Login (session-based, LDAP-ready) |

## Quick Start

### Prerequisites

- **Docker & Docker Compose** — [Install Docker](https://docs.docker.com/get-docker/) | [Install Docker Compose](https://docs.docker.com/compose/install/)
- **Python 3.13+** (for local development) — [Download Python](https://www.python.org/downloads/)
- **Discogs account + API token** — [Get your token](https://www.discogs.com/settings/developers) (with a personal music collection available)
- **MariaDB 10+** — [Download MariaDB](https://mariadb.org/download/) | [MariaDB Documentation](https://mariadb.com/kb/en/documentation/)

### Setup

1. **Clone the repo:**
   ```bash
   git clone git@github.com:JaccovL/music-collection.git
   cd music-collection
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your settings:
   ```env
   SECRET_KEY=your-random-secret-key
   DISCOGS_TOKEN=your-discogs-token
   DISCOGS_USERNAME=your-discogs-username
   DATABASE_URL=mysql+pymysql://music:***@db-host:3306/music_collection
   ```

3. **Deploy with Docker:**
   ```bash
   docker-compose up -d
   ```
   Or manually:
   ```bash
   docker build -t music-collection .
   docker run -d --name music-collection -p 5000:5000 \
     -e TZ=Europe/Amsterdam \
     -e DATABASE_URL="mysql+pymysql://music:***@db-host:3306/music_collection" \
     -e SECRET_KEY="your-secret" \
     -e DISCOGS_TOKEN="your-token" \
     -e DISCOGS_USERNAME="your-username" \
     music-collection
   ```

4. **Access:**
   - Open http://localhost:5000
   - Default login: `admin` / `test-key` (change immediately!)

### Changing the Default Admin Password

The default admin password is set via the `SECRET_KEY` environment variable. The admin user logs in with username `admin` and the `SECRET_KEY` as password.

**To change the password:**

1. **Via Docker environment variable:**
   ```bash
   docker stop music-collection
   docker rm music-collection
   docker run -d --name music-collection -p 5000:5000 \
     -e SECRET_KEY="your-new-secure-password" \
     -e DATABASE_URL="mysql+pymysql://music:***@db-host:3306/music_collection" \
     -e DISCOGS_TOKEN="your-token" \
     -e DISCOGS_USERNAME="your-username" \
     music-collection:latest
   ```

2. **Via .env file:**
   ```
   SECRET_KEY=your-new-secure-password
   ```
   Then restart: `docker restart music-collection`

> **Important:** Choose a strong, random string as your SECRET_KEY. It serves both as the Flask session encryption key and as the admin password.

### Database Setup

```sql
CREATE DATABASE music_collection;
CREATE USER 'music'@'%' IDENTIFIED BY 'your-password';
GRANT ALL PRIVILEGES ON music_collection.* TO 'music'@'%';
FLUSH PRIVILEGES;
```

Tables are auto-created on first run.

### Database Size Estimates

| Collection Size | Releases | Artists | Tracks | Est. DB Size |
|-----------------|----------|---------|--------|--------------|
| Small           | 1,000    | 500     | 7,000  | ~2 MB        |
| Medium          | 5,000    | 2,500   | 35,000 | ~9 MB        |
| Large           | 10,000   | 5,000   | 70,000 | ~18 MB       |
| Very Large      | 50,000   | 25,000  | 350,000| ~90 MB       |
| Huge            | 100,000  | 50,000  | 700,000| ~180 MB      |

> **Note:** Images are stored as URLs (text), not binary files. Actual image data remains on Discogs' CDN.

## Project Structure

```
music-collection/
├── app.py                  # Main Flask application (routes, auth, settings)
├── config.py               # Configuration class (env vars, defaults)
├── models.py               # SQLAlchemy models (Release, Artist, Track, User, etc.)
├── discogs_client.py       # Discogs API client with rate limiting
├── sync_service.py         # Collection & track sync logic
├── health.py               # Health check services (MariaDB, LDAP)
├── requirements.txt        # Python dependencies
├── Dockerfile              # Multi-stage Docker build
├── docker-compose.yml      # Compose file for easy deployment
├── templates/
│   ├── base.html           # Base template (navbar, theme, layout)
│   ├── search.html         # Main search/listing page (table + cards)
│   ├── wantlist.html       # Wantlist page (table + cards)
│   ├── wantlist_detail.html # Wantlist item detail
│   ├── release.html        # Release detail page
│   ├── artist.html         # Artist detail page
│   ├── login.html          # Login page
│   ├── admin_settings.html # Settings/configuration panel
│   ├── admin_sync_status.html  # Sync status + triggers
│   ├── admin_db_stats.html     # Database statistics
│   └── admin_health.html       # Health check status page
├── static/
│   ├── css/style.css       # All styles (dark/light theme)
│   ├── js/app.js           # Theme toggle, dropdowns, sync polling
│   └── favicon.svg         # Vinyl record favicon
└── test_discogs.sh         # Discogs API connectivity test
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Redirects to `/search` |
| `/search` | GET | Main listing with search & filters |
| `/release/<id>` | GET | Release detail page |
| `/artist/<id>` | GET | Artist detail page |
| `/api/release-tracks/<id>` | GET | JSON tracklist for a release |
| `/wantlist` | GET | Wantlist page with search & filters |
| `/wantlist/<id>` | GET | Wantlist item detail page |
| `/api/discogs-release/<id>` | GET | JSON release detail from Discogs API |
| `/admin/sync-wantlist` | POST | Trigger wantlist sync |
| `/admin/sync-wantlist-status` | GET | Wantlist sync status JSON |
| `/api/search` | GET | JSON search (autocomplete) |
| `/api/health` | GET | Health check (MariaDB, LDAP status) |
| `/login` | POST | Session login |
| `/logout` | GET | Logout |
| `/admin/settings` | GET/POST | Configuration panel |
| `/admin/sync-status` | GET | Sync status page |
| `/admin/sync-status-api` | GET | Sync status JSON API |
| `/admin/sync-collection` | POST | Trigger collection sync |
| `/admin/sync-tracks` | POST | Trigger track sync |
| `/admin/db-stats` | GET | Database statistics |
| `/admin/health` | GET | Health check page |

## Sync Behavior

- **Collection Sync:** Fetches all folders/collections from Discogs → artists + releases
- **Track Sync:** Fetches full tracklist for each release (rate-limited to ~60/min)
- **Daily Scheduler:** Runs collection sync every 24 hours (configurable via `UPDATE_INTERVAL_HOURS`)
- **Manual Trigger:** Use the "Sync Status" page to start/stop syncs
- **Idempotent:** Safe to re-run — won't duplicate data

## Configuration

All settings configurable via `.env` or the web UI:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | random | Flask session encryption key AND admin password |
| `DISCOGS_TOKEN` | — | Discogs API token |
| `DISCOGS_USERNAME` | — | Your Discogs username |
| `DATABASE_URL` | sqlite | MariaDB connection string |
| `UPDATE_INTERVAL_HOURS` | 24 | Hours between auto-syncs |
| `LDAP_ENABLED` | false | Enable LDAP authentication |
| `LDAP_HOST` | — | LDAP server hostname |
| `LDAP_BASE_DN` | — | LDAP base DN for user search |

## Technologies Used

- **[Flask](https://flask.palletsprojects.com/)** — Lightweight web framework
- **[SQLAlchemy](https://www.sqlalchemy.org/)** — ORM for database abstraction
- **[MariaDB](https://mariadb.org/)** — Relational database (MySQL-compatible)
- **[Discogs API](https://www.discogs.com/developers/)** — Music metadata source
- **[APScheduler](https://apscheduler.readthedocs.io/)** — Background task scheduling
- **[Gunicorn](https://gunicorn.org/)** — WSGI HTTP server for production
- **[python-ldap](https://www.python-ldap.org/)** — LDAP authentication (optional)

## License

MIT License — see [LICENSE](LICENSE) for details.

## Contributing

Pull requests welcome! For major changes, open an issue first to discuss.

## Support

Open an issue at https://github.com/JaccovL/music-collection/issues
