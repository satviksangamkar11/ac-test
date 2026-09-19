"""G8: canonical real acoustic measurement kernel.

The ONE implementation of RMS/peak/spectral-centroid computation from real
WAV samples in this repository. Moved here from
serum2/server/production_pipeline.py (where it was first built during the
R1 live run) so a single canonical kernel exists under serum2/evidence/ per
the frozen plan, rather than a competing copy. production_pipeline.py
imports and calls this module; it no longer contains its own DSP code.

TWO INDEPENDENT SUCCESS AXES, never conflated:
  status          artifact-level: can the render even be read as a WAV at
                  all (file exists, header parses, frames readable)?
                  One of: NO_RENDER, FILE_NOT_FOUND, MEASUREMENT_ERROR,
                  UNSUPPORTED_FORMAT, EMPTY_AUDIO, MEASURED.
  acoustic_status DSP-level: did real RMS/peak/centroid computation
                  actually run on decoded samples? One of: COMPUTED,
                  UNSUPPORTED_FORMAT, ERROR, NOT_ATTEMPTED.

A corrupted-but-technically-openable format (e.g. an unsupported sample
width) can be status=MEASURED (the file is real and its header/duration
are trustworthy) while acoustic_status stays UNSUPPORTED_FORMAT/ERROR --
the caller (_record_render_and_finalize) already keys off acoustic_status,
not status, when deciding whether to mark acoustic evidence VERIFIED. This
is deliberate, not a naming bug: "MEASURED" describes the ARTIFACT
(duration/rate/sha256 are real and usable), not a claim that RMS/peak/
centroid are valid -- those are validated independently via
acoustic_status. Never let a caller mark acoustic evidence VERIFIED from
`status` alone; test_acoustic_measurement.py asserts this decoupling
explicitly (test_unsupported_format_never_becomes_verified_acoustic).
"""
from __future__ import annotations

import hashlib
import wave
from pathlib import Path
from typing import Any, Dict, Optional

MEASUREMENT_DEFINITION_ID = "g8-basic-acoustic-v1"
KERNEL_VERSION = "1"
CHANNEL_POLICY = "mean_channels"  # stereo/multichannel -> deterministic channel mean -> mono
SAMPLE_POLICY = "normalized_float64_[-1,1]"

DB_FLOOR = -120.0  # silence floor, avoids log10(0) = -inf


def _sha256(path: str) -> Optional[str]:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except Exception:
        return None


def compute_acoustic_metrics(samples, sample_rate: int) -> Dict[str, float]:
    """RMS, peak, and spectral centroid from real, already-decoded samples.

    samples: 1-D float array, mono, normalized to [-1, 1] (per CHANNEL_POLICY
    -- multichannel input must already be downmixed by the caller).
    Standard DSP formulas (np.sqrt(mean(x^2)), max(abs(x)), rfft-weighted
    frequency centroid) -- no framework, no third-party similarity score.
    """
    import numpy as np

    if samples.size == 0:
        return {"rms_db": DB_FLOOR, "peak_db": DB_FLOOR, "spectral_centroid_hz": 0.0}

    x = samples.astype(np.float64)
    rms = float(np.sqrt(np.mean(x ** 2)))
    peak = float(np.max(np.abs(x)))
    rms_db = 20.0 * np.log10(rms) if rms > 0 else DB_FLOOR
    peak_db = 20.0 * np.log10(peak) if peak > 0 else DB_FLOOR

    spectrum = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(x.size, d=1.0 / sample_rate)
    magnitude_sum = float(np.sum(spectrum))
    centroid_hz = float(np.sum(freqs * spectrum) / magnitude_sum) if magnitude_sum > 0 else 0.0

    return {
        "rms_db": float(round(max(rms_db, DB_FLOOR), 2)),
        "peak_db": float(round(max(peak_db, DB_FLOOR), 2)),
        "spectral_centroid_hz": float(round(centroid_hz, 1)),
    }


