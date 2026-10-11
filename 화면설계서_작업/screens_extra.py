"""화면설계서용 추가 와이어프레임 9장 (요구사항정의서 그림과 같은 스타일).

사용: python screens_extra.py <out_dir>
요구사항정의서_작업/figures.py의 도구(box, badge, phone, appbar, chips, notes)를 가져다 쓴다.
figures.py를 import하면 기존 7장도 같은 폴더에 다시 그려진다.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "요구사항정의서_작업"))
import figures as F  # noqa: E402  (draws the base figures into sys.argv[1] too)
from figures import GRAY, MID, OUT, PH, PW, Rectangle, appbar, badge, box, chips, notes, phone, plt  # noqa: E402


def white(ax):
    ax.texts[-1].set_color("white")


def bubble(ax, x, y, w, h, text, fc="white", fs=9):
    box(ax, x, y, w, h, "", fc=fc, r=0.02)
    ax.text(x + 0.02, y + h - 0.02, text, fontsize=fs, va="top", linespacing=1.4)


def input_bar(ax, ox, oy):
    ax.plot([ox + 0.004, ox + PW - 0.004], [oy + 0.12, oy + 0.12], color=MID, lw=1)
    box(ax, ox + 0.03, oy + 0.045, 0.39, 0.055, "궁금한 것을 물어보세요", fs=9, r=0.027, ha="left")
    ax.texts[-1].set_color("#808080")
    box(ax, ox + 0.44, oy + 0.045, 0.09, 0.055, "전송", fc="black", fs=9, r=0.027)
    white(ax)


# ---------------------------------------------------------------- app
def screen_onboarding():
    fig, ax, ox, oy = phone("SCR-004-A 첫 실행 캠퍼스 선택")
    ax.text(ox + PW / 2, oy + 0.86, "물어봐 캠퍼스", fontsize=17, fontweight="bold", ha="center", va="center")
    ax.text(ox + PW / 2, oy + 0.80, "재학 중인 캠퍼스를 선택해 주세요", fontsize=10.5, ha="center", va="center")
    badge(ax, ox + PW - 0.05, oy + 0.86, 1)
    for i, (name, sel) in enumerate([("영동캠퍼스", False), ("아산캠퍼스", True)]):
        x = ox + 0.04 + i * 0.25
        box(ax, x, oy + 0.6, 0.23, 0.13, name, fc="black" if sel else "white", fs=11, bold=True, r=0.02)
        if sel:
            white(ax)
    badge(ax, ox + PW + 0.012, oy + 0.665, 2)
    ax.text(ox + 0.04, oy + 0.53, "학과·관심 분야 (선택)", fontsize=10, fontweight="bold", va="center")
    y = oy + 0.47
    x = ox + 0.04
    for label, sel in [("AI·SW", True), ("디자인", False), ("경영·마케팅", False)]:
        w = 0.018 * len(label) + 0.05
        box(ax, x, y - 0.021, w, 0.042, label, fc="black" if sel else "white", fs=8.5, r=0.021)
        if sel:
            white(ax)
        x += w + 0.012
    ax.text(ox + 0.04, oy + 0.41, "나중에 설정에서 바꿀 수 있어요", fontsize=8, color="#606060", va="center")
    badge(ax, ox + PW + 0.012, oy + 0.47, 3)
    box(ax, ox + 0.04, oy + 0.24, PW - 0.08, 0.1, "", fc=GRAY, r=0.015)
    ax.text(ox + 0.06, oy + 0.29, "선택한 정보는 이 기기에만 저장되고, 이름·학번 등\n개인정보는 받지 않습니다. 답을 못 찾은 질문의\n답변 알림에는 익명 기기 정보만 씁니다.",
            fontsize=8.5, va="center", linespacing=1.4)
    badge(ax, ox + PW + 0.012, oy + 0.29, 4)
    box(ax, ox + 0.04, oy + 0.07, PW - 0.08, 0.07, "시작하기", fc="black", fs=11, r=0.035)
    white(ax)
    badge(ax, ox + PW + 0.012, oy + 0.105, 5)
    notes(ax, [
        ("앱 이름·안내", "처음 실행할 때 한 번만 표시"),
        ("캠퍼스 선택", "영동 / 아산 중 하나, 필수"),
        ("학과·관심 분야", "복수 선택, 선택 사항"),
        ("개인정보 안내", "기기에만 저장, 개인정보 미수집"),
        ("시작하기", "캠퍼스 선택 후 활성화 → 메인 화면"),
    ])
    fig.savefig(OUT / "wire_scr004a_onboarding.png", facecolor="white")
    plt.close(fig)


def screen_clarify():
    fig, ax, ox, oy = phone("SCR-001-A 메인 화면: 되묻기")
    y = appbar(ax, ox, oy, "물어봐 캠퍼스 · 아산", action="일정   설정")
    box(ax, ox + 0.2, oy + 0.77, 0.33, 0.06, "지원할 만한 공모전 있어?", fc=MID, fs=9, r=0.02)
    badge(ax, ox + 0.19, oy + 0.8, 1)
    bubble(ax, ox + 0.03, oy + 0.6, 0.42, 0.14, "어떤 분야를 찾으세요?\n학과나 관심 분야를 알려주시면\n맞춰 드릴게요.")
    badge(ax, ox + 0.475, oy + 0.67, 2)
    x = ox + 0.03
    for label in ["AI·SW", "디자인", "경영·마케팅", "전체"]:
        w = 0.018 * len(label) + 0.04
        box(ax, x, oy + 0.535, w, 0.042, label, fs=8.5, r=0.021)
        x += w + 0.01
    badge(ax, ox + PW + 0.012, oy + 0.556, 3)
    box(ax, ox + 0.33, oy + 0.45, 0.2, 0.05, "AI·SW", fc=MID, fs=9, r=0.02)
    bubble(ax, ox + 0.03, oy + 0.2, 0.42, 0.22,
           "모집 중인 AI·SW 공모전 3건이에요\n(마감일 순).\n1. SW 아이디어 공모전 · 10.02 마감\n2. 청년 IT 서포터즈 · 10.08 마감\n3. …")
    box(ax, ox + 0.03, oy + 0.135, 0.42, 0.05, "", fc=GRAY, r=0.015)
    ax.text(ox + 0.045, oy + 0.16, "이 분야를 설정에 저장할까요?", fontsize=8, va="center")
    box(ax, ox + 0.3, oy + 0.143, 0.065, 0.034, "저장", fc="black", fs=7.5, r=0.012)
    white(ax)
    box(ax, ox + 0.372, oy + 0.143, 0.07, 0.034, "괜찮아요", fs=7, r=0.012)
    badge(ax, ox + 0.475, oy + 0.16, 4)
    ax.plot([ox + 0.004, ox + PW - 0.004], [oy + 0.12, oy + 0.12], color=MID, lw=1)
    box(ax, ox + 0.03, oy + 0.045, 0.39, 0.055, "궁금한 것을 물어보세요", fs=9, r=0.027, ha="left")
    ax.texts[-1].set_color("#808080")
    box(ax, ox + 0.44, oy + 0.045, 0.09, 0.055, "전송", fc="black", fs=9, r=0.027)
    white(ax)
    notes(ax, [
        ("조건이 빠진 질문", "분야·캠퍼스·학기 정보가 없는 질문"),
        ("되묻기 말풍선", "바로 답하지 않고 조건을 먼저 확인"),
        ("선택지 버튼", "한 번 눌러 답하기, '전체' 항상 제공"),
        ("저장 안내", "고른 분야를 설정에 저장할지 확인"),
    ])
    fig.savefig(OUT / "wire_scr001a_clarify.png", facecolor="white")
    plt.close(fig)


def screen_notfound():
    fig, ax, ox, oy = phone("SCR-001-B 메인 화면: 근거 없음 안내")
    y = appbar(ax, ox, oy, "물어봐 캠퍼스 · 아산", action="일정   설정")
    box(ax, ox + 0.12, oy + 0.77, 0.41, 0.06, "편입생 전공 학점 인정 몇 학점까지?", fc=MID, fs=8.5, r=0.02)
    badge(ax, ox + 0.11, oy + 0.8, 1)
    bubble(ax, ox + 0.03, oy + 0.53, 0.44, 0.21,
           "해당 정보를 찾을 수 없습니다.\n수집한 학교 자료에 아직 이 내용이 없어요.\n\n"
           "질문은 학과 조교에게 전달했어요.\n답변이 등록되면 알림으로 알려 드릴게요.")
    badge(ax, ox + 0.495, oy + 0.635, 2)
    box(ax, ox + 0.03, oy + 0.33, PW - 0.06, 0.16, "", fc=GRAY, lw=1.0, r=0.015, ec=MID)
    ax.text(ox + 0.05, oy + 0.465, "서버에서 자동 처리 (화면에 보이지 않음)", fontsize=8, fontweight="bold", va="center", color="#404040")
    ax.text(ox + 0.05, oy + 0.395, "· 질문 문장·카테고리·캠퍼스 + 익명 기기 토큰 저장\n· 비슷한 질문은 묶어서 질문 수 +1 (현재 14건)",
            fontsize=7.8, va="center", color="#404040", linespacing=1.5)
    badge(ax, ox + PW + 0.012, oy + 0.41, 3)
    input_bar(ax, ox, oy)
    notes(ax, [
        ("근거가 없는 질문", "수집한 자료로 답할 수 없는 질문"),
        ("근거 없음 안내", "지어내지 않고 찾을 수 없다고 안내,\n답변이 오면 알려 준다고 안내 (버튼 없음)"),
        ("자동 등록", "질문 문장 + 알림용 익명 기기 토큰 (FR-028)\n이름·학번은 저장하지 않음"),
    ])
    ax.text(0.67 + 0.06, 0.95 - 3 * 0.108 - 0.03,
            "※ 개인 성적·시간표처럼 공개 자료로 답할 수\n   없는 질문은 학사정보센터 등 공식 창구를\n   안내합니다 (FR-005)",
            fontsize=8.5, color="#404040", va="top", linespacing=1.4)
    fig.savefig(OUT / "wire_scr001b_notfound.png", facecolor="white")
    plt.close(fig)


def screen_answered():
    fig, ax, ox, oy = phone("SCR-001-C 메인 화면: 조교 답변 알림·확인")
    box(ax, ox + 0.025, oy + PH - 0.16, PW - 0.05, 0.1, "", fc=GRAY, lw=1.4, r=0.02)
    ax.text(ox + 0.05, oy + PH - 0.085, "물어봐 캠퍼스 · 지금", fontsize=8, color="#404040", va="center")
    ax.text(ox + 0.05, oy + PH - 0.125, "물어본 질문에 답변이 등록되었어요", fontsize=9.5, fontweight="bold", va="center")
    badge(ax, ox + PW + 0.012, oy + PH - 0.11, 1)
    ax.plot([ox + 0.004, ox + PW - 0.004], [oy + PH - 0.19, oy + PH - 0.19], color=MID, lw=1, ls="--")
    box(ax, ox + 0.12, oy + 0.72, 0.41, 0.06, "편입생 전공 학점 인정 몇 학점까지?", fc=MID, fs=8.5, r=0.02)
    bubble(ax, ox + 0.03, oy + 0.4, 0.44, 0.26,
           "편입생의 전공 학점 인정은 학과 안내\n기준에 따라 최대 OO학점까지 인정됩니다.\n자세한 과목별 기준은 학과 사무실\n안내문을 참고해 주세요.")
    ax.plot([ox + 0.045, ox + 0.455], [oy + 0.49, oy + 0.49], color=MID, lw=1)
    ax.text(ox + 0.05, oy + 0.465, "출처: 학과 조교 답변 · 10.09 등록", fontsize=7.5, va="center", color="#404040")
    ax.text(ox + 0.05, oy + 0.435, "근거 문서: 편입생 학점 인정 안내", fontsize=7.5, va="center", color="#404040")
    badge(ax, ox + 0.495, oy + 0.53, 2)
    box(ax, ox + 0.05, oy + 0.335, 0.13, 0.04, "원문 보기 ↗", fs=8, r=0.012)
    badge(ax, ox + 0.21, oy + 0.355, 3)
    input_bar(ax, ox, oy)
    notes(ax, [
        ("답변 알림", "조교 답변이 등록되면 질문했던 기기에\n익명 알림 (FCM, FR-030)"),
        ("답변·출처", "알림을 누르면 원래 질문과 답변 표시\n출처는 ‘학과 조교 답변 · 등록일’"),
        ("원문 보기", "조교가 연결한 보충 문서가 있으면\n원문으로 확인 (FR-007)"),
    ])
    ax.text(0.67 + 0.06, 0.95 - 3 * 0.108 - 0.03,
            "※ 같은 질문을 하는 다른 학생도 이 답변을\n   바로 받습니다 (FAQ DB 반영, FR-029).",
            fontsize=8.5, color="#404040", va="top", linespacing=1.4)
    fig.savefig(OUT / "wire_scr001c_answered.png", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- web
TA_MENU = ["대시보드", "답변 대기", "FAQ 관리", "로그아웃"]
ADMIN_MENU = ["대시보드", "답변 대기", "FAQ 관리", "보충 문서", "수집 현황", "중간 관리자", "로그아웃"]


def browser(title, crumb, active, menu=ADMIN_MENU, url="askcampus-admin"):
    fig = plt.figure(figsize=(12, 8.4), dpi=150)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1.43)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.03, 0.97, title, fontsize=13, fontweight="bold", va="center")
    bx, by, bw, bh = 0.03, 0.03, 0.95, 0.9
    box(ax, bx, by, bw, bh, fc="white", lw=2, r=0.015)
    ax.add_patch(Rectangle((bx + 0.003, by + bh - 0.06), bw - 0.006, 0.055, fc=GRAY, ec="none"))
    box(ax, bx + 0.12, by + bh - 0.047, 0.5, 0.032, f"{url} / {crumb}", fs=8.5, r=0.015, ha="left")
    ax.text(bx + 0.02, by + bh - 0.032, "●  ●  ●", fontsize=8, va="center", color="#808080")
    if active:
        ax.add_patch(Rectangle((bx + 0.003, by + 0.003), 0.17, bh - 0.066, fc=GRAY, ec="none"))
        for i, label in enumerate(menu):
            yy = by + bh - 0.13 - i * 0.07
            if label == active:
                box(ax, bx + 0.015, yy - 0.022, 0.145, 0.044, "", fc="black", r=0.01)
            ax.text(bx + 0.03, yy, label, fontsize=10, va="center", color="white" if label == active else "black",
                    fontweight="bold" if label == active else "normal")
    return fig, ax, bx, by, bw, bh


def side_notes(ax, items):
    for i, (title, desc) in enumerate(items):
        yy = 0.86 - i * 0.14
        badge(ax, 1.08, yy, i + 1)
        ax.text(1.12, yy, title, fontsize=11, fontweight="bold", va="center")
        ax.text(1.12, yy - 0.05, desc, fontsize=9, va="center", color="#333333", linespacing=1.3)


def field(ax, x, y, w, label, value, placeholder=False, h=0.05):
    ax.text(x, y + h + 0.022, label, fontsize=9.5, fontweight="bold", va="center")
    box(ax, x, y, w, h, value, fs=9.5, r=0.008, ha="left")
    if placeholder:
        ax.texts[-1].set_color("#808080")


def screen_login():
    fig, ax, bx, by, bw, bh = browser("SCR-006-A 로그인: 이메일 인증 코드 (웹, 학과 조교·관리자)", "로그인", None)
    cx, cw = bx + 0.25, 0.46
    box(ax, cx, by + 0.12, cw, 0.66, "", fc="white", lw=1.6, r=0.012)
    ax.text(cx + cw / 2, by + 0.72, "물어봐 캠퍼스 답변·운영 관리", fontsize=14, fontweight="bold", ha="center", va="center")
    ax.text(cx + cw / 2, by + 0.675, "학과 조교(중간 관리자)·관리자 전용", fontsize=9.5, ha="center", va="center", color="#404040")
    badge(ax, cx + cw + 0.03, by + 0.72, 1)
    field(ax, cx + 0.04, by + 0.55, cw - 0.2, "업무용 이메일", "ta.ai@u1.ac.kr")
    box(ax, cx + cw - 0.15, by + 0.55, 0.11, 0.05, "인증 코드 받기", fc="black", fs=8.5, r=0.008)
    white(ax)
    ax.text(cx + 0.04, by + 0.515, "등록된 이메일이면 인증 코드를 보냈습니다.", fontsize=8,
            va="center", color="#404040")
    badge(ax, cx + cw + 0.03, by + 0.575, 2)
    ax.text(cx + 0.04, by + 0.46, "인증 코드 (6자리)", fontsize=9.5, fontweight="bold", va="center")
    for k, ch in enumerate("4 8 2 7 1 5".split()):
        box(ax, cx + 0.04 + k * 0.064, by + 0.375, 0.052, 0.06, ch, fs=13, r=0.008)
    ax.text(cx + 0.04, by + 0.345, "남은 시간 09:41 · 다시 받기 (1분 뒤 가능)", fontsize=8, va="center", color="#606060")
    badge(ax, cx + cw + 0.03, by + 0.405, 3)
    box(ax, cx + 0.04, by + 0.24, cw - 0.08, 0.06, "로그인", fc="black", fs=11, r=0.01)
    white(ax)
    badge(ax, cx + cw + 0.03, by + 0.27, 4)
    ax.text(cx + cw / 2, by + 0.17, "인증 코드를 5회 틀리면 10분 동안 로그인이 제한됩니다", fontsize=8.5,
            ha="center", va="center", color="#606060")
    badge(ax, cx + cw + 0.03, by + 0.17, 5)
    side_notes(ax, [
        ("페이지 제목", "학과 조교(중간 관리자)·관리자 전용"),
        ("이메일·인증 코드 받기", "등록된 이메일이면 6자리 코드 발송\n등록 여부와 관계없이 같은 안내 표시"),
        ("인증 코드", "10분 동안 1회 사용\n같은 이메일은 1분에 한 번만 재발송"),
        ("로그인", "역할에 맞는 메뉴로 대시보드(SCR-006)\n이동, 12시간 유지"),
        ("실패 제한 안내", "5회 실패 시 10분 제한 (FR-033)"),
    ])
    fig.savefig(OUT / "wire_scr006a_login.png", facecolor="white")
    plt.close(fig)


def screen_managers():
    fig, ax, bx, by, bw, bh = browser("SCR-006-D 중간 관리자 관리 (웹, 관리자)", "중간 관리자", "중간 관리자")
    mx = bx + 0.2
    ax.text(mx, by + bh - 0.11, "중간 관리자 (학과 조교)", fontsize=13, fontweight="bold", va="center")
    ax.text(mx, by + bh - 0.15, "등록한 이메일만 인증 코드로 로그인하고 답변 대기 요약 메일을 받습니다.",
            fontsize=8.5, color="#606060", va="center")
    field(ax, mx, by + 0.6, 0.3, "이메일 (필수)", "새 중간 관리자 이메일", True)
    field(ax, mx + 0.32, by + 0.6, 0.12, "이름 (선택)", "김조교")
    field(ax, mx + 0.46, by + 0.6, 0.14, "소속 (선택)", "AI소프트웨어")
    box(ax, mx + 0.62, by + 0.6, 0.1, 0.05, "등록", fc="black", fs=10, r=0.008)
    white(ax)
    badge(ax, mx + 0.765, by + 0.625, 1)
    cols = [("이메일", 0.22), ("이름·소속", 0.2), ("등록일", 0.09), ("마지막 로그인", 0.13), ("", 0.08)]
    hy = by + 0.5
    total = sum(w for _, w in cols)
    ax.add_patch(Rectangle((mx, hy - 0.02), total, 0.04, fc=GRAY, ec="black", lw=1))
    x = mx
    for name, w in cols:
        ax.text(x + 0.01, hy, name, fontsize=9, fontweight="bold", va="center")
        x += w
    rows = [("ta.ai@u1.ac.kr", "김조교 · AI소프트웨어학과", "10.10", "10.10 09:12"),
            ("ta.nurse@u1.ac.kr", "이조교 · 간호학과", "10.10", "-"),
            ("ta.police@u1.ac.kr", "박조교 · 경찰소방행정학부", "10.10", "10.10 10:03")]
    for r, row in enumerate(rows):
        ry = hy - 0.055 - r * 0.055
        ax.add_patch(Rectangle((mx, ry - 0.0275), total, 0.055, fc="white", ec=MID, lw=1))
        x = mx
        for (name, w), val in zip(cols[:4], row):
            ax.text(x + 0.01, ry, val, fontsize=8.8, va="center")
            x += w
        box(ax, x + 0.01, ry - 0.017, 0.06, 0.034, "삭제", fs=8.5, r=0.008)
    badge(ax, mx + 0.765, hy - 0.055, 2)
    badge(ax, mx + 0.765, hy - 0.165, 3)
    box(ax, mx, by + 0.12, 0.72, 0.1, "", fc=GRAY, lw=1.0, r=0.008)
    ax.text(mx + 0.015, by + 0.17, "관리자 계정 (송승현·이승우)은 서버 설정으로 정해 이 화면에서 지울 수 없습니다.\n"
            "삭제하면 즉시 권한이 회수되고, 로그인 중인 세션이 끝나며, 요약 메일 대상에서 빠집니다.",
            fontsize=8.5, va="center", linespacing=1.5)
    badge(ax, mx + 0.765, by + 0.17, 4)
    side_notes(ax, [
        ("이메일 등록", "이메일 필수, 이름·소속 선택\n형식 오류·중복 이메일은 등록 안 됨"),
        ("중간 관리자 목록", "이메일, 이름·소속, 등록일,\n마지막 로그인"),
        ("삭제", "확인 창 후 즉시 권한 회수\n세션 종료·요약 메일 제외"),
        ("관리자 계정", "서버 설정(환경 변수)으로 정함\n이 화면에서 삭제 불가 (FR-032)"),
    ])
    fig.savefig(OUT / "wire_scr006d_managers.png", facecolor="white")
    plt.close(fig)


def screen_digest():
    fig, ax, bx, by, bw, bh = browser("SCR-006-E 답변 대기 요약 메일 (이메일, 학과 조교)", "받은 편지함", None,
                                      url="mail.u1.ac.kr")
    mx, mw = bx + 0.06, 0.83
    ax.text(mx, by + bh - 0.11, "[물어봐 캠퍼스] 답변 대기 3건", fontsize=14, fontweight="bold", va="center")
    ax.text(mx, by + bh - 0.155, "보낸 사람: 물어봐 캠퍼스 <noreply@askcampus>   받는 사람: ta.ai@u1.ac.kr   10.12 (월) 09:00",
            fontsize=8.5, color="#606060", va="center")
    badge(ax, mx + mw + 0.02, by + bh - 0.11, 1)
    ax.plot([mx, mx + mw], [by + bh - 0.185, by + bh - 0.185], color=MID, lw=1)
    ax.text(mx, by + 0.66, "앱이 답하지 못한 학생 질문이 3건 있습니다. (같은 질문이 많은 순)", fontsize=10, va="center")
    cols = [("질문", 0.5), ("카테고리", 0.15), ("질문 수", 0.1)]
    hy = by + 0.6
    total = sum(w for _, w in cols)
    ax.add_patch(Rectangle((mx, hy - 0.02), total, 0.04, fc=GRAY, ec="black", lw=1))
    x = mx
    for name, w in cols:
        ax.text(x + 0.01, hy, name, fontsize=9, fontweight="bold", va="center")
        x += w
    rows = [("편입생 전공 학점 인정 몇 학점까지?", "학사정보", "14"),
            ("휴학 신청 서류 어디서 받아요?", "학사정보", "9"),
            ("졸업작품 전시회 언제 해요?", "동아리·행사", "5")]
    for r, row in enumerate(rows):
        ry = hy - 0.055 - r * 0.055
        ax.add_patch(Rectangle((mx, ry - 0.0275), total, 0.055, fc="white", ec=MID, lw=1))
        x = mx
        for (name, w), val in zip(cols, row):
            ax.text(x + 0.01, ry, val, fontsize=9, va="center")
            x += w
    badge(ax, mx + total + 0.03, hy - 0.11, 2)
    box(ax, mx, by + 0.3, 0.26, 0.06, "답변 페이지에서 확인하기", fc="black", fs=10, r=0.01)
    white(ax)
    badge(ax, mx + 0.29, by + 0.33, 3)
    ax.text(mx, by + 0.2, "이 메일은 매일 오전 9시, 답변 대기 질문이 있을 때만 보내집니다.\n"
            "학생 이름·학번 등 식별 정보는 포함하지 않습니다. ('담당 아님'으로 표시한 질문은 제외)",
            fontsize=8.5, va="center", color="#606060", linespacing=1.5)
    badge(ax, mx + 0.66, by + 0.2, 4)
    side_notes(ax, [
        ("메일 제목", "[물어봐 캠퍼스] 답변 대기 N건"),
        ("답변 대기 목록", "같은 질문 수 순, 질문 문장·카테고리·\n질문 수만 표시"),
        ("답변 페이지 링크", "로그인(SCR-006-A) 후\n답변 대기(SCR-006)로 이동"),
        ("발송 안내", "매일 09:00, 0건이면 보내지 않음\n(FR-031, AVL-009)"),
    ])
    fig.savefig(OUT / "wire_scr006e_digest.png", facecolor="white")
    plt.close(fig)


def screen_faq():
    fig, ax, bx, by, bw, bh = browser("SCR-006-B 답변 작성 (웹, 학과 조교)", "답변 대기 / 답변 작성", "답변 대기", menu=TA_MENU)
    mx = bx + 0.2
    ax.text(mx, by + bh - 0.11, "답변 작성", fontsize=13, fontweight="bold", va="center")
    ax.text(mx, by + bh - 0.15, "같은 질문 14건 · 처음 들어온 날 10.07 · 카테고리 학사정보",
            fontsize=8.5, color="#606060", va="center")
    badge(ax, mx + 0.75, by + bh - 0.11, 1)
    field(ax, mx, by + 0.63, 0.7, "학생 질문 (대표 문장)", "편입생 전공 학점 인정 몇 학점까지?")
    badge(ax, mx + 0.75, by + 0.655, 2)
    ax.text(mx, by + 0.575, "답변", fontsize=9.5, fontweight="bold", va="center")
    box(ax, mx, by + 0.36, 0.7, 0.19, "", r=0.008)
    ax.text(mx + 0.015, by + 0.535, "편입생의 전공 학점 인정은 학과 안내 기준에 따라 최대 OO학점까지 인정됩니다.\n"
            "자세한 과목별 기준은 학과 사무실 안내문을 참고해 주세요.",
            fontsize=9, va="top", linespacing=1.5)
    badge(ax, mx + 0.75, by + 0.455, 3)
    field(ax, mx, by + 0.25, 0.45, "근거 문서 (선택)", "편입생 학점 인정 안내.pdf  (보충 문서)")
    badge(ax, mx + 0.47, by + 0.275, 4)
    box(ax, mx, by + 0.14, 0.7, 0.06, "", fc=GRAY, lw=1.0, r=0.008)
    ax.text(mx + 0.015, by + 0.17, "등록하면 승인 없이 바로 FAQ DB에 저장·재색인되고, 질문했던 14개 기기에 답변 알림이 갑니다.",
            fontsize=8.5, va="center")
    badge(ax, mx + 0.75, by + 0.17, 5)
    box(ax, mx + 0.39, by + 0.05, 0.1, 0.045, "담당 아님", fs=9.5, r=0.008)
    box(ax, mx + 0.5, by + 0.05, 0.09, 0.045, "취소", fs=9.5, r=0.008)
    box(ax, mx + 0.61, by + 0.05, 0.09, 0.045, "등록", fc="black", fs=9.5, r=0.008)
    white(ax)
    badge(ax, mx + 0.75, by + 0.072, 6)
    side_notes(ax, [
        ("질문 정보", "같은 질문 수, 처음 들어온 날, 카테고리"),
        ("학생 질문", "비슷한 질문을 묶은 대표 문장, 100자 이내\n(식별 정보는 가려서 표시)"),
        ("답변", "필수, 학과장·교무처 등에서 전달받은\n기준으로 작성"),
        ("근거 문서", "선택, 보충 문서와 연결해 출처 표시"),
        ("반영 안내", "승인 없이 즉시 FAQ DB 저장·재색인\n질문했던 기기에 익명 알림 (FR-029·030)"),
        ("담당 아님·취소·등록", "담당 아님은 관리자가 확인해 다른\n경로로 안내"),
    ])
    fig.savefig(OUT / "wire_scr006b_faq.png", facecolor="white")
    plt.close(fig)


def screen_docs():
    fig, ax, bx, by, bw, bh = browser("SCR-006-C 보충 문서 등록 (웹, 관리자)", "보충 문서", "보충 문서")
    mx = bx + 0.2
    ax.text(mx, by + bh - 0.11, "보충 문서", fontsize=13, fontweight="bold", va="center")
    box(ax, mx, by + 0.58, 0.72, 0.17, "", fc=GRAY, lw=1.2, r=0.01)
    ax.text(mx + 0.36, by + 0.69, "파일을 끌어다 놓거나 클릭해서 선택", fontsize=11, ha="center", va="center", fontweight="bold")
    ax.text(mx + 0.36, by + 0.635, "PDF · HWP · TXT, 10MB 이하", fontsize=9, ha="center", va="center", color="#404040")
    badge(ax, mx + 0.765, by + 0.665, 1)
    field(ax, mx, by + 0.47, 0.34, "제목", "편입생 학점 인정 안내")
    field(ax, mx + 0.38, by + 0.47, 0.16, "카테고리", "학사정보  ▼")
    field(ax, mx + 0.56, by + 0.47, 0.16, "제공처", "학과 사무실")
    badge(ax, mx + 0.765, by + 0.495, 2)
    box(ax, mx + 0.52, by + 0.39, 0.2, 0.045, "업로드 후 재색인", fc="black", fs=9.5, r=0.008)
    white(ax)
    badge(ax, mx + 0.765, by + 0.412, 3)
    cols = [("문서", 0.3), ("제공처", 0.12), ("등록일", 0.12), ("상태", 0.18)]
    hy = by + 0.32
    total = sum(w for _, w in cols)
    ax.add_patch(Rectangle((mx, hy - 0.02), total, 0.04, fc=GRAY, ec="black", lw=1))
    x = mx
    for name, w in cols:
        ax.text(x + 0.01, hy, name, fontsize=9, fontweight="bold", va="center")
        x += w
    rows = [("편입생 학점 인정 안내.pdf", "학과 사무실", "10.05", "색인 완료 (청크 12)"),
            ("아산캠 동아리방 배치도.hwp", "학생지원팀", "10.05", "재색인 대기"),
            ("2026 학교 FAQ 발췌.txt", "교무처(허락)", "10.04", "색인 완료 (청크 30)")]
    for r, row in enumerate(rows):
        ry = hy - 0.055 - r * 0.055
        ax.add_patch(Rectangle((mx, ry - 0.0275), total, 0.055, fc="white", ec=MID, lw=1))
        x = mx
        for (name, w), val in zip(cols, row):
            ax.text(x + 0.01, ry, val, fontsize=8.8, va="center")
            x += w
    badge(ax, mx + 0.765, hy - 0.055, 4)
    side_notes(ax, [
        ("파일 선택", "자동 수집이 안 되는 자료를 직접 업로드"),
        ("문서 정보", "제목·카테고리·제공처를 답변 출처에 표시"),
        ("업로드 후 재색인", "청킹·임베딩 후 벡터 DB에 반영"),
        ("문서 목록·상태", "색인 완료 / 재색인 대기, 청크 수"),
    ])
    fig.savefig(OUT / "wire_scr006c_docs.png", facecolor="white")
    plt.close(fig)


screen_onboarding()
screen_clarify()
screen_notfound()
screen_answered()
screen_login()
screen_faq()
screen_docs()
screen_managers()
screen_digest()
print("extra ok", sorted(p.name for p in OUT.glob("wire_*.png")))
