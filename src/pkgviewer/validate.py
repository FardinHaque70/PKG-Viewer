import hashlib
from datetime import datetime, timezone
from itertools import pairwise
from pathlib import Path

from .models import Advisory, PkgDocument, Status, ValidationCheck, ValidationReport
from .pkg import PkgDecoder


class Validator:
    def validate(self, doc: PkgDocument) -> ValidationReport:
        checks: list[ValidationCheck] = []
        h = doc.header
        checks.append(ValidationCheck("pkg.magic", Status.PASS if h and h.magic == PkgDecoder.MAGIC else Status.FAIL, "PKG magic matches" if h and h.magic == PkgDecoder.MAGIC else "PKG magic does not match", {"magic": hex(h.magic) if h else None}))
        checks.append(ValidationCheck("pkg.header", Status.PASS if h and doc.file_size >= 0x5A0 else Status.FAIL, "header is present" if h and doc.file_size >= 0x5A0 else "header is truncated"))
        if h:
            declared = [("body", h.body_offset, h.body_size), ("content", h.content_offset, h.content_size), ("entry_table", h.table_offset, h.entry_count * 0x20)]
            bad = [(name, off, size) for name, off, size in declared if off > doc.file_size or size > doc.file_size - off]
            checks.append(ValidationCheck("pkg.header_ranges", Status.FAIL if bad else Status.PASS, "declared header ranges fit inside the file" if not bad else "declared header range exceeds the file", {"invalid": bad}))
        else:
            checks.append(ValidationCheck("pkg.header_ranges", Status.NOT_CHECKED, "header ranges unavailable"))
        decode_failed = any(d.check_id == "pkg.decode" for d in doc.diagnostics)
        checks.append(ValidationCheck("pkg.entry_table", Status.FAIL if decode_failed else Status.PASS, "entry table is readable" if not decode_failed else "entry table could not be read"))
        bounds_failed = any(d.check_id == "pkg.entry_bounds" for d in doc.diagnostics)
        checks.append(ValidationCheck("pkg.entry_bounds", Status.FAIL if bounds_failed else Status.PASS, "all entries fit inside the file" if not bounds_failed else "one or more entries exceed the file"))
        checks.append(ValidationCheck("pkg.names", Status.PASS if all(e.name_offset == 0 or e.name for e in doc.entries) else Status.WARNING, "entry names resolved" if all(e.name_offset == 0 or e.name for e in doc.entries) else "some entry names could not be resolved"))
        ranges = sorted((e.offset, e.offset + e.size, e.entry_id) for e in doc.entries if e.size)
        overlaps = [(hex(a[2]), hex(b[2])) for a, b in pairwise(ranges) if b[0] < a[1]]
        checks.append(ValidationCheck("pkg.overlap", Status.FAIL if overlaps else Status.PASS, "entry ranges do not overlap" if not overlaps else "entry ranges overlap", {"overlaps": overlaps}))
        integrity = self._integrity_checks(doc)
        checks.extend(integrity)
        required = next((e for e in doc.entries if e.entry_id == PkgDecoder.ENTRY_PARAM_SFO), None)
        checks.append(ValidationCheck("pkg.param_sfo", Status.PASS if required and doc.sfo and not doc.sfo.diagnostics else Status.FAIL, "param.sfo is present and readable" if required and doc.sfo and not doc.sfo.diagnostics else "required param.sfo is missing or unreadable"))
        for d in doc.diagnostics:
            if d.check_id not in {c.check_id for c in checks}:
                checks.append(ValidationCheck(d.check_id, d.severity, d.message, d.evidence))
        status = Status.FAIL if any(c.status == Status.FAIL for c in checks) else Status.WARNING if any(c.status in (Status.WARNING, Status.NOT_CHECKED) for c in checks) else Status.PASS
        advisories = []
        if any(0x1400 <= e.entry_id <= 0x1463 for e in doc.entries):
            advisories.append(Advisory("trophy.presence", "Trophy data", "trophy entries are present", {"source": "entry table"}, "high"))
        name = Path(doc.path).name.lower()
        if "backport" in name:
            advisories.append(Advisory("filename.backport_hint", "Backport filename hint", "filename contains a backport hint", {"filename": Path(doc.path).name}, "low"))
        return ValidationReport(doc.path, status, checks, doc.diagnostics, "0.1.0", doc.file_size, datetime.now(timezone.utc).isoformat(), advisories=advisories)

    @staticmethod
    def _integrity_checks(doc: PkgDocument) -> list[ValidationCheck]:
        """Verify the documented header and param.sfo SHA-256 slots.

        The general-digests entry layout is: unknown, content, game, header,
        system, major-param, param (32-byte SHA-256 values). Other slots remain
        unavailable until their exact coverage can be established.
        """
        raw = doc.general_digests
        if len(raw) < 7 * 32:
            return [ValidationCheck("pkg.integrity.header", Status.NOT_CHECKED,
                                   "general digest records are unavailable or incomplete",
                                   {"available_bytes": len(raw), "algorithm": "SHA-256"}),
                    ValidationCheck("pkg.integrity.param_sfo", Status.NOT_CHECKED, "param.sfo digest is unavailable")]
        expected_header = raw[3 * 32:4 * 32]
        expected_param = raw[6 * 32:7 * 32]
        actual_header = hashlib.sha256(doc.header.raw[:0x40] + doc.header.raw[0x400:0x480]).digest() if doc.header else b""
        actual_param = hashlib.sha256(doc.param_sfo_raw).digest() if doc.param_sfo_raw else b""
        evidence = {"algorithm": "SHA-256", "regions": {"header": ["0x0-0x40", "0x400-0x480"], "param.sfo": "entry bytes"}}
        return [ValidationCheck("pkg.integrity.header", Status.PASS if expected_header == actual_header else Status.FAIL, "header SHA-256 digest matches" if expected_header == actual_header else "header SHA-256 digest does not match", {**evidence, "expected": expected_header.hex(), "computed": actual_header.hex()}), ValidationCheck("pkg.integrity.param_sfo", Status.PASS if expected_param == actual_param else Status.FAIL, "param.sfo SHA-256 digest matches" if expected_param == actual_param else "param.sfo SHA-256 digest does not match", {**evidence, "expected": expected_param.hex(), "computed": actual_param.hex()})]
