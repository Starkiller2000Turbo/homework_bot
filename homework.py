import logging
import os
import time

import requests
from dotenv import load_dotenv
import telegram

load_dotenv()

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}


def check_tokens() -> bool:
    """Функция для проверки доступности переменных окружения."""
    if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        logging.critical('Отсутствие обязательных переменных окружения')
        raise Exception


def send_message(bot: telegram.Bot, message: str) -> None:
    """Функция для отправки сообщения.

    Args:
        bot: Чат-бот.
        message: Строка передаваемого текста.
    """
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logging.debug('Удачная отправка сообщения')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp: int) -> requests.Response:
    """Функция для отправки сообщения.

    Args:
        timestamp: Текущие дата и время.

    Returns:
        Список домашних работ.
    """
    try:
        responce: requests.Response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp - RETRY_PERIOD},
        )
        if responce.status_code == 200:
            return responce.json()
        logging.error('Недоступность эндпоинта')
        raise Exception('Недоступность эндпоинта')
    except Exception as error:
        logging.error(f'Проблемы с доступоп к Эндпоинту: {error}')
        raise Exception(f'Проблемы с доступоп к Эндпоинту: {error}')


def check_response(response: requests.Response) -> requests.Response:
    """Функция проверяет правильность полученного ответа.

    Args:
        response: полученный ответ.

    Returns:
        Полученный ответ в случае его правильности
    """
    if (
        isinstance(response, dict)
        and all(
            key in response.keys() for key in ('current_date', 'homeworks')
        )
        and isinstance(response['homeworks'], list)
    ):
        return response
    else:
        logging.error('Нет ожидаемых ключей в словаре эндпоинта')
        raise TypeError


def parse_status(homework: dict) -> str:
    """Функция для возвращения информации о домашней работе.

    Args:
        homework: Определённая домашняя работа.

    Returns:
        Строка, указывающая изменение статуса.
    """
    try:
        homework_name = homework["homework_name"]
    except KeyError:
        logging.error('Отсутствует ключ "homework_name"')
    try:
        status = homework["status"]
    except KeyError:
        logging.error('Отсутствует ключ "status"')
    try:
        return (
            f'Изменился статус проверки работы "{homework_name}". '
            f'{HOMEWORK_VERDICTS[status]}'
        )
    except KeyError:
        logging.error(
            f'Неожиданный статус домашней работы: ' f'{homework["status"]}',
        )
        raise Exception


def main():
    """Основная логика работы бота."""
    check_tokens()
    logging.debug('Инициализация бота')
    bot: telegram.Bot = telegram.Bot(token=TELEGRAM_TOKEN)
    logging.debug('Бот успешно инициализирован')
    while True:
        try:
            timestamp: int = int(time.time())
            responce: requests.Response = check_response(
                get_api_answer(timestamp),
            )
            if responce['homeworks'] == []:
                logging.debug('Отсутствуют новые ответы')
            else:
                for homework in responce['homeworks']:
                    send_message(bot, parse_status(homework))
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
