import struct

from pkgviewer.models import Status
from pkgviewer.pkg import PkgDecoder
from pkgviewer.reports import to_text
from pkgviewer.sfo import SfoDecoder
from pkgviewer.validate import Validator


def pkg_header(size=0x5A0, magic=0x7F434E54, entries=0, table=0x5A0):
    data = bytearray(size); struct.pack_into(">I", data, 0, magic); struct.pack_into(">I", data, 0x10, entries); struct.pack_into(">I", data, 0x18, table); return bytes(data)


def test_truncated_and_bad_magic(tmp_path):
    p = tmp_path / "bad.pkg"; p.write_bytes(b"tiny"); doc = PkgDecoder().decode(p); assert Validator().validate(doc).status == Status.FAIL
    p.write_bytes(pkg_header(magic=0xDEADBEEF)); assert Validator().validate(PkgDecoder().decode(p)).status == Status.FAIL


def test_entry_table_bounds(tmp_path):
    p = tmp_path / "bad.pkg"; p.write_bytes(pkg_header(entries=1, table=0x5A0)); doc = PkgDecoder().decode(p); assert any(d.check_id == "pkg.decode" for d in doc.diagnostics)


def test_sfo_string_and_integer():
    keys, values = b"TITLE\0SYSTEM_VER\0", b"Demo\0" + b"\0" * 3 + struct.pack("<I", 0x09000000)
    data = bytearray(0x80 + len(values)); struct.pack_into("<5I", data, 0, 0x46535000, 0x101, 0x54, 0x80, 2)
    struct.pack_into("<HHIII", data, 20, 0, 0x0204, 5, 8, 0); struct.pack_into("<HHIII", data, 36, 6, 0x0404, 4, 4, 8)
    data[0x54:0x54+len(keys)] = keys; data[0x80:] = values
    doc = SfoDecoder().decode(bytes(data)); assert doc.values["TITLE"].value == "Demo"; assert doc.values["SYSTEM_VER"].value == 0x09000000


def test_report_includes_evidence():
    report = Validator().validate(PkgDecoder().decode(__file__))
    text = to_text(report)
    assert "Evidence:" in text or "Diagnostics:" in text
