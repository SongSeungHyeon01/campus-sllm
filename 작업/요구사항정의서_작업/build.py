"""03_요구사항정의서 양식(HWPX로 변환본)에 content.py 내용을 채워 HWPX를 만든다.

사용: python build.py <template.hwpx> <out.hwpx>
그림 자리에는 '@@IMG:key@@' 문단을 남기고, insert_images.py(한글 COM)가 그림으로 바꾼다.
"""
import copy
import itertools
import json
import sys
import zipfile

from lxml import etree

import content as C

HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HP = "{%s}" % HP_NS

# 양식에서 확인한 스타일 번호
PP_BODY, PP_ITEM, PP_CENTER, PP_CELL_C, PP_CELL_L, PP_WRAP = "19", "26", "14", "14", "22", "20"
CP_BODY, CP_BOLD, CP_CELL_HEAD, CP_TITLE2, CP_COVER_BIG, CP_COVER = "30", "33", "23", "22", "19", "20"
BF_HEAD, BF_BODY = "3", "2"
TABLE_LEFT = 2130          # 본문 들여쓰기와 맞춤
TABLE_WIDTH = 52450 - 2130

_ids = itertools.count(1942270000)


def strip_layout(el):
    """linesegarray is Hancom's cached line layout; drop it so the editor re-flows text."""
    for seg in el.iter(HP + "linesegarray"):
        seg.getparent().remove(seg)


def para(text="", pp=PP_BODY, cp=CP_BODY, style="0", runs=None):
    p = etree.Element(HP + "p", {"id": "0", "paraPrIDRef": pp, "styleIDRef": style,
                                 "pageBreak": "0", "columnBreak": "0", "merged": "0"})
    for t, c in (runs or [(text, cp)]):
        r = etree.SubElement(p, HP + "run", {"charPrIDRef": c})
        etree.SubElement(r, HP + "t").text = t
    return p


def set_text(p, text):
    """Replace the visible text of a template paragraph, keeping its controls (bookmarks)."""
    ts = [t for t in p.iter(HP + "t")]
    target = next((t for t in ts if (t.text or "").strip()), ts[0] if ts else None)
    if target is None:
        run = p.find(HP + "run")
        target = etree.SubElement(run, HP + "t")
    target.text = text
    for t in ts:
        if t is not target:
            t.text = None
    return p


def page_break(p):
    p.set("pageBreak", "1")
    return p


def heading_without_ctrl(src, text):
    p = copy.deepcopy(src)
    for ctrl in list(p.iter(HP + "ctrl")):
        ctrl.getparent().remove(ctrl)
    p.set("id", "0")
    return set_text(p, text)


def make_table(tpl_tbl, headers, rows, widths, aligns):
    scale = TABLE_WIDTH / sum(widths)
    widths = [int(w * scale) for w in widths]
    widths[-1] = TABLE_WIDTH - sum(widths[:-1])

    tbl = copy.deepcopy(tpl_tbl)
    tpl_head_tc = copy.deepcopy(tbl.find(HP + "tr").find(HP + "tc"))
    for tr in tbl.findall(HP + "tr"):
        tbl.remove(tr)
    n_rows = len(rows) + 1
    tbl.set("id", str(next(_ids)))
    tbl.set("rowCnt", str(n_rows))
    tbl.set("colCnt", str(len(headers)))
    sz = tbl.find(HP + "sz")
    sz.set("width", str(TABLE_WIDTH))
    sz.set("height", str(1420 * n_rows))
    tbl.find(HP + "pos").set("treatAsChar", "1")  # inline: never floats above its heading

    def cell(r, c, text, head):
        tc = copy.deepcopy(tpl_head_tc)
        tc.set("borderFillIDRef", BF_HEAD if head else BF_BODY)
        tc.set("header", "1" if head else "0")  # header row repeats on the next page
        tc.set("hasMargin", "1")                # use cellMargin (510) so text clears the border
        sub = tc.find(HP + "subList")
        for p in sub.findall(HP + "p"):
            sub.remove(p)
        pp = PP_CELL_C if head or aligns[c] == "c" else PP_CELL_L
        sub.append(para(text, pp, CP_CELL_HEAD if head else CP_BODY))
        tc.find(HP + "cellAddr").attrib.update({"colAddr": str(c), "rowAddr": str(r)})
        tc.find(HP + "cellSz").attrib.update({"width": str(widths[c]), "height": "1420"})
        return tc

    for r, values in enumerate([headers] + rows):
        tr = etree.SubElement(tbl, HP + "tr")
        for c, text in enumerate(values):
            tr.append(cell(r, c, text, r == 0))

    wrap = para("", PP_BODY, "29")  # body indent (2130) = where the table starts
    run = wrap.find(HP + "run")
    run.remove(run.find(HP + "t"))
    run.append(tbl)
    etree.SubElement(run, HP + "t")
    return wrap


