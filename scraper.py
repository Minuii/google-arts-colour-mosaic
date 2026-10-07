"""
Google Arts & Culture colour scraper.

Builds one dataset per colour (images + metadata.csv) from
https://artsandculture.google.com/color and assigns each colour a numeric value.

Usage:
    python scraper.py --colors GREEN --limit 200        # quick test
    python scraper.py                                   # all 12 colours, everything
    python scraper.py --size 64 --no-images             # metadata only / tiny tiles
"""
import argparse, csv, json, os, random, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://artsandculture.google.com/api"
UA = {"User-Agent": "Mozilla/5.0"}

# Numeric value (label) assigned to each colour group. Edit freely.
COLOR_VALUES = {
    "WHITE": 0, "GRAY": 1, "PINK": 2, "PURPLE": 3, "BLUE": 4, "TEAL": 5,
    "GREEN": 6, "YELLOW": 7, "ORANGE": 8, "RED": 9, "BROWN": 10, "BLACK": 11,
}

FIELDS = ["filename", "asset_id", "title", "artist", "museum", "asset_path",
          "thumbnail_url", "dominant_hex", "dom_r", "dom_g", "dom_b",
          "aspect_ratio", "color_label", "color_hex", "color_r", "color_g",
          "color_b", "color_value"]


def get_json(url, retries=6):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
            return json.loads(raw[raw.find("["):])
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(30 * (attempt + 1))  # ponytail: flat long backoff; covers 429s


def rgb(hexstr):
    h = (hexstr or "").lstrip("#")
    if len(h) != 6:
        return ("", "", "")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def at(lst, i):
    return lst[i] if isinstance(lst, list) and len(lst) > i else None


def parse_item(it, label, chex):
    info = at(it, 10) or []
    asset_id = at(info, 0) or ""
    thumb = at(it, 3) or ""
    dom = at(it, 8) or ""
    cr, cg, cb = rgb(chex)
    dr, dg, db = rgb(dom)
    return {
        "filename": f"{asset_id}.jpg".replace("/", "_"),
        "asset_id": asset_id,
        "title": at(it, 1) or "",
        "artist": at(it, 2) or "",
        "museum": at(info, 12) or "",
        "asset_path": at(it, 4) or "",
        "thumbnail_url": ("https:" + thumb) if thumb.startswith("//") else thumb,
        "dominant_hex": dom, "dom_r": dr, "dom_g": dg, "dom_b": db,
        "aspect_ratio": at(info, 1) or "",
        "color_label": label, "color_hex": chex,
        "color_r": cr, "color_g": cg, "color_b": cb,
        "color_value": COLOR_VALUES.get(label, -1),
    }


def scrape_color(name, limit, delay):
    """Return (rows, total_available) for one colour, following pagination."""
    d = get_json(f"{API}/color?col={name}")
    entry = next(c for c in d[0][5] if c[1] == name)
    chex, pr = entry[0], entry[2]
    total = pr[4]
    rows, seen = [], set()

    def add(items):
        for it in items:
            r = parse_item(it, name, chex)
            if r["asset_id"] and r["asset_id"] not in seen and r["thumbnail_url"]:
                seen.add(r["asset_id"])
                rows.append(r)

    add(pr[2])
    token = pr[8]
    page = 0
    while token and (limit is None or len(rows) < limit):
        page += 1
        url = f"{API}/assets/images/color?s=30&pt={urllib.parse.quote(token)}&hl=en&_reqid={142882 + page * 100000}&rt=j"
        try:
            pr = get_json(url)[0][0]
        except Exception as e:
            print(f"  [{name}] page {page} failed: {e}; stopping")
            break
        before = len(rows)
        add(pr[2] or [])
        new_token = pr[8] if len(pr) > 8 else None
        if len(rows) == before or new_token == token:
            break  # no progress -> end
        token = new_token
        if page % 10 == 0:
            print(f"  [{name}] {len(rows)}/{total}")
        time.sleep(random.uniform(*delay))
    return (rows[:limit] if limit else rows), total


def download(args):
    url, path = args
    if os.path.exists(path):
        return True
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            data = urllib.request.urlopen(req, timeout=30).read()
            with open(path, "wb") as f:
                f.write(data)
            return True
        except Exception:
            time.sleep(1 + attempt)
    return False


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--colors", nargs="*", default=list(COLOR_VALUES),
                    help="e.g. GREEN RED (default: all 12)")
    ap.add_argument("--limit", type=int, default=None, help="max items per colour")
    ap.add_argument("--size", type=int, default=128, help="square thumbnail px")
    ap.add_argument("--out", default="datasets")
    ap.add_argument("--no-images", action="store_true")
    ap.add_argument("--threads", type=int, default=8)
    a = ap.parse_args()

    all_rows = []
    for name in [c.upper() for c in a.colors]:
        print(f"== {name} (value={COLOR_VALUES[name]})")
        cap = a.limit or (500 if name in ("BROWN", "BLACK") else 300)
        rows, total = scrape_color(name, cap, (0.3, 0.8))
        folder = os.path.join(a.out, name)
        os.makedirs(os.path.join(folder, "images"), exist_ok=True)
        for r in rows:
            r["thumbnail_url"] = r["thumbnail_url"].split("=")[0] + f"=w{a.size}-h{a.size}-c"
        if not a.no_images:
            jobs = [(r["thumbnail_url"], os.path.join(folder, "images", r["filename"])) for r in rows]
            with ThreadPoolExecutor(a.threads) as ex:
                ok = list(ex.map(download, jobs))
            rows = [r for r, good in zip(rows, ok) if good]
        write_csv(os.path.join(folder, "metadata.csv"), rows)
        print(f"   saved {len(rows)} of {total} available")
        time.sleep(random.uniform(5, 10))  # breather between colours (rate limit)
    merged = []
    for c in COLOR_VALUES:
        p = os.path.join(a.out, c, "metadata.csv")
        if os.path.exists(p):
            with open(p, newline="", encoding="utf-8") as f:
                merged += list(csv.DictReader(f))
    write_csv(os.path.join(a.out, "all_colors.csv"), merged)
    print(f"Done. {len(merged)} rows -> {a.out}/all_colors.csv")


if __name__ == "__main__":
    main()
