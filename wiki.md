---
title: Music Collection
created: 2026-08-24
updated: 2026-08-28
type: project
tags: [music, discogs, webapp, flask, mariadb]
sources: []
---

# Music Collection

## Overview
Web application for presenting and searching a personal music collection, imported from Discogs.
Runs in Docker on the Docker host (192.168.178.98), backed by MariaDB on 10.10.0.10.

- **URL:** http://192.168.178.98:5000
- **Source:** `/opt/data/code-server/workspace/music-collection/`
- **GitHub:** https://github.com/JaccovL/music-collection (v1.3.4)
- **Container:** `music-collection` (persistent, no --rm, TZ=Europe/Amsterdam)

## Architecture
- **Backend:** Flask (Python 3.13) + SQLAlchemy + gunicorn
- **Database:** MariaDB 10.10.0.10 — database `music_collection`, user `music`
- **Discogs API:** Authenticated client, 60 req/min rate limit
- **Auth:** Local admin (username/password) + optional LDAP (admin-provisioned, group-based)
- **Scheduler:** APScheduler — automatic daily sync + manual trigger
- **Frontend:** Server-rendered Jinja2 templates, dark/light theme toggle

## Database Schema
- `users` — local admin/LDAP users
- `artists` — discogs_id, name, profile, image_url
- `releases` — discogs_id, title, artist_id, year, format, genre, style, label, catalog_number, country, thumb_url, cover_image_url, folder_id, date_added, notes
- `tracks` — release_id, position, title, duration
- `wantlist` — discogs_id, title, artist_name, year, format, genre, style, label, country, thumb_url, cover_image_url, notes, date_added, rating
- `update_log` — sync_type (collection/track/wantlist), sync history (status, counts, errors)
- `app_settings` — key-value store for Discogs token, LDAP config, sync interval, features

## Features
- Search with filters (format, genre, style, label, year range) and Reset button
- Wantlist page with separate sync from Discogs wantlist
- **Statistics Dashboard** — Visual breakdowns: pie/bar charts by genre, decade, format, country, label
- Searches across release title, artist name, label, and track titles
- Sortable columns (click any header)
- Table view (spreadsheet-like) and Card view (grid of covers)
- Detail modal — cover image, full release info, tracklist
- Artist page with all releases
- Dark/light theme toggle (single line in Settings dropdown: 🌙 Dark / ☀️ Light)
- Settings dropdown menu:
 - **Configuration** — Discogs credentials, MariaDB connection, LDAP config, sync interval
 - **Sync Status** — live sync progress, trigger collection/track syncs
 - **Database Statistics** — modern dashboard with visual bar chart
- **Collection Statistics** — visual breakdowns with pie/bar charts
 - **Health Check** — MariaDB and LDAP connectivity monitoring
 - **Toggle Theme** — shows current theme, one-click switch
 - **About** — links to GitHub release notes
- Sync status badge (right-aligned in navbar)
- Pagination with "Go to page" and items-per-page dropdown (100/200/500/1000)
- Local Admin Login — fallback when LDAP is unavailable (configurable)
- Health Checks — `/admin/health` page and `/api/health` endpoint
- Search Discogs button — search Discogs.com directly (no API key needed)

## Discogs Integration
- Username: `SR-Jacco`
- Token stored in `app_settings` (or env `DISCOGS_TOKEN`)
- Import: collection/folders → releases → tracks (separate passes)
- Rate limit: 60 requests/minute (authenticated)

## Deployment
```bash
# Rebuild
docker build -t music-collection:latest /opt/data/code-server/workspace/music-collection

# Run (persistent — no --rm, survives restarts)
docker run -d --name music-collection \
 -p 5000:5000 \
 -e TZ=Europe/Amsterdam \
 -e DATABASE_URL="mysql+pymysql://music:***@10.10.0.10:3306/music_collection" \
 -e SECRET_KEY="change-me" \
 -e DISCOGS_TOKEN="..." \
 -e DISCOGS_USERNAME="SR-Jacco" \
 music-collection:latest

# For config changes, restart instead of rebuild+recreate:
docker restart music-collection
```

> **Note:** Using `--rm` causes the container to disappear on every rebuild. For production use, omit `--rm` and use `docker restart` to preserve the container across updates.

## Relationships
- [[docker-host]] — runs on this container host
- [[network-topology]] — accessible on Management VLAN (10.10.0.0/24)
