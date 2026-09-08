import mmap
import os
import struct
from pathlib import Path

from .binary import BinaryFormatError, BoundedReader
from .extract import source_identity
from .models import Diagnostic, PkgDocument, PkgEntry, PkgHeader, Status
from .sfo import SfoDecoder


class PkgDecoder:
    MAGIC = 0x7F434E54
    ENTRY_PARAM_SFO = 0x1000
    ENTRY_NAMES = 0x200
    ENTRY_ICON0 = 0x1200
    ENTRY_RECORD_SIZE = 0x20
    MAX_METADATA = 16 * 1024 * 1024
    MAX_ENTRIES = 100_000

    def decode(self, path):
        doc = PkgDocument(str(Path(path).resolve()), 0)
        try:
            with open(doc.path, "rb") as fh:
                stat = os.fstat(fh.fileno())
                doc.file_size = stat.st_size
                doc.source_identity = source_identity(stat)
                if doc.file_size < 0x5A0:
                    raise BinaryFormatError("file is smaller than the documented PKG header")
                with mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as data:
                    self._decode_data(doc, data)
                if source_identity(os.fstat(fh.fileno())) != doc.source_identity:
                    raise BinaryFormatError("source changed while reading")
        except (OSError, BinaryFormatError, struct.error, ValueError) as exc:
            doc.diagnostics.append(Diagnostic(Status.FAIL, "pkg.decode", str(exc), 0,
                                              {"error_type": type(exc).__name__}))
        return doc

    def _decode_data(self, doc, data):
        r = BoundedReader(data)
        size = doc.file_size
        # PFS region is documented at 0x410/0x418. 0x30/0x38 are reserved.
        h = PkgHeader(
            magic=r.u32be(0), pkg_type=r.u32be(4), flags=r.u32be(8),
            file_count=r.u32be(0x0C), entry_count=r.u32be(0x10),
            table_offset=r.u32be(0x18), body_offset=r.u64be(0x20), body_size=r.u64be(0x28),
            content_offset=r.u64be(0x410), content_size=r.u64be(0x418),
            content_id=r.bytes(0x40, 0x30).split(b"\0")[0].decode("ascii", errors="replace"),
            raw=r.bytes(0, 0x5A0), drm_type=r.u32be(0x70), content_type=r.u32be(0x74),
            content_flags=r.u32be(0x78), pfs_offset=r.u64be(0x410), pfs_size=r.u64be(0x418))
        doc.header = h
        if h.magic != self.MAGIC:
            doc.diagnostics.append(Diagnostic(Status.FAIL, "pkg.magic", "invalid PKG magic", 0,
                                              {"actual": hex(h.magic)}))
            return
        if h.entry_count > self.MAX_ENTRIES:
            raise BinaryFormatError("entry count exceeds safety limit")
        table_size = h.entry_count * self.ENTRY_RECORD_SIZE
        if h.table_offset < 0x5A0 or h.table_offset > size - table_size:
            raise BinaryFormatError("entry table is outside the file or overlaps the header")
        for i in range(h.entry_count):
            pos = h.table_offset + i * self.ENTRY_RECORD_SIZE
            entry = PkgEntry(r.u32be(pos), r.u32be(pos + 4), r.u32be(pos + 8),
                             r.u32be(pos + 12), r.u32be(pos + 16), r.u32be(pos + 20), r.u64be(pos + 24))
            doc.entries.append(entry)
            if entry.offset > size - entry.size:
                doc.diagnostics.append(Diagnostic(Status.FAIL, "pkg.entry_bounds", "entry extends beyond file", pos,
                                                  {"entry_id": hex(entry.entry_id), "offset": entry.offset, "size": entry.size}))

        def metadata(entry_id):
            matches = [e for e in doc.entries if e.entry_id == entry_id]
            if len(matches) != 1:
                return b""
            entry = matches[0]
            if entry.encrypted or entry.offset > size - entry.size:
                return b""
            if entry.size > self.MAX_METADATA:
                doc.diagnostics.append(Diagnostic(Status.WARNING, "pkg.metadata_limit", "metadata exceeds read limit", entry.offset,
                                                  {"entry_id": hex(entry_id), "size": entry.size, "limit": self.MAX_METADATA}))
                return b""
            return bytes(data[entry.offset:entry.offset + entry.size])

        names = metadata(self.ENTRY_NAMES)
        known_names = {0x1000: "param.sfo", 0x1200: "icon0.png"}
        for entry in doc.entries:
            if entry.name_offset:
                end = names.find(b"\0", entry.name_offset)
                if entry.name_offset < len(names) and end >= 0:
                    entry.name = names[entry.name_offset:end].decode("utf-8", errors="replace")
            else:
                entry.name = known_names.get(entry.entry_id)
        doc.general_digests = metadata(0x80)
        doc.param_sfo_raw = metadata(self.ENTRY_PARAM_SFO)
        doc.icon_data = metadata(self.ENTRY_ICON0)
        if doc.param_sfo_raw:
            doc.sfo = SfoDecoder().decode(doc.param_sfo_raw)
            entry = next(e for e in doc.entries if e.entry_id == self.ENTRY_PARAM_SFO)
            doc.diagnostics.extend(Diagnostic(d.severity, d.check_id, d.message,
                                              entry.offset + (d.offset or 0), d.evidence) for d in doc.sfo.diagnostics)
            doc.metadata = {k: v.value for k, v in doc.sfo.values.items()}
