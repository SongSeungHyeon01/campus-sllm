"""요구사항정의서용 그림: 유스케이스 다이어그램 + 화면 와이어프레임 4장 (흑백, 맑은 고딕)."""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle, Ellipse, FancyBboxPatch, Rectangle

font_manager.fontManager.addfont(r"C:\Windows\Fonts\malgun.ttf")
font_manager.fontManager.addfont(r"C:\Windows\Fonts\malgunbd.ttf")
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
GRAY = "#F2F2F2"
MID = "#BFBFBF"


def box(ax, x, y, w, h, text="", fc="white", lw=1.6, fs=11, bold=False, r=0.02, ha="center", ec="black"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                fc=fc, ec=ec, lw=lw))
    if text:
        tx = x + w / 2 if ha == "center" else x + 0.02
        ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=fs,
                fontweight="bold" if bold else "normal")


def badge(ax, x, y, n):
    ax.add_patch(Circle((x, y), 0.028, fc="black", ec="black", zorder=5))
    ax.text(x, y, str(n), color="white", ha="center", va="center", fontsize=10,
            fontweight="bold", zorder=6)


# ---------------------------------------------------------------- use case
def actor(ax, x, y, label):
    ax.add_patch(Circle((x, y + 0.075), 0.022, fc="white", ec="black", lw=1.6))
    ax.plot([x, x], [y + 0.053, y - 0.005], color="black", lw=1.6)
    ax.plot([x - 0.03, x + 0.03], [y + 0.035, y + 0.035], color="black", lw=1.6)
    ax.plot([x, x - 0.025], [y - 0.005, y - 0.045], color="black", lw=1.6)
    ax.plot([x, x + 0.025], [y - 0.005, y - 0.045], color="black", lw=1.6)
    ax.text(x, y - 0.07, label, ha="center", va="top", fontsize=11, fontweight="bold")


