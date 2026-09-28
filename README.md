# Проект: Telegram-бот с функцией календаря

- **Имя Фамилия:** Арутюн Газарян
- **Логин на GitHub:** Arutggg
- **E-mail:** samparryqfb965@gmail.com

## Что это

Многопользовательский календарь в Telegram с веб-частью на Django:

- **бот** — события, встречи с другими пользователями, публичные события, выгрузка;
- **админка Django** — пользователи, события, встречи и статистика;
- **личный кабинет** — веб-страница с календарём пользователя;
- **REST API** на Django REST Framework;
- всё упаковано в **Docker**: бот, база данных и веб-приложение в отдельных контейнерах.

## Команды бота

| Команда | Что делает |
|---|---|
| `/start`, `/help` | Список команд |
| `/register` | Регистрация |
| `/login` | Подключает Telegram ID к учётной записи и присылает ссылку на личный кабинет |
| `/calendar` | Весь календарь: мои события, встречи и общие события других пользователей |
| `/create_event` | Пошаговое создание события (название → дата → время → описание) |
| `/events` | Мои события |
| `/read_event [название]` | Показать событие |
| `/edit_event` | Пошаговое редактирование; `-` оставляет поле без изменений |
| `/delete_event [название]` | Удалить (отменить) событие |
| `/share [название]` | Поделиться событием; без названия — список событий с кнопками 🌐/🔒 |
| `/unshare название` | Скрыть событие |
| `/shared [@username]` | Общие события всех пользователей или одного |
| `/export` | Выгрузка событий: кнопки CSV / JSON, бот присылает файл |
| `/meeting` | Назначить встречу: тема → дата → время → длительность → участники |
| `/meetings` | Мои встречи и статусы участников |
| `/cancel` | Прервать текущий диалог |

Даты — `ДД.ММ.ГГГГ`, время — `ЧЧ:ММ`. На неверный ввод бот просит повторить шаг, не сбрасывая диалог.

### Встречи

Перед приглашением бот проверяет, свободен ли участник: берутся его неотменённые встречи
(`get_busy_slots`) и проверяется пересечение интервалов. Занятых и незарегистрированных
пользователей бот не приглашает и сообщает об этом организатору.

Приглашённым приходит сообщение с кнопками **Принять** / **Отклонить**. Статус встречи:
все приняли — «подтверждена», кто-то отклонил — «отменена», пока ответили не все — «ожидается».
Организатор получает уведомление о каждом ответе.

## Веб-часть

| Адрес | Что там |
|---|---|
| `/admin/` | Админка: пользователи со счётчиками и их событиями, события, встречи с участниками, статистика по дням |
| `/cabinet/<токен>/` | Личный кабинет (ссылку присылает `/login`) |
| `/export/<токен>/?format=csv\|json` | Выгрузка событий владельца токена |
| `/api/` | REST API (Browsable API, вход через `/api-auth/login/`) |

Токен в ссылках подписан `SECRET_KEY` и содержит Telegram ID, поэтому подставить чужой ID
нельзя: пользователь видит и выгружает только свои события. Ссылка действует неделю.

### REST API

| Эндпоинт | Методы | Доступ |
|---|---|---|
| `/api/users/` | CRUD, пользователь по адресу `/api/users/<telegram_id>/` | администраторы |
| `/api/events/` | CRUD, фильтры `?owner=<telegram_id>&is_public=true&date=ГГГГ-ММ-ДД` | администраторы |
| `/api/meetings/` | только чтение | администраторы |
| `/api/statistics/` | только чтение | администраторы |
| `/api/public-events/` | только чтение | все |

Встречи через API только читаются: создаются они в боте, где проверяется занятость участников.

```bash
curl -u admin:пароль http://localhost:8000/api/events/?owner=123456789
```

### Статистика

- **По дням** (модель `BotStatistics`): новые пользователи, созданные, изменённые и отменённые события.
- **По пользователям:** сколько событий каждый создал, изменил и отменил.

Счётчики увеличиваются атомарно через `F()`, поэтому одновременные запросы не теряют данные.

## Структура

