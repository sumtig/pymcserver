"""Starts the real network loop, logs in with a raw socket and places a block."""
import os, socket, struct, sys, threading, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mcserver.network import run_server_network
from mcserver.plates import run_tick_loop
from mcserver.protocol import pack_varint, read_varint, encode_position
from mcserver.world import get_world_block


def frame(packet_id, data=b''):
    body = pack_varint(packet_id) + data
    return pack_varint(len(body)) + body


def read_packets(sock, seconds):
    sock.settimeout(0.2)
    buf, end = b'', time.time() + seconds
    while time.time() < end:
        try:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buf += chunk
        except socket.timeout:
            pass
    packets, off = [], 0
    while off < len(buf):
        try:
            length, o2 = read_varint(buf, off)
        except IndexError:
            break
        if o2 + length > len(buf):
            break
        pid, o3 = read_varint(buf, o2)
        packets.append((pid, buf[o3:o2 + length]))
        off = o2 + length
    return packets


threading.Thread(target=run_server_network, daemon=True).start()
threading.Thread(target=run_tick_loop, daemon=True).start()
time.sleep(0.5)

s = socket.create_connection(('127.0.0.1', 25565))
host = b'localhost'
s.sendall(frame(0x00, pack_varint(47) + bytes([len(host)]) + host + struct.pack('>H', 25565) + pack_varint(2)))
name = b'smoke'
s.sendall(frame(0x00, bytes([len(name)]) + name))
login = read_packets(s, 1.0)
ids = [p[0] for p in login]
assert 0x02 in ids and 0x01 in ids and 0x08 in ids, ids       # login success, join game, position
assert ids.count(0x21) == 4, ids                              # four chunks
print('login ok, packets:', len(login))

# place a stone block on the side of a block that exists only in the world dict
from mcserver.state import world_blocks
world_blocks[(8, 46, 8)] = (1, 0)
place = (encode_position(8, 46, 8) + bytes([3]) +
         struct.pack('>hbhB', 1, 1, 0, 0) + bytes([8, 8, 8]))
s.sendall(frame(0x08, place))
resp = read_packets(s, 0.6)
assert any(p[0] == 0x23 for p in resp), [p[0] for p in resp]  # block change broadcast back
assert get_world_block(8, 46, 9) == (1, 0), get_world_block(8, 46, 9)
print('placement over the network ok')

# a button: press it, then the server must release it by itself
world_blocks[(8, 47, 9)] = (77, 3)
press = (encode_position(8, 47, 9) + bytes([3]) + struct.pack('>h', -1) + bytes([8, 8, 8]))
s.sendall(frame(0x08, press))
time.sleep(0.3)
assert get_world_block(8, 47, 9)[1] & 8, 'button should be powered'
time.sleep(1.2)
assert not get_world_block(8, 47, 9)[1] & 8, 'button should have released itself'
print('button press/release ok')
print('SMOKE OK')
