import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from apscheduler.schedulers.background import BackgroundScheduler
from functools import wraps
import threading
import json

from config import Config
from models import db, User, Artist, Release, Track, UpdateLog, AppSettings
from sync_service import SyncService
from discogs_client import DiscogsClient
from health import run_health_checks, HealthStatus, _health_cache

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

scheduler = BackgroundScheduler()

_filter_cache = {'ts': 0, 'data': {}}
FILTER_CACHE_TTL = 300

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
    if s and s.value:
        return s.value
    return default

def set_setting(key, value):
    s = AppSettings.query.filter_by(key=key).first()
    if s:
        s.value = value
    else:
        s = AppSettings(key=key, value=value)
        db.session.add(s)
    db.session.commit()

def get_filter_options():
    now = datetime.utcnow().timestamp()
    if now - _filter_cache['ts'] < FILTER_CACHE_TTL:
        return _filter_cache['data']
    
    formats = [f[0] for f in db.session.query(Release.format).distinct().limit(50).all() if f[0]]
    genres = [g[0] for g in db.session.query(Release.genre).distinct().limit(50).all() if g[0]]
    styles = [s[0] for s in db.session.query(Release.style).distinct().limit(50).all() if s[0]]
    countries = [c[0] for c in db.session.query(Release.country).distinct().limit(50).all() if c[0]]
    labels = [l[0] for l in db.session.query(Release.label).distinct().limit(50).all() if l[0]]
    
    _filter_cache['data'] = {
        'formats': formats, 'genres': genres, 'styles': styles,
        'countries': countries, 'labels': labels
    }
    _filter_cache['ts'] = now
    return _filter_cache['data']

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
        
        ldap_enabled = get_setting('ldap_enabled', 'false') == 'true'
        ldap_available = False
        
        if ldap_enabled:
            ldap_host = get_setting('ldap_host', '')
            ldap_port = int(get_setting('ldap_port', '389') or '389')
            ldap_use_ssl = get_setting('ldap_use_ssl', 'false') == 'true'
            ldap_bind_dn = get_setting('ldap_bind_dn', '')
            ldap_bind_password = get_setting('ldap_bind_password', '')
            
            status = run_health_checks(
                db_host=get_setting('db_host', '10.10.0.10') or '10.10.0.10',
                db_port=int(get_setting('db_port', '3306') or '3306'),
                ldap_enabled=True,
                ldap_host=ldap_host,
                ldap_port=ldap_port,
                ldap_use_ssl=ldap_use_ssl,
                ldap_bind_dn=ldap_bind_dn,
                ldap_bind_password=ldap_bind_password,
                local_fallback=get_setting('local_fallback', 'true') == 'true'
            )
            
            ldap_available = status.ldap_ok
            
            if not status.ldap_ok and status.ldap_configured:
                logger.warning(f"LDAP unavailable: {status.ldap_error}")
                if get_setting('local_fallback', 'true') == 'true':
                    flash('LDAP unavailable — local login enabled', 'warning')
                else:
                    flash('LDAP unavailable and local fallback disabled', 'error')
                    return render_template('login.html')
        
        if ldap_enabled and ldap_available:
            user = _try_ldap_login(username, password)
            if user:
                return _complete_login(user)
        
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
    try:
        import ldap
    except ImportError:
        logger.warning("python-ldap not installed")
        return None
    
    host = get_setting('ldap_host', '')
    port = int(get_setting('ldap_port', '389') or '389')
    use_ssl = get_setting('ldap_use_ssl', 'false') == 'true'
    base_dn = get_setting('ldap_base_dn', '')
    bind_dn = get_setting('ldap_bind_dn', '')
    bind_password = get_setting('ldap_bind_password', '')
    user_filter = get_setting('ldap_user_filter', '(uid={username})')
    group_dn = get_setting('ldap_group_dn', '')
    admin_group_dn = get_setting('ldap_admin_group_dn', '')
    
    if not host or not base_dn:
        return None
    
    protocol = 'ldaps' if use_ssl else 'ldap'
    uri = f"{protocol}://{host}:{port}"
    
    try:
        conn = ldap.initialize(uri)
        conn.set_option(ldap.OPT_REFERRALS, 0)
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 5)
        conn.set_option(ldap.OPT_TIMEOUT, 5)
        if use_ssl:
            conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        
        if bind_dn and bind_password:
            conn.simple_bind_s(bind_dn, bind_password)
        
        search_filter = user_filter.format(username=username)
        result = conn.search_s(base_dn, ldap.SCOPE_SUBTREE, search_filter, ['dn', 'cn', 'mail'])
        
        if not result:
            return None
        
        user_dn = result[0][0]
        
        user_conn = ldap.initialize(uri)
        user_conn.set_option(ldap.OPT_REFERRALS, 0)
        user_conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 5)
        user_conn.set_option(ldap.OPT_TIMEOUT, 5)
        user_conn.simple_bind_s(user_dn, password)
        
        if group_dn:
            group_filter = f"(member={user_dn})"
            group_result = conn.search_s(group_dn, ldap.SCOPE_BASE, group_filter)
            if not group_result:
                logger.info(f"User {username} not in required group")
                return None
        
        is_admin = False
        if admin_group_dn:
            admin_filter = f"(member={user_dn})"
            admin_result = conn.search_s(admin_group_dn, ldap.SCOPE_BASE, admin_filter)
            is_admin = bool(admin_result)
        
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, is_admin=is_admin)
            db.session.add(user)
        else:
            user.is_admin = is_admin
        
        conn.unbind()
        user_conn.unbind()
        return user
        
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
    per_page = min(max(per_page, 1), 500)
    
    q = Release.query.options(db.joinedload(Release.artist))
    
    if query:
        search_filter = f"%{query}%"
        q = q.filter(
            db.or_(
                Release.title.like(search_filter),
                Artist.name.like(search_filter),
                Release.label.like(search_filter)
            )
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
    
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    releases = pagination.items
    
    filter_opts = get_filter_options()
    
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
        query=query, sort=sort, order=order,
        format_filter=format_filter, genre_filter=genre_filter,
        style_filter=style_filter, country_filter=country_filter,
        label_filter=label_filter, year_from=year_from, year_to=year_to,
        **filter_opts
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
            Artist.name.like(search_filter)
        )
    ).limit(10).all()
    
    return jsonify([{
        'id': r.id, 'title': r.title,
        'artist': r.artist.name if r.artist else '',
        'year': r.year, 'thumb': r.thumb_url
    } for r in releases])

