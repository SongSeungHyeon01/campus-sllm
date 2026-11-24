"""캡스톤디자인 전시회 판넬 만들기.

학교가 준 샘플 판넬(05_캡스톤디자인_전시회_판넬(샘플-유원대학교).pptx)의 배경·칸·제목 띠를 그대로 쓰고,
글과 그림만 우리 프로젝트 내용으로 바꾼다. 샘플 파일은 리포에 넣지 않는다 (샘플 그림 속성에 다른 사람 이름이 있음).

사용: python build_panel.py <샘플.pptx> <출력.pptx>
그림: 문서/그림/전시회판넬/app_*.png (웹 채팅 화면, Figma 시안 색·컴포넌트 적용)
수치 출처: 문서/보고서/진행보고서/진행보고서_11주차.md
"""
import copy
import sys
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

SRC, OUT = sys.argv[1], sys.argv[2]
FIG = Path(__file__).resolve().parents[2] / "그림" / "전시회판넬"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"

# Figma 변수 색 (UI디자인_인수인계서.md 2절)
PRIMARY = RGBColor(0x2F, 0x5B, 0xD3)
CALLOUT = RGBColor(0xE5, 0xED, 0xFF)
INK = RGBColor(0x1A, 0x1D, 0x26)
MUTED = RGBColor(0x68, 0x70, 0x83)
NAVY = RGBColor(0x1F, 0x3A, 0x5F)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

prs = Presentation(SRC)
slide = prs.slides[0]
shapes = {sh.name: sh for sh in slide.shapes}

# ---------- 샘플 내용 지우기 ----------
KEEP = {"모서리가 둥근 직사각형 3", "Rectangle 21", "TextBox 4", "TextBox 151", "TextBox 175", "TextBox 81",
        "TextBox 89", "TextBox 90", "TextBox 58", "표 1", "표 57"}
KEEP |= {n for n in shapes if n.startswith("모서리가 둥근 직사각형")}
for sh in list(slide.shapes):
    if sh.name not in KEEP:
        sh._element.getparent().remove(sh._element)


# ---------- 글 상자 채우기 (샘플 서식 그대로) ----------
def _run(text, sz, bold=True, color=None):
    r = etree.SubElement(etree.Element(qn("a:p")), qn("a:r"))
    rpr = etree.SubElement(r, qn("a:rPr"), lang="ko-KR", altLang="en-US", sz=str(sz), b="1" if bold else "0", dirty="0")
    if color:
        fill = etree.SubElement(rpr, qn("a:solidFill"))
        etree.SubElement(fill, qn("a:srgbClr"), val=color)
    etree.SubElement(rpr, qn("a:latin"), typeface="+mn-ea")
    etree.SubElement(r, qn("a:t")).text = text
    return r


def _para(kind, text):
    p = etree.Element(qn("a:p"))
    if kind == "h":      # ➢ 소제목 (Wingdings Ø), 24pt
        ppr = etree.SubElement(p, qn("a:pPr"), marL="342900", indent="-342900")
        etree.SubElement(ppr, qn("a:buFont"), typeface="Wingdings", pitchFamily="2", charset="2")
        etree.SubElement(ppr, qn("a:buChar"), char="Ø")
        p.append(_run(text, 2400))
    elif kind == "b":    # • 항목, 20pt
        ppr = etree.SubElement(p, qn("a:pPr"), marL="533400", indent="-190500")
        etree.SubElement(ppr, qn("a:buFont"), typeface="Arial", pitchFamily="34", charset="0")
        etree.SubElement(ppr, qn("a:buChar"), char="•")
        p.append(_run(text, 2000))
    elif kind == "n":    # ① 번호 항목, 20pt (글머리표 없음)
        ppr = etree.SubElement(p, qn("a:pPr"), marL="533400", indent="-342900")
        etree.SubElement(ppr, qn("a:buNone"))
        p.append(_run(text, 2000))
    else:                # 빈 줄
        ppr = etree.SubElement(p, qn("a:pPr"))
        etree.SubElement(ppr, qn("a:buNone"))
        etree.SubElement(p, qn("a:endParaRPr"), lang="ko-KR", sz="1000")
    return p


def fill(shape, items, x=None, y=None, w=None):
    body = shape._element.find(qn("p:txBody"))
    for p in body.findall(qn("a:p")):
        body.remove(p)
    for kind, *text in items:
        body.append(_para(kind, text[0] if text else ""))
    bp = body.find(qn("a:bodyPr"))
    bp.set("wrap", "square")
    if x is not None:
        shape.left, shape.top, shape.width = Inches(x), Inches(y), Inches(w)


