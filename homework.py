import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from json import JSONDecodeError
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv

from exceptions import UnexpectedStatusError, DecoderError, MessageError


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTIC_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
PAYLOAD = {'from_date': None}
NEWEST_HOMEWORK = -1
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}
exceptions_loggins = {
    'MessageError': 'Cбой при отправке сообщения в Telegram',
    'requests.exceptions.RequestException':
    'Возникла проблема с запросом',
    'UnexpectedStatusError': f'Недоступен {ENDPOINT}.',
    'JSONDecodeError': 'Возникла проблема с декодировкой json',
    'TypeError': 'Тип данных API не соотвествует',
    'KeyError': 'Ошибка с ключами "homework_name" или  "status"',
}


def check_tokens():
    """Убеждаемся что все данные окружения присуствуют."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
        'ENDPOINT': ENDPOINT,
    }

    if not all(tokens.values()):
        for name, value in tokens.items():
            if value is None:
                logging.critical(
                    f'Отсутствие обязательных переменных окружения {name}'
                )
        return False
    return True


def send_message(bot, message=None):
    """Бот отправляет сообщение о неисправности в случае."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
    except TelegramError as error:
        raise MessageError(
            f'Неудается отправить сообщение {message}. Ошибка {error}'
        )
    else:
        logging.debug(f'Удачная отправка "{message}" сообщения в Telegram')


def get_api_answer(timestamp):
    """Отправляем запрос к эндпоинту и проверяем статус ответа."""
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=PAYLOAD)
    except requests.exceptions.RequestException as error:
        raise UnexpectedStatusError(f'Возникла проблема с заросом {error}')
    if response.status_code != HTTPStatus.OK:
        raise UnexpectedStatusError(
            f'Недоступен {ENDPOINT}. Стаус ответа {response.status_code}'
        )
    try:
        response = response.json()
    except JSONDecodeError as error:
        raise DecoderError(f'Возникла проблема с декодировкой .json {error}')
    else:
        return response


def check_response(response):
    """Валидируем полученные данные от API."""
    if not isinstance(response, dict):
        raise TypeError(f'Тип данных API {type(response)} != <dict>')
    elif not isinstance(response.get('homeworks'), list):
        raise TypeError(
            'Тип данных по ключу "homeworks" '
            f'{type(response.get("homeworks"))} != <list>'
        )
    elif response['homeworks'] == []:
        return response['homeworks']
    else:
        final_homework = response['homeworks'][NEWEST_HOMEWORK]
        return final_homework


def parse_status(homework):
    """Дополнительная валидация, проверяем изменился ли статус.
    Отправляем ответ в Телеграм
    """
    name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICTS.get(homework.get('status'))
    if verdict not in HOMEWORK_VERDICTS.values():
        raise KeyError(f'Неожиданный статус домашки {homework.get("status")}')
    elif 'homework_name' not in homework.keys():
        raise KeyError('В ответе API отсутсвует название домашки')
    return f'Изменился статус проверки работы "{name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit(['Ошибка c переменными окружения. Смотрите логи.'])

    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    PAYLOAD['from_date'] = timestamp

    activation_button = True

    while True:
        try:
            response = get_api_answer(timestamp)
            answer_server = check_response(response)
            if not answer_server:
                if activation_button:
                    activation_button = False
                    send_message(
                        bot, message='Привет, статус домашки не изменился'
                    )
                    logging.DEBUG('Статус домашнего задания не изменился')
            else:
                send_message(bot, message=parse_status(answer_server))
                activation_button = True
                PAYLOAD['from_date'] = answer_server['current_time']
                logging.info(answer_server)

        except (
            MessageError,
            requests.exceptions.RequestException,
            JSONDecodeError,
            KeyError,
            TypeError,
        ) as error:
            error_msg = ''.join(
                [
                    name
                    for name in str(error.add_note).split(' ')
                    if name in exceptions_loggins.keys()
                ]
            )
            logging.error(exceptions_loggins.get(error_msg))
        except Exception as error:
            send_message(bot, message=f'Сбой в работе программы: {error}')
            logging.error(f'Сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename='/yandex_practicum/Dev/homework_bot/program.log',
        level=logging.DEBUG,
    )
    main()
