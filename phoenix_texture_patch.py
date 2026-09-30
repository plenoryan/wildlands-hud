# SPDX-License-Identifier: GPL-2.0-or-later
"""Hide only the inspected enemy detection disc texture, in base and patch.

The Forge caller retains set 0 and all archive metadata. This module replaces
only BC7 pixels inside set 1; it never reads or writes a game file.
"""
from dataclasses import dataclass
import hashlib
import struct


@dataclass(frozen=True)
class TextureTarget:
    archive: str
    name: str
    sha256: str


TARGETS = (
    TextureTarget("DataPC_extra.forge", "UI_HUD_Mark_Detection_MapDesc",
                  "671cbf0c39a0df9f1d8e34b68c54749c04c380bfb50fca324fd8dd15d2b82374"),
    TextureTarget("DataPC_extra_patch_01.forge", "UI_HUD_Mark_Detection_MapDesc",
                  "d575572642115c85cd40bcd362a3910fa3e27ef41a4b24e84d7c02b767e8c935"),
)

BODY_LENGTH = 16841
PIXEL_OFFSET = 0x1C9
PIXEL_LENGTH = 16384
CTM_OFFSET = 0x191
TRANSPARENT_BC7_BLOCK = b"\x40" + b"\0" * 15


def _authorize(target):
    if type(target) is not TextureTarget or target not in TARGETS:
        raise ValueError("Texture target is not one of the two inspected enemy detection copies")


def _validate_record(body, offset, end, expected_class, expected_id, expected_name, expected_body_size):
    if offset < 0 or end > len(body) or offset + 12 > end:
        raise ValueError("Texture resource record exceeds inspected bounds")
    resource_class, body_size, name_length = struct.unpack_from("<III", body, offset)
    name = expected_name.encode("ascii")
    if (resource_class, body_size, name_length) != (expected_class, expected_body_size, len(name)):
        raise ValueError("Unexpected texture resource header")
    body_start = end - body_size
    if body_start != offset + 12 + len(name) + 1:
        raise ValueError("Unexpected texture resource layout")
    if body[offset + 12:body_start] != name + b"\0":
        raise ValueError("Unexpected texture resource identity")
    file_id, inner_class = struct.unpack_from("<QI", body, body_start)
    if (file_id, inner_class) != (expected_id, expected_class):
        raise ValueError("Texture resource ID or class mismatch")
    return body_start


def hide_texture(body: bytes, target: TextureTarget) -> bytes:
    """Replace the complete BC7 mip with valid transparent mode-6 blocks.

    Exact original hashes deliberately reject other versions, unrelated
    textures, prior edits, and a second application. Caller receives new bytes.
    """
    _authorize(target)
    if not isinstance(body, (bytes, bytearray, memoryview)):
        raise ValueError("Texture body must be bytes")
    body = bytes(body)
    if len(body) != BODY_LENGTH or hashlib.sha256(body).hexdigest() != target.sha256:
        raise ValueError(f"Unsupported or already modified detection texture: {target.archive}")
    _validate_record(body, 0, 295, 0x989DC6B2, 0x1021FC22466,
                     "UI_HUD_Mark_Detection_MapDesc", 253)
    texture_body = _validate_record(body, 295, BODY_LENGTH, 0xA2B7E917, 0x1021FC22465,
                                    "UI_HUD_Mark_Detection_Map", 16508)
    if texture_body + 68 != CTM_OFFSET:
        raise ValueError("Unexpected CompiledTextureMap position")
    # Outer TextureMap fields: flag, width, height, depth, format, array size.
    if body[texture_body + 12] != 1 or struct.unpack_from("<5I", body, texture_body + 13) != (128, 128, 1, 9, 1):
        raise ValueError("Unexpected outer texture dimensions or format")
    expected_ctm = (0x13237FE9, 1, 7, 128, 128, 1, 1, 9, 1, 0, 0, 0, 0, PIXEL_LENGTH)
    if struct.unpack_from("<14I", body, CTM_OFFSET) != expected_ctm:
        raise ValueError("Unexpected compiled texture header or mip layout")
    if PIXEL_OFFSET != CTM_OFFSET + 56 or PIXEL_OFFSET + PIXEL_LENGTH != len(body):
        raise ValueError("Unexpected texture pixel span")
    if PIXEL_LENGTH != ((128 + 3) // 4) ** 2 * 16:
        raise ValueError("Unexpected BC7 block count")
    # 0x40 selects valid BC7 mode 6. Zero endpoints/P bits/indices give RGBA=0.
    # An all-zero 16-byte block would select a reserved BC7 mode instead.
    pixels = TRANSPARENT_BC7_BLOCK * (PIXEL_LENGTH // 16)
    return body[:PIXEL_OFFSET] + pixels + body[PIXEL_OFFSET + PIXEL_LENGTH:]


def change_details(target: TextureTarget) -> dict:
    """Describe the exact intended mutation for the prepared package manifest."""
    _authorize(target)
    return {"kind": "texture_pixels", "name": target.name,
            "texture_resource": "UI_HUD_Mark_Detection_Map", "texture_file_id": 0x1021FC22465,
            "original_set1_sha256": target.sha256, "format": "BC7", "format_code": 9,
            "width": 128, "height": 128, "mip_count": 1,
            "pixel_offset": PIXEL_OFFSET, "pixel_length": PIXEL_LENGTH,
            "replacement_block_hex": TRANSPARENT_BC7_BLOCK.hex(), "decoded_rgba": [0, 0, 0, 0]}
