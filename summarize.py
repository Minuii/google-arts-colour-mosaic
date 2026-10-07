import csv, os, glob
from scraper import COLOR_VALUES, write_csv

CAP = lambda c: 500 if c in ("BROWN", "BLACK") else 300
merged, lines = [], []
for c, v in COLOR_VALUES.items():
    p = os.path.join("datasets", c, "metadata.csv")
    if not os.path.exists(p):
        lines.append(f"| {c} | {v} | 0 | pending |"); continue
    rows = list(csv.DictReader(open(p, newline="", encoding="utf-8")))
    rows = [r for r in rows if os.path.exists(os.path.join("datasets", c, "images", r["filename"]))][:CAP(c)]
    keep = {r["filename"] for r in rows}
    for f in glob.glob(os.path.join("datasets", c, "images", "*.jpg")):
        if os.path.basename(f) not in keep:
            os.remove(f)  # stray image from the uncapped run
    write_csv(p, rows)
    merged += rows
    n = len(glob.glob(os.path.join("datasets", c, "images", "*.jpg")))
    assert n == len(rows), (c, n, len(rows))
    lines.append(f"| {c} | {v} | {len(rows)} | done |")
write_csv("datasets/all_colors.csv", merged)
print("\n".join(lines)); print("TOTAL", len(merged))
