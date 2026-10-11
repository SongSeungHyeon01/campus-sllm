"""script_content.py로 발표 대본 Word 파일을 만든다.

사용: python make_script.py <출력 .docx 경로>
"""
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

import script_content as S

FONT = "맑은 고딕"
BLUE = RGBColor(0x2A, 0x63, 0xB8)
GRAY = RGBColor(0x5A, 0x69, 0x7B)


def set_font(run, size=None, bold=None, color=None):
    run.font.name = FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def para(doc, text, size=11, bold=False, color=None, align=None, space_after=6):
    p = doc.add_paragraph()
    set_font(p.add_run(text), size, bold, color)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.4
    if align:
        p.alignment = align
    return p


def main(out):
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

    para(doc, S.TITLE, 18, True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    para(doc, S.SUBTITLE, 10.5, color=GRAY, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)
    total = sum(s[3] for s in S.SLIDES)
    para(doc, f"{S.NOTE} (예상 합계 약 {total // 60}분 {total % 60}초)", 10, color=GRAY, space_after=14)

    # 한눈에 보는 순서표
    table = doc.add_table(rows=1, cols=4)
    table.style = "Light Grid Accent 1"
    for cell, text in zip(table.rows[0].cells, ["#", "슬라이드", "발표자", "시간"]):
        cell.text = ""
        set_font(cell.paragraphs[0].add_run(text), 10, True)
    for no, name, who, sec, _ in S.SLIDES:
        row = table.add_row().cells
        for cell, text in zip(row, [str(no), name, who, f"{sec}초"]):
            cell.text = ""
            set_font(cell.paragraphs[0].add_run(text), 10)

    doc.add_page_break()
    for no, name, who, sec, lines in S.SLIDES:
        p = doc.add_paragraph()
        set_font(p.add_run(f"{no:02d}  {name}"), 14, True)
        set_font(p.add_run(f"    {who} · 약 {sec}초"), 10, False, BLUE)
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        for line in lines:
            para(doc, line, 11.5)

    doc.add_page_break()
    para(doc, "예상 질문과 답변", 16, True, space_after=10)
    for i, (q, answers) in enumerate(S.QNA, 1):
        para(doc, f"Q{i}. {q}", 12, True, BLUE, space_after=3)
        for a in answers:
            para(doc, a, 11, space_after=10)

    doc.save(out)
    print("saved", out, "| slides", len(S.SLIDES), "| total", total, "sec | qna", len(S.QNA))


if __name__ == "__main__":
    main(sys.argv[1])
