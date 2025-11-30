import paramiko
import time

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def deploy_fix_exchange():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)
        sftp = ssh.open_sftp()

        print("Uploading utils/exchange_manager.py...")
        sftp.put("utils/exchange_manager.py", "/home/devyjones/MaxFlash/utils/exchange_manager.py")
        sftp.close()

        print("File uploaded.")

    except Exception as e:
        print(f"Deploy failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    deploy_fix_exchange()
