"""중간현황보고서_9주차.md 내용으로 발표 자료(pptx)와 대본(md)을 만든다.

구성은 구현현황발표_준비/해커톤_발표분석.md 2절 흐름을 따른다:
문제(훅) → 원인·비교 → 해결 장면 → AI 검증 → 데이터·개인정보 → 직접 잰 수치 → 고친 사례 → 진척 → 한계 → 계획 → 마무리.
사용: python build_deck_9w.py
"""
import sys
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches

ROOT = Path(__file__).resolve().parents[3]   # 문서/작업/<폴더>/이 파일 → 리포 최상위
sys.path.insert(0, str(ROOT / "DB모델링_작업"))
from build_db_doc import INK, LINE, MUTED, MX, NAVY, SH, SW, TINT, WHITE, badge, box, new, rgb, table, text, title  # noqa: E402

FIG = ROOT / "문서" / "07_진행보고서" / "그림_중간현황"
OUT_PPTX = ROOT / "문서" / "07_진행보고서" / "중간현황_9주차_발표자료.pptx"
OUT_MD = ROOT / "문서" / "07_진행보고서" / "중간현황_9주차_발표대본.md"

GREEN, BLUE, CORAL, GRAY = rgb("2E7D5B"), rgb("2A6F97"), rgb("C8553D"), rgb("8A929E")
LIGHT = rgb("CADCFC")
I = Inches
FULL = SW - 2 * MX


def tile(s, x, y, w, h, big, label, color=NAVY, big_size=36):
    box(s, x, y, w, h, TINT)
    text(s, x + I(0.2), y + I(0.15), w - I(0.4), I(0.85), big, size=big_size, bold=True, color=color)
    text(s, x + I(0.2), y + h - I(0.75), w - I(0.4), I(0.65), label.split("\n"), size=13, color=MUTED)


def picture(s, path, x, y, h):
    im = Image.open(path)
    w = int(h * im.width / im.height)
    s.shapes.add_picture(str(path), x, y, w, h)
    return w


def cover(prs, no):
    s = new(prs, dark=True)
    text(s, MX, I(1.3), I(11), I(0.5), "물어봐 캠퍼스 (Ask Campus)", size=20, color=LIGHT)
    text(s, MX, I(1.9), I(12), I(1.2), "중간 현황 발표", size=56, bold=True, color=WHITE, name="Title")
    text(s, MX, I(3.25), I(12), I(0.5), "RAG와 sLLM 기반 캠퍼스 정보 질의응답 앱", size=20, color=WHITE)
    text(s, MX, I(5.5), I(11), I(0.9), ["캡스톤디자인 1조 · 송승현 · 이승우", "계획 15주 중 9주차 · 2026-11-10 기준"], size=15, color=LIGHT)
    return s


def problem(prs, no):
    s = new(prs)
    title(s, "학교 정보는 있는데, 못 찾는다", "기숙사 신청 기간, 포털에서 한 번에 찾아보신 적 있으신가요?", no)
    w = I(3.9)
    tile(s, MX, I(1.8), w, I(2.0), "78%", "포털이 불편하다 (검색·메뉴)\n1차 사전 설문 9명", CORAL, 44)
    tile(s, MX + w + I(0.25), I(1.8), w, I(2.0), "89%", "이런 앱을 쓰겠다\n1차 사전 설문 9명", GREEN, 44)
    tile(s, MX + 2 * (w + I(0.25)), I(1.8), w - I(0.02), I(2.0), "6곳", "자료를 모아 온 메뉴 수\n공지 게시판 3곳, 학사일정, 통학버스, 동아리", NAVY, 44)
    box(s, MX, I(4.2), FULL, I(1.9), TINT)
    text(s, MX + I(0.3), I(4.35), FULL - I(0.6), I(0.45), "예: 신입생이 시험 기간에 알고 싶은 것", size=17, bold=True, color=NAVY)
    text(s, MX + I(0.3), I(4.85), FULL - I(0.6), I(1.2),
         ["· \"기말고사 언제야?\" → 학사일정 메뉴를 알아야 함",
          "· \"폐강된 과목 언제 정정해?\" → 학사공지 게시판을 뒤져야 함"], size=16)
    text(s, MX, I(6.3), FULL, I(0.5), "설문은 응답 9명, 모두 아산캠퍼스라 방향 참고용입니다.", size=13, color=MUTED)
    return s


