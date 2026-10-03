# SPDX-License-Identifier: GPL-2.0-or-later
"""Independent HUD choices. Checked means hidden; unchecked resources stay original.

Use the game's already-transparent 4x4 image, without altering any shared texture.
This avoids coupling unchecked enemy detection to other selected categories.
"""
from uuid import UUID
import hashlib
import struct
from phoenix_leaf_patch import TARGETS as ENEMIES
from phoenix_friendly_patch import FRIENDLY_TARGETS
from phoenix_full_hud_patch import HUD_TARGETS, hide_hud_except_downed, dependencies, change_details
from phoenix_image_patch import IMAGE_GUID as OLD_IMAGE, PROVIDER_ID as OLD_ID, image_references

OPTIONS = (
    ('enemies', 'Inimigos: ícones, nomes, distâncias e pulsos', True),
    ('objects', 'Objetos: geradores, alarmes, minas e afins', True),
    ('allies', 'Aliados normais: ícones, nomes e distâncias', True),
    ('world', 'Outros marcadores: objetivos, coleta, pings e tiro sincronizado', True),
    ('minimap', 'Minimapa', False),
    ('crosshair', 'Mira', False),
    ('optics', 'Informações do binóculo e drone', False),
    ('weapons', 'Informações de armas e munição', False),
)
DEFAULTS = {key: default for key, _, default in OPTIONS}
INVISIBLE_GUID = UUID('2C83D744-3019-426C-8619-F059C42FEDD8')
INVISIBLE_ID = 1241263910639
PROVIDER_NAME = '4x4_Invisible_' + str(INVISIBLE_GUID).upper()
PROVIDER_HASH = '6ec455b7a89f74ce9b18652b298bd40994992138fe30263437cc0c5c10948a9c'
TEXTURE_HASHES = {
    'DataPC_extra.forge': 'f3767465641f314bb0e80659e3df8e325912e574c7bb9a428c480ea791be0f42',
    'DataPC_extra_patch_01.forge': '3b0a9699cd6890fd4382377cb96eeb3d4be716708962fad50e6a2b5adc760118',
}


def normalize_options(options=None):
    if options is None:
        return dict(DEFAULTS)
    if not isinstance(options, dict) or set(options) != set(DEFAULTS) or any(type(v) is not bool for v in options.values()):
        raise ValueError('Seleção de opções inválida ou incompleta.')
    return dict(options)


def category(target):
    if target in ENEMIES:
        return 'enemies'
    if target in FRIENDLY_TARGETS:
        return 'allies'
    name = target.name
    if name.startswith('HUD_Marker_ObjectIntel_'):
        return 'objects'
    if name.startswith('HUD_Marker_') and not name.startswith(('HUD_Marker_Hostile', 'HUD_Marker_Friendly')):
        return 'world'
    for key, prefixes in (
        ('minimap', ('HUD_Minimap_', 'HUD_MinimapIcons_')),
        ('crosshair', ('CrossHair_',)),
        ('optics', ('HUD_Binocular_', 'HUD_BinocularMask_', 'HUD_BinocularCompassSection_', 'HUD_Drone_')),
        ('weapons', ('HUD_WeaponItemDisplay_', 'HUD_WeaponItem_')),
    ):
        if name.startswith(prefixes):
            return key
    return None


ALL_TARGETS = tuple(ENEMIES) + tuple(FRIENDLY_TARGETS) + tuple(t for t in HUD_TARGETS if category(t))


def selected_targets(options=None):
    chosen = normalize_options(options)
    return tuple(t for t in ALL_TARGETS if chosen[category(t)])


def patch_selected(body, target):
    if target not in ALL_TARGETS:
        raise ValueError('Resource is not an inspected configurable HUD target')
    patched = bytearray(hide_hud_except_downed(body, target))
    for _, offset in image_references(patched):
        if patched[offset:offset + 16] == OLD_IMAGE.bytes_le:
            patched[offset:offset + 16] = INVISIBLE_GUID.bytes_le
    # All original patchers explicitly load OLD_ID when using the hidden image.
    # Leave unrelated references/dependencies untouched, including the gauge.
    if any(patched[o:o+16] == INVISIBLE_GUID.bytes_le for _,o in image_references(patched)):
        slots = [(o,i) for o,i in dependencies(patched,target) if i == OLD_ID]
        if len(slots) != 1:
            raise ValueError('Missing transparent-image dependency')
        struct.pack_into('<Q',patched,slots[0][0],INVISIBLE_ID)
    return bytes(patched)


def describe_change(target):
    return {'category':category(target),'image_provider':PROVIDER_NAME,
            'shared_textures_modified':False}


def verify_invisible(archive, logical_name, codec):
    from forge_io import decode_payload
    checks = [('4x4_Invisible_MapDesc',1241263910630,TEXTURE_HASHES[logical_name])]
    if logical_name == 'DataPC_extra.forge':
        checks.append((PROVIDER_NAME,INVISIBLE_ID,PROVIDER_HASH))
    for name,file_id,expected in checks:
        entries=archive.find(name)
        if len(entries)!=1 or entries[0].file_id!=file_id:
            raise ValueError('Recurso transparente original ausente ou ambíguo.')
        payload=decode_payload(archive.read_raw(entries[0]),codec)
        if len(payload.sets)!=2 or hashlib.sha256(payload.sets[1].data).hexdigest()!=expected:
            raise ValueError('Versão desconhecida do recurso transparente original.')
