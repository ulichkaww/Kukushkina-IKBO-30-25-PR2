"""Обратные зависимости: какие пакеты зависят от заданного.

Используется тот же обход DFS, что и для прямых зависимостей
(graph.build_graph): репозиторий «переворачивается» адаптером,
у которого зависимостями узла служат пакеты, зависящие от него.
"""

import graph


class ReverseRepository:
    """Репозиторий с перевёрнутыми рёбрами (для обхода тем же DFS)."""

    def __init__(self, repository):
        """Построить таблицу «пакет -> пакеты, которые от него зависят»."""
        self.dependents = {}
        for node in repository.all_nodes():
            self.dependents.setdefault(node, [])
            for dep in repository.dependencies(node):
                users = self.dependents.setdefault(dep, [])
                if node not in users:
                    users.append(node)

    def dependencies(self, node):
        """«Зависимости» в перевёрнутом графе — зависящие пакеты."""
        return self.dependents.get(node, [])


def reverse_graph(reverse_repository, root, substring=""):
    """Обойти перевёрнутый граф алгоритмом DFS из предыдущего этапа."""
    return graph.build_graph(reverse_repository, root, substring)


def direct_dependents(result):
    """Пакеты, напрямую зависящие от заданного."""
    return list(result.edges[result.root])


def all_dependents(result):
    """Все пакеты, зависящие от заданного прямо или транзитивно."""
    return sorted(node for node in result.edges if node != result.root)


def join_labels(nodes):
    """Подписи узлов через запятую или «нет»."""
    return ", ".join(graph.label(node) for node in nodes) or "нет"


def report_lines(result, substring=""):
    """Текстовый отчёт об обратных зависимостях."""
    root = graph.label(result.root)
    lines = [f"Обратные зависимости {root} "
             f'(фильтр: "{substring}")',
             "Каждый пакет в дереве зависит от своего родителя:"]
    lines += graph.tree_lines(result)
    lines.append(f"Напрямую зависят от {root}: "
                 f"{join_labels(direct_dependents(result))}")
    lines.append(f"Зависят прямо или транзитивно: "
                 f"{join_labels(all_dependents(result))}")
    if result.excluded:
        lines.append("Не учтены из-за фильтра: "
                     f"{join_labels(result.excluded)}")
    for cycle in result.cycles:
        forward = graph.cycle_text(list(reversed(cycle)))
        lines.append(f"Циклическая зависимость: {forward}")
    return lines
