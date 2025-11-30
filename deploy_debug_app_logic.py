import paramiko
import time
import os

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def deploy_and_run_app_logic():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)
        sftp = ssh.open_sftp()

        print("Uploading debug_app_logic.py...")
        sftp.put("debug_app_logic.py", "/home/devyjones/MaxFlash/debug_app_logic.py")
        sftp.close()

        print("Running debug_app_logic.py...")
        stdin, stdout, stderr = ssh.exec_command("python3 /home/devyjones/MaxFlash/debug_app_logic.py")
        print(stdout.read().decode())
        print(stderr.read().decode())

    except Exception as e:
        print(f"Deploy failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    deploy_and_run_app_logic()
