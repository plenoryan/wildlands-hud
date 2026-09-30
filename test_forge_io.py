# SPDX-License-Identifier: GPL-2.0-or-later
"""Focused safety tests; the optional installed-game checks are read-only."""
import os
import pathlib
import struct
import tempfile
import unittest

from forge_io import (ALIGNMENT, MAGIC, SET_HEADER, INDEX_RECORD, SECTION_HEADER,
                      Block, BlockSet, BlockPayload, ForgeArchive, ForgeFormatError,
                      LzoCodec, adler32_zero, decode_payload, encode_payload)


def raw_payload(*sets, trailer=b""):
    result = []
    for set_blocks in sets:
        header = SET_HEADER.pack(MAGIC, 1, 1, 0x8000, 0x8000, len(set_blocks))
        result.append(BlockSet(header, tuple(Block(data, data, adler32_zero(data)) for data in set_blocks)))
    return encode_payload(BlockPayload(tuple(result), trailer))


def synthetic_forge(path):
    payloads = [raw_payload([b"first"]), raw_payload([b"second"]), raw_payload([b"third"])]
    data = bytearray(ALIGNMENT)
    data[:21] = b"scimitar" + b"\0" + struct.pack("<IQ", 27, 64)
    struct.pack_into("<I", data, 64, 3)
    struct.pack_into("<q", data, 100, 128)
    SECTION_HEADER.pack_into(data, 128, 2, 0, 256, 176, 0, 1, 512, 0)
    SECTION_HEADER.pack_into(data, 176, 1, 0, 296, -1, 2, 2, 896, 0)
    position = 4096
    for i, payload in enumerate(payloads):
        INDEX_RECORD.pack_into(data, 256 + i * 20, position, i + 1, len(payload))
        record = 512 + i * 192
        struct.pack_into("<I", data, record, len(payload))
        name = b"duplicate" if i < 2 else b"third"
        data[record + 44:record + 44 + len(name)] = name
        data[position:position + len(payload)] = payload
        position += len(payload)
    path.write_bytes(data)
    return bytes(data)


class BlockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codec = LzoCodec()

    def test_multiple_sets_blocks_and_trailer_roundtrip(self):
        original = raw_payload([b"resource header"], [b"a" * 32000, b"b" * 200, b"c" * 45], trailer=b"preserved trailer")
        payload = decode_payload(original, self.codec)
        self.assertEqual(encode_payload(payload, codec=self.codec), original)
        changed = b"a" * 32000 + b"d" * 200 + b"c" * 45
        encoded = encode_payload(payload, {1: changed}, self.codec)
        result = decode_payload(encoded, self.codec)
        self.assertEqual(result.sets[0], payload.sets[0])
        self.assertEqual(result.sets[1].blocks[0], payload.sets[1].blocks[0])
        self.assertEqual(result.sets[1].blocks[2], payload.sets[1].blocks[2])
        self.assertEqual(result.sets[1].data, changed)
        self.assertEqual(result.trailer, b"preserved trailer")

    def test_growing_and_shrinking_data(self):
        payload = decode_payload(raw_payload([b"header"], [b"old body"]), self.codec)
        for changed in (b"x", b"changed" * 20000):
            result = decode_payload(encode_payload(payload, {1: changed}, self.codec), self.codec)
            self.assertEqual(result.sets[1].data, changed)
            self.assertEqual(result.sets[1].header[:15], payload.sets[1].header[:15])
            self.assertTrue(all(len(block.data) <= 0x8000 for block in result.sets[1].blocks))

    def test_corrupt_checksum_and_truncated_block_rejected(self):
        original = raw_payload([b"abcdef"])
        damaged = bytearray(original)
        damaged[-1] ^= 1
        with self.assertRaisesRegex(ForgeFormatError, "Checksum"):
            decode_payload(damaged, self.codec)
        for cutoff in (7, 18, 22, len(original) - 1):
            with self.assertRaises(ForgeFormatError):
                decode_payload(original[:cutoff], self.codec)

    def test_zero_seed_checksum_and_safe_lzo(self):
        self.assertEqual(adler32_zero(b"abc"), 0x024A0126)
        data = b"some repeatable text" * 500
        compressed = self.codec.compress(data)
        self.assertEqual(self.codec.decompress(compressed, len(data)), data)
        with self.assertRaises(ForgeFormatError):
            self.codec.decompress(compressed, len(data) - 1)
        with self.assertRaises(ForgeFormatError):
            self.codec.decompress(b"corrupt", 20)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="wildlands_forge_test_")
        self.root = pathlib.Path(self.directory.name)
        self.source = self.root / "source.forge"
        self.original = synthetic_forge(self.source)

    def tearDown(self):
        self.directory.cleanup()

    def test_noop_byte_identical_and_multisection(self):
        archive = ForgeArchive(self.source)
        self.assertEqual(len(archive.entries), 3)
        self.assertEqual(len(archive.find("duplicate")), 2)
        archive.rebuild(self.root / "noop.forge", {})
        self.assertEqual((self.root / "noop.forge").read_bytes(), self.original)

    def test_grow_reflow_both_tables_and_alignment(self):
        archive = ForgeArchive(self.source)
        changed = b"new stored entry" * 3000
        archive.rebuild(self.root / "changed.forge", {2: changed})
        rebuilt = ForgeArchive(self.root / "changed.forge")
        self.assertEqual(rebuilt.read_raw(2), changed)
        self.assertEqual(rebuilt.read_raw(1), archive.read_raw(1))
        self.assertEqual(rebuilt.read_raw(3), archive.read_raw(3))
        self.assertEqual(rebuilt.entries[2].offset, rebuilt.entries[1].offset + len(changed))
        self.assertEqual(rebuilt.file_size % ALIGNMENT, 0)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_source_and_existing_destination_are_protected(self):
        archive = ForgeArchive(self.source)
        with self.assertRaises(ValueError):
            archive.rebuild(self.source, {})
        target = self.root / "exists.forge"
        target.write_bytes(b"keep")
        with self.assertRaises(FileExistsError):
            archive.rebuild(target, {})
        self.assertEqual(target.read_bytes(), b"keep")

    def test_table_corruption_and_section_cycle_rejected(self):
        changed = bytearray(self.original)
        struct.pack_into("<I", changed, 512, 999)
        self.source.write_bytes(changed)
        with self.assertRaisesRegex(ForgeFormatError, "size mismatch"):
            ForgeArchive(self.source)
        changed = bytearray(self.original)
        struct.pack_into("<q", changed, 176 + 16, 128)
        self.source.write_bytes(changed)
        with self.assertRaisesRegex(ForgeFormatError, "Cycle"):
            ForgeArchive(self.source)


GAME = pathlib.Path(os.environ.get("WILDLANDS_TEST_GAME", "__no_game_fixture_configured__"))


@unittest.skipUnless((GAME / "DataPC_extra.forge").is_file(), "Wildlands is not installed here")
class InstalledArchiveReadOnlyTests(unittest.TestCase):
    def test_enemy_ui_and_crosshair_roundtrip(self):
        codec = LzoCodec()
        total = 0
        for filename in ("DataPC_extra.forge", "DataPC_extra_patch_01.forge"):
            archive = ForgeArchive(GAME / filename)
            for entry in archive.entries:
                if "HUD_Marker_Hostile" not in entry.name and "Crosshair" not in entry.name:
                    continue
                raw = archive.read_raw(entry)
                payload = decode_payload(raw, codec)
                self.assertEqual(encode_payload(payload, codec=codec), raw, entry.name)
                total += 1
        self.assertGreater(total, 30)


if __name__ == "__main__":
    unittest.main(verbosity=2)
