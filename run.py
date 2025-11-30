#!/usr/bin/env python3
"""
MaxFlash Unified Entry Point
Usage:
    python run.py [command] [options]

Commands:
    all         Start all services (Bot + Dashboard + MCP)
    bot         Start Telegram Bot only
    dashboard   Start Web Dashboard only
    core        Start Core Services (MCP only for now)

Options:
    --debug     Enable debug logging
    --port      Port for dashboard (default: 8050)
"""

import argparse
import os
import sys
import subprocess
import time
import threading
import webbrowser
import socket
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))


def print_status(msg, level="INFO"):
    colors = {
        "INFO": "\033[92m",  # Green
        "WARN": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "RESET": "\033[0m",
    }
    if sys.platform == "win32":
        print(f"[{level}] {msg}")
    else:
        print(f"{colors.get(level, '')}[{level}] {msg}{colors['RESET']}")


def check_dependencies():
    """Check and install requirements."""
    print_status("Checking dependencies...", "INFO")
    try:
        import pandas
        import dash
        import plotly
        import requests
    except ImportError:
        print_status("Installing missing dependencies...", "WARN")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print_status("Dependencies installed.", "INFO")
        except subprocess.CalledProcessError:
            print_status(
                "Failed to install dependencies. Please run 'pip install -r requirements.txt' manually.", "ERROR"
            )
            sys.exit(1)


def run_mcp_server():
    """Start MCP Server."""
    print_status("Starting MCP Server...", "INFO")
    return subprocess.Popen([sys.executable, "mcp_server.py"], cwd=PROJECT_ROOT)


def run_telegram_bot():
    """Start Telegram Bot."""
    print_status("Starting Telegram Bot...", "INFO")
    # Assuming run_bot.py is the entry point for the bot
    return subprocess.Popen([sys.executable, "run_bot.py"], cwd=PROJECT_ROOT)


def run_dashboard(port=8050):
    """Start Web Dashboard."""
    print_status(f"Starting Dashboard on port {port}...", "INFO")

    # Open browser in a separate thread
    def open_browser():
        time.sleep(3)
        url = f"http://localhost:{port}"
        print_status(f"Opening browser: {url}", "INFO")
        try:
            webbrowser.open(url)
        except Exception as e:
            print_status(f"Failed to open browser: {e}", "WARN")

    threading.Thread(target=open_browser, daemon=True).start()

    # Run dashboard
    # We use subprocess to keep it isolated, or we could import it.
    # Subprocess is safer for a runner script.
    env = os.environ.copy()
    env["PORT"] = str(port)
    return subprocess.Popen([sys.executable, "web_interface/app.py"], cwd=PROJECT_ROOT, env=env)


def main():
    parser = argparse.ArgumentParser(description="MaxFlash Trading System CLI")
    parser.add_argument("command", choices=["all", "bot", "dashboard", "core"], help="Command to execute")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--port", type=int, default=8050, help="Dashboard port")

    args = parser.parse_args()

    check_dependencies()

    processes = []

    try:
        if args.command in ["core", "all"]:
            processes.append(run_mcp_server())

        if args.command in ["bot", "all"]:
            processes.append(run_telegram_bot())

        if args.command in ["dashboard", "all"]:
            processes.append(run_dashboard(args.port))

        # Keep main thread alive to monitor processes
        while True:
            time.sleep(1)
            for p in processes:
                if p.poll() is not None:
                    print_status(f"Process {p.args} exited with code {p.returncode}", "WARN")
                    # Optionally restart or exit
                    # For now, if any critical process dies, we exit all?
                    # Let's just log it.
                    processes.remove(p)

            if not processes:
                print_status("All processes finished.", "INFO")
                break

    except KeyboardInterrupt:
        print_status("Stopping all services...", "INFO")
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()


if __name__ == "__main__":
    main()
