"""Capture the Serum FX rack of the currently loaded preset, top to bottom, as PNGs (GUI evidence for Finish Line B).
Finds the Serum plugin window by title, brings it to the front, scrolls with the wheel over the FX logo column only
(wheel-over-knob mutates the value), and grabs ONLY that window's rack area. Aborts if Serum is not the foreground
window, so nothing else on screen is ever captured or scrolled.

    python gui_capture_rack.py <preset_name> [n_steps]
"""
import ctypes
import ctypes.wintypes as wt
import os
import sys
import time

from PIL import ImageGrab

U = ctypes.windll.user32
U.SetProcessDPIAware()
S = 1920 / 1456                     # computer-use frame -> physical pixels (window measured at frame x=89, y=45)
LOGO_REL = (int(368 * S), int(138 * S))
RACK_REL = (0, int(85 * S), int(1125 * S), int(395 * S))
TICKS = 5
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "parameter_characterization",
                   "finish_line_b_gui_evidence")


def serum_hwnd():
    found = []
    proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

    def cb(h, _):
        n = U.GetWindowTextLengthW(h)
        b = ctypes.create_unicode_buffer(n + 1)
        U.GetWindowTextW(h, b, n + 1)
        if b.value.startswith("Serum 2/") and U.IsWindowVisible(h):
            found.append(h)
        return True
    U.EnumWindows(proc(cb), 0)
    if not found:
        sys.exit("Serum plugin window not found")
    return found[0]


def print_window(h):
    from PIL import Image
    G = ctypes.windll.gdi32
    r = wt.RECT()
    U.GetWindowRect(h, ctypes.byref(r))
    w, hh = r.right - r.left, r.bottom - r.top
    hdc = U.GetWindowDC(h)
    mdc = G.CreateCompatibleDC(hdc)
    bmp = G.CreateCompatibleBitmap(hdc, w, hh)
    G.SelectObject(mdc, bmp)
    U.PrintWindow(h, mdc, 2)   # PW_RENDERFULLCONTENT

    class BMI(ctypes.Structure):
        _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32), ("biHeight", ctypes.c_int32),
                    ("biPlanes", ctypes.c_uint16), ("biBitCount", ctypes.c_uint16), ("rest", ctypes.c_uint32 * 6)]
    bi = BMI(ctypes.sizeof(BMI), w, -hh, 1, 32)
    buf = ctypes.create_string_buffer(w * hh * 4)
    G.GetDIBits(mdc, bmp, 0, hh, buf, ctypes.byref(bi), 0)
    G.DeleteObject(bmp)
    G.DeleteDC(mdc)
    U.ReleaseDC(h, hdc)
    return Image.frombuffer("RGBA", (w, hh), buf, "raw", "BGRA", 0, 1).convert("RGB")


def front(h):
    U.ShowWindow(h, 5)
    U.SetForegroundWindow(h)
    time.sleep(0.4)
    if U.GetForegroundWindow() != h:
        sys.exit("Serum window is not in front; refusing to scroll/capture")


def main():
    name, steps = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 4
    os.makedirs(OUT, exist_ok=True)
    h = serum_hwnd()
    front(h)
    r = wt.RECT()
    U.GetWindowRect(h, ctypes.byref(r))
    logo = (r.left + LOGO_REL[0], r.top + LOGO_REL[1])
    bbox = (r.left + RACK_REL[0], r.top + RACK_REL[1], r.left + RACK_REL[2], r.top + RACK_REL[3])

    def wheel(ticks):
        front(h)
        U.SetCursorPos(*logo)
        for _ in range(abs(ticks)):
            U.mouse_event(0x0800, 0, 0, 120 if ticks > 0 else -120, 0)
            time.sleep(0.03)
        U.SetCursorPos(r.left + 400, r.top + 12)   # park on the title bar so no hover tooltip covers a slot
        time.sleep(0.6)

    if steps == -2:  # press-and-hold (no movement, so no value change) on the GLOBAL-page CURVE control: its tooltip shows the value
        front(h)
        cx, cy = r.left + int((1173 - 89) * S), r.top + int((737 - 45) * S)
        U.SetCursorPos(cx, cy)
        time.sleep(0.3)
        U.mouse_event(2, 0, 0, 0, 0)
        time.sleep(0.9)
        p = os.path.abspath(os.path.join(OUT, "%s__curve_tooltip.png" % name))
        print_window(h).save(p)
        U.mouse_event(4, 0, 0, 0, 0)
        print(p)
        return
    if steps < 0:    # every top-level page (tab clicks only), PrintWindow each
        for tab, (fx, fy) in (("osc", (276, 112)), ("mix", (340, 112)), ("fx", (404, 112)), ("matrix", (469, 112)),
                              ("global", (533, 112))):
            front(h)
            cx, cy = r.left + int((fx - 89) * S), r.top + int((fy - 45) * S)
            U.SetCursorPos(cx - 6, cy - 4)
            time.sleep(0.2)
            U.SetCursorPos(cx, cy)
            time.sleep(0.3)
            U.mouse_event(2, 0, 0, 0, 0)
            time.sleep(0.12)
            U.mouse_event(4, 0, 0, 0, 0)
            U.SetCursorPos(r.left + 400, r.top + 12)
            time.sleep(1.2)
            p = os.path.abspath(os.path.join(OUT, "%s__page_%s.png" % (name, tab)))
            print_window(h).save(p)
            print(p)
        return
    if steps == 0:   # whole plugin window via PrintWindow: Serum's own pixels even when another window overlaps it
        p = os.path.abspath(os.path.join(OUT, "%s__window.png" % name))
        print_window(h).save(p)
        print(p)
        return
    wheel(40)
    shots = []
    for i in range(steps):
        front(h)
        p = os.path.abspath(os.path.join(OUT, "%s__rack_%02d.png" % (name, i)))
        im = ImageGrab.grab(bbox=bbox)
        im.save(p)
        shots.append(im.crop((500, 0, 1000, im.height)))   # name + first knobs column only, for a quick read
        print(p)
        wheel(-TICKS)
    from PIL import Image
    sheet = Image.new("RGB", (500, sum(s.height for s in shots)))
    y = 0
    for s in shots:
        sheet.paste(s, (0, y))
        y += s.height
    sheet.save(os.path.abspath(os.path.join(OUT, "%s__names_sheet.png" % name)))


if __name__ == "__main__":
    main()
