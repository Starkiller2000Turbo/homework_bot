import logging
import os
import sys
import time
import typing
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
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


def func_logger(func):
    """Декоратор логгирует запуск функции func.

    Args:
        func: Функция, которую необходимо логгировать.
    """

    def inner(*args, **kwargs):
        ret = func(*args, **kwargs)
        logger.info(
            f'Call func {func.__name__} with {args, kwargs} returns {ret}',
        )
        return ret

    return inner


@func_logger
def check_tokens() -> None:
    """Функция для проверки доступности переменных окружения.

    Raises:
        SystemExit: Если отсутствуют обязательные переменные окружения.
    """
    print(globals())
    missing = [
        token
        for token in ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
        if globals()[token] is None
    ]
    if len(missing) > 0:
        logging.critical(
            'Отсутствие обязательных переменных окружения: '
            + ", ".join(missing),
        )
        sys.exit()


@func_logger
def send_message(bot: telegram.Bot, text: str) -> None:
    """Функция для отправки сообщения.

    Args:
        bot: Чат-бот.
        message: Строка передаваемого текста.
    """
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
        )
    except telegram.TelegramError as ex:
        logging.error('Ошибка при отправке сообщения: ', ex)
    else:
        logging.debug('Удачная отправка сообщения')


@func_logger
def get_api_answer(timestamp: int) -> requests.Response:
    """Функция для отправки сообщения.

    Args:
        timestamp: Текущие дата и время.

    Returns:
        Список домашних работ.

    Raises:
        RequestException: Если есть проблемы с доступом к эндпоинту.
        HTTPError: Если код ответа отличен от HTTPStatus.OK.
    """
    try:
        responce = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp - RETRY_PERIOD},
        )
    except requests.exceptions.RequestException as ex:
        logging.error('Проблемы с доступоп к Эндпоинту: ', ex)
        raise Exception('Проблемы с доступоп к Эндпоинту: ', ex)
    else:
        if responce.status_code == HTTPStatus.OK:
            return responce.json()
        logging.error('Недоступность эндпоинта')
        raise requests.exceptions.HTTPError('Недоступность эндпоинта')


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
        Exception: Если статус домашней работы не удаётся определить.
    """
    try:
        homework_name, status = homework['homework_name'], homework['status']
    except KeyError:
        logging.error('Отсутствует ключ "homework_name" или "status"')
    try:
        return (
            f'Изменился статус проверки работы "{homework_name}". '
            f'{HOMEWORK_VERDICTS[status]}'
        )
    except KeyError:
        logging.error(
            f'Неожиданный статус домашней работы: {homework["status"]}',
        )
        raise Exception


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
            else:
                for homework in responce['homeworks']:
                    send_message(bot, parse_status(homework))
        except Exception as ex:
            logging.error('Сбой в работе программы: ', ex)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
