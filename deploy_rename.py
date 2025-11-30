import paramiko
import time

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def deploy_rename():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)
        sftp = ssh.open_sftp()

        print("Uploading web_interface/dashboard.py...")
        sftp.put("web_interface/dashboard.py", "/home/devyjones/MaxFlash/web_interface/dashboard.py")
        sftp.close()

        print("Updating dashboard.service...")
        # Read current service file
        stdin, stdout, stderr = ssh.exec_command("cat /etc/systemd/system/dashboard.service")
        service_content = stdout.read().decode()

        # Replace app.py with dashboard.py
        new_service_content = service_content.replace("app.py", "dashboard.py")

        # Write back (requires sudo)
        # We'll write to a temp file then move it
        temp_file = "/home/devyjones/dashboard.service.tmp"
        sftp = ssh.open_sftp()
        with sftp.file(temp_file, "w") as f:
            f.write(new_service_content)
        sftp.close()

        ssh.exec_command(f"echo '{password}' | sudo -S mv {temp_file} /etc/systemd/system/dashboard.service")
        ssh.exec_command(f"echo '{password}' | sudo -S systemctl daemon-reload")

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

        # Optional: Remove old app.py
        # ssh.exec_command("rm /home/devyjones/MaxFlash/web_interface/app.py")

    except Exception as e:
        print(f"Deploy failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    deploy_rename()
