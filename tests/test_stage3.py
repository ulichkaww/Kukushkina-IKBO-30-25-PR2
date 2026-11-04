"""Тесты этапа 3: граф DFS, фильтр, циклы, тестовый репозиторий."""

import os
import unittest

import helpers
import cargo_index
import depgraph
import file_repo
import graph
from errors import DepGraphError, RepositoryError

REPOS = helpers.path("tests", "repos")
CHAIN_LENGTH = 300


def repo(name):
    """Тестовый репозиторий из tests/repos."""
    return file_repo.FileRepository(os.path.join(REPOS, name))


def build(name, root="A", substring=""):
    """Построить граф для файла тестового репозитория."""
    repository = repo(name)
    return graph.build_graph(repository, (root, None), substring)


def names(edges):
    """Словарь имя -> имена зависимостей (без версий)."""
    return {node[0]: [dep[0] for dep in deps]
            for node, deps in edges.items()}


class FileRepositoryTest(unittest.TestCase):
    """Разбор файла тестового репозитория."""

    def test_parse(self):
        """Пакеты, зависимости, комментарии, повторы."""
        text = "# c\nA: B C B\n\nB:\nC: A\n"
        self.assertEqual(file_repo.parse_graph(text),
                         {"A": ["B", "C"], "B": [], "C": ["A"]})

    def test_invalid_files(self):
        """Неверные файлы сообщают об ошибке."""
        folder = os.path.join(REPOS, "invalid")
        for name in sorted(os.listdir(folder)):
            if name == "empty.txt":
                continue
            with self.assertRaises(RepositoryError, msg=name):
                file_repo.read_graph(os.path.join(folder, name))

    def test_missing_file_and_package(self):
        """Нет файла, нет пакета."""
        with self.assertRaises(RepositoryError):
            file_repo.read_graph(os.path.join(REPOS, "nofile.txt"))
        with self.assertRaises(RepositoryError):
            repo("tree.txt").root_node("Z", "1.0.0")


class GraphTest(unittest.TestCase):
    """Построение графа."""

    def test_tree(self):
        """Дерево без повторов."""
        self.assertEqual(names(build("tree.txt").edges),
                         {"A": ["B", "C"], "B": ["D"], "C": [], "D": []})

    def test_diamond_visits_once(self):
        """Общая зависимость обходится один раз."""
        result = build("diamond.txt")
        self.assertEqual(len(result.edges), 5)
        self.assertEqual(graph.edge_count(result), 5)
        self.assertEqual(result.cycles, [])

    def test_cycle(self):
        """Цикл обнаружен, обход завершился."""
        result = build("cycle.txt")
        self.assertEqual([graph.cycle_text(c) for c in result.cycles],
                         ["A -> B -> C -> A"])
        self.assertEqual(len(result.edges), 4)

    def test_self_cycle(self):
        """Пакет зависит от самого себя."""
        result = build("self_cycle.txt")
        self.assertEqual([graph.cycle_text(c) for c in result.cycles],
                         ["A -> A"])

    def test_two_cycles(self):
        """Несколько циклов в большом графе."""
        result = build("big.txt")
        texts = [graph.cycle_text(c) for c in result.cycles]
        self.assertEqual(texts, ["B -> E -> H -> J -> B",
                                 "A -> C -> F -> A"])
        self.assertEqual(len(result.edges), 11)

    def test_root_only_reachable(self):
        """Несвязанные пакеты не попадают в граф."""
        self.assertEqual(sorted(names(build("disconnected.txt").edges)),
                         ["A", "B"])

    def test_other_root(self):
        """Граф можно строить от любого пакета."""
        self.assertEqual(sorted(names(build("tree.txt", "B").edges)),
                         ["B", "D"])

    def test_deep_chain(self):
        """Длинная цепочка обходится рекурсивно без ошибок."""
        class Chain:
            """Длинная цепочка пакетов."""

            def dependencies(self, node):
                """Следующий пакет цепочки."""
                number = int(node[0])
                if number >= CHAIN_LENGTH:
                    return []
                return [(str(number + 1), None)]

        result = graph.build_graph(Chain(), ("0", None))
        self.assertEqual(len(result.edges), CHAIN_LENGTH + 1)


