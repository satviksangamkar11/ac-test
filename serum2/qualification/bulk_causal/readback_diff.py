"""Diff two .SerumPreset files and print every raw leaf that differs. For residual controls whose raw path is
unknown (voice_priority, the 3 unresolved arp.transpose.shape labels): change ONE thing in Serum, save under a
new name, then run this against the untouched baseline. No guessing of raw keys needed.

    python readback_diff.py <baseline.SerumPreset> <changed.SerumPreset>
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from campaign_derive import leaves  # noqa: E402
from preset_build import unpack_file  # noqa: E402


def main(a, b):
    da, db = unpack_file(a).data, unpack_file(b).data
    d = leaves(da, db)
    if not d:
        print("NO DIFFERENCE -- the two files are identical. Did the save actually happen, or did the change not stick?")
        return
    print("%d leaf(ves) differ:" % len(d))
    for path, old, new in d:
        print("  %s\n    baseline: %r\n    changed:  %r" % (json.dumps(path), old, new))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python readback_diff.py <baseline.SerumPreset> <changed.SerumPreset>")
    main(sys.argv[1], sys.argv[2])
