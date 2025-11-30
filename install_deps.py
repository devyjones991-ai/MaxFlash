import paramiko
import time

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def install_deps():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)

        print("Installing dependencies as user...")
        # Use user install
        cmd = "pip3 install --user dash dash-bootstrap-components ccxt plotly python-dotenv pandas numpy paramiko --break-system-packages"
        stdin, stdout, stderr = ssh.exec_command(cmd)

        # Stream output
        while not stdout.channel.exit_status_ready():
            if stdout.channel.recv_ready():
                print(stdout.channel.recv(1024).decode(), end="")

        print(stdout.read().decode())
        print(stderr.read().decode())

        print("Restarting services...")
        ssh.exec_command(f"echo '{password}' | sudo -S systemctl restart dashboard.service")
        ssh.exec_command(f"echo '{password}' | sudo -S systemctl restart bot.service")

        time.sleep(5)

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
        print(f"Installation failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    install_deps()
