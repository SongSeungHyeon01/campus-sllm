"""9주차 중간 현황 발표 자료를 트립버짓 해커톤 발표(v6) 디자인으로 만든다.

- 내용과 대본은 build_deck_9w.py의 SLIDES/QNA를 그대로 쓴다 (장 순서 동일).
- v6 파일에 내장된 'a고딕' 글꼴을 쓰려고 v6를 템플릿으로 열고, 기존 슬라이드를 모두 지운 뒤 새로 그린다.
- 디자인 규칙 (v6에서 추출): 흰 배경, 보라 #5E2BB8 강조, 제목 가운데 30pt + 키워드만 보라,
  왼쪽 위 섹션 머리말, 오른쪽 위 브랜드명, 오른쪽 아래 쪽번호, 얇은 회색 선 카드, 연보라 인용 상자.
사용: set TRIP_TEMPLATE=<트립버짓_해커톤_발표_v6.pptx 경로> 후 python build_deck_9w_trip.py
"""
import os
import sys
from pathlib import Path

from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]   # 문서/작업/<폴더> → 리포 최상위
sys.path.insert(0, str(HERE))
from build_deck_9w import QNA, SLIDES as BASE  # noqa: E402  (대본 재사용)

# 템플릿은 각자 PC에 있는 파일 경로를 환경 변수로 준다 (리포에는 넣지 않음)
TEMPLATE = Path(os.environ.get("TRIP_TEMPLATE", Path.home() / "트립버짓_해커톤_발표_v6.pptx"))
FIG = ROOT / "문서" / "07_진행보고서" / "그림_중간현황"
OUT_PPTX = ROOT / "문서" / "07_진행보고서" / "중간현황_9주차_발표자료_v2.pptx"
OUT_MD = ROOT / "문서" / "07_진행보고서" / "중간현황_9주차_발표대본.md"

I = Inches
P, P2, P3 = RGBColor(0x5E, 0x2B, 0xB8), RGBColor(0xB7, 0x9C, 0xFF), RGBColor(0xE6, 0xDC, 0xFF)
INK, MUTED, FAINT = RGBColor(0x11, 0x11, 0x11), RGBColor(0x6B, 0x6B, 0x73), RGBColor(0x9A, 0x9A, 0xA3)
LINE, TINT, LAV = RGBColor(0xD9, 0xD9, 0xDF), RGBColor(0xF3, 0xEE, 0xFD), RGBColor(0xDC, 0xCF, 0xFF)
WHITE, CORAL = RGBColor(0xFF, 0xFF, 0xFF), RGBColor(0xD9, 0x4F, 0x3D)
F_B, F_M, F_R = "a고딕15", "a고딕14", "a고딕13"      # 굵게(제목·숫자), 중간(라벨), 본문
L, W = 0.72, 11.89                                # 본문 왼쪽 여백, 폭 (인치)
BRAND = "물어봐 캠퍼스"


# ---------- 기본 도형 ----------
def _font(run, name, size, color):
    run.font.name, run.font.size = name, Pt(size)
    run.font.color.rgb = color
    rpr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rpr.find(qn(tag))
        if el is None:
            el = etree.SubElement(rpr, qn(tag))
        el.set("typeface", name)


def rich(line, color, accent):
    """'**강조**' 표기를 (글자, 색) 조각으로 나눈다."""
    parts = line.split("**")
    return [(t, accent if i % 2 else color) for i, t in enumerate(parts) if t]


def tx(s, x, y, w, h, content, size=13, font=F_R, color=INK, accent=P, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.15):
    """content: 문자열 또는 문자열 목록(줄). 줄 안의 **...**는 accent 색."""
    b = s.shapes.add_textbox(I(x), I(y), I(w), I(h))
    tf = b.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    lines = content if isinstance(content, list) else [content]
    for k, line in enumerate(lines):
        para = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        para.alignment, para.line_spacing = align, spacing
        for t, c in rich(line, color, accent):
            r = para.add_run()
            r.text = t
            _font(r, font, size, c)
    return b


def rect(s, x, y, w, h, fill=None, line=None, lw=1.0, shape=MSO_SHAPE.RECTANGLE):
    r = s.shapes.add_shape(shape, I(x), I(y), I(w), I(h))
    r.shadow.inherit = False
    if fill is None:
        r.fill.background()
    else:
        r.fill.solid()
        r.fill.fore_color.rgb = fill
    if line is None:
        r.line.fill.background()
    else:
        r.line.color.rgb, r.line.width = line, Pt(lw)
    return r


