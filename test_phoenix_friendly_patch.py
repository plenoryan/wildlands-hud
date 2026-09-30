# SPDX-License-Identifier: GPL-2.0-or-later
"""V4 regression: preserve downed-ally branch and every working enemy V3 edit."""
from dataclasses import replace
import hashlib
from pathlib import Path
import struct
import unittest

from phoenix_friendly_patch import (FRIENDLY_TARGETS, TARGETS, GAUGE_NAME, GAUGE_GUID,
                                     GAUGE_HASHES, OOS_NAMES, OOS_EDITS, hide_normal_allies, hide_markers_except_downed)
from phoenix_image_patch import (TARGETS as V3_TARGETS, hide_enemy_visuals, IMAGE_GUID,
                                 PROVIDER_ID, dependencies)
from phoenix_texture_patch import TextureTarget
from phoenix_visual import records

ROOT = Path(__file__).resolve().parent


def sample(target):
    if isinstance(target, TextureTarget):
        return (ROOT / "analysis_red_textures" / (target.archive + "__" + target.name + ".set1.bin")).read_bytes()
    return (ROOT / "analysis_assets" / target.archive / (target.name + ".set1.bin")).read_bytes()


@unittest.skipUnless((ROOT / "analysis_assets").is_dir(), "Optional proprietary fixtures are not distributed")
class FriendlyPatchTests(unittest.TestCase):
    def test_v3_enemy_changes_are_preserved_exactly(self):
        for target in V3_TARGETS:
            body = sample(target)
            self.assertEqual(hide_markers_except_downed(body, target), hide_enemy_visuals(body, target))

    def test_all_32_normal_visuals_hidden_and_downed_visuals_unchanged(self):
        images = texts = gauges = arrows = 0
        for target in FRIENDLY_TARGETS:
            old = sample(target)
            new = hide_normal_allies(old, target)
            self.assertEqual(len(old), len(new))
            allowed = set(range(target.dependency_offset, target.dependency_offset + 8))
            if target.player:
                for offset, _, _ in OOS_EDITS[target.archive]:
                    allowed.update(range(offset, offset + 4))
            for before, after in zip(records(old), records(new)):
                if before["name"] == GAUGE_NAME:
                    gauges += 1
                    self.assertEqual(before, after)
                    offset = before["fields_offset"]
                    self.assertEqual(new[offset:offset + 119], old[offset:offset + 119])
                    self.assertEqual(new[offset + 103:offset + 119], GAUGE_GUID.bytes_le)
                    continue
                if before["name"] in OOS_NAMES:
                    arrows += 1
                    offset = before["fields_offset"]
                    self.assertEqual(before, after)
                    self.assertEqual(new[offset:offset + 119], old[offset:offset + 119])
                    continue
                self.assertEqual(after["scale"], (0.0, 0.0, 1.0))
                allowed.update(range(before["scale_offset"], before["scale_offset"] + 8))
                if before["type"] == "dd999fc1":
                    images += 1
                    offset = before["fields_offset"] + 103
                    allowed.update(range(offset, offset + 16))
                    self.assertEqual(new[offset:offset + 16], IMAGE_GUID.bytes_le)
                else:
                    self.assertEqual(before["type"], "e504a441")
                    texts += 1
            # This also preserves all conditional Heal/Default/Active curves,
            # visible bindings, masks, object IDs, and the nested gauge itself.
            self.assertTrue(all(a == b or i in allowed for i, (a, b) in enumerate(zip(old, new))))
        self.assertEqual((images, texts, gauges, arrows), (16, 16, 2, 4))

    def test_offscreen_arrow_uses_downed_and_out_of_sight_flags_only(self):
        # Read the actual serialized property IDs of the inspected AND binding.
        # Default=0, Active=1, Revive=2 are the original PlayerState constants.
        for target in (t for t in FRIENDLY_TARGETS if t.player):
            body = hide_normal_allies(sample(target), target)
            locations = (0x2634, 0x265E, 0x2923) if target.archive == "DataPC_extra.forge" else (0x268C, 0x26B6, 0x297B)
            left, right, destination_source = [struct.unpack_from("<I", body, p)[0] for p in locations]
            self.assertEqual(destination_source, 0x1C1F21A1)  # NotFocused result
            for state in (0, 1, 2):
                for offscreen in (False, True):
                    properties = {0x156E429E: state == 2, 0x1C63E672: offscreen}
                    result = properties[left] and properties[right]
                    self.assertEqual(result, state == 2 and offscreen)
                    self.assertFalse(state == 1 and result)  # cannot trigger ActiveUnfocused
                    self.assertFalse(state == 0 and result)  # cannot show normal active arrow

    def test_only_one_image_dependency_changes_all_others_survive(self):
        for target in FRIENDLY_TARGETS:
            before = dependencies(sample(target), target)
            after = dependencies(hide_normal_allies(sample(target), target), target)
            self.assertEqual(len(before), len(after))
            changed = [(old, new) for old, new in zip(before, after) if old != new]
            self.assertEqual(len(changed), 1)
            self.assertEqual(changed[0][1], (target.dependency_offset, PROVIDER_ID))
            if target.player:
                # Native dependency of the preserved FriendlyGauge resource.
                self.assertIn(512489394492, [fid for _, fid in after])

    def test_downed_gauges_and_containers_are_not_targets(self):
        for archive, digest in GAUGE_HASHES.items():
            path = ROOT / "analysis_assets" / archive / (GAUGE_NAME + "_" + str(GAUGE_GUID).upper() + ".set1.bin")
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
        for target in TARGETS:
            self.assertNotIn(GAUGE_NAME, target.name)
            self.assertNotIn("FriendlyPlayer_Container", target.name)

    def test_unauthorized_gauge_cannot_be_hidden_with_a_forged_target(self):
        target = FRIENDLY_TARGETS[0]
        path = ROOT / "analysis_assets" / target.archive / (GAUGE_NAME + "_" + str(GAUGE_GUID).upper() + ".set1.bin")
        body = path.read_bytes()
        forged = replace(target, name=path.name[:-9], sha256=hashlib.sha256(body).hexdigest())
        with self.assertRaisesRegex(ValueError, "not an inspected"):
            hide_normal_allies(body, forged)

    def test_different_version_corruption_and_reapplication_refused(self):
        for target in FRIENDLY_TARGETS:
            body = sample(target)
            cases = (body[:-1], b"x" + body[1:], hide_normal_allies(body, target))
            for candidate in cases:
                with self.assertRaisesRegex(ValueError, "Unsupported"):
                    hide_normal_allies(candidate, target)


if __name__ == "__main__":
    unittest.main()
