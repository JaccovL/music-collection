"""Wantlist blueprint — wantlist page, detail."""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Wantlist
from app_utils import (
    get_request_filters, apply_common_filters, get_filter_options,
    admin_required, now_amsterdam
)

wantlist_bp = Blueprint('wantlist', __name__)


@wantlist_bp.route('/wantlist')
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


@wantlist_bp.route('/wantlist/<int:item_id>')
@login_required
def wantlist_detail(item_id):
    item = Wantlist.query.get_or_404(item_id)
    return render_template('wantlist_detail.html', item=item)