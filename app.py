import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from apscheduler.schedulers.background import BackgroundScheduler
from functools import wraps
import threading

from config import Config
from models import db, User, Artist, Release, Track, UpdateLog, AppSettings
from sync_service import SyncService
from discogs_client import DiscogsClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

scheduler = BackgroundScheduler()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def get_setting(key, default=None):
    s = AppSettings.query.filter_by(key=key).first()
    return s.value if s else default

def set_setting(key, value):
    s = AppSettings.query.filter_by(key=key).first()
    if s:
        s.value = value
    else:
        s = AppSettings(key=key, value=value)
        db.session.add(s)
    db.session.commit()

# ==================== AUTH ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Username and password required', 'error')
            return render_template('login.html')
        
        # Try LDAP first if enabled
        ldap_enabled = app.config.get('LDAP_ENABLED', False)
        if ldap_enabled:
            user = _try_ldap_login(username, password)
            if user:
                return _complete_login(user)
        
        # Check local admin (fallback)
        if username == 'admin' and password == app.config.get('SECRET_KEY'):
            user = User.query.filter_by(username='admin').first()
            if not user:
                user = User(username='admin', is_admin=True)
                db.session.add(user)
                db.session.commit()
            return _complete_login(user)
        
        flash('Invalid credentials', 'error')
    
    return render_template('login.html')

def _try_ldap_login(username, password):
    """Attempt LDAP authentication"""
    try:
        import ldap
    except ImportError:
        logger.warning("python-ldap not installed")
        return None
    
    host = app.config.get('LDAP_HOST', '')
    port = app.config.get('LDAP_PORT', 389)
    use_ssl = app.config.get('LDAP_USE_SSL', False)
    base_dn = app.config.get('LDAP_BASE_DN', '')
    bind_dn = app.config.get('LDAP_BIND_DN', '')
    bind_password = app.config.get('LDAP_BIND_PASSWORD', '')
    user_filter = app.config.get('LDAP_USER_FILTER', '(uid={username})')
    group_dn = app.config.get('LDAP_GROUP_DN', '')
    admin_group_dn = app.config.get('LDAP_ADMIN_GROUP_DN', '')
    
    if not host or not base_dn:
        return None
    
    protocol = 'ldaps' if use_ssl else 'ldap'
    uri = f"{protocol}://{host}:{port}"
    
    try:
        conn = ldap.initialize(uri)
        conn.set_option(ldap.OPT_REFERRALS, 0)
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 5)
        if use_ssl:
            conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        
        # Bind with service account if provided
        if bind_dn and bind_password:
            conn.simple_bind_s(bind_dn, bind_password)
        
        # Search for user
        search_filter = user_filter.format(username=username)
        result = conn.search_s(base_dn, ldap.SCOPE_SUBTREE, search_filter, ['dn', 'cn', 'mail'])
        
        if not result:
            return None
        
        user_dn = result[0][0]
        
        # Try to bind as user
        user_conn = ldap.initialize(uri)
        user_conn.set_option(ldap.OPT_REFERRALS, 0)
        user_conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 5)
        user_conn.simple_bind_s(user_dn, password)
        
        # Check group membership
        if group_dn:
            group_filter = f"(member={user_dn})"
            group_result = conn.search_s(group_dn, ldap.SCOPE_BASE, group_filter)
            if not group_result:
                logger.info(f"User {username} not in required group")
                return None
        
        # Check admin group
        is_admin = False
        if admin_group_dn:
            admin_filter = f"(member={user_dn})"
            admin_result = conn.search_s(admin_group_dn, ldap.SCOPE_BASE, admin_filter)
            is_admin = bool(admin_result)
        
        # Get or create local user
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, is_admin=is_admin)
            db.session.add(user)
        else:
            user.is_admin = is_admin
        
        conn.unbind()
        user_conn.unbind()
        return user
        
    except ldap.INVALID_CREDENTIALS:
        return None
    except Exception as e:
        logger.error(f"LDAP error: {e}")
        return None

def _complete_login(user):
    user.last_login = datetime.utcnow()
    db.session.commit()
    login_user(user)
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ==================== MAIN PAGES ====================

