"""db_content.py로 DB 모델링 발표 자료(pptx)를 만든다.

사용: python build_db_doc.py <erd.png> <out.pptx>
구성은 교수님 예시(DB모델링예시.pdf)를 따른다:
표지 → 목차 → 문서 버전 관리 → 저장 구조 → E-R 다이어그램 → 데이터 사전 → 관계 요약 → RDM → 제약 조건 → 기기 저장
"""
import sys

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

import db_content as C

FONT = "Malgun Gothic"
NAVY = RGBColor(0x1F, 0x3A, 0x5F)
INK = RGBColor(0x22, 0x26, 0x2E)
MUTED = RGBColor(0x5F, 0x67, 0x73)
LINE = RGBColor(0xD5, 0xDB, 0xE3)
TINT = RGBColor(0xF3, 0xF5, 0xF8)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SW, SH = Inches(13.333), Inches(7.5)
MX = Inches(0.6)                      # 좌우 여백


def rgb(hexstr):
    return RGBColor.from_string(hexstr)


def text(slide, x, y, w, h, runs, size=14, color=INK, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, name=None):
    """runs: 문자열 또는 [문단, ...], 문단은 문자열 또는 [(글자, {옵션}), ...]"""
    tb = slide.shapes.add_textbox(x, y, w, h)
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    tf.vertical_anchor = anchor
    paras = runs if isinstance(runs, list) else [runs]
    for i, p in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        for t, opt in (p if isinstance(p, list) else [(p, {})]):
            r = para.add_run()
            r.text = t
            f = r.font
            f.name = FONT
            f.size = Pt(opt.get("size", size))
            f.bold = opt.get("bold", bold)
            f.color.rgb = opt.get("color", color)
    return tb


def box(slide, x, y, w, h, fill, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06, name=None):
    s = slide.shapes.add_shape(shape, x, y, w, h)
    if name:
        s.name = name
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(1)
    s.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    return s


def badge(slide, x, y, d, label, fill, size=14):
    s = box(slide, x, y, d, d, fill, shape=MSO_SHAPE.OVAL)
    tf = s.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    r.font.name, r.font.size, r.font.bold, r.font.color.rgb = FONT, Pt(size), True, WHITE
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    return s


def table(slide, x, y, w, header, rows, widths, size=12, row_h=0.3, head_fill=NAVY, center_cols=()):
    tot = sum(widths)
    shp = slide.shapes.add_table(len(rows) + 1, len(header), x, y, w, Inches(row_h * (len(rows) + 1)))
    tbl = shp.table
    tbl.first_row = True
    for j, wd in enumerate(widths):
        tbl.columns[j].width = Emu(int(w * wd / tot))
    for i in range(len(rows) + 1):
        tbl.rows[i].height = Inches(row_h)
    for i, row in enumerate([header] + rows):
        for j, val in enumerate(row):
            c = tbl.cell(i, j)
            c.margin_left = c.margin_right = Inches(0.07)
            c.margin_top = c.margin_bottom = Inches(0.02)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.fill.solid()
            c.fill.fore_color.rgb = head_fill if i == 0 else (WHITE if i % 2 else TINT)
            tf = c.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER if (i == 0 or j in center_cols) else PP_ALIGN.LEFT
            r = p.add_run()
            r.text = str(val)
            r.font.name = FONT
            r.font.size = Pt(size)
            r.font.bold = i == 0
            r.font.color.rgb = WHITE if i == 0 else INK
    return shp


def title(slide, t, sub=None, no=None):
    text(slide, MX, Inches(0.4), Inches(10.5), Inches(0.7), t, size=30, bold=True, color=NAVY, name="Title")
    if sub:
        text(slide, MX, Inches(1.05), Inches(12), Inches(0.4), sub, size=14, color=MUTED, name="Subtitle")
    if no is not None:
        text(slide, SW - Inches(1.3), SH - Inches(0.5), Inches(0.9), Inches(0.3), str(no), size=11,
             color=MUTED, align=PP_ALIGN.RIGHT, name="PageNo")


def new(prs, dark=False):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg = s.background.fill
    bg.solid()
    bg.fore_color.rgb = NAVY if dark else WHITE
    return s


T = {t["name"]: t for t in C.TABLES}


def cover(prs):
    s = new(prs, dark=True)
    text(s, MX, Inches(1.2), Inches(8), Inches(0.5), "물어봐 캠퍼스 (Ask Campus)", size=20, color=rgb("CADCFC"))
    text(s, MX, Inches(1.8), Inches(11), Inches(1.3), "DB 모델링", size=60, bold=True, color=WHITE, name="Title")
    text(s, MX, Inches(3.2), Inches(11), Inches(0.5), "RAG·sLLM 캠퍼스 질의응답 앱의 서버 데이터베이스 설계",
         size=20, color=WHITE)
    # 그룹 색 점으로 테이블 묶음 미리 보기 (E-R 다이어그램과 같은 색)
    x = MX
    for g, (lab, col) in C.GROUPS.items():
        n = sum(1 for t in C.TABLES if t["group"] == g)
        box(s, x, Inches(4.3), Inches(0.22), Inches(0.22), rgb(col), line=WHITE, shape=MSO_SHAPE.OVAL)
        text(s, x + Inches(0.3), Inches(4.22), Inches(2.4), Inches(0.4), f"{lab} {n}개", size=14, color=WHITE)
        x += Inches(2.6)
    text(s, MX, Inches(5.6), Inches(9), Inches(1.0),
         [C.TEAM, f"작성일 {C.DATE} · 기준 문서 {C.BASIS}"], size=14, color=rgb("CADCFC"))


