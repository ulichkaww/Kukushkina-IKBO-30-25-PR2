"""Тесты этапа 4: обратные зависимости."""

import os
import unittest

import helpers
import depgraph
import file_repo
import graph
import reverse

REPOS = helpers.path("tests", "repos")


def reverse_of(repo_name, target, substring=""):
    """Обратный граф для пакета target в файле tests/repos/repo_name."""
    repository = file_repo.FileRepository(os.path.join(REPOS, repo_name))
    inverted = reverse.ReverseRepository(repository)
    return reverse.reverse_graph(inverted, (target, None), substring)


def names(nodes):
    """Имена пакетов из списка узлов."""
    return [node[0] for node in nodes]


def run_config(*parts):
    """Запустить depgraph --action reverse с конфигурацией из tests/."""
    config = helpers.path(*parts)
    return helpers.run_main(
        depgraph.main, ["--config", config, "--action", "reverse"])


class ReverseGraphTest(unittest.TestCase):
    """Поиск пакетов, зависящих от заданного."""

    def test_chain(self):
        """Дерево: от D зависят B (напрямую) и A (через B)."""
        result = reverse_of("tree.txt", "D")
        self.assertEqual(names(reverse.direct_dependents(result)), ["B"])
        self.assertEqual(names(reverse.all_dependents(result)), ["A", "B"])

    def test_diamond(self):
        """Ромб: общий пакет учитывается один раз."""
        result = reverse_of("diamond.txt", "E")
        self.assertEqual(names(reverse.direct_dependents(result)), ["D"])
        self.assertEqual(names(reverse.all_dependents(result)),
                         ["A", "B", "C", "D"])

    def test_nobody_depends(self):
        """От корня пакета никто не зависит."""
        result = reverse_of("diamond.txt", "A")
        self.assertEqual(reverse.all_dependents(result), [])
        text = "\n".join(reverse.report_lines(result))
        self.assertIn("Напрямую зависят от A: нет", text)

    def test_cycle_does_not_hang(self):
        """Цикл найден и показан в прямом порядке зависимостей."""
        result = reverse_of("cycle.txt", "C")
        self.assertEqual(names(reverse.all_dependents(result)), ["A", "B"])
        text = "\n".join(reverse.report_lines(result))
        self.assertIn("Циклическая зависимость: C -> A -> B -> C", text)

    def test_self_dependency(self):
        """Пакет, зависящий от себя, считается своим потребителем."""
        result = reverse_of("self_cycle.txt", "A")
        self.assertEqual(names(reverse.direct_dependents(result)), ["A"])
        self.assertEqual(reverse.all_dependents(result), [])

    def test_filter(self):
        """Пакеты с подстрокой фильтра не учитываются."""
        result = reverse_of("filter.txt", "D", "B")
        self.assertEqual(names(reverse.all_dependents(result)), ["A", "C"])
        self.assertEqual(names(result.excluded), ["BA"])

    def test_same_result_as_forward_search(self):
        """Обратный обход согласован с прямым: X зависит от T."""
        forward = file_repo.FileRepository(
            os.path.join(REPOS, "big.txt"))
        target = ("K", None)
        result = reverse_of("big.txt", "K")
        for name in names(reverse.all_dependents(result)):
            from_name = graph.build_graph(
                forward, (name, None))
            self.assertIn(target, from_name.edges, name)


class ReverseCommandTest(unittest.TestCase):
    """Режим --action reverse."""

    def test_output(self):
        """Вывод содержит дерево и итоговые списки."""
        code, out, _ = run_config("configs", "reverse_diamond.yaml")
        self.assertEqual(code, depgraph.EXIT_OK)
        self.assertIn("Обратные зависимости E", out)
        self.assertIn("Напрямую зависят от E: D", out)
        self.assertIn("Зависят прямо или транзитивно: A, B, C, D", out)

    def test_all_demo_configs(self):
        """Все демонстрационные конфигурации выполняются."""
        folder = helpers.path("configs")
        for name in sorted(os.listdir(folder)):
            if name.startswith("reverse_"):
                code = run_config("configs", name)[0]
                self.assertEqual(code, depgraph.EXIT_OK, name)

    def test_errors(self):
        """Неизвестный пакет, исключённый корень, реальный реестр."""
        folder = helpers.path("tests", "reverse_configs")
        config_names = sorted(os.listdir(folder))
        self.assertEqual(len(config_names), 3)
        for name in config_names:
            code, _, err = run_config("tests", "reverse_configs", name)
            self.assertEqual(code, depgraph.EXIT_ERROR, name)
            self.assertTrue(err.startswith("Ошибка:"), name)

    def test_real_registry_is_not_supported(self):
        """Для crates.io сообщается причина, сеть не нужна."""
        _, _, err = run_config("tests", "reverse_configs",
                               "real_registry.yaml")
        self.assertIn("только в тестовом режиме", err)


if __name__ == "__main__":
    unittest.main()
