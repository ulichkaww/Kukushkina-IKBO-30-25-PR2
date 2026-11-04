"""Текстовое представление графа зависимостей на языке Mermaid."""

import graph as graph_module

HEADER = "graph TD"
ROOT_CLASS = "classDef root fill:#ffe9a8,stroke:#b58900,stroke-width:2px"
QUOTE_ESCAPE = "#quot;"


def node_ids(result):
    """Присвоить узлам безопасные идентификаторы n0, n1, ..."""
    return {node: f"n{index}" for index, node in enumerate(result.edges)}


def escape_label(text):
    """Экранировать кавычки в подписи узла."""
    return text.replace('"', QUOTE_ESCAPE)


def cycle_edges(result):
    """Рёбра, замыкающие циклы: они рисуются пунктиром."""
    return {(cycle[-2], cycle[-1]) for cycle in result.cycles}


def mermaid_lines(result):
    """Строки диаграммы: узлы с подписями, рёбра, выделение корня."""
    ids = node_ids(result)
    lines = [HEADER]
    for node, node_id in ids.items():
        label = escape_label(graph_module.label(node))
        lines.append(f'    {node_id}["{label}"]')
    closing = cycle_edges(result)
    for node, children in result.edges.items():
        for child in children:
            arrow = "-.->" if (node, child) in closing else "-->"
            lines.append(f"    {ids[node]} {arrow} {ids[child]}")
    lines.append(f"    {ROOT_CLASS}")
    lines.append(f"    class {ids[result.root]} root")
    return lines


def mermaid_text(result):
    """Диаграмма одной строкой текста."""
    return "\n".join(mermaid_lines(result)) + "\n"
