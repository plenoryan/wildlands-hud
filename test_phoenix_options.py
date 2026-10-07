# SPDX-License-Identifier: GPL-2.0-or-later
import itertools
import os
from pathlib import Path
import unittest
from uuid import UUID
import phoenix_options as options
from phoenix_visual import records
from phoenix_image_patch import image_references
from phoenix_full_hud_patch import dependencies

FIXTURES=Path(os.environ.get('WILDLANDS_V5_FIXTURES','analysis_v5'))

class ChoiceTests(unittest.TestCase):
    def test_default_preserves_operational_hud_and_downed(self):
        targets=options.selected_targets()
        self.assertEqual({options.category(t) for t in targets},{key for key,value in options.DEFAULTS.items() if value})
        self.assertFalse(options.DEFAULTS['pings'])
        self.assertTrue(options.DEFAULTS['scanning'])
        self.assertFalse(options.DEFAULTS['optics'])
        self.assertTrue(options.DEFAULTS['weapons'])
        self.assertFalse(options.DEFAULTS['grenades'])
        for t in targets:
            self.assertTrue(t.name.startswith('HUD_Marker_') or t in options.ENEMIES or options.category(t) in ('scanning','weapons'))
            self.assertNotIn('FriendlyGauge',t.name)
            self.assertNotIn('HUD_Marker_Ping_',t.name)
            self.assertNotIn('HUD_Marker_Beacon_',t.name)
        self.assertEqual(options.selected_targets(dict.fromkeys(options.DEFAULTS,False)),())

    def test_all_combinations_are_independent_and_never_modify_textures(self):
        for values in itertools.product((False,True),repeat=len(options.DEFAULTS)):
            chosen=dict(zip(options.DEFAULTS,values))
            targets=options.selected_targets(chosen)
            self.assertEqual(len(targets),len({(t.archive,t.name) for t in targets}))
            self.assertTrue(all(chosen[options.category(t)] for t in targets))
            self.assertFalse(any('MapDesc' in t.name or 'ContextualInteraction' in t.name or 'ControlHelper' in t.name for t in targets))
        for key in options.DEFAULTS:
            chosen=dict.fromkeys(options.DEFAULTS,False);chosen[key]=True
            self.assertTrue(options.selected_targets(chosen),key)

    def test_invalid_options_rejected(self):
        for invalid in ({}, {'enemies':True},dict(options.DEFAULTS,enemies=1),dict(options.DEFAULTS,unknown=True)):
            with self.assertRaises(ValueError):options.selected_targets(invalid)

    def test_categories_cover_each_checkbox_exactly_once(self):
        keys=[key for _,_,children in options.GROUPS for key in children]
        self.assertEqual(len(keys),len(set(keys)))
        self.assertEqual(set(keys),set(options.DEFAULTS))

@unittest.skipUnless(FIXTURES.is_dir(),'Private game fixtures are not distributed')
class RealChoices(unittest.TestCase):
    def test_original_invisible_texture_is_transparent_in_both_archives(self):
        from PIL import Image
        for archive in options.TEXTURE_HASHES:
            body=(FIXTURES/(archive+'__4x4_Invisible_MapDesc.bin')).read_bytes()
            # Inspected 4x4 BC1, single mip, eight-byte payload.
            image=Image.frombytes('RGBA',(4,4),body[-8:],'bcn',(1,))
            self.assertEqual(image.getchannel('A').getextrema(),(0,0))

    def test_every_selected_image_uses_unmodified_invisible_provider(self):
        for target in options.ALL_TARGETS:
            body=(FIXTURES/target.archive/(target.name+'.bin')).read_bytes()
            patched=options.patch_selected(body,target)
            self.assertEqual(len(patched),len(body))
            references=list(image_references(patched))
            invisible=[o for _,o in references if patched[o:o+16]==options.INVISIBLE_GUID.bytes_le]
            if invisible:
                self.assertEqual(sum(i==options.INVISIBLE_ID for _,i in dependencies(patched,target)),1)
            self.assertFalse(any(patched[o:o+16]==options.OLD_IMAGE.bytes_le for _,o in references))

    def test_nested_kept_categories_never_scaled_by_another_choice(self):
        # Check across archive overrides: a nested instance must not hide a
        # category that the user left unchecked. This protects binocular/drone
        # controls and independently selected marker groups.
        by_guid={UUID(t.name[-36:]).bytes_le:options.category(t) for t in options.ALL_TARGETS}
        for t in options.ALL_TARGETS:
            body=(FIXTURES/t.archive/(t.name+'.bin')).read_bytes()
            patched=options.patch_selected(body,t)
            for node in records(body):
                if node['type']!='3313560f':continue
                child=by_guid.get(body[node['fields_offset']+103:node['fields_offset']+119])
                if child and child!=options.category(t):
                    pos=node['scale_offset']
                    self.assertEqual(patched[pos:pos+8],body[pos:pos+8],(t.name,node['name'],child))

    def test_operational_optics_never_suppresses_unselected_scanning(self):
        for t in options.ALL_TARGETS:
            if options.category(t)!='optics':continue
            body=(FIXTURES/t.archive/(t.name+'.bin')).read_bytes()
            patched=options.patch_selected(body,t)
            for node in records(body):
                if node['type']=='3313560f':
                    at=node['scale_offset']
                    self.assertEqual(body[at:at+8],patched[at:at+8])

    def test_weapon_parent_retains_grenade_selection_and_count(self):
        checked = 0
        for t in options.ALL_TARGETS:
            if not t.name.startswith('HUD_WeaponItemDisplay_C607'):continue
            body=(FIXTURES/t.archive/(t.name+'.bin')).read_bytes()
            patched=options.patch_selected(body,t)
            for node in records(body):
                if node['name'] not in ('Hud_WeaponItemDisplay_Item','HUD_WeaponItemDisplay_SwitchItems'):continue
                start=node['fields_offset']; end=start+119
                self.assertEqual(body[start:end],patched[start:end])
                checked+=1
        self.assertEqual(checked,4)  # Current item and selector in base + patch.

    def test_weapon_and_grenade_choices_are_separate(self):
        for weapons,grenades in itertools.product((False,True),repeat=2):
            selected=options.selected_targets(dict(options.DEFAULTS,weapons=weapons,grenades=grenades))
            names={t.name for t in selected}
            self.assertEqual(any(n.startswith('HUD_WeaponItemDisplay_MainWeapon_') for n in names),weapons)
            self.assertEqual(any(n.startswith('HUD_WeaponItemDisplay_Item_') for n in names),grenades)
            self.assertEqual(any(n.startswith('HUD_WeaponItemDisplay_SwitchItems_') for n in names),grenades)

if __name__=='__main__':unittest.main()
