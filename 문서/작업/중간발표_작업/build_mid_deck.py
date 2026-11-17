"""중간현황보고서_8주차.md 내용으로 발표 자료(pptx)와 대본(md)을 만든다.

사용: python build_mid_deck.py
슬라이드 함수와 대본(SCRIPT)을 한 파일에 둬서 노트와 대본 md가 같은 내용이 되게 한다.
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
OUT_PPTX = ROOT / "문서" / "07_진행보고서" / "중간현황_발표자료.pptx"
OUT_MD = ROOT / "문서" / "07_진행보고서" / "중간현황_발표대본.md"

GREEN, BLUE, CORAL, GRAY = rgb("2E7D5B"), rgb("2A6F97"), rgb("C8553D"), rgb("8A929E")
I = Inches


def tile(s, x, y, w, h, big, label, color=NAVY, big_size=40):
    box(s, x, y, w, h, TINT)
    text(s, x + I(0.2), y + I(0.15), w - I(0.4), I(0.95), big, size=big_size, bold=True, color=color)
    text(s, x + I(0.2), y + h - I(0.72), w - I(0.4), I(0.62), label, size=14, color=MUTED)


def picture(s, path, x, y, h):
    im = Image.open(path)
    w = int(h * im.width / im.height)
    s.shapes.add_picture(str(path), x, y, w, h)
    return w


def cover(prs, no):
    s = new(prs, dark=True)
    text(s, MX, I(1.3), I(11), I(0.5), "물어봐 캠퍼스 (Ask Campus)", size=20, color=rgb("CADCFC"))
    text(s, MX, I(1.9), I(12), I(1.2), "중간 현황 발표", size=56, bold=True, color=WHITE, name="Title")
    text(s, MX, I(3.25), I(12), I(0.5), "RAG와 sLLM 기반 캠퍼스 정보 질의응답 앱", size=20, color=WHITE)
    text(s, MX, I(5.5), I(11), I(0.9), ["캡스톤디자인 1조 · 송승현 · 이승우", "계획 15주 중 8주차 · 2026-11-03 기준"],
         size=15, color=rgb("CADCFC"))
    return s


def summary(prs, no):
    s = new(prs)
    title(s, "핵심 흐름은 동작합니다", "설계를 마치고 MVP를 만들었고, 다음 과제는 정확도 측정과 남은 기능입니다", no)
    w = I(2.85)
    data = [("6종", "설계 산출물 완료", NAVY), ("20 / 33", "기능 요구사항 착수\n(구현 7, 일부 구현 13)", BLUE),
            ("9 / 9", "조교 답변 흐름 시험 통과", GREEN), ("3.4초", "sLLM 평균 답변 시간\n(질문 5개, 목표 5초)", GREEN)]
    for i, (b, l, c) in enumerate(data):
        tile(s, MX + i * (w + I(0.243)), I(1.75), w, I(1.95), b, l, c)
    text(s, MX, I(4.1), I(12), I(0.4), "지금까지", size=16, bold=True, color=NAVY)
    text(s, MX, I(4.5), I(5.8), I(1.8), ["· 실제 학교 자료로 근거를 대고 답함", "· 모르는 질문이 조교 답변을 거쳐 FAQ로 쌓임",
                                         "· Android 앱과 조교 웹이 서버와 연결됨"], size=15)
    text(s, I(6.9), I(4.1), I(5.8), I(0.4), "아직", size=16, bold=True, color=CORAL)
    text(s, I(6.9), I(4.5), I(5.8), I(1.8), ["· 검색 정확도 목표는 측정 전 (평가 질문셋 없음)", "· 파인튜닝 미착수 (계획은 7주차)",
                                             "· 기능 13개 미착수, 데이터 자동 갱신 없음"], size=15)
    return s


def schedule(prs, no):
    s = new(prs)
    title(s, "일정: 파인튜닝이 늦어졌습니다", "앱 개발은 계획보다 먼저 시작했고, 평가와 파인튜닝이 밀렸습니다", no)
    x0, span, y = I(1.05), I(11.2), I(3.95)
    box(s, x0, y - I(0.02), span, I(0.04), LINE, shape=MSO_SHAPE.RECTANGLE)
    items = [(1, "계획서", "완료", GREEN), (3, "데이터 수집", "일부 완료", BLUE), (5, "RAG 파이프라인", "1차 완료", GREEN),
             (7, "sLLM 파인튜닝", "지연", CORAL), (8, "중간고사", "현재", NAVY), (10, "앱 개발·통합", "먼저 시작", BLUE),
             (12, "구현현황 발표", "예정", GRAY), (14, "판넬·전시", "예정", GRAY), (15, "최종 발표", "예정", GRAY)]
    for i, (wk, name, st, c) in enumerate(items):
        cx = x0 + int(span * (wk - 1) / 14)
        d = I(0.5)
        badge(s, cx - d // 2, y - d // 2, d, str(wk), c, size=13)
        lw = I(1.75)
        lx = min(max(cx - lw // 2, MX), SW - MX - lw)
        ly = y - I(1.35) if i % 2 == 0 else y + I(0.4)
        text(s, lx, ly, lw, I(0.9), [[(name, {"bold": True, "size": 14, "color": INK})], [(st, {"size": 13, "color": c, "bold": True})]],
             align=PP_ALIGN.CENTER)
    text(s, MX, I(6.0), I(12), I(0.7), "숫자는 계획서의 주차입니다. 프로토타입은 10/12에 완성했고, 데이터도 그날 수집한 자료입니다.", size=14, color=MUTED)
    return s


def outputs(prs, no):
    s = new(prs)
    title(s, "설계 산출물", "요구사항부터 API까지 같은 요구사항 번호로 이어집니다", no)
    cards = [("요구사항 정의서", "v1.11", "기능 33 · 유스케이스 15\n성능 11 · 가용성 9"), ("화면설계서", "v1.5", "화면 13개\nUser flow 2 · Logic process 4"),
             ("DB 모델링", "v1.0", "테이블 13개 · 관계 14개\nE-R 다이어그램, 제약 조건"), ("API 명세서", "v1.0", "앱 API 5개\n관리 웹 API 13개 묶음"),
             ("모델·예산 검토", "v1.11 기준", "모델 후보 비교, 개발 가능성\n예산 최소 0원 ~ 10만 원 이내"), ("사전 설문", "1차 9명", "포털 불편 78%, 사용 의향 89%\n2차 문항 14개 준비, 배포 전")]
    w, h = I(3.87), I(2.2)
    for i, (n, v, d) in enumerate(cards):
        x = MX + (i % 3) * (w + I(0.26))
        y = I(1.7) + (i // 3) * (h + I(0.25))
        box(s, x, y, w, h, TINT)
        text(s, x + I(0.2), y + I(0.15), w - I(0.4), I(0.5), n, size=19, bold=True, color=NAVY)
        text(s, x + I(0.2), y + I(0.62), w - I(0.4), I(0.35), v, size=13, bold=True, color=BLUE)
        text(s, x + I(0.2), y + I(1.05), w - I(0.4), I(1.0), d.split("\n"), size=14)
    return s


def changed(prs, no):
    s = new(prs)
    title(s, "피드백으로 바뀐 핵심 설계", "조교를 답변 담당자로 바꾸고, 모르는 질문이 답으로 쌓이게 했습니다", no)
    steps = [("근거 없음", "질문 자동 등록", True), ("요약 메일", "매일 09:00", False), ("조교 답변", "승인 없이 등록", True),
             ("FAQ 즉시 반영", "같은 질문에 바로 답", True), ("익명 알림", "질문한 기기로", False)]
    w, gap = I(2.05), I(0.47)
    for i, (a, b, done) in enumerate(steps):
        x = MX + i * (w + gap)
        c = NAVY if done else GRAY
        box(s, x, I(1.85), w, I(1.45), c)
        text(s, x + I(0.08), I(2.05), w - I(0.16), I(1.05), [[(a, {"bold": True, "size": 17, "color": WHITE})], [(b, {"size": 13, "color": WHITE})]],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        if i < 4:
            box(s, x + w + I(0.09), I(2.42), I(0.29), I(0.3), LINE, shape=MSO_SHAPE.RIGHT_ARROW)
    text(s, MX, I(3.4), I(12), I(0.4), "진한 색은 MVP에 구현, 회색은 설계만 완료 (메일 계정·Firebase 준비 필요)", size=13, color=MUTED)
    rows = [("조교 역할", "학생과 같은 사용자", "중간 관리자 (답변 담당자)"), ("상위 조직", "액터 여부 미정", "시스템 밖 '정보 제공 조직'"),
            ("조교 로그인", "아이디·비밀번호", "이메일 6자리 인증 코드 (설계)"), ("앱 화면", "카테고리·상세 화면 별도", "채팅 화면 중심으로 축소")]
    table(s, MX, I(3.95), I(12.13), ["항목", "이전", "지금"], [list(r) for r in rows], [2, 4, 5], size=14, row_h=0.46)
    return s


def system(prs, no):
    s = new(prs)
    title(s, "구현한 시스템", "실제 학교 자료로 동작하는 MVP입니다", no)
    # 왼쪽 사용자, 가운데 서버, 오른쪽 저장소
    left = [("학생", "Android 앱 (Kotlin)\n질문, 답변, 출처, 원문 보기", I(1.8)), ("학과 조교", "웹 (임시 로그인)\n답변 대기, 답변 작성, FAQ", I(3.95))]
    for n, d, y in left:
        box(s, MX, y, I(3.1), I(1.8), TINT)
        text(s, MX + I(0.15), y + I(0.15), I(2.8), I(0.45), n, size=18, bold=True, color=NAVY)
        text(s, MX + I(0.15), y + I(0.65), I(2.8), I(1.0), d.split("\n"), size=14)
        box(s, MX + I(3.17), y + I(0.75), I(0.36), I(0.3), LINE, shape=MSO_SHAPE.RIGHT_ARROW)
    box(s, I(4.25), I(1.8), I(4.5), I(3.95), NAVY)
    text(s, I(4.45), I(1.95), I(4.1), I(0.45), "서버 (FastAPI)", size=18, bold=True, color=WHITE)
    text(s, I(4.45), I(2.5), I(4.1), I(3.1), ["검색: KURE-v1", "답변: Kanana 1.5 2.1B", "(노트북 GPU 8GB, 파인튜닝 전)", "버스 시간: 코드로 계산",
                                              "근거 없으면 답변 대기 등록"], size=18, color=WHITE)
    box(s, I(8.82), I(3.62), I(0.36), I(0.3), LINE, shape=MSO_SHAPE.RIGHT_ARROW)
    right = [("Chroma", "학교 자료 청크 154개", I(1.8)), ("SQLite", "FAQ, 답변 대기, 통계\n설계 13개 중 4개 테이블", I(3.35))]
    for n, d, y in right:
        box(s, I(9.25), y, I(3.48), I(1.4), TINT)
        text(s, I(9.4), y + I(0.1), I(3.2), I(0.45), n, size=18, bold=True, color=NAVY)
        text(s, I(9.4), y + I(0.55), I(3.2), I(0.8), d.split("\n"), size=14)
    text(s, I(9.25), I(4.9), I(3.48), I(0.9), ["수집: 공지, 학사일정 66건,", "통학버스, 동아리현황"], size=14, color=MUTED)
    text(s, MX, I(6.1), I(12), I(0.5), "구동에 유료 서비스를 쓰지 않았습니다.", size=14, color=MUTED)
    return s


def screens(prs, no):
    s = new(prs)
    title(s, "동작 화면", "출처와 원문을 함께 보여 주고, 모르면 조교에게 넘깁니다", no)
    h = I(5.0)
    w1 = picture(s, FIG / "app_answer.png", MX, I(1.6), h)
    x2 = MX + w1 + I(0.25)
    w2 = picture(s, FIG / "app_notfound.png", x2, I(1.6), h)
    x3 = x2 + w2 + I(0.35)
    wa = SW - MX - x3
    admin = FIG / "admin_table.png"          # 왼쪽 메뉴를 잘라 표를 크게 보여 준다
    Image.open(FIG / "admin_pending.png").crop((215, 20, 1260, 545)).save(admin)
    im = Image.open(admin)
    ha = int(wa * im.height / im.width)
    s.shapes.add_picture(str(admin), x3, I(1.6), wa, ha)
    text(s, x3, I(1.7) + ha, wa, I(1.6), ["왼쪽: 답변, 출처, 메뉴 위치, 원문 보기", "가운데: 자료에 없는 질문", "오른쪽: 조교 웹 답변 대기 (시험 중 화면)"], size=14, color=MUTED)
    return s


def progress(prs, no):
    s = new(prs)
    title(s, "기능 요구사항 진척", "33개 중 20개를 시작했고 13개가 남았습니다", no)
    # 비율 막대
    total, x, y, full = 33, MX, I(1.7), I(12.13)
    for n, c in ((7, GREEN), (13, BLUE), (13, GRAY)):
        w = int(full * n / total)
        box(s, x, y, w, I(0.55), c, shape=MSO_SHAPE.RECTANGLE)
        text(s, x, y, w, I(0.55), str(n), size=18, bold=True, color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        x += w
    cols = [("구현 7", GREEN, ["질의 입력, 근거 기반 답변", "출처 표시, 근거 없음 응답", "원문 보기, 통학버스", "메뉴 위치 안내"]),
            ("일부 구현 13", BLUE, ["검색 (동의어 사전 없음)", "수집 (수동 실행, 첨부 제외)", "조교 답변 (수정·삭제 없음)", "관리 페이지 (임시 로그인)", "자동 등록 (알림 토큰 없음) 등"]),
            ("미착수 13", GRAY, ["파인튜닝, 품질 평가", "이메일 로그인, 요약 메일", "답변 알림, 되묻기", "추천 질문, 대화 기록", "마감 일정, 교외활동 등"])]
    w = I(3.87)
    for i, (h, c, items) in enumerate(cols):
        cx = MX + i * (w + I(0.26))
        box(s, cx, I(2.55), w, I(3.3), TINT)
        text(s, cx + I(0.2), I(2.68), w - I(0.4), I(0.5), h, size=19, bold=True, color=c)
        text(s, cx + I(0.2), I(3.25), w - I(0.4), I(2.9), ["· " + t for t in items], size=16)
    return s


def tests(prs, no):
    s = new(prs)
    title(s, "시험 결과 (11/3 재시험)", "동작은 확인했고, 정확도는 아직 재지 못했습니다", no)
    w = I(2.85)
    data = [("9 / 9", "조교 답변 흐름\n등록부터 FAQ 답변까지", GREEN), ("10 / 10", "통학버스 시간 계산\n시각·요일을 바꿔 시험", GREEN),
            ("4 / 4", "자료에 없는 질문\n근거 없음으로 처리", GREEN), ("3.4초", "sLLM 평균 답변\n최대 5.3초, 질문 5개", GREEN)]
    for i, (b, l, c) in enumerate(data):
        tile(s, MX + i * (w + I(0.243)), I(1.75), w, I(2.05), b, l, c)
    box(s, MX, I(4.2), I(12.13), I(1.75), TINT)
    text(s, MX + I(0.25), I(4.35), I(11.6), I(0.45), "아직 모르는 것", size=18, bold=True, color=CORAL)
    text(s, MX + I(0.25), I(4.85), I(11.6), I(1.0), ["검색 정확도 목표(테스트 질문 80개 중 정답 근거 상위 3개 포함 80%)는 평가 질문셋이 없어 측정하지 못했습니다.",
                                                     "위 수치는 대표 질문으로 동작을 확인한 값이고, 정확도를 뜻하지 않습니다."], size=15)
    return s


def bug(prs, no):
    s = new(prs)
    title(s, "시험에서 찾은 문제와 해결", "\"가장 빠른 버스\"에 08:00이 아니라 10:15로 답했습니다", no)
    causes = [("1", "시간표 일부만 검색", "행 단위 조각의 점수가 비슷해 08:00이 든 조각이 4위. 모델에는 3개만 전달"),
              ("2", "현재 시각 미전달", "프롬프트에 날짜만 있고 시각이 없음"),
              ("3", "모델의 계산 한계", "표와 시각을 다 줘도 07:37, 10:00, 13:00 모두 08:00으로 답함")]
    for i, (n, h, d) in enumerate(causes):
        y = I(1.75) + i * I(1.3)
        box(s, MX, y, I(7.2), I(1.15), TINT)
        badge(s, MX + I(0.2), y + I(0.3), I(0.55), n, CORAL, size=15)
        text(s, MX + I(0.95), y + I(0.08), I(6.1), I(0.4), h, size=16, bold=True, color=NAVY)
        text(s, MX + I(0.95), y + I(0.48), I(6.1), I(0.65), d, size=13)
    box(s, I(8.1), I(1.75), I(4.63), I(3.75), NAVY)
    text(s, I(8.3), I(1.9), I(4.25), I(0.45), "해결", size=18, bold=True, color=WHITE)
    text(s, I(8.3), I(2.4), I(4.25), I(3.0), ["시간표 조회는 서버 코드가 계산", "응답 0.04초 안팎, 시험 10/10", "일반 질문에는 현재 시각 전달", "평일·주말 시간표를 구분"], size=19, color=WHITE)
    text(s, MX, I(5.8), I(12), I(0.7), "배운 점: 날짜·시간 계산은 작은 모델에 맡기지 않고 코드로 처리합니다. 다른 문제 5건도 원인과 해결을 기록했습니다.", size=15, color=INK)
    return s


def issues(prs, no):
    s = new(prs)
    title(s, "아직 남은 문제", "재시험에서 확인한 내용입니다", no)
    rows = [("구어체 질문을 놓침", "\"학교 동아리 뭐있냐…\"가 근거 없음 (점수 0.552)", "평가셋 측정, 리랭커, 기준값 조정"),
            ("지난 일정을 그대로 안내", "수강정정에 9월 기간을 답함", "날짜를 코드로 비교해 표시"),
            ("데이터가 갱신되지 않음", "10/12 수집본 그대로", "자동 재수집 구현"),
            ("이름을 가리지 않음", "전화번호·학번 형태만 가림", "이름 처리 방법 검토"),
            ("30일 만료 미동작", "만료일만 저장", "스케줄러에 포함"),
            ("방학 시간표 자동 선택 불가", "평일은 학기 중으로 답함", "학사일정에서 방학 판정")]
    table(s, MX, I(1.65), I(12.13), ["문제", "내용", "대응"], [list(r) for r in rows], [3.4, 4.6, 4.1], size=14, row_h=0.68)
    return s


def plan(prs, no):
    s = new(prs)
    title(s, "앞으로의 계획", "측정부터 하고, 그 결과로 개선합니다", no)
    steps = [("9주", "측정 준비", ["평가 질문 약 100개", "조교 인터뷰, 2차 설문", "데이터 재수집"], NAVY),
             ("9~10주", "검색 개선", ["정확도 첫 측정", "리랭커, 기준값 조정", "모델 비교"], NAVY),
             ("10~11주", "파인튜닝·기능", ["근거 충실, 모르면 모른다", "로그인·메일·알림", "되묻기, 마감 일정"], BLUE),
             ("12주", "구현현황 발표", ["전체 흐름 시연", "측정 결과 발표"], CORAL),
             ("13~15주", "마무리", ["시범 운영", "판넬·전시", "최종보고서"], GRAY)]
    w, gap = I(2.27), I(0.195)
    for i, (t, h, items, c) in enumerate(steps):
        x = MX + i * (w + gap)
        box(s, x, I(1.75), w, I(0.6), c)
        text(s, x, I(1.75), w, I(0.6), t, size=16, bold=True, color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        box(s, x, I(2.45), w, I(2.4), TINT)
        text(s, x + I(0.12), I(2.55), w - I(0.24), I(0.45), h, size=16, bold=True, color=NAVY)
        text(s, x + I(0.12), I(3.05), w - I(0.24), I(2.1), ["· " + a for a in items], size=14)
    text(s, MX, I(5.2), I(12), I(0.9), "파인튜닝은 같은 질문셋으로 전후를 비교해 좋아졌을 때만 반영합니다. 바뀌는 정보는 수집(RAG)으로, 시간 계산은 코드로 유지합니다.", size=15)
    return s


def risks(prs, no):
    s = new(prs)
    title(s, "위험과 결정할 사항", "일정이 가장 큰 위험입니다", no)
    table(s, MX, I(1.65), I(7.1), ["위험", "대응"], [["남은 기능 대비 시간 부족", "우선순위 '상', 시연 흐름 먼저"], ["파인튜닝 지연", "RAG + 프롬프트로도 시연 가능"],
                                                     ["Android 전용", "2차 설문으로 iPhone 비율 확인"], ["노트북 한 대가 서버", "시범 운영 기간만 구동"], ["조교 협조 미확정", "어려우면 팀원이 조교 역할"]],
          [3, 4], size=14, row_h=0.72)
    box(s, I(8.0), I(1.65), I(4.73), I(4.32), TINT)
    text(s, I(8.2), I(1.8), I(4.35), I(0.45), "결정할 사항", size=18, bold=True, color=NAVY)
    text(s, I(8.2), I(2.35), I(4.35), I(3.5), ["1. sLLM·임베딩 최종 확정 (비교 후)", "2. 메일 발송 계정", "3. 시간 조회의 코드 처리를 요구사항에 반영할지", "4. 학교 FAQ 활용 허락 경로"], size=15)
    return s


def closing(prs, no):
    s = new(prs, dark=True)
    text(s, MX, I(1.5), I(12), I(0.9), "정리", size=40, bold=True, color=WHITE, name="Title")
    text(s, MX, I(2.6), I(12), I(2.4), ["핵심 흐름은 실제 학교 자료로 동작합니다", "다음 단계는 평가 질문셋으로 정확도를 재는 것입니다", "12주차 구현현황 발표까지 남은 기능을 채우겠습니다"], size=22, color=WHITE)
    text(s, MX, I(5.3), I(12), I(0.6), "감사합니다", size=24, bold=True, color=rgb("CADCFC"))
    return s


SLIDES = [
    (cover, "표지", 15, "안녕하세요, 캡스톤디자인 1조입니다. 물어봐 캠퍼스의 중간 현황을 발표하겠습니다. 물어봐 캠퍼스는 학사일정, 통학버스, 공지 같은 학교 정보를 채팅으로 물으면 학교 자료를 근거로 답하는 앱입니다."),
    (summary, "요약", 35, "먼저 결론입니다. 설계 산출물을 마쳤고, 핵심 흐름이 동작하는 MVP까지 만들었습니다. 기능 요구사항 33개 중 20개를 시작했고, 그중 7개는 구현, 13개는 일부 구현입니다. 조교 답변 흐름 시험은 9개 모두 통과했습니다. 다만 검색 정확도는 평가 질문셋이 없어 아직 재지 못했고, 파인튜닝도 시작하지 못했습니다."),
    (schedule, "일정", 35, "계획서 일정과 비교하면, 계획서, RAG 파이프라인은 완료했고 데이터 수집은 일부 완료했습니다. 앱 개발은 10주차 계획이지만 먼저 시작했습니다. 반면 7주차였던 파인튜닝이 늦어졌습니다. 프로토타입은 10월 12일에 완성했고, 데이터도 그날 수집한 자료입니다."),
    (outputs, "설계 산출물", 30, "설계 산출물은 여섯 가지입니다. 요구사항 정의서는 기능 33개이고, 화면설계서는 화면 13개, DB 모델링은 테이블 13개, API 명세서는 앱 API 5개와 관리 웹 API 13개 묶음입니다. 모델·예산 검토와 사전 설문도 마쳤습니다. 1차 설문은 9명이 모두 아산캠퍼스라 방향 참고용으로만 썼고, 2차 설문 문항은 준비했지만 아직 배포 전입니다."),
    (changed, "바뀐 설계", 45, "교수님 피드백으로 가장 크게 바뀐 부분입니다. 처음에는 조교가 학생과 같은 사용자였는데, 답변 담당자인 중간 관리자로 바꿨습니다. 그래서 앱이 모르는 질문은 자동으로 답변 대기에 등록되고, 조교가 답하면 승인 없이 FAQ에 반영되어 같은 질문에 바로 답합니다. 학과장이나 교무처는 시스템을 직접 쓰지 않아 액터가 아니라 정보 제공 조직으로 표시했습니다. 회색으로 표시한 요약 메일과 익명 알림은 설계만 끝났고 아직 구현하지 않았습니다."),
    (system, "시스템", 35, "구현한 시스템입니다. 학생은 Android 앱으로, 조교는 웹으로 서버에 접속합니다. 서버는 KURE-v1으로 학교 자료를 찾고, Kanana 2.1B 모델로 근거만 사용해 답합니다. 모델은 노트북 GPU 8GB에서 돌리고 있고 아직 파인튜닝 전입니다. 학교 자료 청크 154개를 수집했고, 유료 서비스는 쓰지 않았습니다."),
    (screens, "동작 화면", 30, "실제 화면입니다. 왼쪽은 답변과 함께 출처, 홈페이지 메뉴 위치, 원문 보기를 보여 주는 화면입니다. 가운데는 자료에 없는 질문으로, 지어내지 않고 조교에게 전달했다고 안내합니다. 오른쪽은 조교 웹으로, 그런 질문이 같은 질문 수와 함께 쌓입니다."),
    (progress, "진척", 30, "기능 요구사항 기준으로 보면 초록색 7개가 구현, 파란색 13개가 일부 구현, 회색 13개가 미착수입니다. 일부 구현은 예를 들어 수집은 되지만 수동 실행이고, 조교 답변은 되지만 수정과 삭제가 없는 경우입니다. 미착수에는 파인튜닝과 품질 평가, 이메일 로그인, 알림이 있습니다."),
    (tests, "시험 결과", 35, "11월 3일에 다시 시험한 결과입니다. 조교 답변 흐름 9개, 통학버스 시간 계산 10개를 모두 통과했고, 자료에 없는 질문 4개도 근거 없음으로 처리했습니다. 답변 시간은 평균 3.4초입니다. 다만 대표 질문으로 동작을 확인한 값이고, 질문 5개만 잰 시간입니다. 정확도 목표는 아직 측정하지 못했습니다."),
    (bug, "해결 사례", 45, "시험 중 찾은 대표적인 문제입니다. 두정역에서 가장 빠른 버스를 물었는데 08시 차가 아니라 10시 15분 차를 답했습니다. 원인은 세 가지였습니다. 시간표 일부만 검색됐고, 모델이 현재 시각을 몰랐고, 표와 시각을 다 줘도 모델이 다음 차를 계산하지 못했습니다. 그래서 시간표 조회는 서버 코드가 계산하도록 바꿨고, 시험 10개를 모두 통과했습니다."),
    (issues, "남은 문제", 40, "아직 남은 문제입니다. 가장 중요한 것은 구어체 질문입니다. 학교 동아리 뭐있냐 같은 질문은 자료가 있는데도 찾지 못했습니다. 또 지난 일정을 지났다는 안내 없이 답하고, 데이터가 10월 12일에서 갱신되지 않습니다. 요구사항과 달리 질문의 이름은 아직 가리지 않고, 30일 만료도 동작하지 않습니다. 모두 이후 작업에 포함했습니다."),
    (plan, "계획", 35, "앞으로는 측정부터 하겠습니다. 9주차에 평가 질문 약 100개를 만들고 조교 인터뷰와 2차 설문을 진행합니다. 그 결과로 검색을 개선하고 모델을 비교한 뒤, 파인튜닝과 남은 기능을 구현합니다. 파인튜닝은 같은 질문으로 전후를 비교해 좋아졌을 때만 반영합니다. 12주차에 구현현황을 발표하겠습니다."),
    (risks, "위험", 25, "가장 큰 위험은 일정입니다. 그래서 우선순위 상과 시연 흐름부터 구현하고, 파인튜닝이 늦어지면 현재 구조로도 시연할 수 있게 하겠습니다. 오른쪽은 앞으로 정해야 할 사항입니다. 특히 시간 조회를 코드로 처리하는 방식을 요구사항에 반영할지는 검토가 필요합니다."),
    (closing, "정리", 15, "정리하겠습니다. 핵심 흐름은 실제 학교 자료로 동작합니다. 다음 단계는 평가 질문셋으로 정확도를 재는 것이고, 12주차까지 남은 기능을 채우겠습니다. 감사합니다."),
]

QNA = [
    ("왜 파인튜닝이 늦어졌나요?", "교수님 피드백으로 조교 역할과 답변 흐름을 바꾸며 설계 수정이 길어졌고, 평가 질문셋이 먼저 있어야 효과를 비교할 수 있어 순서를 뒤로 뒀습니다."),
    ("정확도는 어느 정도인가요?", "아직 측정하지 못했습니다. 지금 수치는 동작 확인용입니다. 평가 질문셋을 만들어 목표인 80%와 비교하겠습니다."),
    ("왜 버스 시간은 모델이 답하지 않나요?", "표와 현재 시각을 줘도 2B 모델이 다음 차를 고르지 못했습니다. 답이 정해진 계산이라 코드가 더 정확하고 빠릅니다."),
    ("조교 답변을 승인 없이 공개해도 되나요?", "팀에서 즉시 반영으로 정했습니다. 다만 수정·삭제 기능은 아직 없고, 조교 인터뷰에서 승인 필요 여부를 확인할 예정입니다."),
    ("개인정보는 안전한가요?", "학생 로그인 없이 쓰고 이름·학번 칸이 없습니다. 다만 질문 문장 안의 이름은 아직 가리지 못해 구현이 필요합니다."),
    ("iPhone은 지원하나요?", "현재 Android만 지원합니다. 2차 설문으로 iPhone 비율을 확인해 범위를 판단하겠습니다."),
]


def main():
    prs = Presentation()
    prs.slide_width, prs.slide_height = SW, SH
    for i, (fn, _, _, script) in enumerate(SLIDES, 1):
        s = fn(prs, i)
        s.notes_slide.notes_text_frame.text = script
    prs.save(OUT_PPTX)

    total = sum(x[2] for x in SLIDES)
    lines = ["# 물어봐 캠퍼스 중간 현황 발표 대본", "",
             f"- 발표 자료: 중간현황_발표자료.pptx ({len(SLIDES)}장)", "- 기준: 중간현황보고서_8주차 (2026-11-03)",
             f"- 예상 시간: 약 {total // 60}분 {total % 60}초", "- 같은 내용이 슬라이드 발표자 노트에도 들어 있습니다.", "", "---", ""]
    for i, (_, name, sec, script) in enumerate(SLIDES, 1):
        lines += [f"## {i}. {name} (약 {sec}초)", "", script, ""]
    lines += ["---", "", "## 예상 질문", "", "| 질문 | 답변 |", "|---|---|"] + [f"| {q} | {a} |" for q, a in QNA]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("saved", OUT_PPTX.name, len(SLIDES), "slides;", f"{total // 60}m{total % 60}s")


if __name__ == "__main__":
    main()
