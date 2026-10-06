"""Pressure plates and the main tick loop."""

import time

from .constants import PRESSURE_PLATE_IDS
from .logs import log_msg
from .scheduler import process_scheduled
from .state import clients, clients_lock, plate_positions
from .world import get_world_block, set_world_block

plate_last_seen = {}


def tick_pressure_plates():
    if not plate_positions:
        return
    with clients_lock:
        players = [(s.x, s.y, s.z) for s in clients.values() if s.state == 3 and s.is_alive]
    now = time.time()

    for pos in list(plate_positions):
        x, y, z = pos
        block_id, meta = get_world_block(x, y, z)
        if block_id not in PRESSURE_PLATE_IDS:
            plate_positions.discard(pos)
            continue

        count = sum(
            1 for px, py, pz in players
            if x - 0.175 < px < x + 1.175 and z - 0.175 < pz < z + 1.175
            and py < y + 0.25 and py + 1.8 > y
        )

        if block_id in (70, 72):
            power = 1 if count else 0
        elif block_id == 147:
            power = min(count, 15)
        else:
            power = min(15, (count + 9) // 10)

        if power:
            plate_last_seen[pos] = now
        elif meta != 0 and now - plate_last_seen.get(pos, 0) < 0.5:
            continue   # short release delay, like vanilla

        if power != meta:
            set_world_block(x, y, z, block_id, power)


def run_tick_loop():
    while True:
        time.sleep(0.05)
        process_scheduled()
        try:
            tick_pressure_plates()
        except Exception as e:
            log_msg(f"[ERROR] Pressure plate tick failed: {e}")
