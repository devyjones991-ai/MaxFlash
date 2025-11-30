import paramiko

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def read_remote_file():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)

        print("\n--- utils/exchange_manager.py ---")
        stdin, stdout, stderr = ssh.exec_command(f"cat /home/devyjones/MaxFlash/utils/exchange_manager.py")
        print(stdout.read().decode())

    except Exception as e:
        print(f"Read failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    read_remote_file()
