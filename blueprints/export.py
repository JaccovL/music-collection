"""Export blueprint — CSV, PDF export."""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Release, Artist, Wantlist
from app_utils import (
    get_request_filters, apply_common_filters, get_filter_options,
    admin_required, now_amsterdam, export_to_csv, export_to_pdf
)

export_bp = Blueprint('export', __name__)


@export_bp.route('/export/<export_type>')
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