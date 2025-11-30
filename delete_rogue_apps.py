import paramiko
import time

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def delete_rogue():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)

        print("Deleting rogue app.py files...")
        ssh.exec_command(f"echo '{password}' | sudo -S rm /home/devyjones/MaxFlash/web_interface/app.py")
        ssh.exec_command(f"echo '{password}' | sudo -S rm /home/devyjones/MaxFlash/web_interface/components/app.py")

        print("Cleaning PyCache...")
        ssh.exec_command(
            f"echo '{password}' | sudo -S find /home/devyjones/MaxFlash -name '__pycache__' -type d -exec rm -rf {{}} +"
        )

        print("Restarting Dashboard...")
        ssh.exec_command(f"echo '{password}' | sudo -S systemctl restart dashboard.service")
        time.sleep(5)

        print("\n--- Dashboard Status ---")
        stdin, stdout, stderr = ssh.exec_command("systemctl status dashboard.service")
        print(stdout.read().decode())

        print("\n--- Dashboard Logs (Last 20) ---")
        stdin, stdout, stderr = ssh.exec_command(
            f"echo '{password}' | sudo -S journalctl -u dashboard.service -n 20 --no-pager"
        )
        print(stdout.read().decode())

    except Exception as e:
        print(f"Delete failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    delete_rogue()
