import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, Response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from apscheduler.schedulers.background import BackgroundScheduler
from functools import wraps
import threading
import json
import csv
import io

# Timezone for display (CEST/CET)
AMSTERDAM_TZ = ZoneInfo('Europe/Amsterdam')

def now_amsterdam():
    """Get current time in UTC for storage."""
    return datetime.utcnow()

def utc_to_amsterdam(dt):
    """Convert UTC datetime to Amsterdam timezone."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo('UTC'))
    return dt.astimezone(AMSTERDAM_TZ)

from config import Config
from models import db, User, Artist, Release, Track, UpdateLog, AppSettings, Wantlist
from sync_service import SyncService, _sync_tracks_for_releases, _verify_sync, _fix_missing_fields
from discogs_client import DiscogsClient
from health import run_health_checks, _health_cache

# ==================== APP SETUP ====================

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

# ==================== HELPERS ====================

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
    return s.value if s and s.value else default

app.jinja_env.globals['get_setting'] = get_setting
app.jinja_env.globals['utc_to_amsterdam'] = utc_to_amsterdam

def set_setting(key, value):
    s = AppSettings.query.filter_by(key=key).first()
    if s:
        s.value = value
    else:
        s = AppSettings(key=key, value=value)
        db.session.add(s)
    db.session.commit()

def get_distinct(column, limit=50):
    """Get distinct non-null values from a column."""
    return [r[0] for r in db.session.query(column).distinct().limit(limit).all() if r[0]]

def get_filter_options():
    """Get filter options with caching."""
    now = now_amsterdam().timestamp()
    if now - _filter_cache['ts'] < FILTER_CACHE_TTL:
        return _filter_cache['data']
    
    _filter_cache['data'] = {
        'formats': get_distinct(Release.format),
        'styles': get_distinct(Release.style),
        'countries': get_distinct(Release.country),
        'labels': get_distinct(Release.label),
    }
    _filter_cache['ts'] = now
    return _filter_cache['data']

def get_health_status():
    """Get consolidated health status for all pages."""
    settings = {k: get_setting(k, '') for k in [
        'db_host', 'db_port', 'ldap_enabled', 'ldap_host', 'ldap_port',
        'ldap_use_ssl', 'ldap_bind_dn', 'ldap_bind_password', 'local_fallback'
    ]}
    
    return run_health_checks(
        db_host=settings['db_host'] or '10.10.0.10',
        db_port=int(settings['db_port'] or '3306'),
        ldap_enabled=settings['ldap_enabled'] == 'true',
        ldap_host=settings['ldap_host'],
        ldap_port=int(settings['ldap_port'] or '389'),
        ldap_use_ssl=settings['ldap_use_ssl'] == 'true',
        ldap_bind_dn=settings['ldap_bind_dn'],
        ldap_bind_password=settings['ldap_bind_password'],
        local_fallback=settings['local_fallback'] == 'true'
    )

def get_request_filters():
    """Extract and return common filter parameters from request."""
    return {
        'search': request.args.get('q', '').strip(),
        'format_filter': request.args.get('format', '').strip(),
        'style_filter': request.args.get('style', '').strip(),
        'label_filter': request.args.get('label', '').strip(),
        'year_from': request.args.get('year_from', '').strip(),
        'year_to': request.args.get('year_to', '').strip(),
    }

def apply_common_filters(q, search, format_filter, style_filter, label_filter, year_from, year_to, model=Release):
    """Apply common filters to a query."""
    if search:
        search_filter = f"%{search}%"
        if model == Release:
            q = q.outerjoin(Track, Track.release_id == Release.id)
            q = q.filter(db.or_(
                Release.title.like(search_filter),
                Artist.name.like(search_filter),
                Release.label.like(search_filter),
                Track.title.like(search_filter)
            ))
        else:
            q = q.filter(db.or_(
                Wantlist.title.like(search_filter),
                Wantlist.artist_name.like(search_filter),
                Wantlist.label.like(search_filter)
            ))
        q = q.distinct()
    
    if format_filter:
        q = q.filter(model.format.like(f"%{format_filter}%"))
    if style_filter:
        q = q.filter(model.style.like(f"%{style_filter}%"))
    if label_filter:
        q = q.filter(model.label.like(f"%{label_filter}%"))
    if year_from:
        q = q.filter(model.year >= int(year_from))
    if year_to:
        q = q.filter(model.year <= int(year_to))
    
    return q

def export_to_csv(headers, rows, filename):
    """Generate CSV response from headers and rows."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename={filename}'})

