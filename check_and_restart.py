import paramiko
import time

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def check_and_restart():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)

        print("\n--- Checking for Fix ---")
        cmd = "grep 'if not exchange.markets:' /home/devyjones/MaxFlash/utils/exchange_manager.py"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        result = stdout.read().decode().strip()

        if result:
            print(f"Fix FOUND: {result}")
        else:
            print("Fix NOT FOUND! Re-uploading required.")
            # Re-upload immediately if missing
            sftp = ssh.open_sftp()
            print("Uploading utils/exchange_manager.py...")
            sftp.put("utils/exchange_manager.py", "/home/devyjones/MaxFlash/utils/exchange_manager.py")
            sftp.close()
            print("Upload complete.")

        print("\n--- Cleaning PyCache ---")
        ssh.exec_command(
            f"echo '{password}' | sudo -S find /home/devyjones/MaxFlash -name '__pycache__' -type d -exec rm -rf {{}} +"
        )

        print("\n--- Restarting Services ---")
        ssh.exec_command(f"echo '{password}' | sudo -S systemctl restart dashboard.service bot.service")
        time.sleep(5)

        print("\n--- Service Status ---")
        stdin, stdout, stderr = ssh.exec_command("systemctl status dashboard.service bot.service")
        print(stdout.read().decode())

    except Exception as e:
        print(f"Operation failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    check_and_restart()
