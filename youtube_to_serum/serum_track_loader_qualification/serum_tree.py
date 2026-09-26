"""Dump the child-window tree of the Serum plugin window: class, rect, WS_EX_ACCEPTFILES, OLE drop-target props."""
import ctypes
import ctypes.wintypes as w
import sys

from ableton_windows import windows

u = ctypes.windll.user32
u.GetWindowLongPtrW.restype = ctypes.c_ssize_t
u.GetPropW.restype = ctypes.c_void_p
nonce = sys.argv[1]
top = [x for x in windows() if x["class"] == "Vst3PlugWindow" and nonce in x["title"]]
assert len(top) == 1, top


def info(h, depth):
    c, r = ctypes.create_unicode_buffer(256), w.RECT()
    u.GetClassNameW(h, c, 256)
    u.GetWindowRect(h, ctypes.byref(r))
    ex = u.GetWindowLongPtrW(h, -20)
    ole = u.GetPropW(h, "OleDropTargetInterface") or u.GetPropW(h, "OleDropTargetMarshalHwnd")
    print("  " * depth, h, c.value, [r.left, r.top, r.right, r.bottom],
          "ACCEPTFILES" if ex & 0x10 else "", "OLE_DROP_TARGET" if ole else "")


def walk(h, depth):
    info(h, depth)
    kids = []
    cb = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)(lambda k, _: kids.append(k) or True)
    u.EnumChildWindows(h, cb, 0)
    for k in kids:
        if u.GetParent(k) == h:
            walk(k, depth + 1)


walk(top[0]["hwnd"], 0)
