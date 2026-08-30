# Release v1.5.3

## What's New

### Bug Fixes
- **Fixed Random Release button** — The button called `showDetail()` which only looked for releases in the current page's array. Since the random release is unlikely to be on the current page, nothing happened. Now `showDetail()` fetches from the API when the release isn't found locally.

### Files Modified
- `templates/search.html` — Fixed showDetail() to handle releases not on current page
- `README.md` — Version history
- `RELEASE_NOTES.md` — This file

---

**Full Changelog**: https://github.com/JaccovL/music-collection/compare/v1.5.2...v1.5.3
