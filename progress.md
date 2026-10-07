# Progress Log — start to finish

Everything done in this project, in order, including dead ends and mistakes.

## 1. Request
Scrape `https://artsandculture.google.com/color?col=GREEN`, but give **each colour its own dataset** and **assign each a value**. Clarifying answers:
- Value = a mix of metadata and other fields, used to train an ML model and combine other pictures using these as small tiles.
- Download actual image files into per-colour folders, with CSV metadata.
- All 12 colours, then "as many as possible", later capped at 300 per colour and 500 for BROWN and BLACK.

## 2. Reconnaissance
1. Fetched the page. The HTML had a `window.INIT_data` JSON blob with **12 colours** (WHITE, GRAY, PINK, PURPLE, BLUE, TEAL, GREEN, YELLOW, ORANGE, RED, BROWN, BLACK), each holding ~45–48 artworks plus a total count and a continuation token.
2. Totals available: WHITE 2,196; GRAY 6,623; PINK 169; PURPLE 222; BLUE 2,741; TEAL 2,738; GREEN 2,547; YELLOW 1,987; ORANGE 1,627; RED 1,942; BROWN 23,012; BLACK 18,705.
3. Found `GET /api/color?col=NAME` returns the same JSON, so no HTML parsing is needed.
4. Item layout (positional JSON): `[1]` title, `[2]` artist, `[3]` thumbnail URL, `[4]` asset path, `[8]` dominant hex, `[10][0]` asset id, `[10][1]` aspect ratio, `[10][12]` museum.
5. Image URLs accept size suffixes, e.g. `=w128-h128-c` for a 128px centre-cropped square.

## 3. Dead ends (worth knowing)
- `p=<token>` on `/api/color` and `/api/search` does **not** paginate. Both return the same first page, and the "next" token never changes. Confirmed by overlap checks (42 of 45 titles identical).
- Guessed `/api/assets`, `/api/query`, batchexecute and `/api/category` paths: all 404 or 400.
- The `stella` JS bundle was 404 on the artsandculture host but loads from `www.gstatic.com`. Searching it showed the site uses a generic protobuf RPC, which was too hard to reverse by reading minified code.
- Web searches turned up ArtScraper (Selenium screenshot-based). I did not use it.
- Several shell one-liners failed from PowerShell quoting, so I switched to script files.

## 4. Finding the real pagination
- `pip install playwright` failed because the default Python is **32-bit 3.14** and its dependency `greenlet` needs MSVC. A pandas install was also started and cancelled (not needed).
- Workaround: `uv run --python 3.13 --with playwright python capture.py`, using installed **Edge** headless.
- Captured the page's traffic while scrolling. The infinite scroll calls:
  `GET /api/assets/images/color?s=30&pt=<token>&hl=en&_reqid=N&rt=j`
  The first POST body was gzip, which crashed my first capture. Decompressing it fixed that.
- Response format: `[[pr, ...]]`, with items in `pr[2]` and the next token in `pr[8]`. This is the endpoint the scraper uses.

