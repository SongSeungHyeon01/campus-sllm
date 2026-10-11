"""04_화면설계서+양식.pptx에 screen_content.py 내용을 채워 화면설계서를 만든다.

사용: python build_screen_doc.py <template.pptx> <img_dir> <out.pptx>
양식의 순서도 도형·화살표·표를 복제해서 쓰므로 PowerPoint에서 그대로 수정할 수 있다.
"""
import copy
import datetime
import io
import sys
from pathlib import Path

from lxml import etree
from PIL import Image
from pptx import Presentation

import screen_content as C

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
IN = 914400


def E(v):
    return int(round(v * IN))


# ---------------------------------------------------------------- text
def fill_txbody(txbody, lines, size=None):
    """Replace paragraphs with one per line, reusing the first paragraph's pPr/rPr (keeps template styling)."""
    ps = txbody.findall(A + "p")
    tpl = ps[0]
    ppr = tpl.find(A + "pPr")
    end = tpl.find(A + "endParaRPr")
    r0 = tpl.find(A + "r")
    rpr = copy.deepcopy(r0.find(A + "rPr")) if r0 is not None and r0.find(A + "rPr") is not None else None
    if rpr is None and end is not None:
        rpr = copy.deepcopy(end)
        rpr.tag = A + "rPr"
    if rpr is not None and size:
        rpr.set("sz", str(size))
    for p in ps:
        txbody.remove(p)
    for line in lines or [""]:
        p = etree.SubElement(txbody, A + "p")
        if ppr is not None:
            p.append(copy.deepcopy(ppr))
        if line:
            r = etree.SubElement(p, A + "r")
            if rpr is not None:
                r.append(copy.deepcopy(rpr))
            etree.SubElement(r, A + "t").text = line
        if end is not None:
            e = copy.deepcopy(end)
            if size:
                e.set("sz", str(size))
            p.append(e)


def set_cell(cell, lines, size=None):
    fill_txbody(cell._tc.find(A + "txBody"), [lines] if isinstance(lines, str) else lines, size)


def set_shape_text(shape, lines, size=None):
    fill_txbody(shape._element.find(P + "txBody"), [lines] if isinstance(lines, str) else lines, size)


# ---------------------------------------------------------------- drawing with template prototypes
class Draw:
    def __init__(self, slide, protos, font=None):
        self.tree = slide.shapes._spTree
        self.protos = protos
        self.font = font
        self.nid = 1 + max(int(c.get("id")) for c in self.tree.iter(P + "cNvPr"))

    def clone(self, key):
        el = copy.deepcopy(self.protos[key])
        c = next(el.iter(P + "cNvPr"))
        c.set("id", str(self.nid))
        c.set("name", f"{key} {self.nid}")
        for ext in c.findall(A + "extLst"):
            c.remove(ext)
        self.nid += 1
        self.tree.append(el)
        return el

    @staticmethod
    def xfrm(el, x, y, w, h, flip_h=False, flip_v=False):
        xf = next(el.iter(A + "xfrm"))
        xf.attrib.pop("flipH", None)
        xf.attrib.pop("flipV", None)
        if flip_h:
            xf.set("flipH", "1")
        if flip_v:
            xf.set("flipV", "1")
        xf.find(A + "off").attrib.update({"x": str(E(x)), "y": str(E(y))})
        xf.find(A + "ext").attrib.update({"cx": str(E(w)), "cy": str(E(h))})

    def node(self, key, cx, cy, w, h, lines=None, size=None):
        el = self.clone(key)
        self.xfrm(el, cx - w / 2, cy - h / 2, w, h)
        tb = el.find(P + "txBody")
        if tb is not None and lines is not None:
            body = tb.find(A + "bodyPr")
            for k in ("lIns", "rIns"):
                body.set(k, str(E(0.03)))
            fill_txbody(tb, lines.split("\n"), size or self.font)
        return el

    def seg(self, x1, y1, x2, y2, head, tail, dashed=False):
        el = self.clone("arrow")
        cnv = el.find(P + "nvCxnSpPr").find(P + "cNvCxnSpPr")
        for ch in list(cnv):
            cnv.remove(ch)
        self.xfrm(el, min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1), x2 < x1, y2 < y1)
        ln = el.find(P + "spPr").find(A + "ln")
        for tag, keep in (("headEnd", head), ("tailEnd", tail)):
            e = ln.find(A + tag)
            if e is not None and not keep:
                e.set("type", "none")
        if dashed:
            d = etree.SubElement(ln, A + "prstDash")
            d.set("val", "dash")
            ln.remove(d)
            ln.insert(1, d)  # prstDash goes right after the fill
        return el

    def path(self, pts, dashed=False):
        for i in range(len(pts) - 1):
            self.seg(*pts[i], *pts[i + 1], head=(i == 0), tail=(i == len(pts) - 2), dashed=dashed)

    def label(self, x, y, text, size=None):
        el = self.clone("label")
        self.xfrm(el, x, y, 0.5, 0.2)
        fill_txbody(el.find(P + "txBody"), [text], size or self.font)
        return el


