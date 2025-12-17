#!/usr/bin/env python3
"""Запуск оптимизации confidence на сервере."""

import paramiko
import sys

SERVER = "192.168.0.203"
PORT = 22
USER = "devyjones"
PASSWORD = "19Maxon91!"
REMOTE_PATH = "/home/devyjones/MaxFlash"


def main():
    print("=" * 60)
    print("ОПТИМИЗАЦИЯ ПОРОГА CONFIDENCE")
    print("=" * 60)
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER, port=PORT, username=USER, password=PASSWORD, timeout=30)
        print("[OK] Подключено к серверу\n")
        
        stdin, stdout, stderr = ssh.exec_command("which python3 python 2>/dev/null | head -1")
        python_cmd = stdout.read().decode().strip() or "python3"
        
        command = f"cd {REMOTE_PATH} && {python_cmd} scripts/find_optimal_confidence.py"
        
        stdin, stdout, stderr = ssh.exec_command(command)
        
        while True:
            line = stdout.readline()
            if not line:
                break
            try:
                print(line.rstrip())
            except:
                pass
        
        ssh.close()
        
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

