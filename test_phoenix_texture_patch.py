# SPDX-License-Identifier: GPL-2.0-or-later
"""Narrow texture-scope and binary-integrity checks; never touches game files."""
import dataclasses
import hashlib
from pathlib import Path
import unittest

from phoenix_texture_patch import TARGETS, TextureTarget, change_details, hide_texture

try:
    from PIL import Image
except ImportError:
    Image = None


FIXTURES = Path(__file__).resolve().parent / "analysis_red_textures"
# Independently inspected boundary: 457 bytes of resources/header, then one
# 128x128 BC7 mip (1024 blocks), with no bytes after the pixels.
EXPECTED_PIXEL_START = 457
EXPECTED_PIXEL_BYTES = 16384


class PhoenixTexturePatchTests(unittest.TestCase):
    def fixture(self, target):
        path = FIXTURES / (target.archive + "__" + target.name + ".set1.bin")
        if not path.is_file():
            self.skipTest("Optional inspected texture fixture unavailable: " + str(path))
        return path.read_bytes()

    def test_only_detection_disc_base_and_patch_are_authorized(self):
        self.assertEqual(len(TARGETS), 2)
        self.assertEqual({(target.archive, target.name) for target in TARGETS}, {
            ("DataPC_extra.forge", "UI_HUD_Mark_Detection_MapDesc"),
            ("DataPC_extra_patch_01.forge", "UI_HUD_Mark_Detection_MapDesc"),
        })

    def test_pixels_only_change_with_exact_body_and_header_preservation(self):
        for target in TARGETS:
            with self.subTest(archive=target.archive):
                original = self.fixture(target)
                supplied = bytearray(original)
                result = hide_texture(supplied, target)
                self.assertIsInstance(result, bytes)
                self.assertEqual(bytes(supplied), original)
                self.assertEqual(len(result), 16841)
                self.assertEqual(len(result), len(original))
                self.assertEqual(result[:EXPECTED_PIXEL_START], original[:EXPECTED_PIXEL_START])
                self.assertEqual(result[EXPECTED_PIXEL_START + EXPECTED_PIXEL_BYTES:],
                                 original[EXPECTED_PIXEL_START + EXPECTED_PIXEL_BYTES:])
                self.assertNotEqual(result, original)
                changed = {i for i, (old, new) in enumerate(zip(original, result)) if old != new}
                self.assertTrue(changed)
                self.assertTrue(all(EXPECTED_PIXEL_START <= i < EXPECTED_PIXEL_START + EXPECTED_PIXEL_BYTES
                                    for i in changed))

    def test_different_base_and_patch_metadata_survive(self):
        base, patch = (self.fixture(target) for target in TARGETS)
        self.assertNotEqual(hashlib.sha256(base).digest(), hashlib.sha256(patch).digest())
        results = [hide_texture(data, target) for data, target in zip((base, patch), TARGETS)]
        self.assertNotEqual(results[0][:EXPECTED_PIXEL_START], results[1][:EXPECTED_PIXEL_START])
        self.assertEqual(results[0][EXPECTED_PIXEL_START:], results[1][EXPECTED_PIXEL_START:])

    def test_unknown_targets_cannot_authorize_other_textures(self):
        target = TARGETS[0]
        original = self.fixture(target)
        forbidden = (
            dataclasses.replace(target, name="UI_HUD_MarkIcon_MapDesc"),
            dataclasses.replace(target, name="UI_HUD_detection_BG_MapDesc"),
            dataclasses.replace(target, name="HUD_Marker_FriendlyNPC"),
            dataclasses.replace(target, archive="DataPC.forge"),
            dataclasses.replace(target, sha256="0" * 64),
            object(),
        )
        for altered in forbidden:
            with self.subTest(target=altered):
                with self.assertRaises(ValueError):
                    hide_texture(original, altered)
                with self.assertRaises(ValueError):
                    change_details(altered)

    def test_wrong_copy_hash_or_prior_modification_is_rejected(self):
        for target in TARGETS:
            original = self.fixture(target)
            cases = [b"", original[:456], original[:-1], original + b"\0",
                     hide_texture(original, target), self.fixture(next(t for t in TARGETS if t != target))]
            for offset in (0, 12, 295, 333, 401, 429, 453, 457, len(original) - 1):
                changed = bytearray(original)
                changed[offset] ^= 1
                cases.append(changed)
            for body in cases:
                with self.subTest(archive=target.archive, length=len(body)):
                    before = bytes(body)
                    with self.assertRaises(ValueError):
                        hide_texture(body, target)
                    self.assertEqual(bytes(body), before)

    def test_manifest_describes_only_the_approved_pixel_change(self):
        for target in TARGETS:
            details = change_details(target)
            self.assertEqual(details["name"], "UI_HUD_Mark_Detection_MapDesc")
            self.assertEqual(details["format"], "BC7")
            self.assertEqual(details["pixel_offset"], EXPECTED_PIXEL_START)
            self.assertEqual(details["pixel_length"], EXPECTED_PIXEL_BYTES)
            self.assertEqual((details["width"], details["height"], details["mip_count"]), (128, 128, 1))
            self.assertEqual(details["decoded_rgba"], [0, 0, 0, 0])
            self.assertEqual(details["original_set1_sha256"], target.sha256)

    @unittest.skipUnless(Image is not None, "Independent BC7 decode needs Pillow (bundled Python provides it)")
    def test_independent_bc7_decoder_confirms_transparency_for_every_texel(self):
        for target in TARGETS:
            with self.subTest(archive=target.archive):
                original = self.fixture(target)
                before = Image.frombytes("RGBA", (128, 128), original[EXPECTED_PIXEL_START:], "bcn", (7,))
                result = hide_texture(original, target)
                after = Image.frombytes("RGBA", (128, 128), result[EXPECTED_PIXEL_START:], "bcn", (7,))
                self.assertGreater(before.getchannel("A").getextrema()[1], 0)
                self.assertEqual(after.getextrema(), ((0, 0), (0, 0), (0, 0), (0, 0)))
                self.assertEqual(after.tobytes(), bytes(128 * 128 * 4))


if __name__ == "__main__":
    unittest.main(verbosity=2)
