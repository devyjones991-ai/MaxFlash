import paramiko

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def fetch_dash_logs():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)

        print("\n--- Dashboard Logs (Last 50) ---")
        stdin, stdout, stderr = ssh.exec_command(
            f"echo '{password}' | sudo -S journalctl -u dashboard.service -n 50 --no-pager"
        )
        print(stdout.read().decode())

    except Exception as e:
        print(f"Fetch failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    fetch_dash_logs()
