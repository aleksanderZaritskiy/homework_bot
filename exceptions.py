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
