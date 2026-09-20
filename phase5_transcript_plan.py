#!/usr/bin/env python3
"""Phase 5: Generate TranscriptCuePlan for HEEGN1Xl5o4 tutorial."""

import json
import hashlib
from datetime import datetime

# Transcript text from the video
transcript_text = """[Music] Hey everyone, this is Lady from Abstract Music Lab and today I'm back here in the sound design channel. Today we're creating a lead called Prague and it sounds like this. If you want to listen to this in solo, [Music] you can see that there's some modulation in the sound even in the MIDI directly in the MIDI that you get from the pack. You can see that there's a bit of mod wheel modulation. Now, if you want to listen to this in context with side chain, [Music] really cool sound that you can find over here in the description below in the Serum 2 melodic progressive pack that you can find at Production Music Live's website. But now, let's initialize the sound and let's get started with this tutorial. We're going to deactivate shaper box and we're going to activate serum. This is the initial preset. Let's get started by selecting mono. Now we're going to go into default shapes. We're going to select a saw minus one unison to make it with a bit more voices but lastly tune. And we're going to select here phase distortion from B. Now let's activate B default waves default shape saw but this is going to be plus one and level all the way down to zero. But now just so you could listen to what it does. Now we're going to select here a free chaos Laurens in the LFO and we're going to select the X. We're going to put it to the fine as 10. Something like this. and also to be something like this. But now let's modulate this a little bit. So Kas Lawrence free, this is going to be a half. [Music] We're going to select a noise white filter up level all the way down to zero. Why? Because we're modulating this with envelope 3. So envelope 3 with the amount of modulation that we need. Make this into a plucker and a bit more release. Awesome. Now envelope one. Envelope one is going to be the main envelope of the sound. And we're going to do pretty much the same thing, but just a bit more release. Maybe a bit less. And if you haven't selected mono it's going to make a lot of difference. So, select mono filter MG18. [Music] This is going to be only A. You can select B, but B is not playing, so that's okay. So only A. We're going to modulate this with envelope 2. So let's first place the cut off where it needs to be, which we barely listen. But now envelope 2. And this is going to go 100%. More resonance. And that's it. Now let's modulate envelope 2. So sustain all the way down. Decay a bit down as well. Something like this. Release a bit more up. Yeah. Something like this. Maybe a bit more up. Yeah. Something like this. But now this handle, we're going to pick it and put a lot down. [Music] Now, in addition to that, we're also going to go into envelope 4. And in envelope 4, sustain all the way down the decay pretty much all the way down as well. We're going to intensify the pluck with this. So, envelope 4 here, we're going to select here main tuning in the global just so you can listen. Can you see the plucky feeling without? But we're going to select a bit less of this. [Music] And we're sending a bit of filter one to bus number one. [Applause] Important to mention now when we go here into the effects, we're going to go here first into the mix. Bus number one is going directly out. So, what we're going to do here into bus number one, we're going to select a convolve and we're going to select a long digital hall number two, which is pretty much going to make a reverb out of this, smaller, but all the way with the mix. Now, we're going to use an EQ to pretty much shape this sound. gain all the way down. A little bit less here. Now effects main. We're going to go and start by using a distortion overdrive. [Music] more drive, which is going to turn the loudness a lot up in your sound. A bit less mix. You're not going to hear a difference in the video because I'm going to level match everything so it remains a constant and a smooth listening to you, but it's going to make the sound a lot louder in your side. Now, hyper just to make things a bit wider. Rate all the way down. Mix a little bit down as well. Something like this. Seven voices. And a bit of the tune as well. Yeah. Size down and the dimension a bit up as well. Without make things a bit wider. Now equalizer [Music] all the way up. Gain all the way down. Delay. Ping pong 116, [Music] but a lot less Q here. [Music] A bit more feed. [Music] That's it pretty much. Now, lastly, just a bit of compression. if we needed, if there's anything going off [Music] and a bit of gain here. [Music] But here's there's one thing missing that I left it to the end. What you can do here is you can go here and select a filter. We're going to place this in the middle of the hyper and the EQ. And we're going to select here in the miscellaneous in this Sfield 2 filters MG ladder. Now this going to go here a bit down with a bit of drive and most especially envelope 2 is going to modulate this. [Music] And that's pretty much it. You can see how without the filter, it's a really cool sound as well. And that's why I made it without it. So now in the end, if you want to make it a tighter sound, you can just add the filter and just go with that. I hope that you like the sound. And if you want something even further, you can get the preset and you're going to get a lot more macros and a mod wheel that you can play around with in your song. And if you like the sound, you can get over here in the description below. This is already from Abstract Music Lab signing off. Cow."""

