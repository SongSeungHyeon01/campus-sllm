"""완성본 PDF에서 목차 제목들이 실제로 시작하는 쪽을 찾아 JSON으로 저장한다.

사용: python find_pages.py <doc.pdf> <out.json>
목차 쪽(3쪽)은 건너뛰고, 줄 맨 앞이 제목으로 시작하는 첫 쪽을 찾는다.
"""
import json
import sys

import pymupdf

import content as C


def main(pdf, out):
    doc = pymupdf.open(pdf)
    pages = {}
    for title, _ in C.TOC:
        for i in range(3, len(doc)):
            for line in doc[i].get_text().splitlines():
                line = line.strip()
                nxt = line[len(title):len(title) + 1]
                if line.startswith(title) and (not nxt or nxt not in ".0123456789"):
                    pages[title] = i + 1
                    break
            if title in pages:
                break
    missing = [t for t, _ in C.TOC if t not in pages]
    json.dump(pages, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(pages, "| missing:", missing)
    if missing:
        sys.exit(1)


if __name__ == "__main__":
    main(*sys.argv[1:3])
