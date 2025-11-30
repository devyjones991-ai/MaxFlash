import paramiko

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def find_rogue_apps():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)

        print("\n--- Finding app.py files ---")
        stdin, stdout, stderr = ssh.exec_command("find /home/devyjones/MaxFlash -name 'app.py'")
        print(stdout.read().decode())
        print(stderr.read().decode())

    except Exception as e:
        print(f"Check failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    find_rogue_apps()
