"""Load an existing .SerumPreset into a Serum 2 editor via OLE drag/drop (G3).

Serum's editor registers only an OLE drop target (no WS_EX_ACCEPTFILES), so
WM_DROPFILES is not an option. This module:

  1. finds the Serum plugin window for a track (title follows the track name),
  2. restores Ableton's main window without activating it if it is minimized
     (a minimized Live suppresses plugin windows),
  3. waits for the user's mouse to be idle,
  4. parks the cursor over Serum's preset-name bar and runs DoDragDrop with a
     shell IDataObject (CF_HDROP) for the file, with an IDropSource that drops
     as soon as the target has seen a DragOver -- no button press is required,
     so no click ever lands on the host UI.

No parameter reconstruction, no readback: the job is only "hand this file to
Serum's native loader". Windows-only; needs pywin32.

Run standalone:  python serum2/ableton/serum_preset_drop.py "<track>" <preset>
"""
from __future__ import annotations

import ctypes
import os
import sys
import time
from ctypes import wintypes

import pythoncom
import win32con
import win32gui
from win32com.server.util import wrap
from win32com.shell import shell

user32 = ctypes.windll.user32

DRAGDROP_S_DROP = 0x00040100
DRAGDROP_S_CANCEL = 0x00040101
DRAGDROP_S_USEDEFAULTCURSORS = 0x00040102
DROPEFFECT_COPY = 1

# Serum's header (preset name bar) sits near the top centre of the editor.
PRESET_BAR_REL = (0.5, 0.06)


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


def _idle_ms() -> int:
    lii = _LASTINPUTINFO(ctypes.sizeof(_LASTINPUTINFO), 0)
    user32.GetLastInputInfo(ctypes.byref(lii))
    return ctypes.windll.kernel32.GetTickCount() - lii.dwTime


def wait_for_idle(idle_s: float = 3.0, timeout_s: float = 60.0) -> None:
    deadline = time.monotonic() + timeout_s
    while _idle_ms() < idle_s * 1000:
        if time.monotonic() > deadline:
            raise TimeoutError(f"user input never idle for {idle_s}s")
        time.sleep(0.2)


def _windows() -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    win32gui.EnumWindows(lambda h, _: out.append((h, win32gui.GetWindowText(h))), None)
    return out


def restore_ableton_noactivate() -> None:
    for hwnd, title in _windows():
        if "Ableton Live" in title and win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)


def find_serum_hwnd(track_name: str, timeout_s: float = 10.0) -> int:
    """Exactly one visible Serum window whose title names the track."""
    deadline = time.monotonic() + timeout_s
    restored = False
    while True:
        hits = [h for h, t in _windows()
                if "Serum" in t and track_name in t and win32gui.IsWindowVisible(h)]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise RuntimeError(f"{len(hits)} Serum windows for track {track_name!r}")
        if not restored:
            restore_ableton_noactivate()
            restored = True
        if time.monotonic() > deadline:
            raise LookupError(f"no Serum window for track {track_name!r}")
        time.sleep(0.25)


class _DropSource:
    """Drops once the cursor has sat over the target for a few ticks."""
    _public_methods_ = ["QueryContinueDrag", "GiveFeedback"]
    _com_interfaces_ = [pythoncom.IID_IDropSource]

    def __init__(self, ticks: int = 5, max_ticks: int = 400):
        self.n = 0
        self.ticks = ticks
        self.max_ticks = max_ticks

    def QueryContinueDrag(self, escape_pressed, key_state):
        self.n += 1
        if escape_pressed or self.n > self.max_ticks:
            return DRAGDROP_S_CANCEL
        if self.n == 2:
            # Nudge so OLE delivers DragEnter/DragOver to the window under the cursor.
            x, y = win32gui.GetCursorPos()
            win32gui.SetCursorPos((x + 1, y))
        return DRAGDROP_S_DROP if self.n >= self.ticks else 0

    def GiveFeedback(self, effect):
        return DRAGDROP_S_USEDEFAULTCURSORS


def _file_data_object(path: str):
    folder, name = os.path.split(os.path.abspath(path))
    desktop = shell.SHGetDesktopFolder()
    _, pidl, _ = desktop.ParseDisplayName(0, None, folder)
    sub = desktop.BindToObject(pidl, None, shell.IID_IShellFolder)
    _, child, _ = sub.ParseDisplayName(0, None, name)
    return sub.GetUIObjectOf(0, [child], pythoncom.IID_IDataObject, 0)[1]


def ole_drop_file(hwnd: int, path: str, idle_s: float = 3.0) -> int:
    """Drop `path` onto `hwnd`. Returns the DoDragDrop HRESULT (never raises on it)."""
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    l, t, r, b = win32gui.GetWindowRect(hwnd)
    target = (int(l + (r - l) * PRESET_BAR_REL[0]), int(t + (b - t) * PRESET_BAR_REL[1]))
    pythoncom.OleInitialize()
    try:
        data = _file_data_object(path)
        wait_for_idle(idle_s)
        prev = win32gui.GetCursorPos()
        win32gui.SetCursorPos(target)
        try:
            result = pythoncom.DoDragDrop(data, wrap(_DropSource(), pythoncom.IID_IDropSource),
                                          DROPEFFECT_COPY)
        except pythoncom.com_error as e:
            result = e.hresult
        finally:
            win32gui.SetCursorPos(prev)
        return result
    finally:
        pythoncom.OleUninitialize()


def load_preset_into_serum(track_name: str, preset_path: str) -> dict:
    hwnd = find_serum_hwnd(track_name)
    hr = ole_drop_file(hwnd, preset_path)
    return {"hwnd": hwnd, "title": win32gui.GetWindowText(hwnd),
            "dropped": hr == DRAGDROP_S_DROP, "hresult": hr}


def create_serum_track(preset_path: str, name: str | None = None, *, ableton) -> dict:
    """Create a MIDI track, load Serum 2 on it, and hand `preset_path` to Serum.

    `ableton` is the Ableton MCP client used by G1; it must expose
    create_midi_track() -> index, set_track_name(index, name) and
    load_serum(index) (the Live-browser load that auto-opens the editor).
    """
    name = name or f"{os.path.splitext(os.path.basename(preset_path))[0]} {os.urandom(2).hex()}"
    idx = ableton.create_midi_track()
    ableton.set_track_name(idx, name)
    ableton.load_serum(idx)
    return {"track_index": idx, "track_name": name, **load_preset_into_serum(name, preset_path)}


if __name__ == "__main__":
    print(load_preset_into_serum(sys.argv[1], sys.argv[2]))
