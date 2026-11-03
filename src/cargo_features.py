"""Включённые по умолчанию необязательные зависимости (features Cargo)."""

DEP_PREFIX = "dep:"
DEFAULT_FEATURE = "default"


def apply_item(item, features, optional, state):
    """Обработать один элемент списка feature.

    state — пара (включённые зависимости, очередь feature).
    """
    enabled, queue = state
    if item.startswith(DEP_PREFIX):
        enabled.add(item[len(DEP_PREFIX):])
        return
    if "/" in item:
        dependency = item.partition("/")[0]
        if not dependency.endswith("?"):
            enabled.add(dependency)
        return
    if item in features:
        queue.append(item)
    if item in optional:
        enabled.add(item)


def enabled_optional(features, optional):
    """Имена необязательных зависимостей, включаемых feature default."""
    enabled, queue, seen = set(), [DEFAULT_FEATURE], set()
    while queue:
        name = queue.pop()
        if name in seen or name not in features:
            continue
        seen.add(name)
        for item in features[name]:
            apply_item(item, features, optional, (enabled, queue))
    return enabled & set(optional)
