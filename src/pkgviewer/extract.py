"""Bounded extraction of exposed PKG entries; never decrypts the payload."""
import os
import re
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path, PureWindowsPath

from .models import PkgDocument, PkgEntry


class ExtractionError(ValueError):
    pass


class ExtractionCancelled(ExtractionError):
    pass


class CollisionPolicy(str, Enum):
    SKIP = "Skip"
    KEEP_BOTH = "Keep both"
    OVERWRITE = "Overwrite"


@dataclass(frozen=True)
class ExtractionResult:
    entry_id: int
    destination: str | None
    bytes_written: int
    status: str
    error: str = ""
    cancelled: bool = False


@dataclass
class ExtractionSummary:
    results: list[ExtractionResult] = field(default_factory=list)
    cancelled: bool = False

    @property
    def bytes_written(self):
        return sum(r.bytes_written for r in self.results)

    @property
    def completed(self):
        return sum(r.status == "Extracted" for r in self.results)


def source_identity(stat):
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def resolve_entry(document, identifier):
    if isinstance(identifier, PkgEntry):
        matches = [e for e in document.entries if e.entry_id == identifier.entry_id]
        if len(matches) == 1 and matches[0] != identifier:
            raise ExtractionError("entry no longer matches inspected record")
    else:
        matches = [e for e in document.entries
                   if (e.entry_id == identifier if isinstance(identifier, int) else e.name == identifier)]
    if len(matches) != 1:
        raise ExtractionError("entry identifier is missing or ambiguous")
    return matches[0]


def availability(document, entry):
    if sum(e.entry_id == entry.entry_id for e in document.entries) != 1:
        return "Ambiguous entry ID"
    if entry.encrypted:
        return "Encrypted; decryption unavailable"
    if entry.offset < 0 or entry.size < 0 or entry.offset > document.file_size - entry.size:
        return "Invalid entry range"
    if any(d.severity.value == "Fail" for d in document.diagnostics):
        return "Package structure must be corrected before extraction"
    if document.source_identity is None:
        return "Source identity unavailable; inspect again"
    return "Available"


def output_name(entry):
    name = entry.name or {0x1000: "param.sfo", 0x1200: "icon0.png"}.get(entry.entry_id, "")
    if not name:
        return f"entry_{entry.entry_id:08X}.bin"
    path = Path(name.replace("\\", "/"))
    if path.is_absolute() or PureWindowsPath(name).drive or ".." in path.parts:
        raise ExtractionError("unsafe absolute or traversal entry name")
    name = path.name
    reserved = {"CON", "PRN", "AUX", "NUL"} | {f"{prefix}{i}" for prefix in ("COM", "LPT") for i in range(1, 10)}
    if (not name or name in (".", "..") or re.search(r'[<>:"|?*\x00-\x1f]', name)
            or name.rstrip(". ") != name or name.split(".")[0].upper() in reserved
            or len(name.encode("utf-8")) > 180):
        return f"entry_{entry.entry_id:08X}.bin"
    return name


def safe_directory(destination):
    root = Path(destination).expanduser().absolute()
    # Refuse user-selected symlink paths, including intermediate components.
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise ExtractionError("destination contains a symbolic link")
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise ExtractionError("destination is not a directory")
    return root.resolve()


