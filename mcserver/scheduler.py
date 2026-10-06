"""Delayed tasks (button release etc.)."""

import heapq
import itertools
import threading
import time

from .logs import log_msg

scheduled = []

sched_lock = threading.Lock()

sched_counter = itertools.count()


def schedule_ticks(ticks, fn, *args):
    with sched_lock:
        heapq.heappush(scheduled, (time.time() + ticks * 0.05, next(sched_counter), fn, args))


def process_scheduled(now=None):
    now = time.time() if now is None else now
    due = []
    with sched_lock:
        while scheduled and scheduled[0][0] <= now:
            due.append(heapq.heappop(scheduled))
    for _, _, fn, args in due:
        try:
            fn(*args)
        except Exception as e:
            log_msg(f"[ERROR] Scheduled task failed: {e}")