@app.route('/')
@login_required
def index():
    return redirect(url_for('search'))

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'artist')
    order = request.args.get('order', 'asc')
    format_filter = request.args.get('format', '')
    genre_filter = request.args.get('genre', '')
    style_filter = request.args.get('style', '')
    country_filter = request.args.get('country', '')
    label_filter = request.args.get('label', '')
    year_from = request.args.get('year_from', '')
    year_to = request.args.get('year_to', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 48, type=int)
    # Clamp per_page to reasonable values
    per_page = min(max(per_page, 1), 500)
    
    # Build query
    q = Release.query
    
    if query:
        search_filter = f"%{query}%"
        q = q.filter(
            db.or_(
                Release.title.like(search_filter),
                Release.artist.has(Artist.name.like(search_filter)),
                Release.label.like(search_filter))
        )
    
    if format_filter:
        q = q.filter(Release.format.like(f"%{format_filter}%"))
    
    if genre_filter:
        q = q.filter(Release.genre.like(f"%{genre_filter}%"))
    
    if style_filter:
        q = q.filter(Release.style.like(f"%{style_filter}%"))
    
    if country_filter:
        q = q.filter(Release.country == country_filter)
    
    if label_filter:
        q = q.filter(Release.label.like(f"%{label_filter}%"))
    
    if year_from:
        q = q.filter(Release.year >= int(year_from))
    if year_to:
        q = q.filter(Release.year <= int(year_to))
    
    # Sorting
    sort_map = {
        'title': Release.title,
        'artist': Artist.name,
        'year': Release.year,
        'label': Release.label,
        'date_added': Release.date_added,
        'format': Release.format
    }
    
    sort_col = sort_map.get(sort, Release.title)
    if order == 'desc':
        sort_col = sort_col.desc()
    
    q = q.join(Artist).order_by(sort_col)
    
    # Pagination
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    releases = pagination.items
    
    # Get filter options
    formats = db.session.query(Release.format).distinct().limit(50).all()
    genres = db.session.query(Release.genre).distinct().limit(50).all()
    styles = db.session.query(Release.style).distinct().limit(50).all()
    countries = db.session.query(Release.country).distinct().limit(50).all()
    labels = db.session.query(Release.label).distinct().limit(50).all()
    
    # Serialize releases for JavaScript
    import json
    releases_json = json.dumps([{
        'id': r.id,
        'title': r.title,
        'artist': r.artist.name if r.artist else 'Unknown',
        'year': r.year,
        'format': r.format,
        'genre': r.genre,
        'style': r.style,
        'label': r.label,
        'country': r.country,
        'catalog': r.catalog_number,
        'date_added': r.date_added.strftime('%Y-%m-%d') if r.date_added else '',
        'thumb': r.thumb_url,
        'discogs_id': r.discogs_id
    } for r in releases])
    
    return render_template('search.html',
        releases=releases,
        releases_json=releases_json,
        pagination=pagination,
        query=query,
        sort=sort,
        order=order,
        format_filter=format_filter,
        genre_filter=genre_filter,
        style_filter=style_filter,
        country_filter=country_filter,
        label_filter=label_filter,
        year_from=year_from,
        year_to=year_to,
        formats=[f[0] for f in formats if f[0]],
        genres=[g[0] for g in genres if g[0]],
        styles=[s[0] for s in styles if s[0]],
        countries=[c[0] for c in countries if c[0]],
        labels=[l[0] for l in labels if l[0]]
    )

@app.route('/release/<int:release_id>')
@login_required
def release_detail(release_id):
    release = Release.query.get_or_404(release_id)
    tracks = Track.query.filter_by(release_id=release.id).order_by(Track.position).all()
    return render_template('release.html', release=release, tracks=tracks)

@app.route('/artist/<int:artist_id>')
@login_required
def artist_detail(artist_id):
    artist = Artist.query.get_or_404(artist_id)
    releases = Release.query.filter_by(artist_id=artist.id).order_by(Release.year).all()
    return render_template('artist.html', artist=artist, releases=releases)

# ==================== API ====================

@app.route('/api/search')
@login_required
def api_search():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify([])
    
    search_filter = f"%{query}%"
    releases = Release.query.filter(
        db.or_(
            Release.title.like(search_filter),
            Release.artist.has(Artist.name.like(search_filter))
        )
    ).limit(10).all()
    
    return jsonify([{
        'id': r.id,
        'title': r.title,
        'artist': r.artist.name if r.artist else '',
        'year': r.year,
        'thumb': r.thumb_url
    } for r in releases])

@app.route('/api/release-tracks/<int:release_id>')
@login_required
def api_release_tracks(release_id):
    tracks = Track.query.filter_by(release_id=release_id).order_by(Track.position).all()
    return jsonify([{
        'position': t.position,
        'title': t.title,
        'duration': t.duration
    } for t in tracks])

