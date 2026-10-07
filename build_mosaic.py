"""Pack dataset tiles into embedded JPEG atlas + average RGB -> mosaic/atlas.js.
Supports either datasets/ (Google) or datasets_pd/ (AIC CC0 Public Domain).
Usage:
    python build_mosaic.py               # default: datasets_pd (safe for public sites)
    python build_mosaic.py --source datasets  # legacy Google Arts dataset
"""
import argparse, base64, csv, io, json, os
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("--source", default="datasets_pd", help="datasets_pd (default, CC0) or datasets")
ap.add_argument("--tile-size", type=int, default=40, help="pixel size of each tile in atlas")
ap.add_argument("--cols", type=int, default=70, help="columns in atlas sprite sheet")
args = ap.parse_args()

T, COLS = args.tile_size, args.cols
csv_path = os.path.join(args.source, "all_colors.csv")
rows = list(csv.DictReader(open(csv_path, newline="", encoding="utf-8")))
rows = [r for r in rows if os.path.exists(os.path.join(args.source, r["color_label"], "images", r["filename"]))]

atlas = Image.new("RGB", (COLS * T, -(-len(rows) // COLS) * T))
tiles = []
for i, r in enumerate(rows):
    img_path = os.path.join(args.source, r["color_label"], "images", r["filename"])
    im = Image.open(img_path).convert("RGB").resize((T, T), Image.LANCZOS)
    atlas.paste(im, ((i % COLS) * T, (i // COLS) * T))
    tiles.append([*im.resize((1, 1), Image.BOX).getpixel((0, 0)), r["color_label"]])

buf = io.BytesIO()
atlas.save(buf, "JPEG", quality=80)
os.makedirs("mosaic", exist_ok=True)
with open("mosaic/atlas.js", "w") as f:
    f.write(f"const T={T},COLS={COLS},TILES={json.dumps(tiles, separators=(',', ':'))};\n"
            f"const ATLAS='data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}';\n")

print(f"Packed {len(tiles)} tiles from {args.source} into mosaic/atlas.js ({os.path.getsize('mosaic/atlas.js') // 1024} KB)")
