"""Folder discovery and metadata-based game grouping, independent of Qt."""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FolderScan:
    paths: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def discover_packages(folder, cancelled=lambda: False) -> FolderScan:
    root = Path(folder)
    if not root.is_dir():
        raise NotADirectoryError(str(root))
    result = FolderScan()
    found = set()
    for directory, _, filenames in os.walk(
        root, followlinks=False, onerror=lambda error: result.errors.append(str(error))
    ):
        if cancelled():
            break
        for name in filenames:
            if cancelled():
                break
            if Path(name).suffix.lower() != ".pkg":
                continue
            try:
                path = Path(directory, name)
                if path.is_file():
                    found.add(str(path.resolve()))
            except (OSError, RuntimeError) as error:
                result.errors.append(str(error))
    result.paths = sorted(found, key=str.casefold)
    return result


def game_identity(document):
    title_id = str(document.metadata.get("TITLE_ID", "")).strip()
    if not title_id:
        content_id = str(document.metadata.get("CONTENT_ID", ""))
        if not content_id and document.header:
            content_id = document.header.content_id
        match = re.search(r"-(CUSA\d{5})_", content_id)
        if match:
            title_id = match.group(1)
    # Unknown identities stay separate; filenames and display titles are not reliable IDs.
    return ("title:" + title_id.upper() if title_id else "file:" + document.path), title_id
