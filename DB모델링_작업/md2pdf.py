"""md 문서 → 스타일 입힌 HTML → Edge headless PDF. 사용: python md2pdf.py <in.md> <out.pdf> [새 쪽에서 시작할 장 번호 정규식]"""
import re
import subprocess
import sys
from pathlib import Path

import markdown

src, out_pdf = Path(sys.argv[1]), Path(sys.argv[2])
NEWPAGE = sys.argv[3] if len(sys.argv) > 3 else "[12]"  # 새 쪽에서 시작할 장 번호 (정규식)
md = src.read_text(encoding="utf-8")

# 제목과 머리 정보는 표지 블록으로 따로 만든다
title = md.splitlines()[0].lstrip("# ").strip()
body_md = md.split("\n", 1)[1]
meta_md, rest_md = body_md.split("\n## ", 1)
rest_md = "## " + rest_md

def fix_lists(text):
    """python-markdown용: 목록 앞에 빈 줄을 넣고, 2칸 들여쓴 하위 목록을 4칸으로 바꾼다."""
    out = []
    for line in text.splitlines():
        is_item = bool(re.match(r"\s*([-*]|\d+\.) ", line))
        if is_item and out and out[-1].strip() and not re.match(r"\s*([-*]|\d+\.) ", out[-1]):
            out.append("")
        m = re.match(r"^( +)((?:[-*]|\d+\.) .*)", line)
        if m:
            line = " " * (len(m.group(1)) * 2) + m.group(2)
        out.append(line)
    return "\n".join(out)


meta_md, rest_md = fix_lists(meta_md), fix_lists(rest_md)
ext = ["tables", "sane_lists", "md_in_html", "fenced_code"]
meta_html = markdown.markdown(meta_md, extensions=ext)
html = markdown.markdown(rest_md, extensions=ext)

# 심각도 배지
for word, cls in [("높음", "hi"), ("중간", "mid"), ("낮음", "lo")]:
    html = html.replace(f"<td>{word}</td>", f'<td><span class="sev {cls}">{word}</span></td>')
# 오류 ID 배지
html = re.sub(r"<td>(E-\d\d)</td>", r'<td><span class="eid">\1</span></td>', html)
html = re.sub(r"<h3>(E-\d\d)\. ", r'<h3><span class="eid big">\1</span> ', html)
# 큰 장은 새 쪽에서 시작
html = re.sub(r"<h2>((?:%s)\. )" % NEWPAGE, r'<h2 class="newpage">\1', html)


def figure(m):
    """<img alt src> 문단을 캡션 있는 figure로 바꾸고, 그림 경로는 md 파일 기준 절대 경로로."""
    alt, rel = m.group(1), m.group(2)
    uri = (src.parent / rel).resolve().as_uri()
    return f'<figure><img src="{uri}" alt="{alt}"><figcaption>{alt}</figcaption></figure>'


html = re.sub(r'<p><img alt="([^"]*)" src="([^"]+)" ?/?></p>', figure, html)
html = html.replace("<hr />", "")

css = """
@page { size: A4; margin: 16mm 14mm 16mm 14mm; }
* { box-sizing: border-box; }
body { font-family: 'Malgun Gothic', sans-serif; font-size: 9.6pt; line-height: 1.55; color: #1d1d1f; margin: 0; }
.cover { border-bottom: 3px solid #1f3a5f; padding-bottom: 10px; margin-bottom: 14px; }
.cover .tag { display: inline-block; background: #1f3a5f; color: #fff; font-size: 8.5pt; padding: 2px 9px; border-radius: 3px; letter-spacing: .5px; }
.cover h1 { font-size: 19pt; margin: 8px 0 4px; color: #1f3a5f; line-height: 1.3; }
.meta { background: #f4f6f9; border: 1px solid #dde3ea; border-radius: 6px; padding: 8px 14px; font-size: 8.8pt; margin-bottom: 6px; }
.meta ul { margin: 0; padding-left: 16px; } .meta li { margin: 1px 0; }
h2 { font-size: 13.5pt; color: #1f3a5f; border-left: 5px solid #1f3a5f; padding: 2px 0 2px 9px; margin: 18px 0 8px; }
h2.newpage { page-break-before: always; margin-top: 0; }
h3 { font-size: 11pt; margin: 16px 0 6px; padding-bottom: 4px; border-bottom: 1px solid #d0d7e1; page-break-after: avoid; }
h3 + * { page-break-before: avoid; }
p { margin: 5px 0; }
ul { margin: 4px 0; padding-left: 18px; } li { margin: 2px 0; }
table { width: 100%; border-collapse: collapse; margin: 7px 0 10px; font-size: 8.6pt; line-height: 1.45; }
thead { display: table-header-group; }
tr { page-break-inside: avoid; }
th { background: #1f3a5f; color: #fff; font-weight: 600; text-align: left; padding: 5px 7px; border: 1px solid #1f3a5f; }
td { padding: 5px 7px; border: 1px solid #d5dbe3; vertical-align: top; }
tbody tr:nth-child(even) td { background: #f7f9fb; }
table table { margin: 4px 0; }
strong { color: #0f2744; }
figure { margin: 10px auto 14px; text-align: center; page-break-inside: avoid; }
figure img { max-width: 100%; max-height: 118mm; border: 1px solid #dde3ea; border-radius: 4px; }
figcaption { font-size: 8.4pt; color: #555; margin-top: 4px; }
.figrow { display: flex; gap: 12px; page-break-inside: avoid; }
.figrow figure { flex: 1; margin: 6px 0; }
.figrow figure img { max-height: 110mm; }
pre { background: #f4f6f9; border: 1px solid #dde3ea; border-radius: 5px; padding: 8px 10px; font-size: 8pt; line-height: 1.45; white-space: pre-wrap; word-break: break-all; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 8pt; }
code { font-family: Consolas, 'Malgun Gothic', monospace; font-size: 8.4pt; background: #eef1f5; padding: 0 4px; border-radius: 3px; }
.sev { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 8pt; font-weight: 700; white-space: nowrap; }
.sev.hi { background: #fde2e1; color: #b42318; } .sev.mid { background: #fff1d6; color: #9a6200; } .sev.lo { background: #e3f4e8; color: #22703a; }
.eid { display: inline-block; background: #e6ecf4; color: #1f3a5f; font-weight: 700; padding: 0 6px; border-radius: 3px; white-space: nowrap; font-size: 8.4pt; }
.eid.big { background: #1f3a5f; color: #fff; font-size: 9.5pt; padding: 1px 8px; margin-right: 4px; }
"""

doc = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{title}</title><style>{css}</style></head>
<body><div class="cover"><span class="tag">캡스톤디자인 1조 · 물어봐 캠퍼스</span><h1>{title}</h1></div>
<div class="meta">{meta_html}</div>{html}</body></html>"""

html_path = out_pdf.with_suffix(".html")
html_path.write_text(doc, encoding="utf-8")
edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
subprocess.run([edge, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={out_pdf}", html_path.resolve().as_uri()], check=True, timeout=120)
print("saved", out_pdf, out_pdf.stat().st_size)
