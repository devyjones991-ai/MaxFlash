import paramiko
import os
import time

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def nuke_and_pave():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)
        sftp = ssh.open_sftp()

        print("Stopping services...")
        ssh.exec_command(f"echo '{password}' | sudo -S systemctl stop dashboard.service")
        ssh.exec_command(f"echo '{password}' | sudo -S systemctl stop bot.service")

        print("Killing all python processes...")
        ssh.exec_command(f"echo '{password}' | sudo -S pkill -9 python3")
        time.sleep(2)

        # Re-upload run_bot.py just in case
        print("Uploading run_bot.py...")
        sftp.put("run_bot.py", "/home/devyjones/MaxFlash/run_bot.py")

        # Re-upload service files
        bot_service = """[Unit]
Description=MaxFlash Telegram Bot
After=network.target

[Service]
User=devyjones
WorkingDirectory=/home/devyjones/MaxFlash
ExecStart=/usr/bin/python3 run_bot.py
Restart=always
Environment=PYTHONPATH=/home/devyjones/MaxFlash
Environment=FLASK_ENV=production

[Install]
WantedBy=multi-user.target
"""
        with open("bot.service", "w") as f:
            f.write(bot_service)

        print("Updating bot.service...")
        sftp.put("bot.service", "/home/devyjones/bot.service")
        ssh.exec_command(f"echo '{password}' | sudo -S mv /home/devyjones/bot.service /etc/systemd/system/bot.service")

        dashboard_service = """[Unit]
Description=MaxFlash Dashboard
After=network.target

[Service]
User=devyjones
WorkingDirectory=/home/devyjones/MaxFlash
ExecStart=/usr/bin/python3 web_interface/app.py
Restart=always
Environment=PYTHONPATH=/home/devyjones/MaxFlash
Environment=FLASK_ENV=production

[Install]
WantedBy=multi-user.target
"""
        with open("dashboard.service", "w") as f:
            f.write(dashboard_service)

        print("Updating dashboard.service...")
        sftp.put("dashboard.service", "/home/devyjones/dashboard.service")
        ssh.exec_command(
            f"echo '{password}' | sudo -S mv /home/devyjones/dashboard.service /etc/systemd/system/dashboard.service"
        )

        sftp.close()

        print("Reloading systemd...")
        ssh.exec_command(f"echo '{password}' | sudo -S systemctl daemon-reload")

        print("Starting services...")
        ssh.exec_command(f"echo '{password}' | sudo -S systemctl start bot.service")
        ssh.exec_command(f"echo '{password}' | sudo -S systemctl start dashboard.service")

        time.sleep(5)

        print("\n--- Final Status ---")
        stdin, stdout, stderr = ssh.exec_command("systemctl status bot.service dashboard.service")
        print(stdout.read().decode())

        print("\n--- Network Ports ---")
        stdin, stdout, stderr = ssh.exec_command(f"echo '{password}' | sudo -S netstat -tulnp | grep python")
        print(stdout.read().decode())

        # Cleanup
        if os.path.exists("bot.service"):
            os.remove("bot.service")
        if os.path.exists("dashboard.service"):
            os.remove("dashboard.service")

    except Exception as e:
        print(f"Nuke failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    nuke_and_pave()
