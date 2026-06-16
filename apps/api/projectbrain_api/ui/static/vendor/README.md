# UI vendor assets

By default the ProjectBrain UI loads HTMX from jsDelivr at a pinned version.
To run fully offline, or to avoid CDN traffic for privacy reasons, drop a
local copy here:

```bash
curl -fSL https://cdn.jsdelivr.net/npm/htmx.org@1.9.12/dist/htmx.min.js \
     -o htmx.min.js
```

The router (`apps/api/projectbrain_api/ui/router.py`) auto-detects
`htmx.min.js` in this directory and prefers it over the CDN. If the file is
absent, the page falls back to the CDN URL pinned in `_HTMX_CDN_URL`.

When you upgrade the pinned version, update both `_HTMX_CDN_URL` in
`router.py` and the `curl` command above.
