"""Facing / metadata calculation for placed blocks."""

from .constants import BUTTON_IDS, DOOR_BLOCK_IDS, FACING_PLAYER_IDS, FACING_TOWARD_PLAYER, FLUID_BLOCK_IDS, LOG_IDS, PRESSURE_PLATE_IDS, SIDE_FACE_TO_ATTACH_META, SLAB_IDS, STAIR_IDS, STAIR_META, TORCH_IDS, TRAPDOOR_FLOOR_META, TRAPDOOR_IDS

def look_index(yaw):
    """0 = looking South, 1 = West, 2 = North, 3 = East."""
    return int(((yaw % 360) + 45) // 90) % 4


def get_piston_facing(session):
    if session.pitch > 45.0:
        return 1  # Looking down -> faces up
    elif session.pitch < -45.0:
        return 0  # Looking up -> faces down
    return FACING_TOWARD_PLAYER[look_index(session.yaw)]


def calculate_block_meta(block_id, damage, face, cursor_y, session):
    """Metadata for a block about to be placed. Returns None if it can't be placed this way."""
    look = look_index(session.yaw)
    top_half = (face == 0) or (face > 1 and cursor_y > 8)

    if block_id in (29, 33):                       # pistons
        return get_piston_facing(session)
    if block_id in BUTTON_IDS:
        return 0 if face == 0 else (5 if face == 1 else SIDE_FACE_TO_ATTACH_META[face])
    if block_id == 69:                             # lever
        if face == 1:
            return 6 if look in (1, 3) else 5
        if face == 0:
            return 0 if look in (1, 3) else 7
        return SIDE_FACE_TO_ATTACH_META[face]
    if block_id in TORCH_IDS:
        if face == 0:
            return None
        return 5 if face == 1 else SIDE_FACE_TO_ATTACH_META[face]
    if block_id == 65:                             # ladder
        return face if face >= 2 else None
    if block_id in TRAPDOOR_IDS:
        if face >= 2:
            meta = {2: 0, 3: 1, 4: 2, 5: 3}[face]
            return meta | (8 if cursor_y > 8 else 0)
        # Face 0 = bottom face of block (ceiling trapdoor -> top half, meta | 8)
        # Face 1 = top face of block (floor trapdoor -> bottom half, meta | 0)
        return TRAPDOOR_FLOOR_META[look] | (8 if face == 0 else 0)
    if block_id in DOOR_BLOCK_IDS:
        return (look + 1) % 4
    if block_id in (93, 149):                      # repeater / comparator
        return (look + 2) % 4
    if block_id in STAIR_IDS:
        return STAIR_META[look] | (4 if top_half else 0)
    if block_id in SLAB_IDS:
        return (damage & 7) | (8 if top_half else 0)
    if block_id in LOG_IDS:
        axis = 0 if face < 2 else (8 if face in (2, 3) else 4)
        return (damage & 3) | axis
    if block_id in FACING_PLAYER_IDS:
        return FACING_TOWARD_PLAYER[look]
    if block_id in FLUID_BLOCK_IDS or block_id in PRESSURE_PLATE_IDS or block_id in (55, 152):
        return 0
    return damage & 15                             # wool colour, planks type, ...