@app.route('/api/release-detail/<int:release_id>')
@login_required
def api_release_detail(release_id):
    release = Release.query.get_or_404(release_id)
    tracks = Track.query.filter_by(release_id=release.id).order_by(Track.position).all()
    
    return jsonify({
        'id': release.id,
        'discogs_id': release.discogs_id,
        'title': release.title,
        'artist': release.artist.name if release.artist else '',
        'year': release.year,
        'format': release.format,
        'format_details': release.format_details,
        'genre': release.genre,
        'style': release.style,
        'label': release.label,
        'catalog_number': release.catalog_number,
        'country': release.country,
        'thumb_url': release.thumb_url,
        'cover_image_url': release.cover_image_url,
        'date_added': release.date_added.strftime('%Y-%m-%d') if release.date_added else '',
        'notes': release.notes,
        'tracks': [{'position': t.position, 'title': t.title, 'duration': t.duration} for t in tracks]
    })

# ==================== ADMIN / SETTINGS ====================

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_settings():
    if request.method == 'POST':
        # Discogs settings
        set_setting('discogs_token', request.form.get('discogs_token', ''))
        set_setting('discogs_username', request.form.get('discogs_username', ''))
        
        # MariaDB settings
        set_setting('db_host', request.form.get('db_host', '10.10.0.10'))
        set_setting('db_port', request.form.get('db_port', '3306'))
        set_setting('db_name', request.form.get('db_name', 'music_collection'))
        set_setting('db_user', request.form.get('db_user', ''))
        set_setting('db_password', request.form.get('db_password', ''))
        
        # LDAP settings
        set_setting('ldap_enabled', 'true' if request.form.get('ldap_enabled') else 'false')
        set_setting('ldap_host', request.form.get('ldap_host', ''))
        set_setting('ldap_port', request.form.get('ldap_port', '389'))
        set_setting('ldap_use_ssl', 'true' if request.form.get('ldap_use_ssl') else 'false')
        set_setting('ldap_base_dn', request.form.get('ldap_base_dn', ''))
        set_setting('ldap_bind_dn', request.form.get('ldap_bind_dn', ''))
        set_setting('ldap_bind_password', request.form.get('ldap_bind_password', ''))
        set_setting('ldap_user_filter', request.form.get('ldap_user_filter', '(uid={username})'))
        set_setting('ldap_group_dn', request.form.get('ldap_group_dn', ''))
        set_setting('ldap_admin_group_dn', request.form.get('ldap_admin_group_dn', ''))
        
        # Update interval
        set_setting('update_interval_hours', request.form.get('update_interval_hours', '24'))
        
        # Reschedule if needed
        _reschedule_sync()
        
        flash('Settings saved', 'success')
        return redirect(url_for('admin_settings'))
    
    # Load current settings
    settings = {}
    for key in ['discogs_token', 'discogs_username', 'db_host', 'db_port', 'db_name', 'db_user', 'db_password',
                'ldap_enabled', 'ldap_host', 'ldap_port', 'ldap_use_ssl', 'ldap_base_dn', 'ldap_bind_dn',
                'ldap_bind_password', 'ldap_user_filter', 'ldap_group_dn',
                'ldap_admin_group_dn', 'update_interval_hours']:
        settings[key] = get_setting(key, '')
    
    return render_template('admin_settings.html', settings=settings)

@app.route('/admin/sync-status')
@login_required
@admin_required
def admin_sync_status():
    sync_log = UpdateLog.query.order_by(UpdateLog.id.desc()).first()
    
    total_releases = Release.query.count()
    releases_with_tracks = db.session.query(Release.id).join(Track).distinct().count()
    
    total_artists = Artist.query.count()
    
    return render_template('admin_sync_status.html',
        sync_log=sync_log,
        total_releases=total_releases,
        total_artists=total_artists,
        releases_with_tracks=releases_with_tracks,
        releases_without_tracks=total_releases - releases_with_tracks
    )

@app.route('/admin/db-stats')
@login_required
@admin_required
def admin_db_stats():
    tables = db.session.execute(
        db.text("""
            SELECT table_name, 
                   ROUND(data_length / 1024 / 1024, 2) as data_mb,
                   ROUND(index_length / 1024 / 1024, 2) as index_mb,
                   ROUND((data_length + index_length) / 1024 / 1024, 2) as total_mb,
                   table_rows
            FROM information_schema.tables
            WHERE table_schema = 'music_collection'
            ORDER BY (data_length + index_length) DESC
        """)
    ).fetchall()
    
    total_size = sum(t[3] or 0 for t in tables)
    
    return render_template('admin_db_stats.html', tables=tables, total_size=total_size)

