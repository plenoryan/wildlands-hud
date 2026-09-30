# SPDX-License-Identifier: GPL-2.0-or-later
"""V2: zero XY scale on the visuals inside inspected enemy-only resources.

Alpha inheritance did not work in the user's test. This version keeps all alpha
bindings and animations intact, and changes the local scale of actual image/text
instances as well as their nested marker instances. Runtime validation is pending.
"""
from dataclasses import dataclass
import hashlib
import struct

from phoenix_visual import records


@dataclass(frozen=True)
class LeafTarget:
    archive: str
    name: str
    node_count: int
    sha256: str


BASE = "DataPC_extra.forge"
PATCH = "DataPC_extra_patch_01.forge"
TARGETS = (
    LeafTarget(BASE, "DLC_HUD_Marker_HostilePMC_IconHolder_2746C34F-9745-4068-BBE9-599D2B9EB314", 12, "2b151913b887758d211496ca6f3dc3eef7b6a9fe4297ea79cec4d041359f3526"),
    LeafTarget(BASE, "DLC_HUD_Marker_HostileRebel_IconHolder_7E65DDFD-9D9E-419F-BF13-70D969F990AF", 12, "39cd8830e79d17d53e9b2b29ae6cedd2473530d5ffab60b8b568b2d0ed662022"),
    LeafTarget(BASE, "DLC_HUD_Marker_Hostile_PMC_DA907DE0-150F-4CF3-B935-289E80CD282C", 9, "46e69e0ba772fa45a7da417821aea8839376d2d673ee276f15c8f42f0b140168"),
    LeafTarget(BASE, "DLC_HUD_Marker_Hostile_Rebel_3A075E8C-D9D1-4263-A2CA-12C8FFA7B792", 9, "d65227d94dcbe4f68c55c5d3bd114e91b11872f832fa7722d5cfdde66c189e73"),
    LeafTarget(BASE, "HUD_Marker_HostileNPC_8D6BB8B6-26B5-4A04-A10A-D215593D70E4", 13, "418a2b78080d6cb50eec808779c26befd275e84823cae6729d083c1eb76b044c"),
    LeafTarget(BASE, "HUD_Marker_HostilePlayer_082CFE52-C4E4-4480-B82A-6F1DE9968D56", 10, "97933cd7ba86ffb5a59e2e72fdac2626354e6465cafe94241f4f210a354df416"),
    LeafTarget(BASE, "HUD_Marker_HostileSantaBlanca_IconHolder_7BF143FE-715E-49B1-9449-9D824523FD58", 15, "f1aed879e6bcfe33498f6b10a54a06df31c7ea8dbc48d610a419a4f078015690"),
    LeafTarget(BASE, "HUD_Marker_HostileUnidad_IconHolder_BEF2A27D-F8F8-4820-8823-3E0231F89205", 12, "a2b9e266e56c3e601b06b9034fe42372ea88c0868d65f6fb3bd217b950a2e3c3"),
    LeafTarget(BASE, "HUD_Marker_Hostile_Detection_04A33602-130E-4868-8B38-66DBC4896B07", 4, "a650de62926b95d9491f0b5b4518dc7e46b7db52f0812a13eb8a91b4867a223a"),
    LeafTarget(BASE, "HUD_Marker_Hostile_SantaBlanca_6D225ADC-FB70-417F-B20F-61D8248FAE1E", 7, "ce3f4744d2dd03afdf5af48b634c5a413466bac6ecefc30c8deb542aee124716"),
    LeafTarget(BASE, "HUD_Marker_Hostile_Unidad_DF04C8B4-4094-4598-83EE-DBE1B035993C", 7, "3ec8b7d0733d874c5df0890ce02985b620d8a0ba72b996a8f04d8acdc5ff4b75"),
    LeafTarget(BASE, "HUD_Marker_Hostile_White_D26113FF-9A46-44A2-BFE0-B6E1A89E7CB4", 11, "eb29cef7af6b2629b9375fd4b0713ceca03a43016afe2c3b168f87bf89e26353"),
    LeafTarget(PATCH, "DLC30_LAZ_HUD_Marker_HostilePenitentes_IconHolder_C627C5D3-AFDD-4EB9-8707-5C619C62D168", 12, "a60165db1eb045657552dc8552770b7e9a53508b70f50dc737c1de6d4713b0a4"),
    LeafTarget(PATCH, "DLC30_LAZ_HUD_Marker_Hostile_Penitentes_C593CB35-A42D-4ED8-B901-681B70F3F841", 8, "f22e5c45a1166f09949667452caa9bed25790b7f8683c63143eca2e0a2a75499"),
    LeafTarget(PATCH, "DLC_HUD_Marker_HostilePMC_IconHolder_2746C34F-9745-4068-BBE9-599D2B9EB314", 15, "0c217ca01300eff8fee9c8a1bcd9d9d3ee79dff1dc38a08f11654f4e0bece081"),
    LeafTarget(PATCH, "DLC_HUD_Marker_HostileRebel_IconHolder_7E65DDFD-9D9E-419F-BF13-70D969F990AF", 13, "8ab6602d44c7bddfafbd78106e655f38e5cde6180bcd0e1d3658479651f6af5c"),
    LeafTarget(PATCH, "DLC_HUD_Marker_Hostile_PMC_DA907DE0-150F-4CF3-B935-289E80CD282C", 9, "757af9a503c56f0f66e504eba9669db319ce48cc35302fc0019c7453adeefaa5"),
    LeafTarget(PATCH, "DLC_HUD_Marker_Hostile_Rebel_3A075E8C-D9D1-4263-A2CA-12C8FFA7B792", 9, "928ba7817d587080e7621e81381eb6e5ebe0ea73bffa2b8c51dac06d29ca5830"),
    LeafTarget(PATCH, "HUD_Marker_HostileSantaBlanca_IconHolder_7BF143FE-715E-49B1-9449-9D824523FD58", 15, "34839c82dcb65d064120b2cd10cd4f9ba44b85b123e2406641931fbe858be678"),
    LeafTarget(PATCH, "HUD_Marker_HostileUnidad_IconHolder_BEF2A27D-F8F8-4820-8823-3E0231F89205", 12, "2878d58c6334ac72def5e34f2e285ddaa9c5325998014810985c7ad3b8ef33e7"),
    LeafTarget(PATCH, "HUD_Marker_Hostile_Detection_04A33602-130E-4868-8B38-66DBC4896B07", 4, "84d357a3b137c886285b38d218e92a688b6038c3eceaf58d287b2620eed5d7a1"),
    LeafTarget(PATCH, "HUD_Marker_Hostile_SantaBlanca_6D225ADC-FB70-417F-B20F-61D8248FAE1E", 8, "606898d2ff4e8cd79297826755fdb494a23b3d76d9703aeebd2aec8f380f00b4"),
    LeafTarget(PATCH, "HUD_Marker_Hostile_Unidad_DF04C8B4-4094-4598-83EE-DBE1B035993C", 9, "420da8ed4800c628790194ec4e42e946945fca8bc2a15b87a33fc4fd37442c02"),
)


