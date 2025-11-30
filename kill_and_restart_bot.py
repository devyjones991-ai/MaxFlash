import paramiko
import time

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def kill_and_restart_bot():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)

        print("Killing duplicate bots...")
        ssh.exec_command(f"echo '{password}' | sudo -S pkill -f run_bot.py")
        ssh.exec_command(f"echo '{password}' | sudo -S pkill -f start_bot_server.py")
        time.sleep(2)

        print("Restarting Bot...")
        ssh.exec_command(f"echo '{password}' | sudo -S systemctl restart bot.service")
        time.sleep(5)

        print("\n--- Bot Status ---")
        stdin, stdout, stderr = ssh.exec_command("systemctl status bot.service")
        print(stdout.read().decode())

        print("\n--- Bot Logs (Last 20) ---")
        stdin, stdout, stderr = ssh.exec_command(
            f"echo '{password}' | sudo -S journalctl -u bot.service -n 20 --no-pager"
        )
        print(stdout.read().decode())

    except Exception as e:
        print(f"Fix failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    kill_and_restart_bot()