@app.route('/api/release-tracks/<int:release_id>')
@login_required
def api_release_tracks(release_id):
    tracks = Track.query.filter_by(release_id=release_id).order_by(Track.position).all()
    return jsonify([{
        'position': t.position, 'title': t.title, 'duration': t.duration
    } for t in tracks])

@app.route('/api/release-detail/<int:release_id>')
@login_required
def api_release_detail(release_id):
    release = Release.query.get_or_404(release_id)
    tracks = Track.query.filter_by(release_id=release.id).order_by(Track.position).all()
    
    return jsonify({
        'id': release.id, 'discogs_id': release.discogs_id,
        'title': release.title,
        'artist': release.artist.name if release.artist else '',
        'year': release.year, 'format': release.format,
        'format_details': release.format_details,
        'genre': release.genre, 'style': release.style,
        'label': release.label, 'catalog_number': release.catalog_number,
        'country': release.country, 'thumb_url': release.thumb_url,
        'cover_image_url': release.cover_image_url,
        'date_added': release.date_added.strftime('%Y-%m-%d') if release.date_added else '',
        'notes': release.notes,
        'tracks': [{'position': t.position, 'title': t.title, 'duration': t.duration} for t in tracks]
    })

@app.route('/api/health')
@login_required
def api_health():
    db_host = get_setting('db_host', '10.10.0.10') or '10.10.0.10'
    db_port = int(get_setting('db_port', '3306') or '3306')
    ldap_enabled = get_setting('ldap_enabled', 'false') == 'true'
    ldap_host = get_setting('ldap_host', '')
    ldap_port = int(get_setting('ldap_port', '389') or '389')
    ldap_use_ssl = get_setting('ldap_use_ssl', 'false') == 'true'
    ldap_bind_dn = get_setting('ldap_bind_dn', '')
    ldap_bind_password = get_setting('ldap_bind_password', '')
    local_fallback = get_setting('local_fallback', 'true') == 'true'
    
    status = run_health_checks(
        db_host=db_host, db_port=db_port,
        ldap_enabled=ldap_enabled, ldap_host=ldap_host,
        ldap_port=ldap_port, ldap_use_ssl=ldap_use_ssl,
        ldap_bind_dn=ldap_bind_dn, ldap_bind_password=ldap_bind_password,
        local_fallback=local_fallback
    )
    
    return jsonify(status.to_dict())