def export_to_pdf(template, context, filename):
    """Generate PDF response from template."""
    from weasyprint import HTML
    html = render_template(template, **context, now=now_amsterdam())
    pdf = HTML(string=html).write_pdf()
    return Response(pdf, mimetype='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename={filename}'})

def _run_in_background(fn, sync_type=None):
    """Run a function in a background thread with app context."""
    def wrapper(app_instance):
        with app_instance.app_context():
            try:
                fn(app_instance)
            except Exception as e:
                logging.error(f"Background task {fn.__name__} failed: {e}")
            finally:
                if sync_type:
                    _active_syncs.pop(sync_type, None)
    
    thread = threading.Thread(target=wrapper, args=(app,))
    if sync_type:
        _active_syncs[sync_type] = thread
    thread.start()


# Sync lock to prevent concurrent syncs
_sync_lock = threading.Lock()

# Cancel events for running syncs
_cancel_events = {
    'collection': threading.Event(),
    'track': threading.Event(),
    'wantlist': threading.Event(),
}

# Track running sync threads
_active_syncs = {}


@app.route('/admin/cancel-sync', methods=['POST'])
@login_required
@admin_required
def cancel_sync():
    """Cancel a running sync."""
    data = request.get_json() or {}
    sync_type = data.get('sync_type', 'collection')
    
    if sync_type not in _cancel_events:
        return jsonify({'error': 'Invalid sync type'}), 400
    
    if sync_type not in _active_syncs:
        return jsonify({'error': f'No active {sync_type} sync to cancel'}), 404
    
    # Signal cancellation
    _cancel_events[sync_type].set()
    
    # Update log
    log = UpdateLog.query.filter_by(sync_type=sync_type, status='running').order_by(UpdateLog.id.desc()).first()
    if log:
        log.status = 'error'
        log.error_message = 'Cancelled by user'
        log.finished_at = now_amsterdam()
        db.session.commit()
    
    return jsonify({'status': 'cancelled', 'message': f'{sync_type} sync cancelled'})


def _is_cancelled(sync_type):
    """Check if a sync has been cancelled."""
    return _cancel_events.get(sync_type, threading.Event()).is_set()


def _reset_cancel(sync_type):
    """Reset the cancel event for a sync type."""
    if sync_type in _cancel_events:
        _cancel_events[sync_type].clear()


