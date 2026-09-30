# SPDX-License-Identifier: GPL-2.0-or-later
"""V3: retain V2 scales and route hostile images to a valid transparent image.

The original shared circle/icon textures also serve friendly widgets. Only the
image-reference fields and one image-loading dependency in the exact hostile
allowlist change. The existing
Hostile_Detection image provider is retained and its dedicated texture is made
transparent by phoenix_texture_patch, including the patch archive override.
"""
import hashlib
import struct
from uuid import UUID

from phoenix_leaf_patch import TARGETS as LEAF_TARGETS, hide_visuals
from phoenix_texture_patch import TARGETS as TEXTURE_TARGETS, hide_texture
from phoenix_texture_patch import change_details as texture_details
from phoenix_visual import records

TARGETS = LEAF_TARGETS + TEXTURE_TARGETS
IMAGE_GUID = UUID("5632F537-4E3F-4CE2-A7FE-B05C3F2C3EF3")
PROVIDER_NAME = "UI_HUD_Mark_Detection_" + str(IMAGE_GUID).upper()
PROVIDER_ID = 1108634390485
PROVIDER_SHA256 = "0f628d75c2bbad090c1ffbf209c8a778bc6cf5d1578ae6bd82654b96b757fe62"
IMAGE_REFERENCE_CLASS = bytes.fromhex("0dec2c23")
# Exact reviewed replacement: original-body hash -> (native ID offset, old ID,
# old image GUID). After all image references are redirected, this dependency
# is unused and its slot can load the transparent image without growing a list.
# Hostile_Detection already declares PROVIDER_ID and needs no footer change.
DEPENDENCY_REPLACEMENTS = {
    "2b151913b887758d211496ca6f3dc3eef7b6a9fe4297ea79cec4d041359f3526": (5844, 1173723307358, "9B6467E6-B7FE-42BB-A807-DE616859454C"),
    "39cd8830e79d17d53e9b2b29ae6cedd2473530d5ffab60b8b568b2d0ed662022": (5769, 512489393509, "1BB11F58-9CCB-4EEB-BFA6-1E9A742DA6F7"),
    "46e69e0ba772fa45a7da417821aea8839376d2d673ee276f15c8f42f0b140168": (16570, 512489393509, "1BB11F58-9CCB-4EEB-BFA6-1E9A742DA6F7"),
    "d65227d94dcbe4f68c55c5d3bd114e91b11872f832fa7722d5cfdde66c189e73": (16847, 512489393509, "1BB11F58-9CCB-4EEB-BFA6-1E9A742DA6F7"),
    "418a2b78080d6cb50eec808779c26befd275e84823cae6729d083c1eb76b044c": (30763, 512489393509, "1BB11F58-9CCB-4EEB-BFA6-1E9A742DA6F7"),
    "97933cd7ba86ffb5a59e2e72fdac2626354e6465cafe94241f4f210a354df416": (9879, 522702430884, "CCD1F2AC-B680-44DE-B90A-C9D6549131F0"),
    "f1aed879e6bcfe33498f6b10a54a06df31c7ea8dbc48d610a419a4f078015690": (7068, 512489393509, "1BB11F58-9CCB-4EEB-BFA6-1E9A742DA6F7"),
    "a2b9e266e56c3e601b06b9034fe42372ea88c0868d65f6fb3bd217b950a2e3c3": (6008, 512489393511, "FB243B67-84F9-483E-9764-53B561D12D25"),
    "a650de62926b95d9491f0b5b4518dc7e46b7db52f0812a13eb8a91b4867a223a": None,
    "ce3f4744d2dd03afdf5af48b634c5a413466bac6ecefc30c8deb542aee124716": (17317, 512489393509, "1BB11F58-9CCB-4EEB-BFA6-1E9A742DA6F7"),
    "3ec8b7d0733d874c5df0890ce02985b620d8a0ba72b996a8f04d8acdc5ff4b75": (16476, 512489393509, "1BB11F58-9CCB-4EEB-BFA6-1E9A742DA6F7"),
    "eb29cef7af6b2629b9375fd4b0713ceca03a43016afe2c3b168f87bf89e26353": (14131, 512489393509, "1BB11F58-9CCB-4EEB-BFA6-1E9A742DA6F7"),
    "a60165db1eb045657552dc8552770b7e9a53508b70f50dc737c1de6d4713b0a4": (13664, 2512936217545, "27023842-9E6E-45A2-8293-71F9CF69D394"),
    "f22e5c45a1166f09949667452caa9bed25790b7f8683c63143eca2e0a2a75499": (21922, 512489393509, "1BB11F58-9CCB-4EEB-BFA6-1E9A742DA6F7"),
    "0c217ca01300eff8fee9c8a1bcd9d9d3ee79dff1dc38a08f11654f4e0bece081": (7085, 512489393511, "FB243B67-84F9-483E-9764-53B561D12D25"),
    "8ab6602d44c7bddfafbd78106e655f38e5cde6180bcd0e1d3658479651f6af5c": (6134, 512489393509, "1BB11F58-9CCB-4EEB-BFA6-1E9A742DA6F7"),
    "757af9a503c56f0f66e504eba9669db319ce48cc35302fc0019c7453adeefaa5": (16836, 512489393509, "1BB11F58-9CCB-4EEB-BFA6-1E9A742DA6F7"),
    "928ba7817d587080e7621e81381eb6e5ebe0ea73bffa2b8c51dac06d29ca5830": (17110, 512489393509, "1BB11F58-9CCB-4EEB-BFA6-1E9A742DA6F7"),
    "34839c82dcb65d064120b2cd10cd4f9ba44b85b123e2406641931fbe858be678": (14854, 512489393509, "1BB11F58-9CCB-4EEB-BFA6-1E9A742DA6F7"),
    "2878d58c6334ac72def5e34f2e285ddaa9c5325998014810985c7ad3b8ef33e7": (13797, 512489393511, "FB243B67-84F9-483E-9764-53B561D12D25"),
    "84d357a3b137c886285b38d218e92a688b6038c3eceaf58d287b2620eed5d7a1": None,
    "606898d2ff4e8cd79297826755fdb494a23b3d76d9703aeebd2aec8f380f00b4": (22360, 512489393509, "1BB11F58-9CCB-4EEB-BFA6-1E9A742DA6F7"),
    "420da8ed4800c628790194ec4e42e946945fca8bc2a15b87a33fc4fd37442c02": (22725, 512489393509, "1BB11F58-9CCB-4EEB-BFA6-1E9A742DA6F7"),
}