## 5. Scraper (`scraper.py`, stdlib only)
- Follows the token chain, de-duplicates by asset id, and stops when a page adds nothing new.
- Downloads thumbnails with 8 threads and skips files already on disk, so it is resumable.
- Writes `datasets/<COLOR>/images/*.jpg`, `datasets/<COLOR>/metadata.csv` and a merged `all_colors.csv`.
- **Colour values** (my choice, following the site's listing order): WHITE 0, GRAY 1, PINK 2, PURPLE 3, BLUE 4, TEAL 5, GREEN 6, YELLOW 7, ORANGE 8, RED 9, BROWN 10, BLACK 11.
- CSV columns: `filename, asset_id, title, artist, museum, asset_path, thumbnail_url, dominant_hex, dom_r, dom_g, dom_b, aspect_ratio, color_label, color_hex, color_r, color_g, color_b, color_value`.
- Test: GREEN with 200 items gave 200 images and 200 correct rows.

## 6. The full run and what went wrong
1. First launched an **uncapped** run for all 12 colours.
2. You then asked for caps (300 per colour, 500 for BROWN and BLACK). I cancelled the first run in the task manager. **The Python process survived in the background and kept scraping.**
3. I cleared `datasets/` and ran the capped scraper, so two scrapers were hitting the site at once.
4. The capped run saved 10 colours (WHITE, GRAY, PINK, PURPLE, BLUE, TEAL, GREEN, YELLOW, ORANGE, RED), then Google returned **HTTP 429** and its `google.com/sorry` captcha page at BROWN.
5. I added a 30s-or-longer backoff, a 5–10s pause between colours, and made `all_colors.csv` merge the per-colour files on disk. Retries over about 7 minutes did not clear the block.
6. Later checks showed GRAY had 6,623 rows and BLUE 1,215, because the leftover uncapped process had overwritten the capped output. No Python process was running at that point. I trimmed both back to 300, deleted stray images, and asserted that every CSV row has an image (`summarize.py`).
7. I did not try to get past the captcha. I re-tested with a single request later and the block was still active.

## 7. CSV validation (`validate.py`)
Checked for every row of every colour CSV and the merged file:
- header matches the expected columns
- filename equals `<asset_id>.jpg` and the image exists, opens and is 128×128
- `color_label` and `color_value` match the mapping, and `color_hex` plus `color_r/g/b` match the colour's hex
- `dom_r/g/b` match `dominant_hex`
- thumbnail URL ends with `=w128-h128-c`
- no duplicate asset ids within a colour or across colours (0 found)
- no mojibake and no stray whitespace or newlines in text fields
- no extra image files that lack a CSV row

Found one issue: **438 rows had a blank artist** (the API gives none for many institutions, e.g. Musée d'Orsay). `--fix` set them to "Unknown". Re-run: **no problems**. Current data: 2,791 rows, all matching an image file.

## 8. Mosaic generator
- `build_mosaic.py` shrinks every tile to 48×48, computes its true mean RGB, packs all tiles into **one JPEG atlas**, and writes it with the colour table to `mosaic/atlas.js` (about 2.9 MB). Embedding it as base64 means the page works from `file://` and the canvas can still be exported (a plain image from disk would taint it).
- `mosaic/index.html` is a single page with no dependencies:
  1. Choose any image. It is downscaled to one pixel per tile cell.
  2. Each cell is matched to the closest tile by weighted RGB distance, plus a penalty for reusing the same tile (the **Variety** slider).
  3. Tiles are drawn onto a canvas, with an optional **Original blend** overlay for likeness.
  4. **Tiles across** sets the grid size. **Download PNG** saves the result.
- Test (headless Edge): uploaded a generated gradient-and-circle image. Result: 80×60 tiles, 1,162 distinct artworks used, a 3840×2880 PNG, no console errors, export works. `mosaic/sample_output.png` is a screenshot of that test.

## 9. Documentation
- `plan.md` is the forward-looking plan (the reference-site mention was removed as requested).
- This file (`progress.md`) is the full history.

## 10. State right now
| Item | State |
|---|---|
| 10 of 12 colour datasets | done, validated, 2,791 images |
| BROWN and BLACK (500 each) | **not done**: Google block still active at last check |
| Mosaic page | working with the 2,791 tiles now |

**To finish:** wait a few hours or switch network, then `python scraper.py --colors BROWN BLACK`, `python validate.py --fix`, `python build_mosaic.py`. Nothing else needs changing.

## 11. Files
`scraper.py`, `validate.py`, `build_mosaic.py`, `summarize.py` (offline cap enforcement), `capture.py` (network discovery), `test_mosaic.py` (page test), `plan.md`, `progress.md`, `mosaic/index.html`, `mosaic/atlas.js`, `mosaic/sample_output.png`, `datasets/`.

## 12. Viewer interactions (added after first version)
- Scroll wheel zooms toward the cursor, drag pans, double-click resets (tested headless: scale 0.24 -> 0.60, reset restores fit).
- Hover magnifier: a 220px round lens follows the cursor and shows the mosaic at (slider x current zoom). Slider 0 = off, default 6x. Hidden while dragging or when the mouse leaves. Tested headless (lens has real artwork pixels, hides correctly). Screenshot: `mosaic/sample_magnifier.png`.
