"""Console commands."""

import signal
import threading
import time

from . import logs
from .fluids import run_fluid_physics
from .logs import log_lock, log_msg, logs_list
from .network import run_server_network, shutdown_server
from .plates import run_tick_loop
from .players import execute_kick_command, execute_kill_command
from .weather import set_server_weather

def display_help_menu():
    print("--- Available Commands ---")
    print("  weather set <clear|rain|thunder> : Changes world weather")
    print("  kill <@e|@p|@r|player>           : Kills targeted entity/player")
    print("  kick <@e|@p|@r|player> [reason]  : Kicks targeted player(s) from the server")
    print("  log / logs                       : Opens live server log stream view")
    print("  help                             : Displays this list of commands")
    print("  stop / exit                      : Gracefully shuts down the server")


def main_cli():
    net_thread = threading.Thread(target=run_server_network, daemon=True)
    net_thread.start()

    fluid_thread = threading.Thread(target=run_fluid_physics, daemon=True)
    fluid_thread.start()

    tick_thread = threading.Thread(target=run_tick_loop, daemon=True)
    tick_thread.start()

    time.sleep(0.2)

    while True:
        try:
            cmd_input = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nType 'stop' or 'exit' to shut down the server.")
            continue

        if not cmd_input:
            continue

        if cmd_input.startswith('/'):
            cmd_input = cmd_input[1:]

        parts = cmd_input.split()
        cmd = parts[0].lower()

        if cmd in ("help", "?"):
            display_help_menu()

        elif cmd in ("log", "logs"):
            logs.in_log_mode = True
            print("\n=== LOG STREAM VIEW (Press Ctrl+C or Ctrl+Z to return to console) ===")

            with log_lock:
                for line in logs_list:
                    print(line)

            def sig_handler(signum, frame):
                raise KeyboardInterrupt

            old_sigtstp = None
            if hasattr(signal, 'SIGTSTP'):
                old_sigtstp = signal.signal(signal.SIGTSTP, sig_handler)

            try:
                while logs.in_log_mode:
                    time.sleep(0.1)
            except (KeyboardInterrupt, EOFError):
                pass
            finally:
                logs.in_log_mode = False
                if hasattr(signal, 'SIGTSTP') and old_sigtstp is not None:
                    signal.signal(signal.SIGTSTP, old_sigtstp)
                print("=== EXITED LOG VIEW ===\n")

        elif cmd == "weather":
            if len(parts) >= 3 and parts[1].lower() == "set":
                set_server_weather(parts[2].lower())
            elif len(parts) >= 2 and parts[1].lower() in ("clear", "rain", "thunder"):
                set_server_weather(parts[1].lower())
            else:
                log_msg("[CONSOLE] Usage: weather set <clear|rain|thunder>")

        elif cmd == "kill":
            if len(parts) > 1:
                execute_kill_command(parts[1])
            else:
                log_msg("[CONSOLE] Please select what to kill. (Usage: kill <@e|@p|@r|player>)")

        elif cmd == "kick":
            if len(parts) > 1:
                reason = " ".join(parts[2:]) or "No reason specified"
                execute_kick_command(parts[1], reason)
            else:
                log_msg("[CONSOLE] Please select who to kick. (Usage: kick <@e|@p|@r|player> [reason])")

        elif cmd in ("stop", "exit"):
            shutdown_server()

        else:
            print(f"Unknown command: '{cmd}'. Type 'help' for available commands.")
