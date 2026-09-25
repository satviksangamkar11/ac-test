"""Windows helpers for loading a .SerumPreset through Serum's OWN drag/drop loader (real OLE DoDragDrop).

Qualified 2026-09-25/26 on Live 12 Suite + Serum 2.0.23: the drag must START from a window owned by this process
(pressing on someone else's window never enters the OLE loop), then the cursor is moved onto the Serum editor and released.
"""
import ctypes
import ctypes.wintypes as w
import hashlib
import os
import threading
import time

import psutil
import pythoncom
import win32api
import win32con
import win32gui
import win32ui
import winerror
from PIL import Image, ImageChops
from win32com.server.util import wrap
from win32com.shell import shell

PINNED_SHA256 = "9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3"  # Serum 2.0.23
DROP_REL = (700, 48)  # drop point inside the Serum window: the preset-name bar
_u = ctypes.windll.user32
_lock = threading.Lock()  # one drag at a time: it owns the mouse


def _live_pid():
    for p in psutil.process_iter(["name", "exe"]):
        if "ableton live" in (p.info["exe"] or "").lower():
            return p.pid


def ensure_live_visible():
    """Live suppresses plugin windows while minimized; restore without stealing focus."""
    h = win32gui.FindWindow("Ableton Live Window Class", None)
    if h and win32gui.IsIconic(h):
        win32gui.ShowWindow(h, win32con.SW_SHOWNOACTIVATE)
        time.sleep(1.0)


def serum_module_sha256(pid=None):
    """SHA-256 of the Serum2.vst3 mapped INTO Live's process (not merely the file on disk)."""
    pid = pid or _live_pid()
    paths = {m.path for m in psutil.Process(pid).memory_maps() if "serum2.vst3" in m.path.lower()}
    return {p: hashlib.sha256(open(p, "rb").read()).hexdigest() for p in paths}


def find_serum_windows(nonce):
    pid, out = _live_pid(), []

    @ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
    def cb(h, _):
        wp = w.DWORD()
        _u.GetWindowThreadProcessId(h, ctypes.byref(wp))
        if wp.value == pid and _u.IsWindowVisible(h) and win32gui.GetClassName(h) == "Vst3PlugWindow" \
                and nonce in win32gui.GetWindowText(h):
            out.append(h)
        return True

    _u.EnumWindows(cb, 0)
    return out


