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


def check_tokens() -> None:
    """Функция для проверки доступности переменных окружения.

    Raises:
        SystemExit: Если отсутствуют обязательные переменные окружения.
    """
    logger.info('Call function check_tokens with no arguments')
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


def send_message(bot: telegram.Bot, text: str) -> None:
    """Функция для отправки сообщения.

    Args:
        bot: Чат-бот.
        message: Строка передаваемого текста.
    """
    logger.info(
        'Call function send_message with arguments: %s, %s',
        str(bot),
        text,
    )
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
        )
    except telegram.TelegramError:
        logging.error('Ошибка при отправке сообщения')
    else:
        logging.debug('Удачная отправка сообщения')


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
    logger.info(
        'Call function get_api_answer with argument: %s',
        str(timestamp),
    )
    try:
        responce = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp - RETRY_PERIOD},
        )
    except Exception:
        logging.error('Проблемы с доступоп к Эндпоинту')
        raise Exception('Проблемы с доступоп к Эндпоинту')
    else:
        if responce.status_code == HTTPStatus.OK:
            return responce.json()
        logging.error('Недоступность эндпоинта')
        raise Exception('Недоступность эндпоинта')


def check_response(response: requests.Response) -> requests.Response:
    """Функция проверяет правильность полученного ответа.

    Args:
        response: полученный ответ.

    Returns:
        Полученный ответ в случае его правильности

    Raises:
        TypeError: Если response не соответствует ожидаемому виду.
    """
    logger.info(
        'Call function check_response with argument: %s',
        str(response),
    )
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


def parse_status(homework: typing.Dict[str, typing.Any]) -> str:
    """Функция для возвращения информации о домашней работе.

    Args:
        homework: Определённая домашняя работа.

    Returns:
        Строка, указывающая изменение статуса.

    Raises:
        Exception: Если статус домашней работы не удаётся определить.
    """
    logger.info('Call function parse_status with argument: %s', str(homework))
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


def main() -> None:
    """Основная логика работы бота."""
    logger.info('Call function main with no argument')
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
                send_message(bot, text='Отсутствуют новые ответы')
            else:
                for homework in responce['homeworks']:
                    send_message(bot, parse_status(homework))
        except Exception:
            logging.error('Сбой в работе программы')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
