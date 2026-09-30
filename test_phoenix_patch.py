# SPDX-License-Identifier: GPL-2.0-or-later
"""Integrity and scope tests using the inspected, optional Phoenix fixtures.

Run with ``python -m unittest test_phoenix_patch -v``. Tests never write fixtures
or game files. Extracted assets are optional and fixture tests skip when absent.
"""
import hashlib
from pathlib import Path
import unittest

from phoenix_patch import TARGETS, Target, hide_container


FIXTURES = Path(__file__).resolve().parent / "analysis_assets"

# Independent inspection results: a change outside one of these four-byte
# regions would affect something other than the intended parent opacity.
EXPECTED_TARGETS = {
    "DLC_HUD_Marker_Hostile_PMC_Container_533050F2-72DE-4788-AB2B-55879158CF3C": ("DataPC_extra.forge", 0x240),
    "DLC_HUD_Marker_Hostile_Rebel_Container_F7544F6C-B771-4A9D-8816-1A0E1702A5BA": ("DataPC_extra.forge", 0x246),
    "HUD_Marker_HostileNPC_Container_46328289-79C3-4B70-967F-B37D4B8FFE63": ("DataPC_extra.forge", 0x231),
    "HUD_Marker_HostilePlayer_Container_62EBE99E-B4AD-4C63-829A-1BC0793B0508": ("DataPC_extra.forge", 0x23E),
    "HUD_Marker_Hostile_Detection_Container_6994F53A-C71A-4F20-9CC2-0E3A15BE17E2": ("DataPC_extra.forge", 0x246),
    "HUD_Marker_Hostile_SantaBlanca_Container_ACA6C5AA-2946-4E94-A28E-5536313520CC": ("DataPC_extra.forge", 0x24C),
    "HUD_Marker_Hostile_Unidad_Container_88186DFF-0CD7-48D6-9F38-611F7274E0AD": ("DataPC_extra.forge", 0x23D),
    "HUD_Marker_Hostile_White_Container_D186076D-01AA-4358-8DF0-C3451FF6B2E5": ("DataPC_extra.forge", 0x23A),
    "DLC30_LAZ_HUD_Marker_Hostile_Penitentes_Container_7311063D-2B27-4860-AEA4-6DBAEA4088AE": ("DataPC_extra_patch_01.forge", 0x267),
}


class PhoenixPatchTests(unittest.TestCase):
    def fixture(self, archive, name):
        path = FIXTURES / archive / (name + ".set1.bin")
        if not path.is_file():
            self.skipTest("Optional extracted fixture unavailable: " + str(path))
        return path.read_bytes()

    def npc(self):
        target = next(item for item in TARGETS if item.child == "HUD_Marker_HostileNPC")
        return target, self.fixture(target.archive, target.name)

    def assert_rejected_without_mutation(self, body, target):
        # A mutable input makes unintended writes observable even on failure.
        supplied = bytearray(body)
        snapshot = bytes(supplied)
        with self.assertRaises(ValueError):
            hide_container(supplied, target)
        self.assertEqual(bytes(supplied), snapshot)

    def test_exact_nine_inspected_hostile_targets_only(self):
        self.assertEqual(len(TARGETS), 9)
        self.assertEqual(
            {item.name: (item.archive, item.alpha_offset) for item in TARGETS},
            EXPECTED_TARGETS,
        )
        self.assertTrue(all("Friendly" not in item.name for item in TARGETS))

    def test_unknown_layouts_are_rejected_without_mutation(self):
        target, original = self.npc()
        cases = {
            "empty": b"",
            "truncated_header": original[:12],
            "truncated_before_alpha": original[:target.alpha_offset],
            "truncated_after_alpha": original[:target.alpha_offset + 4],
            "extra_trailing_byte": original + b"\0",
        }
        changed_header = bytearray(original)
        changed_header[0] ^= 1
        cases["corrupt_resource_header"] = changed_header
        changed_magic = bytearray(original)
        changed_magic[original.index(b"PHXWI")] = ord("X")
        cases["unknown_ui_format"] = changed_magic
        changed_child = bytearray(original)
        child_offset = original.rindex(target.child.encode("ascii"))
        changed_child[child_offset] = ord("X")
        cases["corrupt_child_name"] = changed_child
        changed_alpha = bytearray(original)
        changed_alpha[target.alpha_offset:target.alpha_offset + 4] = b"\0\0\0?"
        cases["changed_opacity"] = changed_alpha
        changed_tail = bytearray(original)
        changed_tail[-1] ^= 1
        cases["unrecognised_version_even_outside_visual_fields"] = changed_tail
        for label, body in cases.items():
            with self.subTest(case=label):
                self.assert_rejected_without_mutation(body, target)

    def test_reapplication_is_rejected(self):
        target, original = self.npc()
        already_patched = hide_container(original, target)
        self.assert_rejected_without_mutation(already_patched, target)

    def test_wrong_hostile_target_is_rejected(self):
        target, original = self.npc()
        wrong_target = next(item for item in TARGETS if item != target)
        self.assert_rejected_without_mutation(original, wrong_target)

    def test_unlisted_target_cannot_authorize_an_arbitrary_offset(self):
        target, original = self.npc()
        forged = Target(target.archive, target.name, target.sha256, 0, target.child)
        self.assert_rejected_without_mutation(original, forged)


def preserved_fixture_test(name, archive, alpha_offset):
    def test(self):
        original = self.fixture(archive, name)
        target = next(item for item in TARGETS if item.name == name)
        snapshot = bytes(original)
        result = hide_container(original, target)
        self.assertIsInstance(result, bytes)
        self.assertEqual(original, snapshot)
        self.assertEqual(len(result), len(original))
        self.assertEqual(original[alpha_offset:alpha_offset + 4], b"\0\0\x80?")
        self.assertEqual(result[alpha_offset:alpha_offset + 4], b"\0" * 4)
        self.assertEqual(result[:alpha_offset], original[:alpha_offset])
        self.assertEqual(result[alpha_offset + 4:], original[alpha_offset + 4:])
        changed = [i for i, (before, after) in enumerate(zip(original, result)) if before != after]
        self.assertEqual(changed, [alpha_offset + 2, alpha_offset + 3])
    return test


def ally_refusal_test(name, child, alpha_offset):
    def test(self):
        archive = "DataPC_extra.forge"
        body = self.fixture(archive, name)
        ally_target = Target(archive, name, hashlib.sha256(body).hexdigest(), alpha_offset, child)
        # Even an exact ally checksum and correct alpha offset cannot authorize it.
        self.assert_rejected_without_mutation(body, ally_target)
        # Passing an allowlisted hostile descriptor with ally bytes is also refused.
        self.assert_rejected_without_mutation(body, TARGETS[0])
    return test


for name, (archive, alpha_offset) in EXPECTED_TARGETS.items():
    setattr(PhoenixPatchTests, "test_preserves_every_other_byte_" + name,
            preserved_fixture_test(name, archive, alpha_offset))

for name, child, alpha_offset in (
    ("HUD_Marker_FriendlyNPC_Container_8794835B-C7D3-4ED6-9CA3-ED9A6663D882", "HUD_Marker_FriendlyNPC", 0x236),
    ("HUD_Marker_FriendlyPlayer_Container_69122488-EBE6-4B34-90AC-B4E4DAE678DB", "HUD_Marker_FriendlyPlayer", 0x23D),
):
    setattr(PhoenixPatchTests, "test_ally_refused_" + child,
            ally_refusal_test(name, child, alpha_offset))


if __name__ == "__main__":
    unittest.main()
