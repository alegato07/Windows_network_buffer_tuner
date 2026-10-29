#!/usr/bin/env python3
"""
Buffer Tuner — простой инструмент для просмотра и изменения
буферов сетевого адаптера в Windows.
Требует прав администратора для изменения настроек.
"""

import subprocess
import sys

def run_ps(command: str) -> str:
    """Выполняет PowerShell-команду и возвращает stdout."""
    try:
        # encoding="utf-8" и errors="replace" решают проблему с русскими символами
        # (кракозябрами) и падением UnicodeDecodeError в Windows.
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            # Если команда упала, выводим ошибку, но не крашим весь скрипт
            print(f"[!] PowerShell вернул ошибку:\n{result.stderr}", file=sys.stderr)
            return ""
        return result.stdout or ""
    except FileNotFoundError:
        print("[!] PowerShell не найден. Убедитесь, что вы запускаете это в Windows.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[!] Неизвестная ошибка при вызове PowerShell: {e}", file=sys.stderr)
        return ""

def list_adapters():
    """Возвращает список имён сетевых адаптеров."""
    output = run_ps("Get-NetAdapter | Select-Object -ExpandProperty Name")
    adapters = [line.strip() for line in output.splitlines() if line.strip()]
    if not adapters:
        print("[!] Не найдено ни одного сетевого адаптера (или нет прав администратора).")
        sys.exit(1)
    return adapters

def show_buffers(adapter_name: str):
    """Показывает текущие значения буферов для адаптера."""
    print(f"\n--- Текущие настройки буферов для: {adapter_name} ---")
    cmd = (
        f'Get-NetAdapterAdvancedProperty -Name "{adapter_name}" | '
        f'Where-Object {{ $_.DisplayName -match "Buffer" }} | '
        f'Format-Table DisplayName, DisplayValue -AutoSize'
    )
    output = run_ps(cmd)
    if output.strip():
        print(output)
    else:
        print("Параметры с 'Buffer' в названии не найдены.")
        print("Возможно, драйвер этого адаптера не предоставляет такие настройки в 'Дополнительно'.")

def set_buffer(adapter_name: str, display_name: str, value: str) -> bool:
    """Устанавливает значение advanced property."""
    cmd = (
        f'Set-NetAdapterAdvancedProperty -Name "{adapter_name}" '
        f'-DisplayName "{display_name}" -DisplayValue "{value}" -ErrorAction SilentlyContinue'
    )
    print(f"  -> Установка {display_name} = {value} ... ", end="", flush=True)
    
    # Запускаем команду
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    
    if result.returncode == 0 and not result.stderr.strip():
        print("OK")
        return True
    else:
        print("ОШИБКА (возможно, недопустимое значение или нет прав)")
        return False

def main():
    print("=" * 50)
    print("  Windows Network Buffer Tuner")
    print("=" * 50)
    
    # Проверка на права администратора (по желанию, но полезно)
    import ctypes
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("\n[!] ВНИМАНИЕ: Вы запустили скрипт без прав администратора.")
        print("    Просмотр может работать, но ИЗМЕНЕНИЕ настроек - нет.")

    adapters = list_adapters()
    print("\nДоступные сетевые адаптеры:")
    for i, name in enumerate(adapters, 1):
        print(f"  {i}. {name}")

    try:
        choice = int(input("\nВыберите номер адаптера: ").strip())
        adapter = adapters[choice - 1]
    except (ValueError, IndexError):
        print("Неверный выбор.")
        sys.exit(1)

    show_buffers(adapter)

       # Спрашиваем, хочет ли пользователь изменить
    print("\nДоступные варианты буферов (рекомендуется 2048 или 4096):")
    print("  1. 1024 (мало, но безопасно)")
    print("  2. 2048 (оптимально)")
    print("  3. 4096 (для высоких нагрузок)")
    
    choice_buf = input("Выберите вариант [1/2/3] (или Enter для отмены): ").strip()
    
    if choice_buf == "1":
        val = "1024"
    elif choice_buf == "2":
        val = "2048"
    elif choice_buf == "3":
        val = "4096"
    else:
        print("Выход без изменений.")
        return

    # Пробуем установить оба буфера с выбранным значением
    success_rx = set_buffer(adapter, "Receive Buffers", val)
    success_tx = set_buffer(adapter, "Transmit Buffers", val)

    if success_rx or success_tx:
        print(f"\nИзменения применены (значение: {val}). Проверьте результат:")

    if success_rx or success_tx:
        print("\nИзменения применены. Проверьте результат:")
        show_buffers(adapter)
        print("\nПримечание: некоторым сетевым картам требуется перезагрузка для применения настроек.")
    else:
        print("\n[!] Не удалось изменить ни один буфер. Проверьте права администратора и названия параметров.")

if __name__ == "__main__":
    main()
