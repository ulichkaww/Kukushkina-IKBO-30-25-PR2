"""Параметры пользователя: чтение из YAML и проверка значений."""

import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from errors import ConfigError
from yaml_config import load_yaml

CONFIG_KEYS = ("package", "repository", "test_mode", "version", "filter")
NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
VERSION_PATTERN = re.compile(
    r"\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?")
MAX_NAME_LENGTH = 64
URL_SCHEMES = ("http", "https")


@dataclass
class Settings:
    """Проверенные параметры пользователя."""

    package: str
    repository: str
    test_mode: bool
    version: str
    filter: str


def require_string(key, value):
    """Значение обязательно и должно быть непустой строкой."""
    if value is None or value == "":
        raise ConfigError(f"параметр '{key}' не задан")
    if not isinstance(value, str):
        raise ConfigError(f"параметр '{key}' должен быть строкой")
    return value


def check_package(value):
    """Имя пакета: буквы, цифры, '-' и '_'."""
    name = require_string("package", value)
    if len(name) > MAX_NAME_LENGTH or not NAME_PATTERN.fullmatch(name):
        raise ConfigError(
            f"package: неверное имя пакета '{name}' (латинские буквы, "
            f"цифры, '-' и '_', не длиннее {MAX_NAME_LENGTH})")
    return name


def check_test_mode(value):
    """Режим тестового репозитория: булево значение."""
    if not isinstance(value, bool):
        raise ConfigError("test_mode: ожидается true или false")
    return value


def check_repository(value, test_mode):
    """URL репозитория или путь к файлу тестового репозитория."""
    text = require_string("repository", value)
    if test_mode:
        if not os.path.exists(text):
            raise ConfigError(f"repository: файл не найден: {text}")
        if not os.path.isfile(text):
            raise ConfigError(f"repository: {text} — не файл")
        return text
    parts = urlparse(text)
    if parts.scheme not in URL_SCHEMES or not parts.netloc:
        raise ConfigError(
            f"repository: '{text}' не похож на URL (http:// или https://)")
    return text


def check_version(value):
    """Версия пакета в формате MAJOR.MINOR.PATCH."""
    text = require_string("version", value)
    if not VERSION_PATTERN.fullmatch(text):
        raise ConfigError(
            f"version: '{text}' не похоже на версию вида 1.2.3")
    return text


def check_filter(value):
    """Подстрока фильтра: строка без переводов строк, может быть пустой."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ConfigError("filter: ожидается строка")
    if "\n" in value or "\r" in value:
        raise ConfigError("filter: подстрока не должна содержать перевод "
                          "строки")
    return value


def check_keys(data):
    """Проверить набор ключей: нет лишних и нет пропущенных."""
    unknown = [key for key in data if key not in CONFIG_KEYS]
    if unknown:
        raise ConfigError(f"неизвестные параметры: {', '.join(unknown)}")
    missing = [key for key in CONFIG_KEYS if key not in data]
    if missing:
        raise ConfigError(f"не заданы параметры: {', '.join(missing)}")


def build_settings(data):
    """Проверить словарь конфигурации и создать Settings."""
    check_keys(data)
    test_mode = check_test_mode(data["test_mode"])
    return Settings(
        package=check_package(data["package"]),
        repository=check_repository(data["repository"], test_mode),
        test_mode=test_mode,
        version=check_version(data["version"]),
        filter=check_filter(data["filter"]))


def load_settings(path):
    """Прочитать и проверить конфигурационный файл."""
    return build_settings(load_yaml(path))


def describe(settings):
    """Строки «ключ: значение» для всех параметров."""
    values = {
        "package": settings.package,
        "repository": settings.repository,
        "test_mode": "true" if settings.test_mode else "false",
        "version": settings.version,
        "filter": f'"{settings.filter}"',
    }
    return [f"{key}: {values[key]}" for key in CONFIG_KEYS]
