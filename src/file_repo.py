"""Тестовый репозиторий: граф зависимостей в текстовом файле.

Формат: одна строка на пакет, имена — большие латинские буквы::

    A: B C
    B: C
    C:

Пустые строки и строки, начинающиеся с #, пропускаются.
"""

import re

from errors import RepositoryError

NAME_PATTERN = re.compile(r"[A-Z]+")
COMMENT_PREFIX = "#"


def parse_graph(text):
    """Разобрать описание графа: словарь пакет -> список зависимостей."""
    graph = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith(COMMENT_PREFIX):
            continue
        name, separator, rest = line.partition(":")
        name = name.strip()
        if not separator:
            raise RepositoryError(
                f"строка {number}: ожидалось 'ПАКЕТ: зависимости'")
        if name in graph:
            raise RepositoryError(
                f"строка {number}: пакет '{name}' описан повторно")
        graph[name] = parse_dependencies(name, rest, number)
    return graph


def parse_dependencies(name, text, number):
    """Проверить имена пакета и его зависимостей; убрать повторы."""
    names = [name] + text.split()
    for item in names:
        if not NAME_PATTERN.fullmatch(item):
            raise RepositoryError(
                f"строка {number}: имя '{item}' должно состоять из "
                "больших латинских букв")
    unique = []
    for dependency in names[1:]:
        if dependency not in unique:
            unique.append(dependency)
    return unique


def read_graph(path):
    """Прочитать файл тестового репозитория."""
    try:
        with open(path, encoding="utf-8") as file:
            return parse_graph(file.read())
    except FileNotFoundError as err:
        raise RepositoryError(f"файл не найден: {path}") from err
    except (OSError, UnicodeDecodeError) as err:
        raise RepositoryError(f"не удалось прочитать {path}: {err}") from err


class FileRepository:
    """Репозиторий, прочитанный из файла (версии не используются)."""

    def __init__(self, path):
        """Загрузить граф из файла."""
        self.graph = read_graph(path)

    def packages(self):
        """Все известные пакеты: описанные и упомянутые."""
        names = list(self.graph)
        for dependencies in self.graph.values():
            names += [name for name in dependencies if name not in names]
        return names

    def root_node(self, package, version):
        """Узел-корень; пакет должен быть в репозитории."""
        if package not in self.packages():
            raise RepositoryError(
                f"пакет '{package}' не найден в тестовом репозитории")
        return (package, None)

    def dependencies(self, node):
        """Прямые зависимости узла."""
        return [(name, None) for name in self.graph.get(node[0], [])]
