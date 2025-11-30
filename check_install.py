import paramiko
import time

hostname = "192.168.0.204"
username = "devyjones"
password = "19Maxon91!"
port = 22


def check_install():
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, port=port, username=username, password=password)

        print("\n--- Check Dashboard Status ---")
        stdin, stdout, stderr = ssh.exec_command("systemctl status dashboard.service")
        print(stdout.read().decode())

        print("\n--- Check Bot Status ---")
        stdin, stdout, stderr = ssh.exec_command("systemctl status bot.service")
        print(stdout.read().decode())

        print("\n--- Verify Imports (as devyjones) ---")
        cmd = "python3 -c \"import dash; print('Dash OK'); import paramiko; print('Paramiko OK'); import ccxt; print('CCXT OK')\""
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print("STDOUT:", stdout.read().decode())
        print("STDERR:", stderr.read().decode())

        print("\n--- Verify Imports (as root) ---")
        cmd = f"echo '{password}' | sudo -S python3 -c \"import dash; print('Dash OK'); import paramiko; print('Paramiko OK')\""
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print("STDOUT:", stdout.read().decode())

    except Exception as e:
        print(f"Check failed: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    check_install()
