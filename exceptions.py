class UnexpectedStatusError(Exception):
    """Вызывается, если неожиданный статус домашней работы.
    обнаруженный в ответе API
    """

    pass


class HomeWorkStatus(Exception):
    """Вызывается, если статус домашнего задания не изменился."""

    pass
