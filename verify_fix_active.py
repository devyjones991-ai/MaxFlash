import paramiko
import time

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def verify_fix_active():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)

        print("\n--- Checking for Fix String ---")
        cmd = "grep 'if not exchange.markets:' /home/devyjones/MaxFlash/utils/exchange_manager.py"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        result = stdout.read().decode().strip()
        print(f"Result: '{result}'")

        print("\n--- Dashboard Logs (Last 20) ---")
        stdin, stdout, stderr = ssh.exec_command(
            f"echo '{password}' | sudo -S journalctl -u dashboard.service -n 20 --no-pager"
        )
        print(stdout.read().decode())

        print("\n--- Bot Logs (Last 20) ---")
        stdin, stdout, stderr = ssh.exec_command(
            f"echo '{password}' | sudo -S journalctl -u bot.service -n 20 --no-pager"
        )
        print(stdout.read().decode())

    except Exception as e:
        print(f"Verify failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    verify_fix_active()