@app.route('/admin/sync', methods=['POST'])
@login_required
@admin_required
def trigger_sync():
    token = get_setting('discogs_token', '') or app.config.get('DISCOGS_TOKEN', '')
    username = get_setting('discogs_username', '') or app.config.get('DISCOGS_USERNAME', '')
    
    if not token or not username:
        return jsonify({'error': 'Discogs credentials not configured'}), 400
    
    def do_sync(app_instance):
        with app_instance.app_context():
            try:
                service = SyncService(token, username)
                service.sync_collection(triggered_by='manual')
            except Exception as e:
                logging.error(f"Background sync failed: {e}")
    
    thread = threading.Thread(target=do_sync, args=(app,))
    thread.start()
    
    return jsonify({'status': 'started'})

@app.route('/admin/sync-tracks', methods=['POST'])
@login_required
@admin_required
def trigger_track_sync():
    from flask import current_app
    
    def do_track_sync(app_instance):
        with app_instance.app_context():
            try:
                token = get_setting('discogs_token', '') or app_instance.config.get('DISCOGS_TOKEN', '')
                username = get_setting('discogs_username', '') or app_instance.config.get('DISCOGS_USERNAME', '')
                
                if not token or not username:
                    return
                
                client = DiscogsClient(token, username)
                
                # Get all releases with no tracks
                releases = Release.query.outerjoin(Track).filter(Track.id == None).all()
                total = len(releases)
                logger.info(f"Fetching tracks for {total} releases")
                
                for i, release in enumerate(releases):
                    try:
                        data = client.get_release(release.discogs_id)
                        if data:
                            tracklist = data.get('tracklist', [])
                            if tracklist:
                                # Clear existing tracks first
                                Track.query.filter_by(release_id=release.id).delete()
                                db.session.flush()
                                
                                for t in tracklist:
                                    track = Track(
                                        release_id=release.id,
                                        position=t.get('position', ''),
                                        title=t.get('title', ''),
                                        duration=t.get('duration', '')
                                    )
                                    db.session.add(track)
                                db.session.commit()
                        
                        if (i+1) % 50 == 0:
                            logger.info(f"Track sync: {i+1}/{total}")
                    except Exception as e:
                        logger.error(f"Failed to fetch tracks for release {release.discogs_id}: {e}")
                        db.session.rollback()
                
                logger.info("Track sync complete")
            except Exception as e:
                logging.error(f"Track sync failed: {e}")
    
    thread = threading.Thread(target=do_track_sync, args=(app,))
    thread.start()
    
    return jsonify({'status': 'started'})

@app.route('/admin/sync-tracks-status')
@login_required
@admin_required
def track_sync_status():
    total_releases = Release.query.count()
    releases_with_tracks = db.session.query(Release.id).join(Track).distinct().count()
    return jsonify({
        'total_releases': total_releases,
        'releases_with_tracks': releases_with_tracks,
        'releases_without_tracks': total_releases - releases_with_tracks
    })

@app.route('/admin/sync-status')
@login_required
@admin_required
def sync_status():
    log = UpdateLog.query.order_by(UpdateLog.id.desc()).first()
    if not log:
        return jsonify({'status': 'never_run'})
    return jsonify({
        'status': log.status,
        'started_at': log.started_at.isoformat() if log.started_at else None,
        'finished_at': log.finished_at.isoformat() if log.finished_at else None,
        'releases_added': log.releases_added,
        'releases_updated': log.releases_updated,
        'error_message': log.error_message,
        'triggered_by': log.triggered_by
    })

# ==================== SCHEDULER ====================

def _scheduled_sync():
    """Background sync job"""
    with app.app_context():
        token = get_setting('discogs_token', '')
        username = get_setting('discogs_username', '')
        if token and username:
            try:
                service = SyncService(token, username)
                service.sync_collection(triggered_by='cron')
            except Exception as e:
                logger.error(f"Scheduled sync failed: {e}")

def _reschedule_sync():
    """Reschedule the sync job based on current settings"""
    try:
        interval = int(get_setting('update_interval_hours', '24'))
        if 'sync_job' in scheduler._jobstore:
            scheduler.remove_job('sync_job')
        scheduler.add_job(_scheduled_sync, 'interval', hours=interval, id='sync_job')
    except Exception as e:
        logger.error(f"Failed to reschedule: {e}")

def start_scheduler():
    """Start the scheduler (call from post_fork in gunicorn)"""
    with app.app_context():
        try:
            interval = int(get_setting('update_interval_hours', '24'))
            scheduler.add_job(_scheduled_sync, 'interval', hours=interval, id='sync_job', replace_existing=True)
            scheduler.start()
            logger.info("Scheduler started")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")

# ==================== INIT ====================

def init_db():
    with app.app_context():
        db.create_all()
        # Create default admin if none exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', is_admin=True)
            db.session.add(admin)
            db.session.commit()
            logger.info("Created default admin user")

# Initialize DB on startup
init_db()

# Start scheduler
start_scheduler()