# ==================== ADMIN / SETTINGS ====================

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_settings():
    if request.method == 'POST':
        set_setting('discogs_token', request.form.get('discogs_token', ''))
        set_setting('discogs_username', request.form.get('discogs_username', ''))
        set_setting('db_host', request.form.get('db_host', '10.10.0.10'))
        set_setting('db_port', request.form.get('db_port', '3306'))
        set_setting('db_name', request.form.get('db_name', 'music_collection'))
        set_setting('db_user', request.form.get('db_user', ''))
        set_setting('db_password', request.form.get('db_password', ''))
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
        set_setting('update_interval_hours', request.form.get('update_interval_hours', '24'))
        set_setting('local_fallback', 'true' if request.form.get('local_fallback') else 'false')
        
        _reschedule_sync()
        _health_cache.invalidate()
        flash('Settings saved', 'success')
        return redirect(url_for('admin_settings'))
    
    settings = {}
    for key in ['discogs_token', 'discogs_username', 'db_host', 'db_port', 'db_name', 'db_user', 'db_password',
                'ldap_enabled', 'ldap_host', 'ldap_port', 'ldap_use_ssl', 'ldap_base_dn', 'ldap_bind_dn',
                'ldap_bind_password', 'ldap_user_filter', 'ldap_group_dn',
                'ldap_admin_group_dn', 'update_interval_hours', 'local_fallback']:
        settings[key] = get_setting(key, '')
    
    return render_template('admin_settings.html', settings=settings)