def usecase_diagram():
    fig = plt.figure(figsize=(11, 8.8), dpi=150)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1.34)
    ax.set_ylim(-0.08, 1)
    ax.axis("off")

    box(ax, 0.22, 0.04, 0.84, 0.92, fc=GRAY, r=0.015)
    ax.text(0.25, 0.925, "물어봐 캠퍼스 (Ask Campus)", fontsize=14, fontweight="bold", va="center")

    user_cases = [
        ("UC-01", "자연어 질문하기"),
        ("UC-02", "답변 및 출처 확인"),
        ("UC-03", "출처 원문 확인"),
        ("UC-04", "추천 질문으로 질문하기"),
        ("UC-05", "대화 기록 확인·삭제"),
        ("UC-06", "개인 설정(캠퍼스·분야·알림)"),
        ("UC-11", "마감 일정 확인·관심 저장"),
        ("UC-14", "답변 알림 받기"),
    ]
    admin_cases = [
        ("UC-07", "캠퍼스 데이터 수집"),
        ("UC-08", "청킹·임베딩 갱신"),
        ("UC-09", "답변 품질 평가"),
        ("UC-10", "sLLM 파인튜닝·반영"),
        ("UC-12", "답변 작성·즉시 반영"),
        ("UC-13", "답변 대기·인기 질문 확인"),
        ("UC-15", "중간 관리자 이메일 관리"),
    ]
    ew, eh = 0.30, 0.085
    left_x, right_x = 0.44, 0.84
    ys_user = [0.85 - i * 0.12 for i in range(len(user_cases))]
    ys_admin = [0.84 - i * 0.115 for i in range(len(admin_cases))]

    def ellipse(cx, cy, uc, name):
        ax.add_patch(Ellipse((cx, cy), ew, eh, fc="white", ec="black", lw=1.6))
        ax.text(cx, cy + 0.013, uc, ha="center", va="center", fontsize=9, color="#404040")
        ax.text(cx, cy - 0.014, name, ha="center", va="center", fontsize=11)

    for (uc, name), y in zip(user_cases, ys_user):
        ellipse(left_x, y, uc, name)
    for (uc, name), y in zip(admin_cases, ys_admin):
        ellipse(right_x, y, uc, name)

    # actors
    actor(ax, 0.10, 0.52, "학생")
    actor(ax, 1.21, 0.66, "관리자\n(송승현·이승우)")
    actor(ax, 1.21, 0.40, "스케줄러\n(시스템)")
    actor(ax, 1.21, 0.14, "학과 조교\n(중간 관리자)")
    for y in ys_user:
        ax.plot([0.135, left_x - ew / 2], [0.53, y], color="black", lw=1.1)
    for y in ys_admin[:4] + ys_admin[5:]:
        ax.plot([1.175, right_x + ew / 2], [0.67, y], color="black", lw=1.1)
    for y in ys_admin[:2]:
        ax.plot([1.175, right_x + ew / 2], [0.41, y], color="black", lw=1.1, ls="--")
    for y in ys_admin[4:6]:
        ax.plot([1.175, right_x + ew / 2], [0.15, y], color="black", lw=1.1)
    # 학과장·교무처·학생처 등은 시스템을 직접 쓰지 않고 조교에게 정보를 전달 (경계 밖)
    box(ax, 0.62, -0.075, 0.40, 0.05, "«정보 제공 조직» 학과장 · 교무처 · 학생처 등", fs=9, r=0.008)
    ax.plot([1.02, 1.17], [-0.05, 0.06], color="black", lw=1.1, ls="--")
    ax.text(1.06, -0.035, "회의 결과·안내 전달", fontsize=8, color="#404040", va="center")

    # UC-01 (질문하기) always includes UC-02 (답변·출처 확인): arrow base -> included
    x_inc = left_x + ew / 2 - 0.03
    ax.annotate("", xy=(x_inc, ys_user[1] + eh / 2 - 0.004), xytext=(x_inc, ys_user[0] - eh / 2 + 0.004),
                arrowprops=dict(arrowstyle="->", ls="--", lw=1.1, color="black"))
    ax.text(x_inc + 0.012, (ys_user[0] + ys_user[1]) / 2, "«include»", fontsize=8.5,
            va="center", color="#404040")

    # external data sources sit outside the system boundary, linked to UC-07
    box(ax, 1.09, 0.855, 0.235, 0.1, "«외부 시스템»\n학교 홈페이지\n온통청년 Open API", fs=9, r=0.01)
    ax.plot([right_x + ew / 2, 1.09], [ys_admin[0] + 0.01, 0.885], color="black", lw=1.1, ls="--")

    fig.savefig(OUT / "diagram_usecase.png", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- phone frame
PW, PH = 0.56, 1.0  # phone canvas (axes units)


def phone(title):
    fig = plt.figure(figsize=(9.6, 8.6), dpi=150)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1.2)
    ax.set_ylim(0, 1.075)
    ax.axis("off")
    ax.text(0.03, 1.05, title, fontsize=13, fontweight="bold", va="center")
    ox, oy = 0.03, 0.02
    box(ax, ox, oy, PW, PH, fc="white", lw=2.2, r=0.04)
    # status bar
    ax.text(ox + 0.04, oy + PH - 0.03, "9:41", fontsize=9, va="center")
    ax.text(ox + PW - 0.04, oy + PH - 0.03, "LTE  100%", fontsize=8, va="center", ha="right")
    return fig, ax, ox, oy


def appbar(ax, ox, oy, text, back=False, action=None):
    y = oy + PH - 0.115
    ax.add_patch(Rectangle((ox + 0.004, y), PW - 0.008, 0.07, fc=GRAY, ec="none"))
    ax.plot([ox + 0.004, ox + PW - 0.004], [y, y], color=MID, lw=1)
    x = ox + 0.035
    if back:
        ax.text(x, y + 0.035, "‹", fontsize=18, va="center")
        x += 0.04
    ax.text(x, y + 0.035, text, fontsize=12, fontweight="bold", va="center")
    if action:
        ax.text(ox + PW - 0.035, y + 0.035, action, fontsize=13, va="center", ha="right")
    return y


def notes(ax, items, x=0.67, top=0.95, gap=0.108):
    for i, (title, desc) in enumerate(items, 1):
        y = top - (i - 1) * gap
        badge(ax, x + 0.02, y, i)
        ax.text(x + 0.06, y, title, fontsize=11, fontweight="bold", va="center")
        ax.text(x + 0.06, y - 0.036, desc, fontsize=9, va="center", color="#333333", linespacing=1.3)


def chips(ax, ox, y, labels, active=None, fs=9):
    x = ox + 0.03
    for label in labels:
        w = 0.018 * len(label) + 0.03
        box(ax, x, y, w, 0.042, label, fc="black" if label == active else "white", fs=fs, r=0.021)
        if label == active:
            ax.texts[-1].set_color("white")
        x += w + 0.012