def find(slide, name):
    return next(s for s in slide.shapes if s.name == name)


def keep_only(slide, keep_names):
    for sh in list(slide.shapes):
        if sh.name not in keep_names:
            sh._element.getparent().remove(sh._element)


# ---------------------------------------------------------------- user flow
def draw_flow(slide, protos, flow, table_shape):
    left_title, cols = flow
    t = table_shape.table
    set_cell(t.cell(0, 0), left_title.split("\n"))
    for i, (head, _) in enumerate(cols):
        set_cell(t.cell(0, i + 1), head)
    x0, y0 = table_shape.left / IN, table_shape.top / IN
    widths = [c.width / IN for c in t.columns]
    top = y0 + t.rows[0].height / IN
    d = Draw(slide, protos, font=700)
    nw, nh, dh, step = 1.15, 0.36, 0.42, 0.6
    for ci, (_, nodes) in enumerate(cols):
        cl = x0 + sum(widths[:ci + 1])
        w = widths[ci + 1]
        cx = cl + 0.1 + nw / 2
        sx0, sx1 = cl + 0.1 + nw + 0.12, cl + w - 0.08
        ys = [top + 0.38 + k * step for k in range(len(nodes))]
        hs = []
        for k, (kind, text, branch) in enumerate(nodes):
            if kind in ("start", "end"):
                d.node("term", cx, ys[k], nw, nh, text)
                hs.append(nh)
            elif kind == "proc":
                d.node("proc", cx, ys[k], nw, nh, text)
                hs.append(nh)
            elif kind == "dec":
                d.node("dec", cx, ys[k], nw, dh, text)
                hs.append(dh)
            else:  # connector dot + letter
                d.node("conn", cx, ys[k], 0.24, 0.23)
                d.label(cx + 0.16, ys[k] - 0.11, f"연결 {text}")
                hs.append(0.23)
        for k in range(len(nodes) - 1):
            kind, _, branch = nodes[k]
            if kind == "dec" and branch and branch[2] == "skip":
                continue_to = k + 1
            d.path([(cx, ys[k] + hs[k] / 2), (cx, ys[k + 1] - hs[k + 1] / 2)])
        for k, (kind, text, branch) in enumerate(nodes):
            if kind != "dec" or not branch:
                continue
            down, side_text, back = branch
            other = "NO" if down == "YES" else "YES"
            d.label(cx - 0.42, ys[k] + dh / 2 - 0.02, down)
            right = cx + nw / 2
            if back == "skip":  # other answer skips the next node
                tx = cl + 0.1 + nw + 0.25
                d.path([(right, ys[k]), (tx, ys[k]), (tx, ys[k + 2]), (right, ys[k + 2])])
                d.label(right + 0.04, ys[k] - 0.27, other)
                continue
            sw = sx1 - sx0
            d.node("proc", sx0 + sw / 2, ys[k], sw, nh + 0.04, side_text)
            d.path([(right, ys[k]), (sx0, ys[k])])
            d.label(right + 0.04, ys[k] - 0.27, other)
            if isinstance(back, int):
                bx = sx0 + sw / 2
                d.path([(bx, ys[k] - (nh + 0.04) / 2), (bx, ys[back]), (right, ys[back])])