def hide_visuals(body, target):
    if target not in TARGETS:
        raise ValueError("Target is not an inspected hostile visual resource")
    if hashlib.sha256(body).hexdigest() != target.sha256:
        raise ValueError(f"Unsupported or already modified visual resource: {target.name}")
    name = target.name.encode("ascii")
    phoenix = 12 + len(name) + 1 + 8 + 4 + 1 + 4
    if (body[:4] != bytes.fromhex("83898ddb") or body[12:12 + len(name)] != name
            or body[phoenix:phoenix + 5] != b"PHXWI"):
        raise ValueError("Unexpected resource identity or Phoenix header")
    # No occurrences in these exact baseline bodies. Do not silently accept a
    # future version that may animate the scale property (runtime ID 0x35).
    if bytes.fromhex("35000080") in body:
        raise ValueError("Potential serialized scale path requires review")
    nodes = records(body)
    if len(nodes) != target.node_count:
        raise ValueError("Unexpected visual object count")
    patched = bytearray(body)
    for node in nodes:
        if node["scale"] not in ((1.0, 1.0, 1.0), (0.5, 0.5, 1.0)):
            raise ValueError("Unexpected local scale")
        # Only X/Y change. Z, alpha, animation data and identity remain intact.
        struct.pack_into("<2f", patched, node["scale_offset"], 0.0, 0.0)
    return bytes(patched)
