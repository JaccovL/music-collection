"""API blueprint — all API endpoints."""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Release, Artist, Track, Wantlist
from app_utils import (
    get_request_filters, apply_common_filters, get_filter_options,
    admin_required, now_amsterdam, export_to_csv, export_to_pdf
)

api_bp = Blueprint('api', __name__)


@api_bp.route('/api/search')
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


@api_bp.route('/api/release-tracks/<int:release_id>')
@login_required
def api_release_tracks(release_id):
    tracks = Track.query.filter_by(release_id=release_id).order_by(Track.position).all()
    return jsonify([{'position': t.position, 'title': t.title, 'duration': t.duration} for t in tracks])


@api_bp.route('/api/track-counts', methods=['GET', 'POST'])
@login_required
def api_track_counts():
    """Batch endpoint for track counts — returns counts for all releases at once."""
    from sqlalchemy import func
    counts = dict(db.session.query(Track.release_id, func.count(Track.id)).group_by(Track.release_id).all())
    return jsonify(counts)


@api_bp.route('/api/discogs-release/<int:discogs_id>')
@login_required
def api_discogs_release(discogs_id):
    """Fetch release details from Discogs API (for wantlist items)."""
    from app_utils import get_setting
    from discogs_client import DiscogsClient
    
    token = get_setting('discogs_token', '') or current_app.config.get('DISCOGS_TOKEN', '')
    username = get_setting('discogs_username', '') or current_app.config.get('DISCOGS_USERNAME', '')
    
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


@api_bp.route('/api/release-detail/<int:release_id>')
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


@api_bp.route('/api/random-release')
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


@api_bp.route('/api/health')
@login_required
def api_health():
    from app_utils import get_health_status
    return jsonify(get_health_status().to_dict())