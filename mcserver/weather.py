"""Weather control."""

import struct
import threading
import time

from .logs import log_msg
from .protocol import broadcast_packet

current_weather = "clear"

weather_transition_thread = None


def transition_weather_task(target_type):
    global current_weather
    target_type = target_type.lower()

    if target_type == "clear":
        log_msg("[CONSOLE] Set the weather to Clear")
        steps = 10
        for i in range(steps, -1, -1):
            level = i / float(steps)
            broadcast_packet(0x2B, struct.pack('>Bf', 7, level))
            broadcast_packet(0x2B, struct.pack('>Bf', 8, level))
            time.sleep(0.2)

        broadcast_packet(0x2B, struct.pack('>Bf', 1, 0.0))
        current_weather = "clear"

    elif target_type == "rain":
        log_msg("[CONSOLE] Set the weather to Rain")
        broadcast_packet(0x2B, struct.pack('>Bf', 2, 0.0))
        broadcast_packet(0x2B, struct.pack('>Bf', 8, 0.0))

        steps = 10
        for i in range(1, steps + 1):
            level = i / float(steps)
            broadcast_packet(0x2B, struct.pack('>Bf', 7, level))
            time.sleep(0.2)

        current_weather = "rain"

    elif target_type == "thunder":
        log_msg("[CONSOLE] Set the weather to Rain and Thunder")
        broadcast_packet(0x2B, struct.pack('>Bf', 2, 0.0))

        steps = 10
        for i in range(1, steps + 1):
            level = i / float(steps)
            broadcast_packet(0x2B, struct.pack('>Bf', 7, level))
            broadcast_packet(0x2B, struct.pack('>Bf', 8, level))
            time.sleep(0.2)

        current_weather = "thunder"


def set_server_weather(target_type):
    global weather_transition_thread
    if target_type not in ("clear", "rain", "thunder"):
        log_msg(f"[CONSOLE] Unknown weather type '{target_type}'. Options: clear, rain, thunder")
        return

    weather_transition_thread = threading.Thread(
        target=transition_weather_task,
        args=(target_type,),
        daemon=True
    )
    weather_transition_thread.start()