def wait_for_window(nonce, timeout=8.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        hs = find_serum_windows(nonce)
        if hs:
            return hs
        time.sleep(0.2)
    return []


def capture(hwnd):
    l, t, r, b = win32gui.GetWindowRect(hwnd)
    wd, ht = r - l, b - t
    src = win32gui.GetWindowDC(hwnd)
    mfc = win32ui.CreateDCFromHandle(src)
    mem = mfc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(mfc, wd, ht)
    mem.SelectObject(bmp)
    _u.PrintWindow(hwnd, mem.GetSafeHdc(), 2)  # PW_RENDERFULLCONTENT: works while occluded
    img = Image.frombuffer("RGB", (wd, ht), bmp.GetBitmapBits(True), "raw", "BGRX", 0, 1)
    win32gui.DeleteObject(bmp.GetHandle())
    mem.DeleteDC()
    mfc.DeleteDC()
    win32gui.ReleaseDC(hwnd, src)
    return img


NAME_BAR = (540, 36, 940, 62)  # preset-name field in the Serum header (window coords): changes for ANY preset load


def changed_fraction(a, b, box=None):
    if box:
        a, b = a.crop(box), b.crop(box)
    d = ImageChops.difference(a.convert("L"), b.convert("L")).point(lambda v: 255 if v > 24 else 0)
    return sum(1 for v in d.getdata() if v) / (a.size[0] * a.size[1])


def _data_object(path):
    path = os.path.abspath(path)
    desk = shell.SHGetDesktopFolder()
    folder = desk.BindToObject(desk.ParseDisplayName(0, None, os.path.dirname(path))[1], None, shell.IID_IShellFolder)
    child = folder.ParseDisplayName(0, None, os.path.basename(path))[1]
    r = folder.GetUIObjectOf(0, [child], pythoncom.IID_IDataObject, 0)
    return r[1] if isinstance(r, tuple) else r


class _Source:
    _com_interfaces_ = [pythoncom.IID_IDropSource]
    _public_methods_ = ["QueryContinueDrag", "GiveFeedback"]

    def __init__(self):
        self.go = threading.Event()

    def QueryContinueDrag(self, esc, keys):
        if esc:
            return winerror.DRAGDROP_S_CANCEL
        return winerror.DRAGDROP_S_DROP if self.go.is_set() else winerror.S_OK

    def GiveFeedback(self, effect):
        return winerror.DRAGDROP_S_USEDEFAULTCURSORS


def ole_drop(hwnd, path, rel=DROP_REL, idle_ms=3000, idle_wait=60.0):
    """Drop `path` on the Serum window. Returns the OLE drop effect (0 = rejected). Raises RuntimeError on setup errors."""
    with _lock:
        t0 = time.time()
        while win32api.GetTickCount() - win32api.GetLastInputInfo() < idle_ms:  # never race the user's mouse
            if time.time() - t0 > idle_wait:
                raise RuntimeError("USER_ACTIVE: no %d ms idle window in %.0f s" % (idle_ms, idle_wait))
            time.sleep(0.2)
        l, t, _, _ = win32gui.GetWindowRect(hwnd)
        pt = (l + rel[0], t + rel[1])
        if win32gui.GetAncestor(win32gui.WindowFromPoint(pt), win32con.GA_ROOT) != hwnd:
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            if win32gui.GetAncestor(win32gui.WindowFromPoint(pt), win32con.GA_ROOT) != hwnd:
                raise RuntimeError("DROP_POINT_OCCLUDED")

        pythoncom.OleInitialize()
        src, result, saved = _Source(), {}, win32api.GetCursorPos()
        W, H = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
        box = (int(W * 0.5), int(H * 0.5))
        dobj = _data_object(path)

        def mv(x, y):
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE | win32con.MOUSEEVENTF_ABSOLUTE,
                                 int(x * 65535 / (W - 1)), int(y * 65535 / (H - 1)), 0, 0)

        def wndproc(h, msg, wp, lp):
            if msg == win32con.WM_LBUTTONDOWN and "r" not in result:
                result["r"] = pythoncom.DoDragDrop(dobj, wrap(src, pythoncom.IID_IDropSource), 7)
                return 0
            return win32gui.DefWindowProc(h, msg, wp, lp)

        wc = win32gui.WNDCLASS()
        wc.lpszClassName, wc.lpfnWndProc, wc.hInstance = "SerumDropSrc%d_%d" % (os.getpid(), time.time_ns()), wndproc, win32api.GetModuleHandle(None)
        win32gui.RegisterClass(wc)
        sw = win32gui.CreateWindowEx(win32con.WS_EX_TOPMOST | win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE,
                                     wc.lpszClassName, "dropsrc", win32con.WS_POPUP | win32con.WS_VISIBLE,
                                     box[0], box[1], 60, 60, 0, 0, wc.hInstance, None)
        cx, cy = box[0] + 30, box[1] + 30

        def steer():
            time.sleep(0.3)
            mv(cx, cy)
            time.sleep(0.15)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.4)
            for i in range(1, 31):
                mv(cx + (pt[0] - cx) * i / 30, cy + (pt[1] - cy) * i / 30)
                time.sleep(0.02)
            for k in range(8):  # hover so DragEnter/DragOver run on the target
                mv(pt[0] + (k % 2), pt[1])
                time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            src.go.set()

        threading.Thread(target=steer, daemon=True).start()
        t_end = time.time() + 25
        try:
            while "r" not in result and time.time() < t_end:
                win32gui.PumpWaitingMessages()
                time.sleep(0.005)
        finally:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            win32gui.DestroyWindow(sw)
            win32gui.UnregisterClass(wc.lpszClassName, wc.hInstance)
            win32api.SetCursorPos(saved)
        if "r" not in result:
            raise RuntimeError("DRAG_TIMEOUT")
        return result["r"]
