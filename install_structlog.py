import paramiko
import time

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def install_structlog():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)

        print("Installing structlog...")
        ssh.exec_command("pip3 install structlog --user --break-system-packages")
        time.sleep(5)

        print("Restarting Bot...")
        ssh.exec_command(f"echo '{password}' | sudo -S systemctl restart bot.service")
        time.sleep(5)

        print("\n--- Bot Status ---")
        stdin, stdout, stderr = ssh.exec_command("systemctl status bot.service")
        print(stdout.read().decode())

        print("\n--- Bot Logs (Last 20) ---")
        stdin, stdout, stderr = ssh.exec_command(
            f"echo '{password}' | sudo -S journalctl -u bot.service -n 20 --no-pager"
        )
        print(stdout.read().decode())

    except Exception as e:
        print(f"Install failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    install_structlog()
