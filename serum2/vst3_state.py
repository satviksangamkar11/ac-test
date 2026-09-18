"""JUCE VC2! ValueTree VST3 state container -- wraps/unwraps the XferJson
IComponent blob inside the XML envelope DawDreamer's save_state/load_state
consume. Reuses only the generic JUCE base64 helper from serum2_preset_loader
(not their preset-translation logic, which targets the wrong schema version).
"""
import re
import serum2_preset_loader as _loader  # only for the generic JUCE base64 codec

_b64encode = _loader.juce_memoryblock_b64encode
_b64decode = _loader.juce_memoryblock_b64decode

_ICOMP_RE = re.compile(rb'<IComponent>(.*?)</IComponent>', re.S)
_XML_HEADER = b'<?xml version="1.0" encoding="UTF-8"?> <VST3PluginState><IComponent>'
_XML_FOOTER = b'</IComponent></VST3PluginState>'


def wrap_vc2(icomponent_xferjson: bytes) -> bytes:
    """Raw XferJson IComponent bytes -> full VC2! state blob DawDreamer's
    load_state(filepath) accepts, matching the structure of Serum's own
    save_state() output exactly (verified byte-for-byte on 2.0.21)."""
    b64 = _b64encode(icomponent_xferjson).encode('ascii')
    xml = _XML_HEADER + b64 + _XML_FOOTER
    return b'VC2!' + len(xml).to_bytes(4, 'little') + xml


def unwrap_vc2(vc2_blob: bytes) -> bytes:
    """VC2! state blob -> raw XferJson IComponent bytes."""
    xml_start = vc2_blob.find(b'<?xml')
    xml = vc2_blob[xml_start:]
    m = _ICOMP_RE.search(xml)
    if not m:
        raise ValueError('no <IComponent> section found')
    return _b64decode(m.group(1).decode('ascii'))
