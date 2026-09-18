"""Serum 2 XferJson container codec.

Layout: b'XferJson' 00 | u64 meta_len | JSON meta | u32 raw_len | u32 mode | zstd(CBOR)

Used for both flavors of Serum's own format:
  - .SerumPreset files      (meta.version == 5.0, no "component" field)
  - VST3 processor state    (meta.version == 8.0 on Serum 2.0.21, meta.component == "processor")
Both share this exact container; only the JSON meta and CBOR body schemas differ.
"""
import struct, json
import zstandard as zstd
import cbor2

MAGIC = b'XferJson'


def decode(raw: bytes):
    """raw XferJson container bytes -> (meta: dict, body: dict)."""
    if raw[:8] != MAGIC:
        raise ValueError('not a XferJson container')
    meta_len = struct.unpack('<Q', raw[9:17])[0]
    meta = json.loads(raw[17:17 + meta_len])
    tail = raw[17 + meta_len:]
    raw_len, mode = struct.unpack('<II', tail[0:8])
    body = cbor2.loads(
        zstd.ZstdDecompressor().decompress(tail[8:], max_output_size=max(raw_len * 4, 1 << 22))
    )
    return meta, body


def encode(meta: dict, body: dict, mode: int = 2) -> bytes:
    """(meta, body) -> raw XferJson container bytes."""
    payload = cbor2.dumps(body)
    comp = zstd.ZstdCompressor().compress(payload)
    mj = json.dumps(meta, separators=(',', ':')).encode()
    return (MAGIC + b'\x00' + struct.pack('<Q', len(mj)) + mj
            + struct.pack('<II', len(payload), mode) + comp)


def load_preset_file(path: str):
    """Read a .SerumPreset file -> (meta, body)."""
    return decode(open(path, 'rb').read())


def dump_preset_file(path: str, meta: dict, body: dict, mode: int = 2):
    open(path, 'wb').write(encode(meta, body, mode))
