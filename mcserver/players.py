"""Kill / kick commands and player entity handling."""

import math
import random
import socket
import struct

from .constants import SPAWN_X, SPAWN_Y, SPAWN_Z
from .logs import log_msg
from .protocol import pack_chat, pack_varint, send_packet
from .state import clients, clients_lock

def kill_player(session):
    health_payload = struct.pack('>f', 0.0) + pack_varint(0) + struct.pack('>f', 0.0)
    send_packet(session.sock, "PLAY", 0x06, health_payload)
    session.is_alive = False


def execute_kill_command(target_str):
    with clients_lock:
        active_players = [s for s in clients.values() if s.state == 3 and s.is_alive]

    if not active_players:
        log_msg("[CONSOLE] No living targets found to kill.")
        return

    if target_str == "@e":
        for p in active_players:
            kill_player(p)
        log_msg(f"[CONSOLE] Killed {len(active_players)} entity/entities")

    elif target_str == "@p":
        nearest = min(
            active_players,
            key=lambda p: math.sqrt((p.x - SPAWN_X)**2 + (p.y - SPAWN_Y)**2 + (p.z - SPAWN_Z)**2)
        )
        kill_player(nearest)
        log_msg(f"[CONSOLE] Killed {nearest.username}")

    elif target_str == "@r":
        target = random.choice(active_players)
        kill_player(target)
        log_msg(f"[CONSOLE] Killed {target.username}")

    else:
        matched = [p for p in active_players if p.username.lower() == target_str.lower()]
        if matched:
            for p in matched:
                kill_player(p)
            log_msg(f"[CONSOLE] Killed {target_str}")
        else:
            log_msg(f"[CONSOLE] Selector or player '{target_str}' matched no targets.")


def kick_player(session, reason):
    """Send a disconnect screen, then close the connection.

    shutdown() (instead of close()) lets the network thread notice the end of the
    stream and clean the session up through its normal disconnect path.
    """
    message = f"§cYou've been kicked by the server.§r\n\n§7Reason: §f{reason}"
    send_packet(session.sock, "PLAY", 0x40, pack_chat(message))
    try:
        session.sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass


def execute_kick_command(target_str, reason="No reason specified"):
    with clients_lock:
        online = [s for s in clients.values() if s.state == 3]

    if not online:
        log_msg("[CONSOLE] No players online to kick.")
        return

    if target_str == "@e":
        targets = online
    elif target_str == "@p":
        targets = [min(
            online,
            key=lambda p: math.sqrt((p.x - SPAWN_X)**2 + (p.y - SPAWN_Y)**2 + (p.z - SPAWN_Z)**2)
        )]
    elif target_str == "@r":
        targets = [random.choice(online)]
    else:
        targets = [p for p in online if p.username.lower() == target_str.lower()]

    if not targets:
        log_msg(f"[CONSOLE] Selector or player '{target_str}' matched no targets.")
        return

    for p in targets:
        kick_player(p, reason)
    names = ", ".join(p.username for p in targets)
    log_msg(f"[CONSOLE] Kicked {names} ({reason})")
