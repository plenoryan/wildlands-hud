# SPDX-License-Identifier: GPL-2.0-or-later
"""V2 verifies exact edit scope on shipped assets, including dynamic UI graphs."""
from collections import Counter
from dataclasses import replace
import hashlib
from pathlib import Path
import struct
import unittest

from phoenix_leaf_patch import TARGETS, hide_visuals
from phoenix_visual import records

SAMPLES = Path(__file__).with_name("analysis_assets")


@unittest.skipUnless(SAMPLES.is_dir(), "Optional proprietary fixtures are not distributed")
class LeafTests(unittest.TestCase):
    def test_all_shipped_targets_keep_every_non_xy_byte(self):
        count = 0
        for target in TARGETS:
            with self.subTest(asset=target.name, archive=target.archive):
                body = (SAMPLES / target.archive / (target.name + ".set1.bin")).read_bytes()
                before = records(body)
                changed = hide_visuals(body, target)
                after = records(changed)
                self.assertEqual(len(body), len(changed))
                self.assertEqual(len(before), len(after))
                allowed = set()
                for old, new in zip(before, after):
                    self.assertEqual(new["scale"], (0.0, 0.0, old["scale"][2]))
                    self.assertEqual(new["guid"], old["guid"])
                    self.assertEqual(new["name"], old["name"])
                    self.assertEqual(new["alpha"], old["alpha"])
                    allowed.update(range(old["scale_offset"], old["scale_offset"] + 8))
                    count += 1
                self.assertTrue(all(a == b or i in allowed
                                    for i, (a, b) in enumerate(zip(body, changed))))
        self.assertEqual(count, 235)

    def test_expected_enemy_leaf_coverage_and_no_wrappers(self):
        types = Counter()
        named = set()
        for target in TARGETS:
            self.assertNotIn("Friendly", target.name)
            self.assertNotIn("_Container_", target.name)
            for record in records((SAMPLES / target.archive / (target.name + ".set1.bin")).read_bytes()):
                types[record["type"]] += 1
                named.add(record["name"])
        self.assertEqual(types, {"dd999fc1": 176, "e504a441": 36, "3313560f": 23})
        self.assertTrue({"DistanceSanta", "DistanceUnidad", "DistanceHVT", "Icon_Veteran",
                         "UI_HUD_Mark_Sniper", "AnimState", "bg", "anim"} <= named)

    def test_friendly_asset_cannot_be_authorized_by_forging_hash(self):
        friendly = next(SAMPLES.glob("*/*FriendlyPlayer_852A*.set1.bin"))
        body = friendly.read_bytes()
        forged = replace(TARGETS[0], name=friendly.name[:-9], sha256=hashlib.sha256(body).hexdigest())
        with self.assertRaisesRegex(ValueError, "not an inspected"):
            hide_visuals(body, forged)

    def test_corrupted_and_reapplied_resources_are_refused(self):
        target = TARGETS[0]
        body = (SAMPLES / target.archive / (target.name + ".set1.bin")).read_bytes()
        for candidate in (body[:-1], b"bad" + body[3:], hide_visuals(body, target)):
            with self.subTest(length=len(candidate)):
                with self.assertRaisesRegex(ValueError, "Unsupported"):
                    hide_visuals(candidate, target)

    def test_wrong_hostile_variant_is_refused(self):
        target = TARGETS[0]
        body = (SAMPLES / target.archive / (target.name + ".set1.bin")).read_bytes()
        with self.assertRaises(ValueError):
            hide_visuals(body, TARGETS[1])

    def test_real_zero_scale_precedent_retains_z(self):
        import json
        examples = json.loads((Path(__file__).parent / "analysis_scales/non_unit_scales.json").read_text())
        zero_xy = [x for x in examples if x["scale"] == [0.0, 0.0, 1.0]]
        self.assertTrue(zero_xy, "Need a stock zero-XY precedent before this experiment")


if __name__ == "__main__":
    unittest.main()
