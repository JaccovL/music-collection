# Music Collection — Discogs Web App

A web application for browsing and managing a personal music collection synced from [Discogs](https://www.discogs.com/). Features full-text search, advanced filtering, multiple views, and automatic daily syncs with Discogs.

## Features

- **Collection Sync** — Import your Discogs collection (releases, artists, tracks) via Discogs API
- **Daily Auto-Update** — Scheduler pulls new additions automatically every 24 hours (configurable)
- **Manual Sync** — Trigger sync from the web UI anytime
- **Full-Text Search** — Search across titles, artists, labels, catalog numbers
- **Advanced Filters** — Filter by Format, Genre, Style, Country, Label, Year range
- **Sortable Columns** — Click any column header to sort
- **Dual Views** — Table view (spreadsheet-like) or Card view (grid of covers)
- **Detail Modal** — Click any release for full info: tracklist, metadata, cover image
- **Duplicate Detection** — Highlights releases with same artist + title
- **Responsive Design** — Works on desktop, tablet, and mobile
- **Dark/Light Theme** — Toggle with one click
- **LDAP Auth Ready** — Settings page configured for LDAP integration
- **Database Stats** — Live view of table sizes and row counts
- **Settings Panel** — Configure Discogs token, update interval, database connection

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

- Docker & Docker Compose
- Python 3.13+ (for local development)
- Discogs account + API token ([get one here](https://www.discogs.com/settings/developers))
- MariaDB 10+

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
   DATABASE_URL=mysql+pymysql://music:password@db-host:3306/music_collection
   ```

3. **Deploy with Docker:**
   ```bash
   docker-compose up -d
   ```
   Or manually:
   ```bash
   docker build -t music-collection .
   docker run -d --name music-collection -p 5000:5000 \
     -e DATABASE_URL="mysql+pymysql://music:password@db-host:3306/music_collection" \
     -e SECRET_KEY="your-secret" \
     -e DISCOGS_TOKEN="your-token" \
     -e DISCOGS_USERNAME="your-username" \
     music-collection
   ```

4. **Access:**
   - Open http://localhost:5000
   - Default login: `admin` / `test-key` (change immediately!)

### Database Setup

```sql
CREATE DATABASE music_collection;
CREATE USER 'music'@'%' IDENTIFIED BY 'your-password';
GRANT ALL PRIVILEGES ON music_collection.* TO 'music'@'%';
FLUSH PRIVILEGES;
```

Tables are auto-created on first run.

## Project Structure

```
music-collection/
├── app.py                  # Main Flask application (routes, auth, settings)
├── config.py               # Configuration class (env vars, defaults)
├── models.py               # SQLAlchemy models (Release, Artist, Track, User, etc.)
├── discogs_client.py       # Discogs API client with rate limiting
├── sync_service.py         # Collection & track sync logic
├── requirements.txt        # Python dependencies
├── Dockerfile              # Multi-stage Docker build
├── docker-compose.yml      # Compose file for easy deployment
├── templates/
│   ├── base.html           # Base template (navbar, theme, layout)
│   ├── search.html         # Main search/listing page (table + cards)
│   ├── release.html        # Release detail page
│   ├── artist.html         # Artist detail page
│   ├── login.html          # Login page
│   ├── admin_settings.html # Settings/configuration panel
│   ├── admin_sync_status.html  # Sync status + triggers
│   └── admin_db_stats.html     # Database statistics
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
| `/login` | POST | Session login |
| `/logout` | GET | Logout |
| `/admin/settings` | GET/POST | Configuration panel |
| `/admin/sync-status` | GET | Sync status page |
| `/admin/sync-collection` | POST | Trigger collection sync |
| `/admin/sync-tracks` | POST | Trigger track sync |
| `/admin/db-stats` | GET | Database statistics |

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
| `SECRET_KEY` | random | Flask session encryption key |
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
