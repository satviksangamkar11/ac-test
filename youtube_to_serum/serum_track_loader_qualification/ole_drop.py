"""G3: drop <file> onto the Serum window of track <nonce> via real OLE DoDragDrop. Usage: ole_drop.py <nonce> <file> [x y]
(x, y) = drop point relative to the Serum plugin window; default = preset-name bar."""
import os
import sys
import threading
import time

import pythoncom
import win32api
import win32con
import win32gui
import winerror
from win32com.server.util import wrap
from win32com.shell import shell

from ableton_windows import windows


def data_object(path):
    path = os.path.abspath(path)
    desk = shell.SHGetDesktopFolder()
    folder = desk.BindToObject(desk.ParseDisplayName(0, None, os.path.dirname(path))[1], None, shell.IID_IShellFolder)
    child = folder.ParseDisplayName(0, None, os.path.basename(path))[1]
    r = folder.GetUIObjectOf(0, [child], pythoncom.IID_IDataObject, 0)
    return r[1] if isinstance(r, tuple) else r


class DropSource:
    _com_interfaces_ = [pythoncom.IID_IDropSource]
    _public_methods_ = ["QueryContinueDrag", "GiveFeedback"]

    def __init__(self):
        self.go = threading.Event()
        self.calls = 0

    def QueryContinueDrag(self, esc, keys):
        self.calls += 1
        print("QCD", self.calls, esc, keys, self.go.is_set(), flush=True)
        if esc:
            return winerror.DRAGDROP_S_CANCEL
        return winerror.DRAGDROP_S_DROP if self.go.is_set() else winerror.S_OK

    def GiveFeedback(self, effect):
        return winerror.DRAGDROP_S_USEDEFAULTCURSORS


def idle_ms():
    return win32api.GetTickCount() - win32api.GetLastInputInfo()


def drop(nonce, path, rel=(700, 48)):
    t0 = time.time()
    while idle_ms() < 3000:  # never race the user's own mouse
        if time.time() - t0 > 120:
            raise SystemExit("USER_ACTIVE: no 3 s idle window within 120 s")
        time.sleep(0.2)
    top = [x for x in windows() if x["class"] == "Vst3PlugWindow" and nonce in x["title"]]
    if len(top) != 1:
        raise SystemExit("SERUM_WINDOW_NOT_FOUND: %d candidates" % len(top))
    h = top[0]["hwnd"]
    l, t, _, _ = win32gui.GetWindowRect(h)
    pt = (l + rel[0], t + rel[1])
    hit = win32gui.WindowFromPoint(pt)
    if hit != h and win32gui.GetAncestor(hit, win32con.GA_ROOT) != h:  # covered -> raise Serum to top for the drop
        win32gui.SetWindowPos(h, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        win32gui.SetWindowPos(h, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        hit = win32gui.WindowFromPoint(pt)
    if win32gui.GetAncestor(hit, win32con.GA_ROOT) != h:
        raise SystemExit("DROP_POINT_OCCLUDED: %s" % win32gui.GetClassName(hit))

    pythoncom.OleInitialize()
    src = DropSource()
    saved = win32api.GetCursorPos()
    W, H = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
    box = (int(W * 0.5), int(H * 0.5), 60, 60)  # small source window; the press lands ON it so this thread owns the drag
    result = {}

    def mv(x, y):
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE | win32con.MOUSEEVENTF_ABSOLUTE,
                             int(x * 65535 / (W - 1)), int(y * 65535 / (H - 1)), 0, 0)

    def wndproc(hwnd, msg, wp, lp):
        if msg == win32con.WM_LBUTTONDOWN and "r" not in result:
            result["r"] = pythoncom.DoDragDrop(data_object(path), wrap(src, pythoncom.IID_IDropSource), 7)
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wp, lp)

    wc = win32gui.WNDCLASS()
    wc.lpszClassName, wc.lpfnWndProc, wc.hInstance = "DropSrc%d" % os.getpid(), wndproc, win32api.GetModuleHandle(None)
    win32gui.RegisterClass(wc)
    src_hwnd = win32gui.CreateWindowEx(win32con.WS_EX_TOPMOST | win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE,
                                       wc.lpszClassName, "dropsrc", win32con.WS_POPUP | win32con.WS_VISIBLE,
                                       box[0], box[1], box[2], box[3], 0, 0, wc.hInstance, None)
    cx, cy = box[0] + 30, box[1] + 30

    def steer():
        time.sleep(0.3)
        mv(cx, cy)
        time.sleep(0.15)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.4)
        n = 30
        for i in range(1, n + 1):
            mv(cx + (pt[0] - cx) * i / n, cy + (pt[1] - cy) * i / n)
            time.sleep(0.02)
        for k in range(8):
            mv(pt[0] + (k % 2), pt[1])
            time.sleep(0.05)
        print("steer end; cursor", win32api.GetCursorPos(), "calls", src.calls, flush=True)
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
        win32gui.DestroyWindow(src_hwnd)
        win32api.SetCursorPos(saved)
    r = result.get("r", "TIMEOUT")
    print("DoDragDrop ->", r, "| QueryContinueDrag calls:", src.calls, "| drop point", pt)
    return r


if __name__ == "__main__":
    a = sys.argv
    drop(a[1], a[2], (int(a[3]), int(a[4])) if len(a) > 4 else (700, 48))