def screen_main():
    fig, ax, ox, oy = phone("SCR-001 메인(채팅) 화면")
    y = appbar(ax, ox, oy, "물어봐 캠퍼스 · 아산", action="일정   설정")
    badge(ax, ox + 0.35, y + 0.035, 1)
    badge(ax, ox + PW - 0.16, y + 0.075, 6)
    # 대화형 중심: 별도 카테고리 화면 없이, 채팅창 안에서 카테고리 칩 → 추천 질문 칩
    chips(ax, ox, y - 0.065, ["학사정보", "통학버스", "동아리·행사", "교외활동"], active="학사정보", fs=8)
    badge(ax, ox + PW + 0.012, y - 0.044, 2)
    ax.text(ox + 0.035, y - 0.105, "추천 질문", fontsize=8, color="#606060", va="center")
    x = ox + 0.03
    for label in ["수강정정 언제까지?", "이번 주 학사일정"]:
        w = 0.016 * len(label) + 0.035
        box(ax, x, y - 0.155, w, 0.036, label, fs=7.5, r=0.018)
        x += w + 0.01
    box(ax, ox + 0.2, oy + 0.61, 0.33, 0.065, "수강정정 언제까지야?", fc=MID, fs=9, r=0.02)
    box(ax, ox + 0.03, oy + 0.305, 0.42, 0.265, "", fc="white", r=0.02)
    ax.text(ox + 0.05, oy + 0.55,
            "2026학년도 2학기 수강정정은\n9월 30일(수) 18:00까지입니다.\n(9/24 학사공지로 하루 연장된\n일정입니다.)",
            fontsize=9, va="top", linespacing=1.4)
    ax.plot([ox + 0.045, ox + 0.435], [oy + 0.425, oy + 0.425], color=MID, lw=1)
    ax.text(ox + 0.05, oy + 0.40, "출처: 학사공지 · 09.29 09:00 수집", fontsize=7.5, va="center", color="#404040")
    ax.text(ox + 0.05, oy + 0.37, "위치: 홈 > 커뮤니티 > 공지사항 > 학사공지", fontsize=7.5, va="center", color="#404040")
    box(ax, ox + 0.05, oy + 0.323, 0.17, 0.028, "☆ 관심 일정 저장", fs=7.5, r=0.012)
    badge(ax, ox + 0.475, oy + 0.385, 3)
    box(ax, ox + 0.05, oy + 0.245, 0.16, 0.045, "원문 보기 ↗", fs=8.5, r=0.02)
    badge(ax, ox + 0.235, oy + 0.267, 4)
    ax.plot([ox + 0.004, ox + PW - 0.004], [oy + 0.12, oy + 0.12], color=MID, lw=1)
    box(ax, ox + 0.03, oy + 0.045, 0.39, 0.055, "궁금한 것을 물어보세요", fs=9, r=0.027, ha="left")
    ax.texts[-1].set_color("#808080")
    box(ax, ox + 0.44, oy + 0.045, 0.09, 0.055, "전송", fc="black", fs=9, r=0.027)
    ax.texts[-1].set_color("white")
    badge(ax, ox + 0.03, oy + 0.135, 5)
    notes(ax, [
        ("상단 바", "앱 이름과 설정한 캠퍼스(영동/아산) 표시"),
        ("카테고리·추천 질문", "카테고리를 고르면 그 분야 추천 질문\n버튼 표시, 누르면 바로 질문"),
        ("답변·출처·메뉴 위치", "출처, 수집 일시, 홈페이지 메뉴 경로,\n일정 답변에는 관심 일정 저장 버튼"),
        ("원문 보기", "근거 원문 페이지를 외부 브라우저로\n열기 (별도 상세 화면 없음)"),
        ("질문 입력창·전송", "최대 200자, 빈 입력은 전송 불가"),
        ("일정 · 설정", "마감 일정(SCR-005) / 설정(SCR-004) 이동"),
    ], gap=0.1)
    fig.savefig(OUT / "wire_scr001_main.png", facecolor="white")
    plt.close(fig)


