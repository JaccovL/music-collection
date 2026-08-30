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
|- **Collection Statistics** — Visual breakdowns: pie/bar charts by decade, format, country, label
- **Settings Panel** — Configure Discogs token, update interval, database connection, features
- **Search Discogs** — Search directly on Discogs.com without API key

## Version History

### v2.0.2 (2026-08-30)
- **Post-Sync Verification** — Automatic check for missing country, tracks, cover images after sync
- **Auto-fix missing data** — Fetches missing fields from Discogs API automatically
- **Flash notifications** — Alerts when missing data detected, success when verified

### v2.0.1 (2026-08-30)
- **Bug Fixes** — Fixed flash message display (success messages were hidden), fixed statistics dashboard (replaced broken genre chart with style chart)
- **Code Optimization** — Extracted `_sync_tracks_for_releases()` helper to eliminate ~50 lines of duplicated track sync code
- **Removed genre references** — From statistics API and templates

### v2.0.0 (2026-08-30)
- **🎲 Random Release Picker** — Button in search bar picks a random release from current filtered results
- **⚠️ Missing Tracks Indicator** — Releases without tracklists show ⚠️ instead of track count
- **🔄 Sync All (Collection + Tracks)** — One button runs collection sync then track sync sequentially
- **🗑️ Reset Collection** — Danger Zone with double-confirmation to delete all data and start fresh
- **🔒 Sync Lock** — Prevents concurrent syncs (only one sync at a time)
- **📊 Progress Bar** — Sync status page shows visual progress bar for track sync completion
- **🌓 System Theme Preference** — First visit follows OS dark/light mode
- **Enhanced Health Checks** — Two-level MariaDB check (socket + query)
- **Format: "Qty: N" suppressed** — Removed quantity info from format display
- **Code Optimization** — Extracted helpers, fixed duplicate route, consolidated settings

### v1.4.0 (2026-08-29)
- **Enhanced Health Checks** — Two-level MariaDB check (socket + query)
- **Code Optimization** — Extracted helpers, fixed duplicate route, reduced app.py by 21%
- **Documentation** — Added missing API endpoints, fixed project structure

### v1.3.5 (2026-08-29)
- **Removed Genre column** — Genre filter and column removed from Collection and Wantlist
- **Format column filtering** — Shows only first 3 comma-separated values

### v1.3.0 (2026-08-28)
- **Wantlist** — Separate page synced from Discogs wantlist
- **Navigation** — Renamed "Search" to "Collection", added Wantlist link
- **Filter Bar** — Removed Country dropdown, all filters on one line

### v1.2.0 (2026-08-28)
- **Health Checks** — MariaDB and LDAP monitoring
- **Database Stats** — Modern dashboard with visual bar chart
- **Track Sync** — Separate sync with status and timestamp

### v1.1.0 (2026-08-27)
- **Filter Cache** — 5-minute cache for filter options

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
│   ├── admin_statistics.html   # Collection statistics dashboard
│   ├── admin_health.html       # Health check status page
│   ├── export_pdf.html         # PDF export template (collection)
│   └── export_pdf_wantlist.html # PDF export template (wantlist)
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
| `/export/csv` | GET | Export filtered results as CSV |
| `/export/pdf` | GET | Export filtered results as PDF |
| `/admin/statistics` | GET | Collection statistics dashboard |
| `/admin/statistics-api/<type>` | GET | Statistics JSON data (format, country, label, decade, summary) |
| `/api/release-detail/<id>` | GET | JSON release detail with tracklist |
| `/admin/sync` | POST | Trigger collection sync |
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
| `SECRET_KEY` | `dev-secret-change-me` | Flask session encryption key AND admin password |
| `DATABASE_URL` | `mysql+pymysql://music:***@10.10.0.10:3306/music_collection` | Database connection string |
| `DISCOGS_TOKEN` | — | Discogs API token |
| `DISCOGS_USERNAME` | — | Your Discogs username |
| `UPDATE_INTERVAL_HOURS` | `24` | Hours between auto-syncs |
| `LDAP_ENABLED` | `false` | Enable LDAP authentication |
| `LDAP_HOST` | — | LDAP server hostname |
| `LDAP_PORT` | `389` | LDAP server port |
| `LDAP_USE_SSL` | `false` | Use LDAPS (SSL) |
| `LDAP_BASE_DN` | — | LDAP base DN for user search |
| `LDAP_BIND_DN` | — | LDAP bind DN for service account |
| `LDAP_BIND_PASSWORD` | — | LDAP bind password |
| `LDAP_USER_FILTER` | `(uid={username})` | LDAP user search filter |
| `LDAP_GROUP_DN` | — | LDAP group DN for membership check |
| `LDAP_ADMIN_GROUP_DN` | — | LDAP admin group DN |
| `TZ` | — | Timezone (e.g., `Europe/Amsterdam`) |

> **Note:** All settings are also configurable via the web Settings panel (except `SECRET_KEY` and `DATABASE_URL` which require container restart).

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