# ---------------------------------------------------------------- logic process
def draw_logic_qa(slide, protos, db_pics):
    d = Draw(slide, protos, font=800)
    W, H, DH = 1.75, 0.46, 0.52
    y1, y2, y3, ye = 1.95, 3.95, 5.45, 6.55
    xs = [1.25, 3.45, 5.65, 7.85, 10.05]
    d.node("term", xs[0], y1, 1.3, 0.36, "질문 전송")
    d.node("data", xs[1], y1, W, H, "질문 입력\n(+카테고리·캠퍼스·분야)")
    d.node("dec", xs[2], y1, W, DH, "조건 충분?")
    d.node("proc", xs[3], y1, W, H, "동의어 변환\n(수정 → 수강정정)")
    d.node("proc", xs[4], y1, W, H, "질문 임베딩")
    for a, b, wa, wb in [(0, 1, 1.3, W), (1, 2, W, W), (2, 3, W, W), (3, 4, W, W)]:
        d.path([(xs[a] + wa / 2 - (0.08 if a == 1 else 0), y1), (xs[b] - wb / 2 + (0.08 if b == 1 else 0), y1)])
    d.label(xs[2] + W / 2 - 0.05, y1 - 0.25, "YES")
    d.node("proc", xs[2], y1 + 1.0, W, H, "되묻기\n(SCR-001-A)")
    d.path([(xs[2], y1 + DH / 2), (xs[2], y1 + 1.0 - H / 2)])
    d.label(xs[2] + 0.05, y1 + 0.32, "NO")
    d.path([(xs[2] - W / 2, y1 + 1.0), (xs[1], y1 + 1.0), (xs[1], y1 + H / 2)])
    d.node("info", 1.35, y1 + 1.05, 1.6, 0.85, None)
    set_info(d, ["입력 정보", "질문 (1~200자)", "카테고리 (선택)", "캠퍼스 (설정값)", "관심 분야 (선택)"])
    # row 2 (right to left)
    d.node("proc", xs[4], y2, W, H, "벡터 DB 검색\n(Top-5, 카테고리·캠퍼스 필터)")
    d.path([(xs[4], y1 + H / 2), (xs[4], y2 - H / 2)])
    pic_place(db_pics[0], xs[4] + W / 2 + 0.55, y2, "벡터 DB", d)
    d.path([(xs[4] + W / 2, y2), (xs[4] + W / 2 + 0.3, y2)], dashed=True)
    d.node("dec", xs[3] - 0.3, y2, W, DH, "유사도 ≥ 기준?")
    d.path([(xs[4] - W / 2, y2), (xs[3] - 0.3 + W / 2, y2)])
    d.node("proc", xs[2] - 0.5, y2, W, H, "sLLM 답변 생성\n(근거 청크 + 현재 날짜)")
    d.path([(xs[3] - 0.3 - W / 2, y2), (xs[2] - 0.5 + W / 2, y2)])
    d.label(xs[3] - 0.3 - W / 2 - 0.35, y2 - 0.25, "YES")
    d.node("doc", xs[1] - 0.7, y2, W, H, "답변·출처·메뉴 위치\n표시 (SCR-001)")
    d.path([(xs[2] - 0.5 - W / 2, y2), (xs[1] - 0.7 + W / 2, y2)])
    d.node("term", xs[1] - 0.7, ye, 1.3, 0.36, "종료")
    d.path([(xs[1] - 0.7, y2 + H / 2), (xs[1] - 0.7, ye - 0.18)])
    d.node("info", xs[2] - 0.5, y2 + 0.95, 1.9, 0.75, None)
    set_info(d, ["생성 조건", "근거 청크만 사용", "현재 날짜·시각(KST) 전달", "최신 게시물 우선"])
    # NO branch
    d.path([(xs[3] - 0.3, y2 + DH / 2), (xs[3] - 0.3, y3 - H / 2)])
    d.label(xs[3] - 0.25, y2 + 0.32, "NO")
    d.node("proc", xs[3] - 0.3, y3, W, H, "찾을 수 없음 안내\n(SCR-001-B)")
    d.node("proc", xs[4], y3, W, H, "답변 대기 자동 등록\n(문장 + 익명 기기 토큰)")
    d.path([(xs[3] - 0.3 + W / 2, y3), (xs[4] - W / 2, y3)], dashed=True)
    pic_place(db_pics[1], xs[4] + W / 2 + 0.55, y3, "답변 대기 DB", d)
    d.path([(xs[4] + W / 2, y3), (xs[4] + W / 2 + 0.3, y3)], dashed=True)
    d.node("term", xs[3] - 0.3, ye, 1.3, 0.36, "종료")
    d.path([(xs[3] - 0.3, y3 + H / 2), (xs[3] - 0.3, ye - 0.18)])


