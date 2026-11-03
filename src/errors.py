"""Ошибки приложения."""


class DepGraphError(Exception):
    """Базовая ошибка: сообщение показывается пользователю."""


class ConfigError(DepGraphError):
    """Ошибка чтения или проверки конфигурационного файла."""


class RepositoryError(DepGraphError):
    """Ошибка доступа к репозиторию или неверные данные в нём."""