# ==================== ADMIN / SETTINGS ====================

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
        
        if ldap_enabled:
            status = get_health_status()
            if status.ldap_ok:
                user = _try_ldap_login(username, password)
                if user:
                    return _complete_login(user)
            elif status.ldap_configured:
                if get_setting('local_fallback', 'true') == 'true':
                    flash('LDAP unavailable — local login enabled', 'warning')
                else:
                    flash('LDAP unavailable and local fallback disabled', 'error')
                    return render_template('login.html')
        
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
    """Attempt LDAP authentication."""
    try:
        import ldap
    except ImportError:
        return None
    
    host = get_setting('ldap_host', '')
    port = int(get_setting('ldap_port', '389') or '389')
    use_ssl = get_setting('ldap_use_ssl', 'false') == 'true'
    base_dn = get_setting('ldap_base_dn', '')
    
    if not host or not base_dn:
        return None
    
    uri = f"{'ldaps' if use_ssl else 'ldap'}://{host}:{port}"
    
    try:
        conn = ldap.initialize(uri)
        conn.set_option(ldap.OPT_REFERRALS, 0)
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 5)
        conn.set_option(ldap.OPT_TIMEOUT, 5)
        if use_ssl:
            conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        
        bind_dn = get_setting('ldap_bind_dn', '')
        bind_password = get_setting('ldap_bind_password', '')
        if bind_dn and bind_password:
            conn.simple_bind_s(bind_dn, bind_password)
        
        user_filter = get_setting('ldap_user_filter', '(uid={username})')
        result = conn.search_s(base_dn, ldap.SCOPE_SUBTREE, user_filter.format(username=username), ['dn', 'cn', 'mail'])
        
        if not result:
            return None
        
        user_dn = result[0][0]
        user_conn = ldap.initialize(uri)
        user_conn.set_option(ldap.OPT_REFERRALS, 0)
        user_conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 5)
        user_conn.set_option(ldap.OPT_TIMEOUT, 5)
        user_conn.simple_bind_s(user_dn, password)
        
        group_dn = get_setting('ldap_group_dn', '')
        if group_dn:
            group_result = conn.search_s(group_dn, ldap.SCOPE_BASE, f"(member={user_dn})")
            if not group_result:
                return None
        
        is_admin = False
        admin_group_dn = get_setting('ldap_admin_group_dn', '')
        if admin_group_dn:
            admin_result = conn.search_s(admin_group_dn, ldap.SCOPE_BASE, f"(member={user_dn})")
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
    user.last_login = now_amsterdam()
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
    filters = get_request_filters()
    page = request.args.get('page', 1, type=int)
    per_page = min(max(request.args.get('per_page', 48, type=int), 1), 500)
    sort = request.args.get('sort', 'artist')
    order = request.args.get('order', 'asc')
    
    q = Release.query.options(db.joinedload(Release.artist))
    q = apply_common_filters(q, **filters)
    
    sort_map = {
        'title': Release.title, 'artist': Artist.name, 'year': Release.year,
        'label': Release.label, 'date_added': Release.date_added, 'format': Release.format
    }
    sort_col = sort_map.get(sort, Release.title)
    q = q.join(Artist).order_by(sort_col.desc() if order == 'desc' else sort_col)
    
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    releases = pagination.items
    
    releases_json = json.dumps([{
        'id': r.id, 'title': r.title,
        'artist': r.artist.name if r.artist else 'Unknown',
        'year': r.year, 'format': r.format, 'format_details': r.format_details,
        'style': r.style, 'label': r.label, 'country': r.country,
        'catalog': r.catalog_number,
        'date_added': r.date_added.strftime('%Y-%m-%d') if r.date_added else '',
        'thumb': r.thumb_url, 'discogs_id': r.discogs_id
    } for r in releases])
    
    return render_template('search.html',
        releases=releases, releases_json=releases_json, pagination=pagination,
        query=filters['search'], sort=sort, order=order,
        format_filter=filters['format_filter'],
        style_filter=filters['style_filter'], label_filter=filters['label_filter'],
        year_from=filters['year_from'], year_to=filters['year_to'],
        **get_filter_options()
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
        db.or_(Release.title.like(search_filter), Artist.name.like(search_filter))
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
    return jsonify([{'position': t.position, 'title': t.title, 'duration': t.duration} for t in tracks])

@app.route('/api/discogs-release/<int:discogs_id>')
@login_required
def api_discogs_release(discogs_id):
    """Fetch release details from Discogs API (for wantlist items)."""
    token = get_setting('discogs_token', '') or app.config.get('DISCOGS_TOKEN', '')
    username = get_setting('discogs_username', '') or app.config.get('DISCOGS_USERNAME', '')
    
    if not token or not username:
        return jsonify({'error': 'Discogs credentials not configured'}), 400
    
    client = DiscogsClient(token, username)
    data = client.get_release(discogs_id)
    
    if not data:
        return jsonify({'error': 'Failed to fetch from Discogs'}), 500
    
    return jsonify({
        'discogs_id': discogs_id,
        'title': data.get('title', ''),
        'year': data.get('year'),
        'format': ', '.join(f.get('name', '') for f in data.get('formats', [])),
        'style': ', '.join(data.get('styles', [])),
        'label': data.get('labels', [{}])[0].get('name') if data.get('labels') else None,
        'catalog_number': data.get('labels', [{}])[0].get('catno') if data.get('labels') else None,
        'country': data.get('country'),
        'tracks': [{'position': t.get('position', ''), 'title': t.get('title', ''), 'duration': t.get('duration', '')} 
                   for t in data.get('tracklist', [])]
    })

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
        'style': release.style,
        'label': release.label, 'catalog_number': release.catalog_number,
        'country': release.country, 'thumb_url': release.thumb_url,
        'cover_image_url': release.cover_image_url,
        'date_added': release.date_added.strftime('%Y-%m-%d') if release.date_added else '',
        'notes': release.notes,
        'tracks': [{'position': t.position, 'title': t.title, 'duration': t.duration} for t in tracks]
    })

@app.route('/api/random-release')
@login_required
def api_random_release():
    """Return a random release from the current filtered results."""
    filters = get_request_filters()
    q = Release.query.options(db.joinedload(Release.artist))
    q = apply_common_filters(q, **filters)
    
    random_release = q.order_by(db.func.random()).first()
    
    if not random_release:
        return jsonify({'error': 'No releases found'}), 404
    
    return jsonify({
        'id': random_release.id,
        'title': random_release.title,
        'artist': random_release.artist.name if random_release.artist else 'Unknown',
        'year': random_release.year,
        'format': random_release.format,
        'format_details': random_release.format_details,
        'style': random_release.style,
        'label': random_release.label,
        'catalog_number': random_release.catalog_number,
        'country': random_release.country,
        'thumb_url': random_release.thumb_url,
        'cover_image_url': random_release.cover_image_url,
        'discogs_id': random_release.discogs_id,
        'date_added': random_release.date_added.strftime('%Y-%m-%d') if random_release.date_added else '',
    })

