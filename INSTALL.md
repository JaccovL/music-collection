# Music Collection — Complete Installation Guide

Table of Contents
- [Prerequisites](#prerequisites)
- [Database Setup](#database-setup)
- [Application Installation](#application-installation)
  - [Option A: Docker (Recommended)](#option-a-docker-recommended)
  - [Option B: Docker Compose](#option-b-docker-compose)
  - [Option C: Manual (Python)](#option-c-manual-python)
- [Initial Configuration](#initial-configuration)
- [First Sync](#first-sync)
- [LDAP Authentication (Optional)](#ldap-authentication-optional)
- [Reverse Proxy (Optional)](#reverse-proxy-optional)
- [Updating](#updating)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **OS** | Linux (Debian/Ubuntu) | Debian 12 / Ubuntu 22.04+ |
| **RAM** | 2 GB | 4 GB+ |
| **Disk** | 5 GB free | 20 GB+ (for collection images) |
| **Docker** | 20.10+ | Latest |
| **MariaDB** | 10.5+ | 10.10+ |
| **Network** | Outbound to discogs.com | Persistent connection |

### 1. Install Docker

```bash
# Debian/Ubuntu
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in for group change to take effect

# Verify
docker --version
```

### 2. Install Docker Compose (Optional)

```bash
sudo apt install docker-compose-plugin
docker compose version
```

### 3. Install MariaDB

```bash
# On the database host (can be same or different machine)
sudo apt install mariadb-server
sudo mysql_secure_installation
```

---

## Database Setup

### 1. Create Database and User

```bash
sudo mysql -u root -p
```

```sql
CREATE DATABASE music_collection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'music'@'%' IDENTIFIED BY 'DiscoGS2026';
GRANT ALL PRIVILEGES ON music_collection.* TO 'music'@'%';
FLUSH PRIVILEGES;
EXIT;
```

### 2. Add FULLTEXT Indexes (Required for search)

```bash
# On the database host
sudo mysql music_collection
```

```sql
ALTER TABLE releases ADD FULLTEXT INDEX idx_releases_title_fulltext (title);
ALTER TABLE releases ADD FULLTEXT INDEX idx_releases_label_fulltext (label);
ALTER TABLE artists ADD FULLTEXT INDEX idx_artists_name_fulltext (name);
ALTER TABLE tracks ADD FULLTEXT INDEX idx_tracks_title_fulltext (title);
EXIT;
```

---

## Application Installation

### Option A: Docker (Recommended)

#### 1. Create Application Directory

```bash
sudo mkdir -p /opt/music-collection
sudo chown $USER:$USER /opt/music-collection
cd /opt/music-collection
```

#### 2. Create Environment File

```bash
cat > .env << 'EOF'
# Database Configuration
DATABASE_URL=mysql+pymysql://music:DiscoGS2026@YOUR_DB_HOST:3306/music_collection

# Flask Secret Key (generate with: openssl rand -hex 32)
SECRET_KEY=change-me-to-random-string

# Discogs API (https://www.discogs.com/settings/developers)
DISCOGS_TOKEN=your-discogs-token-here
DISCOGS_USERNAME=your-discogs-username

# Timezone
TZ=Europe/Amsterdam

# Server Port
PORT=5000
EOF
```

**Generate a secure secret key:**

```bash
openssl rand -hex 32
```

Edit `.env` and replace `change-me-to-random-string` with the generated key.

#### 3. Get Discogs Token

1. Go to https://www.discogs.com/settings/developers
2. Click **Generate new token**
3. Copy the token to `.env` as `DISCOGS_TOKEN`
4. Set `DISCOGS_USERNAME` to your Discogs username

#### 4. Run the Container

```bash
docker run -d \
  --name music-collection \
  --restart unless-stopped \
  -p 5000:5000 \
  -e TZ=Europe/Amsterdam \
  -e DATABASE_URL="mysql+pymysql://music:DiscoGS2026@YOUR_DB_HOST:3306/music_collection" \
  -e SECRET_KEY="$(openssl rand -hex 32)" \
  -e DISCOGS_TOKEN="your-discogs-token" \
  -e DISCOGS_USERNAME="your-discogs-username" \
  ghcr.io/jaccovl/music-collection:v2.1.0
```

Replace `YOUR_DB_HOST` with your MariaDB server IP/hostname.

#### 5. Verify It's Running

```bash
docker logs music-collection
# Should show: "Listening at: http://0.0.0.0:5000"

docker ps | grep music-collection
# Should show status "Up"
```

---

### Option B: Docker Compose

#### 1. Create Project Directory

```bash
mkdir -p /opt/music-collection
cd /opt/music-collection
```

#### 2. Create `docker-compose.yml`

```yaml
version: '3.8'

services:
  music-collection:
    image: ghcr.io/jaccovl/music-collection:v2.1.0
    container_name: music-collection
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - TZ=Europe/Amsterdam
      - DATABASE_URL=mysql+pymysql://music:DiscoGS2026@YOUR_DB_HOST:3306/music_collection
      - SECRET_KEY=change-me-to-random-string
      - DISCOGS_TOKEN=your-discogs-token-here
      - DISCOGS_USERNAME=your-discogs-username
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

#### 3. Run

```bash
docker compose up -d
docker compose logs -f
```

---

### Option C: Manual (Python)

For advanced users who want to run without Docker.

#### 1. Install System Dependencies

```bash
sudo apt update
sudo apt install -y python3.13 python3.13-venv python3-pip \
  libldap2-dev libsasl2-dev gcc libcairo2 libpango-1.0-0 \
  libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info
```

#### 2. Create User and Directory

```bash
sudo useradd -r -s /bin/false music-collection
sudo mkdir -p /opt/music-collection
sudo chown music-collection:music-collection /opt/music-collection
```

#### 3. Download and Extract Release

```bash
cd /opt/music-collection
sudo -u music-collection wget https://github.com/JaccovL/music-collection/releases/download/v2.1.0/music-collection-v2.1.0.tar.gz
sudo -u music-collection tar -xzf music-collection-v2.1.0.tar.gz --strip-components=1
sudo -u music-collection rm music-collection-v2.1.0.tar.gz
```

#### 4. Create Virtual Environment

```bash
sudo -u music-collection python3.13 -m venv /opt/music-collection/venv
sudo -u music-collection /opt/music-collection/venv/bin/pip install --upgrade pip
sudo -u music-collection /opt/music-collection/venv/bin/pip install -r requirements.txt
```

#### 5. Create Environment File

```bash
sudo -u music-collection cat > /opt/music-collection/.env << 'EOF'
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=change-me-to-random-string
DATABASE_URL=mysql+pymysql://music:DiscoGS2026@YOUR_DB_HOST:3306/music_collection
DISCOGS_TOKEN=your-discogs-token-here
DISCOGS_USERNAME=your-discogs-username
TZ=Europe/Amsterdam
EOF
```

#### 6. Create systemd Service

```bash
sudo cat > /etc/systemd/system/music-collection.service << 'EOF'
[Unit]
Description=Music Collection Web App
After=docker.service network.target
Wants=network-online.target

[Service]
Type=simple
User=music-collection
Group=music-collection
WorkingDirectory=/opt/music-collection
EnvironmentFile=/opt/music-collection/.env
ExecStart=/opt/music-collection/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 1 --preload app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable music-collection
sudo systemctl start music-collection
```

---

## Initial Configuration

### 1. Access the Application

Open your browser: `http://YOUR_SERVER_IP:5000`

### 2. Login

**Default credentials:**
- Username: `admin`
- Password: (your `SECRET_KEY` from `.env`)

> **Security:** Change the SECRET_KEY in settings after first login.

### 3. Configure Settings

Navigate to **Settings** (gear icon in navbar):

| Setting | Description | Required |
|---------|-------------|----------|
| **Discogs Username** | Your Discogs account username | ✅ |
| **Discogs API Token** | From https://www.discogs.com/settings/developers | ✅ |
| **Database Host** | MariaDB server IP/hostname | ✅ |
| **Database Port** | Usually 3306 | ✅ |
| **Database Name** | `music_collection` | ✅ |
| **Database User** | `music` | ✅ |
| **Database Password** | Your DB password | ✅ |
| **Update Interval** | Hours between automatic syncs (default: 24) | 🟡 |
| **Secret Key** | Flask secret key (also used as admin password) | ✅ |

Click **Save Settings**.

---

## First Sync

### 1. Sync Collection

Navigate to **Sync Status** page and click:
1. **🔄 Sync All (Collection + Tracks)** — imports everything
2. Wait for completion (depends on collection size)

### 2. Monitor Progress

- Collection sync: ~100 releases/minute
- Track sync: ~60 releases/minute (Discogs rate limit)
- A 500-release collection takes ~15 minutes total

### 3. Post-Sync Verification

After sync completes, the app automatically verifies data:
- Missing country info → auto-fetched from Discogs
- Missing tracks → auto-fetched from Discogs
- Missing cover images → auto-fetched from Discogs

---

## LDAP Authentication (Optional)

### 1. Enable in Settings

| Setting | Example Value |
|---------|---------------|
| LDAP Enabled | ✅ checked |
| LDAP Host | `ldap.example.com` |
| LDAP Port | `389` (or `636` for SSL) |
| Use SSL | ❌ (or ✅ for LDAPS) |
| Base DN | `dc=example,dc=com` |
| Bind DN | `cn=admin,dc=example,dc=com` |
| Bind Password | `ldap-password` |
| User Filter | `(uid={username})` |
| Group DN | `cn=music-users,ou=groups,dc=example,dc=com` |
| Admin Group DN | `cn=music-admins,ou=groups,dc=example,dc=com` |

### 2. Test LDAP

1. Enable LDAP in settings
2. Try logging in with an LDAP user
3. Check logs if it fails: `docker logs music-collection`

---

## Reverse Proxy (Optional)

### Nginx (Recommended)

```nginx
server {
    listen 80;
    server_name music.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name music.example.com;

    ssl_certificate /etc/letsencrypt/live/music.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/music.example.com/privkey.pem;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/music-collection/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
```

### Traefik (Docker)

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.music.rule=Host(`music.example.com`)"
  - "traefik.http.routers.music.entrypoints=websecure"
  - "traefik.http.routers.music.tls.certresolver=letsencrypt"
  - "traefik.http.services.music.loadbalancer.server.port=5000"
```

---

## Updating

### Docker

```bash
# Pull latest image
docker pull ghcr.io/jaccovl/music-collection:latest

# Stop and remove old container
docker stop music-collection
docker rm music-collection

# Run new version (use same command as installation)
docker run -d \
  --name music-collection \
  --restart unless-stopped \
  -p 5000:5000 \
  -e TZ=Europe/Amsterdam \
  -e DATABASE_URL="mysql+pymysql://music:DiscoGS2026@YOUR_DB_HOST:3306/music_collection" \
  -e SECRET_KEY="your-secret-key" \
  -e DISCOGS_TOKEN="your-discogs-token" \
  -e DISCOGS_USERNAME="your-discogs-username" \
  ghcr.io/jaccovl/music-collection:latest
```

### Docker Compose

```bash
cd /opt/music-collection
docker compose pull
docker compose up -d
```

### Manual

```bash
cd /opt/music-collection
sudo -u music-collection wget https://github.com/JaccovL/music-collection/releases/download/v2.1.0/music-collection-v2.1.0.tar.gz
sudo systemctl stop music-collection
sudo -u music-collection tar -xzf music-collection-v2.1.0.tar.gz --strip-components=1
sudo -u music-collection rm music-collection-v2.1.0.tar.gz
sudo -u music-collection venv/bin/pip install -r requirements.txt
sudo systemctl start music-collection
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs music-collection

# Common issues:
# 1. Database connection failed → Check DATABASE_URL
# 2. Port already in use → Change -p 5000:5000 to -p 8080:5000
# 3. Permission denied → Run with --user $(id -u):$(id -g)
```

### Can't Login

```bash
# Reset SECRET_KEY (used as admin password)
docker exec -it music-collection flask reset-password
```

Or set a new SECRET_KEY in `.env` and restart.

### Sync Stuck or Failing

```bash
# Check Discogs token
docker logs music-collection | grep -i "discogs\|rate\|error"

# Rate limit: 60 requests/minute (authenticated)
# If rate limited, wait 60 seconds — the app auto-retries
```

### Database Connection Issues

```bash
# Test connection from Docker host
mysql -h YOUR_DB_HOST -u music -p music_collection

# Check firewall
sudo ufw allow 3306/tcp  # On DB host
```

### Search Not Working

```bash
# Verify FULLTEXT indexes exist
mysql -u root -p music_collection -e "SHOW INDEX FROM releases WHERE Index_type = 'FULLTEXT';"

# If missing, run the FULLTEXT migration from Database Setup section
```

### Performance Issues

```bash
# Check container resources
docker stats music-collection

# Increase resources if needed
docker update --memory 2g --cpus 2 music-collection
```

### View Logs

```bash
# Live logs
docker logs -f music-collection

# Last 100 lines
docker logs --tail 100 music-collection

# Filter for errors
docker logs music-collection 2>&1 | grep -i error
```

---

## Security Checklist

- [ ] Changed default SECRET_KEY
- [ ] Using HTTPS (reverse proxy with Let's Encrypt)
- [ ] MariaDB user has minimal privileges (only on `music_collection.*`)
- [ ] Firewall allows only necessary ports (80, 443, 5000)
- [ ] Discogs token has minimal scope (read-only)
- [ ] Regular backups of MariaDB database
- [ ] Container runs as non-root user (default in Docker image)

---

## Backup and Restore

### Backup Database

```bash
mysqldump -h YOUR_DB_HOST -u music -p music_collection > backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
mysql -h YOUR_DB_HOST -u music -p music_collection < backup_20260902.sql
```

### Backup Container Config

```bash
cp /opt/music-collection/.env /opt/music-collection/.env.backup
```

---

## Support

- **GitHub Issues:** https://github.com/JaccovL/music-collection/issues
- **Documentation:** https://github.com/JaccovL/music-collection/wiki
- **Discogs API:** https://www.discogs.com/developers
