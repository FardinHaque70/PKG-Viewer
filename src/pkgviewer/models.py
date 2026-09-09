from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Status(str, Enum):
    PASS = "Pass"
    FAIL = "Fail"
    WARNING = "Warning"
    NOT_CHECKED = "Not checked"


class TrophyType(str, Enum):
    PLATINUM = "Platinum"
    GOLD = "Gold"
    SILVER = "Silver"
    BRONZE = "Bronze"
    UNKNOWN = "Unknown"


class TrophyAvailability(str, Enum):
    READABLE = "Readable"
    PARTIAL = "Partially readable"
    ENCRYPTED = "Encrypted"
    MALFORMED = "Malformed"
    NOT_PRESENT = "Not present"


PKG_TYPES = {0x40000001: "PS4 Game", 0x40000002: "PS4 Patch", 0x81000001: "PS4 Theme", 1: "PS4 App"}
CONTENT_TYPES = {0x1A: "Game", 0x1B: "Addon", 0x1C: "License", 0x1E: "Patch"}
DRM_TYPES = {0: "None", 0xF: "PS4"}


@dataclass(frozen=True)
class Diagnostic:
    severity: Status
    check_id: str
    message: str
    offset: int | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SfoValue:
    key: str
    value: str | int
    format: int
    raw: bytes
    source_offset: int | None = None


@dataclass
class SfoDocument:
    values: dict[str, SfoValue] = field(default_factory=dict)
    diagnostics: list[Diagnostic] = field(default_factory=list)


@dataclass
class PkgEntry:
    entry_id: int
    name_offset: int
    flags: int
    flags2: int
    offset: int
    size: int
    padding: int = 0
    name: str | None = None

    @property
    def encrypted(self) -> bool:
        return bool(self.flags & 0x80000000)

    @property
    def key_index(self) -> int:
        return (self.flags2 & 0xF00) >> 8


@dataclass
class PkgHeader:
    magic: int
    pkg_type: int
    flags: int
    file_count: int
    entry_count: int
    table_offset: int
    body_offset: int
    body_size: int
    content_offset: int = 0
    content_size: int = 0
    content_id: str = ""
    raw: bytes = b""
    drm_type: int = 0
    content_type: int = 0
    content_flags: int = 0
    pfs_offset: int = 0
    pfs_size: int = 0


@dataclass
class PkgDocument:
    path: str
    file_size: int
    header: PkgHeader | None = None
    entries: list[PkgEntry] = field(default_factory=list)
    sfo: SfoDocument | None = None
    metadata: dict[str, str | int] = field(default_factory=dict)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    # Raw integrity material retained for auditable verification.
    param_sfo_raw: bytes = b""
    general_digests: bytes = b""
    source_identity: tuple[int, ...] | None = None
    icon_data: bytes = b""
    trophies: "TrophyDocument | None" = None


@dataclass(frozen=True)
class TrophyEntry:
    trophy_id: int
    trophy_type: TrophyType
    name: str = ""
    description: str = ""
    hidden: bool = False
    icon_name: str = ""
    icon_data: bytes = b""
    source_entry_id: int | None = None
    source_offset: int | None = None


@dataclass
class TrophyDocument:
    availability: TrophyAvailability = TrophyAvailability.NOT_PRESENT
    trophies: list[TrophyEntry] = field(default_factory=list)
    diagnostics: list["Diagnostic"] = field(default_factory=list)
    source_entries: list[int] = field(default_factory=list)
    icon_count: int = 0


@dataclass(frozen=True)
class ValidationCheck:
    check_id: str
    status: Status
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Advisory:
    id: str
    title: str
    message: str
    evidence: dict[str, Any]
    confidence: str


@dataclass
class ValidationReport:
    path: str
    status: Status
    checks: list[ValidationCheck]
    diagnostics: list[Diagnostic]
    parser_version: str
    file_size: int = 0
    generated_at: str = ""
    schema_version: str = "1.0"
    advisories: list[Advisory] = field(default_factory=list)


@dataclass(frozen=True)
class PackageSummary:
    path: str
    title: str = ""
    title_id: str = ""
    content_id: str = ""
    package_type: str = ""
    version: str = ""
    firmware: str = ""
    size: int = 0
    icon_available: bool = False
    category: str = ""
    sdk_version: str = ""
    pubtool_info: str = ""
    region: str = ""
    raw_firmware: str = ""
    package_type_raw: int = 0
    drm_type: str = ""
    content_type: str = ""
    content_flags: str = ""
    file_count: int = 0
    body_size: int = 0


@dataclass(frozen=True)
class PackageEntryView:
    entry_id: int
    name: str
    offset: int
    size: int
    encrypted: bool
    extractable: bool
