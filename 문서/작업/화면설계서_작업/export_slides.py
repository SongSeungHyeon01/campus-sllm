import os, sys
import win32com.client as win32
src, out = map(os.path.abspath, sys.argv[1:3])
os.makedirs(out, exist_ok=True)
app = win32.Dispatch("PowerPoint.Application")
pres = app.Presentations.Open(src, True, False, False)
try:
    for i, s in enumerate(pres.Slides, 1):
        s.Export(os.path.join(out, f"s{i:02d}.png"), "PNG", 1333, 750)
    pres.SaveAs(os.path.join(out, "v12.pdf"), 32)
    print("exported", pres.Slides.Count)
finally:
    pres.Close()
