import logging
import os
import time
from http import HTTPStatus

import requests
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv

from exceptions import UnexpectedStatusError, HomeWorkStatus


load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='program.log',
    level=logging.INFO,
)

PRACTICUM_TOKEN = os.getenv('PRACTIC_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
PAYLOAD = {'from_date': None}
NEWEST_API_ANSWER = 0
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}


def check_tokens():
    """Убеждаемся что все данные окружения присуствуют."""
    return None not in (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)


def send_message(bot, message=None):
    """Бот отправляет сообщение о неисправности в случае."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Удачная отправка "{message}" сообщения в Telegram')
    except TelegramError:
        logging.error(f'Cбой при отправке "{message}" сообщения в Telegram')


def get_api_answer(timestamp):
    """Отправляем запрос к эндпоинту и проверяем статус ответа."""
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=PAYLOAD)
    except requests.exceptions.RequestException:
        raise UnexpectedStatusError
    if response.status_code != HTTPStatus.OK:
        logging.error(
            f'Недоступен {ENDPOINT}. Стаус ответа {response.status_code}'
        )
        raise UnexpectedStatusError
    return response.json()


def check_response(response):
    """Валидируем полученные данные от API."""
    final_homework = {}
    if not isinstance(response, dict):
        logging.error(f'Тип данных API {type(response)} != <dict>')
        raise TypeError
    elif not isinstance(response.get('homeworks'), list):
        logging.error(
            (
                'Тип данных по ключу "homeworks" '
                f'{type(response.get("homeworks"))} != <list>'
            )
        )
        raise TypeError
    for d in response['homeworks']:
        if 'homework_name' in d.keys() or 'status' in d.keys():
            final_homework.update(d)

    if (
        'homework_name' not in final_homework.keys()
        or 'status' not in final_homework.keys()
    ):
        logging.error('Отсуствуют ожидаемые  ключи API')
    else:
        return final_homework


def parse_status(homework):
    """Дополнительная валидация, проверяем изменился ли статус.
    Отправляем ответ в Телеграм
    """
    name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICTS.get(homework.get('status'))
    try:
        if homework.get('status') not in HOMEWORK_VERDICTS.keys():
            logging.error(
                (
                    'Неожиданный статус домашней работы, '
                    f'обнаруженный в ответе API {homework.get("status")}'
                )
            )
            raise UnexpectedStatusError()
        elif not name:
            raise NameError()
        elif homework.get('homeworks') == []:
            raise HomeWorkStatus()
    except HomeWorkStatus:
        logging.DEBUG('Статус домашнего задания не изменился')
    return f'Изменился статус проверки работы "{name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(
            'Отсутствие обязательных переменных окружения'
        )

    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    PAYLOAD['from_date'] = timestamp

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if not homework:
                send_message(bot, message='Статус домашки не изменился')
            else:
                send_message(bot, message=parse_status(homework))
                logging.info(homework)
                PAYLOAD['from_date'] = homework['current_time']
        except Exception as error:
            send_message(bot, message=f'Сбой в работе программы: {error}')

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