def draw_logic_answer(slide, protos, db_pic):
    """학과 조교 답변 → FAQ DB 즉시 반영 → 질문했던 기기 익명 알림 (FR-028~030)."""
    d = Draw(slide, protos, font=800)
    W, H, DH = 1.85, 0.46, 0.52
    y1, y2, y3, ye = 2.0, 3.3, 4.6, 5.9
    xa, xb, xc, xd, xe = 1.3, 3.6, 5.9, 8.2, 10.5
    d.node("term", xa, y1, 1.4, 0.36, "이메일 인증 로그인")
    d.node("doc", xb, y1, W, H, "답변 대기 목록\n(SCR-006)")
    d.node("dec", xc, y1, W, DH, "담당 업무?")
    d.node("data", xd, y1, W, H, "답변 작성\n(SCR-006-B)")
    d.node("proc", xe, y1, W, H, "FAQ DB 즉시 저장\n(승인 없음)")
    d.path([(xa + 0.7, y1), (xb - W / 2, y1)])
    d.path([(xb + W / 2, y1), (xc - W / 2, y1)])
    d.path([(xc + W / 2, y1), (xd - W / 2 + 0.08, y1)])
    d.label(xc + W / 2 - 0.05, y1 - 0.25, "YES")
    d.path([(xd + W / 2 - 0.08, y1), (xe - W / 2, y1)])
    pic_place(db_pic, xe + W / 2 + 0.55, y1, "FAQ DB", d)
    d.path([(xe + W / 2, y1), (xe + W / 2 + 0.3, y1)], dashed=True)
    d.node("proc", xe, y2, W, H, "청킹·임베딩 재색인")
    d.path([(xe, y1 + H / 2), (xe, y2 - H / 2)])
    d.node("proc", xe, y3, W, H, "질문했던 기기에 익명 알림\n(FCM) 후 토큰 삭제")
    d.path([(xe, y2 + H / 2), (xe, y3 - H / 2)])
    d.node("term", xe, ye, 1.4, 0.36, "종료")
    d.path([(xe, y3 + H / 2), (xe, ye - 0.18)])
    d.path([(xc, y1 + DH / 2), (xc, y2 - H / 2)])
    d.label(xc + 0.05, y1 + 0.32, "NO")
    d.node("proc", xc, y2, W, H, "‘담당 아님’ 표시")
    d.node("proc", xc, y3, W, H, "관리자가 확인해\n다른 경로로 안내")
    d.path([(xc, y2 + H / 2), (xc, y3 - H / 2)])
    d.node("term", xc, ye, 1.4, 0.36, "종료")
    d.path([(xc, y3 + H / 2), (xc, ye - 0.18)])
    d.node("info", 1.9, y1 + 1.05, 2.5, 0.85, None)
    set_info(d, ["답변 기준", "학과장·교무처·학생처 등에서", "회의로 결정해 전달한 내용으로 작성", "(정보 제공 조직은 시스템 밖)"])
    d.node("info", xd, y2 + 0.2, 2.0, 0.85, None)
    set_info(d, ["반영 결과", "같은 질문에 즉시 답변", "출처: 학과 조교 답변·등록일", "PER-010: 1분 이내 반영·알림"])


