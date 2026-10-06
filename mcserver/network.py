"""Socket server loop and shutdown."""

import select
import socket
import sys
import time

from .logs import log_msg
from .packets import handle_packet
from .protocol import pack_chat, pack_varint, send_packet
from .session import ClientSession
from .state import clients, clients_lock

def shutdown_server():
    log_msg("[SERVER] Gracefully shutting down server...")

    disconnect_payload = pack_chat("Server closed")
    with clients_lock:
        sessions = list(clients.values())
        clients.clear()
    for session in sessions:
        if session.state == 3:
            send_packet(session.sock, "PLAY", 0x40, disconnect_payload)
        try:
            session.sock.close()
        except Exception:
            pass

    time.sleep(0.1)
    sys.exit(0)


def run_server_network():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', 25565))
    server.listen(5)
    server.setblocking(False)

    inputs = [server]

    log_msg("[SERVER] Minecraft 1.8.9 Server running on port 25565...")
    log_msg("[SERVER] Type 'help' to see all available server commands.")

    try:
        while True:
            readable, _, exceptional = select.select(inputs, [], inputs, 0.05)
            now = time.time()

            for sock in readable:
                if sock is server:
                    client_sock, addr = server.accept()
                    client_sock.setblocking(False)
                    inputs.append(client_sock)
                    with clients_lock:
                        clients[client_sock] = ClientSession(client_sock, addr)
                    log_msg(f"[CONNECTION] Accepted new connection from {addr}")
                else:
                    with clients_lock:
                        session = clients.get(sock)
                    if not session:
                        continue

                    try:
                        data = sock.recv(4096)
                        if not data:
                            raise ConnectionError("Client disconnected.")

                        session.feed_data(data)
                        packets = session.extract_packets()

                        for packet_data in packets:
                            handle_packet(session, packet_data)

                    except Exception as e:
                        log_msg(f"[DISCONNECT] Client {session.addr} ({session.username}) dropped: {e}")
                        if sock in inputs:
                            inputs.remove(sock)
                        sock.close()
                        with clients_lock:
                            if sock in clients:
                                del clients[sock]

            with clients_lock:
                active_sessions = list(clients.items())

            for sock, session in active_sessions:
                if session.state == 3 and (now - session.last_keep_alive) > 5.0:
                    try:
                        keep_alive_id = int(now) & 0x7FFFFFFF
                        send_packet(session.sock, "PLAY", 0x00, pack_varint(keep_alive_id))
                        session.last_keep_alive = now
                    except Exception as e:
                        log_msg(f"[ERROR] Keep alive failed for {session.username}: {e}")

            for sock in exceptional:
                with clients_lock:
                    session = clients.get(sock)
                    if session:
                        log_msg(f"[ERROR] Socket error for {session.addr}")
                        if sock in clients:
                            del clients[sock]
                if sock in inputs:
                    inputs.remove(sock)
                sock.close()

    except Exception as e:
        log_msg(f"[SERVER EXCEPTION] Network loop stopped: {e}")
    finally:
        server.close()
