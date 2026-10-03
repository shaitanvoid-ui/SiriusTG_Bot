# DEPLOY — SiriusTG_Bot

Ран-бук деплоя и эксплуатации. Стек: Python 3.14.7 (Docker), aiogram 3.31,
SQLAlchemy 2.1 (async, SQLite), Alembic, APScheduler 3.11.
Актуальные изменения: [этап 7](STAGE7.md), [антифрод](STAGE12.md),
[учёт средств](EXACT_MONEY.md). Первичная модернизация: [MODERNIZATION.md](MODERNIZATION.md).

## Требования

- Docker + Docker Compose (хостовый Python не используется).
- Telegram-бот (токен от @BotFather).
- Приватный лог-канал, бот — админ в нём (бэкапы/алерты/дайджест).

## Первый запуск

```bash
test -f .env || cp .env.example .env
docker compose build
docker compose run --rm -T --no-deps --volume "$PWD/.env:/setup.env" \
  --volume "$PWD/scripts/init_env.py:/setup.py:ro" --entrypoint python bot /setup.py /setup.env
# заполнить BOT_TOKEN, OWNER_ID, LOG_CHANNEL_ID в .env; существующий Fernet-ключ сохраняется
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
- Ручной бэкап перед миграцией: остановить бот, выполнить команду ниже с новым
  каталогом. Помощник использует SQLite backup API с учётом WAL, проверяет целостность
  и расшифровку. Простое копирование `.db` не является консистентным бэкапом.

```bash
docker compose stop bot
docker compose run --rm -T --no-deps -e PYTHONPATH=/app \
  --volume "$PWD/scripts/backup_local.py:/maintenance.py:ro" --entrypoint python bot \
  /maintenance.py /app/data/backups/before-update-YYYYMMDD
```

В PowerShell вместо `$PWD` в параметре volume используйте `${PWD}`. При обновлении
0015 → 0016 сначала проверьте зашифрованный снимок на отдельной копии через
`scripts/stage12_migration_probe.py`; он никогда не открывает рабочую БД.

Восстановление (в `.env` должен быть тот же `FERNET_KEY`, которым создан бэкап):

```bash
cp /path/to/downloaded.db.fernet data/restore.db.fernet
docker compose stop bot
docker compose run --rm --no-deps --entrypoint python bot -m utils.backup_crypto \
  /app/data/restore.db.fernet /app/data/restored.db
mv data/restored.db data/bot.db
docker compose up -d
curl http://localhost:8080/ready
```

До замены БД требуется сверить неизвестные и уже отправленные подарки с журналом.
Старый снимок может не содержать выполненные выдачи. Сохраните новое состояние
консистентным зашифрованным бэкапом. Убедитесь, что все SQLite-клиенты остановлены;
файлы WAL/SHM от предыдущей БД нельзя переносить к восстановленной БД.
Резервную копию и ключ храните раздельно в защищённом хранилище.

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

## Userbot для bio и выдачи подарков

Этап 7 отправляет обычные Stars-подарки через личный аккаунт Telethon.
Каталог, резерв, очередь, неизвестные оплаты и владельческие решения описаны
в [STAGE7.md](STAGE7.md). Для подключения заполнить
`TG_API_ID`/`TG_API_HASH` (my.telegram.org) и `USERBOT_PHONE` в `.env`, затем выполнить
одноразовый интерактивный логин:

```bash
docker compose stop bot
docker compose run --rm bot python -m userbot.login
docker compose up -d bot
```

Сессия шифруется Fernet и хранится в БД. Пока юзербот не подключён, бонус с `bonus.bio_required=true` отдаёт «проверка временно недоступна» (можно выключить ключом в Экономике).

После входа проверить выбранный номер через getMe и закрепить `USERBOT_ACCOUNT_ID`.
`OWNER_ID` определяет права владельца в боте и может относиться к другому аккаунту.
Код и 2FA вводятся скрыто в терминале. Клиенты одной сессии не запускаются параллельно.
Оплата подарков выключена до настройки владельцем `gifts.enabled` и
`gifts.daily_budget_stars`; настоящий Stars-баланс пополняет владелец.
Платный тест требует отдельной команды с получателем и пределом расходов.