@app.route('/api/health')
@login_required
def api_health():
    return jsonify(get_health_status().to_dict())

# ==================== ADMIN / SETTINGS ====================

@app.route('/admin/reset-collection', methods=['POST'])
@login_required
@admin_required
def reset_collection():
    """Drop all collection data (releases, artists, tracks, wantlist) and start fresh."""
    global _sync_lock
    
    if not _sync_lock.acquire(blocking=False):
        return jsonify({'error': 'A sync is already running. Wait for it to finish.'}), 409
    
    try:
        from sqlalchemy import text
        
        # Use TRUNCATE TABLE to avoid "Record has changed" errors from concurrent access
        # Disable foreign key checks temporarily since TRUNCATE doesn't cascade
        db.session.execute(text('SET FOREIGN_KEY_CHECKS=0'))
        db.session.execute(text('TRUNCATE TABLE tracks'))
        db.session.execute(text('TRUNCATE TABLE releases'))
        db.session.execute(text('TRUNCATE TABLE artists'))
        db.session.execute(text('TRUNCATE TABLE wantlist'))
        db.session.execute(text('TRUNCATE TABLE update_log'))
        db.session.execute(text('SET FOREIGN_KEY_CHECKS=1'))
        db.session.commit()
        
        # Invalidate health cache
        _health_cache.invalidate()
        
        # Reset cancel events for clean state
        for event in _cancel_events.values():
            event.clear()
        
        return jsonify({'status': 'success', 'message': 'Collection cleared. You can now sync fresh from Discogs.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Reset failed: {e}'}), 500
    finally:
        _sync_lock.release()

@app.route('/admin/sync-all', methods=['POST'])
@login_required
@admin_required
def sync_all():
    """Run collection sync followed by track sync sequentially."""
    global _sync_lock
    
    if not _sync_lock.acquire(blocking=False):
        return jsonify({'error': 'A sync is already running. Wait for it to finish.'}), 409
    
    token = get_setting('discogs_token', '') or app.config.get('DISCOGS_TOKEN', '')
    username = get_setting('discogs_username', '') or app.config.get('DISCOGS_USERNAME', '')
    
    if not token or not username:
        _sync_lock.release()
        return jsonify({'error': 'Discogs credentials not configured'}), 400
    
    # Reset cancel event for this sync type
    _reset_cancel('collection')
    _reset_cancel('track')
    
    def do_sync_all(app_instance):
        try:
            service = SyncService(token, username)
            service.sync_collection(triggered_by='manual', fetch_country=True)
            if _is_cancelled('collection'):
                logger.info("Sync all cancelled after collection sync")
                return
            releases = Release.query.outerjoin(Track).filter(Track.id == None).all()
            if releases and not _is_cancelled('track'):
                client = DiscogsClient(token, username)
                _sync_tracks_for_releases(releases, client)
        except Exception as e:
            logger.error(f"Sync all failed: {e}")
        finally:
            _sync_lock.release()
    
    _run_in_background(do_sync_all, sync_type='collection')
    return jsonify({'status': 'started', 'message': 'Collection sync started, track sync will follow automatically.'})

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_settings():
    if request.method == 'POST':
        settings_map = {
            'discogs_token': request.form.get('discogs_token', ''),
            'discogs_username': request.form.get('discogs_username', ''),
            'db_host': request.form.get('db_host', '10.10.0.10'),
            'db_port': request.form.get('db_port', '3306'),
            'db_name': request.form.get('db_name', 'music_collection'),
            'db_user': request.form.get('db_user', ''),
            'db_password': request.form.get('db_password', ''),
            'ldap_enabled': 'true' if request.form.get('ldap_enabled') else 'false',
            'ldap_host': request.form.get('ldap_host', ''),
            'ldap_port': request.form.get('ldap_port', '389'),
            'ldap_use_ssl': 'true' if request.form.get('ldap_use_ssl') else 'false',
            'ldap_base_dn': request.form.get('ldap_base_dn', ''),
            'ldap_bind_dn': request.form.get('ldap_bind_dn', ''),
            'ldap_bind_password': request.form.get('ldap_bind_password', ''),
            'ldap_user_filter': request.form.get('ldap_user_filter', '(uid={username})'),
            'ldap_group_dn': request.form.get('ldap_group_dn', ''),
            'ldap_admin_group_dn': request.form.get('ldap_admin_group_dn', ''),
            'update_interval_hours': request.form.get('update_interval_hours', '24'),
            'local_fallback': 'true' if request.form.get('local_fallback') else 'false',
            'wantlist_enabled': 'true' if request.form.get('wantlist_enabled') else 'false',
        }
        for key, value in settings_map.items():
            set_setting(key, value)
        
        _reschedule_sync()
        _health_cache.invalidate()
        flash('Settings saved', 'success')
        return redirect(url_for('admin_settings'))
    
    keys = ['discogs_token', 'discogs_username', 'db_host', 'db_port', 'db_name', 'db_user', 'db_password',
            'ldap_enabled', 'ldap_host', 'ldap_port', 'ldap_use_ssl', 'ldap_base_dn', 'ldap_bind_dn',
            'ldap_bind_password', 'ldap_user_filter', 'ldap_group_dn',
            'ldap_admin_group_dn', 'update_interval_hours', 'local_fallback', 'wantlist_enabled']
    settings = {key: get_setting(key, '') for key in keys}
    
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
    
    track_sync_finished = ''
    if track_sync_log and track_sync_log.finished_at:
        track_sync_finished = track_sync_log.finished_at.strftime('%Y-%m-%d %H:%M')
    
    # Flash alert if verification failed
    if sync_log and sync_log.verification_status == 'failed' and sync_log.missing_fields:
        import json
        try:
            missing = json.loads(sync_log.missing_fields)
            flash(f'Missing data detected: {", ".join(f"{k}: {v}" for k, v in missing.items())} — auto-fix in progress...', 'warning')
        except:
            flash('Missing data detected — auto-fix in progress...', 'warning')
    elif sync_log and sync_log.verification_status == 'passed':
        flash('All data verified complete', 'success')
    
    return render_template('admin_sync_status.html',
        sync_log=sync_log, total_releases=total_releases,
        total_artists=total_artists, releases_with_tracks=releases_with_tracks,
        releases_without_tracks=total_releases - releases_with_tracks,
        track_sync_status=track_sync_log.status if track_sync_log else 'never_run',
        track_sync_finished=track_sync_finished,
        track_sync_error=track_sync_log.error_message if track_sync_log else None,
        verification_status=sync_log.verification_status if sync_log else None,
        missing_fields=sync_log.missing_fields if sync_log else None
    )

