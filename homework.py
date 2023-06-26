import logging
import os
import sys
import time
import typing
from functools import wraps
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(funcName)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600  # Время ожидания следующего запроса в секундах
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}


class ProblemsWithEndpoint(Exception):
    """Ошибка при проблемах с эндпоинтом."""

    pass


class EndpointDoesNotReturn200(Exception):
    """Ошибка, если эндпоинт возвращает код отличный от 200."""

    pass


class CanNotSendMessage(Exception):
    """Ошибка, если невозможно отправить сообщение в телеграм."""

    pass


def func_logger(func):
    """Декоратор для логгирования вызова функций."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        ret = func(*args, **kwargs)
        logger.info(
            'Call func "%s" with arguments %s, %s returns %s',
            func.__name__,
            args,
            kwargs,
            ret,
        )
        return ret

    return wrapper


@func_logger
def check_tokens() -> None:
    """Функция для проверки доступности переменных окружения."""
    missing = [
        token
        for token in ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
        if globals().get(token) is None
    ]
    if missing:
        logging.critical(
            'Отсутствие обязательных переменных окружения: '
            + ', '.join(missing),
        )
        sys.exit()


@func_logger
def send_message(bot: telegram.Bot, text: str) -> None:
    """Функция для отправки сообщения.

    Args:
        bot: Чат-бот.
        text: Строка передаваемого текста.

    Raises:
        CanNotSendMessage: Если не получается отправить сообщение в телеграм.
    """
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
        )
    except telegram.TelegramError:
        logging.exception('Ошибка при отправке сообщения')
        raise CanNotSendMessage('Ошибка при отправке сообщения')
    logging.debug('Удачная отправка сообщения')


@func_logger
def get_api_answer(timestamp: int) -> requests.Response:
    """Функция для отправки сообщения.

    Args:
        timestamp: Текущие дата и время.

    Returns:
        Список домашних работ.

    Raises:
        ProblemsWithEndpoint: Если есть проблемы с доступом к эндпоинту.
        EndpointDoesNotReturn200: Если код ответа отличен от HTTPStatus.OK.
    """
    try:
        responce = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp - RETRY_PERIOD},
        )
    except Exception:
        logging.exception('Проблемы с доступоп к Эндпоинту')
        raise ProblemsWithEndpoint('Проблемы с доступоп к Эндпоинту')
    if responce.status_code == HTTPStatus.OK:
        return responce.json()
    logging.error('Недоступность эндпоинта')
    raise EndpointDoesNotReturn200('Недоступность эндпоинта')


@func_logger
def check_response(response: requests.Response) -> requests.Response:
    """Функция проверяет правильность полученного ответа.

    Args:
        response: полученный ответ.

    Returns:
        Полученный ответ в случае его правильности

    Raises:
        TypeError: Если response не соответствует ожидаемому виду.
    """
    if (
        isinstance(response, dict)
        and all(
            key in response.keys() for key in ('current_date', 'homeworks')
        )
        and isinstance(response['homeworks'], list)
    ):
        return response
    logging.error('Нет ожидаемых ключей в словаре эндпоинта')
    raise TypeError


@func_logger
def parse_status(homework: typing.Dict[str, typing.Any]) -> str:
    """Функция для возвращения информации о домашней работе.

    Args:
        homework: Определённая домашняя работа.

    Returns:
        Строка, указывающая изменение статуса.

    Raises:
        KeyError: Если статус домашней работы не удаётся определить.
    """
    try:
        homework_name, status = homework['homework_name'], homework['status']
    except KeyError:
        logging.exception('Отсутствует ключ "homework_name" или "status"')
        raise KeyError('Домашняя работа не обладает нужными ключами')
    try:
        return (
            f'Изменился статус проверки работы "{homework_name}". '
            f'{HOMEWORK_VERDICTS[status]}'
        )
    except KeyError:
        logging.error(
            'Неожиданный статус домашней работы: %s',
            homework["status"],
        )
        raise KeyError('Статус домашней работы не определён из ряда возможных')


@func_logger
def main() -> None:
    """Основная логика работы бота."""
    check_tokens()
    logging.debug('Инициализация бота')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    logging.debug('Бот успешно инициализирован')
    while True:
        try:
            timestamp = int(time.time())
            responce = check_response(get_api_answer(timestamp))
            if responce['homeworks'] == []:
                logging.debug('Отсутствуют новые ответы')
                # send_message(bot, text='Отсутствуют новые ответы')
            else:
                for homework in responce['homeworks']:
                    send_message(bot, parse_status(homework))
        except Exception:
            logging.exception('Сбой в работе программы')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
