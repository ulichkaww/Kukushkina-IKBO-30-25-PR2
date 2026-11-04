"""Чтение зависимостей из разреженного (sparse) индекса реестра Cargo.

Индекс crates.io (https://index.crates.io) — набор текстовых файлов:
для каждого пакета файл, в котором одна строка JSON описывает одну
версию (имя, версия, зависимости, features, признак yanked).
Менеджер пакетов и сторонние библиотеки не используются, только HTTP.
"""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field

import semver
from cargo_features import enabled_optional
from errors import RepositoryError

USER_AGENT = "depgraph-student/1.0 (educational project)"
TIMEOUT_SECONDS = 20
NORMAL_KIND = "normal"
HTTP_NOT_FOUND = 404
SHORT_NAME_LENGTHS = (1, 2)
THREE_LETTER_NAME = 3
PREFIX_LENGTH = 2


@dataclass
class Dependency:
    """Зависимость версии пакета."""

    alias: str
    package: str
    req: str
    optional: bool = False
    kind: str = NORMAL_KIND
    target: str = None
    default_features: bool = True
    features: list = field(default_factory=list)


@dataclass
class IndexEntry:
    """Одна версия пакета в индексе."""

    name: str
    version: semver.Version
    yanked: bool
    deps: list
    features: dict


def index_path(name):
    """Путь к файлу пакета в индексе: serde -> se/rd/serde."""
    lowered = name.lower()
    size = len(lowered)
    if size in SHORT_NAME_LENGTHS:
        return f"{size}/{lowered}"
    if size == THREE_LETTER_NAME:
        return f"3/{lowered[0]}/{lowered}"
    return f"{lowered[:PREFIX_LENGTH]}/{lowered[2:4]}/{lowered}"


def fetch_text(url):
    """Скачать текст по HTTP(S); ошибки сети — RepositoryError."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as r:
            return r.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        if err.code == HTTP_NOT_FOUND:
            raise FileNotFoundError(url) from err
        raise RepositoryError(f"{url}: HTTP {err.code}") from err
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        raise RepositoryError(
            f"не удалось подключиться к репозиторию ({url}): {err}") from err
    except UnicodeDecodeError as err:
        raise RepositoryError(f"{url}: ответ не в UTF-8") from err


def parse_dependency(raw):
    """Создать Dependency из объекта JSON."""
    try:
        alias = raw["name"]
        return Dependency(
            alias=alias,
            package=raw.get("package") or alias,
            req=raw["req"],
            optional=bool(raw.get("optional", False)),
            kind=raw.get("kind") or NORMAL_KIND,
            target=raw.get("target"),
            default_features=bool(raw.get("default_features", True)),
            features=list(raw.get("features") or []))
    except (KeyError, TypeError) as err:
        raise RepositoryError(f"некорректная зависимость в индексе: {err}")


def parse_entry(line):
    """Создать IndexEntry из строки JSON индекса."""
    try:
        raw = json.loads(line)
        features = dict(raw.get("features") or {})
        features.update(raw.get("features2") or {})
        return IndexEntry(
            name=raw["name"],
            version=semver.parse_version(raw["vers"]),
            yanked=bool(raw.get("yanked", False)),
            deps=[parse_dependency(dep) for dep in raw.get("deps") or []],
            features=features)
    except (ValueError, KeyError, TypeError, AttributeError) as err:
        raise RepositoryError(f"некорректная запись индекса: {err}") from err


def parse_index(text):
    """Разобрать содержимое файла пакета: список IndexEntry."""
    return [parse_entry(line) for line in text.splitlines() if line.strip()]


def active_dependencies(entry):
    """Прямые зависимости: обычные, без платформенных, включённые."""
    optional = {dep.alias for dep in entry.deps if dep.optional}
    enabled = enabled_optional(entry.features, optional)
    return [dep for dep in entry.deps
            if dep.kind == NORMAL_KIND and dep.target is None
            and (not dep.optional or dep.alias in enabled)]


class CargoRepository:
    """Реестр Cargo, доступный по URL (разреженный индекс)."""

    def __init__(self, base_url, fetch=fetch_text):
        """base_url — адрес индекса; fetch — функция загрузки текста."""
        self.base_url = base_url.rstrip("/")
        self.fetch = fetch
        self.cache = {}

    def entries(self, name):
        """Все версии пакета (с кэшированием запросов)."""
        if name not in self.cache:
            url = f"{self.base_url}/{index_path(name)}"
            try:
                self.cache[name] = parse_index(self.fetch(url))
            except FileNotFoundError as err:
                raise RepositoryError(
                    f"пакет '{name}' не найден в репозитории") from err
        return self.cache[name]

    def exact(self, name, version_text):
        """Запись о конкретной версии пакета."""
        wanted = semver.parse_version(version_text)
        for entry in self.entries(name):
            if entry.version == wanted:
                return entry
        known = ", ".join(str(e.version) for e in self.entries(name)[-5:])
        raise RepositoryError(
            f"версия {version_text} пакета '{name}' не найдена "
            f"(последние версии: {known})")

    def resolve(self, name, req_text):
        """Наибольшая не отозванная версия, подходящая под требование."""
        try:
            req = semver.parse_requirement(req_text)
        except ValueError as err:
            raise RepositoryError(f"{name}: {err}") from err
        fits = [entry for entry in self.entries(name)
                if not entry.yanked and semver.satisfies(req, entry.version)]
        if not fits:
            raise RepositoryError(
                f"для пакета '{name}' нет версии, подходящей под '{req_text}'")
        return max(fits, key=lambda entry: entry.version)

    def direct_dependencies(self, name, version_text):
        """Прямые зависимости указанной версии пакета."""
        return active_dependencies(self.exact(name, version_text))

    def root_node(self, package, version_text):
        """Узел-корень (имя, версия); версия должна существовать."""
        entry = self.exact(package, version_text)
        return (package, str(entry.version))

    def dependencies(self, node):
        """Прямые зависимости узла с разрешёнными версиями."""
        name, version = node
        result = []
        for dep in active_dependencies(self.exact(name, version)):
            found = self.resolve(dep.package, dep.req)
            child = (dep.package, str(found.version))
            if child not in result:
                result.append(child)
        return result