def _decode_pcm(raw: bytes, sampwidth: int, channels: int):
    """Returns a 1-D float64 array normalized to [-1, 1], channel-mean-
    downmixed per CHANNEL_POLICY, or None if the format isn't supported.
    Handles 8/16/32-bit standard PCM via numpy dtypes and 24-bit PCM via
    manual little-endian sign-extension (numpy has no native int24)."""
    import numpy as np

    if not raw:
        return None

    if sampwidth == 3:
        raw_bytes = np.frombuffer(raw, dtype=np.uint8)
        n_samples = raw_bytes.size // 3
        if n_samples == 0:
            return None
        raw_bytes = raw_bytes[: n_samples * 3].reshape(-1, 3)
        padded = np.zeros((n_samples, 4), dtype=np.uint8)
        padded[:, :3] = raw_bytes
        sign = (raw_bytes[:, 2] & 0x80) != 0
        padded[sign, 3] = 0xFF
        ints = padded.view(np.int32).flatten()
        if channels > 1:
            ints = ints.reshape(-1, channels).mean(axis=1)
        return ints.astype(np.float64) / float(2 ** 23)

    dtype_map = {1: np.int8, 2: np.int16, 4: np.int32}
    dtype = dtype_map.get(sampwidth)
    if dtype is None:
        return None
    ints = np.frombuffer(raw, dtype=dtype)
    if channels > 1:
        ints = ints.reshape(-1, channels).mean(axis=1)
    max_val = float(2 ** (8 * sampwidth - 1))
    return ints.astype(np.float64) / max_val


def measure_render(render_path: Optional[str]) -> Dict[str, Any]:
    """Full artifact-check + decode + measure pipeline for one render file.

    Never returns rms_db/peak_db/spectral_centroid_hz as if real unless
    acoustic_status == "COMPUTED". A failure at any stage returns an
    explicit, honest status -- never a fabricated MEASURED result standing
    in for a real computation that didn't happen.
    """
    if not render_path:
        return {"status": "NO_RENDER", "acoustic_status": "NOT_ATTEMPTED"}

    p = Path(render_path)
    if not p.exists():
        return {"status": "FILE_NOT_FOUND", "acoustic_status": "NOT_ATTEMPTED", "path": render_path}

    size = p.stat().st_size
    sha = _sha256(render_path)

    try:
        with wave.open(str(p), "rb") as wf:
            nframes = wf.getnframes()
            channels = wf.getnchannels()
            rate = wf.getframerate()
            sampwidth = wf.getsampwidth()
            duration = nframes / rate if rate else 0.0
            raw = wf.readframes(nframes)
    except Exception as e:
        return {
            "status": "MEASUREMENT_ERROR",
            "acoustic_status": "NOT_ATTEMPTED",
            "error": f"{type(e).__name__}: {e}",
            "file_size_bytes": size,
            "sha256": sha,
        }

    if nframes == 0:
        return {
            "status": "EMPTY_AUDIO",
            "acoustic_status": "NOT_ATTEMPTED",
            "file_size_bytes": size,
            "duration_sec": 0.0,
            "channels": channels,
            "sample_rate": rate,
            "sha256": sha,
        }

    samples = _decode_pcm(raw, sampwidth, channels)
    if samples is None:
        return {
            "status": "UNSUPPORTED_FORMAT",
            "acoustic_status": "UNSUPPORTED_FORMAT",
            "file_size_bytes": size,
            "duration_sec": round(duration, 2),
            "channels": channels,
            "sample_rate": rate,
            "sample_width_bytes": sampwidth,
            "sha256": sha,
        }

    try:
        acoustic = compute_acoustic_metrics(samples, rate)
        acoustic_status = "COMPUTED"
    except Exception as e:
        return {
            "status": "MEASUREMENT_ERROR",
            "acoustic_status": "ERROR",
            "error": f"{type(e).__name__}: {e}",
            "file_size_bytes": size,
            "duration_sec": round(duration, 2),
            "channels": channels,
            "sample_rate": rate,
            "sha256": sha,
        }

    return {
        "status": "MEASURED",
        "acoustic_status": acoustic_status,
        "file_size_bytes": size,
        "duration_sec": round(duration, 2),
        "channels": channels,
        "sample_rate": rate,
        "sha256": sha,
        "measurement_definition_id": MEASUREMENT_DEFINITION_ID,
        "kernel_version": KERNEL_VERSION,
        "channel_policy": CHANNEL_POLICY,
        "sample_policy": SAMPLE_POLICY,
        **acoustic,
    }
