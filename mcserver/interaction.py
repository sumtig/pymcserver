"""Right-click handling: activating blocks, placing blocks, slabs."""

import struct

from .constants import BUTTON_IDS, DOOR_BLOCK_IDS, DOUBLE_SLAB_OF, FENCE_GATE_IDS, ITEM_TO_BLOCK, REPLACEABLE_IDS, USABLE_BLOCK_IDS, WOODEN_DOOR_IDS
from .logs import log_msg
from .orientation import calculate_block_meta
from .protocol import decode_position
from .scheduler import schedule_ticks
from .world import get_world_block, is_supported, resync_block, set_world_block

def press_button(x, y, z):
    block_id, meta = get_world_block(x, y, z)
    if block_id not in BUTTON_IDS or meta & 8:
        return
    set_world_block(x, y, z, block_id, meta | 8)
    schedule_ticks(20 if block_id == 77 else 30, release_button, x, y, z)   # stone 1.0s, wood 1.5s


def release_button(x, y, z):
    block_id, meta = get_world_block(x, y, z)
    if block_id in BUTTON_IDS and meta & 8:
        set_world_block(x, y, z, block_id, meta & 7)


def activate_block(session, x, y, z):
    block_id, meta = get_world_block(x, y, z)

    if block_id in WOODEN_DOOR_IDS:
        if meta & 8:                                  # clicked the upper half; open state lives in the lower half
            y -= 1
            lower_id, meta = get_world_block(x, y, z)
            if lower_id != block_id:
                return
        set_world_block(x, y, z, block_id, meta ^ 4)
    elif block_id == 96 or block_id in FENCE_GATE_IDS:
        set_world_block(x, y, z, block_id, meta ^ 4)
    elif block_id == 69:                              # lever
        set_world_block(x, y, z, block_id, meta ^ 8)
    elif block_id in BUTTON_IDS:
        press_button(x, y, z)
    elif block_id in (93, 94):                        # repeater: cycle delay
        set_world_block(x, y, z, block_id, (meta & 3) | ((((meta >> 2) + 1) & 3) << 2))
    elif block_id in (149, 150):                      # comparator: toggle mode
        set_world_block(x, y, z, block_id, meta ^ 4)


def find_slab_merge(block_id, damage, face, clicked_pos, target_pos):
    """Position where placing this slab turns an existing slab into a double slab, or None."""
    variant = damage & 7
    cid, cmeta = get_world_block(*clicked_pos)
    # Top of a bottom slab, or underside of a top slab
    if cid == block_id and (cmeta & 7) == variant and (
            (face == 1 and not cmeta & 8) or (face == 0 and cmeta & 8)):
        return clicked_pos
    # Placing from the side (or anywhere) into a spot that already holds the same slab
    tid, tmeta = get_world_block(*target_pos)
    if tid == block_id and (tmeta & 7) == variant:
        return target_pos
    return None


def handle_block_placement(session, payload):
    if len(payload) < 14:
        return
    face = payload[8]
    if face not in (0, 1, 2, 3, 4, 5):   # 255 = "use item" in air
        return

    bx, by, bz = decode_position(struct.unpack('>q', payload[0:8])[0])
    item_id = struct.unpack('>h', payload[9:11])[0]
    holding = item_id > 0
    damage = struct.unpack('>h', payload[12:14])[0] if holding and len(payload) >= 17 else 0
    cursor_y = payload[-2]   # last 3 bytes are the cursor position (0-16)

    clicked_id, _ = get_world_block(bx, by, bz)
    log_msg(f"[DEBUG] {session.username} right-click at ({bx}, {by}, {bz}) face={face} "
            f"item={item_id} damage={damage} clicked={clicked_id} sneaking={session.sneaking}")

    # Clicking something usable consumes the click, exactly like vanilla:
    # it only places a block instead if the player sneaks while holding an item.
    if clicked_id in USABLE_BLOCK_IDS and (not session.sneaking or not holding):
        activate_block(session, bx, by, bz)
        return

    if not holding:
        return

    block_id = ITEM_TO_BLOCK.get(item_id, item_id if item_id <= 255 else None)
    if block_id is None or block_id == 0:
        return   # tools, food, etc. must never turn into blocks

    # Where does the block go?
    if clicked_id in REPLACEABLE_IDS:
        tx, ty, tz = bx, by, bz
    else:
        tx, ty, tz = bx, by, bz
        if face == 0: ty -= 1
        elif face == 1: ty += 1
        elif face == 2: tz -= 1
        elif face == 3: tz += 1
        elif face == 4: tx -= 1
        elif face == 5: tx += 1

    def reject(reason):
        log_msg(f"[WORLD] {session.username} placement of {block_id} at ({tx}, {ty}, {tz}) rejected: {reason}")
        resync_block(session, tx, ty, tz)
        if block_id in DOOR_BLOCK_IDS:
            resync_block(session, tx, ty + 1, tz)

    # Slab + same slab = double slab (clicking the matching face, or the target spot already holds that slab)
    if block_id in DOUBLE_SLAB_OF:
        merge_pos = find_slab_merge(block_id, damage, face, (bx, by, bz), (tx, ty, tz))
        if merge_pos:
            set_world_block(*merge_pos, DOUBLE_SLAB_OF[block_id], damage & 7)
            log_msg(f"[WORLD] {session.username} made a double slab at {merge_pos}")
            return

    if not (0 <= ty < 255):
        return reject("out of world")
    if get_world_block(tx, ty, tz)[0] not in REPLACEABLE_IDS:
        return reject("space occupied")

    meta = calculate_block_meta(block_id, damage, face, cursor_y, session)
    if meta is None:
        return reject("invalid face")
    if not is_supported(block_id, meta, tx, ty, tz, placing=True):
        return reject("no support")

    if block_id in DOOR_BLOCK_IDS:
        if get_world_block(tx, ty + 1, tz)[0] not in REPLACEABLE_IDS or ty + 1 >= 255:
            return reject("no room above")
        set_world_block(tx, ty, tz, block_id, meta)
        set_world_block(tx, ty + 1, tz, block_id, 8)
        log_msg(f"[WORLD] {session.username} placed door at ({tx}, {ty}, {tz})")
        return

    set_world_block(tx, ty, tz, block_id, meta)
    log_msg(f"[WORLD] {session.username} placed block ID {block_id} (meta {meta}) at ({tx}, {ty}, {tz})")
