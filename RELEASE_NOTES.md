# Release v1.3.5

## What's New

### Removed Genre Column
- **Genre filter removed** — No longer filtering or displaying genre on Collection and Wantlist pages
- **Cleaner UI** — More space for other columns and better readability

### Format Column Filtering
- **Smart format display** — Combines `format` + `format_details`, shows only first 3 comma-separated values
- **Example:** `Vinyl, 12", 45 RPM, Maxi-Single, Stereo, Qty: 1` → `Vinyl, 12", 45 RPM…`
- **Applied everywhere** — Table view, card view, and detail modal on both Collection and Wantlist pages

### Backend Cleanup
- Removed genre references from filters, API responses, and template context
- Both Collection and Wantlist pages maintain identical column structure

### Files Modified
- `app.py` — Removed genre from filters, API responses, and template context
- `templates/search.html` — Removed genre column, added `shortFormat()` helper
- `templates/wantlist.html` — Removed genre column, added `shortFormat()` helper

---

**Full Changelog**: https://github.com/JaccovL/music-collection/compare/v1.3.4...v1.3.5
