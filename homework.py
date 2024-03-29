import logging
import os
import sys
import time
from http import HTTPStatus
from json import JSONDecodeError
from typing import Type, List, Dict, Any, NoReturn

import requests
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv

from exceptions import (
    UnexpectedStatusError,
    DecoderError,
    MessageError,
    ApiConnectionError,
    CurrentDateKeyError,
    CurrentDateTypeError,
    OnlyForLoggingsError,
)


load_dotenv()


PRACTICUM_TOKEN: str = os.getenv('PRACTIC_TOKEN')
TELEGRAM_TOKEN: str = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID: str = os.getenv('CHAT_ID')
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: Dict[str, str] = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
RETRY_PERIOD: int = 600
ERROR_MESSAGE: str = 'Сбой в работе программы: '
DONT_CHANGE_STATUS_MSG: str = 'C крайней проверки, статус не изменился'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE_DIR = os.path.join(SCRIPT_DIR, 'program.log')
HOMEWORK_VERDICTS: Dict[str, str] = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}
EXCEPTIONS_MESSAGE: Dict[Type[Exception], str] = {
    MessageError: 'Cбой при отправке сообщения в Telegram',
    requests.exceptions.RequestException: 'Возникла проблема с запросом',
    UnexpectedStatusError: f'Недоступен {ENDPOINT}.',
    JSONDecodeError: 'Возникла проблема с декодировкой json',
    TypeError: 'Тип данных API не соотвествует',
    KeyError: 'Ошибка с ключами homework_name, status',
    ApiConnectionError: 'Ошибка соединения с API',
    Exception: '{ERROR_MESSAGE}',
}
ENV_TOKENS: List[str] = [
    'PRACTICUM_TOKEN',
    'TELEGRAM_TOKEN',
    'TELEGRAM_CHAT_ID',
    'ENDPOINT',
]


def check_tokens() -> bool:
    """Убеждаемся что все данные окружения присуствуют."""
    uncorrect_token: List = list(
        filter(lambda env_name: globals()[env_name] is None, ENV_TOKENS)
    )
    if uncorrect_token:
        logging.critical(
            f'Отсутствие обязательных переменных окружения {uncorrect_token}'
        )
    return not uncorrect_token


def send_message(bot: Type[Bot], message: Any = None) -> str:
    """Бот отправляет сообщение о неисправности в случае."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
    except TelegramError as error:
        logging.error(
            f'{error} Неудачная отправка сообщения в Telegram: "{message}"'
        )
    else:
        logging.debug(f'Удачная отправка сообщения в Telegram: "{message}"')


def get_api_answer(timestamp: int) -> Dict[str, Any]:
    """Отправляем запрос к эндпоинту и проверяем статус ответа."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp},
        )
        if response.status_code != HTTPStatus.OK:
            logging.info(f'Стаус ответа {response.status_code}')
            raise UnexpectedStatusError(
                f'Недоступен {ENDPOINT}. Статус ответа {response.status_code}'
            )
        return response.json()
    except requests.exceptions.RequestException as error:
        raise ApiConnectionError(f'Ошибка соединения с API {error}')
    except JSONDecodeError as error:
        raise DecoderError(f'Возникла проблема с декодировкой .json {error}')


def check_response(response: Dict) -> List:
    """Валидируем полученные данные от API."""
    if not isinstance(response, dict):
        raise TypeError('Тип данных API не соотвествуют <dict>')

    homeworks: List[Any] = response.get("homeworks")

    if not isinstance(homeworks, list):
        raise TypeError(
            'Тип данных по ключу "homeworks" не соответсвует <list>'
        )

    elif not response.get('current_date'):
        raise CurrentDateKeyError('Отсутствуют данные "current_date"')

    elif not isinstance(response.get('current_date'), int):
        raise CurrentDateTypeError(
            'Тип данных "current_date" не соответвует <int>'
        )
    return homeworks


def parse_status(homework: Dict) -> str:
    """Дополнительная валидация, проверяем изменился ли статус.
    Отправляем ответ в Телеграм
    """
    name: str = homework.get('homework_name')
    verdict: str = HOMEWORK_VERDICTS.get(homework.get('status'))

    if homework.get('status') not in HOMEWORK_VERDICTS.keys():
        raise ValueError(
            f'Неожиданный статус домашки {homework.get("status")}'
        )

    elif 'homework_name' not in homework.keys():
        raise KeyError('В ответе API отсутсвует название домашки')

    return f'Изменился статус проверки работы "{name}". {verdict}'


def main() -> NoReturn:
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Ошибка c переменными окружения. Смотрите логи.')

    bot: Type[Bot] = Bot(token=TELEGRAM_TOKEN)
    timestamp: int = int(time.time())

    logging.info('Бот начал работу')

    while True:
        try:
            response: Dict = get_api_answer(timestamp)
            answer_server: List = check_response(response)
            timestamp: int = response['current_date']

            if answer_server:
                send_message(bot, message=parse_status(answer_server[0]))
                logging.info(parse_status(answer_server))

            else:
                logging.info(DONT_CHANGE_STATUS_MSG)

        except OnlyForLoggingsError as error:
            logging.error(
                f'{error.__class__.__name__}: {error}',
                exc_info=True,
            )
        except Exception as error:
            error_msg: str = EXCEPTIONS_MESSAGE.get(error.__class__)
            logging.error(
                f'{error.__class__.__name__}: {error_msg}',
                exc_info=True,
            )
            send_message(bot, message=f'{error_msg}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(LOG_FILE_DIR, encoding='UTF-8'),
            logging.StreamHandler(sys.stdout),
        ],
    )

    main()
