# OneMap 3D Viewer — Handover

Status as of last commit on branch `claude/onemap-singapore-3d-eIqFW`.

## Goal

Recreate the viewer at https://www.onemap.gov.sg/3d/ — a CesiumJS-based
3D view of Singapore — using the same public OneMap data the existing
`onemap-slicer` CLI already consumes. Initial framing: southern
Singapore (Sentosa → CBD → Marina Bay).

## What's in place

Two files under `docs/viewer/`:

| File | Role |
|------|------|
| `index.html` | Single-page CesiumJS viewer. Loads tileset, basemap, click-to-inspect, search box, view shortcuts. |
| `serve.mjs`  | Zero-dependency Node dev server. Serves the static page **and** reverse-proxies `/omapi/*` + `/maps/*` to `www.onemap.gov.sg` with CORS headers added. |

Endpoints used (all public, all unauthenticated):

- `https://www.onemap.gov.sg/omapi/tilesets/sg_noterrain_tiles/tileset.json` — 3D Tiles root
- `https://www.onemap.gov.sg/maps/tiles/Default_HD/{z}/{x}/{y}.png` — basemap
- `https://www.onemap.gov.sg/omapi/ss/search?searchVal=…` — search

CesiumJS is loaded from jsdelivr CDN (no Ion token needed; uses
ellipsoid terrain, not Cesium World Terrain).

## How to run

```bash
cd docs/viewer
node serve.mjs            # listens on :8000, PORT=… to override
# open http://localhost:8000/
```

Watch the **status pill** in the bottom-right:

- `Loading 3D tileset…` → fetch in flight
- `Tileset ready`       → buildings rendering
- `Failed to load tileset (likely CORS — see notes)` → see Debugging below

## Why the proxy exists

OneMap's CDN does **not** send `Access-Control-Allow-Origin`. A page
served from `localhost:8000` can't fetch the tileset directly. `serve.mjs`
fronts OneMap from the same origin and injects CORS headers, so to the
browser everything is same-origin.

It also rewrites absolute `https://www.onemap.gov.sg/` URLs inside JSON
bodies (tileset.json can reference child tilesets by absolute URL), so
all recursive fetches stay on the proxy.

## Debugging checklist

If the tileset doesn't load on the user's machine:

1. **DevTools → Network.** Find the first failing request.
   - `502` from `localhost:8000/omapi/...` → proxy reached OneMap and got an error; check `serve.mjs` terminal output.
   - `CORS error` → request bypassed the proxy. Confirm `index.html` uses relative `/omapi/...`, `/maps/...` paths (not `https://www.onemap.gov.sg/...`).
   - `4xx` on a deep tile path → OneMap moved/restructured the dataset.
2. **Verify the upstream is alive** independently:
   ```bash
   curl -I https://www.onemap.gov.sg/omapi/tilesets/sg_noterrain_tiles/tileset.json
   ```
3. **Cesium console errors?** Check the browser console — Cesium logs
   per-tile failures.

## Known gaps / next steps

- **Verification:** This was developed in a sandboxed environment that
  blocks `onemap.gov.sg` outbound, so the live tileset path was never
  exercised end-to-end. First task on the local machine: confirm it
  actually loads, screenshot it.
- **Terrain:** Currently uses `EllipsoidTerrainProvider` (flat earth).
  OneMap's dataset is `sg_noterrain_tiles` for a reason — buildings have
  their bases baked in. Real terrain would need Cesium Ion or a custom
  provider.
- **Whole island:** Initial view frames south Singapore. Could add view
  shortcuts for Jurong, Changi, the heartland. Probably also a button
  for "max-zoom Singapore overview".
- **Building deep-link:** Click → info panel works, but no URL state.
  Worth wiring `?lat=…&lon=…&bldg=…` for shareable views.
- **Export integration:** Natural next feature is a "Download as .3mf"
  button on the info panel that shells out to the existing CLI
  (`onemap-slicer --building-index …`). Would need a small backend
  endpoint in `serve.mjs` to run the subprocess.
- **Search UX:** Only flies to the first hit. Could show a dropdown of
  matches.
- **Licensing:** OneMap data © SLA. See
  https://www.onemap.gov.sg/termsofuse — fine for personal/educational
  use, redistribution requires checking the terms.

## How this fits the existing repo

`onemap-slicer` (Python CLI) extracts buildings from the same OneMap
tileset and exports them as 3MF/STL for 3D printing. The pipeline is
documented in `CLAUDE.md` and `docs/onemap-3d-technical-spec.md`. The
viewer is the visual complement: browse first, then export. The two
share no code today — the viewer is a static page Cesium handles
entirely client-side — but a future export button would bridge them.

## Branch & commits

Branch: `claude/onemap-singapore-3d-eIqFW`

```
cb6ca0d  Add CORS proxy dev server for OneMap viewer
3c7a3c0  Add CesiumJS viewer for OneMap 3D tiles
```