def toc_para(text, level, page):
    """One TOC line: title, a dotted right tab, the page number (template TOC styles)."""
    pp, style, cp = ("12", "18", "13") if level == 1 else ("24", "19", "14")
    p = etree.Element(HP + "p", {"id": "0", "paraPrIDRef": pp, "styleIDRef": style,
                                 "pageBreak": "0", "columnBreak": "0", "merged": "0"})
    t = etree.SubElement(etree.SubElement(p, HP + "run", {"charPrIDRef": cp}), HP + "t")
    t.text = ("      " if level == 3 else "") + text
    tab = etree.SubElement(t, HP + "tab", {"width": "40000", "leader": "3", "type": "2"})
    tab.tail = str(page) if page else ""
    return p


def render(blocks, ctx):
    out = []
    break_next = False
    for b in blocks:
        kind = b[0]
        if kind == "pagebreak":
            break_next = True
            continue
        if kind == "p":
            p = para(b[1])
        elif kind == "b":
            p = para(b[1], cp=CP_BOLD)
        elif kind == "li":
            p = para(b[1], pp=PP_ITEM)
        elif kind == "num":
            p = para(b[1], cp=CP_BOLD)
        elif kind == "blank":
            p = para("")
        elif kind == "img":
            p = para(f"@@IMG:{b[1]}:{b[2]}@@", pp=PP_CENTER)
        elif kind == "table":
            headers, rows, widths, aligns = b[1:5]
            size = b[5] if len(b) > 5 else len(rows)  # inline tables never split across pages: chunk long ones
            chunks = [make_table(ctx["tbl"], headers, rows[i:i + size], widths, aligns)
                      for i in range(0, len(rows), size)]
            out.extend(chunks[:-1])
            p = chunks[-1]
        elif kind == "h2":
            p = heading_without_ctrl(ctx["h2"], b[1])
        else:
            raise ValueError(kind)
        if break_next:
            p.set("pageBreak", "1")
            break_next = False
        out.append(p)
    return out


def requirement_blocks(ctx):
    out = []
    for rid, title, desc, note in C.FR:
        out.append(set_text(copy.deepcopy(ctx["req_title"]), f"  [{rid}] {title}"))
        out.append(para("1) 요구사항 설명"))
        out += [para(d, pp=PP_ITEM) for d in desc]
        out.append(para("2) 비고"))
        prio = getattr(C, "FR_PRIORITY", {}).get(rid)
        if prio and not note[0].startswith("우선순위"):
            note = [f"우선순위: {prio}. {note[0]}", *note[1:]]
        out += [para(n, pp=PP_ITEM) for n in note]
        out.append(para(""))
    return out