# Calculate SHA256
transcript_sha256 = hashlib.sha256(transcript_text.encode('utf-8')).hexdigest()

# TranscriptCuePlan with focused cues
plan = {
    "schema_version": "1.0",
    "runtime": "claude-code",
    "direct_anthropic_sdk": False,
    "api_key_used": False,

    "source_id": "yt_phase5_interactive",
    "video_id": "HEEGN1Xl5o4",
    "source_url": "https://www.youtube.com/watch?v=HEEGN1Xl5o4",

    "transcript_sha256": transcript_sha256,
    "transcript_language": "en",

    "cues": [
        {
            "cue_id": "cue-init-serum",
            "segment_ids": ["seg-init"],
            "start_s": 60.0,
            "end_s": 69.0,
            "preferred_timestamps_s": [67.0],
            "kind": "ACTION",
            "focus_terms": ["deactivate", "shaper box", "activate", "serum", "preset"],
            "verification_reason": "Visual inspection of serum activation and initial preset state before modifications begin.",
            "confidence": 0.95
        },
        {
            "cue_id": "cue-osc-a-saw",
            "segment_ids": ["seg-osc-a"],
            "start_s": 69.0,
            "end_s": 81.0,
            "preferred_timestamps_s": [72.0, 78.0],
            "kind": "ACTION",
            "focus_terms": ["select", "mono", "saw", "unison", "phase distortion"],
            "verification_reason": "Visual inspection of oscillator A configuration: saw wave selection, unison voices, and phase distortion activation.",
            "confidence": 0.93
        },
        {
            "cue_id": "cue-osc-b-saw",
            "segment_ids": ["seg-osc-b"],
            "start_s": 81.0,
            "end_s": 100.0,
            "preferred_timestamps_s": [87.0, 98.0],
            "kind": "ACTION",
            "focus_terms": ["activate", "oscillator", "saw", "level", "zero"],
            "verification_reason": "Visual inspection of oscillator B setup: saw wave selection and level control set to zero.",
            "confidence": 0.91
        },
        {
            "cue_id": "cue-lfo-chaos",
            "segment_ids": ["seg-lfo"],
            "start_s": 108.0,
            "end_s": 126.0,
            "preferred_timestamps_s": [113.0, 119.0],
            "kind": "ACTION",
            "focus_terms": ["LFO", "chaos", "select", "fine", "modulate"],
            "verification_reason": "Visual inspection of LFO setup: chaos waveform selection and fine parameter adjustment.",
            "confidence": 0.89
        },
        {
            "cue_id": "cue-noise-envelope",
            "segment_ids": ["seg-noise"],
            "start_s": 134.0,
            "end_s": 161.0,
            "preferred_timestamps_s": [141.0, 152.0],
            "kind": "ACTION",
            "focus_terms": ["noise", "filter", "envelope", "modulation", "plucker"],
            "verification_reason": "Visual inspection of noise oscillator: filter selection, level control, and envelope 3 modulation routing.",
            "confidence": 0.90
        },
        {
            "cue_id": "cue-filter-mg18",
            "segment_ids": ["seg-filter"],
            "start_s": 189.0,
            "end_s": 207.0,
            "preferred_timestamps_s": [196.0, 201.0],
            "kind": "ACTION",
            "focus_terms": ["filter", "MG18", "mono", "select", "only A"],
            "verification_reason": "Visual inspection of filter selection (MG18) and routing: oscillator A only (B disabled).",
            "confidence": 0.92
        },
        {
            "cue_id": "cue-env2-cutoff",
            "segment_ids": ["seg-env2"],
            "start_s": 207.0,
            "end_s": 228.0,
            "preferred_timestamps_s": [213.0, 220.0],
            "kind": "VALUE_MENTION",
            "focus_terms": ["envelope 2", "cutoff", "modulate", "100%", "resonance"],
            "verification_reason": "Visual inspection of envelope 2 setup: cutoff placement and 100% modulation amount with resonance adjustment.",
            "confidence": 0.88
        },
        {
            "cue_id": "cue-env4-tuning",
            "segment_ids": ["seg-env4"],
            "start_s": 252.0,
            "end_s": 282.0,
            "preferred_timestamps_s": [258.0, 273.0],
            "kind": "ACTION",
            "focus_terms": ["envelope 4", "sustain", "decay", "tuning", "global"],
            "verification_reason": "Visual inspection of envelope 4 configuration: sustain and decay settings, then tuning modulation.",
            "confidence": 0.86
        },
        {
            "cue_id": "cue-routing-bus1",
            "segment_ids": ["seg-routing"],
            "start_s": 288.0,
            "end_s": 308.0,
            "preferred_timestamps_s": [294.0, 302.0],
            "kind": "ACTION",
            "focus_terms": ["route", "bus", "filter", "effects", "convolve"],
            "verification_reason": "Visual inspection of signal routing: filter to bus 1, and effects chain setup (convolver reverb).",
            "confidence": 0.89
        },
        {
            "cue_id": "cue-distortion-drive",
            "segment_ids": ["seg-distortion"],
            "start_s": 335.0,
            "end_s": 364.0,
            "preferred_timestamps_s": [342.0, 355.0],
            "kind": "VALUE_MENTION",
            "focus_terms": ["distortion", "overdrive", "drive", "mix", "loudness"],
            "verification_reason": "Visual inspection of distortion effect: drive increase and mix level adjustment.",
            "confidence": 0.87
        },
        {
            "cue_id": "cue-hyper-voices",
            "segment_ids": ["seg-hyper"],
            "start_s": 383.0,
            "end_s": 408.0,
            "preferred_timestamps_s": [389.0, 402.0],
            "kind": "VALUE_MENTION",
            "focus_terms": ["hyper", "voices", "dimension", "width", "modulation"],
            "verification_reason": "Visual inspection of hyper effect: voice count, dimension adjustment, and spatial width parameters.",
            "confidence": 0.85
        },
        {
            "cue_id": "cue-eq-delay",
            "segment_ids": ["seg-eq-delay"],
            "start_s": 414.0,
            "end_s": 447.0,
            "preferred_timestamps_s": [420.0, 434.0],
            "kind": "ACTION",
            "focus_terms": ["equalizer", "delay", "ping pong", "feedback", "Q"],
            "verification_reason": "Visual inspection of EQ settings and delay configuration: ping pong mode, feedback, and Q adjustments.",
            "confidence": 0.84
        },
        {
            "cue_id": "cue-compression-final",
            "segment_ids": ["seg-compression"],
            "start_s": 447.0,
            "end_s": 467.0,
            "preferred_timestamps_s": [453.0, 462.0],
            "kind": "ACTION",
            "focus_terms": ["compression", "gain", "loudness", "control"],
            "verification_reason": "Visual inspection of compression effect and final gain settings for dynamic control.",
            "confidence": 0.83
        },
        {
            "cue_id": "cue-final-filter",
            "segment_ids": ["seg-final-filter"],
            "start_s": 467.0,
            "end_s": 498.0,
            "preferred_timestamps_s": [475.0, 491.0],
            "kind": "ACTION",
            "focus_terms": ["filter", "MG ladder", "placement", "envelope modulation", "drive"],
            "verification_reason": "Visual inspection of final filter placement (after hyper, before EQ) and envelope 2 modulation.",
            "confidence": 0.86
        },
    ],

    "provenance": (
        ("planner", "claude-code"),
        ("schema_version", "1.0"),
        ("analysis_date", datetime.now().isoformat()),
        ("source_video", "HEEGN1Xl5o4"),
    )
}

# Output
with open("phase5_cue_plan.json", "w") as f:
    json.dump(plan, f, indent=2)

print("[DONE] TranscriptCuePlan generated")
print(f"   Schema version: {plan['schema_version']}")
print(f"   Video ID: {plan['video_id']}")
print(f"   Cues identified: {len(plan['cues'])}")
print(f"   Transcript SHA256: {plan['transcript_sha256'][:16]}...")
print(f"\n   Saved to: phase5_cue_plan.json")
