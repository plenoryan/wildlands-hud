# SPDX-License-Identifier: GPL-2.0-or-later
"""V5 experimental full HUD suppression, retaining V4's downed-ally chain.

Only explicitly inventoried HUD resources are accepted. No global image, font,
menu, binding, animation or widget identity is erased. Image references use V3's
transparent provider; text and non-protected child instances get zero XY scale.
Native/runtime-generated visuals still require an in-game acceptance test.
V5.1 also retains contextual interaction prompts and control hints, including
their ancestor instances, so action text and keyboard/controller icons remain.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import struct

from phoenix_full_hud_targets import ROWS
from phoenix_friendly_patch import TARGETS as V4_TARGETS, hide_markers_except_downed
from phoenix_friendly_patch import change_details as v4_details
from phoenix_image_patch import IMAGE_GUID, PROVIDER_ID, image_references
from phoenix_visual import records


@dataclass(frozen=True)
class HudTarget:
    archive: str
    name: str
    sha256: str
    node_count: int
    hide_guids: tuple
    dependency: tuple | None


HUD_TARGETS = tuple(HudTarget(*row) for row in ROWS)
TARGETS = V4_TARGETS + HUD_TARGETS


def dependencies(body, target):
    """Read inspected PHXWI/PHXSC footer variants without changing their size."""
    phx = 12 + len(target.name) + 18
    if body[phx:phx + 5] not in (b'PHXWI', b'PHXSC'):
        raise ValueError('Unexpected Phoenix HUD header')
    footer = phx + struct.unpack_from('<I', body, phx - 4)[0]
    at = body.index(target.name[-36:].lower().encode('ascii'), footer) + 36
    if body[at:at + 2] not in (b'\0\0', b'\0\1'):
        raise ValueError('Unexpected HUD dependency header')
    count = struct.unpack_from('<I', body, at + 2)[0]
    at += 6
    result = []
    for _ in range(count):
        if body[at:at + 2] != b'\1\1':
            raise ValueError('Unexpected HUD dependency entry')
        result.append((at + 2, struct.unpack_from('<Q', body, at + 2)[0]))
        at += 10
    return result


def hide_hud_except_downed(body, target):
    if target in V4_TARGETS:
        return hide_markers_except_downed(body, target)
    if type(target) is not HudTarget or target not in HUD_TARGETS:
        raise ValueError('Target is not an inspected V5 HUD resource')
    if hashlib.sha256(body).hexdigest() != target.sha256:
        raise ValueError('Unsupported or already modified HUD resource')
    nodes = records(body)
    selected = set(target.hide_guids)
    if len(nodes) != target.node_count or not selected <= {n['guid'] for n in nodes}:
        raise ValueError('Unexpected HUD visual objects')
    patched = bytearray(body)
    for node in nodes:
        if node['guid'] in selected:
            struct.pack_into('<2f', patched, node['scale_offset'], 0.0, 0.0)
    images = list(image_references(body))
    for node, offset in images:
        if node['guid'] not in selected:
            raise ValueError('Protected image would lose its dependency')
        patched[offset:offset + 16] = IMAGE_GUID.bytes_le
    if images:
        original = dependencies(body, target)
        if target.dependency is not None:
            if target.dependency not in original:
                raise ValueError('Expected HUD image dependency missing')
            struct.pack_into('<Q', patched, target.dependency[0], PROVIDER_ID)
        if sum(fid == PROVIDER_ID for _, fid in dependencies(patched, target)) != 1:
            raise ValueError('Transparent provider must be declared once')
    return bytes(patched)


def change_details(target):
    if target in V4_TARGETS:
        return v4_details(target)
    return {'visual_instances_hidden': len(target.hide_guids),
            'visual_instances_preserved': target.node_count - len(target.hide_guids),
            'scale_xy_to': [0.0, 0.0], 'image_references_to': str(IMAGE_GUID),
            'image_dependency_change': target.dependency}
