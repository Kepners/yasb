import logging
import os
import subprocess
import sys

from PyQt6.QtCore import QMetaObject, QProcess, Qt
from PyQt6.QtWidgets import QApplication

from core.application import LFBarApplication
from core.event_service import EventService
from core.utils.cli_server import CliPipeHandler

LAYOUTFORGE_RESTART_SCRIPT = os.path.join(
    os.path.expanduser("~"),
    ".config",
    "layoutforge",
    "restart-layoutforge-shell.bat",
)


def reload_application(msg: str = "Reloading Application..."):
    try:
        logging.info(msg)
        if hasattr(sys, "_cli_pipe_handler") and sys._cli_pipe_handler is not None:
            sys._cli_pipe_handler.stop_cli_pipe_server()

        app = QApplication.instance()
        if isinstance(app, LFBarApplication):
            if app.loop and app.close_event:
                app.loop.call_soon_threadsafe(app.close_event.set)
            else:  # Should never happen while we use qasync
                QMetaObject.invokeMethod(app, "quit", Qt.ConnectionType.QueuedConnection)

        # Skip sys.argv[0] since QProcess.startDetached takes program + args separately
        args = list(sys.argv[1:])
        if "--restart-wait" not in args:
            args.append("--restart-wait")

        QProcess.startDetached(sys.executable, args)
    except Exception as e:
        logging.error(f"Error during reload: {e}")
        os._exit(0)


def exit_application(msg: str = "Exiting Application..."):
    logging.info(msg)
    try:
        if hasattr(sys, "_cli_pipe_handler") and sys._cli_pipe_handler is not None:
            sys._cli_pipe_handler.stop_cli_pipe_server()

        app = QApplication.instance()
        if isinstance(app, LFBarApplication):
            if app.loop and app.close_event:
                app.loop.call_soon_threadsafe(app.close_event.set)
            else:  # Should never happen while we use qasync
                QMetaObject.invokeMethod(app, "quit", Qt.ConnectionType.QueuedConnection)
    except:
        os._exit(0)


def restart_layoutforge_shell(msg: str = "Restarting LayoutForge shell..."):
    try:
        logging.info(msg)

        if not os.path.exists(LAYOUTFORGE_RESTART_SCRIPT):
            logging.warning(f"LayoutForge restart script not found: {LAYOUTFORGE_RESTART_SCRIPT}")
            return

        subprocess.Popen(
            ["cmd.exe", "/c", LAYOUTFORGE_RESTART_SCRIPT],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        logging.error(f"Failed to restart LayoutForge shell: {e}")


def process_cli_command(command: str):
    """
    Process CLI commands received from the Named Pipe server.
    Args:
        command (str): The command received from the CLI.
    """
    # Parse the command and options

    parts = command.strip().split()
    base_command = parts[0] if parts else ""

    # Extract screen parameter if present
    screen_name = None
    if "--screen" in command:
        screen_name = command.split("--screen", 1)[1].strip()
    elif "-s" in command:
        screen_name = command.split("-s", 1)[1].strip()

    if base_command == "reload":
        reload_application("Reloading Application from CLI...")

    elif base_command == "stop":
        exit_application("Exiting Application from CLI...")

    elif base_command in ["show-bar", "hide-bar", "toggle-bar"]:
        action = base_command.split("-")[0]
        EventService().emit_event("handle_bar_cli", action, screen_name)


def start_cli_server():
    handler = CliPipeHandler(process_cli_command)
    handler.start_cli_pipe_server()
    sys._cli_pipe_handler = handler
