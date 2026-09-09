"""Bounded, metadata-only PS4 trophy reader.

Encrypted ESFM records are intentionally reported as unavailable.
"""
import re
from typing import ClassVar

from .models import TrophyAvailability, TrophyDocument, TrophyEntry, TrophyType


class TrophyDecoder:
    _types: ClassVar = {"P": TrophyType.PLATINUM, "G": TrophyType.GOLD,
              "S": TrophyType.SILVER, "B": TrophyType.BRONZE}

    def decode(self, records: list[tuple[int, str, bytes, int]]):
        doc = TrophyDocument()
        if not records:
            return doc
        doc.source_entries = [r[0] for r in records]
        blobs = b"".join(data[:16 * 1024 * 1024] for _, _, data, _ in records)
        doc.icon_count = blobs.count(b"\x89PNG\r\n\x1a\n")
        if b"ESFM" in blobs or any(b".esfm" in name.lower().encode() for _, name, _, _ in records):
            doc.availability = TrophyAvailability.ENCRYPTED
        xml = blobs.decode("utf-8", errors="ignore")
        pattern = re.compile(r"<trophy\b([^>]*)>(.*?)</trophy\s*>", re.IGNORECASE | re.DOTALL)
        for match in pattern.finditer(xml):
            attrs, body = match.groups()
            fields = dict(re.findall(r"([\w-]+)\s*=\s*[\"']([^\"']*)", attrs))
            try: tid = int(fields.get("id", "0"))
            except ValueError: continue
            kind = self._types.get(fields.get("ttype", "").upper(), TrophyType.UNKNOWN)
            name = self._tag(body, "name")
            detail = self._tag(body, "detail") or self._tag(body, "description")
            hidden = fields.get("hidden", "no").lower() in {"yes", "true", "1"}
            icon = fields.get("icon", f"TROP{tid:03d}.PNG")
            doc.trophies.append(TrophyEntry(tid, kind, name, detail, hidden, icon))
        if doc.trophies:
            doc.availability = TrophyAvailability.READABLE if doc.availability != TrophyAvailability.ENCRYPTED else TrophyAvailability.PARTIAL
        elif doc.icon_count:
            # Plaintext PNG records remain useful even when ESFM text is encrypted.
            start = 0
            for index in range(doc.icon_count):
                start = blobs.find(b"\x89PNG\r\n\x1a\n", start)
                if start < 0:
                    break
                end_marker = blobs.find(b"IEND\xaeB`\x82", start)
                end = end_marker + 8 if end_marker >= 0 else len(blobs)
                doc.trophies.append(TrophyEntry(index, TrophyType.UNKNOWN, "", "", False,
                                                 f"TROP{index:03d}.PNG", blobs[start:end]))
                start = end
            doc.availability = TrophyAvailability.PARTIAL
        elif (doc.availability == TrophyAvailability.ENCRYPTED and doc.icon_count) or doc.availability == TrophyAvailability.NOT_PRESENT:
            doc.availability = TrophyAvailability.PARTIAL
        return doc

    @staticmethod
    def _tag(body, tag):
        match = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", body, re.IGNORECASE | re.DOTALL)
        return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""
