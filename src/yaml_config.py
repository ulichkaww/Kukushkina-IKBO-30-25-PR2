"""Чтение простого YAML: плоский набор строк вида ключ: значение.

Поддерживается подмножество YAML, достаточное для конфигурации:
комментарии (#), строки в кавычках, булевы значения (true/false,
yes/no, on/off) и пустое значение (null). Вложенные структуры и
списки не поддерживаются и сообщаются как ошибка.
"""

import re

from errors import ConfigError

KEY_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
TRUE_WORDS = ("true", "yes", "on")
FALSE_WORDS = ("false", "no", "off")
NULL_WORDS = ("", "null", "~")
QUOTES = ("'", '"')
DOCUMENT_START = "---"
MIN_QUOTED_LENGTH = 2


def strip_comment(line):
    """Убрать комментарий: # вне кавычек в начале или после пробела."""
    quote = None
    for index, char in enumerate(line):
        if quote:
            quote = None if char == quote else quote
        elif char in QUOTES:
            quote = char
        elif char == "#" and (index == 0 or line[index - 1].isspace()):
            return line[:index]
    return line


def parse_quoted(text, number):
    """Разобрать строку в кавычках."""
    quote = text[0]
    if len(text) < MIN_QUOTED_LENGTH or text[-1] != quote:
        raise ConfigError(f"строка {number}: не закрыта кавычка")
    body = text[1:-1]
    if quote == '"':
        body = body.replace('\\"', '"').replace("\\\\", "\\")
    return body


def parse_scalar(text, number):
    """Преобразовать значение: строка, булево или None."""
    text = text.strip()
    if text[:1] in QUOTES:
        return parse_quoted(text, number)
    lowered = text.lower()
    if lowered in TRUE_WORDS:
        return True
    if lowered in FALSE_WORDS:
        return False
    return None if lowered in NULL_WORDS else text


def parse_line(line, number):
    """Разобрать одну строку; вернуть (ключ, значение)."""
    if line[:1].isspace() or line.lstrip().startswith("-"):
        raise ConfigError(
            f"строка {number}: вложенные структуры и списки "
            "не поддерживаются")
    key, separator, value = line.partition(":")
    key = key.strip()
    if not separator or not KEY_PATTERN.fullmatch(key):
        raise ConfigError(f"строка {number}: ожидалось 'ключ: значение'")
    return key, parse_scalar(value, number)


def parse_yaml(text):
    """Разобрать текст конфигурации в словарь."""
    result = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = strip_comment(raw).rstrip()
        if not line.strip() or line.strip() == DOCUMENT_START:
            continue
        key, value = parse_line(line, number)
        if key in result:
            raise ConfigError(f"строка {number}: ключ '{key}' повторяется")
        result[key] = value
    return result


def load_yaml(path):
    """Прочитать YAML-файл; ошибки чтения превращаются в ConfigError."""
    try:
        with open(path, encoding="utf-8") as file:
            return parse_yaml(file.read())
    except FileNotFoundError as err:
        raise ConfigError(f"файл конфигурации не найден: {path}") from err
    except IsADirectoryError as err:
        raise ConfigError(f"{path} — папка, нужен файл") from err
    except (OSError, UnicodeDecodeError) as err:
        raise ConfigError(f"не удалось прочитать {path}: {err}") from err