class ExtractionService:
    CHUNK_SIZE = 1024 * 1024

    def extract_entry(self, document: PkgDocument, identifier, destination,
                      collision_policy=CollisionPolicy.SKIP, cancelled=None, progress=None):
        entry = resolve_entry(document, identifier)
        reason = availability(document, entry)
        if reason != "Available":
            raise ExtractionError(reason)
        policy = CollisionPolicy(collision_policy)
        target = Path(destination).absolute()
        root = safe_directory(target.parent)
        target = root / target.name
        root_identity = (root.stat().st_dev, root.stat().st_ino)
        cancel = cancelled or (lambda: False)

        def check_cancel():
            if cancel():
                raise ExtractionCancelled("extraction cancelled")

        def check_source(src):
            for st in (os.fstat(src.fileno()), os.stat(document.path)):
                if source_identity(st) != document.source_identity or st.st_size != document.file_size:
                    raise ExtractionError("source changed since inspection; inspect again")

        check_cancel()
        with open(document.path, "rb") as src:
            check_source(src)
            if target.is_symlink() or (target.exists() and not target.is_file()):
                raise ExtractionError("destination is a symlink or is not a regular file")
            if target.exists() and os.path.samefile(document.path, target):
                raise ExtractionError("destination is the source package")
            if target.exists() and policy == CollisionPolicy.SKIP:
                return ExtractionResult(entry.entry_id, str(target), 0, "Skipped", "destination exists")
            fd, temp_name = tempfile.mkstemp(prefix=".pkgviewer-", dir=root)
            temp = Path(temp_name)
            written = 0
            try:
                with os.fdopen(fd, "wb") as out:
                    src.seek(entry.offset)
                    while written < entry.size:
                        check_cancel()
                        chunk = src.read(min(self.CHUNK_SIZE, entry.size - written))
                        if not chunk:
                            raise ExtractionError("entry ended before its declared size")
                        out.write(chunk)
                        written += len(chunk)
                        if progress:
                            progress(written, entry.size)
                    out.flush()
                    os.fsync(out.fileno())
                check_cancel()
                check_source(src)
                if root.is_symlink() or (root.stat().st_dev, root.stat().st_ino) != root_identity:
                    raise ExtractionError("destination directory changed during extraction")
                if target.is_symlink():
                    raise ExtractionError("destination became a symbolic link")
                if policy == CollisionPolicy.OVERWRITE:
                    if target.exists() and os.path.samefile(document.path, target):
                        raise ExtractionError("destination is the source package")
                    os.replace(temp, target)
                else:
                    # Exclusive publication: a concurrently-created file is never overwritten.
                    candidate, suffix = target, 0
                    while True:
                        check_cancel()
                        try:
                            os.link(temp, candidate)
                            target = candidate
                            break
                        except FileExistsError:
                            if policy == CollisionPolicy.SKIP:
                                return ExtractionResult(entry.entry_id, str(target), 0, "Skipped", "destination appeared during extraction")
                            suffix += 1
                            candidate = target.with_name(f"{target.stem} ({suffix}){target.suffix}")
                return ExtractionResult(entry.entry_id, str(target), written, "Extracted")
            finally:
                temp.unlink(missing_ok=True)

    def extract_many(self, document, entries, destination, collision_policy=CollisionPolicy.SKIP,
                     cancelled=None, progress=None, entry_finished=None):
        root = safe_directory(destination)
        entries = list(entries)
        summary = ExtractionSummary()
        total = sum(max(0, e.size) for e in entries)
        completed_bytes = 0
        names = set()
        for index, entry in enumerate(entries):
            target = None
            if summary.cancelled or (cancelled and cancelled()):
                result = ExtractionResult(entry.entry_id, None, 0, "Cancelled", "extraction cancelled", True)
            else:
                try:
                    name = output_name(entry)
                    if name.casefold() in names:
                        raise ExtractionError("duplicate output name in this batch")
                    names.add(name.casefold())
                    target = root / name
                    result = self.extract_entry(
                        document, entry, target, collision_policy, cancelled,
                        lambda written, size, i=index, base=completed_bytes: progress(i, len(entries), base + written, total) if progress else None)
                except ExtractionCancelled as exc:
                    result = ExtractionResult(entry.entry_id, str(target) if target else None, 0, "Cancelled", str(exc), True)
                except (OSError, ExtractionError) as exc:
                    result = ExtractionResult(entry.entry_id, str(target) if target else None, 0, "Failed", str(exc))
            summary.results.append(result)
            summary.cancelled |= result.cancelled
            completed_bytes += result.bytes_written
            if entry_finished:
                entry_finished(result)
            if progress:
                progress(index + 1, len(entries), completed_bytes, total)
        return summary


def extract_entry(document, entry_id, destination, overwrite=False, cancelled=None):
    """Compatibility wrapper for existing callers expecting a Path."""
    result = ExtractionService().extract_entry(
        document, entry_id, destination,
        CollisionPolicy.OVERWRITE if overwrite else CollisionPolicy.SKIP, cancelled)
    if result.status == "Skipped":
        raise FileExistsError(result.destination)
    return Path(result.destination)