def toc(prs, no):
    s = new(prs)
    title(s, "목차", no=no)
    items = [("01", "문서 관리", "문서 버전 관리, 기준 문서"), ("02", "저장 구조", "관계형 DB · 벡터 DB · 기기 저장"),
             ("03", "E-R 다이어그램", "릴레이션, 데이터 사전, 관계 요약"), ("04", "RDM과 제약 조건", "테이블 13개 상세, 삭제·중복 규칙")]
    for i, (n, h, d) in enumerate(items):
        x = MX + (i % 2) * Inches(6.15)
        y = Inches(1.6) + (i // 2) * Inches(2.6)
        box(s, x, y, Inches(5.9), Inches(2.2), TINT)
        badge(s, x + Inches(0.35), y + Inches(0.4), Inches(0.8), n, NAVY, size=18)
        text(s, x + Inches(1.4), y + Inches(0.4), Inches(4.3), Inches(0.6), h, size=24, bold=True, color=NAVY)
        text(s, x + Inches(1.4), y + Inches(1.05), Inches(4.3), Inches(0.8), d, size=16, color=MUTED)


def versions(prs, no):
    s = new(prs)
    title(s, "문서 버전 관리", "DB 모델링은 요구사항 정의서·화면설계서와 같은 요구사항 ID(FR·PER·AVL)로 추적합니다", no)
    table(s, MX, Inches(1.7), Inches(12.1), ["버전", "작성일", "내용", "작성자"], C.HISTORY, [1, 1.4, 8, 1.2],
          size=14, row_h=0.5, center_cols=(0, 1, 3))
    facts = [("기준 문서", C.BASIS.split(" · ")), ("대상 DBMS", ["SQLite (개발·시연)", "필요하면 PostgreSQL로 옮김"]),
             ("테이블", [f"서버 {len(C.TABLES)}개 · 관계 {len(C.RELATIONS)}개", f"기기 저장 {len(C.DEVICE)}개"])]
    for i, (h, d) in enumerate(facts):
        x = MX + i * Inches(4.1)
        box(s, x, Inches(3.4), Inches(3.85), Inches(1.6), TINT)
        text(s, x + Inches(0.3), Inches(3.6), Inches(3.3), Inches(0.4), h, size=14, bold=True, color=MUTED)
        text(s, x + Inches(0.3), Inches(4.05), Inches(3.3), Inches(0.9), d, size=16, bold=True, color=NAVY)
    text(s, MX, Inches(5.5), Inches(12), Inches(0.9),
         "관계형 DB는 이 문서를 만들면서 SQLite로 정했고, 요구사항 정의서 v1.11의 2.7 기술 표에도 같은 내용을 추가했습니다.",
         size=14, color=MUTED)


def stores(prs, no):
    s = new(prs)
    title(s, "저장 구조", "데이터를 성격에 따라 세 곳에 나눠 저장합니다", no)
    cols = ["1F3A5F", "2A6F97", "6C757D"]
    for i, (h, tech, items, why) in enumerate(C.STORES):
        x = MX + i * Inches(4.1)
        y = Inches(1.7)
        box(s, x, y, Inches(3.85), Inches(4.3), TINT)
        badge(s, x + Inches(0.3), y + Inches(0.3), Inches(0.6), str(i + 1), rgb(cols[i]), size=16)
        text(s, x + Inches(1.05), y + Inches(0.28), Inches(2.7), Inches(0.5), h, size=22, bold=True, color=NAVY)
        text(s, x + Inches(1.05), y + Inches(0.78), Inches(2.7), Inches(0.4), tech, size=12, color=MUTED)
        text(s, x + Inches(0.3), y + Inches(1.45), Inches(3.3), Inches(2.3),
             [[("· " + it, {})] for it in items], size=14)
        text(s, x + Inches(0.3), y + Inches(3.1), Inches(3.3), Inches(1.0), why, size=13, color=MUTED)


def erd(prs, img, no):
    s = new(prs)
    title(s, "E-R 다이어그램", "테이블마다 PK·FK와 주요 속성만 표시 (전체 속성은 RDM)", no)
    im = Image.open(img)
    maxw, maxh = Inches(12.1), Inches(5.6)
    scale = min(maxw / im.width, maxh / im.height)
    w, h = int(im.width * scale), int(im.height * scale)
    s.shapes.add_picture(img, int((SW - w) / 2), Inches(1.6), w, h)


def dictionary(prs, part, names, no):
    s = new(prs)
    title(s, f"데이터 사전 ({part}/2)", "개체마다 주요 속성과 관련 요구사항", no)
    rows = []
    for n in names:
        t = T[n]
        keys = ", ".join(f[0] + (" (PK)" if f[2] else " (FK)" if f[3] else "") for f in t["fields"][:5])
        rows.append([f'{t["kor"]}\n{n}', keys, t["desc"], t["fr"]])
    table(s, MX, Inches(1.6), Inches(12.1), ["개체", "주요 속성", "설명", "관련 요구사항"], rows,
          [2.0, 4.1, 4.4, 1.6], size=12, row_h=0.72, center_cols=(0,))


def relations(prs, no):
    s = new(prs)
    title(s, "관계 요약", "1 : N 관계 13개와 1 : 0..1 관계 1개 (자기 참조 2개 포함)", no)
    rows = [[r[0], f"{T[r[1]]['kor']} – {T[r[2]]['kor']}", r[3], r[4]] for r in C.RELATIONS]
    table(s, MX, Inches(1.55), Inches(12.1), ["관계명", "관련 개체", "유형", "설명"], rows, [2.2, 3.8, 1.2, 4.9],
          size=12, row_h=0.36, center_cols=(2,))


def rdm(prs, names, no):
    s = new(prs)
    labs = list(dict.fromkeys(C.GROUPS[T[n]["group"]][0] for n in names))
    title(s, "RDM", " · ".join(labs) + " 영역", no)
    y = Inches(1.55)
    for n in names:
        t = T[n]
        col = C.GROUPS[t["group"]][1]
        badge(s, MX, y + Inches(0.03), Inches(0.28), "", rgb(col))
        text(s, MX + Inches(0.38), y - Inches(0.02), Inches(11.6), Inches(0.4),
             [[(f'{t["kor"]}  {n}', {"bold": True, "color": NAVY, "size": 15}),
               (f'   {t["desc"]}  ({t["fr"]})', {"color": MUTED, "size": 11})]])
        rows = [[f[0], f[1], "O" if f[2] else "", f[3].split(".")[0] if f[3] else "",
                 "NULL" if f[4] else "NOT NULL", f[5]] for f in t["fields"]]
        rh = 0.3
        table(s, MX, y + Inches(0.42), Inches(12.1), ["필드명", "데이터 타입", "PK", "FK", "Null 여부", "설명"], rows,
              [2.0, 1.6, 0.55, 2.0, 1.15, 5.3], size=12, row_h=rh, head_fill=rgb(col), center_cols=(2, 3, 4))
        y += Inches(0.42 + rh * (len(rows) + 1) + 0.35)


def constraints(prs, no):
    s = new(prs)
    title(s, "제약 조건과 삭제 규칙", "매핑 카디널리티를 지키기 위한 조건", no)
    table(s, MX, Inches(1.55), Inches(12.1), ["조건", "규칙", "요구사항"], [list(c) for c in C.CONSTRAINTS],
          [2.2, 8.4, 1.5], size=12, row_h=0.5, center_cols=(2,))


def device(prs, no):
    s = new(prs)
    title(s, "기기 저장 데이터와 벡터 DB", "서버 관계형 DB에 두지 않는 데이터", no)
    text(s, MX, Inches(1.55), Inches(12), Inches(0.4), "기기 저장 (Android, 서버로 보내지 않음)", size=16, bold=True, color=NAVY)
    table(s, MX, Inches(2.0), Inches(12.1), ["저장소", "항목", "설명", "요구사항"], [list(d) for d in C.DEVICE],
          [2.4, 4.3, 4.0, 1.4], size=12, row_h=0.45, center_cols=(3,))
    text(s, MX, Inches(4.2), Inches(12), Inches(0.4), "벡터 DB (Chroma 컬렉션)", size=16, bold=True, color=NAVY)
    table(s, MX, Inches(4.65), Inches(12.1), ["컬렉션", "id", "메타데이터", "관계형 DB와 연결"],
          [["campus_chunks", "chunk_id", "category, campus, posted_at, deadline, menu_path", "chunk.chunk_id와 같은 값"],
           ["faq", "faq-{faq_id}", "category, campus, created_at", "faq.faq_id (답변 등록·수정 시 바로 재색인)"]],
          [2.0, 1.8, 4.6, 3.7], size=12, row_h=0.45)


def main(erd_png, out):
    prs = Presentation()
    prs.slide_width, prs.slide_height = SW, SH
    cover(prs)
    no = 2
    for fn in (toc, versions, stores):
        fn(prs, no)
        no += 1
    erd(prs, erd_png, no)
    no += 1
    names = [t["name"] for t in C.TABLES]
    dictionary(prs, 1, names[:7], no)
    dictionary(prs, 2, names[7:], no + 1)
    no += 2
    relations(prs, no)
    no += 1
    for group in (["source"], ["document"], ["chunk"], ["collect_log", "digest_log"], ["manager"],
                  ["auth_code", "login_session"], ["pending_question"], ["notify_token", "synonym"], ["faq"], ["query_log"]):
        rdm(prs, group, no)
        no += 1
    constraints(prs, no)
    device(prs, no + 1)
    prs.save(out)
    print("saved", out, "slides", len(prs.slides))


if __name__ == "__main__":
    main(*sys.argv[1:3])
