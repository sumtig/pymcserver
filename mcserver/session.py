"""Per-connection client state and packet framing."""

import time

from .constants import SPAWN_X, SPAWN_Y, SPAWN_Z

class ClientSession:
    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr
        self.buffer = bytearray()
        self.state = 0
        self.username = "Unknown"
        self.last_keep_alive = time.time()
        self.x = SPAWN_X
        self.y = SPAWN_Y
        self.z = SPAWN_Z
        self.yaw = 0.0
        self.pitch = 0.0
        self.is_alive = True
        self.sneaking = False

    def feed_data(self, data):
        self.buffer.extend(data)

    def extract_packets(self):
        packets = []
        offset = 0

        while True:
            val = 0
            shift = 0
            varint_bytes_read = 0

            for i in range(offset, len(self.buffer)):
                byte = self.buffer[i]
                val |= (byte & 0x7F) << shift
                varint_bytes_read += 1
                if not (byte & 0x80):
                    break
                shift += 7
                if shift >= 32:
                    raise ValueError("VarInt is too big!")
            else:
                break

            packet_length = val
            total_header_size = varint_bytes_read

            if len(self.buffer) - offset < total_header_size + packet_length:
                break

            start_idx = offset + total_header_size
            end_idx = start_idx + packet_length
            packets.append(bytes(self.buffer[start_idx:end_idx]))
            offset = end_idx

        if offset > 0:
            del self.buffer[:offset]

        return packets