def screen_category():
    fig, ax, ox, oy = phone("SCR-002 카테고리(FAQ) 화면")
    y = appbar(ax, ox, oy, "카테고리", back=True)
    chips(ax, ox, y - 0.065, ["학사정보", "통학버스", "동아리·행사", "교외활동"], active="통학버스", fs=8)
    badge(ax, ox + PW + 0.012, y - 0.044, 1)
    ax.text(ox + 0.035, y - 0.12, "자주 묻는 질문", fontsize=11, fontweight="bold", va="center")
    faqs = ["영동역에서 학교 가는 첫차는?", "아산캠퍼스 천안터미널 버스 시간", "주말·방학에도 통학버스 있어?",
            "하교 버스 막차는 몇 시야?", "통학버스 불편 신고는 어디에?"]
    for i, q in enumerate(faqs):
        cy = y - 0.235 - i * 0.105
        box(ax, ox + 0.03, cy, PW - 0.06, 0.085, "", r=0.02)
        ax.text(ox + 0.055, cy + 0.0425, q, fontsize=9.5, va="center")
        ax.text(ox + PW - 0.055, cy + 0.0425, "›", fontsize=14, va="center", ha="right")
    badge(ax, ox + PW + 0.012, y - 0.235 + 0.0425, 2)
    box(ax, ox + 0.03, oy + 0.045, PW - 0.06, 0.06, "직접 질문하기", fc="black", fs=10, r=0.03)
    ax.texts[-1].set_color("white")
    badge(ax, ox + PW - 0.02, oy + 0.075, 3)
    notes(ax, [
        ("카테고리 탭", "학사정보 / 통학버스 / 동아리·행사 / 교외활동"),
        ("FAQ 카드", "탭하면 메인 화면 입력창에 질문이 자동 입력·전송"),
        ("직접 질문하기", "빈 입력창 상태로 메인 화면으로 이동"),
    ])
    fig.savefig(OUT / "wire_scr002_category.png", facecolor="white")
    plt.close(fig)


def screen_detail():
    fig, ax, ox, oy = phone("SCR-003 답변 상세 화면")
    y = appbar(ax, ox, oy, "답변 근거", back=True)
    ax.text(ox + 0.035, y - 0.04, "질문", fontsize=9, color="#606060", va="center")
    ax.text(ox + 0.035, y - 0.075, "영동역에서 학교 가는 버스 몇 시에 있어요?", fontsize=9.5, va="center")
    badge(ax, ox + PW - 0.03, y - 0.058, 1)
    ax.plot([ox + 0.03, ox + PW - 0.03], [y - 0.105, y - 0.105], color=MID, lw=1)
    for i, (cat, title, when) in enumerate([
        ("통학버스", "영동캠퍼스 통학버스 · 평일 (1/3)", "2026-09-27 03:00 수집"),
        ("통학버스", "영동캠퍼스 노선·승하차장 안내", "2026-09-27 03:00 수집"),
    ]):
        cy = y - 0.40 - i * 0.29
        box(ax, ox + 0.03, cy, PW - 0.06, 0.27, "", fc="white", r=0.02)
        box(ax, ox + 0.05, cy + 0.215, 0.11, 0.036, cat, fc=GRAY, fs=8, r=0.018)
        ax.text(ox + 0.05, cy + 0.185, title, fontsize=9.5, fontweight="bold", va="center")
        ax.text(ox + 0.05, cy + 0.16, when, fontsize=8, color="#606060", va="center")
        for k in range(4):
            ax.add_patch(Rectangle((ox + 0.05, cy + 0.12 - k * 0.025), PW - 0.13 - (k == 3) * 0.12, 0.011,
                                   fc=MID, ec="none"))
        ax.text(ox + 0.05, cy + 0.02, "원문 페이지 열기 ↗", fontsize=8.5, va="center")
    badge(ax, ox + PW - 0.02, y - 0.40 + 0.25, 2)
    badge(ax, ox + 0.25, y - 0.40 + 0.02, 3)
    notes(ax, [
        ("질문 요약", "상세 보기를 연 답변의 원래 질문"),
        ("근거 청크 카드", "카테고리, 문서 제목, 수집 일시, 원문 전체"),
        ("원문 페이지 열기", "출처 URL을 외부 브라우저로 연결"),
    ])
    fig.savefig(OUT / "wire_scr003_detail.png", facecolor="white")
    plt.close(fig)


