import paramiko
import time

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def debug_sqlalchemy():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)

        print("\n--- Pip Install Output ---")
        stdin, stdout, stderr = ssh.exec_command("pip3 install sqlalchemy greenlet --user --break-system-packages")
        print(stdout.read().decode())
        print(stderr.read().decode())

        print("\n--- Check Import ---")
        stdin, stdout, stderr = ssh.exec_command("python3 -c 'import sqlalchemy; print(sqlalchemy.__file__)'")
        print(stdout.read().decode())
        print(stderr.read().decode())

    except Exception as e:
        print(f"Check failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    debug_sqlalchemy()