@app.route('/admin/db-stats')
@login_required
@admin_required
def admin_db_stats():
    tables = db.session.execute(db.text("""
        SELECT table_name, 
               ROUND(data_length / 1024 / 1024, 2) as data_mb,
               ROUND(index_length / 1024 / 1024, 2) as index_mb,
               ROUND((data_length + index_length) / 1024 / 1024, 2) as total_mb,
               table_rows
        FROM information_schema.tables
        WHERE table_schema = 'music_collection'
        ORDER BY (data_length + index_length) DESC
    """)).fetchall()
    
    total_size = sum(t[3] or 0 for t in tables)
    return render_template('admin_db_stats.html', tables=tables, total_size=total_size)

@app.route('/admin/statistics')
@login_required
@admin_required
def admin_statistics():
    return render_template('admin_statistics.html')

@app.route('/admin/statistics-api/<chart_type>')
@login_required
@admin_required
def statistics_api(chart_type):
    """Return JSON data for statistics charts."""
    
    chart_queries = {
        'format': (Release.format, Release.format),
        'style': (Release.style, Release.style),
        'country': (Release.country, Release.country),
        'label': (Release.label, Release.label),
    }
    
    if chart_type in chart_queries:
        col, group_col = chart_queries[chart_type]
        data = db.session.query(col, db.func.count(Release.id)).group_by(group_col).order_by(db.func.count(Release.id).desc()).limit(15).all()
        result = [{'label': d[0] or 'Unknown', 'value': d[1]} for d in data if d[0]]
        
    elif chart_type == 'decade':
        data = db.session.query(
            db.func.floor(Release.year / 10) * 10,
            db.func.count(Release.id)
        ).filter(Release.year > 0).group_by(db.func.floor(Release.year / 10) * 10).order_by(db.func.floor(Release.year / 10) * 10).all()
        result = [{'label': f"{int(d[0])}s", 'value': d[1]} for d in data if d[0]]
        
    elif chart_type == 'summary':
        total_releases = Release.query.count()
        total_artists = Artist.query.count()
        total_tracks = Track.query.count()
        
        year_range = db.session.query(
            db.func.min(Release.year), db.func.max(Release.year)
        ).filter(Release.year > 0).first()
        
        avg_tracks = db.func.count(Track.id).cast(db.Float) / db.func.count(db.distinct(Track.release_id))
        avg_result = db.session.query(avg_tracks).scalar()
        
        top_format = db.session.query(Release.format, db.func.count(Release.id)).group_by(Release.format).order_by(db.func.count(Release.id).desc()).first()
        
        result = {
            'total_releases': total_releases,
            'total_artists': total_artists,
            'total_tracks': total_tracks,
            'year_min': int(year_range[0]) if year_range[0] else None,
            'year_max': int(year_range[1]) if year_range[1] else None,
            'avg_tracks_per_release': round(avg_result, 1) if avg_result else 0,
            'top_format': top_format[0] if top_format else 'N/A',
        }
    else:
        return jsonify({'error': 'Unknown chart type'}), 400
    
    return jsonify(result)