def screen_settings():
    fig, ax, ox, oy = phone("SCR-004 설정 화면")
    y = appbar(ax, ox, oy, "설정", back=True)

    def seg(label, options, active, row_y, n):
        ax.text(ox + 0.035, row_y, label, fontsize=10.5, va="center")
        x = ox + 0.2
        for opt in options:
            box(ax, x, row_y - 0.022, 0.1, 0.045, opt, fc="black" if opt == active else "white", fs=9, r=0.02)
            if opt == active:
                ax.texts[-1].set_color("white")
            x += 0.11
        badge(ax, ox + PW + 0.012, row_y, n)

    seg("캠퍼스", ["영동", "아산"], "아산", y - 0.06, 1)
    ax.text(ox + 0.035, y - 0.13, "학과·관심 분야", fontsize=10.5, va="center")
    ax.text(ox + PW - 0.035, y - 0.13, "AI·SW  ›", fontsize=9.5, va="center", ha="right")
    ax.text(ox + 0.035, y - 0.158, "선택 사항 · 기기에만 저장", fontsize=8, va="center", color="#404040")
    badge(ax, ox + PW + 0.012, y - 0.13, 2)
    seg("글씨 크기", ["작게", "보통", "크게"], "보통", y - 0.21, 3)
    ax.plot([ox + 0.03, ox + PW - 0.03], [y - 0.255, y - 0.255], color=MID, lw=1)
    ax.text(ox + 0.035, y - 0.29, "마감 알림", fontsize=10.5, va="center")
    box(ax, ox + PW - 0.13, y - 0.31, 0.09, 0.04, "", fc="black", r=0.02)
    ax.add_patch(Circle((ox + PW - 0.06, y - 0.29), 0.015, fc="white", ec="white"))
    ax.text(ox + 0.035, y - 0.325, "관심 일정 마감 3일 전·당일 알림", fontsize=8, va="center", color="#404040")
    badge(ax, ox + PW + 0.012, y - 0.29, 4)
    items = [("최근 질문 기록 삭제", "›"), ("데이터 기준일", "2026-09-30 09:00"), ("앱 버전", "1.2.0")]
    for i, (label, value) in enumerate(items):
        cy = y - 0.40 - i * 0.075
        ax.plot([ox + 0.03, ox + PW - 0.03], [cy + 0.038, cy + 0.038], color=MID, lw=1)
        ax.text(ox + 0.035, cy, label, fontsize=10.5, va="center")
        ax.text(ox + PW - 0.035, cy, value, fontsize=9, va="center", ha="right", color="#404040")
    badge(ax, ox + 0.28, y - 0.40, 5)
    box(ax, ox + 0.07, oy + 0.05, PW - 0.14, 0.17, "", fc="white", lw=1.8, r=0.02)
    ax.text(ox + PW / 2, oy + 0.18, "질문 기록을 모두 삭제할까요?", fontsize=9.5, ha="center", va="center",
            fontweight="bold")
    ax.text(ox + PW / 2, oy + 0.145, "삭제한 기록은 복구할 수 없습니다.", fontsize=8.5, ha="center",
            va="center", color="#404040")
    box(ax, ox + 0.1, oy + 0.065, 0.15, 0.045, "취소", fs=9, r=0.02)
    box(ax, ox + PW - 0.25, oy + 0.065, 0.15, 0.045, "삭제", fc="black", fs=9, r=0.02)
    ax.texts[-1].set_color("white")
    badge(ax, ox + PW - 0.05, oy + 0.22, 6)
    notes(ax, [
        ("캠퍼스", "영동 / 아산, 처음 실행할 때 선택\n버스·동아리 답변에 우선 적용"),
        ("학과·관심 분야", "선택 사항, 공모전·대외활동 추천에 사용\n설정하지 않으면 질문할 때 되물음"),
        ("글씨 크기", "작게 / 보통(기본값) / 크게"),
        ("마감 알림", "켜면 관심 일정 마감 3일 전·당일에\n기기 알림 (기본값: 켜짐)"),
        ("기록 삭제·기준일·버전", "대화 기록 삭제, 마지막 수집 일시,\n앱 버전"),
        ("삭제 확인 창", "실수로 지우지 않도록 한 번 더 확인"),
    ], gap=0.1)
    fig.savefig(OUT / "wire_scr004_settings.png", facecolor="white")
    plt.close(fig)


