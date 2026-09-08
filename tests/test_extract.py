import struct

import pytest

from pkgviewer.extract import CollisionPolicy, ExtractionError, ExtractionService
from pkgviewer.pkg import PkgDecoder


def make_pkg(path, payload=b"data", encrypted=False):
    data = bytearray(0x604 + len(payload))
    struct.pack_into(">I", data, 0, PkgDecoder.MAGIC)
    struct.pack_into(">I", data, 0x10, 1)
    struct.pack_into(">I", data, 0x18, 0x5A0)
    pos = 0x5A0
    struct.pack_into(">IIIIIIQ", data, pos, 0x1234, 0, 0x80000000 if encrypted else 0, 0, 0x600, len(payload), 0)
    data[0x600:0x600 + len(payload)] = payload
    path.write_bytes(data)


def test_extract_and_collision(tmp_path):
    source = tmp_path / "sample.pkg"
    make_pkg(source)
    doc = PkgDecoder().decode(source)
    service = ExtractionService()
    target = tmp_path / "out.bin"
    result = service.extract_entry(doc, 0x1234, target, CollisionPolicy.SKIP)
    assert result.status == "Extracted" and target.read_bytes() == b"data"
    skipped = service.extract_entry(doc, 0x1234, target, CollisionPolicy.SKIP)
    assert skipped.status == "Skipped"
    kept = service.extract_entry(doc, 0x1234, target, CollisionPolicy.KEEP_BOTH)
    assert kept.status == "Extracted" and (tmp_path / "out (1).bin").exists()


def test_encrypted_and_cancelled_entries(tmp_path):
    source = tmp_path / "encrypted.pkg"
    make_pkg(source, encrypted=True)
    doc = PkgDecoder().decode(source)
    with pytest.raises(ExtractionError, match="Encrypted"):
        ExtractionService().extract_entry(doc, 0x1234, tmp_path / "x.bin")
    source = tmp_path / "cancel.pkg"
    make_pkg(source, payload=b"x" * 4096)
    doc = PkgDecoder().decode(source)
    summary = ExtractionService().extract_many(doc, doc.entries, tmp_path / "cancelled", cancelled=lambda: True)
    assert summary.cancelled and not list((tmp_path / "cancelled").glob("*"))
