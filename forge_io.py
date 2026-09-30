# SPDX-License-Identifier: GPL-2.0-or-later
"""Conservative Wildlands Forge I/O; never modifies an input archive.

Format reference (independent reverse engineering):
https://github.com/Firejumper93/GhostReconWildlands-AnvilNext2.0-Documentation/blob/main/docs/02-formats.md
"""
from __future__ import annotations

import ctypes
import ctypes.util
import dataclasses
import os
from pathlib import Path
import struct
import uuid
import zlib

MAGIC = bytes.fromhex("33 aa fb 57 99 fa 04 10")
ALIGNMENT = 0x8000
SET_HEADER = struct.Struct("<8shBHHI")
SECTION_HEADER = struct.Struct("<IIqqIIqq")
INDEX_RECORD = struct.Struct("<QQI")


class ForgeFormatError(ValueError):
    """Input is incomplete, inconsistent, or uses an unsupported dialect."""


def adler32_zero(data: bytes) -> int:
    return zlib.adler32(data, 0) & 0xFFFFFFFF


class LzoCodec:
    """Safe LZO1X decoding and compatible minilzo LZO1X-1 encoding.

    Stock compression is LZO1X-999. Unchanged blocks are retained, and changed
    blocks are allowed to grow, so minilzo's larger output is safe to repack.
    """

    def __init__(self, dll_path=None):
        local = Path(__file__).with_name("minilzo.dll")
        library = dll_path or os.environ.get("WILDLANDS_LZO_LIBRARY")
        library = library or (str(local) if local.is_file() else ctypes.util.find_library("lzo2"))
        if not library:
            raise RuntimeError("LZO library missing; compile minilzo.dll beside forge_io.py")
        self.library = ctypes.CDLL(str(library))
        version = self.library.lzo_version
        version.argtypes = []
        version.restype = ctypes.c_uint
        initialize = getattr(self.library, "__lzo_init_v2")
        initialize.argtypes = [ctypes.c_uint] + [ctypes.c_int] * 9
        initialize.restype = ctypes.c_int
        pointer_size = ctypes.sizeof(ctypes.c_void_p)
        code = initialize(version(), ctypes.sizeof(ctypes.c_short), ctypes.sizeof(ctypes.c_int),
                          ctypes.sizeof(ctypes.c_long), 4, ctypes.sizeof(ctypes.c_size_t),
                          pointer_size, pointer_size, pointer_size, pointer_size * 6)
        if code != 0:
            raise RuntimeError(f"LZO library ABI initialization failed: {code}")
        args = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p]
        self._decompress = self.library.lzo1x_decompress_safe
        self._compress = self.library.lzo1x_1_compress
        for function in (self._decompress, self._compress):
            function.argtypes = args
            function.restype = ctypes.c_int

    def decompress(self, data: bytes, expected_size: int) -> bytes:
        if not 0 < expected_size <= 0xFFFF:
            raise ForgeFormatError("Invalid uncompressed block size")
        source = ctypes.create_string_buffer(data)
        target = ctypes.create_string_buffer(expected_size)
        length = ctypes.c_size_t(expected_size)
        code = self._decompress(source, len(data), target, ctypes.byref(length), None)
        if code != 0 or length.value != expected_size:
            raise ForgeFormatError(f"LZO decode failed: code={code}, size={length.value}, expected={expected_size}")
        return target.raw[:length.value]

    def compress(self, data: bytes) -> bytes:
        if not data:
            raise ForgeFormatError("Cannot encode an empty compression block")
        source = ctypes.create_string_buffer(data)
        target = ctypes.create_string_buffer(len(data) + len(data) // 16 + 64 + 3)
        workspace = ctypes.create_string_buffer(16384 * ctypes.sizeof(ctypes.c_void_p))
        length = ctypes.c_size_t(len(target))
        code = self._compress(source, len(data), target, ctypes.byref(length), workspace)
        if code != 0:
            raise ForgeFormatError(f"LZO encode failed: code={code}")
        return target.raw[:length.value]


@dataclasses.dataclass(frozen=True)
class Block:
    data: bytes
    stored: bytes
    checksum: int


@dataclasses.dataclass(frozen=True)
class BlockSet:
    header: bytes
    blocks: tuple[Block, ...]

    @property
    def data(self) -> bytes:
        return b"".join(block.data for block in self.blocks)

    @property
    def compression(self) -> int:
        return self.header[10]

    @property
    def max_block_size(self) -> int:
        return struct.unpack_from("<H", self.header, 11)[0]


@dataclasses.dataclass(frozen=True)
class BlockPayload:
    sets: tuple[BlockSet, ...]
    trailer: bytes = b""


def decode_payload(raw: bytes, codec=None, verify_checksums=True) -> BlockPayload:
    """Decode all sets at their declared boundaries and retain any trailing bytes.

    Do not call on GlobalMetaFile or PrefetchingFileInfos. Those special entries
    must pass through the archive writer unchanged.
    """
    if not raw.startswith(MAGIC):
        raise ForgeFormatError("Entry does not start with a block-set header")
    sets = []
    position = 0
    while raw.startswith(MAGIC, position):
        if position + SET_HEADER.size > len(raw):
            raise ForgeFormatError("Truncated block-set header")
        header = raw[position:position + SET_HEADER.size]
        _, version, compression, max_size, max_size2, count = SET_HEADER.unpack(header)
        if version != 1 or compression not in (0, 1):
            raise ForgeFormatError(f"Unsupported block-set version/compression: {version}/{compression}")
        if not 0 < max_size <= 0xFFFF or not 0 < max_size2 <= 0xFFFF:
            raise ForgeFormatError("Invalid maximum block size")
        position += SET_HEADER.size
        if not 0 < count <= (len(raw) - position) // 8:
            raise ForgeFormatError("Invalid block count or truncated block table")
        sizes = [struct.unpack_from("<HH", raw, position + i * 4) for i in range(count)]
        position += count * 4
        blocks = []
        for index, (uncompressed, compressed) in enumerate(sizes):
            if not 0 < uncompressed <= max_size or not compressed:
                raise ForgeFormatError(f"Invalid block sizes at block {index}")
            end = position + 4 + compressed
            if end > len(raw):
                raise ForgeFormatError(f"Truncated block data at block {index}")
            checksum = struct.unpack_from("<I", raw, position)[0]
            stored = raw[position + 4:end]
            if verify_checksums and adler32_zero(stored) != checksum:
                raise ForgeFormatError(f"Checksum mismatch at set {len(sets)}, block {index}")
            if compressed == uncompressed:
                data = stored
            else:
                codec = codec or LzoCodec()
                data = codec.decompress(stored, uncompressed)
            blocks.append(Block(data, stored, checksum))
            position = end
        sets.append(BlockSet(header, tuple(blocks)))
    return BlockPayload(tuple(sets), raw[position:])


def encode_payload(payload: BlockPayload, replacements=None, codec=None) -> bytes:
    """Replace complete set bodies; retain every unchanged compressed block.

    A replacement may grow. Existing uncompressed block boundaries are reused;
    extra bytes are split at the original set's maximum block size. No padding
    is inserted between sets. Original trailing bytes stay at the logical end.
    """
    replacements = replacements or {}
    unknown = set(replacements) - set(range(len(payload.sets)))
    if unknown:
        raise KeyError(f"Unknown set indices: {sorted(unknown)}")
    output = bytearray()
    for set_index, blockset in enumerate(payload.sets):
        new_data = replacements.get(set_index)
        if new_data is None or new_data == blockset.data:
            blocks = blockset.blocks
        else:
            new_data = bytes(new_data)
            if not new_data:
                raise ForgeFormatError("Refusing to remove a complete block set")
            blocks = []
            position = 0
            for previous in blockset.blocks:
                data = new_data[position:position + len(previous.data)]
                if not data:
                    break
                position += len(data)
                if data == previous.data:
                    blocks.append(previous)
                else:
                    codec = codec or LzoCodec()
                    stored = codec.compress(data)
                    if len(stored) >= len(data):
                        stored = data
                    blocks.append(Block(data, stored, adler32_zero(stored)))
            while position < len(new_data):
                data = new_data[position:position + blockset.max_block_size]
                position += len(data)
                codec = codec or LzoCodec()
                stored = codec.compress(data)
                if len(stored) >= len(data):
                    stored = data
                blocks.append(Block(data, stored, adler32_zero(stored)))
        header = bytearray(blockset.header)
        struct.pack_into("<I", header, 15, len(blocks))
        output.extend(header)
        for block in blocks:
            output.extend(struct.pack("<HH", len(block.data), len(block.stored)))
        for block in blocks:
            output.extend(struct.pack("<I", block.checksum))
            output.extend(block.stored)
    output.extend(payload.trailer)
    return bytes(output)


decode_blocksets = decode_payload
encode_blocksets = encode_payload


@dataclasses.dataclass(frozen=True)
class ForgeEntry:
    ordinal: int
    name: str
    file_id: int
    offset: int
    size: int
    index_offset: int
    name_offset: int


class ForgeArchive:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.file_size = self.path.stat().st_size
        entries = []
        metadata_spans = []

        def read_at(stream, offset, size):
            if offset < 0 or size < 0 or offset + size > self.file_size:
                raise ForgeFormatError(f"Archive range outside file: {offset}+{size}")
            stream.seek(offset)
            data = stream.read(size)
            if len(data) != size:
                raise ForgeFormatError("Archive changed or was truncated during read")
            return data

        with self.path.open("rb") as stream:
            header = read_at(stream, 0, 21)
            if header[:8] != b"scimitar":
                raise ForgeFormatError("Not a scimitar Forge archive")
            version, data_header = struct.unpack_from("<IQ", header, 9)
            if version != 27:
                raise ForgeFormatError(f"Unsupported Forge version {version}")
            data = read_at(stream, data_header, 44)
            total = struct.unpack_from("<I", data, 0)[0]
            next_section = struct.unpack_from("<q", data, 36)[0]
            metadata_spans.extend([(0, 21), (data_header, data_header + 44)])
            visited = set()
            while next_section > 0:
                if next_section in visited:
                    raise ForgeFormatError("Cycle in index-section chain")
                visited.add(next_section)
                section_offset = next_section
                section = read_at(stream, section_offset, SECTION_HEADER.size)
                count, _, indices, next_section, start, end, names, _ = SECTION_HEADER.unpack(section)
                if count > self.file_size // 212 or len(entries) + count > total:
                    raise ForgeFormatError("Index count exceeds declared entry count")
                index_data = read_at(stream, indices, count * INDEX_RECORD.size)
                name_data = read_at(stream, names, count * 192)
                metadata_spans.extend([(section_offset, section_offset + 48),
                                       (indices, indices + count * 20), (names, names + count * 192)])
                for i in range(count):
                    offset, file_id, size = INDEX_RECORD.unpack_from(index_data, i * 20)
                    name_size = struct.unpack_from("<I", name_data, i * 192)[0]
                    if name_size != size:
                        raise ForgeFormatError(f"Index/name size mismatch for file id {file_id}")
                    if not size or offset + size > self.file_size:
                        raise ForgeFormatError(f"Invalid payload range for file id {file_id}")
                    name = name_data[i * 192 + 44:i * 192 + 172].split(b"\0", 1)[0].decode("utf-8", "replace")
                    entries.append(ForgeEntry(len(entries), name, file_id, offset, size,
                                              indices + i * 20, names + i * 192))
                if next_section not in (-1, 0) and next_section < 0:
                    raise ForgeFormatError("Invalid next-section offset")
        if len(entries) != total or not entries:
            raise ForgeFormatError(f"Entry count mismatch: read {len(entries)}, declared {total}")
        self.entries = tuple(entries)
        self.by_id = {entry.file_id: entry for entry in entries}
        if len(self.by_id) != len(entries):
            raise ForgeFormatError("Duplicate file ids inside archive")
        self.payload_start = entries[0].offset
        if any(end > self.payload_start for _, end in metadata_spans):
            raise ForgeFormatError("Metadata extends into the payload area")
        for previous, current in zip(entries, entries[1:]):
            if current.offset != previous.offset + previous.size:
                raise ForgeFormatError("Payloads are not contiguous in original index order")
        self.payload_end = entries[-1].offset + entries[-1].size
        expected_size = (self.payload_end + ALIGNMENT - 1) // ALIGNMENT * ALIGNMENT
        if expected_size != self.file_size:
            raise ForgeFormatError("Archive does not have the expected 0x8000 file alignment")
        with self.path.open("rb") as stream:
            padding = read_at(stream, self.payload_end, self.file_size - self.payload_end)
        if any(padding):
            raise ForgeFormatError("Archive trailing alignment bytes are not zero")

    def find(self, name: str) -> tuple[ForgeEntry, ...]:
        return tuple(entry for entry in self.entries if entry.name == name)

    def read_raw(self, entry_or_file_id) -> bytes:
        entry = entry_or_file_id if isinstance(entry_or_file_id, ForgeEntry) else self.by_id[entry_or_file_id]
        if self.by_id.get(entry.file_id) != entry:
            raise ValueError("Entry belongs to another archive")
        with self.path.open("rb") as stream:
            stream.seek(entry.offset)
            data = stream.read(entry.size)
        if len(data) != entry.size:
            raise ForgeFormatError("Input archive was truncated")
        return data

    def rebuild(self, destination, replacements, overwrite=False):
        """Build a separate archive atomically; replacements are keyed by file id."""
        destination = Path(destination).resolve()
        if destination == self.path or (destination.exists() and os.path.samefile(destination, self.path)):
            raise ValueError("Destination must differ from the input archive")
        if destination.exists() and not overwrite:
            raise FileExistsError(destination)
        unknown = set(replacements) - set(self.by_id)
        if unknown:
            raise KeyError(f"Unknown file ids: {sorted(unknown)}")
        if any(not isinstance(data, bytes) or not data or len(data) > 0x7FFFFFFF
               for data in replacements.values()):
            raise ValueError("Replacements must be nonempty bytes smaller than 2 GiB")
        if self.path.stat().st_size != self.file_size:
            raise ForgeFormatError("Input archive size changed after validation")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + "." + uuid.uuid4().hex + ".tmp")
        try:
            with self.path.open("rb") as source, temporary.open("xb") as target:
                prefix = bytearray(source.read(self.payload_start))
                offset = self.payload_start
                for entry in self.entries:
                    size = len(replacements[entry.file_id]) if entry.file_id in replacements else entry.size
                    struct.pack_into("<Q", prefix, entry.index_offset, offset)
                    struct.pack_into("<I", prefix, entry.index_offset + 16, size)
                    struct.pack_into("<I", prefix, entry.name_offset, size)
                    offset += size
                target.write(prefix)
                for entry in self.entries:
                    if entry.file_id in replacements:
                        target.write(replacements[entry.file_id])
                    else:
                        source.seek(entry.offset)
                        remaining = entry.size
                        while remaining:
                            chunk = source.read(min(1024 * 1024, remaining))
                            if not chunk:
                                raise ForgeFormatError("Input changed during archive copy")
                            target.write(chunk)
                            remaining -= len(chunk)
                padding = (-offset) % ALIGNMENT
                target.write(b"\0" * padding)
                target.flush()
                os.fsync(target.fileno())
            # Re-open and validate both metadata tables before making the file final.
            verified = ForgeArchive(temporary)
            for file_id, data in replacements.items():
                if verified.read_raw(file_id) != data:
                    raise ForgeFormatError("Replacement differs after archive write")
            if overwrite:
                os.replace(temporary, destination)
            else:
                # rename does not replace an existing target on Windows.
                if destination.exists():
                    raise FileExistsError(destination)
                temporary.rename(destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        return {"destination": str(destination), "entries": len(self.entries),
                "replacements": len(replacements), "size": offset + padding}
