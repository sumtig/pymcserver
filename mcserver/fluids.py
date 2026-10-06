"""Water and lava simulation."""

import time

from .constants import FLUID_BLOCK_IDS
from .state import fluid_lock, fluid_queue
from .world import get_world_block, set_world_block

def update_fluid_block(x, y, z):
    block_id, meta = get_world_block(x, y, z)

    if block_id not in FLUID_BLOCK_IDS:
        return

    is_water = block_id in (8, 9)
    fluid_id = 8 if is_water else 10
    max_dist = 7 if is_water else 3
    is_source = (meta == 0)

    # 1. Flow Downward
    below_id, _ = get_world_block(x, y - 1, z)
    if below_id == 0 and y > 0:
        set_world_block(x, y - 1, z, fluid_id, 8)
        return

    # 2. Check source connectivity for non-source flowing blocks
    if not is_source:
        above_id, _ = get_world_block(x, y + 1, z)
        has_source_above = (above_id in (8, 9) if is_water else above_id in (10, 11))

        if not has_source_above:
            min_neighbor_level = 99
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nid, nmeta = get_world_block(x + dx, y, z + dz)
                if (is_water and nid in (8, 9)) or (not is_water and nid in (10, 11)):
                    nlevel = 0 if nmeta == 8 else (nmeta & 0x07)
                    if nlevel < min_neighbor_level:
                        min_neighbor_level = nlevel

            if min_neighbor_level >= max_dist:
                set_world_block(x, y, z, 0, 0)
                return
            elif (min_neighbor_level + 1) != (meta & 0x07):
                set_world_block(x, y, z, fluid_id, min_neighbor_level + 1)

    # 3. Horizontal Spreading across solid ground
    if below_id != 0 and below_id not in FLUID_BLOCK_IDS:
        curr_level = 0 if is_source or meta == 8 else (meta & 0x07)
        if curr_level < max_dist:
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, nz = x + dx, z + dz
                nid, _ = get_world_block(nx, y, nz)
                if nid == 0:
                    set_world_block(nx, y, nz, fluid_id, curr_level + 1)


def run_fluid_physics():
    tick_counter = 0
    while True:
        time.sleep(0.05)  # 1 Tick = 50ms (20 ticks/sec)
        tick_counter += 1

        process_water = (tick_counter % 5 == 0)   # 4 steps / sec
        process_lava = (tick_counter % 30 == 0)   # 1 step / 1.5 sec

        if not process_water and not process_lava:
            continue

        water_targets = []
        lava_targets = []

        with fluid_lock:
            if not fluid_queue:
                continue

            to_remove = set()
            for pos in list(fluid_queue):
                bid, _ = get_world_block(*pos)
                if bid in (8, 9):
                    if process_water:
                        water_targets.append(pos)
                        to_remove.add(pos)
                elif bid in (10, 11):
                    if process_lava:
                        lava_targets.append(pos)
                        to_remove.add(pos)
                else:
                    to_remove.add(pos)

            fluid_queue.difference_update(to_remove)

        if process_water:
            for pos in water_targets:
                update_fluid_block(*pos)

        if process_lava:
            for pos in lava_targets:
                update_fluid_block(*pos)
