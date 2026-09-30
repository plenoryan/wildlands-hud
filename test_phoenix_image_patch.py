# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify V3 preserves working V2 data and edits only hostile image references."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest import mock

from phoenix_image_patch import (LEAF_TARGETS, IMAGE_GUID, hide_enemy_visuals,
                                 image_references, verify_image_provider, PROVIDER_ID,
                                 dependencies, DEPENDENCY_REPLACEMENTS)
from phoenix_leaf_patch import hide_visuals
from phoenix_visual import records

ROOT = Path(__file__).resolve().parent


def sample(target):
    return (ROOT / "analysis_assets" / target.archive / (target.name + ".set1.bin")).read_bytes()


@unittest.skipUnless((ROOT / "analysis_assets").is_dir(), "Optional proprietary fixtures are not distributed")
class ImagePatchTests(unittest.TestCase):
    def test_v3_preserves_all_v2_edits_and_changes_only_image_reference_bytes(self):
        image_count = text_count = nested_count = 0
        red_nodes = set()
        for target in LEAF_TARGETS:
            with self.subTest(archive=target.archive, name=target.name):
                original = sample(target)
                v2 = hide_visuals(original, target)
                v3 = hide_enemy_visuals(original, target)
                self.assertEqual(len(v3), len(v2))
                allowed = set()
                for node, offset in image_references(original):
                    self.assertEqual(v3[offset:offset + 16], IMAGE_GUID.bytes_le)
                    self.assertEqual(v3[offset - 9:offset], v2[offset - 9:offset])
                    allowed.update(range(offset, offset + 16))
                    image_count += 1
                    red_nodes.add(node["name"])
                dep = DEPENDENCY_REPLACEMENTS[target.sha256]
                if dep is not None:
                    allowed.update(range(dep[0], dep[0] + 8))
                # Restore only the permitted reference bytes; every remaining
                # byte must match V2, including text, animation, ID and alpha.
                comparison = bytearray(v3)
                for offset in allowed:
                    comparison[offset] = v2[offset]
                self.assertEqual(bytes(comparison), v2)
                self.assertEqual(records(v3), records(v2))
                text_count += sum(n["type"] == "e504a441" for n in records(v3))
                nested_count += sum(n["type"] == "3313560f" for n in records(v3))
        self.assertEqual((image_count, text_count, nested_count), (176, 36, 23))
        self.assertTrue({"AnimState", "showFeedBack", "bg", "anim", "UI_HUD_ObjectiveIcon"} <= red_nodes)

    def test_dependencies_match_independent_survey_and_keep_non_image_dependencies(self):
        surveyed = json.loads((ROOT / "analysis_red_routing/dependency_binding_review.json").read_text())
        changed_count = 0
        from uuid import UUID
        for target in LEAF_TARGETS:
            before = sample(target)
            after = hide_enemy_visuals(before, target)
            row = next(r for r in surveyed if (r["archive"], r["resource"]) == (target.archive, target.name))
            expected = [(d["offset"], d["id"]) for d in row["dependencies"]]
            self.assertEqual(dependencies(before, target), expected)
            changed = [(offset, old) for offset, old in expected
                       if struct.unpack_from("<Q", after, offset)[0] != old]
            self.assertLessEqual(len(changed), 1)
            for offset, old in changed:
                old_dep = next(d for d in row["dependencies"] if d["offset"] == offset)
                self.assertTrue(old_dep["image"])
                self.assertNotIn(UUID(old_dep["name"][-36:]).bytes_le, after)
                self.assertEqual(struct.unpack_from("<Q", after, offset)[0], PROVIDER_ID)
            self.assertEqual(sum(fid == PROVIDER_ID for _, fid in dependencies(after, target)), 1)
            self.assertEqual(len(dependencies(after, target)), len(expected))
            changed_count += len(changed)
        self.assertEqual(changed_count, 21)

    def test_reference_offsets_and_byte_order_match_independent_routing_survey(self):
        surveyed = json.loads((ROOT / "analysis_red_routing/image_routes.json").read_text())
        from uuid import UUID
        for target in LEAF_TARGETS:
            body = sample(target)
            expected = [r for r in surveyed if r["archive"] == target.archive and r["resource"] == target.name]
            actual = list(image_references(body))
            self.assertEqual(len(actual), len(expected))
            for row in expected:
                offset = row["reference_offset"]
                self.assertEqual(body[offset:offset + 16], UUID(row["image_guid"]).bytes_le)
                self.assertIn(offset, [at for _, at in actual])

    def test_existing_detection_references_remain_valid(self):
        count = 0
        for target in LEAF_TARGETS:
            body = sample(target)
            for node, offset in image_references(body):
                if body[offset:offset + 16] == IMAGE_GUID.bytes_le:
                    count += 1
        self.assertEqual(count, 6)

    def test_friendly_resource_cannot_be_authorized_with_forged_hash(self):
        path = next((ROOT / "analysis_assets").glob("*/*FriendlyPlayer_852A*.set1.bin"))
        body = path.read_bytes()
        forged = replace(LEAF_TARGETS[0], name=path.name[:-9], sha256=hashlib.sha256(body).hexdigest())
        with self.assertRaisesRegex(ValueError, "not an inspected"):
            hide_enemy_visuals(body, forged)

    def test_changed_reference_and_reapplication_are_refused(self):
        target = LEAF_TARGETS[0]
        body = sample(target)
        offset = next(image_references(body))[1]
        corrupt = body[:offset] + b"\0" * 16 + body[offset + 16:]
        for candidate in (corrupt, hide_enemy_visuals(body, target)):
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                hide_enemy_visuals(candidate, target)

    def test_malformed_image_reference_layout_is_refused(self):
        body = sample(LEAF_TARGETS[0])
        offset = next(image_references(body))[1]
        corrupt = body[:offset - 4] + b"bad!" + body[offset:]
        with self.assertRaisesRegex(ValueError, "layout"):
            list(image_references(corrupt))

    def test_missing_transparent_image_provider_is_refused(self):
        archive = mock.Mock()
        archive.find.return_value = []
        with self.assertRaisesRegex(ValueError, "provider missing"):
            verify_image_provider(archive, None)


if __name__ == "__main__":
    unittest.main()
