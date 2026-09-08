import struct


class BinaryFormatError(ValueError):
    pass


class BoundedReader:
    def __init__(self, data: bytes, base_offset: int = 0):
        self.data = data
        self.base_offset = base_offset

    def _read(self, offset: int, size: int) -> bytes:
        if offset < 0 or size < 0 or offset > len(self.data) - size:
            raise BinaryFormatError(f"read outside buffer at 0x{offset:X} ({size} bytes)")
        return self.data[offset:offset + size]

    def u16be(self, offset: int) -> int: return struct.unpack(">H", self._read(offset, 2))[0]
    def u32be(self, offset: int) -> int: return struct.unpack(">I", self._read(offset, 4))[0]
    def u64be(self, offset: int) -> int: return struct.unpack(">Q", self._read(offset, 8))[0]
    def u16le(self, offset: int) -> int: return struct.unpack("<H", self._read(offset, 2))[0]
    def u32le(self, offset: int) -> int: return struct.unpack("<I", self._read(offset, 4))[0]
    def bytes(self, offset: int, size: int) -> bytes: return self._read(offset, size)
