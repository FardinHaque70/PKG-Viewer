from .binary import BinaryFormatError, BoundedReader
from .models import Diagnostic, SfoDocument, SfoValue, Status


class SfoDecoder:
    MAGIC = 0x46535000

    def decode(self, data: bytes) -> SfoDocument:
        doc = SfoDocument()
        pos = 0
        try:
            r = BoundedReader(data)
            if len(data) < 20 or r.u32le(0) != self.MAGIC:
                raise BinaryFormatError("invalid SFO magic or truncated header")
            key_offset, data_offset, count = r.u32le(8), r.u32le(12), r.u32le(16)
            if count > 10000 or not 20 + count * 16 <= key_offset <= data_offset <= len(data):
                raise BinaryFormatError("invalid SFO table offsets or entry count")
            for i in range(count):
                pos = 20 + i * 16
                ko, fmt = r.u16le(pos), r.u16le(pos + 2)
                length, max_len, vo = r.u32le(pos + 4), r.u32le(pos + 8), r.u32le(pos + 12)
                key_pos = key_offset + ko
                key_end = data.find(b"\0", key_pos, data_offset)
                if not key_offset <= key_pos < data_offset or key_end <= key_pos:
                    raise BinaryFormatError(f"invalid SFO key offset at entry {i}")
                value_pos = data_offset + vo
                if length > max_len or value_pos > len(data) - max_len:
                    raise BinaryFormatError(f"invalid SFO value bounds for entry {i}")
                raw = r.bytes(value_pos, length)
                key = data[key_pos:key_end].decode("utf-8")
                if key in doc.values:
                    raise BinaryFormatError(f"duplicate SFO key {key}")
                if fmt in (0x0004, 0x0204):
                    if fmt == 0x0204 and not raw.endswith(b"\0"):
                        raise BinaryFormatError(f"unterminated string for {key}")
                    value = raw.split(b"\0", 1)[0].decode("utf-8")
                elif fmt == 0x0404:
                    if length != 4:
                        raise BinaryFormatError(f"invalid integer length for {key}")
                    value = r.u32le(value_pos)
                else:
                    value = raw.hex()
                    doc.diagnostics.append(Diagnostic(Status.NOT_CHECKED, "sfo.format", "unsupported SFO value format", pos,
                                                      {"key": key, "format": hex(fmt), "raw": value}))
                doc.values[key] = SfoValue(key, value, fmt, raw, value_pos)
        except (BinaryFormatError, UnicodeError) as exc:
            doc.diagnostics.append(Diagnostic(Status.FAIL, "sfo.decode", str(exc), pos, {"size": len(data)}))
        return doc
