"""Граф зависимостей: обход DFS с рекурсией, фильтр, циклы."""

from dataclasses import dataclass, field

from errors import DepGraphError


@dataclass
class Graph:
    """Результат обхода: рёбра, найденные циклы, пропущенные пакеты."""

    root: tuple
    edges: dict = field(default_factory=dict)
    cycles: list = field(default_factory=list)
    excluded: list = field(default_factory=list)


def label(node):
    """Подпись узла: имя и версия (если есть)."""
    name, version = node
    return f"{name} {version}" if version else name


def is_excluded(node, substring):
    """Исключён ли пакет: имя содержит подстроку фильтра."""
    return bool(substring) and substring in node[0]


def build_graph(repository, root, substring=""):
    """Построить граф зависимостей алгоритмом DFS (рекурсивно).

    Пакеты, в имени которых есть substring, не учитываются. Узел
    помечается посещённым до обхода потомков, поэтому циклы не
    приводят к бесконечной рекурсии; найденный цикл записывается.
    """
    if is_excluded(root, substring):
        raise DepGraphError(
            f"корневой пакет '{root[0]}' исключён фильтром '{substring}'")
    graph = Graph(root)
    path = []

    def visit(node):
        """Обойти узел и его зависимости."""
        graph.edges[node] = []
        path.append(node)
        for dep in repository.dependencies(node):
            if is_excluded(dep, substring):
                if dep not in graph.excluded:
                    graph.excluded.append(dep)
                continue
            graph.edges[node].append(dep)
            if dep in path:
                graph.cycles.append(path[path.index(dep):] + [dep])
            elif dep not in graph.edges:
                visit(dep)
        path.pop()

    visit(root)
    return graph


def tree_lines(graph):
    """Дерево зависимостей: (*) — уже показано выше, (цикл) — предок."""
    lines = [label(graph.root)]
    shown = {graph.root}

    def walk(node, prefix, ancestors):
        """Добавить строки для зависимостей узла."""
        children = graph.edges[node]
        for index, child in enumerate(children):
            last = index == len(children) - 1
            branch = "└── " if last else "├── "
            mark = ""
            if child in ancestors:
                mark = " (цикл)"
            elif child in shown:
                mark = " (*)"
            lines.append(prefix + branch + label(child) + mark)
            if not mark:
                shown.add(child)
                extension = "    " if last else "│   "
                walk(child, prefix + extension, ancestors + [child])

    walk(graph.root, "", [graph.root])
    return lines


def edge_count(graph):
    """Число рёбер (зависимостей) в графе."""
    return sum(len(children) for children in graph.edges.values())


def cycle_text(cycle):
    """Запись цикла: A -> B -> A."""
    return " -> ".join(label(node) for node in cycle)


def report_lines(graph, substring=""):
    """Полный текстовый отчёт о графе."""
    lines = [f"Граф зависимостей {label(graph.root)} "
             f'(фильтр: "{substring}")']
    lines += tree_lines(graph)
    lines.append(f"Пакетов: {len(graph.edges)}, "
                 f"зависимостей: {edge_count(graph)}")
    if graph.excluded:
        names = ", ".join(label(node) for node in graph.excluded)
        lines.append(f"Не учтены из-за фильтра: {names}")
    for cycle in graph.cycles:
        lines.append(f"Циклическая зависимость: {cycle_text(cycle)}")
    return lines
