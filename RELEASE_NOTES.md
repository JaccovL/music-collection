# Release v1.3.4

## What's New

### Code Cleanup & Optimization
- **Extracted reusable helpers** — `get_request_filters()`, `apply_common_filters()`, `export_to_csv()`, `export_to_pdf()`
- **Removed duplicate logic** — Filter and export code no longer duplicated between Collection and Wantlist
- **Consolidated settings** — POST handling uses a loop instead of repetitive `set_setting()` calls
- **Removed unused imports** — `os`, `HealthStatus` no longer imported
- **Code reduction** — app.py from 1,141 → 900 lines (-21%)

### Files Modified
- `app.py` — Major cleanup and optimization

---

**Full Changelog**: https://github.com/JaccovL/music-collection/compare/v1.3.3...v1.3.4
