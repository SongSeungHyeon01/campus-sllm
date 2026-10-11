import sys, pymupdf
d = pymupdf.open(sys.argv[1])
bad = []
for i, p in enumerate(d):
    H = p.rect.height
    rules = [dr["rect"] for dr in p.get_drawings() if dr["rect"].height < 2 and dr["rect"].width > 400 and dr["rect"].y0 > 0.85 * H]
    if not rules:
        continue
    fy = min(r.y0 for r in rules)
    body = [b for b in p.get_text("blocks") if b[4].strip() and b[3] > fy + 1 and not b[4].strip().endswith(f"/{len(d)}")]
    if body:
        bad.append((i + 1, body[0][4][:30].replace("\n", " ")))
print("pages", len(d), "overflow", bad)
