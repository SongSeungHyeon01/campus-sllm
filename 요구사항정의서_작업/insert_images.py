"""한글 COM으로 HWPX를 열어 '@@IMG:key:width@@' 자리를 그림으로 바꾸고 HWP/PDF로 저장한다.

사용: python insert_images.py <in.hwpx> <img_dir> <out.hwp> <out.pdf>
"""
import os
import re
import sys

import win32com.client as win32
from PIL import Image

IMAGES = {
    "arch": r"C:\dev\Campus sLLM\diagram_arch.png",
    "usecase": "diagram_usecase.png",
    "scr001": "wire_scr001_main.png",
    "scr002": "wire_scr002_category.png",
    "scr003": "wire_scr003_detail.png",
    "scr004": "wire_scr004_settings.png",
    "scr005": "wire_scr005_deadlines.png",
    "scr006": "wire_scr006_admin.png",
}


def find(hwp, text):
    act = hwp.CreateAction("RepeatFind")
    pset = act.CreateSet()
    act.GetDefault(pset)
    pset.SetItem("FindString", text)
    pset.SetItem("Direction", 0)
    pset.SetItem("IgnoreMessage", 1)
    pset.SetItem("FindRegExp", 0)
    return act.Execute(pset)


def main(src, img_dir, out_hwp, out_pdf):
    hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
    hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
    hwp.XHwpWindows.Item(0).Visible = False
    try:
        assert hwp.Open(os.path.abspath(src), "HWPX", "forceopen:true"), "open failed"
        hwp.MovePos(2)
        text = hwp.GetTextFile("TEXT", "")
        keys = re.findall(r"@@IMG:(\w+):(\d+)@@", text)
        for key, width in keys:
            path = IMAGES[key] if os.path.isabs(IMAGES[key]) else os.path.join(img_dir, IMAGES[key])
            w, h = Image.open(path).size
            width_mm = int(width)
            height_mm = round(width_mm * h / w)
            hwp.MovePos(2)
            assert find(hwp, f"@@IMG:{key}:{width}@@"), f"placeholder {key} not found"
            hwp.HAction.Run("Delete")
            ctrl = hwp.InsertPicture(os.path.abspath(path), True, 1, False, False, 0, width_mm, height_mm)
            assert ctrl is not None, f"insert failed: {key}"
            print("inserted", key, f"{width_mm}x{height_mm}mm")
        left = hwp.GetTextFile("TEXT", "").count("@@IMG:")
        assert left == 0, f"{left} placeholders left"
        print("save hwp", hwp.SaveAs(os.path.abspath(out_hwp), "HWP", ""))
        print("save pdf", hwp.SaveAs(os.path.abspath(out_pdf), "PDF", ""))
        print("pages", hwp.PageCount)
    finally:
        hwp.Clear(1)
        hwp.Quit()


if __name__ == "__main__":
    main(*sys.argv[1:5])