@app.route('/admin/health')
@login_required
@admin_required
def admin_health():
    return render_template('admin_health.html', status=get_health_status())

@app.route('/admin/verify-sync', methods=['POST'])
@login_required
@admin_required
def verify_sync():
    """Verify the latest sync and fix missing fields."""
    latest_log = UpdateLog.query.filter_by(sync_type='collection').order_by(UpdateLog.id.desc()).first()
    if not latest_log:
        return jsonify({'error': 'No sync log found'}), 404
    
    if latest_log.status == 'running':
        return jsonify({'status': 'running', 'message': 'Sync still running'}), 202
    
    # Run verification
    missing = _verify_sync(latest_log)
    if missing:
        # Get credentials
        token = get_setting('discogs_token', '') or app.config.get('DISCOGS_TOKEN', '')
        username = get_setting('discogs_username', '') or app.config.get('DISCOGS_USERNAME', '')
        if not token or not username:
            return jsonify({'error': 'Discogs credentials not configured'}), 400
        
        # Fix missing fields
        _fix_missing_fields(missing, token, username, latest_log)
        # Re-verify
        missing = _verify_sync(latest_log)
        
        if missing:
            return jsonify({
                'status': 'failed',
                'message': f'Still missing: {missing}',
                'verification_status': latest_log.verification_status
            })
        return jsonify({
            'status': 'fixed',
            'message': 'Missing fields fixed',
            'verification_status': latest_log.verification_status
        })
    
    return jsonify({
        'status': 'passed',
        'message': 'All data verified',
        'verification_status': latest_log.verification_status
    })


@app.route('/admin/sync', methods=['POST'])
@login_required
@admin_required
def trigger_sync():
    global _sync_lock
    
    if not _sync_lock.acquire(blocking=False):
        return jsonify({'error': 'A sync is already running. Wait for it to finish.'}), 409
    
    token = get_setting('discogs_token', '') or app.config.get('DISCOGS_TOKEN', '')
    username = get_setting('discogs_username', '') or app.config.get('DISCOGS_USERNAME', '')
    
    if not token or not username:
        _sync_lock.release()
        return jsonify({'error': 'Discogs credentials not configured'}), 400
    
    # Reset cancel event
    _reset_cancel('collection')
    
    def do_sync(app_instance):
        try:
            service = SyncService(token, username)
            service.sync_collection(triggered_by='manual', fetch_country=True)
        finally:
            _sync_lock.release()
    
    _run_in_background(do_sync, sync_type='collection')
    return jsonify({'status': 'started'})

@app.route('/admin/sync-tracks', methods=['POST'])
@login_required
@admin_required
def trigger_track_sync():
    global _sync_lock
    
    if not _sync_lock.acquire(blocking=False):
        return jsonify({'error': 'A sync is already running. Wait for it to finish.'}), 409
    
    log = UpdateLog(sync_type='track', status='running', triggered_by='manual')
    db.session.add(log)
    db.session.commit()
    
    # Reset cancel event
    _reset_cancel('track')
    
    def do_track_sync(app_instance):
        try:
            token = get_setting('discogs_token', '') or app_instance.config.get('DISCOGS_TOKEN', '')
            username = get_setting('discogs_username', '') or app_instance.config.get('DISCOGS_USERNAME', '')
            if not token or not username:
                return
            
            client = DiscogsClient(token, username)
            releases = Release.query.outerjoin(Track).filter(Track.id == None).all()
            log_entry = UpdateLog.query.filter_by(sync_type='track', status='running').order_by(UpdateLog.id.desc()).first()
            _sync_tracks_for_releases(releases, client, log_entry)
        except Exception as e:
            logging.error(f"Track sync failed: {e}")
            log_entry = UpdateLog.query.filter_by(sync_type='track', status='running').order_by(UpdateLog.id.desc()).first()
            if log_entry:
                log_entry.status = 'error'
                log_entry.error_message = str(e)
                log_entry.finished_at = now_amsterdam()
                db.session.commit()
        finally:
            _sync_lock.release()
    
    _run_in_background(do_track_sync, sync_type='track')
    return jsonify({'status': 'started'})