def clone_box(src, name):
    el = copy.deepcopy(src._element)
    slide.shapes._spTree.append(el)
    sh = [s for s in slide.shapes if s._element is el][0]
    sh.name = name
    return sh


def set_text(shape, text, sz=None):
    """첫 문단 첫 글자 서식을 살려 글만 바꾼다."""
    tf = shape.text_frame
    p = tf.paragraphs[0]
    runs = p.runs
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)
    if sz:
        runs[0].font.size = Pt(sz)
    for extra in tf.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)


def set_cell(cell, text):
    p = cell.text_frame.paragraphs[0]
    p.runs[0].text = text
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)


# ---------- 머리 ----------
set_text(shapes["TextBox 4"], "물어봐 캠퍼스 (Ask Campus)")
shapes["표 1"].left = Inches(13.6)
shapes["표 1"].width = Inches(8.4)
tbl = shapes["표 1"].table
tbl.columns[0].width = Inches(1.6)
tbl.columns[1].width = Inches(6.8)
set_cell(tbl.cell(0, 1), "팀원: 송승현(조장), 이승우")
sub = clone_box(shapes["TextBox 4"], "부제목")
set_text(sub, "RAG와 sLLM 기반 캠퍼스 정보 질의응답 앱", sz=28)
sub.text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT
sub.left, sub.top, sub.width = Inches(1.3), Inches(2.0), Inches(12.0)

# ---------- 1. 개요 ----------
fill(shapes["TextBox 151"], [
    ("h", "개발 목표"),
    ("b", "학교 홈페이지 자료만 근거로 학생 질문에 답하는 캠퍼스 Q&A 앱"),
    ("b", "모르는 질문은 지어내지 않고 \"찾을 수 없다\"고 답한 뒤 문의처 안내"),
    ("g",),
    ("h", "개발 배경 및 필요성"),
    ("b", "학교 정보는 있는데 게시판마다 흩어져 있어 찾기 어려움"),
    ("b", "포털 검색은 단어가 맞아야 나오고, 범용 AI는 학교 최신 공지를 모름"),
    ("b", "사전 설문(9명): 포털이 불편하다 78%, 앱을 쓰겠다 89%"),
    ("g",),
    ("h", "개발 방향"),
    ("b", "학교 사이트 수집 → 검색(RAG) → sLLM 답변"),
    ("b", "날짜·시간 계산은 코드가, 문장은 sLLM이 맡고 코드가 다시 검사"),
    ("b", "모델을 노트북에서 실행해 질문이 외부로 나가지 않음"),
], 1.0, 4.95, 9.8)

# ---------- 2. 개발 환경 및 주요 기능 ----------
fill(shapes["TextBox 175"], [
    ("h", "개발 환경"),
    ("b", "서버: Python FastAPI, SQLite, 관리 웹(Jinja2)"),
    ("b", "검색: KURE-v1 임베딩 + Chroma 벡터 DB"),
    ("b", "답변 모델: A.X 4.0 Light 7B 4bit (RTX 5060 8GB)"),
    ("b", "화면: Android(Kotlin), 웹 채팅, Figma 디자인"),
    ("g",),
    ("h", "수집 자료 (청크 3,135개)"),
    ("b", "학교 사이트 메뉴, 학과·대학원 사이트 31곳, 공지, FAQ·Q&A"),
    ("b", "공모전: 충청남도 OPEN API, 네이버 뉴스 검색 API"),
    ("g",),
    ("h", "주요 기능"),
    ("b", "근거 기반 답변 + 출처·메뉴 위치·원문 보기"),
    ("b", "되묻기: 애매한 질문에 선택지 (주제·학과·정류장)"),
    ("b", "코드 계산: 통학버스 다음 차, 학식, 학사일정, 동아리"),
    ("b", "관리 웹: 답변 대기, FAQ, 답변 피드백, 질문 기록"),
], 11.8, 4.95, 9.7)

# ---------- 3. 개발 내용 및 과정 ----------
set_text(shapes["TextBox 89"], "전체 구성도")
shapes["TextBox 89"].left, shapes["TextBox 89"].top = Inches(1.04), Inches(12.3)
set_text(shapes["TextBox 58"], "답변 과정")
shapes["TextBox 58"].left, shapes["TextBox 58"].top = Inches(11.8), Inches(12.3)

