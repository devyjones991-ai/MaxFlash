"""
Скрипт для запуска тестов.
"""
import subprocess
import sys

if __name__ == "__main__":
    result = subprocess.run(
        ["pytest", "tests/", "-v", "--cov=app", "--cov=services"],
        cwd=".",
    )
    sys.exit(result.returncode)

