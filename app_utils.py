"""Shared utilities for blueprints — avoids circular imports."""
from datetime import datetime
from zoneinfo import ZoneInfo
from functools import wraps
from flask import request, redirect, url_for, flash, current_user
from flask_login import login_required as flask_login_required
from extensions import db

AMSTERDAM_TZ = ZoneInfo('Europe/Amsterdam')


def now_amsterdam():
    """Get current time in UTC for storage."""
    return datetime.utcnow()


def utc_to_amsterdam(dt):
    """Convert UTC datetime to Amsterdam timezone for display."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo('UTC'))
    return dt.astimezone(AMSTERDAM_TZ)


def admin_required(f):
    """Decorator to require admin access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required', 'error')
            return redirect(url_for('collection.search'))
        return f(*args, **kwargs)
    return decorated_function


def get_setting(key, default=None):
    """Get a setting from the database."""
    from models import AppSettings
    s = AppSettings.query.filter_by(key=key).first()
    return s.value if s and s.value else default


def set_setting(key, value):
    """Set a setting in the database."""
    from models import AppSettings
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


# Filter cache
_filter_cache = {'ts': 0, 'data': {}}
FILTER_CACHE_TTL = 300


def get_filter_options():
    """Get filter options with caching."""
    from models import Release
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


def invalidate_filter_cache():
    """Invalidate the filter cache (call after sync completes)."""
    _filter_cache['ts'] = 0
    _filter_cache['data'] = {}


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


def apply_common_filters(q, search, format_filter, style_filter, label_filter, year_from, year_to, model=None):
    """Apply common filters to a query. Uses FULLTEXT search when available."""
    from models import Release, Artist, Track, Wantlist
    from sqlalchemy import text
    
    if model is None:
        model = Release
    
    if search:
        if model == Release:
            q = q.join(Artist, Artist.id == Release.artist_id)
            q = q.outerjoin(Track, Track.release_id == Release.id)
            
            # Try FULLTEXT search first, fall back to LIKE
            search_expr = search.strip()
            if len(search_expr) >= 2:
                # Use BOOLEAN MODE for partial word matching
                q = q.filter(text("""
                    MATCH(releases.title) AGAINST(:search IN BOOLEAN MODE)
                    OR MATCH(artists.name) AGAINST(:search IN BOOLEAN MODE)
                    OR MATCH(releases.label) AGAINST(:search IN BOOLEAN MODE)
                    OR MATCH(tracks.title) AGAINST(:search IN BOOLEAN MODE)
                    OR releases.title LIKE :like_search
                    OR artists.name LIKE :like_search
                    OR releases.label LIKE :like_search
                    OR tracks.title LIKE :like_search
                """).bindparams(search=f"{search_expr}*", like_search=f"%{search_expr}%"))
            else:
                search_filter = f"%{search}%"
                q = q.filter(db.or_(
                    Release.title.like(search_filter),
                    Artist.name.like(search_filter),
                    Release.label.like(search_filter),
                    Track.title.like(search_filter)
                ))
        else:
            search_filter = f"%{search}%"
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


def get_health_status():
    """Get consolidated health status for all pages."""
    from health import run_health_checks
    
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


def export_to_csv(headers, rows, filename):
    """Generate CSV response from headers and rows."""
    import io
    import csv
    from flask import Response
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename={filename}'})


def export_to_pdf(template, context, filename):
    """Generate PDF response from template."""
    from flask import render_template
    from weasyprint import HTML
    
    html = render_template(template, **context, now=now_amsterdam())
    pdf = HTML(string=html).write_pdf()
    return Response(pdf, mimetype='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename={filename}'})