def screen_deadlines():
    fig, ax, ox, oy = phone("SCR-005 마감 일정 화면")
    y = appbar(ax, ox, oy, "마감 일정", back=True)
    chips(ax, ox, y - 0.065, ["전체", "학사", "교외활동", "관심"], active="전체", fs=8.5)
    badge(ax, ox + PW + 0.012, y - 0.044, 1)
    box(ax, ox + 0.03, y - 0.14, PW - 0.06, 0.05, "관심 일정 3건 · 마감 3일 전에 알려드려요", fc=GRAY, fs=8.5, r=0.015)
    badge(ax, ox + PW + 0.012, y - 0.115, 2)
    items = [
        ("D-1", "2학기 수강정정 마감", "학사일정 · 09.30(수) 18:00", True),
        ("D-3", "SW 아이디어 공모전 접수", "온통청년 · 10.02(금)", True),
        ("D-6", "학과 캡스톤 멘토링 신청", "AI소프트웨어학과 공지 · 10.05(월)", False),
        ("D-9", "청년 IT 서포터즈 모집", "일반공지 · 10.08(목)", True),
        ("D-16", "2학기 중간고사 시작", "학사일정 · 10.15(목)", False),
    ]
    for i, (dday, title, meta, fav) in enumerate(items):
        cy = y - 0.25 - i * 0.105
        box(ax, ox + 0.03, cy, PW - 0.06, 0.09, "", r=0.02)
        box(ax, ox + 0.045, cy + 0.025, 0.075, 0.04, dday, fc="black" if i < 2 else "white", fs=8.5, r=0.02)
        if i < 2:
            ax.texts[-1].set_color("white")
        ax.text(ox + 0.14, cy + 0.058, title, fontsize=9.5, fontweight="bold", va="center")
        ax.text(ox + 0.14, cy + 0.027, meta, fontsize=7.8, va="center", color="#404040")
        ax.text(ox + PW - 0.05, cy + 0.045, "★" if fav else "☆", fontsize=13, va="center", ha="right")
    badge(ax, ox + 0.03, y - 0.25, 3)
    badge(ax, ox + PW + 0.012, y - 0.25 + 0.045, 4)
    ax.text(ox + PW / 2, oy + 0.06, "일정을 누르면 원문 공지로 이동합니다", fontsize=8, ha="center", color="#606060")
    badge(ax, ox + 0.07, oy + 0.065, 5)
    notes(ax, [
        ("필터 탭", "전체 / 학사 / 교외활동 / 관심(저장한 일정)"),
        ("알림 안내", "관심 일정 수와 알림 시점 표시"),
        ("D-day 표시", "마감까지 남은 날, 3일 이내는 강조"),
        ("관심 저장(☆/★)", "누르면 관심 일정으로 저장·해제\n(기기에만 저장)"),
        ("원문 이동", "일정을 누르면 근거 공지 원문으로 이동"),
    ])
    fig.savefig(OUT / "wire_scr005_deadlines.png", facecolor="white")
    plt.close(fig)


