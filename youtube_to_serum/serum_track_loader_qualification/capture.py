"""Capture the Serum window for <nonce> to <out.png> via PrintWindow(PW_RENDERFULLCONTENT) — works when occluded."""
import ctypes
import sys

import win32gui
import win32ui
from PIL import Image

from ableton_windows import windows


def capture(nonce, out):
    top = [x for x in windows() if x["class"] == "Vst3PlugWindow" and nonce in x["title"]]
    assert len(top) == 1, top
    h = top[0]["hwnd"]
    l, t, r, b = win32gui.GetWindowRect(h)
    wd, ht = r - l, b - t
    src = win32gui.GetWindowDC(h)
    mfc = win32ui.CreateDCFromHandle(src)
    mem = mfc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(mfc, wd, ht)
    mem.SelectObject(bmp)
    ok = ctypes.windll.user32.PrintWindow(h, mem.GetSafeHdc(), 2)
    bits = bmp.GetBitmapBits(True)
    Image.frombuffer("RGB", (wd, ht), bits, "raw", "BGRX", 0, 1).save(out)
    win32gui.DeleteObject(bmp.GetHandle())
    mem.DeleteDC()
    mfc.DeleteDC()
    win32gui.ReleaseDC(h, src)
    return ok


if __name__ == "__main__":
    print("PrintWindow ok:", capture(sys.argv[1], sys.argv[2]))
