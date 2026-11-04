"""Инструмент визуализации графа зависимостей пакетов Cargo (вариант 16)."""

import argparse
import sys

import graph as graph_module
import settings as settings_module
from cargo_index import CargoRepository
from errors import DepGraphError
from file_repo import FileRepository

EXIT_OK = 0
EXIT_ERROR = 2
DEFAULT_CONFIG = "config.yaml"
ACTIONS = ("config", "direct", "graph")
DEFAULT_ACTION = "graph"


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
        help="config — параметры, direct — прямые зависимости, "
             f"graph — граф с транзитивными (по умолчанию {DEFAULT_ACTION})")
    return parser.parse_args(argv)


def make_repository(settings):
    """Создать репозиторий: тестовый файл или реестр по URL."""
    if settings.test_mode:
        return FileRepository(settings.repository)
    return CargoRepository(settings.repository)


def show_direct(settings, repository):
    """Вывести прямые зависимости заданной версии пакета."""
    root = repository.root_node(settings.package, settings.version)
    deps = repository.dependencies(root)
    print(f"Прямые зависимости {graph_module.label(root)}:")
    if not deps:
        print("  (нет)")
    for dep in deps:
        print(f"  {graph_module.label(dep)}")


def show_graph(settings, repository):
    """Построить граф зависимостей (DFS) и вывести отчёт."""
    root = repository.root_node(settings.package, settings.version)
    graph = graph_module.build_graph(repository, root, settings.filter)
    print("\n".join(graph_module.report_lines(graph, settings.filter)))


def run(args):
    """Выполнить выбранное действие."""
    settings = settings_module.load_settings(args.config)
    if args.action == "config":
        print("\n".join(settings_module.describe(settings)))
        return
    repository = make_repository(settings)
    if args.action == "direct":
        show_direct(settings, repository)
    else:
        show_graph(settings, repository)


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