def dependencies(body, target):
    name = target.name.encode("ascii")
    phx = 12 + len(name) + 1 + 8 + 4 + 1 + 4
    phx_length = struct.unpack_from("<I", body, phx - 4)[0]
    footer = phx + phx_length
    guid_at = body.index(target.name[-36:].lower().encode("ascii"), footer)
    at = guid_at + 36
    if body[at:at + 2] != b"\0\x01":
        raise ValueError("Unexpected Phoenix dependency list header")
    count = struct.unpack_from("<I", body, at + 2)[0]
    at += 6
    result = []
    for _ in range(count):
        if body[at:at + 2] != b"\x01\x01" or at + 10 > len(body):
            raise ValueError("Unexpected Phoenix dependency record")
        result.append((at + 2, struct.unpack_from("<Q", body, at + 2)[0]))
        at += 10
    return result


def image_references(body):
    """Yield only the inspected image-reference fields, never object identities."""
    for node in records(body):
        if node["type"] != "dd999fc1":
            continue
        offset = node["fields_offset"] + 103
        if offset + 16 > len(body) or body[offset - 4:offset] != IMAGE_REFERENCE_CLASS:
            raise ValueError("Unexpected Phoenix image-reference layout")
        yield node, offset


def hide_enemy_visuals(body, target):
    if target in LEAF_TARGETS:
        # This performs the exact original-hash and hostile-allowlist checks,
        # preserving every V2 scale change that removed distances in gameplay.
        patched = bytearray(hide_visuals(body, target))
        for node, offset in image_references(body):
            patched[offset:offset + 16] = IMAGE_GUID.bytes_le
        dependency = DEPENDENCY_REPLACEMENTS[target.sha256]
        original_dependencies = dependencies(body, target)
        if dependency is not None:
            offset, old_id, old_guid = dependency
            if (offset, old_id) not in original_dependencies:
                raise ValueError("Inspected image-loading dependency missing")
            if UUID(old_guid).bytes_le not in body or UUID(old_guid).bytes_le in patched:
                raise ValueError("Old image dependency still referenced or not recognized")
            struct.pack_into("<Q", patched, offset, PROVIDER_ID)
        if sum(fid == PROVIDER_ID for _, fid in dependencies(patched, target)) != 1:
            raise ValueError("Transparent image must be declared exactly once")
        return bytes(patched)
    if target in TEXTURE_TARGETS:
        return hide_texture(body, target)
    raise ValueError("Target is not an inspected hostile V3 resource")


def change_details(target):
    if target in LEAF_TARGETS:
        dep = DEPENDENCY_REPLACEMENTS[target.sha256]
        return {"visual_instances": target.node_count, "scale_xy_to": [0.0, 0.0],
                "image_references_to": str(IMAGE_GUID).upper(),
                "image_dependency_change": None if dep is None else
                {"offset": dep[0], "from_file_id": dep[1], "to_file_id": PROVIDER_ID}}
    return texture_details(target)


def verify_image_provider(archive, codec):
    """Fail closed if the existing image provider differs or is missing."""
    from forge_io import decode_payload
    entries = archive.find(PROVIDER_NAME)
    if len(entries) != 1 or entries[0].file_id != PROVIDER_ID:
        raise ValueError("Hostile detection image provider missing or ambiguous")
    payload = decode_payload(archive.read_raw(entries[0]), codec)
    if len(payload.sets) != 2 or hashlib.sha256(payload.sets[1].data).hexdigest() != PROVIDER_SHA256:
        raise ValueError("Unsupported hostile detection image provider")
