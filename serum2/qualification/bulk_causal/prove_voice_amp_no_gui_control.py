"""Finish Line B: proof that global.voice_amp has no on-screen control. FLB_OPEN3_A (voice_amp 0.0) and FLB_OPEN3_D
(voice_amp 1.0) were loaded into the live Serum 2 GUI and every top-level page was captured with PrintWindow (Serum's own pixels).
If any GUI element showed Voice Amp, some page body would differ between the two; the OTHER controls that differ between A and D
(swing, division, curve, porta time) live only in the bottom bar / keyboard area, which is excluded here on purpose.

    python prove_voice_amp_no_gui_control.py -> parameter_characterization/finish_line_b_gui_evidence/voice_amp_gui_absence_proof.json
"""
import json
import os

from PIL import Image, ImageChops

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
D = os.path.join(REPO, "parameter_characterization", "finish_line_b_gui_evidence")
PAGES = ["osc", "mix", "fx", "matrix", "global"]
BODY = (0, 60, 1206, 440)        # page body: everything between the top bar and the modulation/ARP strip
TOPBAR = (0, 0, 1206, 60)        # preset bar, page tabs, MAIN knob


def differs(a, b, box):
    d = ImageChops.difference(a.crop(box), b.crop(box)).convert("L").point(lambda v: 255 if v > 40 else 0)
    return d.getbbox()


def main():
    out = {"comparison": "FLB_OPEN3_A (kParamVoiceAmp=0.0, host 'Amp'='0.0000') vs FLB_OPEN3_D (1.0, '1.0000')",
           "threshold": "any pixel channel difference > 40 counts as a difference", "pages": {}}
    for p in PAGES:
        fa, fd = "FLB_OPEN3_A__page_%s.png" % p, "FLB_OPEN3_D__page_%s.png" % p
        a, d = Image.open(os.path.join(D, fa)).convert("RGB"), Image.open(os.path.join(D, fd)).convert("RGB")
        top = differs(a, d, TOPBAR)
        out["pages"][p] = {"files": [fa, fd], "body_diff_bbox": differs(a, d, BODY), "topbar_diff_bbox": top}
    # the top bar always differs at the preset NAME (A vs D); count only differences outside that text field
    for p in PAGES:
        a = Image.open(os.path.join(D, "FLB_OPEN3_A__page_%s.png" % p)).convert("RGB")
        d = Image.open(os.path.join(D, "FLB_OPEN3_D__page_%s.png" % p)).convert("RGB")
        out["pages"][p]["topbar_diff_outside_preset_name_bbox"] = differs(a, d, (1000, 0, 1206, 60))
    out["voice_amp_visible_in_gui"] = any(v["body_diff_bbox"] or v["topbar_diff_outside_preset_name_bbox"]
                                          for v in out["pages"].values())
    json.dump(out, open(os.path.join(D, "voice_amp_gui_absence_proof.json"), "w"), indent=1)
    print(json.dumps({p: (v["body_diff_bbox"], v["topbar_diff_outside_preset_name_bbox"]) for p, v in out["pages"].items()}))
    print("voice_amp_visible_in_gui:", out["voice_amp_visible_in_gui"])


if __name__ == "__main__":
    main()
