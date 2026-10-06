"""Server log buffer. Read/write `logs.in_log_mode` through the module."""

import threading

logs_list = []

in_log_mode = False

log_lock = threading.Lock()


def log_msg(msg):
    with log_lock:
        logs_list.append(msg)
        if in_log_mode:
            print(msg)