steps = clone_box(shapes["TextBox 151"], "답변 과정 본문")
fill(steps, [
    ("n", "① 되묻기: 조건이 빠진 질문은 선택지로 되물음"),
    ("n", "② FAQ: 관리자가 등록한 답과 비슷하면 그 답"),
    ("n", "③ 코드 계산: 통학버스·학식·학사일정 날짜"),
    ("n", "④ 검색: 유사도 0.55 미만이면 답하지 않음"),
    ("n", "⑤ sLLM: 찾은 근거에 있는 내용만으로 답"),
    ("n", "⑥ 검사: 근거에 없는 숫자가 든 문장 삭제"),
    ("n", "⑦ 출처 최대 3개 + 원문 보기 + 메뉴 위치"),
    ("g",),
    ("h", "모델 선정 (11/17)"),
    ("b", "한국어 소형 모델 13개를 108문항으로 비교"),
    ("b", "A.X 4.0 Light: 63문항 중 62개 정답, 평균 2.1초"),
    ("g",),
    ("h", "개인정보 보호"),
    ("b", "로그인 없이 사용, 질문 속 전화번호·학번 가림"),
    ("b", "수집 자료의 이름·휴대폰·비밀번호 가림"),
], 11.8, 12.85, 9.7)


def box(x, y, w, h, text, fill_c, line_c, color, sz=16, bold=True):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.adjustments[0] = 0.18
    s.fill.solid()
    s.fill.fore_color.rgb = fill_c
    s.line.color.rgb = line_c
    s.line.width = Pt(1.5)
    s.shadow.inherit = False
    tf = s.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = Inches(0.08)
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = ln
        r.font.size = Pt(sz if i == 0 else sz - 2)
        r.font.bold = bold if i == 0 else False
        r.font.color.rgb = color
    return s


def arrow(x1, y1, x2, y2, both=False):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = NAVY
    c.line.width = Pt(2.25)
    ln = c.line._get_or_add_ln()
    etree.SubElement(ln, qn("a:tailEnd"), type="triangle", w="med", len="med")
    if both:
        etree.SubElement(ln, qn("a:headEnd"), type="triangle", w="med", len="med")
    return c


def label(x, y, w, text, sz=14):
    t = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(0.35))
    t.text_frame.margin_left = t.text_frame.margin_right = 0
    p = t.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    r = p.add_run()
    r.text = text
    r.font.size = Pt(sz)
    r.font.bold = True
    r.font.color.rgb = MUTED


# 구성도: 왼쪽 반 (x 1.2 ~ 10.5, y 12.95 ~ 21.25)
L, R = 1.25, 10.45
box(L, 12.95, 4.2, 1.0, "학생\nAndroid 앱 · 웹 채팅", PRIMARY, PRIMARY, WHITE, 18)
box(R - 4.2, 12.95, 4.2, 1.0, "관리자\n관리 웹 (답변 대기·FAQ)", WHITE, NAVY, INK, 18)
arrow(L + 2.1, 13.95, L + 2.1, 14.55, both=True)
label(L + 2.25, 14.05, 2.5, "질문 / 답·출처")
arrow(R - 2.1, 13.95, R - 2.1, 14.55, both=True)

