"""Версии и требования к версиям в формате Cargo (semver)."""

import re
from dataclasses import dataclass
from functools import total_ordering

VERSION_PATTERN = re.compile(
    r"(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?")
COMPARATOR_PATTERN = re.compile(
    r"(\^|~|=|>=|<=|>|<)?\s*(\d+|[*xX])(?:\.(\d+|[*xX]))?"
    r"(?:\.(\d+|[*xX]))?(?:-([0-9A-Za-z.-]+))?")
WILDCARDS = ("*", "x", "X")
CORE_PARTS = 3
RELEASE = (1, ())


@total_ordering
@dataclass(frozen=True)
class Version:
    """Версия MAJOR.MINOR.PATCH[-pre]."""

    major: int
    minor: int
    patch: int
    pre: tuple = ()

    def key(self):
        """Ключ сравнения: релиз старше своей пред-версии."""
        if not self.pre:
            return (self.major, self.minor, self.patch, 1, ())
        parts = tuple((0, int(item), "") if item.isdigit()
                      else (1, 0, item) for item in self.pre)
        return (self.major, self.minor, self.patch, 0, parts)

    def __lt__(self, other):
        """Сравнение по правилам semver."""
        return self.key() < other.key()

    def __str__(self):
        """Запись версии: 1.2.3 или 1.2.3-beta.1."""
        core = f"{self.major}.{self.minor}.{self.patch}"
        return core + ("-" + ".".join(self.pre) if self.pre else "")


@dataclass
class Comparator:
    """Условие на версию: границы и признак пред-версии."""

    lower: Version = None
    lower_inclusive: bool = True
    upper: Version = None
    upper_inclusive: bool = False
    pre_core: tuple = None

    def allows(self, version):
        """Попадает ли версия в границы."""
        return self.above_lower(version) and self.below_upper(version)

    def above_lower(self, version):
        """Версия не ниже нижней границы."""
        if self.lower is None:
            return True
        if self.lower_inclusive:
            return not version < self.lower
        return version > self.lower

    def below_upper(self, version):
        """Версия не выше верхней границы."""
        if self.upper is None:
            return True
        if self.upper_inclusive:
            return not self.upper < version
        return version < self.upper


def parse_version(text):
    """Разобрать версию; ValueError, если запись неверна."""
    match = VERSION_PATTERN.fullmatch(text.strip())
    if match is None:
        raise ValueError(f"неверная версия '{text}'")
    major, minor, patch, pre = match.groups()
    pre_parts = tuple(pre.split(".")) if pre else ()
    return Version(int(major), int(minor), int(patch), pre_parts)


def is_valid_version(text):
    """Корректна ли запись версии."""
    try:
        parse_version(text)
    except ValueError:
        return False
    return True


def bump(numbers):
    """Следующая версия после указанных частей (1 -> 2.0.0, 1.2 -> 1.3.0)."""
    padded = list(numbers) + [0] * (CORE_PARTS - len(numbers))
    index = len(numbers) - 1
    padded[index] += 1
    for later in range(index + 1, CORE_PARTS):
        padded[later] = 0
    return Version(*padded)


def caret_upper(numbers):
    """Верхняя граница ^: первая ненулевая часть растёт."""
    major, minor, patch = (list(numbers) + [None, None])[:CORE_PARTS]
    if major > 0 or minor is None:
        return Version(major + 1, 0, 0)
    if minor > 0 or patch is None:
        return Version(0, minor + 1, 0)
    return Version(0, 0, patch + 1)


def comparator_for(op, numbers, pre):
    """Построить условие по оператору, частям версии и пред-версии."""
    padded = list(numbers) + [0] * (CORE_PARTS - len(numbers))
    low = Version(*padded, pre)
    if op == "^":
        return Comparator(low, True, caret_upper(numbers))
    if op == "~":
        upper = bump(numbers[:2] if len(numbers) > 1 else numbers)
        return Comparator(low, True, upper)
    return comparator_for_relation(op, numbers, low)


def comparator_for_relation(op, numbers, low):
    """Условия =, >, >=, <, <= с учётом неполной версии."""
    partial = len(numbers) < CORE_PARTS
    if op == "=":
        return Comparator(low, True, bump(numbers) if partial else low,
                          not partial)
    if op == ">":
        return Comparator(bump(numbers), True) if partial else Comparator(
            low, False)
    if op == ">=":
        return Comparator(low, True)
    if op == "<":
        return Comparator(None, True, low, False)
    return Comparator(None, True, bump(numbers) if partial else low,
                      not partial)


def split_parts(parts):
    """Числа версии до первого символа-заменителя; признак заменителя."""
    numbers = []
    for part in parts:
        if part is None:
            continue
        if part in WILDCARDS:
            return numbers, True
        numbers.append(int(part))
    return numbers, False


def parse_comparator(text):
    """Разобрать одно условие, например ^1.2, >=0.3.1, 1.*."""
    match = COMPARATOR_PATTERN.fullmatch(text.strip())
    if match is None:
        raise ValueError(f"неверное требование '{text}'")
    op, *parts, pre = match.groups()
    numbers, wildcard = split_parts(parts)
    if not numbers:
        return Comparator()
    pre_parts = tuple(pre.split(".")) if pre else ()
    operator = "~" if wildcard and not op else op or "^"
    comparator = comparator_for(operator, numbers, pre_parts)
    if pre_parts:
        comparator.pre_core = tuple(numbers)
    return comparator


def parse_requirement(text):
    """Разобрать требование: условия через запятую."""
    pieces = [piece for piece in text.split(",") if piece.strip()]
    if not pieces:
        raise ValueError("пустое требование к версии")
    return [parse_comparator(piece) for piece in pieces]


def satisfies(comparators, version):
    """Подходит ли версия под все условия (пред-версии — только явные)."""
    if version.pre:
        core = (version.major, version.minor, version.patch)
        if not any(item.pre_core == core for item in comparators):
            return False
    return all(item.allows(version) for item in comparators)
