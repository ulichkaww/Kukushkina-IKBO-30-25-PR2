"""Инструмент визуализации графа зависимостей пакетов Cargo (вариант 16)."""

import argparse
import sys

import settings as settings_module
from cargo_index import CargoRepository
from errors import DepGraphError

EXIT_OK = 0
EXIT_ERROR = 2
DEFAULT_CONFIG = "config.yaml"
ACTIONS = ("config", "direct")
DEFAULT_ACTION = "direct"


def parse_args(argv):
    """Разобрать параметры командной строки."""
    parser = argparse.ArgumentParser(
        prog="depgraph",
        description="Граф зависимостей пакетов Cargo")
    parser.add_argument(
        "--config", default=DEFAULT_CONFIG,
        help=f"путь к YAML-конфигурации (по умолчанию {DEFAULT_CONFIG})")
    parser.add_argument(
        "--action", choices=ACTIONS, default=DEFAULT_ACTION,
        help="config — показать параметры, direct — прямые зависимости "
             f"(по умолчанию {DEFAULT_ACTION})")
    return parser.parse_args(argv)


def make_repository(settings):
    """Создать репозиторий по параметрам."""
    if settings.test_mode:
        raise DepGraphError(
            "режим тестового репозитория пока не поддерживается")
    return CargoRepository(settings.repository)


def show_direct(settings, repository):
    """Вывести прямые зависимости заданной версии пакета."""
    deps = repository.direct_dependencies(settings.package, settings.version)
    print(f"Прямые зависимости {settings.package} {settings.version}:")
    if not deps:
        print("  (нет)")
    for dep in deps:
        alias = f" (имя в манифесте: {dep.alias})" if (
            dep.alias != dep.package) else ""
        print(f"  {dep.package} {dep.req}{alias}")


def run(args):
    """Выполнить выбранное действие."""
    settings = settings_module.load_settings(args.config)
    if args.action == "config":
        print("\n".join(settings_module.describe(settings)))
    else:
        show_direct(settings, make_repository(settings))


def main(argv=None):
    """Точка входа: выполнить действие, ошибки показать пользователю."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    try:
        run(args)
    except DepGraphError as err:
        print(f"Ошибка: {err}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
