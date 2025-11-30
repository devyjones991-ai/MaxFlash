import paramiko
import time

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def debug_runtime():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)

        print("\n--- Killing Port 8502 ---")
        # Find PID using netstat/lsof/fuser and kill it
        # Using fuser is easiest if installed, otherwise netstat+awk+kill
        cmd = f"echo '{password}' | sudo -S fuser -k 8502/tcp"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode())
        print(stderr.read().decode())

        print("\n--- Listing Log Files ---")
        stdin, stdout, stderr = ssh.exec_command("ls -lt logs/")
        print(stdout.read().decode())

        print("\n--- Fetching Latest Log Content (Last 100 lines) ---")
        # Get the most recent log file
        cmd = "ls -t logs/trading_system_*.log | head -n 1 | xargs tail -n 100"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode())

    except Exception as e:
        print(f"Debug failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    debug_runtime()
