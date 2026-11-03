"""Тесты версий и требований semver."""

import unittest

import helpers
import semver

CASES = [
    ("^1.2.3", "1.2.3", True), ("^1.2.3", "1.9.0", True),
    ("^1.2.3", "2.0.0", False), ("^1.2.3", "1.2.2", False),
    ("1.2", "1.9.9", True), ("1", "2.0.0", False),
    ("^0.2.3", "0.2.9", True), ("^0.2.3", "0.3.0", False),
    ("^0.0.3", "0.0.3", True), ("^0.0.3", "0.0.4", False),
    ("^0", "0.9.9", True), ("^0", "1.0.0", False),
    ("~1.2.3", "1.2.9", True), ("~1.2.3", "1.3.0", False),
    ("~1", "1.9.0", True), ("~1", "2.0.0", False),
    ("=1.2.3", "1.2.3", True), ("=1.2.3", "1.2.4", False),
    ("=1.2", "1.2.7", True), ("=1.2", "1.3.0", False),
    (">=1.2.3, <1.8.0", "1.5.0", True), (">=1.2.3, <1.8.0", "1.8.0", False),
    (">1.2.3", "1.2.3", False), (">1.2.3", "1.2.4", True),
    (">1.2", "1.2.9", False), (">1.2", "1.3.0", True),
    ("<=1.2", "1.2.9", True), ("<=1.2", "1.3.0", False),
    ("<1.2", "1.1.9", True), ("<1.2", "1.2.0", False),
    ("*", "5.5.5", True), ("1.*", "1.7.0", True), ("1.*", "2.0.0", False),
    ("1.2.*", "1.2.8", True), ("1.2.*", "1.3.0", False),
    ("^1.0.0", "1.5.0-beta.1", False), ("^1.5.0-beta.1", "1.5.0", True),
    ("^1.5.0-beta.1", "1.5.0-beta.2", True),
    ("^1.5.0-beta.2", "1.5.0-beta.1", False),
]


class SemverTest(unittest.TestCase):
    """Версии и требования."""

    def test_sources_available(self):
        """Модуль semver лежит в src проекта."""
        self.assertIn("src", semver.__file__.replace(
            helpers.ROOT, "").replace("\\", "/"))

    def test_requirements(self):
        """Таблица требований и версий."""
        for req, version, expected in CASES:
            result = semver.satisfies(
                semver.parse_requirement(req), semver.parse_version(version))
            self.assertEqual(result, expected, f"{req} / {version}")

    def test_ordering(self):
        """Порядок версий, включая пред-версии."""
        texts = ["1.0.0", "1.0.0-beta.11", "1.0.0-beta.2", "1.0.0-alpha",
                 "0.9.9", "1.0.0-1"]
        ordered = sorted(map(semver.parse_version, texts),
                         key=semver.Version.key)
        self.assertEqual([str(v) for v in ordered], [
            "0.9.9", "1.0.0-1", "1.0.0-alpha", "1.0.0-beta.2",
            "1.0.0-beta.11", "1.0.0"])

    def test_invalid(self):
        """Неверные записи."""
        for text in ("", "1.2", "latest", "1.2.x.4"):
            self.assertFalse(semver.is_valid_version(text), text)
        for text in ("", "abc", "^", ">>1", "1.2.3.4"):
            with self.assertRaises(ValueError, msg=text):
                semver.parse_requirement(text)


if __name__ == "__main__":
    unittest.main()