class FilterTest(unittest.TestCase):
    """Фильтр по подстроке."""

    def test_filter_skips_packages(self):
        """Пакеты с подстрокой не учитываются, остальные остаются."""
        result = build("filter.txt", substring="B")
        self.assertEqual(names(result.edges),
                         {"A": ["C"], "C": ["D"], "D": []})
        self.assertEqual([n[0] for n in result.excluded], ["BA", "BB"])

    def test_filter_absent(self):
        """Пустая подстрока ничего не исключает."""
        self.assertEqual(len(build("filter.txt").edges), 6)

    def test_filter_no_match(self):
        """Подстрока, которой нет в именах."""
        self.assertEqual(len(build("filter.txt", substring="ZZ").edges), 6)

    def test_root_excluded(self):
        """Корень, исключённый фильтром, — ошибка."""
        with self.assertRaises(DepGraphError):
            build("tree.txt", substring="A")


class ReportTest(unittest.TestCase):
    """Текстовый вывод."""

    def test_tree_marks(self):
        """Маркеры повторов (*) и циклов."""
        lines = graph.tree_lines(build("diamond.txt"))
        self.assertIn("    └── D (*)", lines)
        cycle_lines = graph.tree_lines(build("cycle.txt"))
        self.assertIn("        ├── A (цикл)", cycle_lines)

    def test_report(self):
        """Сводка: число пакетов, рёбер, циклы, фильтр."""
        text = "\n".join(graph.report_lines(
            build("filter.txt", substring="B"), "B"))
        self.assertIn("Пакетов: 3, зависимостей: 2", text)
        self.assertIn("Не учтены из-за фильтра: BA, BB", text)


class CargoGraphTest(unittest.TestCase):
    """Транзитивный граф реального формата (учебный реестр)."""

    def test_graph_over_http(self):
        """Версии разрешаются по требованиям; фильтр работает."""
        with helpers.registry_url() as url:
            repository = cargo_index.CargoRepository(url)
            root = repository.root_node("app", "1.0.0")
            full = graph.build_graph(repository, root)
            part = graph.build_graph(repository, root, "core")
        self.assertEqual(
            names(full.edges)["util"], ["core-lib", "libx"])
        self.assertIn(("core-lib", "0.1.7"), full.edges)
        self.assertEqual(len(full.edges), 6)
        self.assertNotIn(("core-lib", "0.1.7"), part.edges)


class CliTest(unittest.TestCase):
    """Запуск из командной строки."""

    def run_config(self, *parts, action="graph"):
        """Запустить depgraph с конфигурацией из корня проекта."""
        os.chdir(helpers.ROOT)
        return helpers.run_main(
            depgraph.main, ["--config", os.path.join(*parts),
                            "--action", action])

    def test_graph_output(self):
        """Граф тестового репозитория выводится."""
        code, out, _ = self.run_config("configs", "test_cycle.yaml")
        self.assertEqual(code, depgraph.EXIT_OK)
        self.assertIn("A -> B -> C -> A", out)

    def test_direct_in_test_mode(self):
        """Прямые зависимости в тестовом режиме."""
        code, out, _ = self.run_config(
            "configs", "test_tree.yaml", action="direct")
        self.assertEqual(code, depgraph.EXIT_OK)
        self.assertIn("  B", out)
        self.assertIn("  C", out)

    def test_errors(self):
        """Ошибки репозитория и фильтра: код 2."""
        folder = os.path.join(helpers.ROOT, "tests", "graph_configs")
        for name in sorted(os.listdir(folder)):
            code, _, err = self.run_config("tests", "graph_configs", name)
            self.assertEqual(code, depgraph.EXIT_ERROR, name)
            self.assertTrue(err.startswith("Ошибка:"), name)


if __name__ == "__main__":
    unittest.main()
