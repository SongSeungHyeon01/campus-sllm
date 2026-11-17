import os, sys
import win32com.client as win32
src, dst = map(os.path.abspath, sys.argv[1:3])
hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
hwp.XHwpWindows.Item(0).Visible = False
try:
    assert hwp.Open(src, "HWP", "forceopen:true")
    print("save", hwp.SaveAs(dst, "HWPX", ""))
finally:
    hwp.Clear(1); hwp.Quit()