```
config/                 настройки Django, корневые URL
calendar_app/
  models.py             BotUser, Event, Meeting, MeetingParticipant, BotStatistics
  services.py           класс Calendar: CRUD событий, регистрация, публичные события
  meetings.py           занятость, приглашения, ответы на приглашения
  stats.py              сбор статистики
  tokens.py             подписанные ссылки на кабинет и выгрузку
  export.py             CSV и JSON
  views.py, urls.py     личный кабинет и выгрузка
  api/                  сериализаторы, viewsets и роутер DRF
  admin.py              админка
  management/commands/runbot.py   запуск бота: python manage.py runbot
bot/
  app.py                сборка бота из модулей
  handlers/             events, meetings, sharing, export, common
  states.py, formatting.py, utils.py
docker/                 Dockerfile для bot, db, web
tests/                  pytest
```

Бот и веб-приложение работают с одной базой через Django ORM. Вся бизнес-логика лежит
в `calendar_app`, а бот, веб и API её только вызывают.

## Запуск в Docker

Нужен Docker Desktop.

1. Создайте `.env` из шаблона и впишите токен от [@BotFather](https://t.me/BotFather),
   `DJANGO_SECRET_KEY` и пароль администратора. Настройки базы для Docker
   (`POSTGRES_*`) можно оставить как есть, `DB_*` нужны только для запуска без Docker:
   ```bash
   cp .env.example .env
   ```
2. Соберите и запустите все контейнеры:
   ```bash
   docker compose up -d --build
   ```
   Контейнер `web` сам применит миграции и создаст суперпользователя из `.env`,
   `bot` стартует после `web`. Данные базы хранятся в томе `pgdata` и не пропадают
   при перезапуске и пересборке.
3. Админка: http://localhost:8000/admin/, API: http://localhost:8000/api/.

```bash
docker compose logs -f bot              # логи бота
docker compose run --rm web pytest      # тесты внутри контейнера
docker compose up -d --build            # пересборка после изменений
docker compose down                     # остановить (данные сохранятся)
```

<details>
<summary>То же без Compose: docker build и docker run</summary>

```bash
docker network create calendar
docker volume create pgdata

docker build -f docker/db/Dockerfile  -t calendar-db  .
docker build -f docker/web/Dockerfile -t calendar-web .
docker build -f docker/bot/Dockerfile -t calendar-bot .

DB="-e DB_HOST=db -e DB_NAME=calendar_bot -e DB_USER=postgres -e DB_PASSWORD=postgres"

docker run -d --name db --network calendar -v pgdata:/var/lib/postgresql/data \
  -e POSTGRES_DB=calendar_bot -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres calendar-db
docker run -d --name web --network calendar -p 8000:8000 --env-file .env $DB calendar-web
docker run -d --name bot --network calendar --env-file .env $DB \
  -e INTERNAL_WEB_URL=http://web:8000 calendar-bot
```
</details>

## Запуск без Docker

Нужны Python 3.12 и PostgreSQL.

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # впишите токен и данные для подключения к базе
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver  # веб: админка, кабинет, API
python manage.py runbot     # бот — во втором терминале
```

`python-telegram-bot==13.13` на Python 3.12 работает только с `urllib3<2` и `setuptools<81`,
они уже есть в `requirements.txt`.

## Тесты

```bash
pytest                                        # 48 тестов
pytest --cov=calendar_app --cov=bot           # с покрытием (~95%)
ruff check .                                  # линтер
```

pytest-django сам создаёт тестовую базу `test_<DB_NAME>`, пользователю базы нужно право `CREATEDB`.

Тесты проверяют:
- CRUD событий, валидацию и изоляцию пользователей;
- встречи: занятость, пересечения (в том числе через полночь), смену статусов, кнопки приглашений;
- публичные события;
- выгрузку CSV/JSON, в том числе что пользователь получает только свои события;
- личный кабинет и защиту подписанных ссылок;
- статистику и REST API, включая права доступа.

Диалоги с ботом проверяются сквозными тестами: сообщения и нажатия кнопок проходят через
настоящие обработчики, но без обращения к Telegram (`tests/conftest.py`, класс `FakeTelegram`).

## Что изменилось с первой части

- Хранение переведено с `psycopg2` на Django ORM с миграциями.
- Настройки берутся из `.env` вместо `secrets.py`: файл с таким именем перекрывает
  стандартный модуль `secrets`, который использует Django.
