import re
from collections.abc import Callable, Iterable

from .models import (
    CONTENT_TYPES,
    DRM_TYPES,
    PKG_TYPES,
    PackageEntryView,
    PackageSummary,
    PkgDocument,
    ValidationReport,
)
from .pkg import PkgDecoder
from .validate import Validator

REGION_CODES = {
    "UP": "US", "EP": "EU", "JP": "JP", "HP": "HK",
    "KP": "KR", "AS": "AS", "PC": "AS", "PL": "EU",
}
REGION_FLAGS = {"US": "🇺🇸", "EU": "🇪🇺", "JP": "🇯🇵", "HK": "🇭🇰", "KR": "🇰🇷", "AS": "🌏"}


def detect_region(document: PkgDocument) -> str:
    content_id = str(document.metadata.get("CONTENT_ID", ""))
    if not content_id and document.header:
        content_id = document.header.content_id
    prefix = content_id[:2].upper()
    return REGION_CODES.get(prefix, "Unknown")


def region_display(document: PkgDocument) -> str:
    region = detect_region(document)
    return f"{REGION_FLAGS.get(region, '🏳️')} {region}"


def format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.2f} {unit}"
        value /= 1024


def classify_package(document: PkgDocument) -> str:
    category = str(document.metadata.get("CATEGORY", "")).lower()
    return {"gd": "Base Game", "gp": "Update", "ac": "DLC"}.get(category, "Other")


def format_firmware(value) -> str:
    """Convert PS4 SYSTEM_VER integer encoding (for example 0x05500000) to 5.50."""
    try:
        raw = int(value)
        encoded = f"{raw:08X}"
        if len(encoded) == 8:
            # The first two bytes encode major/minor (05508000 -> 5.50).
            return f"{int(encoded[:2], 16)}.{encoded[2:4]}"
    except (TypeError, ValueError):
        pass
    return str(value) if value is not None else ""


def extract_sdk_version(document: PkgDocument) -> tuple[str, str]:
    info = str(document.metadata.get("PUBTOOLINFO", ""))
    match = re.search(r"(?:^|,)sdk_ver=([0-9A-Fa-fx]+)(?:,|$)", info)
    if not match:
        return "", ""
    raw = match.group(1)
    try:
        value = int(raw, 0) if raw.lower().startswith("0x") else int(raw, 16)
    except ValueError:
        return raw, raw
    return format_firmware(value), raw


def summarize(document: PkgDocument) -> PackageSummary:
    h = document.header
    title = str(document.metadata.get("TITLE", ""))
    title_id = str(document.metadata.get("TITLE_ID", ""))
    firmware = format_firmware(document.metadata.get("SYSTEM_VER", ""))
    pubtool_info = str(document.metadata.get("PUBTOOLINFO", ""))
    sdk_version, _ = extract_sdk_version(document)
    package_type = PKG_TYPES.get(h.pkg_type, f"0x{h.pkg_type:X}") if h else ""
    drm = h.drm_type if h else 0
    content = h.content_type if h else 0
    flags = h.content_flags if h else 0
    return PackageSummary(document.path, title, title_id, h.content_id if h else "", package_type,
                          str(document.metadata.get("APP_VER", "")), firmware, document.file_size,
                          any(e.entry_id == PkgDecoder.ENTRY_ICON0 for e in document.entries),
                          str(document.metadata.get("CATEGORY", "")),
                          sdk_version or str(document.metadata.get("SDK_VERSION", document.metadata.get("SDK_version", ""))),
                          pubtool_info, detect_region(document),
                          str(document.metadata.get("SYSTEM_VER", "")), h.pkg_type if h else 0,
                          DRM_TYPES.get(drm, f"0x{drm:X}"), CONTENT_TYPES.get(content, f"0x{content:X}"),
                          f"0x{flags:08X}", len(document.entries), h.body_size if h else 0)


def entry_views(document: PkgDocument) -> list[PackageEntryView]:
    return [PackageEntryView(e.entry_id, e.name or f"0x{e.entry_id:X}", e.offset, e.size, e.encrypted, not e.encrypted and not any(d.check_id == "pkg.entry_bounds" for d in document.diagnostics)) for e in document.entries]


class PackageService:
    def __init__(self, decoder=None, validator=None):
        self.decoder, self.validator = decoder or PkgDecoder(), validator or Validator()

    def inspect(self, path: str) -> tuple[PkgDocument, ValidationReport, PackageSummary]:
        document = self.decoder.decode(path)
        return document, self.validator.validate(document), summarize(document)

    def inspect_many(self, paths: Iterable[str], progress: Callable[[int, int], None] | None = None, cancelled: Callable[[], bool] | None = None):
        paths = list(paths); results = []
        for index, path in enumerate(paths, 1):
            if cancelled and cancelled(): break
            results.append(self.inspect(path))
            if progress: progress(index, len(paths))
        return results
