import paramiko
import time

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def check_curl():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)

        print("\n--- Curl 8050 ---")
        stdin, stdout, stderr = ssh.exec_command("curl -I http://127.0.0.1:8050")
        print(stdout.read().decode())
        print(stderr.read().decode())

        print("\n--- Curl 8502 ---")
        stdin, stdout, stderr = ssh.exec_command("curl -I http://127.0.0.1:8502")
        print(stdout.read().decode())
        print(stderr.read().decode())

    except Exception as e:
        print(f"Check failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    check_curl()