def cause(prs, no):
    s = new(prs)
    title(s, "왜 기존 방식으로는 안 되나", "포털은 말을 못 알아듣고, 범용 AI는 우리 학교를 모릅니다", no)
    rows = [["우리 학교 최신 자료", "O (흩어져 있음)", "X", "O (한곳에 모아 검색)"],
            ["말로 묻기", "X (단어가 맞아야 함)", "O", "O"],
            ["출처·원문 확인", "O", "X", "O (출처 3개, 원문, 메뉴 위치)"],
            ["모를 때", "결과 없음", "지어낼 수 있음", "\"찾을 수 없습니다\" + 조교에게"],
            ["질문이 외부로 나감", "해당 없음", "나감", "안 나감 (노트북에서 실행)"]]
    table(s, MX, I(1.7), FULL, ["비교", "포털 검색", "범용 AI (ChatGPT 등)", "물어봐 캠퍼스"], rows, [2.6, 2.8, 2.8, 3.9], size=15, row_h=0.72)
    text(s, MX, I(6.15), FULL, I(0.6), "핵심 차이: 학교 자료만 근거로 답하고, 모르면 지어내지 않고 사람에게 넘깁니다.", size=16, bold=True, color=NAVY)
    return s


def scenes(prs, no):
    s = new(prs)
    title(s, "해결: 이렇게 동작합니다", "장면 3개로 보는 물어봐 캠퍼스", no)
    h = I(4.6)
    w1 = picture(s, FIG / "app_answer.png", MX, I(1.6), h)
    w2 = picture(s, FIG / "app_notfound.png", MX + w1 + I(0.2), I(1.6), h)
    x = MX + w1 + w2 + I(0.5)
    w = SW - MX - x
    items = [("1", "\"2학기 기말고사 언제야?\"", "학사일정에서 찾아 \"12월 8일~14일\"로 답하고 출처·원문을 붙임", NAVY),
             ("2", "\"기숙사 신청 언제 해?\" (자료 없음)", "\"찾을 수 없습니다\" → 답변 대기 등록 → 조교 답변이 FAQ로 반영", CORAL),
             ("3", "\"두정역인데 가장 빠른 버스?\"", "현재 시각·요일로 서버 코드가 다음 차를 계산 (AI 안 씀)", GREEN)]
    for i, (n, q, a, c) in enumerate(items):
        y = I(1.6) + i * I(1.55)
        box(s, x, y, w, I(1.4), TINT)
        badge(s, x + I(0.15), y + I(0.15), I(0.45), n, c, size=14)
        text(s, x + I(0.75), y + I(0.1), w - I(0.9), I(0.45), q, size=15, bold=True, color=INK)
        text(s, x + I(0.75), y + I(0.55), w - I(0.9), I(0.8), a, size=13, color=MUTED)
    text(s, MX, I(6.3), FULL, I(0.5), "왼쪽: 답변·출처·원문 보기 / 가운데: 자료에 없는 질문은 조교에게 전달", size=13, color=MUTED)
    return s


