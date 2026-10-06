"""Incoming packet dispatch (handshake, status, login, play)."""

import json
import struct

from . import weather
from .chunks import generate_chunk_section_data
from .constants import FAVICON_BASE64, SERVER_DESCRIPTION, SPAWN_X, SPAWN_Y, SPAWN_Z
from .interaction import handle_block_placement
from .logs import log_msg
from .protocol import block_change_payload, decode_position, pack_chat, pack_varint, read_varint, send_packet
from .state import clients, clients_lock, world_blocks
from .world import drop_unsupported, get_world_block, resync_block, set_world_block

def handle_packet(session, packet_data):
    packet_id = packet_data[0]
    payload = packet_data[1:]

    state_names = {0: "HANDSHAKE", 1: "STATUS", 2: "LOGIN", 3: "PLAY"}

    if session.state == 0:  # Handshake
        offset = 0
        while (payload[offset] & 0x80):
            offset += 1
        offset += 1
        slen = payload[offset]
        offset += 1 + slen
        offset += 2
        next_state = payload[offset]
        session.state = next_state
        log_msg(f"[LOG] Handshake complete. Next state: {state_names.get(session.state)}")

    elif session.state == 1:  # Status
            if packet_id == 0x00:  # Status Request
                with clients_lock:
                    online_count = sum(1 for s in clients.values() if s.state == 3)

                response = {
                    "version": {
                        "name": "1.8.9",
                        "protocol": 47
                    },
                    "players": {
                        "max": 20,
                        "online": online_count,
                        "sample": []
                    },
                    "description": {
                        "text": SERVER_DESCRIPTION
                    }
                }

                if FAVICON_BASE64:
                    response["favicon"] = FAVICON_BASE64

                json_bytes = json.dumps(response).encode('utf-8')
                status_payload = pack_varint(len(json_bytes)) + json_bytes

                send_packet(session.sock, "STATUS", 0x00, status_payload)

            elif packet_id == 0x01:  # Ping Request
                # Echo back the exact payload bytes received (the 64-bit long time payload)
                send_packet(session.sock, "STATUS", 0x01, payload)

    elif session.state == 2:  # Login
        if packet_id == 0x00:
            name_len = payload[0]
            session.username = payload[1:1+name_len].decode('utf-8')
            log_msg(f"[LOG] Login start from player: {session.username}")

            uuid_str = b"00000000-0000-0000-0000-000000000000"
            username_bytes = session.username.encode('utf-8')
            success_data = pack_varint(len(uuid_str)) + uuid_str + pack_varint(len(username_bytes)) + username_bytes
            send_packet(session.sock, "LOGIN", 0x02, success_data)

            session.state = 3
            session.is_alive = True
            log_msg(f"[LOG] State switched to PLAY for {session.username}")

            join_data = (
                struct.pack('>ibbbB', 1, 1, 0, 2, 20) +
                pack_varint(len(b"default")) + b"default" +
                struct.pack('?', False)
            )
            send_packet(session.sock, "PLAY", 0x01, join_data)

            send_packet(session.sock, "PLAY", 0x03, struct.pack('>qq', 6000, 6000))

            if weather.current_weather == "rain":
                send_packet(session.sock, "PLAY", 0x2B, struct.pack('>Bf', 2, 0.0))
                send_packet(session.sock, "PLAY", 0x2B, struct.pack('>Bf', 7, 1.0))
            elif weather.current_weather == "thunder":
                send_packet(session.sock, "PLAY", 0x2B, struct.pack('>Bf', 2, 0.0))
                send_packet(session.sock, "PLAY", 0x2B, struct.pack('>Bf', 7, 1.0))
                send_packet(session.sock, "PLAY", 0x2B, struct.pack('>Bf', 8, 1.0))

            log_msg("[LOG] Sending single-section chunks elevated to Y=32..47 (Grass at Y=45)...")
            raw_chunk_data = generate_chunk_section_data()
            bitmask = 0x0004

            for cx in (0, 1):
                for cz in (0, 1):
                    chunk_header = struct.pack('>ii?H', cx, cz, True, bitmask)
                    chunk_payload = chunk_header + pack_varint(len(raw_chunk_data)) + raw_chunk_data
                    send_packet(session.sock, "PLAY", 0x21, chunk_payload)

            # Blocks players built earlier are not in the chunk data, so send them to the new client
            for (wx, wy, wz), (wid, wmeta) in list(world_blocks.items()):
                send_packet(session.sock, "PLAY", 0x23, block_change_payload(wx, wy, wz, wid, wmeta))

            log_msg("[LOG] Spawning player at (8.0, 46.0, 8.0)...")
            send_packet(session.sock, "PLAY", 0x08, struct.pack('>dddffB', SPAWN_X, SPAWN_Y, SPAWN_Z, 0.0, 0.0, 0x00))

    elif session.state == 3:  # Play
        if packet_id == 0x04:  # Player Position
            session.x, session.y, session.z = struct.unpack('>ddd', payload[0:24])
        elif packet_id == 0x05:  # Player Look
            session.yaw, session.pitch = struct.unpack('>ff', payload[0:8])
        elif packet_id == 0x06:  # Player Position & Look
            session.x, session.y, session.z, session.yaw, session.pitch = struct.unpack('>dddff', payload[0:32])

        elif packet_id == 0x07:  # Player Digging / Item Dropping
            status = payload[0]
            if status in (0, 2):  # Digging
                pos_val = struct.unpack('>q', payload[1:9])[0]
                bx, by, bz = decode_position(pos_val)

                target_block_id, _ = get_world_block(bx, by, bz)
                if target_block_id == 0:
                    resync_block(session, bx, by, bz)   # client thought something was there
                    return
                log_msg(f"[WORLD] {session.username} broke block ID {target_block_id} at ({bx}, {by}, {bz})")

                set_world_block(bx, by, bz, 0, 0)
                # Removes the other door half, buttons/levers/torches/wire/plates that lost their support, etc.
                drop_unsupported(bx, by, bz)

            elif status in (3, 4):  # Drop Item / Drop Item Stack
                log_msg(f"[PLAYER] {session.username} dropped item (Status {status})")

        elif packet_id == 0x08:  # Player Block Placement
            handle_block_placement(session, payload)

        elif packet_id == 0x0B:  # Entity Action (sneak / sprint ...)
            _, off = read_varint(payload, 0)
            action, _ = read_varint(payload, off)
            if action == 0:
                session.sneaking = True
            elif action == 1:
                session.sneaking = False

        elif packet_id == 0x16:  # Client Status (Respawn)
            action_id = payload[0]
            if action_id == 0:
                session.is_alive = True
                session.sneaking = False
                session.x, session.y, session.z = SPAWN_X, SPAWN_Y, SPAWN_Z

                respawn_data = (
                    struct.pack('>ibb', 0, 2, 1) +
                    pack_varint(len(b"default")) + b"default"
                )
                send_packet(session.sock, "PLAY", 0x07, respawn_data)

                health_data = struct.pack('>f', 20.0) + pack_varint(20) + struct.pack('>f', 5.0)
                send_packet(session.sock, "PLAY", 0x06, health_data)

                send_packet(session.sock, "PLAY", 0x08, struct.pack('>dddffB', SPAWN_X, SPAWN_Y, SPAWN_Z, 0.0, 0.0, 0x00))
                log_msg(f"[LOG] {session.username} respawned successfully.")

        elif packet_id == 0x00:  # Keep Alive response
            pass
