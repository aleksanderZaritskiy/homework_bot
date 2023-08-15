class OnlyForLoggingsError(Exception):
    """Все ошибки, которые будут наследоваться от этого супер-класса.
    будут только логироваться без вывода сообщения в телеграмм.
    """

    pass


class UnexpectedStatusError(Exception):
    """Вызывается, если неожиданный статус домашней работы.
    обнаруженный в ответе API
    """

    pass


class HomeWorkStatusError(Exception):
    """Вызывается, если статус домашнего задания не изменился."""

    pass


class DecoderError(Exception):
    """Вызывается, если проблемы с декодировкой json."""

    pass


class MessageError(Exception):
    """Вызывается, если неудается отправить сообщение в Телеграм."""

    pass


class ApiConnectionError(Exception):
    """Вызывается, если ошибка соединения с API."""

    pass


class CurrentDateKeyError(OnlyForLoggingsError):
    """Вызывается, если ошибка c ключом current_date."""

    pass


class CurrentDateTypeError(OnlyForLoggingsError):
    """Вызывается, если тип current_date не int."""

    pass
