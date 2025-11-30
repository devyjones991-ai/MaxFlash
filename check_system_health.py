import paramiko
import time

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def check_health():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)

        print("\n=== SERVICE STATUS ===")
        stdin, stdout, stderr = ssh.exec_command("systemctl status dashboard.service bot.service")
        print(stdout.read().decode())

        print("\n=== PORTS ===")
        stdin, stdout, stderr = ssh.exec_command(f"echo '{password}' | sudo -S netstat -tulnp | grep python")
        print(stdout.read().decode())

        print("\n=== RESOURCES ===")
        stdin, stdout, stderr = ssh.exec_command("free -h; echo ''; df -h")
        print(stdout.read().decode())

        print("\n=== DASHBOARD LOGS (Last 50) ===")
        stdin, stdout, stderr = ssh.exec_command(
            f"echo '{password}' | sudo -S journalctl -u dashboard.service -n 50 --no-pager"
        )
        print(stdout.read().decode())

        print("\n=== BOT LOGS (Last 50) ===")
        stdin, stdout, stderr = ssh.exec_command(
            f"echo '{password}' | sudo -S journalctl -u bot.service -n 50 --no-pager"
        )
        print(stdout.read().decode())

    except Exception as e:
        print(f"Health check failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    check_health()