srv = box(L, 14.55, R - L, 3.15, "", CALLOUT, NAVY, INK)
t = slide.shapes.add_textbox(Inches(L + 0.15), Inches(14.62), Inches(5), Inches(0.4))
r = t.text_frame.paragraphs[0].add_run()
r.text = "서버 (Python FastAPI)"
r.font.size, r.font.bold, r.font.color.rgb = Pt(18), True, NAVY
chips = ["① 되묻기", "② FAQ 확인", "③ 코드 계산", "④ 벡터 검색", "⑤ sLLM 답변", "⑥ 근거 숫자 검사"]
cw, gap = 2.8, 0.2
for i, c in enumerate(chips):
    cx = L + 0.25 + (i % 3) * (cw + gap)
    cy = 15.25 + (i // 3) * 1.15
    box(cx, cy, cw, 0.9, c, WHITE, PRIMARY, PRIMARY, 17)
for i in range(2):
    for j in range(2):
        x0 = L + 0.25 + (j + 1) * cw + j * gap
        arrow(x0, 15.25 + i * 1.15 + 0.45, x0 + gap, 15.25 + i * 1.15 + 0.45)

bw = (R - L - 0.4) / 3
row3 = 18.35
box(L, row3, bw, 1.15, "벡터 DB\nChroma + KURE-v1", WHITE, NAVY, INK, 16)
box(L + bw + 0.2, row3, bw, 1.15, "SQLite\n질문 기록·FAQ·답변 대기", WHITE, NAVY, INK, 16)
box(L + 2 * (bw + 0.2), row3, bw, 1.15, "sLLM\nA.X 4.0 Light 4bit", WHITE, NAVY, INK, 16)
for k in range(3):
    xm = L + k * (bw + 0.2) + bw / 2
    arrow(xm, 17.7, xm, row3, both=True)

row4 = 20.15
box(L, row4, 5.9, 1.0, "수집기 (매일·매주 재수집 예약)\n학교 홈페이지 · 학과 사이트 31곳 · FAQ·Q&A", WHITE, MUTED, INK, 16)
box(L + 6.1, row4, R - L - 6.1, 1.0, "공모전 API\n충청남도 · 네이버", WHITE, MUTED, INK, 16)
arrow(L + bw / 2, row4, L + bw / 2, row3 + 1.15)
label(L + bw / 2 + 0.15, 19.65, 3, "청킹·임베딩")
gx = L + 2 * bw + 0.3          # SQLite와 sLLM 칸 사이 틈으로 서버까지
arrow(gx, row4, gx, 17.7)
label(gx + 0.15, 19.65, 2.5, "질문할 때 조회")

# ---------- 4. 개발 결과 ----------
# Figma 시안 화면 (문서/그림/전시회판넬/figma_*.png, 바깥 검은 배경은 투명으로 처리함). 화면 속 값은 예시
set_text(shapes["TextBox 90"], "화면 디자인 (Figma 시안, 화면 속 값은 예시)")
shapes["TextBox 90"].left, shapes["TextBox 90"].top = Inches(1.0), Inches(22.95)
shots = [("figma_00_start.png", "시작 화면"), ("figma_02_home.png", "첫 화면·추천 질문"),
         ("figma_04_answer.png", "답변과 출처"), ("figma_06_clarify_stop.png", "되묻기 (정류장)")]
iw = 2.15
ih = iw * 1300 / 600
x0, gap = 1.15, (9.4 - 4 * iw) / 3
for i, (f, cap) in enumerate(shots):
    x = x0 + i * (iw + gap)
    slide.shapes.add_picture(str(FIG / f), Inches(x), Inches(23.85), Inches(iw), Inches(ih))
    t = slide.shapes.add_textbox(Inches(x - 0.2), Inches(23.95 + ih), Inches(iw + 0.4), Inches(0.4))
    p = t.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = cap
    r.font.size, r.font.bold, r.font.color.rgb = Pt(15), True, INK

# ---------- 5. 결론 ----------
fill(shapes["TextBox 81"], [
    ("h", "평가 결과 (11/22~23 측정)"),
    ("b", "개발자 작성 108문항: 답 있는 질문 78/84"),
    ("b", "같은 108문항 중 자료에 없는 질문 거르기 11/16"),
    ("b", "학교 Q&A 기반 처음 보는 질문 20개: 맞음 5, 부분 11, 틀림 4"),
    ("b", "통학버스 시간 계산 12/12, sLLM 답변 평균 3.7초"),
    ("g",),
    ("h", "결론"),
    ("b", "학교 자료만 근거로 출처와 함께 답하고, 모르면 지어내지 않음"),
    ("b", "노트북 GPU에서 실행해 외부 AI 요금 0원"),
    ("g",),
    ("h", "남은 과제"),
    ("b", "처음 보는 질문의 정확도, 자료에 없는 질문 거르기"),
    ("b", "첨부파일(PDF·HWP) 본문 검색"),
    ("b", "추천 질문·마감 일정·설정 화면 (미구현)"),
], 11.8, 22.95, 9.7)

# 지운 샘플 그림이 파일 안에 남지 않게, 슬라이드에서 더 쓰지 않는 연결을 끊는다
xml = etree.tostring(slide._element).decode()
for rid, rel in list(slide.part.rels.items()):
    if rel.reltype.endswith("/image") and f'"{rid}"' not in xml:
        slide.part.drop_rel(rid)

prs.save(OUT)
print("저장", OUT)
