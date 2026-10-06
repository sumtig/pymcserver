"""Minecraft 1.8.9 wire helpers: varints, positions, packet sending."""

import json
import select
import struct
import threading
import time

from .state import clients, clients_lock

def pack_varint(d):
    out = bytearray()
    while True:
        byte = d & 0x7F
        d >>= 7
        if d:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            break
    return bytes(out)


def read_varint(data, offset=0):
    val = 0
    shift = 0
    while True:
        byte = data[offset]
        offset += 1
        val |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return val, offset
        shift += 7
        if shift >= 35:
            raise ValueError("VarInt is too big!")


def pack_chat(text):
    json_str = json.dumps({"text": text})
    encoded = json_str.encode('utf-8')
    return pack_varint(len(encoded)) + encoded


def encode_position(x, y, z):
    val = ((x & 0x3FFFFFF) << 38) | ((y & 0xFFF) << 26) | (z & 0x3FFFFFF)
    return struct.pack('>Q', val & 0xFFFFFFFFFFFFFFFF)   # unsigned: negative x/z no longer crash


def decode_position(val):
    x = val >> 38
    if x >= (1 << 25):
        x -= (1 << 26)
    y = (val >> 26) & 0xFFF
    z = val & 0x3FFFFFF
    if z >= (1 << 25):
        z -= (1 << 26)
    return x, y, z


send_lock = threading.Lock()


def send_all(sock, data):
    """Send everything on a non-blocking socket without losing bytes on partial writes."""
    try:
        view = memoryview(data)
        deadline = time.time() + 2.0
        while len(view):
            try:
                sent = sock.send(view)
                view = view[sent:]
            except (BlockingIOError, InterruptedError):
                if time.time() > deadline:
                    return False
                select.select([], [sock], [], 0.1)
        return True
    except (OSError, ValueError):
        return False


def send_packet(sock, state_name, packet_id, data=bytes()):
    payload = pack_varint(packet_id) + data
    packet = pack_varint(len(payload)) + payload
    with send_lock:   # packets from several threads must not interleave
        send_all(sock, packet)


def broadcast_packet(packet_id, data):
    with clients_lock:
        sessions = list(clients.values())
    for session in sessions:
        if session.state == 3:  # PLAY state
            send_packet(session.sock, "PLAY", packet_id, data)


def block_change_payload(x, y, z, block_id, meta):
    return encode_position(x, y, z) + pack_varint((block_id << 4) | (meta & 0x0F))


def send_block_change(x, y, z, block_id=0, meta=0):
    broadcast_packet(0x23, block_change_payload(x, y, z, block_id, meta))
