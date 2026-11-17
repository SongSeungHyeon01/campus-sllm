"""db_content.py의 테이블·관계로 E-R 다이어그램을 그린다.

사용: python erd.py <out_dir>
테이블마다 PK·FK와 주요 속성 몇 개만 보여 주고(전체 속성은 RDM 슬라이드),
관계선의 N 쪽 끝에는 까마귀발 표시를 붙인다.
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

import db_content as C

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
OUT.mkdir(parents=True, exist_ok=True)

W, RH, HH = 2.7, 0.25, 0.42          # 상자 너비, 행 높이, 머리 높이
EXTRA = {                              # PK·FK 말고 그림에 보여 줄 속성
    "source": ["name", "interval_min"],
    "document": ["doc_type", "title"],
    "chunk": ["content", "deadline"],
    "collect_log": ["status"],
    "manager": ["email", "role"],
    "auth_code": ["code_hash", "expires_at"],
    "login_session": ["expires_at"],
    "pending_question": ["question", "question_count", "status"],
    "notify_token": ["fcm_token"],
    "faq": ["question", "answer"],
    "synonym": ["term", "canonical"],
    "query_log": ["question", "response_ms"],
    "digest_log": ["pending_count"],
}
POS = {                                # 상자 왼쪽 위 (x, y)
    "source": (0.3, 8.55), "collect_log": (0.3, 4.6),
    "document": (3.95, 8.55), "chunk": (3.95, 4.6),
    "faq": (7.6, 8.55), "pending_question": (7.6, 5.75), "notify_token": (7.6, 2.75),
    "manager": (11.25, 8.55), "query_log": (11.25, 4.15), "digest_log": (11.25, 2.35),
    "auth_code": (15.6, 8.55), "login_session": (15.6, 6.55), "synonym": (15.6, 4.75),
}

T = {t["name"]: t for t in C.TABLES}
BOX = {}


def rows_of(t):
    keys = [f for f in t["fields"] if f[2] or f[3]]
    extra = [f for f in t["fields"] if f[0] in EXTRA[t["name"]] and f not in keys]
    return keys + extra


def draw_table(ax, name):
    t = T[name]
    x, y = POS[name]
    rows = rows_of(t)
    h = HH + RH * len(rows) + 0.08
    color = "#" + C.GROUPS[t["group"]][1]
    ax.add_patch(FancyBboxPatch((x, y - h), W, h, boxstyle="round,pad=0,rounding_size=0.06",
                                fc="white", ec=color, lw=1.6, zorder=2))
    ax.add_patch(Rectangle((x, y - HH), W, HH, fc=color, ec=color, lw=0, zorder=3))
    ax.text(x + 0.1, y - HH / 2, t["kor"], color="white", fontsize=9.5, fontweight="bold", va="center", zorder=4)
    ax.text(x + W - 0.1, y - HH / 2, name, color="white", fontsize=7.5, va="center", ha="right", zorder=4)
    for i, f in enumerate(rows):
        ry = y - HH - 0.04 - RH * (i + 0.5)
        tag = "PK" if f[2] else ("FK" if f[3] else "")
        if tag:
            ax.text(x + 0.1, ry, tag, fontsize=7, fontweight="bold", va="center", zorder=4,
                    color="#B8860B" if tag == "PK" else "#555555")
        ax.text(x + 0.45, ry, f[0], fontsize=8, va="center", zorder=4,
                fontweight="bold" if f[2] else "normal")
        ax.text(x + W - 0.1, ry, f[1], fontsize=6.5, va="center", ha="right", color="#777777", zorder=4)
    BOX[name] = (x, y - h, W, h)


def edge(name, side, frac=0.5):
    x, y, w, h = BOX[name]
    return {"l": (x, y + h * frac), "r": (x + w, y + h * frac),
            "t": (x + w * frac, y + h), "b": (x + w * frac, y)}[side]


def crow(ax, p, direction):
    """N 쪽 끝 까마귀발. direction: 상자 바깥으로 향하는 방향 (dx, dy)."""
    dx, dy = direction
    px, py = p
    base = (px + dx * 0.22, py + dy * 0.22)
    spread = 0.11
    for s in (-1, 0, 1):
        tip = (px - dy * spread * s, py + dx * spread * s) if s else (px, py)
        ax.plot([base[0], tip[0]], [base[1], tip[1]], color="#333333", lw=1.1, zorder=1)


def bar(ax, p, direction):
    dx, dy = direction
    px, py = p
    c = (px + dx * 0.16, py + dy * 0.16)
    ax.plot([c[0] - dy * 0.1, c[0] + dy * 0.1], [c[1] - dx * 0.1, c[1] + dx * 0.1], color="#333333", lw=1.2, zorder=1)


def link(ax, pts, parent_dir, child_dir, label=None, label_at=None, optional_child=False):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color="#333333", lw=1.1, zorder=1, ls=(0, (4, 2)) if optional_child else "-")
    bar(ax, pts[0], parent_dir)
    crow(ax, pts[-1], child_dir)
    if label:
        lx, ly = label_at or ((pts[0][0] + pts[-1][0]) / 2, (pts[0][1] + pts[-1][1]) / 2)
        ax.text(lx, ly, label, fontsize=7.5, color="#333333", ha="center", va="center", zorder=5,
                bbox=dict(fc="white", ec="none", pad=0.6))


def main():
    fig, ax = plt.subplots(figsize=(18.2, 9.4), dpi=200)
    ax.set_xlim(0, 18.6)
    ax.set_ylim(0.6, 9.4)
    ax.axis("off")
    for name in POS:
        draw_table(ax, name)

    L, R, U, D = (-1, 0), (1, 0), (0, 1), (0, -1)
    # 수집
    a, b = edge("source", "r", 0.7), edge("document", "l")
    link(ax, [a, (a[0] + 0.45, a[1]), (a[0] + 0.45, b[1]), b], R, L, "수집", (a[0] + 0.45, a[1] + 0.2))
    link(ax, [edge("source", "b", 0.5), edge("collect_log", "t", 0.5)], D, U, "수집 기록")
    link(ax, [edge("document", "b", 0.5), edge("chunk", "t", 0.5)], D, U, "청킹")
    # 첨부 (자기 참조)
    p1, p2 = edge("document", "b", 0.85), edge("document", "r", 0.12)
    link(ax, [p1, (p1[0], p1[1] - 0.3), (p2[0] + 0.22, p1[1] - 0.3), (p2[0] + 0.22, p2[1]), p2], D, L,
         "첨부", (p2[0] + 0.05, p1[1] - 0.3), optional_child=True)
    # 근거 문서, FAQ 작성
    a, b = edge("document", "r", 0.62), edge("faq", "l", 0.62)
    link(ax, [a, b], R, L, "근거 문서", ((a[0] + b[0]) / 2, a[1] + 0.2), optional_child=True)
    a, b = edge("manager", "l", 0.62), edge("faq", "r", 0.62)
    link(ax, [a, b], L, R, "FAQ 작성", ((a[0] + b[0]) / 2, a[1] + 0.2))
    # 보충 문서 업로드: manager 위로 돌아 document 위로
    a, b = edge("manager", "t", 0.3), edge("document", "t", 0.7)
    link(ax, [a, (a[0], 9.15), (b[0], 9.15), b], U, D, "보충 문서 업로드", ((a[0] + b[0]) / 2, 9.15), optional_child=True)
    # 답변 대기
    a, b = edge("pending_question", "t", 0.5), edge("faq", "b", 0.5)
    ax.plot([a[0], b[0]], [a[1], b[1]], color="#333333", lw=1.1, ls=(0, (4, 2)), zorder=1)
    bar(ax, a, U)
    bar(ax, b, D)
    ax.add_patch(matplotlib.patches.Circle((b[0], b[1] - 0.34), 0.07, fc="white", ec="#333333", lw=1.1, zorder=2))
    ax.text(a[0] + 0.12, (a[1] + b[1]) / 2, "답변 (1 : 0..1)", fontsize=7.5, va="center", zorder=5,
            bbox=dict(fc="white", ec="none", pad=0.6))
    link(ax, [edge("pending_question", "b", 0.5), edge("notify_token", "t", 0.5)], D, U, "알림 대상")
    a, b = edge("manager", "b", 0.2), edge("pending_question", "r", 0.5)
    link(ax, [a, (a[0], b[1]), b], D, R, "처리", (a[0], b[1] + 0.35), optional_child=True)
    # 관리자 쪽
    for child, frac, lab in (("auth_code", 0.5, "인증 코드"), ("login_session", 0.5, "로그인"), ("synonym", 0.5, "동의어 등록")):
        a = edge("manager", "r", 0.85 if child == "auth_code" else 0.5 if child == "login_session" else 0.15)
        b = edge(child, "l", frac)
        mx = a[0] + 0.35
        link(ax, [a, (mx, a[1]), (mx, b[1]), b], R, L, lab, ((mx + b[0]) / 2, b[1] + 0.2))
    # 중간 관리자 등록 (자기 참조)
    p1, p2 = edge("manager", "b", 0.75), edge("manager", "r", 0.05)
    link(ax, [p1, (p1[0], p1[1] - 0.3), (p2[0] + 0.15, p1[1] - 0.3), (p2[0] + 0.15, p2[1]), p2], D, L,
         "중간 관리자 등록", (p1[0] + 0.05, p1[1] - 0.3), optional_child=True)

    # 범례
    lx, ly = 15.6, 2.6
    ax.text(lx, ly, "범례", fontsize=9, fontweight="bold")
    for i, (g, (lab, col)) in enumerate(C.GROUPS.items()):
        ax.add_patch(Rectangle((lx, ly - 0.42 - i * 0.3), 0.25, 0.18, fc="#" + col, ec="none"))
        ax.text(lx + 0.35, ly - 0.33 - i * 0.3, lab, fontsize=8, va="center")
    ax.text(lx, ly - 1.75, "┼ 1 쪽    까마귀발: N 쪽    ○ 0 가능    점선: 선택 관계", fontsize=7.5, va="center")
    ax.text(lx, ly - 2.05, "통계·기록 테이블은 다른 테이블과 연결 없음", fontsize=7.2, va="center", color="#555555")

    fig.savefig(OUT / "erd.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", OUT / "erd.png")


if __name__ == "__main__":
    main()