def screen_blocks(ctx):
    out = [heading_without_ctrl(ctx["h3"], "2.3.2 화면 요구사항"),
           para("앱은 다른 AI 챗봇처럼 대화형 중심으로 구성하여, 채팅 화면(SCR-001)과 이를 보조하는 설정(SCR-004)·마감 일정(SCR-005) "
                "3개 화면만 두고, 학과 조교·관리자용 답변·운영 관리 웹 페이지(SCR-006)를 더해 총 4개 화면을 정의합니다. 이전 버전의 "
                "카테고리 화면(SCR-002)과 답변 상세 화면(SCR-003)은 채팅 화면의 추천 질문 버튼과 ‘원문 보기’로 통합하여 삭제하였으며, "
                "다른 문서와의 추적성을 위해 번호는 다시 매기지 않습니다."),
           para("화면 그림은 기능 배치를 나타내는 와이어프레임이며, 세부 디자인과 상태별 화면(되묻기, 근거 없음 안내, 답변 알림, 첫 실행, "
                "로그인 등)은 화면설계서에서 정의합니다.")]
    for n, (sid, name, img, items) in enumerate(C.SCREENS):
        title = set_text(copy.deepcopy(ctx["req_title"]), f"[{sid}] {name}")
        title.set("pageBreak", "1")  # one screen per page (no blank line before it: it could spill into an empty page)
        out.append(title)
        out.append(para("1) 화면 그림"))
        out.append(para(f"@@IMG:{img}:{165 if img == 'scr006' else 90 if img == 'scr001' else 104}@@", pp=PP_CENTER))
        out.append(para("2) 화면 설명"))
        for label, lines in items:
            for i, line in enumerate(lines):
                prefix = f"· {label}: " if i == 0 else "   "
                out.append(para(runs=[(prefix, CP_BOLD if i == 0 else CP_BODY), (line, CP_BODY)], pp=PP_ITEM))
    return out


