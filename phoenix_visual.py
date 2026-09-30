# SPDX-License-Identifier: GPL-2.0-or-later
"""Inspect only the three Phoenix visual record layouts confirmed in this installation."""
import re
import struct

VISUAL = re.compile(
    rb"\x02\x02(?P<guid>.{16})(?P<type>"
    rb"\xdd\x99\x9f\xc1\x24\xfb\xff\xca\x3f\xc0|"
    rb"\xe5\x04\xa4\x41\x2c\xfb\xff\xca\x3f\xff\xf0|"
    rb"\x33\x13\x56\x0f\x1f\xfb\xff\xca\x3e)"
    rb"(?P<length>.)\x01", re.S)


def records(body):
    result = []
    for match in VISUAL.finditer(body):
        name_start = match.end()
        end = name_start + match["length"][0]
        if end + 94 > len(body):
            raise ValueError("Truncated visual record")
        name = body[name_start:end].decode("ascii")
        if not name or not all(32 <= ord(c) < 127 for c in name):
            raise ValueError("Unexpected instance name")
        result.append({"name": name, "guid": match["guid"].hex(),
                       "type": match["type"][:4].hex(), "fields_offset": end,
                       "scale_offset": end + 28,
                       "scale": struct.unpack_from("<3f", body, end + 28),
                       "alpha": struct.unpack_from("<f", body, end + 77)[0]})
    return result

