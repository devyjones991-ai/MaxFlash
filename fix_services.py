import paramiko
import os
import time

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def fix_services():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)
        sftp = ssh.open_sftp()

        # 1. Upload run_bot.py and app.py
        print("Uploading run_bot.py...")
        sftp.put("run_bot.py", "/home/devyjones/MaxFlash/run_bot.py")

        print("Uploading app.py...")
        sftp.put("web_interface/app.py", "/home/devyjones/MaxFlash/web_interface/app.py")

        # 2. Fix Bot Service
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

        # 3. Fix Dashboard Service (Ensure correct path)
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

        # 4. Reload and Restart
        print("Reloading systemd...")
        ssh.exec_command(f"echo '{password}' | sudo -S systemctl daemon-reload")

        print("Restarting services...")
        ssh.exec_command(f"echo '{password}' | sudo -S systemctl restart bot.service")
        ssh.exec_command(f"echo '{password}' | sudo -S systemctl restart dashboard.service")

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
        print(f"Fix failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    fix_services()
