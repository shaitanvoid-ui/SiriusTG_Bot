# DEPLOY — SiriusTG_Bot

Ран-бук деплоя и эксплуатации. Стек: Python 3.14.7 (Docker), aiogram 3.31,
SQLAlchemy 2.1 (async, SQLite), Alembic, APScheduler 3.11.
Обновление 01.10.2026, проверки и откат: [MODERNIZATION.md](MODERNIZATION.md).

## Требования

- Docker + Docker Compose (хостовый Python не используется).
- Telegram-бот (токен от @BotFather).
- Приватный лог-канал, бот — админ в нём (бэкапы/алерты/дайджест).

## Первый запуск

```bash
cp .env.example .env        # заполнить BOT_TOKEN, OWNER_ID, LOG_CHANNEL_ID
docker compose build
docker compose run --rm bot python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# скопировать вывод в FERNET_KEY в .env, затем:
docker compose up -d         # entrypoint применит alembic upgrade head до polling
curl http://localhost:8080/health     # liveness: {"status":"ok"}
curl http://localhost:8080/ready      # БД + Alembic head: {"status":"ready"}
docker compose logs -f bot            # ждём "bot_started", "Start polling"
```

Ключ генерируется один раз; production не запустится с пустым или невалидным `FERNET_KEY`.
⚠️ Потеря ключа = потеря доступа к зашифрованным полям, Telethon-сессиям
и ранее созданным `.db.fernet`-бэкапам. Хранить ключ отдельно от сервера.

## Обновление кода

Исходники попадают в образ через строгий `.dockerignore`-allowlist
(без `.env`, БД, `.git`, логов и локального окружения). Для обновления нужна пересборка:

```bash
docker compose build
docker compose up -d    # пересоздаст контейнер и до polling применит миграции
```

Для явной проверки или аварийного режима доступны:

```bash
docker compose run --rm bot alembic current
docker compose run --rm bot alembic upgrade head
```

⚠️ Не запускать второй `docker compose up` параллельно — Telegram отдаст 409 Conflict на long-polling.

## Тесты

Тесты собраны в отдельный image-stage. Сервис использует только фиктивные credentials,
временную SQLite, read-only filesystem и отключённую сеть; production `.env` и volumes
ему не передаются:

```bash
docker compose -f docker-compose.test.yml build test
docker compose -f docker-compose.test.yml run --rm test
```

## Данные и бэкапы

- БД: `./data/bot.db` (volume-mount). Все экономические параметры — в таблице `settings`, правятся из админки (`/admin → Экономика`) без передеплоя.
- **Авто-бэкап**: воркер `db_backup` каждые `backup.interval_hours` (6ч) шлёт в `LOG_CHANNEL_ID` только Fernet-зашифрованный файл `*.db.fernet`; открытый временный файл удаляется после отправки.
- `FERNET_KEY` нужно хранить в отдельном защищённом хранилище: без исходного ключа расшифровать бэкап нельзя. Лог-канал всё равно должен быть приватным.
- Ручной аварийный бэкап: остановить контейнер, скопировать `data/bot.db` в
  защищённое хранилище и снова запустить контейнер. Для регулярных копий
  использовать встроенный Fernet-воркер — он снимает консистентный snapshot
  через SQLite backup API без остановки.

Восстановление (в `.env` должен быть тот же `FERNET_KEY`, которым создан бэкап):

```bash
cp /path/to/downloaded.db.fernet data/restore.db.fernet
docker compose stop bot
docker compose run --rm bot python -m utils.backup_crypto \
  /app/data/restore.db.fernet /app/data/restored.db
cp data/bot.db data/bot.db.before-restore
mv data/restored.db data/bot.db
docker compose up -d
curl http://localhost:8080/ready
```

После проверки удалить локальные `restore.db.fernet` и `bot.db.before-restore`
или перенести их в защищённое хранилище.

## Мониторинг

- `GET :8080/health` → `{"status":"ok"}`: процесс health-сервера жив.
- `GET :8080/ready` → `{"status":"ready"}`: БД доступна и применён актуальный Alembic head. Docker healthcheck использует этот endpoint.
- Лог-канал получает: дайджест метрик раз в сутки (`digest.hour_msk`), алерты о падениях воркеров, события рефералки/заданий/отзывов/выплат, бэкапы.
- Логи: `docker compose logs -f bot` (structlog JSON).

## Воркеры (APScheduler, всё в settings)

| Джоба | Интервал | Ключ settings |
|---|---|---|
| sub_rechecker | 6 ч | `subrecheck.*` |
| ref_maturation | 1 ч | `ref.maturation_days` |
| tasks_rechecker | 5 мин | `tasks_recheck.*` |
| leaderboard_payout | пн 00:05 UTC | `leaderboard.*` |
| db_backup | 6 ч | `backup.*` |
| daily_digest | 09:00 МСК | `digest.*` |

## Userbot для bio-проверки (опционально)

Сейчас нужен только для проверки bio ежедневного бонуса. Этап 7 с выводом подарков
ещё не реализован и этой инструкцией не активируется. Для bio-проверки заполнить
`TG_API_ID`/`TG_API_HASH` (my.telegram.org) и `USERBOT_PHONE` в `.env`, затем выполнить
одноразовый интерактивный логин:

```bash
docker compose run --rm bot python -m userbot.login
```

Сессия шифруется Fernet и хранится в БД. Пока юзербот не подключён, бонус с `bonus.bio_required=true` отдаёт «проверка временно недоступна» (можно выключить ключом в Экономике).
