# Art Colour Dataset + Mosaic — Plan

(full history in [progress.md](progress.md))

## Goal
1. Build one dataset per colour from `artsandculture.google.com/color`, each colour with its own numeric value, for ML training.
2. Use the small artwork thumbnails as tiles for a photo-mosaic page for a portfolio site.

Caps: 300 per colour, 500 for BROWN and BLACK (all available if fewer).

## Pipeline
| Step | File | Status |
|---|---|---|
| Scrape (API + pagination, thumbnails, CSV) | `scraper.py` | done for 10 of 12 colours |
| Validate / normalise CSVs | `validate.py` | done, 0 problems |
| Pack tiles into one embedded atlas | `build_mosaic.py` | done (2,791 tiles) |
| Mosaic generator page | `mosaic/index.html` | done, tested in headless Edge |
| BROWN and BLACK (500 each) | `scraper.py --colors BROWN BLACK` | **pending**: Google 429 block |

## Colour values
WHITE 0, GRAY 1, PINK 2, PURPLE 3, BLUE 4, TEAL 5, GREEN 6, YELLOW 7, ORANGE 8, RED 9, BROWN 10, BLACK 11. Edit `COLOR_VALUES` in `scraper.py` to change.

## Result right now
| Colour | Value | Rows = images |
|---|---|---|
| WHITE | 0 | 300 |
| GRAY | 1 | 300 |
| PINK | 2 | 169 (all available) |
| PURPLE | 3 | 222 (all available) |
| BLUE | 4 | 300 |
| TEAL | 5 | 300 |
| GREEN | 6 | 300 |
| YELLOW | 7 | 300 |
| ORANGE | 8 | 300 |
| RED | 9 | 300 |
| BROWN | 10 | 0 pending |
| BLACK | 11 | 0 pending |
| **Total** | | **2,791** |

## Finishing the last two colours
Google temporarily blocked this IP (HTTP 429 and a captcha page). Wait a few hours or switch network, then run:
```
python scraper.py --colors BROWN BLACK
python validate.py --fix
python build_mosaic.py
```
Run one scraper at a time. The third command rebuilds the mosaic tiles so the dark colours are included.

## Using the mosaic
Open `mosaic/index.html` directly (double-click, no server needed). Choose any image. Sliders:
- **Tiles across**: more tiles means finer detail and a bigger PNG.
- **Variety**: higher means fewer repeats of the same artwork.
- **Original blend**: overlays the original photo for sharper likeness.

Then press Download PNG.

## Known limits and notes
- Weak colours: PINK (169) and PURPLE (222) will repeat more. Dark areas are thin until BROWN and BLACK are added.
- Matching uses weighted RGB distance, not Lab, which is fine for this purpose.
- `atlas.js` is about 2.9 MB, which suits a portfolio page. Lower `T` in `build_mosaic.py` to shrink it.
- These are museum images, so check licensing before publishing them on a public site. Public-domain pieces are safest.
