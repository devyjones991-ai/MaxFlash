import paramiko

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def check_app_files():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)

        print("\n--- Checking Root app.py ---")
        stdin, stdout, stderr = ssh.exec_command("ls -la /home/devyjones/MaxFlash/app.py")
        print(stdout.read().decode())
        print(stderr.read().decode())

        print("\n--- Checking Web Interface app.py ---")
        stdin, stdout, stderr = ssh.exec_command("ls -la /home/devyjones/MaxFlash/web_interface/app.py")
        print(stdout.read().decode())
        print(stderr.read().decode())

        print("\n--- Listing Web Interface Dir ---")
        stdin, stdout, stderr = ssh.exec_command("ls -la /home/devyjones/MaxFlash/web_interface/")
        print(stdout.read().decode())

    except Exception as e:
        print(f"Check failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    check_app_files()