def draw_logic_email(slide, protos, db_pic):
    """중간 관리자 이메일 인증 코드 로그인 (FR-032·033) + 매일 09:00 답변 대기 요약 메일 (FR-031)."""
    d = Draw(slide, protos, font=800)
    W, H, DH = 1.85, 0.46, 0.52
    y1, y2 = 2.2, 3.2            # 로그인 줄, NO 분기
    y3, y4 = 4.7, 5.8            # 요약 메일 줄, NO 분기
    xa, xb, xc, xd, xe = 1.3, 3.6, 5.9, 8.2, 10.5
    d.label(0.75, y1 - 0.62, "로그인 (FR-033)")
    d.node("term", xa, y1, 1.4, 0.36, "이메일 입력\n(SCR-006-A)")
    d.node("dec", xb, y1, W, DH, "등록된 이메일?")
    d.node("proc", xc, y1, W, H, "6자리 인증 코드 메일\n(10분, 1회용)")
    d.node("dec", xd, y1, W, DH, "코드 일치?")
    d.node("doc", xe, y1, W, H, "역할별 메뉴로 로그인\n(SCR-006)")
    d.path([(xa + 0.7, y1), (xb - W / 2, y1)])
    d.path([(xb + W / 2, y1), (xc - W / 2, y1)])
    d.label(xb + W / 2 - 0.05, y1 - 0.25, "YES")
    d.path([(xc + W / 2, y1), (xd - W / 2, y1)])
    d.path([(xd + W / 2, y1), (xe - W / 2, y1)])
    d.label(xd + W / 2 - 0.05, y1 - 0.25, "YES")
    pic_place(db_pic[0], xb, y1 - 0.9, "중간 관리자 이메일", d)
    d.path([(xb, y1 - 0.48), (xb, y1 - DH / 2)], dashed=True)
    d.path([(xb, y1 + DH / 2), (xb, y2 - H / 2)])
    d.label(xb + 0.05, y1 + 0.32, "NO")
    d.node("proc", xb, y2, W, H, "같은 안내만 표시\n(코드 발송 안 함)")
    d.path([(xd, y1 + DH / 2), (xd, y2 - H / 2)])
    d.label(xd + 0.05, y1 + 0.32, "NO")
    d.node("proc", xd, y2, W, H, "다시 입력\n(5회 실패 10분 제한)")
    d.node("info", xe, y2 + 0.15, 2.0, 0.85, None)
    set_info(d, ["로그인 유지", "12시간 유지", "이메일 삭제(SCR-006-D) 시", "즉시 권한 회수·세션 종료"])

    d.label(1.15, y3 - 0.62, "답변 대기 요약 메일 (FR-031)")
    d.node("term", xa, y3, 1.4, 0.36, "매일 09:00\n스케줄러")
    d.node("dec", xb, y3, W, DH, "답변 대기 ≥ 1건?")
    d.node("proc", xc, y3, W, H, "같은 질문 수 순 정렬\n(‘담당 아님’ 제외)")
    d.node("proc", xd, y3, W, H, "중간 관리자 이메일로\n발송 (SCR-006-E)")
    d.node("term", xe, y3, 1.4, 0.36, "종료")
    d.path([(xa + 0.7, y3), (xb - W / 2, y3)])
    d.path([(xb + W / 2, y3), (xc - W / 2, y3)])
    d.label(xb + W / 2 - 0.05, y3 - 0.25, "YES")
    d.path([(xc + W / 2, y3), (xd - W / 2, y3)])
    d.path([(xd + W / 2, y3), (xe - 0.7, y3)])
    pic_place(db_pic[1], xc, y3 + 0.85, "답변 대기 DB", d)
    d.path([(xc, y3 + H / 2), (xc, y3 + 0.65)], dashed=True)
    d.path([(xb, y3 + DH / 2), (xb, y4 - 0.18)])
    d.label(xb + 0.05, y3 + 0.32, "NO")
    d.node("term", xb, y4, 1.4, 0.36, "보내지 않음")
    d.node("info", xd + 0.4, y4 + 0.15, 2.6, 0.85, None)
    set_info(d, ["메일 내용", "제목: [물어봐 캠퍼스] 답변 대기 N건", "질문 문장·카테고리·질문 수만 표시", "답변 페이지 링크 (서버 꺼져 있었으면 켜진 뒤 1회)"])


def draw_logic_collect(slide, protos, db_pic):
    d = Draw(slide, protos, font=800)
    W, H, DH = 1.85, 0.46, 0.52
    y1, y2, y3, ye = 2.0, 3.3, 4.6, 5.9
    xa, xb, xc, xd, xe = 1.3, 3.6, 5.9, 8.2, 10.5
    d.node("term", xa, y1, 1.4, 0.36, "스케줄러 실행")
    d.node("proc", xb, y1, W, H, "소스별 수집\n(홈페이지·온통청년 API)")
    d.node("dec", xc, y1, W, DH, "수집 결과 정상?")
    d.node("proc", xd, y1, W, H, "정리·첨부파일\n텍스트 추출")
    d.node("proc", xe, y1, W, H, "청킹·메타데이터 부여")
    d.path([(xa + 0.7, y1), (xb - W / 2, y1)])
    d.path([(xb + W / 2, y1), (xc - W / 2, y1)])
    d.path([(xc + W / 2, y1), (xd - W / 2, y1)])
    d.label(xc + W / 2 - 0.05, y1 - 0.25, "YES")
    d.path([(xd + W / 2, y1), (xe - W / 2, y1)])
    d.node("proc", xe, y2, W, H, "임베딩")
    d.path([(xe, y1 + H / 2), (xe, y2 - H / 2)])
    d.node("proc", xe, y3, W, H, "벡터 DB 갱신\n(변경분 반영·삭제분 제거)")
    d.path([(xe, y2 + H / 2), (xe, y3 - H / 2)])
    pic_place(db_pic, xe + W / 2 + 0.55, y3, "벡터 DB", d)
    d.path([(xe + W / 2, y3), (xe + W / 2 + 0.3, y3)], dashed=True)
    d.node("term", xe, ye, 1.4, 0.36, "종료")
    d.path([(xe, y3 + H / 2), (xe, ye - 0.18)])
    d.path([(xc, y1 + DH / 2), (xc, y2 - H / 2)])
    d.label(xc + 0.05, y1 + 0.32, "NO")
    d.node("proc", xc, y2, W, H, "직전 데이터 유지\n오류 로그 기록")
    d.node("proc", xc, y3, W, H, "수집 현황에 실패 표시\n(SCR-006)")
    d.path([(xc, y2 + H / 2), (xc, y3 - H / 2)])
    d.node("term", xc, ye, 1.4, 0.36, "종료")
    d.path([(xc, y3 + H / 2), (xc, ye - 0.18)])
    d.node("info", 1.9, y1 + 1.05, 2.5, 0.85, None)
    set_info(d, ["수집 주기", "공지·교외활동: 3시간마다", "학사일정·버스·동아리 등: 1일 1회 03:00", "요청 간격 1초 이상"])
    d.node("info", xd, y2 + 0.2, 2.0, 0.85, None)
    set_info(d, ["청크 메타데이터", "chunk_id, category, content", "source_url, collected_at", "campus, posted_at, deadline, menu_path"])


