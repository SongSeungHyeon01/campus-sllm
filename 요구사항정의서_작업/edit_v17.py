"""요구사항 정의서 v1.6 HWP를 한글 COM으로 열어 v1.7 수정(FR-010 아산 주말·방학, 표지 날짜, 문서 버전 행)을 적용한다."""
import os, sys
import win32com.client as win32

SRC, OUT_HWP, OUT_PDF = map(os.path.abspath, sys.argv[1:4])

REPLACE = [
    ("아산캠퍼스(천안터미널 구간, 천안아산KTX역 구간)의 통학버스",
     "아산캠퍼스(평일 천안터미널·천안아산KTX역 구간, 주말·공휴일·방학)의 통학버스"),
    ("데이터 출처: 학교 홈페이지 통학버스 메뉴. 시간표 변경일자를",
     "데이터 출처: 학교 홈페이지 통학버스 메뉴(캠퍼스별 통학버스, 주말·공휴일·방학 페이지). 시간표 변경일자를"),
    ("2026. 10. 09.", "2026. 10. 10."),
]
ROW = ["1.7", "2026-10-10", "송승현", "통학버스 요구사항(FR-010)에 아산캠퍼스 주말·공휴일·방학 시간표 추가"]


def find(hwp, text):
    act = hwp.CreateAction("RepeatFind"); p = act.CreateSet(); act.GetDefault(p)
    p.SetItem("FindString", text); p.SetItem("Direction", 0); p.SetItem("IgnoreMessage", 1)
    return act.Execute(p)


def replace_all(hwp, a, b):
    act = hwp.CreateAction("AllReplace"); p = act.CreateSet(); act.GetDefault(p)
    p.SetItem("FindString", a); p.SetItem("ReplaceString", b)
    p.SetItem("IgnoreMessage", 1); p.SetItem("Direction", 2)
    return act.Execute(p)


def insert_text(hwp, text):
    act = hwp.CreateAction("InsertText"); p = act.CreateSet(); act.GetDefault(p)
    p.SetItem("Text", text); act.Execute(p)


hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
hwp.XHwpWindows.Item(0).Visible = False
try:
    assert hwp.Open(SRC, "HWP", "forceopen:true"), "open failed"
    before = hwp.GetTextFile("TEXT", "")
    for a, b in REPLACE:
        n = before.replace("\r\n", "").count(a)
        hwp.MovePos(2)
        replace_all(hwp, a, b)
        print("replace", repr(a[:20]), "found in text:", n)
    hwp.MovePos(2)
    assert find(hwp, "앱을 대화형 중심으로"), "history row not found"
    hwp.HAction.Run("TableAppendRow")
    hwp.HAction.Run("TableLowerCell")
    hwp.HAction.Run("TableColBegin")
    for i, t in enumerate(ROW):
        if i:
            hwp.HAction.Run("TableRightCell")
        insert_text(hwp, t)
    after = hwp.GetTextFile("TEXT", "")
    flat = after.replace("\r\n", "")
    for _, b in REPLACE:
        print("present:", b[:25], b in flat)
    print("row present:", ROW[3] in flat)
    print("save hwp", hwp.SaveAs(OUT_HWP, "HWP", ""))
    print("save pdf", hwp.SaveAs(OUT_PDF, "PDF", ""))
    print("pages", hwp.PageCount)
finally:
    hwp.Clear(1)
    hwp.Quit()
