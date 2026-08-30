# Statistics Dashboard Pattern

## Overview
A visual statistics dashboard with summary cards and interactive charts showing collection breakdowns by format, decade, country, and label. Uses Chart.js for rendering.

## Backend API Pattern

Create a single endpoint that accepts a `chart_type` parameter to return different aggregations:

```python
@app.route('/admin/statistics-api/<chart_type>')
@login_required
@admin_required
def statistics_api(chart_type):
    if chart_type == 'genre':
        data = db.session.query(
            Release.genre, db.func.count(Release.id)
        ).group_by(Release.genre).order_by(db.func.count(Release.id).desc()).limit(15).all()
        result = [{'label': d[0] or 'Unknown', 'value': d[1]} for d in data if d[0]]
        
    elif chart_type == 'decade':
        data = db.session.query(
            db.func.floor(Release.year / 10) * 10,
            db.func.count(Release.id)
        ).filter(Release.year.isnot(None)).group_by(db.func.floor(Release.year / 10) * 10).order_by(db.func.floor(Release.year / 10) * 10).all()
        result = [{'label': f"{int(d[0])}s", 'value': d[1]} for d in data if d[0]]
        
    elif chart_type == 'summary':
        total_releases = Release.query.count()
        total_artists = Artist.query.count()
        total_tracks = Track.query.count()
        
        year_range = db.session.query(
            db.func.min(Release.year), db.func.max(Release.year)
        ).filter(Release.year.isnot(None)).first()
        
        avg_tracks = db.func.count(Track.id).cast(db.Float) / db.func.count(db.distinct(Track.release_id))
        avg_result = db.session.query(avg_tracks).scalar()
        
        top_genre = db.session.query(Release.genre, db.func.count(Release.id)).group_by(Release.genre).order_by(db.func.count(Release.id).desc()).first()
        
        result = {
            'total_releases': total_releases,
            'total_artists': total_artists,
            'total_tracks': total_tracks,
            'year_min': int(year_range[0]) if year_range[0] else None,
            'year_max': int(year_range[1]) if year_range[1] else None,
            'avg_tracks_per_release': round(avg_result, 1) if avg_result else 0,
            'top_genre': top_genre[0] if top_genre else 'N/A',
        }
        
    return jsonify(result)
```

**Supported chart types:** `format`, `decade`, `country`, `label`, `summary`

## Frontend Template Structure

```html
<!-- Summary Cards -->
<div class="stats-summary">
    <div class="stat-card">
        <div class="stat-icon">💿</div>
        <div class="stat-info">
            <span class="stat-value" id="stat-releases">...</span>
            <span class="stat-label">Releases</span>
        </div>
    </div>
    <!-- More cards... -->
</div>

<!-- Charts Grid -->
<div class="charts-grid">
    <div class="chart-card chart-large">
        <h3>Releases by Genre</h3>
        <div class="chart-container">
            <canvas id="chart-genre"></canvas>
        </div>
    </div>
    <!-- More charts... -->
</div>
```

## Chart Types and Recommendations

| Data | Chart Type | Reason |
|------|-----------|--------|
| Genre | Doughnut | Proportional breakdown, top 10-15 |
| Format | Pie | Proportional breakdown, fewer categories |
| Decade | Bar | Time-series progression |
| Country | Horizontal Bar | Many labels, easier to read |
| Label | Horizontal Bar | Long label names |

## Chart.js Configuration

Load Chart.js from CDN:
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
```

Consistent color palette:
```javascript
const COLORS = [
    '#6200ee', '#03dac6', '#ff0266', '#ff6d00', '#ffab00',
    '#64dd17', '#00bfa5', '#2979ff', '#651fff', '#d500f9',
    '#ff1744', '#00e676', '#2962ff', '#aa00ff', '#00b8d4'
];
```

Dark mode defaults:
```javascript
Chart.defaults.color = '#b0b0b0';
Chart.defaults.borderColor = '#333';
```

## CSS Grid Layout

```css
.stats-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
}

.charts-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1.5rem;
}

.chart-full {
    grid-column: 1 / -1;
}

.chart-container {
    position: relative;
    height: 300px;
}
```

## Integration Checklist

- [ ] Add `/admin/statistics` route (page)
- [ ] Add `/admin/statistics-api/<chart_type>` route (JSON API)
- [ ] Create `templates/admin_statistics.html`
- [ ] Add Statistics CSS to stylesheet
- [ ] Add link in Settings dropdown menu
- [ ] Add feature to Features list in README
- [ ] Test with real data (aggregate queries work correctly)

## Common Pitfalls

- **Data labels too long** — Use horizontal bar charts for data with long labels (country, label)
- **Too many categories** — Limit to top 10-15, group rest as "Other"
- **Year range queries** — Always filter `Release.year.isnot(None)` to exclude NULL years
- **Decade calculation** — Use `db.func.floor(year / 10) * 10` for decade grouping