def set_info(d, lines):
    """Fill the most recently added info box: bold title + '- ' lines (template 'Input Information' box)."""
    el = d.tree[-1]
    tb = el.find(P + "txBody")
    fill_txbody(tb, lines, 800)
    first = tb.find(A + "p").find(A + "r")
    if first is not None:
        first.find(A + "rPr").set("b", "1")


def pic_place(pic, cx, cy, text, d):
    pic.left, pic.top, pic.width, pic.height = E(cx - 0.25), E(cy - 0.2), E(0.5), E(0.4)
    d.label(cx - 0.3, cy + 0.2, text)


# ---------------------------------------------------------------- slides helpers
def clone_shape(slide, shape_el):
    el = copy.deepcopy(shape_el)
    tree = slide.shapes._spTree
    nid = 1 + max(int(c.get("id")) for c in tree.iter(P + "cNvPr"))
    next(el.iter(P + "cNvPr")).set("id", str(nid))
    tree.append(el)
    return el


def crop(img_dir, name, kind, out_dir):
    im = Image.open(Path(img_dir) / name)
    w, h = im.size
    keep = 0.655 / 1.2 if kind == "phone" else 1.035 / 1.43
    path = Path(out_dir) / f"crop_{name}"
    im.crop((0, 0, int(w * keep), h)).save(path)
    return path


