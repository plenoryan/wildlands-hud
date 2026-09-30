# SPDX-License-Identifier: GPL-2.0-or-later
"""V4: hide normal ally visuals while leaving the downed-player gauge intact.

The user explicitly extended V3's scope to ordinary ally markers. FriendlyPlayer
keeps its nested FriendlyGauge instance, dependency and animations byte-identical.
Its two off-screen arrows are gated to the existing ReviveState AND IsOOS flags.
FriendlyGauge and its image textures are not patch targets.
"""
from dataclasses import dataclass
import hashlib
import struct
from uuid import UUID

from phoenix_image_patch import (TARGETS as ENEMY_TARGETS, IMAGE_GUID, PROVIDER_ID,
                                 dependencies, image_references, hide_enemy_visuals,
                                 change_details as enemy_details)
from phoenix_visual import records


@dataclass(frozen=True)
class FriendlyTarget:
    archive: str
    name: str
    sha256: str
    dependency_offset: int
    player: bool


BASE = "DataPC_extra.forge"
PATCH = "DataPC_extra_patch_01.forge"
NPC = "HUD_Marker_FriendlyNPC_43B96827-DAC5-42A0-BF4F-C7FAF244D87B"
PLAYER = "HUD_Marker_FriendlyPlayer_852A9DC7-A238-4865-9465-444763C20472"
FRIENDLY_TARGETS = (
    FriendlyTarget(BASE, NPC, "dd1cf09bcd2239a499bdb7e9fb4c2422959ed66773e8d1a93ecaa5ae5ffce1a9", 5822, False),
    FriendlyTarget(BASE, PLAYER, "0285eae88e9822ae035b0abe98781481435a08effe3221b33b5603f72ef63a87", 17562, True),
    FriendlyTarget(PATCH, NPC, "31fce03ba2fc7ed71977459eaa306e23932e1deb850c9a9c4e05a4a4273219d4", 8175, False),
    FriendlyTarget(PATCH, PLAYER, "1a76b572b2786f272f9be57cf5d22c7168cb13774db4d73965e872deffa56f45", 17947, True),
)
TARGETS = ENEMY_TARGETS + FRIENDLY_TARGETS
GAUGE_NAME = "HUD_Marker_FriendlyGauge"
GAUGE_GUID = UUID("8C9AF11A-5C44-48EA-94AA-6E68C48AF2F8")
GAUGE_HASHES = {
    BASE: "c1d93e6eab033c5d28a2bc3432d2bcd279e4727dc88fcb72ddd034791bac6d86",
    PATCH: "79b58c95e8cb475035f3a9228bad99af13d1590e4b56e304793d1fee400ea035",
}
NPC_NAMES = frozenset(("MarkAdd_Occluded", "UI_HUD_MarkIcon", "MarkAdd", "distance",
                       "distance_Add", "objective", "objective_Add"))
PLAYER_NAMES = frozenset(("UI_Icons_Tools_Drone_DiffuseMapDesc", "UI_Icons_Tools_Drone_Simple",
                          "UI_HUD_FGT_ActiveArrow", "UI_HUD_FGT_ActiveArrow_01",
                          "UI_HUD_FGT_ActiveArrow_Simple", "playerName", "playerNameAdd",
                          "distance", "Distance_Ad"))
OOS_NAMES = frozenset(("UI_HUD_FGT_ADV_OOS_Arrow", "UI_HUD_FGT_ADV_OOS_Arrow_Simple"))
OOS_EDITS = {
    BASE: ((0x2634, 0x1AC6E8EE, 0x156E429E), (0x265E, 0x1DB4EC9A, 0x1C63E672),
           (0x2923, 0x1C63E672, 0x1C1F21A1)),
    PATCH: ((0x268C, 0x1AC6E8EE, 0x156E429E), (0x26B6, 0x1DB4EC9A, 0x1C63E672),
            (0x297B, 0x1C63E672, 0x1C1F21A1)),
}


