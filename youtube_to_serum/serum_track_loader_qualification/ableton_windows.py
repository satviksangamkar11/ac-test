"""List visible top-level windows owned by Ableton Live processes: hwnd, class, title, rect. Optional arg: nonce filter."""
import ctypes
import ctypes.wintypes as w
import json
import sys

u, k = ctypes.windll.user32, ctypes.windll.kernel32


def exe_of(pid):
    h = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    buf, n = ctypes.create_unicode_buffer(1024), w.DWORD(1024)
    k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n))
    k.CloseHandle(h)
    return buf.value


def windows():
    out = []

    @ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
    def cb(hwnd, _):
        if not u.IsWindowVisible(hwnd):
            return True
        pid = w.DWORD()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        exe = exe_of(pid.value)
        if "ableton" not in exe.lower():
            return True
        t, c, r = ctypes.create_unicode_buffer(512), ctypes.create_unicode_buffer(256), w.RECT()
        u.GetWindowTextW(hwnd, t, 512)
        u.GetClassNameW(hwnd, c, 256)
        u.GetWindowRect(hwnd, ctypes.byref(r))
        out.append({"hwnd": hwnd, "pid": pid.value, "class": c.value, "title": t.value,
                    "rect": [r.left, r.top, r.right, r.bottom], "exe": exe})
        return True

    u.EnumWindows(cb, 0)
    return out


if __name__ == "__main__":
    ws = windows()
    if len(sys.argv) > 1:
        ws = [x for x in ws if sys.argv[1] in x["title"]]
    print(json.dumps(ws, indent=1))
