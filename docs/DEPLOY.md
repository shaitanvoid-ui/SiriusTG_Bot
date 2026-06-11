# DEPLOY — SiriusTG_Bot

Ран-бук деплоя и эксплуатации. Стек: Python 3.12 (Docker), aiogram 3.15, SQLAlchemy 2 (async, SQLite), Alembic, APScheduler.

## Требования

- Docker + Docker Compose (хостовый Python не используется).
- Telegram-бот (токен от @BotFather).
- Приватный лог-канал, бот — админ в нём (бэкапы/алерты/дайджест).

## Первый запуск

```bash
cp .env.example .env        # заполнить BOT_TOKEN, OWNER_ID, LOG_CHANNEL_ID, FERNET_KEY
docker compose build
docker compose run --rm bot alembic upgrade head
docker compose up -d
curl http://localhost:8080/health     # {"status":"ok"}
docker compose logs -f bot            # ждём "bot_started", "Start polling"
```

`FERNET_KEY` генерируется один раз:
```bash
docker compose run --rm bot python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
⚠️ Потеря ключа = потеря Telethon-сессий (юзербот придётся логинить заново).

## Обновление кода

Исходники запекаются в образ слоем `COPY . .` — контейнер не видит правок без пересборки:

```bash
docker compose build
docker compose run --rm bot alembic upgrade head   # если были миграции
docker compose up -d                               # пересоздаст контейнер
```

⚠️ Не запускать второй `docker compose up` параллельно — Telegram отдаст 409 Conflict на long-polling.

## Тесты

pytest не входит в prod-образ, ставится в одноразовый контейнер:

```bash
docker compose run --rm --no-deps bot sh -c "pip install -q pytest==8.3.4 pytest-asyncio==0.24.0 && python -m pytest -q"
```

## Данные и бэкапы

- БД: `./data/bot.db` (volume-mount). Все экономические параметры — в таблице `settings`, правятся из админки (`/admin → Экономика`) без передеплоя.
- **Авто-бэкап**: воркер `db_backup` каждые `backup.interval_hours` (6ч) шлёт копию БД документом в `LOG_CHANNEL_ID`. Восстановление: скачать файл из канала → остановить бот → заменить `data/bot.db` → `docker compose up -d`.
- Ручной бэкап: `docker compose exec bot python -c "import asyncio; from workers.db_backup import *; ..."` или просто скопировать `data/bot.db` при остановленном боте.

## Мониторинг

- `GET :8080/health` → `{"status":"ok"}` (healthcheck зашит в compose).
- Лог-канал получает: дайджест метрик раз в сутки (`digest.hour_utc`), алерты о падениях воркеров, события рефералки/заданий/отзывов/выплат, бэкапы.
- Логи: `docker compose logs -f bot` (structlog JSON).

## Воркеры (APScheduler, всё в settings)

| Джоба | Интервал | Ключ settings |
|---|---|---|
| sub_rechecker | 6 ч | `subrecheck.*` |
| ref_maturation | 1 ч | `ref.maturation_days` |
| tasks_rechecker | 5 мин | `tasks_recheck.*` |
| leaderboard_payout | пн 00:05 UTC | `leaderboard.*` |
| db_backup | 6 ч | `backup.*` |
| daily_digest | 09:00 UTC | `digest.*` |

## Userbot (Этап 7, опционально)

Нужен для проверки bio (бонус) и вывода подарков. Заполнить `TG_API_ID`/`TG_API_HASH` (my.telegram.org) и `USERBOT_PHONE` в `.env`, затем одноразовый интерактивный логин:

```bash
docker compose run --rm bot python -m userbot.login
```

Сессия шифруется Fernet и хранится в БД. Пока юзербот не подключён, бонус с `bonus.bio_required=true` отдаёт «проверка временно недоступна» (можно выключить ключом в Экономике).
