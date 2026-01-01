"""
Deployment script for MaxFlash to remote server.

Deploys:
- LightGBM model (trained, fixed version)
- Dashboard v2 (web interface)
- Telegram bot v2
- All necessary dependencies

Server: 192.168.0.203
User: devyjones
Port: 22
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Server configuration
SERVER_CONFIG = {
    'host': '192.168.0.203',
    'port': 22,
    'user': 'devyjones',
    'password': '19Maxon91!',
    'remote_path': '/home/devyjones/MaxFlash',
}

# Files and directories to sync
SYNC_ITEMS = [
    'ml/',
    'utils/',
    'bots/',
    'web_interface/',
    'app/',
    'services/',
    'indicators/',
    'trading/',
    'models/',
    'scripts/auto_retrain_v2.py',
    'scripts/train_lightgbm_fixed.py',
    'scripts/run_walk_forward_backtest.py',
    'run_bot_v2.py',
    'requirements.txt',
    '.env',
    'infra/',
]

# Files to exclude
EXCLUDE_PATTERNS = [
    '__pycache__',
    '*.pyc',
    '.git',
    '.vscode',
    '.idea',
    'data/',
    'backtest_results/',
    'logs/',
    '*.log',
    'freqtrade/',  # Large, not needed on server
]


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*80}")
    print(title.center(80))
    print(f"{'='*80}\n")


def run_command(cmd: str, description: str = None, capture: bool = False):
    """
    Run a shell command and print output.

    Args:
        cmd: Command to run
        description: Optional description to print
        capture: If True, capture and return output

    Returns:
        Output if capture=True, else None
    """
    if description:
        print(f"[RUN] {description}")
    print(f"  $ {cmd}")

    if capture:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [ERROR] {result.stderr}")
            return None
        return result.stdout.strip()
    else:
        result = subprocess.run(cmd, shell=True)
        return result.returncode == 0


def check_ssh_connection():
    """Check if SSH connection works."""
    print_section("CHECKING SSH CONNECTION")

    cmd = f"ssh -p {SERVER_CONFIG['port']} {SERVER_CONFIG['user']}@{SERVER_CONFIG['host']} 'echo OK'"

    print(f"Testing connection to {SERVER_CONFIG['user']}@{SERVER_CONFIG['host']}:{SERVER_CONFIG['port']}")

    # Note: This is a simplified version. In production, use SSH keys instead of password
    result = run_command(cmd, capture=True)

    if result == "OK":
        print("✅ SSH connection successful")
        return True
    else:
        print("❌ SSH connection failed")
        print("\n⚠️  Make sure:")
        print("  1. Server is accessible")
        print("  2. SSH is configured")
        print("  3. SSH key is set up (recommended) or sshpass is installed")
        return False


def sync_files():
    """Sync files to server using rsync."""
    print_section("SYNCING FILES TO SERVER")

    project_root = Path(__file__).parent.parent

    # Build exclude arguments
    exclude_args = ' '.join([f"--exclude='{pattern}'" for pattern in EXCLUDE_PATTERNS])

    # Build rsync command
    # Note: Using rsync over SSH
    items = ' '.join(SYNC_ITEMS)

    remote = f"{SERVER_CONFIG['user']}@{SERVER_CONFIG['host']}:{SERVER_CONFIG['remote_path']}/"

    cmd = f"rsync -avz --progress {exclude_args} -e 'ssh -p {SERVER_CONFIG['port']}' {items} {remote}"

    print(f"Syncing from: {project_root}")
    print(f"Syncing to: {remote}")
    print(f"\nItems to sync:")
    for item in SYNC_ITEMS:
        print(f"  - {item}")

    success = run_command(cmd, "Syncing files...")

    if success:
        print("\n✅ Files synced successfully")
        return True
    else:
        print("\n❌ File sync failed")
        return False


def install_dependencies():
    """Install Python dependencies on server."""
    print_section("INSTALLING DEPENDENCIES ON SERVER")

    remote_cmd = f"cd {SERVER_CONFIG['remote_path']} && python3 -m pip install -r requirements.txt --user"

    cmd = f"ssh -p {SERVER_CONFIG['port']} {SERVER_CONFIG['user']}@{SERVER_CONFIG['host']} '{remote_cmd}'"

    print("Installing Python packages from requirements.txt...")

    success = run_command(cmd)

    if success:
        print("\n✅ Dependencies installed")
        return True
    else:
        print("\n❌ Dependency installation failed")
        return False


def setup_services():
    """Set up systemd services on server."""
    print_section("SETTING UP SYSTEMD SERVICES")

    services = [
        ('maxflash-bot', 'Telegram Bot v2'),
        ('maxflash-dashboard', 'Dashboard v2'),
        ('maxflash-retrain', 'Auto-retrain service'),
    ]

    print("Services to set up:")
    for service_name, description in services:
        print(f"  - {service_name}: {description}")

    # Copy systemd files
    remote_cmd = f"""
    cd {SERVER_CONFIG['remote_path']} && \
    sudo cp infra/*.service /etc/systemd/system/ && \
    sudo cp infra/*.timer /etc/systemd/system/ && \
    sudo systemctl daemon-reload
    """

    cmd = f"ssh -p {SERVER_CONFIG['port']} {SERVER_CONFIG['user']}@{SERVER_CONFIG['host']} '{remote_cmd}'"

    success = run_command(cmd, "Setting up systemd services...")

    if success:
        print("\n✅ Services configured")
        return True
    else:
        print("\n❌ Service setup failed")
        return False


def start_services():
    """Start services on server."""
    print_section("STARTING SERVICES")

    services = [
        'maxflash-bot',
        'maxflash-dashboard',
        'maxflash-retrain.timer',
    ]

    for service in services:
        remote_cmd = f"sudo systemctl restart {service} && sudo systemctl enable {service}"
        cmd = f"ssh -p {SERVER_CONFIG['port']} {SERVER_CONFIG['user']}@{SERVER_CONFIG['host']} '{remote_cmd}'"

        print(f"\nStarting {service}...")
        run_command(cmd)

    print("\n✅ Services started")


def check_service_status():
    """Check status of services."""
    print_section("SERVICE STATUS")

    services = [
        'maxflash-bot',
        'maxflash-dashboard',
        'maxflash-retrain.timer',
    ]

    for service in services:
        remote_cmd = f"sudo systemctl status {service} --no-pager -l"
        cmd = f"ssh -p {SERVER_CONFIG['port']} {SERVER_CONFIG['user']}@{SERVER_CONFIG['host']} '{remote_cmd}'"

        print(f"\n{'─'*80}")
        print(f"{service} STATUS")
        print(f"{'─'*80}")
        run_command(cmd)


def deploy_full():
    """Full deployment workflow."""
    print_section("MAXFLASH DEPLOYMENT TO SERVER")

    print(f"Target server: {SERVER_CONFIG['user']}@{SERVER_CONFIG['host']}:{SERVER_CONFIG['port']}")
    print(f"Remote path: {SERVER_CONFIG['remote_path']}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 1: Check SSH
    if not check_ssh_connection():
        print("\n❌ Deployment aborted - SSH connection failed")
        return False

    # Step 2: Sync files
    if not sync_files():
        print("\n❌ Deployment aborted - File sync failed")
        return False

    # Step 3: Install dependencies
    if not install_dependencies():
        print("\n⚠️  Warning: Dependency installation failed, continuing anyway...")

    # Step 4: Setup services
    if not setup_services():
        print("\n⚠️  Warning: Service setup failed, continuing anyway...")

    # Step 5: Start services
    start_services()

    # Step 6: Check status
    check_service_status()

    print_section("DEPLOYMENT COMPLETE")
    print("✅ MaxFlash deployed successfully!")
    print("\nNext steps:")
    print("  1. Check service logs: sudo journalctl -u maxflash-bot -f")
    print("  2. Access dashboard: http://192.168.0.203:8050")
    print("  3. Test Telegram bot")

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Deploy MaxFlash to server")
    parser.add_argument('--sync-only', action='store_true', help='Only sync files')
    parser.add_argument('--services-only', action='store_true', help='Only restart services')
    parser.add_argument('--status', action='store_true', help='Check service status only')
    args = parser.parse_args()

    if args.status:
        check_service_status()
    elif args.sync_only:
        sync_files()
    elif args.services_only:
        start_services()
        check_service_status()
    else:
        deploy_full()
