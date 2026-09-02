"""Collection blueprint — search, release detail, artist detail."""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Release, Artist, Track
from app_utils import (
    get_request_filters, apply_common_filters, get_filter_options,
    admin_required, now_amsterdam
)

collection_bp = Blueprint('collection', __name__)


@collection_bp.route('/')
@login_required
def index():
    return redirect(url_for('collection.search'))


@collection_bp.route('/search')
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
        tracks_min=filters.get('tracks_min', ''),
        tracks_max=filters.get('tracks_max', ''),
        date_from=filters.get('date_from', ''),
        date_to=filters.get('date_to', ''),
        has_notes=filters.get('has_notes', ''),
        **get_filter_options()
    )


@collection_bp.route('/release/<int:release_id>')
@login_required
def release_detail(release_id):
    release = Release.query.get_or_404(release_id)
    tracks = Track.query.filter_by(release_id=release.id).order_by(Track.position).all()
    return render_template('release.html', release=release, tracks=tracks)


@collection_bp.route('/artist/<int:artist_id>')
@login_required
def artist_detail(artist_id):
    artist = Artist.query.get_or_404(artist_id)
    releases = Release.query.filter_by(artist_id=artist.id).order_by(Release.year).all()
    return render_template('artist.html', artist=artist, releases=releases)