import json
from dataclasses import asdict

from .models import ValidationReport


def to_dict(report: ValidationReport) -> dict:
    return asdict(report)


def to_json(report: ValidationReport) -> str:
    return json.dumps(to_dict(report), indent=2, sort_keys=True)


def to_text(report: ValidationReport) -> str:
    lines = [f"PKG Viewer validation: {report.status.value}", f"File: {report.path}", f"Size: {report.file_size} bytes", f"Generated: {report.generated_at}", f"Schema: {report.schema_version}", ""]
    for c in report.checks:
        lines.append(f"[{c.status.value}] {c.check_id}: {c.message}")
        if c.evidence:
            lines.append(f"  Evidence: {json.dumps(c.evidence, sort_keys=True, default=str)}")
    if report.diagnostics:
        lines.append("\nDiagnostics:")
        lines.extend(f"  [{d.severity.value}] {d.check_id}: {d.message}"
                     + (f" @ 0x{d.offset:X}" if d.offset is not None else "")
                     for d in report.diagnostics)
    if report.advisories:
        lines.append("\nAdvisories (not authoritative validation):")
        lines.extend(f"  [{a.confidence}] {a.title}: {a.message}; evidence={json.dumps(a.evidence, sort_keys=True)}" for a in report.advisories)
    return "\n".join(lines) + "\n"


class ReportWriter:
    @staticmethod
    def write_json(report: ValidationReport, destination) -> None:
        with open(destination, "w", encoding="utf-8") as fh: fh.write(to_json(report))

    @staticmethod
    def write_text(report: ValidationReport, destination) -> None:
        with open(destination, "w", encoding="utf-8") as fh: fh.write(to_text(report))
