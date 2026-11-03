"""Инструмент визуализации графа зависимостей пакетов Cargo (вариант 16)."""

import argparse
import sys

import settings as settings_module
from errors import DepGraphError

EXIT_OK = 0
EXIT_ERROR = 2
DEFAULT_CONFIG = "config.yaml"


def parse_args(argv):
    """Разобрать параметры командной строки."""
    parser = argparse.ArgumentParser(
        prog="depgraph",
        description="Граф зависимостей пакетов Cargo")
    parser.add_argument(
        "--config", default=DEFAULT_CONFIG,
        help=f"путь к YAML-конфигурации (по умолчанию {DEFAULT_CONFIG})")
    return parser.parse_args(argv)


def main(argv=None):
    """Точка входа: прочитать конфигурацию и вывести параметры."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    try:
        settings = settings_module.load_settings(args.config)
    except DepGraphError as err:
        print(f"Ошибка: {err}", file=sys.stderr)
        return EXIT_ERROR
    print("\n".join(settings_module.describe(settings)))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
