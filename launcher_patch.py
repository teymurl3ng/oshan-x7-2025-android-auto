"""Bounded BSDIFF40 reader for the pinned, locally reconstructed launcher.

Only the maintainer needs bsdiff to generate the patch. Applying it uses the
Python standard library on Windows, macOS and Linux. See docs/launcher.md.
"""
import bz2


class PatchError(ValueError):
    pass


def _integer(raw):
    if len(raw) != 8:
        raise PatchError("Truncated patch integer")
    value = int.from_bytes(raw, "little")
    return -(value & ((1 << 63) - 1)) if value >> 63 else value


def _unpack(raw, limit):
    try:
        decoder = bz2.BZ2Decompressor()
        result = decoder.decompress(raw, max_length=limit + 1)
        if len(result) > limit or not decoder.eof or decoder.unused_data:
            raise PatchError("Patch stream is oversized, truncated or has trailing data")
        return result
    except (OSError, EOFError) as exc:
        raise PatchError("Invalid compressed patch stream") from exc


def apply(old, patch, expected_size):
    """Return exactly expected_size bytes, or refuse malformed/unbounded input."""
    if not 0 < expected_size <= 32 * 1024 * 1024:
        raise PatchError("Unsupported output size")
    if len(patch) < 32 or patch[:8] != b"BSDIFF40":
        raise PatchError("Not a BSDIFF40 patch")
    control_size, diff_size, new_size = (_integer(patch[n:n + 8]) for n in (8, 16, 24))
    if (new_size != expected_size or min(control_size, diff_size) < 0 or
            control_size + diff_size > len(patch) - 32):
        raise PatchError("Invalid patch lengths")
    control_end = 32 + control_size
    diff_end = control_end + diff_size
    control = _unpack(patch[32:control_end], min(expected_size * 24, 64 * 1024 * 1024))
    diff = _unpack(patch[control_end:diff_end], expected_size)
    extra = _unpack(patch[diff_end:], expected_size)
    if len(control) % 24:
        raise PatchError("Truncated patch control triple")
    result = bytearray()
    old_pos = diff_pos = extra_pos = control_pos = 0
    while len(result) < new_size:
        if control_pos + 24 > len(control):
            raise PatchError("Missing patch control triple")
        x, y, seek = (_integer(control[n:n + 8])
                      for n in range(control_pos, control_pos + 24, 8))
        control_pos += 24
        if (min(x, y) < 0 or x + y > new_size - len(result) or
                x > len(diff) - diff_pos or y > len(extra) - extra_pos):
            raise PatchError("Patch copy exceeds the output or input stream")
        block = bytearray(diff[diff_pos:diff_pos + x])
        start, end = max(0, -old_pos), min(x, len(old) - old_pos)
        for i in range(start, end):
            block[i] = (block[i] + old[old_pos + i]) & 255
        result.extend(block)
        result.extend(extra[extra_pos:extra_pos + y])
        diff_pos += x
        extra_pos += y
        old_pos += x + seek
    if (control_pos, diff_pos, extra_pos) != (len(control), len(diff), len(extra)):
        raise PatchError("Unused patch instructions or data")
    return bytes(result)
