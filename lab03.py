"""
Лабораторная работа №3: Парсер настроек INI → JSON

Утилита читает конфигурационный файл в стиле INI (key = value),
автоматически определяет типы значений (int, float, bool, list, str)
и сохраняет результат в JSON-файл или выводит на экран.

Поддерживаются:
- Пропуск пустых строк и комментариев (начинающихся с #)
- Приведение bool: true/false, yes/no (регистронезависимо)
- Списки: значения, разделенные запятыми (например, "1,2,3" или "a, b, c")
- Числа: int и float
- Если тип не определен - остается строкой

Использование:
    python ini2json.py input.ini [output.json]
    python ini2json.py input.ini --indent 4          # вывод в stdout с отступом 4
    python ini2json.py input.ini output.json --indent 2
"""

import sys
import json
import argparse
from typing import Any


def detect_type(value_str: str) -> Any:
    """
    Определяет тип значения и возвращает объект соответствующего типа.

    Правила:
    - bool: true/false/yes/no (регистронезависимо)
    - int: если можно преобразовать в int
    - float: если можно преобразовать в float (и не int)
    - list: если содержит запятую (разбиваем, каждый элемент обрабатываем рекурсивно)
    - str: иначе
    """
    value_str = value_str.strip()
    if not value_str:
        return ""

    if ',' in value_str:
        items = [item.strip() for item in value_str.split(',')]
        return [detect_type(item) for item in items]

    lower_val = value_str.lower()
    if lower_val in ('true', 'yes'):
        return True
    if lower_val in ('false', 'no'):
        return False

    try:
        if '.' not in value_str and 'e' not in value_str.lower():
            return int(value_str)
        else:
            return float(value_str)
    except ValueError:
        pass

    return value_str


def parse_ini_line(line: str) -> tuple[str, str] | None:
    """
    Разбирает строку вида "key = value".
    Возвращает (key, value) или None, если строка невалидна.
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    if '=' not in line:
        return None
    key, val = line.split('=', 1)
    key = key.strip()
    val = val.strip()
    if not key:
        return None
    return key, val


def ini_to_dict(file_path: str) -> dict[str, Any]:
    """
    Читает INI-файл и преобразует в словарь с определением типов.
    """
    config = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            parsed = parse_ini_line(line)
            if parsed is None:
                continue
            key, val_str = parsed
            config[key] = detect_type(val_str)
    return config


def main():
    parser = argparse.ArgumentParser(
        description="Преобразование INI-файла (key=value) в JSON с автоматическим определением типов."
    )
    parser.add_argument('input', help="Входной INI-файл")
    parser.add_argument('output', nargs='?', help="Выходной JSON-файл (если не указан - вывод в stdout)")
    parser.add_argument('--indent', type=int, default=2, help="Отступ в JSON (по умолчанию 2)")

    args = parser.parse_args()

    try:
        data = ini_to_dict(args.input)
    except FileNotFoundError:
        print(f"Ошибка: файл '{args.input}' не найден.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=args.indent, ensure_ascii=False)
        print(f"Конфигурация сохранена в '{args.output}'")
    else:
        json_str = json.dumps(data, indent=args.indent, ensure_ascii=False)
        print(json_str)


if __name__ == "__main__":
    main()