def pipeline(prs, no):
    s = new(prs)
    title(s, "AI가 틀리면 어떻게 막나", "AI는 찾고 문장을 만드는 데만 쓰고, 계산과 판정은 코드가 맡습니다", no)
    steps = [("① 검색", "점수 0.60 미만은\n답하지 않음", NAVY, False),
             ("② 계산은 코드", "버스 다음 차는\n코드가 계산", GREEN, True),
             ("③ sLLM 답변", "근거 자료에 있는\n내용만 쓰도록 지시", NAVY, False),
             ("④ 후처리", "\"모름\" 표현 판정\n빈 칸·맺음말 삭제", GREEN, True),
             ("⑤ 출처 표시", "출처 3개, 원문,\n홈페이지 메뉴 위치", NAVY, False),
             ("⑥ 사람이 답함", "근거 없으면 조교가\n답해 FAQ로 반영", CORAL, False)]
    w, gap = I(1.86), I(0.19)
    for i, (h, d, c, star) in enumerate(steps):
        x = MX + i * (w + gap)
        box(s, x, I(1.85), w, I(2.1), c)
        text(s, x + I(0.08), I(1.95), w - I(0.16), I(0.5), h, size=16, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        text(s, x + I(0.08), I(2.5), w - I(0.16), I(1.3), d.split("\n"), size=13, color=WHITE, align=PP_ALIGN.CENTER)
        if i < 5:
            box(s, x + w + I(0.02), I(2.75), I(0.15), I(0.3), LINE, shape=MSO_SHAPE.RIGHT_ARROW)
    text(s, MX, I(4.1), FULL, I(0.4), "초록색 ②·④는 실제 오답을 겪은 뒤 추가한 단계입니다.", size=14, color=GREEN, bold=True)
    w2 = I(5.95)
    tile(s, MX, I(4.7), w2, I(1.6), "0원", "질문 1건당 외부 AI 요금\n모델을 노트북 GPU에서 직접 실행 (전기료는 미측정)", NAVY, 36)
    tile(s, MX + w2 + I(0.23), I(4.7), w2, I(1.6), "17 / 20", "자료에 없는 질문을 ① 단계에서 걸러 낸 수\n평가 질문셋 기준", GREEN, 36)
    return s


def data_privacy(prs, no):
    s = new(prs)
    title(s, "데이터 출처와 개인정보", "공개 페이지만 수집하고, 학생을 식별하는 정보는 저장하지 않습니다", no)
    table(s, MX, I(1.65), I(6.3), ["자료", "분량"], [["학사·일반·장학 공지", "게시판마다 최근 20건"], ["학사일정", "일정 66건"],
                                                   ["통학버스 (영동·아산)", "페이지 4개, 주말·방학 포함"], ["동아리현황", "1페이지"]],
          [2.6, 3.7], size=14, row_h=0.6)
    text(s, MX, I(4.75), I(6.3), I(1.5), ["· 출처: 학교 홈페이지 공개 페이지 (로그인 페이지 제외)", "· 청크 154개, 수집일 10/12",
                                          "· 약점: 자동 재수집이 없어 그 뒤로 갱신 안 됨"], size=14)
    x = MX + I(6.6)
    w = SW - MX - x
    rows = [["로그인 없음, 이름·학번·기기 ID 칸 없음", "O"], ["질문이 외부 AI로 나가지 않음", "O"], ["저장 전 전화번호·학번 가림", "O"],
            ["질문 속 이름 가림", "X (예정)"], ["답변 대기 30일 뒤 삭제", "X (예정)"]]
    table(s, x, I(1.65), w, ["개인정보 원칙", "구현"], rows, [4.3, 1.3], size=14, row_h=0.6)
    return s


def numbers(prs, no):
    s = new(prs)
    title(s, "직접 잰 수치 (11/10)", "평가 질문 108개를 만들어 처음으로 정확도를 쟀습니다", no)
    w = I(2.85)
    data = [("98.8%", "검색 정확도 79/80\n목표 80%", GREEN), ("9 / 9", "조교 답변 흐름\n등록부터 FAQ 답변까지", GREEN),
            ("10 / 10", "통학버스 시간 계산\n시각·요일을 바꿔 시험", GREEN), ("2.1~3.5초", "sLLM 평균 답변 시간\n목표 평균 5초", GREEN)]
    for i, (b, l, c) in enumerate(data):
        tile(s, MX + i * (w + I(0.243)), I(1.7), w, I(1.95), b, l, c, 34)
    table(s, MX, I(3.95), I(6.6), ["근거 기준값", "답 있는 질문 살림", "없는 질문 걸러 냄"],
          [["0.56", "76/80", "13/20"], ["0.60 (현재)", "72/80", "17/20"], ["0.64", "61/80", "20/20"]], [2.2, 2.2, 2.2], size=14, row_h=0.5)
    x = MX + I(6.9)
    box(s, x, I(3.95), SW - MX - x, I(2.35), TINT)
    text(s, x + I(0.2), I(4.05), SW - MX - x - I(0.4), I(0.45), "주의할 점", size=16, bold=True, color=CORAL)
    text(s, x + I(0.2), I(4.5), SW - MX - x - I(0.4), I(1.8),
         ["· 질문을 우리가 자료를 보며 써서 낙관적인 수치", "· 실제 학생 질문으로는 아직 안 잼", "· 기준값 0.60에서 답 있는 질문 8개를 놓침"], size=14)
    return s


def models(prs, no):
    s = new(prs)
    title(s, "sLLM 비교: Kanana 1.5를 유지합니다", "Hugging Face 후보 3개를 같은 질문 19개, 같은 조건(원본 bf16)으로 시험", no)
    table(s, MX, I(1.65), FULL, ["모델", "답 있는 질문 (12)", "자료에 없는 질문 (4)", "평균 생성 시간", "라이선스"],
          [["Kanana 1.5 2.1B (현재)", "12", "4", "2.1초", "Apache-2.0"], ["Midm 2.0 Mini (KT)", "11", "4", "2.4초", "MIT"],
           ["Kanana-2 3B (카카오, 최신)", "8", "4", "1.65초", "전용 (표시 의무)"]], [3.4, 2.2, 2.4, 2.0, 2.1], size=15, row_h=0.6)
    table(s, MX, I(4.3), FULL, ["\"학습법 공모전 총 상금 얼마야?\"", "답변"],
          [["Kanana 1.5", "대상 30만원, 최우수상 2명 각 20만원, 우수상 3명 각 10만원 (정답)"],
           ["Midm 2.0 Mini", "총 상금은 90만원입니다 (오답, 실제 합계 100만원)"],
           ["Kanana-2 3B", "해당 정보를 찾을 수 없습니다 (자료에 있음)"]], [3.4, 8.7], size=14, row_h=0.5)
    text(s, MX, I(6.45), FULL, I(0.5), "Qwen3.5 2B는 아직 시험하지 못했습니다. 질문 19개라 평가 질문셋 전체로 다시 확인합니다.", size=13, color=MUTED)
    return s


def fixes(prs, no):
    s = new(prs)
    title(s, "시험에서 찾은 오답과 해결", "원인을 찾아 고치고 다시 시험했습니다", no)
    cards = [("\"가장 빠른 버스\"에 10:15로 답함 (08:00이 맞음)",
              ["원인: 시간표 일부만 검색, 현재 시각 미전달, 2B 모델의 시간 비교 한계", "해결: 시간표 조회는 코드가 계산"], "재시험 10 / 10"),
             ("다른 모델이 \"제공되지 않았습니다\"라고 하면 조교에게 안 넘어감",
              ["원인: 근거 없음을 정해 둔 문구로만 판정", "해결: 판정 문구 추가 + 빈 칸 \"010-\"·맺음말 삭제"], "정상 답 오판정 0건"),
             ("자료에 없는 내용을 지어냄",
              ["원인: 근거 기준값이 낮음 (0.45)", "해결: 0.60으로 올림"], "없는 질문\n17 / 20 걸러 냄")]
    for i, (h, body, res) in enumerate(cards):
        y = I(1.65) + i * I(1.55)
        box(s, MX, y, I(9.0), I(1.4), TINT)
        badge(s, MX + I(0.15), y + I(0.15), I(0.45), str(i + 1), CORAL, size=14)
        text(s, MX + I(0.75), y + I(0.08), I(8.1), I(0.45), h, size=15, bold=True, color=NAVY)
        text(s, MX + I(0.75), y + I(0.5), I(8.1), I(0.85), body, size=13)
        box(s, MX + I(9.2), y, SW - 2 * MX - I(9.2), I(1.4), GREEN)
        text(s, MX + I(9.3), y, SW - 2 * MX - I(9.4), I(1.4), res, size=16, bold=True, color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, MX, I(6.4), FULL, I(0.5), "개발 중 문제 8건의 원인과 해결 과정을 모두 오류 보고서로 남겼습니다.", size=13, color=MUTED)
    return s


def progress(prs, no):
    s = new(prs)
    title(s, "진척: 기능 33개 중 21개 착수", "설계 산출물은 끝났고, 파인튜닝이 가장 늦었습니다", no)
    total, x, y = 33, MX, I(1.7)
    for n, c in ((7, GREEN), (14, BLUE), (12, GRAY)):
        w = int(FULL * n / total)
        box(s, x, y, w, I(0.55), c, shape=MSO_SHAPE.RECTANGLE)
        text(s, x, y, w, I(0.55), str(n), size=18, bold=True, color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        x += w
    cols = [("구현 7", GREEN, ["질의 입력, 근거 기반 답변", "출처 표시, 근거 없음 응답", "원문 보기, 통학버스, 메뉴 위치"]),
            ("일부 구현 14", BLUE, ["품질 평가 (이번에 시작)", "수집 (수동 실행)", "조교 답변 (수정·삭제 없음)", "관리 페이지 (임시 로그인) 등"]),
            ("미착수 12", GRAY, ["파인튜닝", "이메일 로그인, 요약 메일", "답변 알림, 되묻기", "추천 질문, 대화 기록 등"])]
    w = I(3.87)
    for i, (h, c, items) in enumerate(cols):
        cx = MX + i * (w + I(0.26))
        box(s, cx, I(2.5), w, I(2.75), TINT)
        text(s, cx + I(0.2), I(2.6), w - I(0.4), I(0.5), h, size=18, bold=True, color=c)
        text(s, cx + I(0.2), I(3.15), w - I(0.4), I(2.0), ["· " + t for t in items], size=14)
    text(s, MX, I(5.5), FULL, I(0.9), ["설계 산출물: 요구사항 정의서 v1.11, 화면설계서 v1.5, DB 모델링 v1.0, API 명세서 v1.0 완료",
                                       "일정: RAG 1차 완료 · 앱은 계획보다 먼저 시작 · sLLM 선정 완료 · 파인튜닝 지연 (계획 7주차)"], size=14, color=MUTED)
    return s


def limits(prs, no):
    s = new(prs)
    title(s, "한계와 남은 문제", "먼저 밝히고, 대응 계획을 붙였습니다", no)
    rows = [("평가 질문이 우리가 쓴 질문", "98.8%는 낙관적인 수치", "Q&A 게시판의 실제 질문으로 다시 측정"),
            ("기준값 0.60의 손익", "답 있는 질문 8개를 놓치고, 없는 질문 3개는 통과", "리랭커 적용 또는 기준값 조정"),
            ("\"다음 학기\" 같은 표현", "지난 학기 공고가 1위로 나옴", "날짜로 바꿔 검색"),
            ("지난 일정 안내", "지났다는 말 없이 9월 기간을 답함", "날짜를 코드로 비교해 표시"),
            ("데이터 갱신", "10/12 수집본 그대로", "자동 재수집 구현"),
            ("이름 가리기, 30일 삭제", "아직 동작하지 않음", "스케줄러 구현 때 함께")]
    table(s, MX, I(1.65), FULL, ["문제", "내용", "대응"], [list(r) for r in rows], [3.3, 4.5, 4.3], size=14, row_h=0.68)
    return s


def plan(prs, no):
    s = new(prs)
    title(s, "앞으로의 계획", "실제 학생 질문으로 다시 재고, 그 결과로 개선합니다", no)
    steps = [("10주", "측정", ["sLLM 답변 전체 평가", "실제 질문 추가 측정", "데이터 재수집"], NAVY),
             ("10~11주", "개선", ["리랭커, 기준값", "임베딩 비교", "Kanana 1.5 파인튜닝"], NAVY),
             ("10~11주", "기능", ["자동 재수집", "로그인·메일·알림", "되묻기, 마감 일정"], BLUE),
             ("12주", "구현현황 발표", ["수치와 검증 중심", "전체 흐름 시연"], CORAL),
             ("13~15주", "마무리", ["시범 운영", "판넬·전시", "최종보고서"], GRAY)]
    w, gap = I(2.27), I(0.195)
    for i, (t, h, items, c) in enumerate(steps):
        x = MX + i * (w + gap)
        box(s, x, I(1.7), w, I(0.6), c)
        text(s, x, I(1.7), w, I(0.6), t, size=16, bold=True, color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        box(s, x, I(2.4), w, I(2.2), TINT)
        text(s, x + I(0.12), I(2.5), w - I(0.24), I(0.45), h, size=16, bold=True, color=NAVY)
        text(s, x + I(0.12), I(3.0), w - I(0.24), I(1.6), ["· " + a for a in items], size=14)
    box(s, MX, I(4.85), FULL, I(1.5), TINT)
    text(s, MX + I(0.25), I(4.95), FULL - I(0.5), I(0.45), "8주차 계획에서 바뀐 점", size=16, bold=True, color=CORAL)
    text(s, MX + I(0.25), I(5.4), FULL - I(0.5), I(0.9),
         ["· 조교 인터뷰와 2차 설문은 하지 않습니다. 실제 질문은 홈페이지 Q&A 게시판에서 모읍니다",
          "· 시연 때 조교 역할은 팀원이 맡습니다 (조교 답변 흐름은 시험 9/9로 검증)"], size=14)
    return s


def closing(prs, no):
    s = new(prs, dark=True)
    text(s, MX, I(1.5), I(12), I(0.9), "정리", size=40, bold=True, color=WHITE, name="Title")
    text(s, MX, I(2.6), I(12), I(1.0), "학교 정보는 있는데 못 찾는 문제를,", size=26, color=WHITE)
    text(s, MX, I(3.2), I(12), I(1.0), "모르면 지어내지 않는 AI와 조교의 답이 쌓이는 구조로 풉니다.", size=26, bold=True, color=WHITE)
    text(s, MX, I(4.4), I(12), I(0.8), "다음은 실제 학생 질문으로 정확도를 다시 재는 것입니다.", size=18, color=LIGHT)
    text(s, MX, I(5.5), I(12), I(0.6), "감사합니다", size=24, bold=True, color=LIGHT)
    return s


SLIDES = [
    (cover, "표지", 10, "안녕하세요, 캡스톤디자인 1조입니다. 물어봐 캠퍼스의 9주차 중간 현황을 발표하겠습니다."),
    (problem, "문제", 40, "혹시 기숙사 신청 기간을 포털에서 한 번에 찾아보신 적 있으신가요? 저희가 본 문제는 한 문장입니다. 학교 정보는 있는데, 못 찾는다는 것입니다. 1차 설문에서 78%가 포털 검색과 메뉴가 불편하다고 했고, 89%가 이런 앱을 쓰겠다고 했습니다. 실제로 자료를 모아 보니 공지는 게시판 세 곳에, 학사일정과 통학버스는 각각 다른 메뉴에 흩어져 있었습니다. 다만 설문은 9명, 모두 아산캠퍼스라 방향 참고용입니다."),
    (cause, "원인과 비교", 35, "그럼 포털 검색이나 ChatGPT로 되지 않을까요? 포털은 단어가 맞아야 찾을 수 있고, ChatGPT는 우리 학교 최신 공지와 버스 시간표를 모릅니다. 물어봐 캠퍼스는 학교 자료만 근거로 말로 물을 수 있고, 출처와 원문을 함께 보여 줍니다. 그리고 모르면 지어내지 않고 조교에게 넘깁니다."),
    (scenes, "해결 장면", 45, "실제 동작을 장면 세 개로 보여 드리겠습니다. 첫째, 2학기 기말고사 언제야라고 물으면 학사일정에서 찾아 12월 8일부터 14일까지라고 답하고 출처와 원문을 붙입니다. 둘째, 자료에 없는 기숙사 신청을 물으면 찾을 수 없다고 답하고 질문을 조교에게 넘깁니다. 조교가 답하면 같은 질문에 바로 그 답이 나갑니다. 셋째, 두정역에서 가장 빠른 버스를 물으면 현재 시각과 요일로 서버 코드가 다음 차를 계산합니다."),
    (pipeline, "AI 검증", 45, "AI가 틀리면 어떻게 막는지입니다. AI는 비슷한 자료를 찾고 문장을 만드는 데만 쓰고, 계산과 판정은 코드가 맡습니다. 검색 점수가 0.60보다 낮으면 답하지 않고, 버스 시간은 코드가 계산하고, 모델이 모른다고 하면 조교에게 넘기고, 항상 출처를 보여 줍니다. 초록색 두 단계는 실제로 오답을 겪은 뒤 추가한 단계입니다. 모델을 노트북에서 직접 돌려 질문 1건당 외부 AI 요금은 0원입니다."),
    (data_privacy, "데이터·개인정보", 30, "데이터는 학교 홈페이지 공개 페이지에서만 모았고, 공지, 학사일정, 통학버스, 동아리 자료로 청크 154개입니다. 다만 10월 12일 수집본이라 자동 재수집이 필요합니다. 학생은 로그인 없이 쓰고, 서버에 이름이나 학번 칸이 없으며, 질문이 외부 AI로 나가지 않습니다. 질문 속 이름 가리기와 30일 삭제는 아직 구현하지 못해 계획에 넣었습니다."),
    (numbers, "직접 잰 수치", 45, "이번 주에 평가 질문 108개를 만들어 처음으로 정확도를 쟀습니다. 정답 근거가 검색 결과 상위 3개 안에 든 비율이 98.8%로 목표 80%를 넘었습니다. 조교 답변 흐름 9개와 버스 시간 계산 10개도 모두 통과했고, 답변 시간은 평균 2에서 3.5초입니다. 다만 질문을 저희가 자료를 보며 썼기 때문에 낙관적인 수치이고, 기준값 0.60에서는 답이 있는 질문 8개를 놓친다는 것도 함께 확인했습니다."),
    (models, "모델 비교", 40, "답변 모델도 비교했습니다. Hugging Face에서 노트북 GPU에 올라가고 한국어를 하는 모델 세 개를 골라 같은 질문, 같은 조건으로 시험했습니다. 지금 쓰는 Kanana 1.5가 12개를 모두 맞혔고, Midm은 상금 합계를 90만원으로 잘못 계산했고, 최신 Kanana-2는 자료에 있는 답을 모른다고 했습니다. 그래서 Kanana 1.5를 유지합니다."),
    (fixes, "고친 사례", 40, "시험에서 찾아 고친 오답입니다. 가장 빠른 버스에 8시 차가 아니라 10시 15분 차를 답했는데, 모델이 시간 비교를 못 해서 시간표는 코드가 계산하도록 바꿨습니다. 모델을 비교하다 다른 모델이 제공되지 않았다고 답하면 조교에게 안 넘어가는 문제도 찾아 고쳤습니다. 자료에 없는 내용을 지어내던 문제는 기준값을 올려 해결했습니다. 문제 8건의 원인과 해결을 모두 기록했습니다."),
    (progress, "진척", 30, "기능 요구사항 33개 중 7개를 구현했고, 이번에 품질 평가를 시작해 일부 구현이 14개, 미착수가 12개입니다. 설계 산출물은 모두 끝났고, 가장 늦은 것은 파인튜닝입니다."),
    (limits, "한계", 35, "한계를 먼저 말씀드리겠습니다. 평가 질문을 저희가 썼기 때문에 실제 학생 질문으로 다시 재야 합니다. 기준값 0.60은 답 있는 질문 일부를 놓칩니다. 다음 학기 같은 표현, 지난 일정 안내, 데이터 갱신, 이름 가리기도 남아 있고, 각각 대응 계획을 세웠습니다."),
    (plan, "계획", 30, "10주차에는 답변 전체를 평가하고 홈페이지 Q&A 게시판의 실제 질문으로 다시 측정합니다. 그 결과로 검색과 모델을 개선하고 파인튜닝을 진행합니다. 계획이 바뀐 점도 있습니다. 조교 인터뷰와 2차 설문은 하지 않기로 했고, 시연에서는 팀원이 조교 역할을 맡습니다."),
    (closing, "정리", 15, "정리하겠습니다. 학교 정보는 있는데 못 찾는 문제를, 모르면 지어내지 않는 AI와 조교의 답이 쌓이는 구조로 풀고 있습니다. 다음은 실제 학생 질문으로 정확도를 다시 재는 것입니다. 감사합니다."),
]

QNA = [
    ("ChatGPT로 되지 않나요?", "ChatGPT는 우리 학교 최신 공지와 버스 시간표를 모릅니다. 저희는 학교 자료만 근거로 출처와 함께 답하고, 모르면 조교에게 넘겨 그 답이 다음 학생의 답이 됩니다."),
    ("98.8%면 거의 완벽한 것 아닌가요?", "아닙니다. 질문을 저희가 자료를 보며 써서 낙관적입니다. 실제 학생 질문으로 다시 재서 따로 발표하겠습니다."),
    ("왜 더 큰 최신 모델을 쓰지 않나요?", "같은 조건으로 시험해 보니 최신 Kanana-2 3B가 12개 중 8개만 맞혀 지금 모델보다 못했습니다. 노트북 GPU 8GB 안에서 정확도가 가장 높은 모델을 골랐습니다."),
    ("조교 인터뷰를 안 하면 조교가 실제로 쓸지 어떻게 아나요?", "맞습니다, 확인하지 못했습니다. 그래서 조교 부담을 줄이도록 같은 질문을 묶어 한 번만 답하게 했고, 시연은 팀원이 조교 역할로 진행합니다."),
    ("개인정보는요?", "학생 로그인이 없고 이름·학번 칸이 없으며, 질문이 외부 AI로 나가지 않습니다. 질문 속 이름 가리기는 아직 못 해서 스케줄러와 함께 구현하겠습니다."),
    ("파인튜닝은 왜 늦어졌나요?", "효과를 비교하려면 평가 질문셋이 먼저 있어야 해서 순서를 바꿨습니다. 이번 주에 질문셋을 만들었으니 같은 질문으로 전후를 비교하겠습니다."),
]


def main():
    prs = Presentation()
    prs.slide_width, prs.slide_height = SW, SH
    for i, (fn, _, _, script) in enumerate(SLIDES, 1):
        s = fn(prs, i)
        s.notes_slide.notes_text_frame.text = script
    prs.save(OUT_PPTX)

    total = sum(x[2] for x in SLIDES)
    lines = ["# 물어봐 캠퍼스 9주차 중간 현황 발표 대본", "",
             f"- 발표 자료: {OUT_PPTX.name} ({len(SLIDES)}장)", "- 기준: 중간현황보고서_9주차 (2026-11-10)",
             "- 구성: 해커톤_발표분석.md 2절 흐름 (문제 → 원인 → 해결 → AI 검증 → 수치 → 한계 → 마무리)",
             f"- 예상 시간: 약 {total // 60}분 {total % 60}초", "- 같은 내용이 슬라이드 발표자 노트에도 들어 있습니다.", "", "---", ""]
    for i, (_, name, sec, script) in enumerate(SLIDES, 1):
        lines += [f"## {i}. {name} (약 {sec}초)", "", script, ""]
    lines += ["---", "", "## 예상 질문 (결론 1문장 + 근거 1문장, 30초 이내)", "", "| 질문 | 답변 |", "|---|---|"] + [f"| {q} | {a} |" for q, a in QNA]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("saved", OUT_PPTX.name, len(SLIDES), "slides;", f"{total // 60}m{total % 60}s")


if __name__ == "__main__":
    main()
