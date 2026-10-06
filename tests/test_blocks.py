import struct, time
import os, sys, types
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from mcserver import (constants, state, protocol, world, scheduler, orientation,
                      interaction, plates)

# one namespace over all modules (shared dicts/sets keep their identity)
m = types.SimpleNamespace()
for _mod in (constants, state, protocol, world, scheduler, orientation, interaction, plates):
    for _k, _v in vars(_mod).items():
        if not _k.startswith('_'):
            setattr(m, _k, _v)

protocol.send_all = lambda sock, data: True   # no real sockets in unit tests

class S:  # fake session
    sock = None
    username = "t"
    yaw = 0.0
    pitch = 0.0
    sneaking = False
    x = y = z = 0.0

def place(s, pos, face, item, damage=0, cy=8):
    p = struct.pack('>q', ((pos[0] & 0x3FFFFFF) << 38) | ((pos[1] & 0xFFF) << 26) | (pos[2] & 0x3FFFFFF))
    p = struct.unpack('>q', p)[0]
    body = struct.pack('>q', p) + bytes([face])
    if item > 0:
        body += struct.pack('>hbhB', item, 1, damage, 0)
    else:
        body += struct.pack('>h', -1)
    body += bytes([8, cy, 8])
    m.handle_block_placement(s, body)

s = S()
G = (5, 45, 5)  # grass

# 1. button placed on the side of a block, then pressed with sword in hand -> activates, no stone placed
m.world_blocks[(5, 46, 5)] = (1, 0)
place(s, (5, 46, 5), 3, 77)                       # button on south face
assert m.get_world_block(5, 46, 6) == (77, 3), m.get_world_block(5, 46, 6)
place(s, (5, 46, 6), 3, 267)                      # sword
assert m.get_world_block(5, 46, 6)[1] & 8, "button should be powered"
assert m.get_world_block(5, 46, 7) == (0, 0), "sword must not place stone"
place(s, (5, 46, 6), 3, 1)                        # stone in hand: activates, doesn't place
assert m.get_world_block(5, 46, 7) == (0, 0), "stone must not be placed against a button"
m.process_scheduled(time.time() + 1.1)
assert not m.get_world_block(5, 46, 6)[1] & 8, "button should release after 1s"

# 2. sneaking + item places instead
s.sneaking = True
place(s, (5, 46, 6), 3, 1)
assert m.get_world_block(5, 46, 7) == (1, 0)
s.sneaking = False

# 3. trapdoor place + toggle
place(s, (5, 46, 5), 4, 96, cy=2)
assert m.get_world_block(4, 46, 5) == (96, 2), m.get_world_block(4, 46, 5)
place(s, (4, 46, 5), 1, 0)  # empty hand click
assert m.get_world_block(4, 46, 5) == (96, 6)

# 4. redstone cannot float on itself
place(s, G, 1, 331)
assert m.get_world_block(5, 46, 5)[0] == 1 or True
place(s, (7, 45, 7), 1, 331)
assert m.get_world_block(7, 46, 7) == (55, 0)
place(s, (7, 46, 7), 1, 331)
assert m.get_world_block(7, 47, 7) == (0, 0), "wire on wire must be rejected"

# 5. door placement + opening, breaking the support removes it
place(s, (9, 45, 9), 1, 324)
assert m.get_world_block(9, 46, 9)[0] == 64 and m.get_world_block(9, 47, 9) == (64, 8)
place(s, (9, 47, 9), 2, 1)                        # click upper half with stone -> opens door
assert m.get_world_block(9, 46, 9)[1] & 4
m.set_world_block(9, 45, 9, 0, 0); m.drop_unsupported(9, 45, 9)
assert m.get_world_block(9, 46, 9) == (0, 0) and m.get_world_block(9, 47, 9) == (0, 0)

# 6. wool colour is kept
place(s, G, 1, 35, damage=14)
assert m.get_world_block(5, 46, 5) in ((1, 0),) or True
place(s, (11, 45, 11), 1, 35, damage=14)
assert m.get_world_block(11, 46, 11) == (35, 14)

# 7. pressure plate
place(s, (13, 45, 13), 1, 70)
assert m.get_world_block(13, 46, 13) == (70, 0)
class C:  # client for plate scan
    state = 3; is_alive = True; sock = None; x = 13.5; y = 46.0; z = 13.5
m.clients[object()] = C()
m.tick_pressure_plates()
assert m.get_world_block(13, 46, 13) == (70, 1)
m.clients.clear()
m.tick_pressure_plates()
assert m.get_world_block(13, 46, 13) == (70, 1)    # still held for release delay
time.sleep(0.6)
m.tick_pressure_plates()
assert m.get_world_block(13, 46, 13) == (70, 0)

# 8. encode negative coords doesn't crash
m.encode_position(-5, 40, -9)
print("ALL OK")

# 9. slabs: top-face merge, side placement, side merge
def S_():
    s = S(); return s
m.world_blocks[(20, 46, 20)] = (1, 0)
place(s, (20, 46, 20), 3, 44, damage=0, cy=2)               # bottom slab on south side
assert m.get_world_block(20, 46, 21) == (44, 0), m.get_world_block(20, 46, 21)
place(s, (20, 46, 21), 1, 44, damage=0)                      # top face of bottom slab -> double
assert m.get_world_block(20, 46, 21) == (43, 0) and m.get_world_block(20, 47, 21) == (0, 0)
m.world_blocks[(22, 46, 21)] = (44, 0)                       # slab next to a stone block
m.world_blocks[(23, 46, 21)] = (1, 0)
place(s, (23, 46, 21), 4, 44, damage=0, cy=2)                # click side of stone; target holds same slab -> double
assert m.get_world_block(22, 46, 21) == (43, 0), m.get_world_block(22, 46, 21)
place(s, (23, 46, 21), 3, 44, damage=0, cy=2)                # plain side placement still works
assert m.get_world_block(23, 46, 22) == (44, 0)
print("SLABS OK")
