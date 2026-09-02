"""Admin blueprint — settings, sync, reset, db stats."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from extensions import db, scheduler
from models import Release, Artist, Track, UpdateLog, AppSettings
from app_utils import (
    get_setting, set_setting, admin_required, get_health_status,
    now_amsterdam, utc_to_amsterdam
)
from sync_service import SyncService, _sync_tracks_for_releases, _verify_sync, _fix_missing_fields
from discogs_client import DiscogsClient
from cancel_events import is_cancelled, reset_cancel, set_cancel
import threading
import json

admin_bp = Blueprint('admin', __name__)

# Sync lock to prevent concurrent syncs
_sync_lock = threading.Lock()

# Track running sync threads (thread-safe with lock)
_active_syncs = {}
_active_syncs_lock = threading.Lock()



@admin_bp.route('/admin/statistics-api/growth')
@login_required
@admin_required
def statistics_api_growth():
    """Return collection growth over time (releases added per month)."""
    from sqlalchemy import func
    
    data = db.session.query(
        func.date_format(Release.date_added, '%Y-%m').label('month'),
        func.count(Release.id).label('count')
    ).filter(Release.date_added.isnot(None)).group_by('month').order_by('month').all()
    
    result = [{'label': d[0], 'value': d[1]} for d in data if d[0]]
    return jsonify(result)


@admin_bp.route('/admin/statistics-api/artists-top')
@login_required
@admin_required
def statistics_api_artists_top():
    """Return most collected artists."""
    from models import Artist
    
    data = db.session.query(
        Artist.name,
        func.count(Release.id).label('count')
    ).join(Release).group_by(Artist.id, Artist.name).order_by(func.count(Release.id).desc()).limit(10).all()
    
    result = [{'label': d[0] or 'Unknown', 'value': d[1]} for d in data if d[0]]
    return jsonify(result)


@admin_bp.route('/admin/statistics-api/format-trend')
@login_required
@admin_required
def statistics_api_format_trend():
    """Return format distribution over time (by year)."""
    from sqlalchemy import func
    
    data = db.session.query(
        func.ifnull(Release.format, 'Unknown').label('format'),
        func.count(Release.id).label('count')
    ).group_by('format').order_by(func.count(Release.id).desc()).limit(8).all()
    
    result = [{'label': d[0] or 'Unknown', 'value': d[1]} for d in data]
    return jsonify(result)

def _run_in_background(fn, sync_type=None):
    """Run a function in a background thread with app context."""
    def wrapper(app_instance):
        with app_instance.app_context():
            try:
                fn(app_instance)
            except Exception as e:
                import logging
                logging.error(f"Background task {fn.__name__} failed: {e}")
            finally:
                if sync_type:
                    with _active_syncs_lock:
                        _active_syncs.pop(sync_type, None)
    
    thread = threading.Thread(target=wrapper, args=(current_app._get_current_object(),))
    if sync_type:
        with _active_syncs_lock:
            _active_syncs[sync_type] = thread
    thread.start()


@admin_bp.route('/admin/settings', methods=['GET', 'POST'])
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
        from health import _health_cache
        _health_cache.invalidate()
        flash('Settings saved', 'success')
        return redirect(url_for('admin.admin_settings'))
    
    keys = ['discogs_token', 'discogs_username', 'db_host', 'db_port', 'db_name', 'db_user', 'db_password',
            'ldap_enabled', 'ldap_host', 'ldap_port', 'ldap_use_ssl', 'ldap_base_dn', 'ldap_bind_dn',
            'ldap_bind_password', 'ldap_user_filter', 'ldap_group_dn',
            'ldap_admin_group_dn', 'update_interval_hours', 'local_fallback', 'wantlist_enabled']
    settings = {key: get_setting(key, '') for key in keys}
    
    return render_template('admin_settings.html', settings=settings)


def _reschedule_sync():
    """Reschedule the sync job based on current settings."""
    try:
        interval = int(get_setting('update_interval_hours', '24') or '24')
        jobs = scheduler.get_jobs()
        if any(j.id == 'sync_job' for j in jobs):
            scheduler.remove_job('sync_job')
        scheduler.add_job(_scheduled_sync, 'interval', hours=interval, id='sync_job')
    except Exception as e:
        import logging
        logging.error(f"Failed to reschedule: {e}")


def _scheduled_sync():
    """Background sync job - runs collection sync then track sync."""
    with current_app._get_current_object().app_context():
        token = get_setting('discogs_token', '')
        username = get_setting('discogs_username', '')
        if token and username:
            try:
                reset_cancel('collection')
                reset_cancel('track')
                
                service = SyncService(token, username)
                service.sync_collection(triggered_by='cron', fetch_country=True)
                if is_cancelled('collection'):
                    return
                releases = Release.query.outerjoin(Track).filter(Track.id == None).all()
                if releases and not is_cancelled('track'):
                    client = DiscogsClient(token, username)
                    _sync_tracks_for_releases(releases, client)
            except Exception as e:
                import logging
                logging.error(f"Scheduled sync failed: {e}")


@admin_bp.route('/admin/reset-collection', methods=['POST'])
@login_required
@admin_required
def reset_collection():
    """Drop all collection data (releases, artists, tracks, wantlist) and start fresh."""
    global _sync_lock
    
    if not _sync_lock.acquire(blocking=False):
        return jsonify({'error': 'A sync is already running. Wait for it to finish.'}), 409
    
    try:
        from sqlalchemy import text
        
        db.session.execute(text('SET FOREIGN_KEY_CHECKS=0'))
        db.session.execute(text('TRUNCATE TABLE tracks'))
        db.session.execute(text('TRUNCATE TABLE releases'))
        db.session.execute(text('TRUNCATE TABLE artists'))
        db.session.execute(text('TRUNCATE TABLE wantlist'))
        db.session.execute(text('TRUNCATE TABLE update_log'))
        db.session.execute(text('SET FOREIGN_KEY_CHECKS=1'))
        db.session.commit()
        
        from health import _health_cache
        _health_cache.invalidate()
        
        reset_cancel('collection')
        reset_cancel('track')
        reset_cancel('wantlist')
        
        return jsonify({'status': 'success', 'message': 'Collection cleared. You can now sync fresh from Discogs.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Reset failed: {e}'}), 500
    finally:
        _sync_lock.release()


@admin_bp.route('/admin/sync-all', methods=['POST'])
@login_required
@admin_required
def sync_all():
    """Run collection sync followed by track sync sequentially."""
    global _sync_lock
    
    if not _sync_lock.acquire(blocking=False):
        return jsonify({'error': 'A sync is already running. Wait for it to finish.'}), 409
    
    token = get_setting('discogs_token', '') or current_app.config.get('DISCOGS_TOKEN', '')
    username = get_setting('discogs_username', '') or current_app.config.get('DISCOGS_USERNAME', '')
    
    if not token or not username:
        _sync_lock.release()
        return jsonify({'error': 'Discogs credentials not configured'}), 400
    
    reset_cancel('collection')
    reset_cancel('track')
    
    def do_sync_all(app_instance):
        try:
            service = SyncService(token, username)
            service.sync_collection(triggered_by='manual', fetch_country=True)
            if is_cancelled('collection'):
                return
            releases = Release.query.outerjoin(Track).filter(Track.id == None).all()
            if releases and not is_cancelled('track'):
                client = DiscogsClient(token, username)
                _sync_tracks_for_releases(releases, client)
        except Exception as e:
            import logging
            logging.error(f"Sync all failed: {e}")
        finally:
            _sync_lock.release()
    
    _run_in_background(do_sync_all, sync_type='collection')
    return jsonify({'status': 'started', 'message': 'Collection sync started, track sync will follow automatically.'})


@admin_bp.route('/admin/sync', methods=['POST'])
@login_required
@admin_required
def trigger_sync():
    global _sync_lock
    
    if not _sync_lock.acquire(blocking=False):
        return jsonify({'error': 'A sync is already running. Wait for it to finish.'}), 409
    
    token = get_setting('discogs_token', '') or current_app.config.get('DISCOGS_TOKEN', '')
    username = get_setting('discogs_username', '') or current_app.config.get('DISCOGS_USERNAME', '')
    
    if not token or not username:
        _sync_lock.release()
        return jsonify({'error': 'Discogs credentials not configured'}), 400
    
    reset_cancel('collection')
    
    def do_sync(app_instance):
        try:
            service = SyncService(token, username)
            service.sync_collection(triggered_by='manual', fetch_country=True)
        except Exception as e:
            import logging
            logging.error(f"Collection sync failed: {e}")
        finally:
            _sync_lock.release()
    
    _run_in_background(do_sync, sync_type='collection')
    return jsonify({'status': 'started'})


@admin_bp.route('/admin/sync-tracks', methods=['POST'])
@login_required
@admin_required
def trigger_track_sync():
    global _sync_lock
    
    if not _sync_lock.acquire(blocking=False):
        return jsonify({'error': 'A sync is already running. Wait for it to finish.'}), 409
    
    log = UpdateLog(sync_type='track', status='running', triggered_by='manual')
    db.session.add(log)
    db.session.commit()
    
    reset_cancel('track')
    
    def do_track_sync(app_instance):
        try:
            token = get_setting('discogs_token', '') or app_instance.config.get('DISCOGS_TOKEN', '')
            username = get_setting('discogs_username', '') or app_instance.config.get('DISCOGS_USERNAME', '')
            if not token or not username:
                log_entry = UpdateLog.query.filter_by(sync_type='track', status='running').order_by(UpdateLog.id.desc()).first()
                if log_entry:
                    log_entry.status = 'error'
                    log_entry.error_message = 'Discogs credentials not configured'
                    log_entry.finished_at = now_amsterdam()
                    db.session.commit()
                return
            
            client = DiscogsClient(token, username)
            releases = Release.query.outerjoin(Track).filter(Track.id == None).all()
            log_entry = UpdateLog.query.filter_by(sync_type='track', status='running').order_by(UpdateLog.id.desc()).first()
            _sync_tracks_for_releases(releases, client, log_entry)
        except Exception as e:
            import logging
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


@admin_bp.route('/admin/sync-wantlist', methods=['POST'])
@login_required
@admin_required
def trigger_wantlist_sync():
    global _sync_lock
    
    if not _sync_lock.acquire(blocking=False):
        return jsonify({'error': 'A sync is already running. Wait for it to finish.'}), 409
    
    token = get_setting('discogs_token', '') or current_app.config.get('DISCOGS_TOKEN', '')
    username = get_setting('discogs_username', '') or current_app.config.get('DISCOGS_USERNAME', '')
    
    if not token or not username:
        _sync_lock.release()
        return jsonify({'error': 'Discogs credentials not configured'}), 400
    
    reset_cancel('wantlist')
    
    def do_wantlist_sync(app_instance):
        try:
            service = SyncService(token, username)
            service.sync_wantlist(triggered_by='manual')
        finally:
            _sync_lock.release()
    
    _run_in_background(do_wantlist_sync, sync_type='wantlist')
    return jsonify({'status': 'started'})


@admin_bp.route('/admin/cancel-sync', methods=['POST'])
@login_required
@admin_required
def cancel_sync():
    """Cancel a running sync."""
    data = request.get_json() or {}
    sync_type = data.get('sync_type', 'collection')
    
    with _active_syncs_lock:
        if sync_type not in _active_syncs:
            return jsonify({'error': f'No active {sync_type} sync to cancel'}), 404
    
    set_cancel(sync_type)
    
    log = UpdateLog.query.filter_by(sync_type=sync_type, status='running').order_by(UpdateLog.id.desc()).first()
    if log:
        log.status = 'error'
        log.error_message = 'Cancelled by user'
        log.finished_at = now_amsterdam()
        db.session.commit()
    
    return jsonify({'status': 'cancelled', 'message': f'{sync_type} sync cancelled'})


@admin_bp.route('/admin/sync-status')
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
    
    if sync_log and sync_log.verification_status == 'failed' and sync_log.missing_fields:
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


@admin_bp.route('/admin/db-stats')
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


@admin_bp.route('/admin/statistics')
@login_required
@admin_required
def admin_statistics():
    return render_template('admin_statistics.html')


@admin_bp.route('/admin/statistics-api/<chart_type>')
@login_required
@admin_required
def statistics_api(chart_type):
    """Return JSON data for statistics charts."""
    from sqlalchemy import func
    
    chart_queries = {
        'format': (Release.format, Release.format),
        'style': (Release.style, Release.style),
        'country': (Release.country, Release.country),
        'label': (Release.label, Release.label),
    }
    
    if chart_type in chart_queries:
        col, group_col = chart_queries[chart_type]
        data = db.session.query(col, func.count(Release.id)).group_by(group_col).order_by(func.count(Release.id).desc()).limit(15).all()
        result = [{'label': d[0] or 'Unknown', 'value': d[1]} for d in data if d[0]]
        
    elif chart_type == 'decade':
        data = db.session.query(
            func.floor(Release.year / 10) * 10,
            func.count(Release.id)
        ).filter(Release.year > 0).group_by(func.floor(Release.year / 10) * 10).order_by(func.floor(Release.year / 10) * 10).all()
        result = [{'label': f"{int(d[0])}s", 'value': d[1]} for d in data if d[0]]
        
    elif chart_type == 'summary':
        total_releases = Release.query.count()
        total_artists = Artist.query.count()
        total_tracks = Track.query.count()
        
        year_range = db.session.query(
            func.min(Release.year), func.max(Release.year)
        ).filter(Release.year > 0).first()
        
        avg_tracks = func.count(Track.id).cast(db.Float) / func.count(db.distinct(Track.release_id))
        avg_result = db.session.query(avg_tracks).scalar()
        
        top_format = db.session.query(Release.format, func.count(Release.id)).group_by(Release.format).order_by(func.count(Release.id).desc()).first()
        
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


@admin_bp.route('/admin/health')
@login_required
@admin_required
def admin_health():
    return render_template('admin_health.html', status=get_health_status())


@admin_bp.route('/admin/verify-sync', methods=['POST'])
@login_required
@admin_required
def verify_sync():
    """Verify the latest sync and fix missing fields."""
    latest_log = UpdateLog.query.filter_by(sync_type='collection').order_by(UpdateLog.id.desc()).first()
    if not latest_log:
        return jsonify({'error': 'No sync log found'}), 404
    
    if latest_log.status == 'running':
        return jsonify({'status': 'running', 'message': 'Sync still running'}), 202
    
    missing = _verify_sync(latest_log)
    if missing:
        token = get_setting('discogs_token', '') or current_app.config.get('DISCOGS_TOKEN', '')
        username = get_setting('discogs_username', '') or current_app.config.get('DISCOGS_USERNAME', '')
        if not token or not username:
            return jsonify({'error': 'Discogs credentials not configured'}), 400
        
        _fix_missing_fields(missing, token, username, latest_log)
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


@admin_bp.route('/admin/sync-tracks-status')
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


@admin_bp.route('/admin/sync-wantlist-status')
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


@admin_bp.route('/admin/sync-status-api')
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
    
    active_syncs = {}
    for sync_type, thread in _active_syncs.items():
        if thread.is_alive():
            active_syncs[sync_type] = True
    
    def to_cest(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo('UTC'))
        return dt.astimezone(AMSTERDAM_TZ).strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({
        'status': log.status, 'sync_type': log.sync_type,
        'started_at': (log.started_at.isoformat() + 'Z') if log.started_at else None,
        'finished_at': (log.finished_at.isoformat() + 'Z') if log.finished_at else None,
        'started_at_cest': to_cest(log.started_at),
        'finished_at_cest': to_cest(log.finished_at),
        'releases_added': log.releases_added, 'releases_updated': log.releases_updated,
        'error_message': log.error_message, 'triggered_by': log.triggered_by,
        'verification_status': log.verification_status,
        'missing_fields': log.missing_fields,
        'active_syncs': active_syncs
    })