def screen_admin():
    fig = plt.figure(figsize=(12, 8.4), dpi=150)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1.43)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.03, 0.97, "SCR-006 답변·운영 관리 페이지 (웹, 학과 조교·관리자)", fontsize=13, fontweight="bold",
            va="center")
    bx, by, bw, bh = 0.03, 0.03, 0.95, 0.9
    box(ax, bx, by, bw, bh, fc="white", lw=2, r=0.015)
    ax.add_patch(Rectangle((bx + 0.003, by + bh - 0.06), bw - 0.006, 0.055, fc=GRAY, ec="none"))
    box(ax, bx + 0.12, by + bh - 0.047, 0.5, 0.032, "askcampus-admin / 답변 대기", fs=8.5, r=0.015, ha="left")
    ax.text(bx + 0.02, by + bh - 0.032, "●  ●  ●", fontsize=8, va="center", color="#808080")
    ax.add_patch(Rectangle((bx + 0.003, by + 0.003), 0.17, bh - 0.066, fc=GRAY, ec="none"))
    for i, (label, active) in enumerate([("대시보드", False), ("답변 대기", True), ("FAQ 관리", False),
                                         ("보충 문서", False), ("수집 현황", False), ("중간 관리자", False),
                                         ("로그아웃", False)]):
        yy = by + bh - 0.13 - i * 0.07
        if active:
            box(ax, bx + 0.015, yy - 0.022, 0.145, 0.044, "", fc="black", r=0.01)
        ax.text(bx + 0.03, yy, label, fontsize=10, va="center", color="white" if active else "black",
                fontweight="bold" if active else "normal")
    badge(ax, bx + 0.14, by + bh - 0.09, 1)
    mx = bx + 0.2
    for i, (title, value) in enumerate([("오늘 질문", "128건"), ("답변 대기", "6건"), ("평균 응답", "3.4초")]):
        box(ax, mx + i * 0.245, by + bh - 0.2, 0.225, 0.11, "", fc="white", r=0.01)
        ax.text(mx + i * 0.245 + 0.015, by + bh - 0.115, title, fontsize=9, va="center", color="#404040")
        ax.text(mx + i * 0.245 + 0.015, by + bh - 0.165, value, fontsize=15, fontweight="bold", va="center")
    badge(ax, mx + 0.72, by + bh - 0.09, 2)
    ty = by + bh - 0.27
    ax.text(mx, ty, "답변 대기 질문 (앱이 답하지 못한 질문, 비슷한 질문끼리 묶음)", fontsize=10.5, fontweight="bold",
            va="center")
    cols = [("질문 예시", 0.34), ("횟수", 0.07), ("카테고리", 0.1), ("처리", 0.2)]
    total = sum(w for _, w in cols)
    rows = [("편입생 전공 학점 인정 몇 학점까지?", "14", "학사정보"),
            ("휴학 신청 서류 어디서 받아요?", "9", "학사정보"),
            ("아산캠 동아리방 위치", "6", "동아리·행사"),
            ("졸업작품 전시회 언제 해요?", "5", "동아리·행사")]
    hy = ty - 0.055
    ax.add_patch(Rectangle((mx, hy - 0.022), total, 0.044, fc=GRAY, ec="black", lw=1))
    x = mx
    for name, w in cols:
        ax.text(x + 0.01, hy, name, fontsize=9, fontweight="bold", va="center")
        x += w
    for r, (q, n, cat) in enumerate(rows):
        ry = hy - 0.06 - r * 0.06
        ax.add_patch(Rectangle((mx, ry - 0.03), total, 0.06, fc="white", ec=MID, lw=1))
        ax.text(mx + 0.01, ry, q, fontsize=9, va="center")
        ax.text(mx + 0.35, ry, n, fontsize=9, va="center")
        ax.text(mx + 0.42, ry, cat, fontsize=9, va="center")
        box(ax, mx + 0.52, ry - 0.018, 0.085, 0.036, "답변 작성", fc="black", fs=8, r=0.01)
        ax.texts[-1].set_color("white")
        box(ax, mx + 0.615, ry - 0.018, 0.09, 0.036, "담당 아님", fs=8, r=0.01)
    badge(ax, mx + 0.735, hy - 0.06, 3)
    badge(ax, mx + 0.735, hy - 0.12, 4)
    ax.text(mx, by + 0.06, "※ 질문은 식별 정보 없이 문장만 보관하며, 답변하면 FAQ DB에 저장되고 질문했던 기기에 익명 알림을 보냅니다.", fontsize=8.5, color="#606060")
    notes_x = 1.07
    for i, (title, desc) in enumerate([
        ("메뉴", "대시보드, 답변 대기, FAQ 관리,\n(관리자) 보충 문서, 수집 현황, 중간 관리자"),
        ("운영 지표", "질문 수, 답변 대기 건수,\n평균 응답 시간"),
        ("답변 대기 목록", "앱이 답하지 못한 질문을 자동 등록,\n묶어서 질문 수가 많은 순으로 표시"),
        ("답변 작성 · 담당 아님", "작성 즉시 FAQ DB 저장·재색인,\n질문했던 학생에게 익명 알림"),
    ]):
        yy = 0.86 - i * 0.14
        badge(ax, notes_x + 0.02, yy, i + 1)
        ax.text(notes_x + 0.06, yy, title, fontsize=11, fontweight="bold", va="center")
        ax.text(notes_x + 0.06, yy - 0.05, desc, fontsize=9, va="center", color="#333333", linespacing=1.3)
    fig.savefig(OUT / "wire_scr006_admin.png", facecolor="white")
    plt.close(fig)


usecase_diagram()
screen_main()
screen_category()
screen_detail()
screen_settings()
screen_deadlines()
screen_admin()
print("ok", sorted(p.name for p in OUT.glob("*.png")))