def main(template, img_dir, out):
    prs = Presentation(template)
    sl = list(prs.slides)
    cover, history, overview, uflow, logic, divider, desc = sl
    layouts = {l.name: l for l in prs.slide_layouts}
    page_box = find(history, "TextBox 4")._element

    # ---- 1. cover
    for ph in cover.placeholders:
        idx = ph.placeholder_format.idx
        val = {0: C.TITLE, 10: C.VERSION, 11: C.DATE, 12: C.WRITER}[idx]
        set_shape_text(ph, val)

    # ---- 2. history
    ht = next(s for s in history.shapes if s.has_table).table
    for r, row in enumerate(C.HISTORY, start=1):
        for c, val in enumerate(row):
            set_cell(ht.cell(r, c), val)

    # ---- 3. overview + schedule
    ot = next(s for s in overview.shapes if s.has_table).table
    for r, key in enumerate(C.OVERVIEW, start=1):
        set_cell(ot.cell(r, 0), key)
        set_cell(ot.cell(r, 1), C.OVERVIEW[key])
    start = datetime.date(*C.SCHEDULE_START)
    days = [start + datetime.timedelta(days=i) for i in range(30)]
    for col in (1, 8, 15, 22, 29):
        set_cell(ot.cell(7, col), f"{days[col - 1].month}/{days[col - 1].day}주")
    for i, day in enumerate(days, start=1):
        set_cell(ot.cell(8, i), str(day.day))
    hatch = next(ot.cell(r, c)._tc for r in range(9, 15) for c in range(1, 31)
                 if b"pattFill" in etree.tostring(ot.cell(r, c)._tc))
    hatch_fill = copy.deepcopy(next(ch for ch in hatch.find(A + "tcPr") if ch.tag == A + "pattFill"))
    for r, (name, a, b) in enumerate(C.SCHEDULE, start=9):
        set_cell(ot.cell(r, 0), name)
        for c in range(1, 31):
            tcpr = ot.cell(r, c)._tc.find(A + "tcPr")
            for ch in list(tcpr):
                if ch.tag in (A + "pattFill", A + "solidFill", A + "noFill", A + "gradFill"):
                    tcpr.remove(ch)
            if a <= c <= b:
                anchor = [i for i, ch in enumerate(tcpr) if ch.tag.split("}")[1] in
                          ("lnL", "lnR", "lnT", "lnB", "lnTlToBr", "lnBlToTr", "cell3D")]
                tcpr.insert(anchor[-1] + 1 if anchor else 0, copy.deepcopy(hatch_fill))

    # ---- 4. user flow (app) + admin flow on a new slide
    uprotos = {
        "term": find(uflow, "순서도: 수행의 시작/종료 5")._element,
        "proc": find(uflow, "순서도: 처리 6")._element,
        "dec": find(uflow, "순서도: 판단 9")._element,
        "conn": find(uflow, "순서도: 연결자 31")._element,
        "arrow": find(uflow, "직선 화살표 연결선 14")._element,
        "label": find(uflow, "직사각형 76")._element,
    }
    uprotos = {k: copy.deepcopy(v) for k, v in uprotos.items()}
    utable = next(s for s in uflow.shapes if s.has_table)
    utable_el = copy.deepcopy(utable._element)
    keep_only(uflow, {"제목 1", utable.name, "TextBox 138"})
    set_shape_text(find(uflow, "제목 1"), "User flow ① 학생")
    draw_flow(uflow, uprotos, C.APP_FLOW, utable)

    aflow = prs.slides.add_slide(layouts["Summary"])
    set_shape_text(aflow.placeholders[0], "User flow ② 학과 조교 (중간 관리자)")
    clone_shape(aflow, page_box)
    tel = clone_shape(aflow, utable_el)
    atable = next(s for s in aflow.shapes if s.has_table)
    draw_flow(aflow, uprotos, C.ADMIN_FLOW, atable)

    # ---- 5. logic process (질의응답) + collect on a new slide
    lprotos = {
        "term": find(logic, "순서도: 수행의 시작/종료 2")._element,
        "proc": find(logic, "순서도: 처리 7")._element,
        "dec": find(logic, "순서도: 판단 23")._element,
        "data": find(logic, "순서도: 데이터 6")._element,
        "doc": find(logic, "순서도: 문서 4")._element,
        "arrow": find(logic, "직선 화살표 연결선 9")._element,
        "label": find(logic, "직사각형 51")._element,
        "info": find(logic, "직사각형 20")._element,
    }
    lprotos = {k: copy.deepcopy(v) for k, v in lprotos.items()}
    db_blob = find(logic, "그림 50").image.blob
    keep_only(logic, {"제목 1", "그림 50", "그림 53"})
    set_shape_text(find(logic, "제목 1"), "Logic process ① 질의응답 처리")
    clone_shape(logic, page_box)
    draw_logic_qa(logic, lprotos, [find(logic, "그림 50"), find(logic, "그림 53")])

    lcol = prs.slides.add_slide(layouts["Summary"])
    set_shape_text(lcol.placeholders[0], "Logic process ② 데이터 수집·갱신")
    clone_shape(lcol, page_box)
    pic = lcol.shapes.add_picture(io.BytesIO(db_blob), 0, 0, E(0.5), E(0.4))
    draw_logic_collect(lcol, lprotos, pic)

    lans = prs.slides.add_slide(layouts["Summary"])
    set_shape_text(lans.placeholders[0], "Logic process ③ 학과 조교 답변 반영")
    clone_shape(lans, page_box)
    pic = lans.shapes.add_picture(io.BytesIO(db_blob), 0, 0, E(0.5), E(0.4))
    draw_logic_answer(lans, lprotos, pic)

    lmail = prs.slides.add_slide(layouts["Summary"])
    set_shape_text(lmail.placeholders[0], "Logic process ④ 이메일 로그인·답변 대기 요약 메일")
    clone_shape(lmail, page_box)
    pics = [lmail.shapes.add_picture(io.BytesIO(db_blob), 0, 0, E(0.5), E(0.4)) for _ in range(2)]
    draw_logic_email(lmail, lprotos, pics)

    # ---- 6. screen list (History table restyled)
    slist = prs.slides.add_slide(layouts["Summary"])
    set_shape_text(slist.placeholders[0], "화면 목록")
    clone_shape(slist, page_box)
    clone_shape(slist, next(s for s in history.shapes if s.has_table)._element)
    lt = next(s for s in slist.shapes if s.has_table)
    tbl = lt._element.find(".//" + A + "tbl")
    rows = tbl.findall(A + "tr")
    body_tpl = copy.deepcopy(rows[2])
    for tr in rows[1:]:
        tbl.remove(tr)
    for _ in C.SCREEN_LIST:
        tbl.append(copy.deepcopy(body_tpl))
    for gc, w in zip(tbl.find(A + "tblGrid").findall(A + "gridCol"), [1.25, 2.35, 1.35, 3.2, 2.56]):
        gc.set("w", str(E(w)))
    lt.top = E(1.45)
    t = lt.table
    for c, head in enumerate(["화면 ID.", "화면명.", "구분.", "진입 경로.", "관련 요구사항."]):
        set_cell(t.cell(0, c), head)
    for r, row in enumerate(C.SCREEN_LIST, start=1):
        for c, val in enumerate(row):
            set_cell(t.cell(r, c), val, 900)
            for ppr in t.cell(r, c)._tc.iter(A + "pPr"):  # History's Content column carries bullets
                for ch in list(ppr):
                    if ch.tag in (A + "buChar", A + "buFont", A + "buAutoNum"):
                        ppr.remove(ch)
                ppr.set("marL", "0")
                ppr.set("indent", "0")
                if ppr.find(A + "buNone") is None:
                    etree.SubElement(ppr, A + "buNone")

    # ---- 7. dividers + description slides
    set_shape_text(next(p for p in divider.placeholders if p.placeholder_format.idx == 0), C.SECTIONS[0][0])
    set_shape_text(next(p for p in divider.placeholders if p.placeholder_format.idx == 10), C.SECTIONS[0][1])
    div2 = prs.slides.add_slide(layouts["사용자 지정 레이아웃"])
    for ph in div2.placeholders:
        set_shape_text(ph, C.SECTIONS[1][0] if ph.placeholder_format.idx == 0 else C.SECTIONS[1][1])

    sum_el = copy.deepcopy(next(s for s in desc.shapes if s.has_table)._element)
    desc_slides = {0: [], 1: []}
    crops = Path(out).parent / "crops"
    crops.mkdir(exist_ok=True)
    for n, (sec, sid, name, group, img, kind, summary, items) in enumerate(C.SCREENS):
        if n == 0:
            s = desc
        else:
            s = prs.slides.add_slide(layouts["Description"])
            clone_shape(s, page_box)
            clone_shape(s, sum_el)
        for ph in s.placeholders:
            set_shape_text(ph, f"{sid} {name}" if ph.placeholder_format.idx == 10 else group)
        st = next(x for x in s.shapes if x.has_table).table
        set_cell(st.cell(1, 0), summary)
        for i in range(7):
            set_cell(st.cell(2 + i, 0), str(i + 1) if i < len(items) else "")
            set_cell(st.cell(2 + i, 1), items[i] if i < len(items) else "")
        path = crop(img_dir, img, kind, crops)
        im = Image.open(path)
        h = 6.75
        w = h * im.width / im.height
        if w > 9.0:
            w, h = 9.0, 9.0 * im.height / im.width
        s.shapes.add_picture(str(path), E(0.15 + (9.25 - w) / 2), E(0.6), E(w), E(h))
        desc_slides[sec].append(s)

    # ---- order + page numbers
    order = [cover, history, overview, uflow, aflow, logic, lcol, lans, lmail, slist, divider, *desc_slides[0], div2, *desc_slides[1]]
    lst = prs.slides._sldIdLst
    ids = {s.slide_id: el for el in lst for s in prs.slides if s.slide_id == int(el.get("id"))}
    for s in order:
        el = ids[s.slide_id]
        lst.remove(el)
        lst.append(el)
    for no, s in enumerate(order, start=1):
        for sh in s.shapes:
            if sh.shape_type == 17 and sh.left and sh.left > E(12.5) and sh.top < E(0.5):
                set_shape_text(sh, str(no))
    prs.save(out)
    print("saved", out, "slides", len(order))


if __name__ == "__main__":
    main(*sys.argv[1:4])
