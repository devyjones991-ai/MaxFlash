import paramiko
import time

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def check_bot():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)

        print("\n--- Bot Status ---")
        stdin, stdout, stderr = ssh.exec_command("systemctl status bot.service")
        status = stdout.read().decode()
        print(status)

        if "Active: active (running)" not in status:
            print("Bot is not running. Restarting...")
            ssh.exec_command(f"echo '{password}' | sudo -S systemctl restart bot.service")
            time.sleep(5)
            stdin, stdout, stderr = ssh.exec_command("systemctl status bot.service")
            print(stdout.read().decode())
        else:
            print("Bot is running.")

    except Exception as e:
        print(f"Check failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    check_bot()