@app.route('/admin/sync-status')
@login_required
@admin_required
def admin_sync_status():
    sync_log = UpdateLog.query.filter_by(sync_type='collection').order_by(UpdateLog.id.desc()).first()
    track_sync_log = UpdateLog.query.filter_by(sync_type='track').order_by(UpdateLog.id.desc()).first()
    
    total_releases = Release.query.count()
    releases_with_tracks = db.session.query(Release.id).join(Track).distinct().count()
    total_artists = Artist.query.count()
    
    # Format track sync finished time
    track_sync_finished = ''
    if track_sync_log and track_sync_log.finished_at:
        track_sync_finished = track_sync_log.finished_at.strftime('%Y-%m-%d %H:%M')
    
    return render_template('admin_sync_status.html',
        sync_log=sync_log, total_releases=total_releases,
        total_artists=total_artists, releases_with_tracks=releases_with_tracks,
        releases_without_tracks=total_releases - releases_with_tracks,
        track_sync_status=track_sync_log.status if track_sync_log else 'never_run',
        track_sync_finished=track_sync_finished,
        track_sync_error=track_sync_log.error_message if track_sync_log else None
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

@app.route('/admin/health')
@login_required
@admin_required
def admin_health():
    db_host = get_setting('db_host', '10.10.0.10') or '10.10.0.10'
    db_port = int(get_setting('db_port', '3306') or '3306')
    ldap_enabled = get_setting('ldap_enabled', 'false') == 'true'
    ldap_host = get_setting('ldap_host', '')
    ldap_port = int(get_setting('ldap_port', '389') or '389')
    ldap_use_ssl = get_setting('ldap_use_ssl', 'false') == 'true'
    ldap_bind_dn = get_setting('ldap_bind_dn', '')
    ldap_bind_password = get_setting('ldap_bind_password', '')
    local_fallback = get_setting('local_fallback', 'true') == 'true'
    
    status = run_health_checks(
        db_host=db_host, db_port=db_port,
        ldap_enabled=ldap_enabled, ldap_host=ldap_host,
        ldap_port=ldap_port, ldap_use_ssl=ldap_use_ssl,
        ldap_bind_dn=ldap_bind_dn, ldap_bind_password=ldap_bind_password,
        local_fallback=local_fallback
    )
    
    return render_template('admin_health.html', status=status)

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
    # Create update_log entry for track sync
    log = UpdateLog(sync_type='track', status='running', triggered_by='manual')
    db.session.add(log)
    db.session.commit()
    
    def do_track_sync(app_instance):
        with app_instance.app_context():
            try:
                token = get_setting('discogs_token', '') or app_instance.config.get('DISCOGS_TOKEN', '')
                username = get_setting('discogs_username', '') or app_instance.config.get('DISCOGS_USERNAME', '')
                if not token or not username:
                    return
                
                client = DiscogsClient(token, username)
                releases = Release.query.outerjoin(Track).filter(Track.id == None).all()
                total = len(releases)
                logger.info(f"Fetching tracks for {total} releases")
                
                for i, release in enumerate(releases):
                    try:
                        data = client.get_release(release.discogs_id)
                        if data:
                            tracklist = data.get('tracklist', [])
                            if tracklist:
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
                
                # Update log on completion
                log_entry = UpdateLog.query.filter_by(sync_type='track', status='running').order_by(UpdateLog.id.desc()).first()
                if log_entry:
                    log_entry.status = 'success'
                    log_entry.finished_at = datetime.utcnow()
                    db.session.commit()
                
                logger.info("Track sync complete")
            except Exception as e:
                logging.error(f"Track sync failed: {e}")
                log_entry = UpdateLog.query.filter_by(sync_type='track', status='running').order_by(UpdateLog.id.desc()).first()
                if log_entry:
                    log_entry.status = 'error'
                    log_entry.error_message = str(e)
                    log_entry.finished_at = datetime.utcnow()
                    db.session.commit()
    
    thread = threading.Thread(target=do_track_sync, args=(app,))
    thread.start()
    return jsonify({'status': 'started'})

@app.route('/admin/sync-tracks-status')
@login_required
@admin_required
def track_sync_status():
    log = UpdateLog.query.filter_by(sync_type='track').order_by(UpdateLog.id.desc()).first()
    total_releases = Release.query.count()
    releases_with_tracks = db.session.query(Release.id).join(Track).distinct().count()
    
    if not log:
        return jsonify({
            'status': 'never_run',
            'total_releases': total_releases,
            'releases_with_tracks': releases_with_tracks,
            'releases_without_tracks': total_releases - releases_with_tracks,
            'finished_at': None,
            'error_message': None
        })
    
    return jsonify({
        'status': log.status,
        'total_releases': total_releases,
        'releases_with_tracks': releases_with_tracks,
        'releases_without_tracks': total_releases - releases_with_tracks,
        'finished_at': log.finished_at.isoformat() if log.finished_at else None,
        'error_message': log.error_message
    })

@app.route('/admin/sync-status-api')
@login_required
@admin_required
def sync_status():
    """Combined sync status - returns the most recent activity from either collection or track sync."""
    coll_log = UpdateLog.query.filter_by(sync_type='collection').order_by(UpdateLog.id.desc()).first()
    track_log = UpdateLog.query.filter_by(sync_type='track').order_by(UpdateLog.id.desc()).first()
    
    # Use the most recent of the two
    log = None
    if coll_log and track_log:
        log = coll_log if coll_log.started_at >= track_log.started_at else track_log
    elif coll_log:
        log = coll_log
    elif track_log:
        log = track_log
    
    if not log:
        return jsonify({'status': 'never_run'})
    
    return jsonify({
        'status': log.status,
        'sync_type': log.sync_type,
        'started_at': log.started_at.isoformat() if log.started_at else None,
        'finished_at': log.finished_at.isoformat() if log.finished_at else None,
        'releases_added': log.releases_added,
        'releases_updated': log.releases_updated,
        'error_message': log.error_message,
        'triggered_by': log.triggered_by
    })

# ==================== SCHEDULER ====================

def _scheduled_sync():
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
    try:
        interval = int(get_setting('update_interval_hours', '24') or '24')
        if 'sync_job' in scheduler._jobstore:
            scheduler.remove_job('sync_job')
        scheduler.add_job(_scheduled_sync, 'interval', hours=interval, id='sync_job')
    except Exception as e:
        logger.error(f"Failed to reschedule: {e}")

def start_scheduler():
    with app.app_context():
        try:
            interval = int(get_setting('update_interval_hours', '24') or '24')
            scheduler.add_job(_scheduled_sync, 'interval', hours=interval, id='sync_job', replace_existing=True)
            scheduler.start()
            logger.info("Scheduler started")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")

# ==================== INIT ====================

def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', is_admin=True)
            db.session.add(admin)
            db.session.commit()
            logger.info("Created default admin user")

init_db()
start_scheduler()
