"""Shared mutable server state (world, players, locks)."""

import threading

world_blocks = {}  # Map of (x, y, z) -> (block_id, meta)

plate_positions = set()

fluid_queue = set()

fluid_lock = threading.Lock()

clients = {}

clients_lock = threading.Lock()