def hide_normal_allies(body, target):
    if type(target) is not FriendlyTarget or target not in FRIENDLY_TARGETS:
        raise ValueError("Target is not an inspected normal-ally resource")
    if hashlib.sha256(body).hexdigest() != target.sha256:
        raise ValueError("Unsupported or already modified ally resource")
    name = target.name.encode("ascii")
    phx = 12 + len(name) + 1 + 8 + 4 + 1 + 4
    if body[:4] != bytes.fromhex("83898ddb") or body[12:12 + len(name)] != name or body[phx:phx + 5] != b"PHXWI":
        raise ValueError("Unexpected ally Phoenix resource identity")
    nodes = records(body)
    names = PLAYER_NAMES if target.player else NPC_NAMES
    expected = names | {GAUGE_NAME} | OOS_NAMES if target.player else names
    if len(nodes) != len(expected) or {n["name"] for n in nodes} != expected:
        raise ValueError("Unexpected normal-ally visual objects")
    patched = bytearray(body)
    for node in nodes:
        if node["name"] == GAUGE_NAME:
            offset = node["fields_offset"] + 103
            if node["type"] != "3313560f" or body[offset:offset + 16] != GAUGE_GUID.bytes_le:
                raise ValueError("Downed-ally gauge reference differs")
            continue
        if node["name"] in OOS_NAMES:
            continue
        if node["type"] not in ("dd999fc1", "e504a441") or node["scale"] != (1.0, 1.0, 1.0):
            raise ValueError("Unexpected normal-ally visual layout")
        struct.pack_into("<2f", patched, node["scale_offset"], 0.0, 0.0)
    for node, offset in image_references(body):
        if node["name"] in OOS_NAMES:
            continue
        if node["name"] not in names:
            raise ValueError("Unexpected image in preserved ally branch")
        patched[offset:offset + 16] = IMAGE_GUID.bytes_le
    # Replace one now-unused image dependency; do not touch the nested gauge's
    # dependency. It retains its own original heal/arrow image dependencies.
    old_id = 656128706380 if target.player else 512489393509
    old_guid = UUID("4EF64BA4-8B3F-417D-B72F-352B16414751" if target.player else
                    "1BB11F58-9CCB-4EEB-BFA6-1E9A742DA6F7").bytes_le
    if (target.dependency_offset, old_id) not in dependencies(body, target):
        raise ValueError("Inspected ally image dependency missing")
    if old_guid not in body or old_guid in patched:
        raise ValueError("Replaced ally image dependency is still in use")
    struct.pack_into("<Q", patched, target.dependency_offset, PROVIDER_ID)
    if target.player:
        # Repurpose NotFocused = InvertFocus AND IsInsight as the downed/OOS
        # conjunction, then use it as the primary off-screen arrow's visibility.
        # Its other consumers require Default/Active (mutually exclusive with
        # Revive), so they cannot start ActiveUnfocused and suppress the gauge.
        # The simple arrow still copies the primary arrow, including rotation.
        for offset, before, after in OOS_EDITS[target.archive]:
            if struct.unpack_from("<I", body, offset)[0] != before:
                raise ValueError("Unexpected downed-arrow boolean input")
            struct.pack_into("<I", patched, offset, after)
    return bytes(patched)


def hide_markers_except_downed(body, target):
    if target in FRIENDLY_TARGETS:
        return hide_normal_allies(body, target)
    return hide_enemy_visuals(body, target)


def verify_downed_gauge(archive, logical_name, codec):
    from forge_io import decode_payload
    entries = archive.find(GAUGE_NAME + "_" + str(GAUGE_GUID).upper())
    if len(entries) != 1:
        raise ValueError("Marcador de aliado caido ausente ou ambiguo.")
    data = decode_payload(archive.read_raw(entries[0]), codec)
    if len(data.sets) != 2 or hashlib.sha256(data.sets[1].data).hexdigest() != GAUGE_HASHES[logical_name]:
        raise ValueError("Versao desconhecida do marcador de aliado caido; alteracao cancelada.")


def change_details(target):
    if target in FRIENDLY_TARGETS:
        return {"kind": "normal_ally_visuals", "hidden_visual_instances": 9 if target.player else 7,
                "hidden_image_instances": 5 if target.player else 3, "hidden_text_instances": 4,
                "scale_xy_to": [0.0, 0.0], "image_references_to": str(IMAGE_GUID).upper(),
                "dependency_offset": target.dependency_offset, "dependency_to_file_id": PROVIDER_ID,
                "preserved_nested_widget": GAUGE_NAME if target.player else None,
                "offscreen_arrow_condition": "ReviveState AND IsOOS" if target.player else None,
                "boolean_property_edits": list(OOS_EDITS[target.archive]) if target.player else []}
    return enemy_details(target)
