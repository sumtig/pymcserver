"""World storage, support rules and block-change syncing."""

from .constants import BUTTON_IDS, DOOR_BLOCK_IDS, FLOOR_ATTACHED_IDS, FLUID_BLOCK_IDS, LADDER_OFFSETS, NEIGHBOR_OFFSETS, NON_SOLID_IDS, PRESSURE_PLATE_IDS, SIDE_OFFSETS, WALL_ATTACHED_IDS
from .protocol import block_change_payload, send_block_change, send_packet
from .state import fluid_lock, fluid_queue, plate_positions, world_blocks

def schedule_fluid_update(x, y, z):
    with fluid_lock:
        fluid_queue.add((x, y, z))
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            fluid_queue.add((x + dx, y + dy, z + dz))


def get_world_block(x, y, z):
    if (x, y, z) in world_blocks:
        return world_blocks[(x, y, z)]
    if y == 45:
        return (2, 0)   # Grass Block
    elif 42 <= y <= 44:
        return (3, 0)   # Dirt
    elif 33 <= y <= 41:
        return (1, 0)   # Stone
    elif y == 32:
        return (7, 0)   # Bedrock
    return (0, 0)       # Air


def set_world_block(x, y, z, block_id, meta=0):
    old_id, _ = get_world_block(x, y, z)
    world_blocks[(x, y, z)] = (block_id, meta)
    if block_id in PRESSURE_PLATE_IDS:
        plate_positions.add((x, y, z))
    else:
        plate_positions.discard((x, y, z))
    send_block_change(x, y, z, block_id, meta)
    if old_id in FLUID_BLOCK_IDS or block_id in FLUID_BLOCK_IDS:
        schedule_fluid_update(x, y, z)


def is_solid(x, y, z):
    return get_world_block(x, y, z)[0] not in NON_SOLID_IDS


def attach_offset(block_id, meta):
    """Direction (from the block) of the block a torch/lever/button hangs on."""
    m = meta & 7
    if m in SIDE_OFFSETS:
        return SIDE_OFFSETS[m]
    if block_id == 69:
        return (0, 1, 0) if m in (0, 7) else (0, -1, 0)
    if block_id in BUTTON_IDS:
        return (0, 1, 0) if m == 0 else (0, -1, 0)
    return (0, -1, 0)


def is_supported(block_id, meta, x, y, z, placing=False):
    if block_id in FLOOR_ATTACHED_IDS:
        return is_solid(x, y - 1, z)
    if block_id in WALL_ATTACHED_IDS:
        dx, dy, dz = attach_offset(block_id, meta)
        return is_solid(x + dx, y + dy, z + dz)
    if block_id == 65:  # Ladder
        off = LADDER_OFFSETS.get(meta & 7)
        return off is not None and is_solid(x + off[0], y + off[1], z + off[2])
    if block_id in DOOR_BLOCK_IDS:
        if meta & 8:  # upper half
            return get_world_block(x, y - 1, z)[0] == block_id
        if not is_solid(x, y - 1, z):
            return False
        return placing or get_world_block(x, y + 1, z)[0] == block_id
    return True


def drop_unsupported(x, y, z):
    """After a block disappeared at (x,y,z), remove neighbours that lost their support."""
    queue = [(x, y, z)]
    while queue:
        cx, cy, cz = queue.pop()
        for dx, dy, dz in NEIGHBOR_OFFSETS:
            nx, ny, nz = cx + dx, cy + dy, cz + dz
            bid, meta = get_world_block(nx, ny, nz)
            if bid != 0 and not is_supported(bid, meta, nx, ny, nz):
                set_world_block(nx, ny, nz, 0, 0)
                queue.append((nx, ny, nz))


def resync_block(session, x, y, z):
    """Tell one client what is really at (x,y,z) (undoes its own client-side prediction)."""
    block_id, meta = get_world_block(x, y, z)
    send_packet(session.sock, "PLAY", 0x23, block_change_payload(x, y, z, block_id, meta))
