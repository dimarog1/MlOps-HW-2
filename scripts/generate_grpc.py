"""
Скрипт для генерации Python кода из gRPC proto файлов.

Использует protoc компилятор для генерации Python классов из определения
gRPC сервиса в файле ml_service.proto.
"""

import subprocess
import sys
from pathlib import Path


def main():
    """
    Генерирует Python файлы из proto определения gRPC сервиса.

    Выполняет команду protoc для генерации:
    - ml_service_pb2.py - Python классы для сообщений
    - ml_service_pb2_grpc.py - Python классы для gRPC сервиса и клиента

    Raises:
        SystemExit: Если proto файл не найден или генерация не удалась
    """
    proto_file = Path("app/grpc_service/ml_service.proto")

    if not proto_file.exists():
        print(f"[ERROR] proto file not found: {proto_file}")
        sys.exit(1)

    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"-I{proto_file.parent}",
        f"--python_out={proto_file.parent}",
        f"--grpc_python_out={proto_file.parent}",
        str(proto_file),
    ]

    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("[OK] gRPC files generated successfully")
    else:
        print("[ERROR] Failed to generate gRPC files")
        sys.exit(1)


if __name__ == "__main__":
    main()
