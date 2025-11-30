import paramiko

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def check_status():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)

        print("\n--- Dashboard Status ---")
        stdin, stdout, stderr = ssh.exec_command("systemctl status dashboard.service")
        print(stdout.read().decode())

        print("\n--- Bot Status ---")
        stdin, stdout, stderr = ssh.exec_command("systemctl status bot.service")
        print(stdout.read().decode())

    except Exception as e:
        print(f"Check failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    check_status()