@app.route('/admin/sync-wantlist', methods=['POST'])
@login_required
@admin_required
def trigger_wantlist_sync():
    global _sync_lock
    
    if not _sync_lock.acquire(blocking=False):
        return jsonify({'error': 'A sync is already running. Wait for it to finish.'}), 409
    
    token = get_setting('discogs_token', '') or app.config.get('DISCOGS_TOKEN', '')
    username = get_setting('discogs_username', '') or app.config.get('DISCOGS_USERNAME', '')
    
    if not token or not username:
        _sync_lock.release()
        return jsonify({'error': 'Discogs credentials not configured'}), 400
    
    # Reset cancel event
    _reset_cancel('wantlist')
    
    def do_wantlist_sync(app_instance):
        try:
            service = SyncService(token, username)
            service.sync_wantlist(triggered_by='manual')
        finally:
            _sync_lock.release()
    
    _run_in_background(do_wantlist_sync, sync_type='wantlist')
    return jsonify({'status': 'started'})

@app.route('/admin/sync-wantlist-status')
@login_required
@admin_required
def wantlist_sync_status():
    log = UpdateLog.query.filter_by(sync_type='wantlist').order_by(UpdateLog.id.desc()).first()
    total_wants = Wantlist.query.count()
    
    if not log:
        return jsonify({'status': 'never_run', 'total_wants': total_wants, 'finished_at': None, 'error_message': None})
    
    return jsonify({
        'status': log.status, 'total_wants': total_wants,
        'added': log.releases_added, 'updated': log.releases_updated,
        'finished_at': (log.finished_at.isoformat() + 'Z') if log.finished_at else None,
        'error_message': log.error_message
    })

