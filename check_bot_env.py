import paramiko
import time

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def check_bot_env():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)

        print("\n--- Pip Install Output ---")
        stdin, stdout, stderr = ssh.exec_command("pip3 install python-telegram-bot --user")
        print(stdout.read().decode())
        print(stderr.read().decode())

        print("\n--- Check Import ---")
        stdin, stdout, stderr = ssh.exec_command("python3 -c 'import telegram; print(telegram.__file__)'")
        print(stdout.read().decode())
        print(stderr.read().decode())

        print("\n--- Python Version ---")
        stdin, stdout, stderr = ssh.exec_command("python3 --version")
        print(stdout.read().decode())

    except Exception as e:
        print(f"Check failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    check_bot_env()