def hline(s, x1, y1, x2, y2, color=LINE, lw=1.0, arrow=False):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, I(x1), I(y1), I(x2), I(y2))
    c.line.color.rgb, c.line.width = color, Pt(lw)
    st = c._element.find(qn("p:style"))       # 테마 스타일(그림자)을 떼어 얇은 선 한 줄로
    if st is not None:
        c._element.remove(st)
    if arrow:
        ln = c.line._get_or_add_ln()
        te = etree.SubElement(ln, qn("a:tailEnd"))
        te.set("type", "triangle"), te.set("w", "med"), te.set("len", "med")
    return c


def num(s, x, y, n, d=0.32, fill=P):
    rect(s, x, y, d, d, fill=fill, shape=MSO_SHAPE.OVAL)
    tx(s, x, y, d, d, str(n), 11, F_B, WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def pic(s, path, x, y, h=None, w=None, border=True):
    im = Image.open(path)
    if h is not None:
        w = h * im.width / im.height
    else:
        h = w * im.height / im.width
    s.shapes.add_picture(str(path), I(x), I(y), I(w), I(h))
    if border:
        rect(s, x, y, w, h, line=RGBColor(0xE2, 0xE2, 0xE8), lw=0.75)
    return w, h


def quote(s, y, h, main, sub=None):
    """연보라 상자 + 왼쪽 보라 막대 (v6의 인용 상자)."""
    rect(s, L, y, W, h, fill=TINT)
    rect(s, L, y, 0.09, h, fill=P)
    if sub:
        tx(s, L + 0.5, y + 0.14, W - 0.8, 0.45, main, 17, F_B, INK)
        tx(s, L + 0.5, y + h - 0.45, W - 0.8, 0.32, sub, 12, F_R, MUTED)
    else:
        tx(s, L + 0.5, y, W - 0.8, h, main, 15, F_R, INK, anchor=MSO_ANCHOR.MIDDLE, spacing=1.3)


def table(s, x, y, widths, header, rows, row_h=0.46, hl_col=None, size=12, hl_row=None):
    """선만 있는 표. hl_col: 연보라로 강조할 열, hl_row: 보라 글씨로 강조할 행."""
    total = sum(widths)
    if hl_col is not None:
        cx = x + sum(widths[:hl_col])
        rect(s, cx, y, widths[hl_col], row_h * (len(rows) + 1), fill=TINT)
    hline(s, x, y, x + total, y, INK, 1.0)
    cx = x
    for j, h in enumerate(header):
        tx(s, cx + 0.12, y, widths[j] - 0.2, row_h, h, 11, F_M, P if j == hl_col else FAINT, anchor=MSO_ANCHOR.MIDDLE)
        cx += widths[j]
    for i, row in enumerate(rows):
        ry = y + row_h * (i + 1)
        hline(s, x, ry, x + total, ry, LINE, 0.75)
        cx = x
        for j, cell in enumerate(row):
            strong = j == hl_col or i == hl_row
            tx(s, cx + 0.12, ry, widths[j] - 0.2, row_h, cell, size, F_M if strong else F_R,
               P if strong else (INK if j == 0 else MUTED), anchor=MSO_ANCHOR.MIDDLE)
            cx += widths[j]
    end = y + row_h * (len(rows) + 1)
    hline(s, x, end, x + total, end, LINE, 0.75)
    return end


def stat(s, x, y, w, big, unit, label, divider=True):
    tx(s, x, y, w, 0.85, [f"{big}"], 44, F_B, P, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.BOTTOM) if not unit else None
    if unit:
        b = s.shapes.add_textbox(I(x), I(y), I(w), I(0.85))
        tf = b.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.BOTTOM
        para = tf.paragraphs[0]
        para.alignment = PP_ALIGN.CENTER
        for t, sz in ((big, 44), (unit, 22)):
            r = para.add_run()
            r.text = t
            _font(r, F_B, sz, P)
    tx(s, x, y + 0.95, w, 0.6, label, 13, F_R, MUTED, align=PP_ALIGN.CENTER)
    if divider:
        hline(s, x, y + 0.1, x, y + 1.45, LINE, 1.0)


def page(prs, no, crumb, title, foot=None):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = WHITE
    tx(s, L, 0.42, 6.0, 0.3, crumb, 11, F_M, FAINT)
    tx(s, 10.61, 0.38, 2.0, 0.34, BRAND, 14, F_B, P, align=PP_ALIGN.RIGHT)
    tx(s, 11.61, 7.08, 1.0, 0.25, f"{no:02d}", 10, F_R, FAINT, align=PP_ALIGN.RIGHT)
    tx(s, L, 0.86, W, 0.62, title, 30, F_B, INK, align=PP_ALIGN.CENTER)
    if foot:
        tx(s, L, 7.12, 10.6, 0.3, foot, 9, F_R, FAINT)
    return s


def purple_slide(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = P
    return s


# ---------- 슬라이드 ----------
def cover(prs, no):
    s = purple_slide(prs)
    tx(s, 0.8, 0.62, 7.0, 0.3, "캡스톤디자인 1조  ·  9주차 중간 현황 발표", 12, F_R, LAV)
    tx(s, 0.72, 1.6, 7.0, 1.5, "물어봐 캠퍼스", 68, F_B, WHITE)
    hline(s, 0.78, 3.32, 1.58, 3.32, WHITE, 2.0)
    tx(s, 0.78, 3.55, 6.4, 1.1, ["학교 자료로만 답하고,", "모르면 조교에게 묻는 캠퍼스 Q&A"], 28, F_B, WHITE, spacing=1.2)
    tx(s, 0.78, 5.1, 6.0, 0.6, ["RAG와 sLLM 기반 캠퍼스 정보 질의응답 앱 (Android)", "2026-11-10 기준 · 계획 15주 중 9주차"], 13, F_R, LAV, spacing=1.3)
    tx(s, 0.78, 6.72, 7.0, 0.3, "송승현 · 이승우", 12, F_R, LAV)
    # 오른쪽 앱 화면 두 장 (답변 / 자료에 없는 질문), 높이를 엇갈리게
    pic(s, FIG / "app_answer.png", 7.9, 0.85, h=4.6, border=False)
    pic(s, FIG / "app_notfound.png", 10.65, 1.75, h=4.6, border=False)
    return s


def problem(prs, no):
    s = page(prs, no, "01  문제 · 정보는 있는데", "학교 정보는 있는데, **못 찾는다**",
             "출처: 1차 사전 설문 (9명, 모두 아산캠퍼스라 방향 참고용) · 학교 홈페이지 수집 2026.10.12")
    cw = W / 3
    for i, (b, u, lab) in enumerate([("78", "%", ["포털이 불편하다", "(검색 · 메뉴)"]), ("89", "%", ["이런 앱을", "쓰겠다"]),
                                      ("6", "곳", ["자료를 모아 온 메뉴", "공지 게시판 3곳 · 학사일정 · 버스 · 동아리"])]):
        stat(s, L + i * cw, 1.9, cw, b, u, lab, divider=i > 0)
    tx(s, L, 4.05, W, 0.4, "신입생이 시험 기간에 알고 싶은 것", 13, F_M, P, align=PP_ALIGN.CENTER)
    for i, (q, a) in enumerate([("“기말고사 언제야?”", "학사일정 메뉴를 알아야 찾는다"), ("“폐강된 과목 언제 정정해?”", "학사공지 게시판을 뒤져야 찾는다")]):
        x = L + 0.6 + i * 5.6
        rect(s, x, 4.55, 5.1, 0.95, line=LINE)
        tx(s, x + 0.3, 4.62, 4.6, 0.4, q, 16, F_B, INK)
        tx(s, x + 0.3, 5.05, 4.6, 0.35, "→  " + a, 12, F_R, MUTED)
    tx(s, L, 5.95, W, 0.5, "문제는 정보가 없는 게 아니라, **어디 있는지 알아야만 찾을 수 있다는 점**이었다", 17, F_R, INK, align=PP_ALIGN.CENTER)
    return s


def cause(prs, no):
    s = page(prs, no, "01  문제 · 기존 방식의 한계", "포털은 말을 못 알아듣고, **AI는 우리 학교를 모른다**")
    rows = [["우리 학교 최신 자료", "있음 (흩어져 있음)", "없음", "한곳에 모아 검색"],
            ["말로 묻기", "단어가 맞아야 함", "가능", "가능"],
            ["출처 · 원문 확인", "가능", "없음", "출처 3개 · 원문 · 메뉴 위치"],
            ["모를 때", "결과 없음", "지어낼 수 있음", "“찾을 수 없습니다” + 조교에게"],
            ["질문이 외부로 나감", "해당 없음", "나감", "안 나감 (노트북에서 실행)"]]
    table(s, L + 0.4, 1.8, [2.6, 2.6, 2.6, 3.3], ["", "포털 검색", "범용 AI (ChatGPT 등)", "물어봐 캠퍼스"], rows, row_h=0.58, hl_col=3, size=13)
    tx(s, L, 5.65, W, 0.9, ["그렇다면, 학교 자료로만 답하고", "**모르면 지어내지 말고 사람에게 넘기면** 되지 않을까?"], 22, F_B, INK, align=PP_ALIGN.CENTER, spacing=1.25)
    return s


def scenes(prs, no):
    s = page(prs, no, "02  해결 · 사용 장면", "묻고, 출처와 함께 받고, **모르면 조교가 답한다**",
             "화면: Android 앱 (2026-10-12 시험) · 답변 내용은 2026-11-10 비교 시험 기준")
    w1, _ = pic(s, FIG / "app_answer.png", L + 0.2, 1.75, h=4.7)
    w2, _ = pic(s, FIG / "app_notfound.png", L + 0.2 + w1 + 0.3, 1.75, h=4.7)
    tx(s, L + 0.2, 6.5, w1, 0.3, "답변 · 출처 · 원문 보기", 10, F_R, FAINT, align=PP_ALIGN.CENTER)
    tx(s, L + 0.5 + w1, 6.5, w2, 0.3, "자료에 없는 질문", 10, F_R, FAINT, align=PP_ALIGN.CENTER)
    x = L + 0.2 + w1 + w2 + 0.85
    w = L + W - x
    items = [("“2학기 기말고사 언제야?”", "학사일정에서 찾아 “12월 8일부터 14일까지”로 답하고 출처 · 원문을 붙인다"),
             ("“기숙사 신청 언제 해?” (자료 없음)", "지어내지 않고 “찾을 수 없습니다” → 답변 대기에 자동 등록"),
             ("조교가 한 번 답하면", "비슷한 질문까지 묶여, 다음 학생부터는 그 답이 바로 나간다"),
             ("“두정역인데 가장 빠른 버스?”", "현재 시각 · 요일로 서버 코드가 다음 차를 계산한다 (AI 안 씀)")]
    for i, (h, d) in enumerate(items):
        y = 1.85 + i * 1.08
        num(s, x, y + 0.02, i + 1)
        tx(s, x + 0.5, y, w - 0.5, 0.35, h, 15, F_B, INK)
        tx(s, x + 0.5, y + 0.42, w - 0.5, 0.55, d, 12, F_R, MUTED)
    rect(s, x, 6.12, w, 0.45, fill=TINT)
    tx(s, x + 0.2, 6.12, w - 0.3, 0.45, "결과   **모르는 질문이 쌓일수록, 답할 수 있는 질문이 늘어난다**", 12, F_M, INK, anchor=MSO_ANCHOR.MIDDLE)
    return s


def pipeline(prs, no):
    s = page(prs, no, "03  검증 · AI 활용 구조", "AI는 **찾고 쓰기만** 한다. 계산과 판정은 코드가 한다",
             "질문 1건당 외부 AI 요금 0원 (모델을 노트북 GPU에서 직접 실행, 전기료는 미측정) · 질문은 외부 서비스로 나가지 않음")
    cards = [("화면", "Android 앱 · 조교 웹", ["질문 · 답변 · 출처 · 원문 보기", "답변 대기 · 답변 작성 · FAQ"]),
             ("서버", "FastAPI (Python)", ["검색 · 판정 · 버스 시간 계산", "답변 대기 등록 · FAQ 반영"]),
             ("모델 (노트북 GPU)", "KURE-v1 · Kanana 1.5 2.1B", ["KURE: 비슷한 자료 찾기", "Kanana: 찾은 자료로 문장 쓰기"])]
    cw, gap = 3.55, 0.62
    for i, (lab, head, desc) in enumerate(cards):
        x = L + i * (cw + gap)
        rect(s, x, 1.72, cw, 1.42, line=LINE)
        tx(s, x + 0.25, 1.86, cw - 0.5, 0.28, lab, 11, F_M, P)
        tx(s, x + 0.25, 2.14, cw - 0.5, 0.36, head, 15, F_B, INK)
        tx(s, x + 0.25, 2.56, cw - 0.5, 0.5, desc, 11, F_R, MUTED)
        if i < 2:
            hline(s, x + cw + 0.08, 2.43, x + cw + gap - 0.08, 2.43, P, 1.5, arrow=True)
    colw = W / 3
    cols = [("AI가 하는 일 - 찾고 쓰기", P, ["질문과 비슷한 학교 자료 찾기", "찾은 자료로만 답 문장 만들기", "자료에 없으면 “찾을 수 없음”"], False),
            ("코드가 하는 일 - 계산과 판정", INK, ["통학버스 다음 차 계산", "검색 점수 0.60 미만이면 답 안 함", "“모름” 표현 판정, 빈 칸 · 맺음말 삭제"], False),
            ("틀렸을 때 - 사람이 마지막", INK, ["출처 3개 · 원문 · 메뉴 위치를 항상 표시", "근거 없으면 답변 대기에 자동 등록", "조교가 답하면 FAQ로 즉시 반영"], True)]
    for i, (h, c, items, numbered) in enumerate(cols):
        x = L + i * colw + (0.15 if i else 0)
        if i:
            hline(s, L + i * colw - 0.05, 3.5, L + i * colw - 0.05, 5.3)
        tx(s, x, 3.48, colw - 0.3, 0.36, h, 15, F_B, c)
        for k, it in enumerate(items):
            y = 3.95 + k * 0.42
            if numbered:
                num(s, x, y + 0.01, k + 1, d=0.28)
                tx(s, x + 0.4, y, colw - 0.7, 0.34, it, 12, F_R, MUTED)
            else:
                tx(s, x, y, colw - 0.3, 0.34, "·  " + it, 12, F_R, MUTED)
    rect(s, L, 5.62, W, 0.95, fill=TINT)
    tx(s, L + 0.35, 5.68, W - 0.6, 0.85,
       ["**왜 AI여야 하는가**    “다음 학기 복학 언제야?” 같은 말은 단어 검색으로 못 찾는다.",
        "**왜 AI에게 다 맡기지 않는가**    2B 모델은 시간을 비교하지 못했고, 모르면 지어낼 수 있다."], 13, F_R, INK, anchor=MSO_ANCHOR.MIDDLE, spacing=1.4)
    return s


def data_privacy(prs, no):
    s = page(prs, no, "03  검증 · 데이터와 개인정보", "공개 자료만 모으고, **학생을 알아볼 정보는 남기지 않는다**",
             "수집: 학교 홈페이지 공개 페이지 (로그인이 필요한 페이지 제외) · 청크 154개 · 수집일 2026.10.12")
    tx(s, L, 1.8, 5.5, 0.36, "데이터 - 어디서, 얼마나", 15, F_B, P)
    table(s, L, 2.3, [2.6, 3.0], ["자료", "분량"], [["학사 · 일반 · 장학 공지", "게시판마다 최근 20건"], ["학사일정", "일정 66건 (일정 하나 = 조각 하나)"],
                                                    ["통학버스 (영동 · 아산)", "페이지 4개, 주말 · 방학 포함"], ["동아리현황", "1페이지"]], row_h=0.5, size=12)
    tx(s, L, 5.0, 5.6, 0.7, ["약점   **자동 재수집이 없어 10/12 이후 갱신되지 않음**", "→ 스케줄러로 자동 재수집 구현 예정"], 12, F_R, MUTED, spacing=1.4)
    x = L + 6.3
    hline(s, x - 0.3, 1.85, x - 0.3, 5.8)
    tx(s, x, 1.8, 5.5, 0.36, "개인정보 - 저장 안 함 · 가림 · 지움", 15, F_B, INK)
    rows = [("로그인 없음, 이름 · 학번 · 기기 ID 칸 자체가 없음", True), ("질문이 외부 AI 서비스로 나가지 않음", True),
            ("저장 전에 전화번호 · 학번 형태를 가림", True), ("질문 속 이름 가리기", False), ("답변 대기 30일 뒤 삭제", False)]
    for k, (t, ok) in enumerate(rows):
        y = 2.35 + k * 0.62
        rect(s, x, y, 0.3, 0.3, fill=P if ok else RGBColor(0xC9, 0xC9, 0xD1), shape=MSO_SHAPE.OVAL)
        tx(s, x, y, 0.3, 0.3, "✓" if ok else "–", 11, F_B, WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        tx(s, x + 0.45, y - 0.02, 4.4, 0.34, t, 13, F_R, INK if ok else MUTED)
        tx(s, x + 4.9, y - 0.02, 0.7, 0.34, "구현" if ok else "예정", 11, F_M, P if ok else FAINT, align=PP_ALIGN.RIGHT)
    return s


def numbers(prs, no):
    s = page(prs, no, "03  검증 · 직접 잰 수치", "평가 질문 108개로 **처음 재 보았다**",
             "2026-11-10 측정 · 평가 질문: 답 있는 질문 80 (구어체 25 포함) · 자료에 없는 질문 20 · 일부만 있는 질문 8")
    cw = W / 4
    for i, (b, u, lab) in enumerate([("98.8", "%", ["검색 정확도 79/80", "(목표 80%)"]), ("9 / 9", "", ["조교 답변 흐름", "등록부터 FAQ 답변까지"]),
                                      ("10 / 10", "", ["통학버스 시간 계산", "시각 · 요일을 바꿔 시험"]), ("2.1~3.5", "초", ["sLLM 평균 답변 시간", "(목표 5초)"])]):
        stat(s, L + i * cw, 1.75, cw, b, u, lab, divider=i > 0)
    tx(s, L, 3.75, 5.6, 0.36, "근거 기준값에 따라 달라지는 것", 15, F_B, INK)
    table(s, L, 4.2, [1.9, 1.85, 1.85], ["기준값", "답 있는 질문 살림", "없는 질문 걸러 냄"],
          [["0.56", "76 / 80", "13 / 20"], ["0.60 (현재)", "72 / 80", "17 / 20"], ["0.64", "61 / 80", "20 / 20"]], row_h=0.44, hl_row=1)
    x = L + 6.2
    rect(s, x, 3.8, L + W - x, 2.55, fill=TINT)
    rect(s, x, 3.8, 0.09, 2.55, fill=P)
    tx(s, x + 0.4, 3.95, 5.0, 0.4, "이 숫자를 그대로 믿으면 안 되는 이유", 15, F_B, P)
    tx(s, x + 0.4, 4.5, 5.2, 1.7, ["·  질문을 우리가 자료를 보며 써서 **낙관적인 수치**", "·  실제 학생 질문으로는 아직 재지 않았다",
                                   "·  기준값 0.60에서는 답 있는 질문 **8개를 놓친다**", "→  홈페이지 Q&A 게시판 질문으로 다시 잰다"], 13, F_R, INK, spacing=1.5)
    return s


def models(prs, no):
    s = page(prs, no, "03  검증 · 모델 선택", "후보 셋 중 **Kanana 1.5**가 가장 정확했다",
             "같은 질문 19개 · 같은 조건 (원본 bf16, 임베딩 CPU) · 시각 2026-11-10 14:00 고정 · Qwen3.5 2B는 아직 시험하지 못함")
    table(s, L, 1.75, [3.3, 2.2, 2.3, 2.0, 2.09], ["Hugging Face 후보", "답 있는 질문 (12)", "자료에 없는 질문 (4)", "평균 생성 시간", "라이선스"],
          [["Kanana 1.5 2.1B (카카오, 현재)", "12", "4", "2.1초", "Apache-2.0"], ["Midm 2.0 Mini (KT)", "11", "4", "2.4초", "MIT"],
           ["Kanana-2 3B (카카오, 최신)", "8", "4", "1.65초", "전용 (표시 의무)"]], row_h=0.52, hl_row=0, size=13)
    tx(s, L, 4.0, W, 0.36, "같은 질문, 다른 답   “학습법 공모전 총 상금 얼마야?”", 15, F_B, INK)
    ans = [("Kanana 1.5", "대상 30만원, 최우수상 2명 각 20만원, 우수상 3명 각 10만원", "정답", P),
           ("Midm 2.0 Mini", "총 상금은 90만원입니다", "오답 · 실제 합계 100만원", CORAL),
           ("Kanana-2 3B", "해당 정보를 찾을 수 없습니다", "자료에 있는데 모른다고 함", CORAL)]
    for i, (m, a, v, c) in enumerate(ans):
        y = 4.5 + i * 0.6
        hline(s, L, y, L + W, y)
        tx(s, L + 0.12, y, 2.6, 0.6, m, 13, F_M, INK, anchor=MSO_ANCHOR.MIDDLE)
        tx(s, L + 2.8, y, 6.2, 0.6, f"“{a}”", 13, F_R, MUTED, anchor=MSO_ANCHOR.MIDDLE)
        tx(s, L + 9.0, y, 2.8, 0.6, v, 12, F_M, c, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    hline(s, L, 6.3, L + W, 6.3)
    return s


def fixes(prs, no):
    s = page(prs, no, "03  검증 · 고친 오답", "틀린 답을 찾아 **원인부터** 고쳤다",
             "개발 중 문제 8건의 원인 · 해결 과정을 모두 오류 보고서(docs/오류보고서)로 남김")
    cards = [("“가장 빠른 버스”에 10:15로 답함 (08:00이 맞음)", "시간표 일부만 검색 · 현재 시각 미전달 · 2B 모델의 시간 비교 한계",
              "시간표 조회는 서버 코드가 계산", "재시험", "10 / 10"),
             ("다른 모델이 “제공되지 않았습니다”라고 하면 조교에게 안 넘어감", "근거 없음을 정해 둔 문구로만 판정",
              "판정 문구 추가 + 빈 칸 “010-” · 맺음말 삭제", "정상 답 오판정", "0건"),
             ("자료에 없는 내용을 지어냄", "근거 기준값이 낮음 (0.45)", "기준값을 0.60으로 올림", "없는 질문 걸러 냄", "17 / 20")]
    for i, (h, why, fix, rl, rv) in enumerate(cards):
        y = 1.8 + i * 1.6
        num(s, L, y + 0.05, i + 1)
        tx(s, L + 0.5, y, 8.3, 0.4, h, 16, F_B, INK)
        tx(s, L + 0.5, y + 0.5, 8.3, 0.75, [f"원인   {why}", f"해결   **{fix}**"], 12, F_R, MUTED, spacing=1.5)
        hline(s, L + 9.0, y + 0.05, L + 9.0, y + 1.25)
        tx(s, L + 9.2, y + 0.02, 2.6, 0.3, rl, 11, F_M, FAINT, align=PP_ALIGN.CENTER)
        tx(s, L + 9.2, y + 0.35, 2.6, 0.8, rv, 34, F_B, P, align=PP_ALIGN.CENTER)
        if i < 2:
            hline(s, L, y + 1.45, L + W, y + 1.45)
    return s


def progress(prs, no):
    s = page(prs, no, "04  진행 · 진척", "기능 33개 중 **21개**를 시작했다",
             "기준: 요구사항 정의서 v1.11 · 설계 산출물 (요구사항 v1.11, 화면설계 v1.5, DB 모델링 v1.0, API 명세 v1.0) 완료")
    x = L
    for n, c, tc in ((7, P, WHITE), (14, P2, WHITE), (12, P3, P)):
        w = W * n / 33
        rect(s, x, 1.8, w, 0.6, fill=c)
        tx(s, x, 1.8, w, 0.6, str(n), 18, F_B, tc, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        x += w
    cols = [("구현 7", P, ["질의 입력 · 근거 기반 답변", "출처 표시 · 근거 없음 응답", "원문 보기 · 통학버스 · 메뉴 위치"]),
            ("일부 구현 14", P2, ["품질 평가 (이번 주 시작)", "수집 (수동 실행)", "조교 답변 (수정 · 삭제 없음)", "관리 페이지 (임시 로그인) 등"]),
            ("미착수 12", FAINT, ["파인튜닝", "이메일 로그인 · 요약 메일", "답변 알림 · 되묻기", "추천 질문 · 대화 기록 등"])]
    cw = W / 3
    for i, (h, c, items) in enumerate(cols):
        cx = L + i * cw + (0.25 if i else 0)
        if i:
            hline(s, L + i * cw, 2.75, L + i * cw, 4.95)
        tx(s, cx, 2.75, cw - 0.4, 0.4, h, 18, F_B, c)
        tx(s, cx, 3.3, cw - 0.4, 1.7, ["·  " + t for t in items], 13, F_R, MUTED, spacing=1.45)
    quote(s, 5.45, 1.1, "가장 늦은 것은 **파인튜닝** (계획 7주차) — 효과를 비교할 평가 질문셋을 먼저 만들었다",
          "RAG 1차 완료 · 앱은 계획보다 먼저 시작 · sLLM 선정 완료")
    return s


def limits(prs, no):
    s = page(prs, no, "04  진행 · 한계", "아직 **못 한 것**부터 밝힌다")
    rows = [["평가 질문을 우리가 씀", "98.8%는 낙관적인 수치", "Q&A 게시판의 실제 질문으로 다시 측정"],
            ["기준값 0.60의 손익", "답 있는 질문 8개를 놓치고, 없는 질문 3개는 통과", "리랭커 적용 또는 기준값 조정"],
            ["“다음 학기” 같은 표현", "지난 학기 공고가 1위로 나옴", "날짜로 바꿔 검색"],
            ["지난 일정 안내", "지났다는 말 없이 9월 기간을 답함", "날짜를 코드로 비교해 표시"],
            ["데이터 갱신", "10/12 수집본 그대로", "자동 재수집 구현"],
            ["이름 가리기 · 30일 삭제", "아직 동작하지 않음", "스케줄러 구현 때 함께"]]
    table(s, L, 1.8, [3.2, 4.6, 4.09], ["문제", "내용", "대응"], rows, row_h=0.62, hl_col=2, size=13)
    return s


def plan(prs, no):
    s = page(prs, no, "04  진행 · 계획", "다음은 **실제 학생 질문**으로 다시 잰다")
    steps = [("10주", "측정", ["sLLM 답변 전체 평가", "실제 질문 추가 측정", "데이터 재수집"]),
             ("10~11주", "개선", ["리랭커 · 기준값", "임베딩 비교", "Kanana 1.5 파인튜닝"]),
             ("10~11주", "기능", ["자동 재수집", "로그인 · 메일 · 알림", "되묻기 · 마감 일정"]),
             ("12주", "구현현황 발표", ["수치와 검증 중심", "전체 흐름 시연"]),
             ("13~15주", "마무리", ["시범 운영", "판넬 · 전시", "최종보고서"])]
    cw = W / 5
    hline(s, L + cw / 2, 2.05, L + W - cw / 2, 2.05, LINE, 1.5)
    for i, (t, h, items) in enumerate(steps):
        cx = L + i * cw
        filled = i == 0
        rect(s, cx + cw / 2 - 0.13, 1.92, 0.26, 0.26, fill=P if filled else WHITE, line=P, lw=1.5, shape=MSO_SHAPE.OVAL)
        tx(s, cx, 2.35, cw, 0.3, t, 11, F_M, P if filled else FAINT, align=PP_ALIGN.CENTER)
        tx(s, cx, 2.65, cw, 0.4, h, 17, F_B, INK, align=PP_ALIGN.CENTER)
        tx(s, cx + 0.15, 3.15, cw - 0.3, 1.3, items, 12, F_R, MUTED, align=PP_ALIGN.CENTER, spacing=1.45)
    rect(s, L, 4.75, W, 1.6, fill=TINT)
    rect(s, L, 4.75, 0.09, 1.6, fill=P)
    tx(s, L + 0.5, 4.9, W - 0.8, 0.4, "8주차 계획에서 바뀐 점", 15, F_B, P)
    tx(s, L + 0.5, 5.4, W - 0.8, 0.9, ["·  조교 인터뷰와 2차 설문은 하지 않는다 → 실제 질문은 **학교 홈페이지 Q&A 게시판**에서 모은다",
                                       "·  시연 때 조교 역할은 팀원이 맡는다 (조교 답변 흐름은 시험 9/9로 검증)"], 13, F_R, INK, spacing=1.5)
    return s


def closing(prs, no):
    s = purple_slide(prs)
    tx(s, 0.8, 0.62, 7.0, 0.3, "캡스톤디자인 1조", 12, F_R, LAV)
    tx(s, 0.78, 1.5, 11.5, 1.6, ["학교 정보는 있는데", "못 찾는 문제를 풉니다"], 44, F_B, WHITE, spacing=1.15)
    hline(s, 0.78, 3.35, 1.58, 3.35, WHITE, 2.0)
    tx(s, 0.78, 3.6, 11.5, 1.0, ["모르면 지어내지 않는 AI,", "그리고 조교의 답이 쌓이는 구조로"], 24, F_R, WHITE, spacing=1.3)
    tx(s, 0.78, 5.0, 11.0, 0.4, "다음 목표: 실제 학생 질문으로 정확도를 다시 잰다", 15, F_R, LAV)
    tx(s, 0.78, 6.2, 6.0, 0.5, "감사합니다", 22, F_B, WHITE)
    tx(s, 0.78, 6.75, 7.0, 0.3, "송승현 · 이승우", 12, F_R, LAV)
    return s


FUNCS = [cover, problem, cause, scenes, pipeline, data_privacy, numbers, models, fixes, progress, limits, plan, closing]
assert len(FUNCS) == len(BASE)
SLIDES = [(fn, name, sec, script) for fn, (_, name, sec, script) in zip(FUNCS, BASE)]


def main():
    prs = Presentation(str(TEMPLATE))
    ids = prs.slides._sldIdLst
    for sid in list(ids):                      # 템플릿 슬라이드 삭제 (내장 글꼴만 남김)
        prs.part.drop_rel(sid.rId)
        ids.remove(sid)
    for i, (fn, _, _, script) in enumerate(SLIDES, 1):
        s = fn(prs, i)
        s.notes_slide.notes_text_frame.text = script
    prs.save(OUT_PPTX)

    total = sum(x[2] for x in SLIDES)
    lines = ["# 물어봐 캠퍼스 9주차 중간 현황 발표 대본", "",
             f"- 발표 자료: {OUT_PPTX.name} ({len(SLIDES)}장, 트립버짓 해커톤 발표 v6 디자인)", "- 기준: 중간현황보고서_9주차 (2026-11-10)",
             "- 구성: 해커톤_발표분석.md 2절 흐름 (문제 → 원인 → 해결 → AI 검증 → 수치 → 한계 → 마무리)",
             f"- 예상 시간: 약 {total // 60}분 {total % 60}초", "- 같은 내용이 슬라이드 발표자 노트에도 들어 있습니다.", "", "---", ""]
    for i, (_, name, sec, script) in enumerate(SLIDES, 1):
        lines += [f"## {i}. {name} (약 {sec}초)", "", script, ""]
    lines += ["---", "", "## 예상 질문 (결론 1문장 + 근거 1문장, 30초 이내)", "", "| 질문 | 답변 |", "|---|---|"] + [f"| {q} | {a} |" for q, a in QNA]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("saved", OUT_PPTX.name, len(SLIDES), "slides;", f"{total // 60}m{total % 60}s")


if __name__ == "__main__":
    main()