@app.route('/wantlist')
@login_required
def wantlist():
    filters = get_request_filters()
    page = request.args.get('page', 1, type=int)
    per_page = min(max(request.args.get('per_page', 48, type=int), 1), 500)
    
    q = Wantlist.query
    q = apply_common_filters(q, **filters, model=Wantlist)
    
    total = q.count()
    pages = (total + per_page - 1) // per_page
    items_raw = q.order_by(Wantlist.date_added.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    items = [{
        'id': item.id, 'discogs_id': item.discogs_id, 'title': item.title,
        'artist': item.artist_name, 'year': item.year, 'format': item.format,
        'format_details': item.format_details, 'style': item.style, 'label': item.label,
        'catalog_number': item.catalog_number, 'country': item.country,
        'thumb': item.thumb_url, 'cover_image_url': item.cover_image_url,
        'date_added': item.date_added.strftime('%Y-%m-%d') if item.date_added else '',
        'notes': item.notes, 'rating': item.rating
    } for item in items_raw]
    
    return render_template('wantlist.html',
        items_json=json.dumps(items), items=items_raw,
        page=page, per_page=per_page, pages=pages, total=total,
        search=filters['search'], format_filter=filters['format_filter'],
        style_filter=filters['style_filter'],
        label_filter=filters['label_filter'], year_from=filters['year_from'],
        year_to=filters['year_to'],
        formats=sorted(set(r[0] for r in db.session.query(Wantlist.format).distinct().all() if r[0])),
        styles=sorted(set(r[0] for r in db.session.query(Wantlist.style).distinct().all() if r[0])),
        labels=sorted(set(r[0] for r in db.session.query(Wantlist.label).distinct().all() if r[0]))
    )

@app.route('/wantlist/<int:item_id>')
@login_required
def wantlist_detail(item_id):
    item = Wantlist.query.get_or_404(item_id)
    return render_template('wantlist_detail.html', item=item)

# ==================== EXPORT ====================

@app.route('/export/<export_type>')
@login_required
def export_collection(export_type):
    """Export filtered collection results as CSV or PDF."""
    filters = get_request_filters()
    source = request.args.get('source', 'collection')
    
    if source == 'wantlist':
        q = Wantlist.query
        q = apply_common_filters(q, **filters, model=Wantlist)
        items = q.order_by(Wantlist.title).all()
        
        if export_type == 'csv':
            rows = [[item.artist_name or '', item.title, item.year or '', item.format or '',
                     item.format_details or '', item.style or '', item.label or '', item.country or '',
                     item.rating or '', item.date_added.strftime('%Y-%m-%d') if item.date_added else ''] for item in items]
            return export_to_csv(
                ['Artist', 'Title', 'Year', 'Format', 'Format Details', 'Style', 'Label', 'Country', 'Rating', 'Date Added'],
                rows, 'music_wantlist_export.csv'
            )
        elif export_type == 'pdf':
            return export_to_pdf('export_pdf_wantlist.html', {'items': items, 'total': len(items)}, 'music_wantlist_export.pdf')
    else:
        q = Release.query.options(db.joinedload(Release.artist))
        q = apply_common_filters(q, **filters)
        releases = q.order_by(Release.title).all()
        
        if export_type == 'csv':
            rows = [[r.artist.name if r.artist else '', r.title, r.year or '', r.format or '',
                     r.format_details or '', r.style or '', r.label or '', r.catalog_number or '',
                     r.country or '', r.date_added.strftime('%Y-%m-%d') if r.date_added else ''] for r in releases]
            return export_to_csv(
                ['Artist', 'Title', 'Year', 'Format', 'Format Details', 'Style', 'Label', 'Catalog #', 'Country', 'Date Added'],
                rows, 'music_collection_export.csv'
            )
        elif export_type == 'pdf':
            return export_to_pdf('export_pdf.html', {'releases': releases, 'total': len(releases)}, 'music_collection_export.pdf')
    
    return jsonify({'error': 'Unknown export type'}), 400

@app.route('/admin/sync-tracks-status')
@login_required
@admin_required
def track_sync_status():
    log = UpdateLog.query.filter_by(sync_type='track').order_by(UpdateLog.id.desc()).first()
    total_releases = Release.query.count()
    releases_with_tracks = db.session.query(Release.id).join(Track).distinct().count()
    
    if not log:
        return jsonify({'status': 'never_run', 'total_releases': total_releases,
                        'releases_with_tracks': releases_with_tracks,
                        'releases_without_tracks': total_releases - releases_with_tracks,
                        'finished_at': None, 'error_message': None})
    
    return jsonify({
        'status': log.status, 'total_releases': total_releases,
        'releases_with_tracks': releases_with_tracks,
        'releases_without_tracks': total_releases - releases_with_tracks,
        'finished_at': (log.finished_at.isoformat() + 'Z') if log.finished_at else None,
        'error_message': log.error_message
    })

@app.route('/admin/sync-status-api')
@login_required
@admin_required
def sync_status():
    """Combined sync status - returns the most recent activity from either collection or track sync."""
    coll_log = UpdateLog.query.filter_by(sync_type='collection').order_by(UpdateLog.id.desc()).first()
    track_log = UpdateLog.query.filter_by(sync_type='track').order_by(UpdateLog.id.desc()).first()
    
    log = None
    if coll_log and track_log:
        log = coll_log if coll_log.started_at >= track_log.started_at else track_log
    elif coll_log:
        log = coll_log
    elif track_log:
        log = track_log
    
    if not log:
        return jsonify({'status': 'never_run'})
    
    # Check if there's an active sync running
    active_syncs = {}
    for sync_type, thread in _active_syncs.items():
        if thread.is_alive():
            active_syncs[sync_type] = True
    
    # Convert UTC times to ISO format with timezone indicator
    # This ensures JavaScript parses them correctly and converts to local time
    started_at = (log.started_at.isoformat() + 'Z') if log.started_at else None
    finished_at = (log.finished_at.isoformat() + 'Z') if log.finished_at else None
    
    return jsonify({
        'status': log.status, 'sync_type': log.sync_type,
        'started_at': started_at,
        'finished_at': finished_at,
        'releases_added': log.releases_added, 'releases_updated': log.releases_updated,
        'error_message': log.error_message, 'triggered_by': log.triggered_by,
        'verification_status': log.verification_status,
        'missing_fields': log.missing_fields,
        'active_syncs': active_syncs
    })

# ==================== SCHEDULER ====================

def _scheduled_sync():
    """Background sync job - runs collection sync then track sync."""
    with app.app_context():
        token = get_setting('discogs_token', '')
        username = get_setting('discogs_username', '')
        if token and username:
            try:
                # Reset cancel events
                _reset_cancel('collection')
                _reset_cancel('track')
                
                service = SyncService(token, username)
                service.sync_collection(triggered_by='cron', fetch_country=True)
                if _is_cancelled('collection'):
                    logger.info("Cron sync cancelled after collection sync")
                    return
                releases = Release.query.outerjoin(Track).filter(Track.id == None).all()
                if releases and not _is_cancelled('track'):
                    client = DiscogsClient(token, username)
                    _sync_tracks_for_releases(releases, client)
            except Exception as e:
                logger.error(f"Scheduled sync failed: {e}")

def _reschedule_sync():
    """Reschedule the sync job based on current settings."""
    try:
        interval = int(get_setting('update_interval_hours', '24') or '24')
        if 'sync_job' in scheduler._jobstore:
            scheduler.remove_job('sync_job')
        scheduler.add_job(_scheduled_sync, 'interval', hours=interval, id='sync_job')
    except Exception as e:
        logger.error(f"Failed to reschedule: {e}")

def start_scheduler():
    """Start the scheduler."""
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
