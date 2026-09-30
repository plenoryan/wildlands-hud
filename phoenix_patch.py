# SPDX-License-Identifier: GPL-2.0-or-later
"""Conservative experimental Phoenix edit, restricted to nine inspected templates.

The alpha field's meaning is inferred from the repeated RGB/alpha layout, not
from a published PHXWI specification. In-game confirmation is still required.
Never apply offsets to unrecognised versions, arbitrary widgets, or ally assets.
"""
import hashlib
import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    archive: str
    name: str
    sha256: str
    alpha_offset: int
    child: str


TARGETS = (
    Target("DataPC_extra.forge", "DLC_HUD_Marker_Hostile_PMC_Container_533050F2-72DE-4788-AB2B-55879158CF3C", "b49fee49dd1bcb782dc3331d2aa2e2ac3026caa9cce11d2e0c37cf046be905a9", 0x240, "DLC_HUD_Marker_Hostile_PMC"),
    Target("DataPC_extra.forge", "DLC_HUD_Marker_Hostile_Rebel_Container_F7544F6C-B771-4A9D-8816-1A0E1702A5BA", "29f168b6f1a20ace295e66a2067f952e13945bbbbb5c1f944116ed8dbddfa526", 0x246, "DLC_HUD_Marker_Hostile_Rebel"),
    Target("DataPC_extra.forge", "HUD_Marker_HostileNPC_Container_46328289-79C3-4B70-967F-B37D4B8FFE63", "25dd9e11ad2139248a0a82ca716cd691219f6276a3f2a098f1ce0c09b8640e60", 0x231, "HUD_Marker_HostileNPC"),
    Target("DataPC_extra.forge", "HUD_Marker_HostilePlayer_Container_62EBE99E-B4AD-4C63-829A-1BC0793B0508", "129c7d820148c940d1661fc51e78e23a2eeabf68ba8dabc5a189d5d2419d940f", 0x23e, "HUD_Marker_HostilePlayer"),
    Target("DataPC_extra.forge", "HUD_Marker_Hostile_Detection_Container_6994F53A-C71A-4F20-9CC2-0E3A15BE17E2", "79b4e9c64a485c5a377a8a08bf1fdae652ca495cb0186b4bae388cb8cd36ee06", 0x246, "HUD_Marker_Hostile_Detection"),
    Target("DataPC_extra.forge", "HUD_Marker_Hostile_SantaBlanca_Container_ACA6C5AA-2946-4E94-A28E-5536313520CC", "934eb293ec315af3331839e0d4cafe269bfe25f266ccdf19c862ddac0e6d25c4", 0x24c, "HUD_Marker_Hostile_SantaBlanca"),
    Target("DataPC_extra.forge", "HUD_Marker_Hostile_Unidad_Container_88186DFF-0CD7-48D6-9F38-611F7274E0AD", "0c8cfda9ea09334b3cdf99e042120bd09bdb95178dbb5cafc9a3ac65c03e7793", 0x23d, "HUD_Marker_Hostile_Unidad"),
    Target("DataPC_extra.forge", "HUD_Marker_Hostile_White_Container_D186076D-01AA-4358-8DF0-C3451FF6B2E5", "1451d191adc1a71782c93325923ee804a97957f137b99313e368652696348d93", 0x23a, "HUD_Marker_Hostile_White"),
    Target("DataPC_extra_patch_01.forge", "DLC30_LAZ_HUD_Marker_Hostile_Penitentes_Container_7311063D-2B27-4860-AEA4-6DBAEA4088AE", "39ca380d1f93ad29b0060ee9b67f03f0d5a4e2fb12e4ab69645ac2a29adee276", 0x267, "DLC30_LAZ_HUD_Marker_Hostile_Penitentes"),
)


def hide_container(body: bytes, target: Target) -> bytes:
    """Change only the inspected 4-byte value; all structure stays byte-identical."""
    if target not in TARGETS:
        raise ValueError("Target is not one of the inspected hostile templates")
    if hashlib.sha256(body).hexdigest() != target.sha256:
        raise ValueError(f"Unsupported or already modified Phoenix asset: {target.name}")
    name = target.name.encode("ascii")
    if body[:4] != bytes.fromhex("83 89 8d db") or body[12:12 + len(name)] != name:
        raise ValueError("Unexpected resource header")
    phoenix = 12 + len(name) + 1 + 8 + 4 + 1 + 4
    if body[phoenix:phoenix + 5] != b"PHXWI":
        raise ValueError("Resource is not the inspected Phoenix widget format")
    prefix = bytes.fromhex("33 13 56 0f 1f fb ff ca 3e")
    child = target.child.encode("ascii")
    record = prefix + bytes([len(child), 1]) + child
    if body.count(record) != 1:
        raise ValueError("Expected exactly one inner widget instance")
    fields = body.index(record) + len(record)
    if fields + 77 != target.alpha_offset:
        raise ValueError("Unexpected widget property layout")
    if struct.unpack_from("<4f", body, fields + 65) != (255.0, 255.0, 255.0, 1.0):
        raise ValueError("Unexpected RGB/alpha tuple")
    return body[:target.alpha_offset] + b"\0" * 4 + body[target.alpha_offset + 4:]
