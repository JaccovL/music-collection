# Release v1.3.1

## What's New

### Settings Page Improvements
- **More compact layout** — Reduced padding, margins, and font sizes throughout
- **Discogs fields side by side** — Username and Token now in a single row
- **Reorganized sections** — Sync Schedule and Features moved to top for quick access
- **Wantlist toggle** — Enabling/disabling Wantlist now:
  - Shows/hides the Wantlist link in the navbar
  - Shows/hides the Wantlist Sync section on the Sync Status page
  - Shows/hides the wantlist sync polling JavaScript

### Bug Fixes
- **Filter box widths** — All filter dropdowns now have explicit `width: 100px` so they're identical on both Collection and Wantlist pages (previously browser auto-sizing caused differences)
- **Year filter placeholders** — Now show "1900" and "2024" instead of "From" and "To" for clarity

### UI Improvements
- **Help → About** — Renamed the Help link in Settings dropdown to About

### Files Modified
- `templates/admin_settings.html` — Compact layout, reorganized sections
- `templates/admin_sync_status.html` — Wantlist sync section hidden when disabled
- `templates/base.html` — Wantlist nav link hidden when disabled, About link
- `static/css/style.css` — Compact settings styles, explicit filter widths
- `app.py` — `get_setting` registered as Jinja global

---

**Full Changelog**: https://github.com/JaccovL/music-collection/compare/v1.3.0...v1.3.1