def main(src, dst, pages_json=None):
    pages = json.load(open(pages_json, encoding="utf-8")) if pages_json else {}
    zin = zipfile.ZipFile(src)
    root = etree.fromstring(zin.read("Contents/section0.xml"))
    ps = root.findall(HP + "p")
    assert len(ps) == 139, f"unexpected template paragraph count {len(ps)}"

    ctx = {
        "tbl": next(ps[30].iter(HP + "tbl")),
        "h2": ps[55],
        "req_title": ps[72],
        "h3": ps[69],
    }

    # --- 머리말 '요구사항정의서' -> '요구사항 정의서'
    for header in root.iter(HP + "header"):
        for t in header.iter(HP + "t"):
            if t.text and "요구사항정의서" in t.text:
                t.text = t.text.replace("요구사항정의서", "요구사항 정의서")
                strip_layout(header)  # cached line layout no longer matches the longer text; Hancom refuses the file

    # --- 양식에 원래 있던 표 2개(템플릿 버전, 문서 버전)도 글자처럼 취급
    for i in (25, 30):
        for tbl in ps[i].iter(HP + "tbl"):
            tbl.find(HP + "pos").set("treatAsChar", "1")
        strip_layout(ps[i])

    # --- 템플릿 버전 표의 빈 줄 4개를 지워 문서 버전 표가 2쪽에 들어갈 자리를 만든다
    tpl_tbl = next(ps[25].iter(HP + "tbl"))
    tpl_rows = tpl_tbl.findall(HP + "tr")
    for tr in tpl_rows[2:]:
        if not "".join(t.text or "" for t in tr.iter(HP + "t")).strip():
            tpl_tbl.remove(tr)
    kept = len(tpl_tbl.findall(HP + "tr"))
    tpl_tbl.find(HP + "sz").set("height", str(int(tpl_tbl.find(HP + "sz").get("height")) * kept // len(tpl_rows)))
    tpl_tbl.set("rowCnt", str(kept))

    # --- 목차: 템플릿의 고정 항목(35~47)을 실제 제목과 쪽번호로 교체
    toc_anchor = ps[35]
    for title, level in C.TOC:
        toc_anchor.addprevious(toc_para(title, level, pages.get(title)))
    for old in ps[35:48]:
        root.remove(old)

    # --- cover: project / team / date under the title
    cover = [para(C.PROJECT, PP_CENTER, CP_COVER_BIG), para(""),
             *[para(line, PP_CENTER, CP_COVER) for line in C.TEAM_LINES],
             para(C.DOC_DATE.replace("-", ". ") + ".", PP_CENTER, CP_COVER)]
    for old, new in zip(ps[11:11 + len(cover)], cover):
        root.replace(old, new)

    # --- 문서 버전 table (template has 5 empty rows; add more when versions outgrow it)
    ver_tbl = ctx["tbl"]
    rows = ver_tbl.findall(HP + "tr")
    while len(rows) - 1 < len(C.VERSION_ROWS):
        new = copy.deepcopy(rows[-1])
        for addr in new.iter(HP + "cellAddr"):
            addr.set("rowAddr", str(len(rows)))
        ver_tbl.append(new)
        rows.append(new)
    ver_tbl.set("rowCnt", str(len(rows)))
    ver_tbl.find(HP + "sz").set("height", str(int(ver_tbl.find(HP + "sz").get("height")) * len(rows) // 6))
    for row, values in zip(rows[1:], C.VERSION_ROWS):
        for tc, value in zip(row.findall(HP + "tc"), values):
            run = tc.find(".//" + HP + "p").find(HP + "run")
            etree.SubElement(run, HP + "t").text = value
            strip_layout(tc)

    # --- body (template paragraphs 50..138 are rebuilt)
    h = {k: copy.deepcopy(ps[i]) for k, i in
         {"s1": 50, "s11": 51, "s12": 55, "s2": 61, "s21": 62, "s22": 65, "s23": 68, "s231": 69,
          "s24": 117, "s25": 122, "s26": 127, "s27": 137}.items()}
    set_text(h["s22"], "2.2 유스케이스(Use Case)")
    set_text(h["s231"], "2.3.1 비즈니스 기능 요구사항")
    h["s2"].set("pageBreak", "1")
    h["s24"].set("pageBreak", "1")
    h["s25"].set("pageBreak", "1")
    h["s27"].set("pageBreak", "1")  # 2.7 heading would otherwise sit alone above its table  # keeps the 2.5 heading with its (unsplittable) table

    body = [h["s1"], h["s11"], *render(C.S11, ctx), para(""),
            h["s12"], *render(C.S12, ctx), para(""),
            heading_without_ctrl(ps[55], "1.3 고객환경"), *render(C.S13, ctx), para(""),
            page_break(heading_without_ctrl(ps[55], "1.4 용어정의")), *render(C.S14, ctx),
            h["s2"], h["s21"], *render(C.S21, ctx), para(""),
            h["s22"], *render(C.S22, ctx), para(""),
            h["s23"], h["s231"],
            para("시스템이 제공해야 할 기능 요구사항은 다음과 같습니다. 요구사항 ID는 FR-001부터 부여하며, 2.2의 유스케이스와 "
                 "설계·테스트 문서에서 동일한 ID로 참조합니다."),
            para(""),
            *requirement_blocks(ctx),
            *screen_blocks(ctx),
            h["s24"], *render(C.S24, ctx), para(""),
            h["s25"], *render(C.S25, ctx), para(""),
            h["s26"], *render(C.S26, ctx), para(""),
            h["s27"], *render(C.S27, ctx)]

    for p in ps[50:]:
        root.remove(p)
    for p in body:
        strip_layout(p)
        root.append(p)

    data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    with zipfile.ZipFile(dst, "w") as zout:
        for info in zin.infolist():
            payload = data if info.filename == "Contents/section0.xml" else zin.read(info.filename)
            compress = zipfile.ZIP_STORED if info.filename == "mimetype" else zipfile.ZIP_DEFLATED
            zout.writestr(info, payload, compress_type=compress)
    print("wrote", dst, "paragraphs:", len(root.findall(HP + "p")))


if __name__ == "__main__":
    main(*sys.argv[1:4])
