#!/usr/bin/env python3
"""
Интерактивный скрипт для настройки ClearML credentials.

Помогает пользователю настроить credentials для интеграции с ClearML:
- Проверяет статус ClearML сервисов
- Запрашивает credentials у пользователя
- Сохраняет их в .env файл
- Опционально применяет credentials в Kubernetes secret
"""

import os
import sys
from pathlib import Path


def main():
    """
    Интерактивно настраивает ClearML credentials.

    Процесс включает:
    1. Проверку статуса ClearML сервисов
    2. Инструкции по получению credentials из ClearML Web UI
    3. Запрос credentials у пользователя
    4. Сохранение в .env файл
    5. Опциональное применение в Kubernetes secret
    """
    print("=" * 50)
    print("Настройка ClearML Credentials")
    print("=" * 50)
    print()

    print("Проверка статуса ClearML сервисов...")

    import subprocess

    try:
        result = subprocess.run(
            [
                "docker",
                "compose",
                "ps",
                "clearml-webserver",
                "clearml-apiserver",
                "clearml-fileserver",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if "Up" in result.stdout:
            print("[OK] ClearML сервисы запущены")
        else:
            print("[WARN] ClearML сервисы не запущены или недоступны")
            print("Запустите сервисы:")
            print("  docker compose up -d clearml-webserver clearml-apiserver clearml-fileserver")
            print()
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        print(f"[WARN] Не удалось проверить статус контейнеров: {e}")
        print("Продолжаем настройку...")

    clearml_web_url = "http://localhost:8080"
    print()
    print(f"ClearML Web UI должен быть доступен по адресу: {clearml_web_url}")
    print("(или по IP вашего Docker хоста, если используете bridge сеть)")

    print()
    print("Для получения credentials:")
    print()
    print("1. Определите IP адрес вашего Docker хоста:")
    print("   - Если используете Docker Desktop: http://localhost:8080")
    print("   - Если используете Docker на удаленной машине: http://<IP_хоста>:8080")
    print("   - Если используете bridge сеть: используйте IP контейнера или проброшенный порт")
    print()
    print("2. Откройте ClearML Web UI в браузере")
    print("3. Зарегистрируйтесь или войдите")
    print("4. Перейдите в Settings -> Workspace Configuration")
    print("5. Нажмите 'Create new credentials'")
    print("6. Скопируйте access_key и secret_key")
    print()

    access_key = input("Введите CLEARML_ACCESS_KEY: ").strip()
    secret_key = input("Введите CLEARML_SECRET_KEY: ").strip()

    if not access_key or not secret_key:
        print("[ERROR] Access key и Secret key обязательны")
        sys.exit(1)

    env_file = Path(".env")
    env_content = ""

    if env_file.exists():
        env_content = env_file.read_text(encoding="utf-8")

    lines = env_content.split("\n")
    updated = False

    new_lines = []
    for line in lines:
        if line.startswith("CLEARML_ACCESS_KEY="):
            new_lines.append(f"CLEARML_ACCESS_KEY={access_key}")
            updated = True
        elif line.startswith("CLEARML_SECRET_KEY="):
            new_lines.append(f"CLEARML_SECRET_KEY={secret_key}")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        if new_lines and new_lines[-1]:
            new_lines.append("")
        new_lines.append("# ClearML Configuration")
        new_lines.append(f"CLEARML_ACCESS_KEY={access_key}")
        new_lines.append(f"CLEARML_SECRET_KEY={secret_key}")

    env_file.write_text("\n".join(new_lines), encoding="utf-8")

    print()
    print("[OK] Credentials сохранены в .env")
    print()

    print("Применить credentials в Kubernetes secret? (y/n): ", end="")
    try:
        apply_k8s = input().strip().lower()
        if apply_k8s in ["y", "yes", "да", "д"]:
            import subprocess

            script_path = Path(__file__).parent / "apply_clearml_secret.sh"
            if script_path.exists():
                print()
                print("Применение credentials в Kubernetes...")
                result = subprocess.run(
                    ["bash", str(script_path)],
                    cwd=Path(__file__).parent.parent,
                )
                if result.returncode == 0:
                    print("[OK] Credentials применены в Kubernetes")
                else:
                    print("[WARN] Не удалось применить credentials в Kubernetes")
                    print("      Выполните вручную: make clearml-apply-secret")
            else:
                print("[WARN] Скрипт apply_clearml_secret.sh не найден")
                print("      Выполните вручную: make clearml-apply-secret")
        else:
            print()
            print("Для применения в Kubernetes выполните:")
            print("  make clearml-apply-secret")
    except (KeyboardInterrupt, EOFError):
        print()
        print("Для применения в Kubernetes выполните:")
        print("  make clearml-apply-secret")
    print()


if __name__ == "__main__":
    main()
