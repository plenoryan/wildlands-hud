# SPDX-License-Identifier: GPL-2.0-or-later
import os
from pathlib import Path
import struct
import unittest
from uuid import UUID

import phoenix_full_hud_patch as v5
from phoenix_friendly_patch import TARGETS as V4_TARGETS, GAUGE_GUID, hide_markers_except_downed
from phoenix_image_patch import image_references, IMAGE_GUID, PROVIDER_ID
from phoenix_visual import records

FIXTURES = Path(os.environ.get('WILDLANDS_V5_FIXTURES', 'analysis_v5'))


class InventoryTests(unittest.TestCase):
    def test_only_explicit_hud_targets_no_menu_or_gauge(self):
        identities = [(t.archive, t.name) for t in v5.TARGETS]
        self.assertEqual(len(identities), len(set(identities)))
        self.assertEqual(len(v5.HUD_TARGETS), 516)
        for t in v5.HUD_TARGETS:
            self.assertTrue(t.name.startswith(('HUD_', 'CrossHair_')) or '_HUD_' in t.name)
            self.assertNotIn('HUD_Marker_Friendly', t.name)
            self.assertFalse(t.name.startswith(('HUD_ContextualInteraction_', 'HUD_ControlHelper_')))
            self.assertEqual(len(t.sha256), 64)
            self.assertTrue(t.hide_guids)

    def test_generators_and_comparable_object_markers_in_both_archives(self):
        objects = [t for t in v5.HUD_TARGETS if t.name.startswith('HUD_Marker_ObjectIntel_753')]
        self.assertEqual(len(objects), 2)
        self.assertEqual({t.node_count for t in objects}, {36, 44})
        for t in objects:
            self.assertEqual(len(t.hide_guids), t.node_count)

    def test_unknown_resource_rejected(self):
        with self.assertRaises(ValueError):
            v5.hide_hud_except_downed(b'unknown game version', v5.HUD_TARGETS[0])
        with self.assertRaises(ValueError):
            v5.hide_hud_except_downed(b'', object())


@unittest.skipUnless(FIXTURES.is_dir(), 'Private game fixtures are not distributed')
class RealResourceTests(unittest.TestCase):
    def test_only_intended_bytes_change_and_image_provider_is_loaded(self):
        for target in v5.HUD_TARGETS:
            with self.subTest(resource=target.name, archive=target.archive):
                body = (FIXTURES / target.archive / (target.name + '.bin')).read_bytes()
                patched = v5.hide_hud_except_downed(body, target)
                self.assertEqual(len(body), len(patched))
                allowed = set()
                for node in records(body):
                    pos = node['scale_offset']
                    if node['guid'] in target.hide_guids:
                        allowed.update(range(pos, pos + 8))
                        self.assertEqual(struct.unpack_from('<2f', patched, pos), (0, 0))
                    else:
                        self.assertEqual(body[pos:pos+12], patched[pos:pos+12])
                refs = list(image_references(body))
                for _, pos in refs:
                    allowed.update(range(pos, pos + 16))
                    self.assertEqual(patched[pos:pos+16], IMAGE_GUID.bytes_le)
                if target.dependency:
                    allowed.update(range(target.dependency[0], target.dependency[0] + 8))
                if refs:
                    self.assertEqual(sum(fid == PROVIDER_ID for _, fid in v5.dependencies(patched,target)),1)
                self.assertTrue(all(i in allowed for i,(a,b) in enumerate(zip(body,patched)) if a != b))

    def test_v4_behaviour_identical_and_gauge_chain_never_scaled(self):
        for target in V4_TARGETS:
            path = FIXTURES / target.archive / (target.name + '.bin')
            if path.is_file():
                body=path.read_bytes()
                self.assertEqual(v5.hide_hud_except_downed(body,target),hide_markers_except_downed(body,target))
        # Walk all widget references across both archive versions. Any parent
        # leading to the downed gauge must keep its child instance untouched.
        resources=[]
        for path in FIXTURES.glob('*/*.bin'):
            try:
                guid=UUID(path.stem[-36:]).bytes_le
            except ValueError:
                continue
            resources.append((path,guid,path.read_bytes()))
        protected={GAUGE_GUID.bytes_le}
        protected.update(guid for path,guid,_ in resources if path.stem.startswith(('HUD_ContextualInteraction_', 'HUD_ControlHelper_')))
        while True:
            parents={guid for _,guid,body in resources if any(n['type']=='3313560f' and body[n['fields_offset']+103:n['fields_offset']+119] in protected for n in records(body))}
            if parents <= protected:break
            protected |= parents
        targets={(t.archive,t.name):t for t in v5.HUD_TARGETS}
        for path,_,body in resources:
            target=targets.get((path.parent.name,path.stem))
            if not target:continue
            for n in records(body):
                if n['type']=='3313560f' and body[n['fields_offset']+103:n['fields_offset']+119] in protected:
                    self.assertNotIn(n['guid'],target.hide_guids)


if __name__ == '__main__':
    unittest.main()
