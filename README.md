### Проект "Тестовый бот". Python-разработчик (бекенд) (Яндекс.Практикум)

### Описание:
Данный проект разрабатывался для практики в создании Telegram-ботов и их связи с различными API-сервисами

### Как запустить проект:

Клонируйте репозиторий:
```
git clone git@github.com:Starkiller2000Turbo/homework_bot.git
```

Измените свою текущую рабочую дерикторию:
```
cd /homework_bot/
```

Создайте и активируйте виртуальное окружение

```
python -m venv venv
```

```
source venv/Scripts/activate
```

Обновите pip:
```
python3 -m pip install --upgrade pip
```

Установите зависимости из requirements.txt:

```
pip install -r requirements.txt
```

Создайте файл .env, где будут указаны без кавычек:

Токен на сервисе Практирум.Домашка:
```
PRACTICUM_TOKEN=...
```
Токен бота:
```
TOKEN=...
```
ID чата в телеграм:
```
CHAT_ID=...
```
Запустите бота:

```
python homework.py
```

### Авторы:

- :white_check_mark: [Starkiller2000Turbo](https://github.com/Starkiller2000Turbo)

### Стек технологий использованный в проекте:

- Python
- API
- Bot API
- logging