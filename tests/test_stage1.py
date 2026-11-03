"""Тесты этапа 1: конфигурация YAML и проверка параметров."""

import os
import unittest

import helpers
import depgraph
import settings
import yaml_config
from errors import ConfigError

GOOD = {
    "package": "A",
    "repository": helpers.path("tests", "repos", "tree.txt"),
    "test_mode": True,
    "version": "1.0.0",
    "filter": "",
}


def good(**changes):
    """Корректная конфигурация с изменениями."""
    data = dict(GOOD)
    data.update(changes)
    return data


class YamlTest(unittest.TestCase):
    """Разбор YAML."""

    def test_scalars(self):
        """Строки, кавычки, булевы значения, пустое значение."""
        text = ("a: text\nb: \"q # not comment\"\nc: yes\nd: false\n"
                "e:\nf: 'x'  # comment\n# full comment\n")
        self.assertEqual(yaml_config.parse_yaml(text), {
            "a": "text", "b": "q # not comment", "c": True, "d": False,
            "e": None, "f": "x"})

    def test_errors(self):
        """Некорректный YAML сообщается как ConfigError."""
        bad = ["no colon", "a: 'open", "a: 1\na: 2", "a:\n  b: 1",
               "- item", "1bad: x"]
        for text in bad:
            with self.assertRaises(ConfigError, msg=text):
                yaml_config.parse_yaml(text)

    def test_missing_file(self):
        """Файл конфигурации не найден."""
        with self.assertRaises(ConfigError):
            yaml_config.load_yaml(helpers.path("nofile.yaml"))


class SettingsTest(unittest.TestCase):
    """Проверка значений параметров."""

    def test_valid(self):
        """Корректная конфигурация принимается."""
        result = settings.build_settings(good())
        self.assertEqual(result.package, "A")
        self.assertTrue(result.test_mode)

    def test_valid_url_mode(self):
        """Режим реального репозитория: URL."""
        data = good(test_mode=False, repository="https://index.crates.io")
        self.assertEqual(settings.build_settings(data).repository,
                         "https://index.crates.io")

    def test_each_parameter_error(self):
        """Ошибка для каждого параметра."""
        bad = [
            good(package=""), good(package="bad name"), good(package=5),
            good(package="x" * 65),
            good(repository=""), good(repository="nofile.txt"),
            good(repository=helpers.path("tests")),
            good(test_mode=False), good(test_mode="yes"),
            good(test_mode=None),
            good(version=""), good(version="1.0"), good(version="latest"),
            good(filter=True), good(filter="a\nb"),
        ]
        for data in bad:
            with self.assertRaises(ConfigError, msg=str(data)):
                settings.build_settings(data)

    def test_missing_and_unknown_keys(self):
        """Лишние и пропущенные ключи."""
        data = good()
        del data["version"]
        with self.assertRaises(ConfigError):
            settings.build_settings(data)
        with self.assertRaises(ConfigError):
            settings.build_settings(good(extra="1"))

    def test_describe(self):
        """Вывод всех параметров в формате ключ-значение."""
        lines = settings.describe(settings.build_settings(good()))
        self.assertEqual(len(lines), len(settings.CONFIG_KEYS))
        self.assertIn("test_mode: true", lines)
        self.assertIn('filter: ""', lines)


class CliTest(unittest.TestCase):
    """Запуск из командной строки."""

    def test_prints_parameters(self):
        """Параметры выводятся при запуске."""
        path = helpers.path("configs", "test_tree.yaml")
        cwd = os.getcwd()
        os.chdir(helpers.ROOT)
        try:
            code, out, _ = helpers.run_main(
                depgraph.main, ["--config", path, "--action", "config"])
        finally:
            os.chdir(cwd)
        self.assertEqual(code, depgraph.EXIT_OK)
        self.assertIn("package: A", out)

    def test_error_exit_code(self):
        """Ошибка конфигурации: код 2 и сообщение в stderr."""
        path = helpers.path("tests", "configs", "bad_version.yaml")
        code, out, err = helpers.run_main(depgraph.main, ["--config", path])
        self.assertEqual(code, depgraph.EXIT_ERROR)
        self.assertEqual(out, "")
        self.assertIn("version", err)


if __name__ == "__main__":
    unittest.main()
