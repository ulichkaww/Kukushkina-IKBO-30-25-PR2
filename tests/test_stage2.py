"""Тесты этапа 2: сбор прямых зависимостей из индекса Cargo."""

import os
import unittest

import helpers
import cargo_features
import cargo_index
import depgraph
from errors import RepositoryError


class IndexPathTest(unittest.TestCase):
    """Пути файлов в индексе."""

    def test_paths(self):
        """Правила crates.io для имён разной длины."""
        expected = {"a": "1/a", "io": "2/io", "log": "3/l/log",
                    "serde": "se/rd/serde", "Tokio": "to/ki/tokio"}
        for name, path in expected.items():
            self.assertEqual(cargo_index.index_path(name), path)


class FeaturesTest(unittest.TestCase):
    """Необязательные зависимости, включённые по умолчанию."""

    def test_default_chain(self):
        """default -> fast -> необязательная зависимость."""
        features = {"default": ["fast"], "fast": ["opt"], "full": ["extra"]}
        result = cargo_features.enabled_optional(features, {"opt", "extra"})
        self.assertEqual(result, {"opt"})

    def test_dep_syntax(self):
        """Синтаксис dep:name и name/feature."""
        features = {"default": ["dep:a", "b/serde", "c?/serde"]}
        result = cargo_features.enabled_optional(features, {"a", "b", "c"})
        self.assertEqual(result, {"a", "b"})

    def test_no_default(self):
        """Без feature default ничего не включено."""
        self.assertEqual(cargo_features.enabled_optional({}, {"a"}), set())


ENTRY_LINE = ('{"name":"x","vers":"1.0.0","deps":[{"name":"a","req":"^1",'
              '"features":[],"optional":false,"default_features":true,'
              '"target":null,"kind":null}],"cksum":"0","features":{},'
              '"features2":{"f":["dep:a"]},"yanked":false}')


class ParseTest(unittest.TestCase):
    """Разбор строк индекса."""

    def test_entry(self):
        """Поля записи; kind null — обычная зависимость."""
        entry = cargo_index.parse_entry(ENTRY_LINE)
        self.assertEqual(str(entry.version), "1.0.0")
        self.assertEqual(entry.deps[0].kind, "normal")
        self.assertIn("f", entry.features)

    def test_bad_lines(self):
        """Некорректные данные индекса."""
        for line in ("not json", "{}", '{"name":"x","vers":"bad"}',
                     '{"name":"x","vers":"1.0.0","deps":[{"req":"1"}]}'):
            with self.assertRaises(RepositoryError, msg=line):
                cargo_index.parse_entry(line)


class RepositoryTest(unittest.TestCase):
    """Репозиторий по HTTP (локальный сервер с учебным реестром)."""

    def test_direct_dependencies(self):
        """Прямые зависимости: только нужные виды."""
        with helpers.registry_url() as url:
            repo = cargo_index.CargoRepository(url)
            deps = repo.direct_dependencies("app", "1.0.0")
        self.assertEqual([d.package for d in deps],
                         ["libx", "util", "opt-speed", "tiny-json"])

    def test_excluded_kinds(self):
        """dev, build, платформенные и выключенные необязательные."""
        with helpers.registry_url() as url:
            deps = cargo_index.CargoRepository(url).direct_dependencies(
                "app", "1.0.0")
        names = {d.package for d in deps}
        for hidden in ("testing", "builder", "winapi", "extra"):
            self.assertNotIn(hidden, names)

    def test_resolve(self):
        """Наибольшая подходящая версия без yanked и пред-версий."""
        with helpers.registry_url() as url:
            repo = cargo_index.CargoRepository(url)
            found = {req: str(repo.resolve(name, req).version)
                     for name, req in (("libx", "^1.0"), ("libx", "^2"),
                                       ("util", "~0.2.1"))}
        self.assertEqual(found["^1.0"], "1.2.0")
        self.assertEqual(found["^2"], "2.0.0")
        self.assertEqual(found["~0.2.1"], "0.2.9")

    def test_errors(self):
        """Нет пакета, версии, подходящей версии."""
        with helpers.registry_url() as url:
            repo = cargo_index.CargoRepository(url)
            for call in (
                    lambda: repo.direct_dependencies("nosuch", "1.0.0"),
                    lambda: repo.direct_dependencies("app", "7.7.7"),
                    lambda: repo.resolve("libx", "^9"),
                    lambda: repo.resolve("libx", "bad")):
                with self.assertRaises(RepositoryError):
                    call()

    def test_connection_error(self):
        """Недоступный сервер."""
        repo = cargo_index.CargoRepository("http://127.0.0.1:1")
        with self.assertRaises(RepositoryError):
            repo.direct_dependencies("app", "1.0.0")


class CliTest(unittest.TestCase):
    """Вывод прямых зависимостей из командной строки."""

    def test_output(self):
        """Команда печатает зависимости заданной версии."""
        config = helpers.path("tests", "tmp_stage2.yaml")
        self.addCleanup(lambda: os.path.exists(config) and os.remove(config))
        with helpers.registry_url() as url:
            with open(config, "w", encoding="utf-8") as file:
                file.write(f"package: app\nrepository: {url}\n"
                           "test_mode: false\nversion: 1.0.0\nfilter: ''\n")
            code, out, _ = helpers.run_main(
                depgraph.main, ["--config", config, "--action", "direct"])
        self.assertEqual(code, depgraph.EXIT_OK)
        self.assertIn("libx 1.2.0", out)
        self.assertIn("tiny-json 0.5.3", out)


if __name__ == "__main__":
    unittest.main()
