"""Тесты этапа 5: диаграмма Mermaid и изображение."""

import base64
import os
import tempfile
import unittest
import urllib.error
from unittest import mock

import helpers
import depgraph
import file_repo
import graph
import mermaid
import render

REPOS = helpers.path("tests", "repos")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def build(name, root="A", substring=""):
    """Граф для файла тестового репозитория."""
    repository = file_repo.FileRepository(os.path.join(REPOS, name))
    return graph.build_graph(repository, (root, None), substring)


class FakeResponse:
    """Подмена ответа urlopen."""

    def __init__(self, body):
        """Запомнить тело ответа."""
        self.body = body

    def __enter__(self):
        """Вход в контекст."""
        return self

    def __exit__(self, *args):
        """Выход из контекста."""

    def read(self):
        """Тело ответа."""
        return self.body


class MermaidTextTest(unittest.TestCase):
    """Текст диаграммы."""

    def test_tree(self):
        """Узлы, рёбра и выделение корня."""
        lines = mermaid.mermaid_lines(build("tree.txt"))
        self.assertEqual(lines[0], "graph TD")
        self.assertIn('    n0["A"]', lines)
        self.assertIn("    n0 --> n1", lines)
        self.assertEqual(lines[-1], "    class n0 root")
        self.assertEqual(sum("-->" in line for line in lines), 3)

    def test_cycle_edge_is_dashed(self):
        """Ребро, замыкающее цикл, рисуется пунктиром."""
        lines = mermaid.mermaid_lines(build("cycle.txt"))
        self.assertIn("    n2 -.-> n0", lines)
        self.assertEqual(sum("-.->" in line for line in lines), 1)

    def test_shared_dependency_is_one_node(self):
        """Общая зависимость — один узел с двумя входящими рёбрами."""
        lines = mermaid.mermaid_lines(build("diamond.txt"))
        nodes = [line for line in lines if '["' in line]
        self.assertEqual(len(nodes), 5)
        self.assertEqual(sum(line.endswith("n2") for line in lines), 2)

    def test_filter_removes_nodes(self):
        """Исключённые фильтром пакеты не попадают на диаграмму."""
        text = mermaid.mermaid_text(build("filter.txt", "A", "B"))
        self.assertNotIn('"BA"', text)
        self.assertNotIn('"BB"', text)

    def test_escape(self):
        """Кавычки в подписи экранируются."""
        self.assertEqual(mermaid.escape_label('a"b'), "a#quot;b")


class RenderTest(unittest.TestCase):
    """Получение изображения без доступа в интернет (подмена сети)."""

    def test_ink_url_contains_text(self):
        """Адрес сервиса содержит закодированный текст диаграммы."""
        url = render.ink_url("graph TD\n  A-->B\n")
        code = url[len(render.INK_URL):].split("?")[0]
        self.assertEqual(base64.urlsafe_b64decode(code).decode("utf-8"),
                         "graph TD\n  A-->B\n")

    def test_render_saves_png_and_text(self):
        """Сохраняются изображение и .mmd."""
        with tempfile.TemporaryDirectory() as folder:
            png = os.path.join(folder, "sub", "g.png")
            with mock.patch("urllib.request.urlopen",
                            return_value=FakeResponse(PNG_SIGNATURE)):
                result = render.render_image("graph TD\n", png)
            self.assertEqual(result.read_bytes(), PNG_SIGNATURE)
            mmd = os.path.join(folder, "sub", "g.mmd")
            self.assertEqual(open(mmd, encoding="utf-8").read(),
                             "graph TD\n")

    def test_network_error(self):
        """Нет сети: понятная ошибка, текст диаграммы сохранён."""
        with tempfile.TemporaryDirectory() as folder:
            png = os.path.join(folder, "g.png")
            error = urllib.error.URLError("offline")
            with mock.patch("urllib.request.urlopen", side_effect=error):
                with self.assertRaises(render.RenderError) as caught:
                    render.render_image("graph TD\n", png)
            self.assertIn("mermaid.live", str(caught.exception))
            self.assertTrue(os.path.exists(os.path.join(folder, "g.mmd")))

    def test_http_error(self):
        """Сервис ответил ошибкой."""
        error = urllib.error.HTTPError("u", 400, "bad", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(render.RenderError):
                render.fetch_png("graph TD\n")

    def test_missing_mmdc(self):
        """Нет утилиты mmdc."""
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch("shutil.which", return_value=None):
                with self.assertRaises(render.RenderError):
                    render.render_image(
                        "graph TD\n", os.path.join(folder, "g.png"), "mmdc")


class CommandTest(unittest.TestCase):
    """Действия --action mermaid и --action image."""

    def test_mermaid_action(self):
        """Печатается текст диаграммы."""
        argv = ["--config", helpers.path("configs", "test_cycle.yaml"),
                "--action", "mermaid"]
        code, out, _ = helpers.run_main(depgraph.main, argv)
        self.assertEqual(code, depgraph.EXIT_OK)
        self.assertTrue(out.startswith("graph TD"))
        self.assertIn("-.->", out)

    def test_image_action(self):
        """Изображение сохраняется; --no-show не открывает просмотр."""
        with tempfile.TemporaryDirectory() as folder:
            png = os.path.join(folder, "out.png")
            argv = ["--config", helpers.path("configs", "test_big.yaml"),
                    "--action", "image", "--output", png, "--no-show"]
            with mock.patch("urllib.request.urlopen",
                            return_value=FakeResponse(PNG_SIGNATURE)):
                with mock.patch("render.show_image") as shown:
                    code, out, _ = helpers.run_main(depgraph.main, argv)
            self.assertEqual(code, depgraph.EXIT_OK)
            self.assertIn("Изображение графа:", out)
            self.assertTrue(os.path.exists(png))
            shown.assert_not_called()

    def test_image_is_shown(self):
        """Без --no-show изображение открывается."""
        with tempfile.TemporaryDirectory() as folder:
            png = os.path.join(folder, "out.png")
            argv = ["--config", helpers.path("configs", "test_tree.yaml"),
                    "--action", "image", "--output", png]
            with mock.patch("urllib.request.urlopen",
                            return_value=FakeResponse(PNG_SIGNATURE)):
                with mock.patch("render.show_image") as shown:
                    helpers.run_main(depgraph.main, argv)
            shown.assert_called_once()

    def test_image_error_exit_code(self):
        """Ошибка получения изображения даёт код 2."""
        with tempfile.TemporaryDirectory() as folder:
            argv = ["--config", helpers.path("configs", "test_tree.yaml"),
                    "--action", "image", "--no-show",
                    "--output", os.path.join(folder, "o.png")]
            error = urllib.error.URLError("offline")
            with mock.patch("urllib.request.urlopen", side_effect=error):
                code, _, err = helpers.run_main(depgraph.main, argv)
            self.assertEqual(code, depgraph.EXIT_ERROR)
            self.assertTrue(err.startswith("Ошибка:"))


if __name__ == "__main__":
    unittest.main()
