# Этап 7 — 03.10.2026

Реализованы целые доли денег (0014), журнал, durable очередь подарков (0015),
Telethon обычные Stars gifts и нативный пользовательский/owner интерфейс.
Резерв при неизвестной оплате сохраняется; repeat/retry/refund запрещены без сверки.
Настоящие расходы выключены по умолчанию: gifts.enabled=false, бюджет0.
Защищённый backup data/backups/stage7-20261003/, migration copy roundtrip passed.
Проверки и инструкции: docs/STAGE7.md и docs/EXACT_MONEY.md.
API ID/hash перенесены локально; наличие данных не подтверждает вход.
Открыт отдельный интерактивный CLI терминал для скрытого ввода кода/2FA владельцем.
Реальные платные тесты не выполнялись, отдельного разрешения на них нет.
Полный этап12 не начинался. Сведения о прежнем запуске ниже исторические.

---

# Передача в новый чат — 03.10.2026

Владелец подтвердил: этап 7 отправляет подарки через Telethon с его аккаунта,
на котором будут Stars. Bot API sendGift не использовать для этой выдачи.
Подробный промпт продолжения, порядок работ и критерии приёмки:
docs/NEXT_CHAT_PROMPT.md. Сначала этап 7 с учётом средств и минимальной защитой,
после его приёмки — отдельный полный этап 12. Новые миссии/сезоны пока только план.
API ID/hash предоставлены в локальном C:/Users/andre/Downloads/telegram_api.txt;
значения не опубликованы, в .env в этой работе не переносились, вход не выполнен.
Текущий чат подготовил только передачу: код/данные/запуск не изменялись.
03.10 Docker Engine при read-only проверке был недоступен: запуск сверять заново.

# Актуальное дополнение — 01.10.2026

По прямой команде владельца выполнена модернизация бота и интерфейса.
Python 3.14.7 / aiogram 3.31.0 / SQLAlchemy 2.1.1, lock-файлы с SHA256.
Нативные Rich Messages, «Мой день», copy/disabled-кнопки, напоминания только по согласию.
Обложки/фотографии удалены по явной просьбе владельца. Удалён Telegram-хук Claude;
именно его уведомление имел в виду владелец. Алёрты/дайджесты/бэкапы бота сохранены.
Новые миграции 0012 (маркер напоминаний) и 0013 (одноразовый токен платного вращения).
Полная проверка: 265 tests passed. Копия исходной БД проверена до head, с откатом
и повторным upgrade; проверка миграций исходную БД не меняла. Затем по отдельной
команде сброшен аккаунт владельца: 1 users, 5 action_logs, 1 FSM. Настройки,
спонсоры, промокод и инструкции сохранены, целостность проверена. Зашифрованные
копии: data/backups/owner-reset-20261001T174153Z/.
Затем по отдельной команде владельца 01.10.2026 бот запущен: sirius_bot healthy,
HTTP /health 200, миграция 0013, polling без ошибок/conflict. getMe подтвердил
@TestBotSirius_bot. Эти сведения о запуске имеют приоритет над историей ниже.
Описание изменений, реальные измерения, проверки и ограничения: docs/MODERNIZATION.md.
Ранее существовавшие незакоммиченные изменения сохранены. Не возвращать старые pins
из исторических блоков ниже; не добавлять фотографии и Telegram-хук Claude.
CLAUDE.md и локальные служебные файлы .claude удалены по просьбе владельца.

---

# HANDOFF — SiriusTG_Bot

> Документ передачи проекта новой сессии. **Актуализировано: 2026-08-10.**
> Прочитай целиком до первого ответа пользователю. Полную исходную спецификацию см. `docs/SPEC.md`.

# 🟢 НОВАЯ СЕССИЯ НАЧИНАЕТСЯ ОТСЮДА (актуально на 2026-08-10)

**Прочитай этот блок + `MEMORY.md`/`project_state.md`. Остальной файл — история и конвенции (читать §5-§10).**

### Что делать первым в новой сессии
1. Не считай production запущенным по этому HANDOFF: в работе 2026-08-10 `docker compose up` не выполнялся. Сначала только проверь `docker compose ps`; запускай по явной команде пользователя.
2. `curl http://localhost:8080/health` → `{"status":"ok"}`.
3. **НЕ переходи к Этапу 7 без явной команды «следующий этап»/«дальше».** Слово «продолжай» = продолжай текущее.
4. После ЛЮБОЙ правки кода — пересборка + весь pytest до зелёного (см. §«🧪 Тесты»).

### Состояние на 2026-08-10

- Этапы 1–6, 8–11 и 13 сохранены и улучшены. **Этап 7 (вывод подарков) и Этап 12 (антифрод) не реализовывались и не экспонируются в UI.**
- Чистая Docker-сборка test-stage и полный hermetic suite: **225/225 passed**. Отдельно migration/infrastructure smoke: **8/8 passed**; `compileall`, `pip check`, shell syntax и compose validation — зелёные.
- Alembic проверен на пустой БД и read-only копии `data/bot.db`: `0009 → 0011`, `foreign_key_check=0`, orphan-ссылок после upgrade нет, исходник не изменялся.
- Runtime image проверен без запуска бота: app-процесс сбрасывает права до `uid=10001`, секреты/БД/`.git`/внутренние docs в образ не попали, production-зависимости целостны.
- В этой работе **production-бот не запускался, не пересоздавался, polling и Telegram-интеграция не проверялись.**

### ✅ Московское время ВЕЗДЕ (2026-06-11, по требованию юзера) + GitHub
- **`utils/tz.py` — единая точка истины**: `MSK` (UTC+3, без DST), `now_msk/today_msk/to_msk/fmt_dt/fmt_date/msk_day_start_utc`. Хранение в БД осталось UTC (`db.base.utcnow` не трогать!), всё видимое и все дневные границы — МСК.
- **Дневные границы по МСК**: бонус (`services/bonus._today`), кликер (`services/clicker._today`, бывш. `_today_utc`), колесо (`services/wheel._today`), статистика дашборда/дайджеста (`services/admin_stats`, SQL-сравнения через `msk_day_start_utc` — ВСЕГДА биндить UTC-aware, иначе кривое строковое сравнение в SQLite).
- **Отображение дат через `tz.fmt_dt/fmt_date`**: профиль, история, поддержка (юзер+админ), админ-юзеры, админ-отзывы, админ-промо (метка «МСК»), заявки партнёров, история выплат партнёра, штамп бэкапа. Приветствие меню — `now_msk().hour`.
- **Settings**: ключ `brand.utc_offset_hours` УДАЛЁН (и из DEFAULTS, и из реальной БД), `digest.hour_utc` → **`digest.hour_msk`** (=9, конвертация в UTC в `daily_digest.register_jobs`). `SettingRepo.delete()` добавлен. FAQ про бонус: «полночь по Москве».
- Тесты: + `tests/test_tz.py` (6). **Весь suite 138 зелёных.**
- **GitHub**: репозиторий создан (см. секцию ниже), секреты вычищены из HANDOFF (`BOT_TOKEN`/`FERNET_KEY` — только в локальном `.env`), README в стиле Elite.

### ✅ Этап 11 (поддержка + уведомления + история) ВЫПОЛНЕН 2026-06-11
- **БД (миграция 0009, применена):** `support_tickets.status` (new/in_progress/awaiting/closed) + `closed_at`, новая таблица `support_messages` (тред), `users.notify_prefs` (JSON-преференции DM).
- **Поддержка, юзер (`bot/handlers/support.py`, `sup:*`):** хаб «💬 Поддержка» (кнопка в Помощи ожила) → FAQ из settings `support.faq` (5 вопросов, правится через Экономику) → FSM нового вопроса (лимиты `support.min/max_text_length`, антиспам `support.max_tickets_per_hour`=3/час) → «Мои обращения» с перепиской, «Дописать», «Закрыть». Сервис `services/support.py` (`SupportService`, `render_thread`, `make_subject`). Жизненный цикл: NEW → (ответ админа) AWAITING → (реплика юзера) IN_PROGRESS → CLOSED.
- **Админка `adm:sup` (`bot/handlers/admin/support.py`):** счётчики по статусам, список открытых (ждущие админа сверху), архив, карточка с тредом, ответ (FSM `SupportAdminStates.waiting_reply` → DM юзеру с кнопкой «Открыть обращение»), закрытие с DM. Новые тикеты/реплики юзера — алерт в лог-канал. Кнопка «💬 Поддержка (скоро)» в /admin заменена живой.
- **Воркер `workers/support_autoclose.py`:** каждые `support.autoclose_check_hours`=6ч закрывает AWAITING-тикеты старше `support.autoclose_days`=7 дней (NEW/IN_PROGRESS не трогает — это очередь админа) + DM. Зарегистрирован в `main.py`.
- **Уведомления (`ntf:*`, `bot/handlers/notifications.py`):** в Профиле «⚙ Уведомления» — тумблеры категорий refs/tasks/rewards (`services/notifications.py NotificationService`, `User.notify_prefs`, NULL=всё вкл). Преференции врезаны во все DM-точки: ref_reward/ref_lost (через поле `notify_allowed` в `RewardEvent`/`RollbackEvent` — вычисляется в `ReferralService`, где загружен реферер), task_lost (tasks_rechecker), top_reward (leaderboard_payout), review_approved (ReviewService). Сервисные (`notify_self_subs_lost`) и ответы поддержки НЕ гасятся.
- **История (`hist:*`, `bot/handlers/history.py`):** в Профиле «📜 История» — пагинированная лента денежных операций из ActionLog (`services/history.py`, `history.page_size`=8). Клики исключены (70 строк/день — шум). Для денег реферера добавлены лог-записи `ref_reward`/`ref_reward_lost` от лица реферера (старые `ref_confirmed`/`ref_lost` атрибутированы приглашённому — оставлены для аудита).
- **Тех-долг попутно:** №1 закрыт — `SponsorService._check_one` → публичный `check_one` (alias `_check_one` оставлен для совместимости, все вызовы и monkeypatch'и тестов обновлены); №4 частично — `user_label` вынесен в `bot/handlers/admin/_common.py` (partners.py переведён, users.py — при следующем касании).
- Тесты: `tests/test_stage11.py` (14). Settings `support.*`/`history.page_size` засеяны в реальную БД (8 ключей). ⚠️ Конвертация отзыва в тикет теперь создаёт и первое сообщение треда (иначе карточка пустая).

### ✅ Алерты + чистка БД + Этап 13 ВЫПОЛНЕНЫ 2026-06-10 (третий заход)
- 🐛 **Алерты с HTML**: `callback.answer` НЕ рендерит HTML — теги были видны текстом. Починены 3 строки: `captcha_wrong` (тег убран), `review_filter_fail`/`review_antispam_fail` (для алертов добавлены плоские варианты `*_alert`, rich-версии остались для сообщений). Guard-тест `test_alert_locales_have_no_html` в `tests/test_design.py` — все `*_alert` ключи + явный список алерт-строк обязаны быть без тегов. ⚠️ Правило: новые тексты для `callback.answer` — только без HTML.
- **БД очищена** (по команде юзера): users и все пользовательские данные (referrals/clicker_days/wheel_spins/promo_activations/action_logs/partners/...) удалены; settings (51), sponsors (2, counters=0), promos (used_count=0), инструкция, стоп-слова — сохранены.
- **Этап 13 (Финал)**: `workers/db_backup.py` (каждые `backup.interval_hours`=6ч копия SQLite через sqlite3 backup API → Fernet-шифрование → `*.db.fernet` в LOG_CHANNEL), `workers/daily_digest.py` (дайджест метрик из AdminStatsService в `digest.hour_msk`=9, 09:00 МСК), APScheduler `EVENT_JOB_ERROR`-listener в `main.py` → алерт `log_worker_error` в лог-канал, `docs/DEPLOY.md` (ран-бук и команда восстановления с тем же `FERNET_KEY`). Settings `backup.*`/`digest.*`. Тесты `tests/test_stage13.py`.
- ✅ **Лог-канал перенастроен 2026-06-10**: актуальный `LOG_CHANNEL_ID` хранится только в локальном `.env`, бот назначен администратором. Бэкап и дайджест доставлены — проверено вживую.
- ✅ **Гейт разблокирован**: оба старых спонсора (id 1, 2 — приватные каналы, оба «chat not found», инвайт-ссылки мертвы) деактивированы (`is_active=0`, soft). Обязательных активных спонсоров нет → онбординг финализируется сразу после капчи. Новые спонсоры — через /admin → Спонсоры.
- Осталось: Этап 7 (нужны TG_API_ID/HASH), Этап 12 (антифрод). Этап 11 закрыт 2026-06-11.

### 🛠 ПОСТОЯННАЯ ЗАДАЧА: улучшай код, где это нужно (добавлено 2026-06-10 по команде юзера)
**Правило бойскаута:** касаешься файла по основной задаче — попутно приведи его в порядок (вынеси дубль, сузь `except`, добей type hints, убери мёртвый код). Без отдельного разрешения, но и без переписывания незатронутых модулей «ради красоты» — этапная дисциплина важнее.

**Конкретный тех-долг (выявлен на ревизии 2026-06-10, бери в порядке приоритета):**
1. ~~**`SponsorService._check_one` зовётся снаружи**~~ ✅ Сделано 2026-06-11: публичный `check_one`, alias `_check_one` для совместимости, вызовы/тесты обновлены.
2. **`datetime.utcnow()` в `ReviewRepo`** (approve/has_recent_review) — deprecated в 3.12 и несогласован с остальным кодом. Заменить на `db.base.utcnow`.
3. **`ReviewService.create_review/moderate` коммитят внутри сервиса** — остальной код доверяет commit'у `DbSessionMiddleware`. Убрать внутренние commit'ы, проверить, что админ-флоу не зависит от мгновенной фиксации (тесты переписать соответственно).
4. **Дубли в админке:** поиск юзера по `tg_id/@username` (admin/users.py `msg_search` и admin/partners.py `msg_add`) — вынести в общий хелпер. ✅ Частично 2026-06-11: `user_label` уже в `bot/handlers/admin/_common.py`, partners.py переведён; admin/users.py перевести при следующем касании.
5. **`with suppress(Exception)` вокруг `edit_text`** скрывает и логические ошибки (например, битый format). Сузить до `suppress(TelegramBadRequest)` хотя бы в новых файлах (partner, admin/partners, reviews).
6. **Рассылка блокирует хендлер** на всё время прогона (`admin/broadcast.py cb_go`). При росте базы вынести в `asyncio.create_task` + защита от двойного запуска.
7. **FSM на `MemoryStorage`** — рестарт контейнера сбрасывает незавершённые диалоги (мастера админки, отзыв, выплата). Рассмотреть SQLite-хранилище FSM (без Redis! стек зафиксирован).
8. **Shadow-ban не enforced** — флаг есть, но награды начисляются (кликер/бонус/колесо/задания/рефы). Это скоуп Этапа 12 — НЕ делать раньше, но помнить.
9. Placeholder-сообщения `await message.answer("…")` перед `_render_card` (admin/users, admin/partners, partner) — заменить на нормальный паттерн «отправь сразу готовый текст» (рендер в строку + send, без промежуточного edit).

После каждого пункта — полный pytest до зелёного (см. §«🧪 Тесты»). Пункты 1-2 — безопасные и быстрые, начинай с них при первом же касании соответствующих файлов.

### ✅ Багфиксы + Этап 10 (партнёрка) ВЫПОЛНЕНЫ 2026-06-10 (вторая сессия)
**Багфиксы (по жалобе «прибавляю звёзды — не прибавляются» + ревизия):**
- 🐛 `admin/users.py msg_balance_delta`: `session.refresh(user)` после `add_balance` ЭКСПАЙРИЛ объект и отбрасывал нефлашнутое начисление → заменено на `session.flush()`. Регресс-тесты в `test_admin_stage9.py`. ⚠️ Паттерн: refresh безопасен только после SQL-`update()`, после in-memory мутаций — сначала flush.
- 🐛 Отзывы были полностью недостижимы: на интро не было кнопки `rev:start` (только «В меню»). Добавлена `kb_review_intro`.
- 🐛 Шаг анонимности: была одна кнопка «Далее»→`rev:anon_yes` при логике `is_anon = (data=="rev:anon_no")` — выбор фиктивный и инверсный. Теперь две кнопки (`rev:anon_no`=с username / `rev:anon_yes`=анонимно), маппинг исправлен.
- 🐛 Кнопка `rev:text_next` вела в никуда (хендлера нет) — убрана; `ins:noop` не отвечал на callback (вечный спиннер) — добавлен хендлер.
- 🐛 Публикация одобренного отзыва в канал `reviews_channel_id` не была реализована (мёртвая переменная) → `ReviewService.publish_review` + DM юзеру `notify_user_approved` + лог при отправке на модерацию. Награда начисляется ДО commit. Гарды от повторной модерации в админ-хендлерах.
- 🐛 `support_tickets`: модель была с Этапа 8, **таблицы в миграциях не было** (конвертация отзыва в тикет падала бы на проде) → создана в `0008`.
- `rev:cancel` теперь возвращает в главное меню; `nav:menu` убран из фильтра отзывов (дублировал menu-роутер).
**Этап 10 — Партнёрская система (вся экономика в settings `partner.*`):**
- Модель заработка: CPA `partner.reward_per_passed_user` (1.0⭐) за приведённого по UTM юзера, прошедшего гейт (хук в `flow.finalize_subs_passed`) + `partner.percent_sponsor_reward` (50%) от награды задания по спонсору партнёра (хук в `TasksService.claim`). Персональные ставки — поля `Partner.reward_per_user/percent_sponsor` (NULL=дефолт).
- Модели `Partner`/`PartnerLink`/`PartnerPayout` + `users.partner_id/partner_link_id`, `sponsors.partner_id`; миграция `0008_partners` (применена). Репо `db/repositories/partner.py`, сервис `services/partner.py`.
- UTM: payload `p<code>` в `/start` (`track_start`: клик всегда; привязка один раз, до гейта, не сам себе), лимит `partner.max_links`.
- Панель партнёра (`bot/handlers/partner.py`, `pa:*`): кнопка «🤝 Партнёрка» в Профиле (видна только партнёрам), статистика (клики/регистрации/прошли гейт), CRUD ссылок, свои каналы (создаются `is_active=False`, активирует owner в админке спонсоров, там же ставит reward), заявка на выплату (вся сумма, мин `partner.min_payout_stars`=50⭐, курс `partner.rub_per_star`=1.5₽ фиксируется, резерв сразу, одна pending), история.
- Админка «🤝 Партнёры» (`adm:pa`, `bot/handlers/admin/partners.py`): назначить по tg_id/@username (DM юзеру), карточка (пауза/персональные CPA и %), заявки на выплату → «Выплачено» (DM) / «Отклонить» (возврат ⭐ + DM).
- Тесты: `tests/test_partner.py` (10) + `tests/test_reviews.py` (8) + 2 регресс-теста баланса. Весь suite 110 зелёных.

- **Этап 6 (геймификация) сдан, ждёт ручной проверки пользователя** в тестовом боте из локальной конфигурации (колесо `whl:open` / достижения `ach:open` / топ `top:open`). Детали — в блоке «✅ Этап 6 ЗАВЕРШЁН» ниже и в `project_state.md`.
- Если пользователь скажет «следующий этап»/«дальше» — это **Этап 7 (вывод подарков)**. Сначала дай план из 3-5 пунктов, жди «ок». ⚠️ Этап 7 требует подключённого userbot: запроси `TG_API_ID`/`TG_API_HASH` с my.telegram.org (телефон уже в `.env`).

### ⚠️ ГЛАВНОЕ: Telethon-аккаунт ЕЩЁ НЕ ПОДКЛЮЧЁН
- `userbot configured=false` (нет `TG_API_ID`/`TG_API_HASH` в `.env`). `USERBOT_PHONE` уже прописан локально без публикации значения в репозитории.
- Логин — одноразовый интерактивный CLI (запускает ПОЛЬЗОВАТЕЛЬ в своём терминале, не ты):
  `docker compose run --rm bot python -m userbot.login` — спросит код из Telegram + 2FA, сохранит зашифр. сессию в БД.
- **Что попросить у пользователя для активации:** `TG_API_ID` и `TG_API_HASH` с my.telegram.org.
- Пока userbot не залогинен: ежедневный бонус с `bonus.bio_required=True` отдаёт алерт «⏳ Проверка временно недоступна» (попытка НЕ сгорает). Чтобы протестировать начисление бонуса БЕЗ userbot — временно `SettingsService.set('bonus.bio_required', False)`.

### Что сделано в Этапе 5 (Telethon + ежедневный бонус + streak) — НЕ переделывай
- `core/crypto.py` (Fernet); сессия Telethon шифруется и хранится в БД (`userbot_sessions`), не на диске.
- `userbot/client.py` — ленивый singleton со стабильными `device_model="Sirius Desktop"`/`system_version="Windows 10"`/`app_version="4.16.8 x64"`/`lang=ru` (мимикрия под Telegram Desktop против вылета сессии); мягкая деградация в None.
- `userbot/login.py` (CLI), `userbot/bio_reader.py` (рефка в bio).
- `services/bonus.py` — бонус 1/UTC-день, streak 1/3/7/14/30, сброс при пропуске, идемпотентность (`DailyBonusLog` unique(user,day) + `User.last_bonus_date`), гейт `bonus.bio_required`.
- Модели `DailyBonusLog`/`UserbotSession` + `User.bonus_streak/last_bonus_date`; миграция `0005_userbot_bonus` (применена).
- UI: `bns:open`/`bns:claim`, кнопка «🎁 Ежедневный бонус» в «Заработать» (была `feat:soon:bonus`).

### Доп. правки после Этапа 5 (по просьбе пользователя)
- **Кликер — лесенка дневного максимума по уровням 4→10⭐** (раньше плоско 7⭐). Тап фиксирован `0.1⭐`, `click_mult=1.0`; `click_daily_limit`: Бронза 40 (4⭐) / Серебро 55 (5.5⭐) / Золото 70 (7⭐) / Платина 85 (8.5⭐) / Алмаз 100 (10⭐). Значения в `DEFAULTS` И в реальной `data/bot.db` (через `SettingsService.set`).
- **Кликер — таймер до следующего тапа** виден на карточке (строка `clicker_cooldown_line`/`ready_line`/`limit_line`), на кнопке (`btn_click_cooldown` = `⏳ M:SS`) и в алерте (`clicker_too_fast_alert` с `{left}`). `ClickerView.cooldown_ms_left` + хелперы `utils/ui.human_duration`/`clock_mmss`.

### ✅ Этап 6 ЗАВЕРШЁН 2026-05-29 (геймификация). 67 тестов зелёных.
- **Кликер (подтверждено юзером):** ставка за тап фикс 0.1⭐, по уровням растёт ТОЛЬКО дневной лимит (Бронза 40=4⭐ → Алмаз 100=10⭐). Множители SPEC x1.1..x2 НЕ возвращали.
- **Колесо** `services/wheel.py` + `WheelSpinRepo` + `bot/handlers/wheel.py` + `bot/keyboards/wheel.py`: 1 free/день, платное `wheel.cost`, призы `wheel.prizes` (EV<cost), кнопка «🎡» → `whl:open`.
- **Достижения** `services/achievements.py` + `UserAchievementRepo` + хендлер: реестр `achievements.config` (метрики confirmed_refs/clicks_total/bonus_streak/tasks_done), ленивое начисление `sync()` при открытии, кнопка «🏅» → `ach:open`.
- **Лидерборд** `services/leaderboard.py` + хендлер/клава: топ по подтв.рефам week/month/all, мин. `leaderboard.min_confirmed_refs`=10, кнопка «🏆 Топ-100» → `top:open`.
- **Воркер** `workers/leaderboard_payout.py`: пн 00:05 UTC, топ-10 недели [50/30/20/5×7], идемпотентность по ISO-неделе. Зарегистрирован в `main.py`.
- Модели `WheelSpin`/`UserAchievement`/`LeaderboardPayout`, миграция `0006_gamification` (применена). Settings wheel.*/achievements.*/leaderboard.* засеяны.

### Следующий — Этап 7 (вывод подарков). ⚠️ Требует подключённого userbot (TG_API_ID/HASH ещё не даны).

### ✅ Этап 8 ДОДЕЛАН + Этап 9 (полная админка) ВЫПОЛНЕН 2026-06-10 (Этап 7 пропущен по команде юзера — нет userbot)
**Этап 8 (доделка):**
- `bot/handlers/admin/instructions.py` — CRUD страниц инструкции (`adm:ins:*`, FSM `InstructionStates`), soft-delete.
- `bot/handlers/admin/channel.py` — установка канала проекта (`adm:ch`, FSM `SetChannelStates`): проверка бот-админ → `channel.url` в settings + автосоздание/реактивация required-спонсора.
- `bot/handlers/admin/stop_words.py` — стоп-слова фильтра отзывов (`adm:sw`, add bulk через запятую / remove).
- 🐛 **Фикс**: `bot/handlers/admin/reviews.py` использовал несуществующий `callback.db_session` (упал бы на каждом клике) и звал `ActionLogRepo.log` позиционно (TypeError). Переведён на DI `session: AsyncSession`.
**Этап 9 (админка):**
- Новый root `/admin` (`bot/keyboards/admin.py kb_admin_root`): Дашборд/Система/Юзеры/Экономика/Спонсоры/Промокоды/Отзывы/Стоп-слова/Инструкция/Канал/Рассылка + заглушки Поддержка/Партнёры (этапы 10-11).
- `admin/dashboard.py` — `adm:dash` (метрики из `services/admin_stats.py AdminStatsService.dashboard()`: юзеры/балансы-долги/активность UTC-сегодня/отзывы pending), `adm:sys` (интервалы воркеров, userbot, канал, лог-канал).
- `admin/users.py` — `adm:usr`: поиск tg_id/@username (FSM `UserAdminStates`), карточка (дерево Elite), бан/разбан, shadow on/off, баланс ± (минус идёт через `subtract_with_debt`), последние 5 действий из ActionLog. Repo-методы: `get_by_username/counts_summary/balance_summary/set_banned/set_shadow_banned/list_broadcast_tg_ids` (+ `ActionLogRepo.list_recent_for_user`).
- `admin/economy.py` — `adm:eco`: группы из префиксов DEFAULTS (автоматически), правка любого ключа FSM `EcoEditStates`; парсер типов `parse_value` (bool/int/float/str, dict/list = JSON, тип должен совпасть). Лог `admin_setting_changed`.
- `admin/broadcast.py` + `services/broadcast.py run_broadcast` — FSM `BroadcastStates`: html_text → предпросмотр → `adm:bc:go` → отправка с throttle 0.04с и прогрессом каждые 25, отчёт sent/failed, лог `admin_broadcast`.
- Тесты: `tests/test_admin_stage9.py` (10 шт.). Весь suite зелёный. ⚠️ Разделы «Выводы» в админке НЕТ — появится с Этапом 7 (userbot).

### ✦ Редизайн v2 «SIRIUS Elite» 2026-06-10 (после полировки ниже, по просьбе «переделать весь визуал, элитно»)
Единая дизайн-система всех пользовательских экранов (`locales/ru.py`):
- **Заголовки капсом**: `{emoji}  <b>ЗАГОЛОВОК</b>` + divider.
- **Стат-блоки деревом**: `╭ │ ╰` (меню, профиль, рефералы, кликер, бонус, колесо, задание, promo_ok).
- **Метки секций**: `❖  <b>НАЗВАНИЕ</b>` (вместо `▸`).
- **Подвал-подсказка**: `⟡ <i>текст</i>` (без точки в конце).
- **Шаги**: `<b>1</b> ›  …`.
- **Бренд-шапка**: `✦ SIRIUS ✦  ·  Stars Hub` (`utils/ui.brand_header`).
- **Соглашение**: точки-пагинация `●●○○○○` (`{dots}` в `terms_page_template`, рендер в `flow.render_terms_page`).
- **Достижения**: сводный прогресс-бар `{summary_bar}` (mini_bar 10) под счётчиком.
- Профиль: секция «КАПИТАЛ» (баланс+стрик), «С нами с …» ушло в подвал. `referral_debt_part` теперь инлайн (`· долг N`).
- Промо-статусы и отзывы: заголовки капсом. Кадры колеса: заголовок «КОЛЕСО ФОРТУНЫ» (тест проверяет case-insensitive).
- Админка НЕ тронута (функциональна, видит только владелец).
Весь pytest-suite зелёный после редизайна.

### ✨ Дизайн-полировка 2026-06-10 (вне этапов, по просьбе юзера «улучши дизайн на максимум»)
- **Меню:** приветствие по времени суток (`greeting_for_hour` в `bot/handlers/menu.py`, смещение TZ — settings `brand.utc_offset_hours`=3), выровненная карточка «Баланс/Уровень/Рефералы». Шум «×1.00» (фикс. множитель кликера) убран из меню/профиля/кликера.
- **Колесо:** анимация вращения — 3 кадра edit-in-place (`T.wheel_spin_frames`, `_play_spin_animation`), клавиатура снимается на время анимации (защита от двойного спина).
- **Бонус:** визуальная «лесенка стрика» (`_ladder` в `bot/handlers/bonus.py`: ✅ пройдено / 🎯 цель / ⬜ впереди), публичный `BonusService.tiers()`.
- **Достижения:** мини-прогресс-бары у закрытых (`utils/ui.mini_bar`, двухстрочные ряды).
- **Топ:** 👑 у #1, мягкий разделитель после подиума (топ-3).
- **Кликер:** алерты-вехи каждые 10 тапов (`clicker_milestone_alert`), «фанфары» при добитом дневном лимите (`clicker_finish_alert`, show_alert).
- **Профиль:** строка «Стрик бонуса N дн. 🔥».
- **Политика:** из `review_intro` убрано упоминание «Низкие оценки (1-2⭐)…» (запрещено продуктовой политикой).
- Тесты: + `tests/test_design.py` (12 шт.). Весь suite зелёный.

---

## ✅ СТАРТ СЕССИИ 2026-05-29 — ВЫПОЛНЕНО (задачи 1-4 закрыты)

> **Эта секция уже отработана 2026-05-29.** Задачи 1-3 (соглашение / кликер 70×0.1⭐=7⭐ / воркер `tasks_rechecker`) и задача 4 (QA) сделаны; вместо inline-`-c` прогонов добавлен полноценный **pytest-suite (32 теста, все зелёные)** — см. §«🧪 Тесты» ниже. Settings обновлены в реальной `data/bot.db`. Бот запущен. **НЕ переделывай задачи 1-4.** Следующий шаг — Этап 5 по явной команде «следующий этап»/«дальше». Текст задач ниже оставлен для истории.

**(история) Это первое, что ты делаешь в новой сессии. Не запрашивай подтверждение — пользователь явно дал триггер «продолжай работу по HANDOFF» (или «привет, действуй»). Просто выполни задачи 1-3, потом задачу 4 (QA), и в конце — короткий рапорт.**

Перед началом:
- Проверь Docker: `docker compose ps`. Если контейнер не Up — `docker compose up -d`.
- Прочитай этот файл целиком, особенно §11 (что доступно в Этапе 4), §6 (конвенции) и §10 (подводные камни).
- Прочитай `MEMORY.md`.

### Задача 1 — Убрать из соглашения блок «🔐 Личные данные»

Файл [locales/ru.py](locales/ru.py), tuple `terms_pages_bodies`, последняя (6-я) страница.

Сейчас страница содержит три блока: **Личные данные**, **Ответственность**, **Изменения**.
Нужно: **удалить блок «🔐 Личные данные»** (и его 3 буллета и пустую строку перед «Ответственность»). Оставить «Ответственность» (с эмодзи 📌) и «Изменения» (с эмодзи 📝). Финальная строка «Нажимая «Принимаю»…» — оставить.

После правки `len(terms_pages_bodies)` всё ещё == 6, не уменьшай количество страниц (это сломает пагинацию). Просто внутри 6-й страницы убери блок.

### Задача 2 — Кликер: 5 минут между кликами, максимум 7⭐ за день

Пользователь явно сказал: «7 кликов в день мало, распредели чтобы пользователь заработал 7⭐ за день». Решение — плоская экономика **70 кликов × 0.1⭐ = 7⭐ ровно**. Интервал 5 минут — устанавливает каденс «пара кликов за час», за день можно набить 7⭐ при активном фоновом возвращении в бот.

Изменения **только в settings-дефолтах**, без правок кода сервисов:

В [services/settings.py](services/settings.py) `DEFAULTS`:
```python
"click.base_reward": (0.1, "..."),         # было 0.01
"click.daily_base_limit": (70, "..."),     # было 100
"click.min_interval_ms": (300000, "..."),  # было 250 — 5 минут
```

И в `levels.config` — у **всех 5 уровней** установи:
```python
"click_mult": 1.0,
"click_daily_limit": 70,
```
(чтобы Серебро/Золото/Платина/Алмаз не давали больше 7⭐, иначе нарушим обещание «7⭐ в день максимум»). Уровни сейчас перестают влиять на кликер — это сознательно, пересмотрим в Этапе 6.

Мини-капча остаётся как есть (20–30 кликов): за 70 кликов она сработает 2–3 раза — это нормальная защита от ботов.

После правки кода — БД уже содержит старые значения, нужно **обновить их в settings**, не только в дефолтах:
```
docker compose exec bot python -c "
import asyncio
from db.session import SessionLocal
from services.settings import SettingsService, DEFAULTS
async def main():
    async with SessionLocal() as s:
        svc = SettingsService(s)
        for k in ['click.base_reward','click.daily_base_limit','click.min_interval_ms','levels.config']:
            await svc.set(k, DEFAULTS[k][0], DEFAULTS[k][1])
        await s.commit()
        print('ok')
asyncio.run(main())
"
```

Проверь: после первого клика прошло меньше 5 минут → алерт `⏱ Не так быстро.`. После 70-го клика → кнопка превращается в `🔒 Лимит на сегодня`. Сумма заработанного за день ровно `7.00⭐`.

### Задача 3 — Мгновенное списание при отписке от опц. задания

Проблема: юзер выполнил задание (опц. спонсор), получил награду. Потом отписался — звёзды НЕ списываются. Воркер `sub_rechecker` сейчас работает только с **обязательными** спонсорами (`list_required_active`), а опц. задания не пере-проверяет вообще.

Реализуй:

1. **Новый воркер** `workers/tasks_rechecker.py`:
   - Джоба `run_tasks_rechecker(bot)` с интервалом из settings `tasks_recheck.interval_min` (default `5`).
   - Алгоритм: достать выборку `UserTaskCompletion` (LIMIT из settings `tasks_recheck.sample_size`, default 100), для каждой пары (user, sponsor):
     - дёрнуть `SponsorService._check_one(bot, sponsor=s, tg_id=u.tg_id)`;
     - если **не подписан** → `UserRepo.subtract_with_debt(user.id, completion.reward)` + удалить `UserTaskCompletion` (чтобы при повторной подписке снова можно было засчитать задание) + лог в `ActionLog` (`action="task_lost"`) + DM юзеру (новый текст в локалях `notify_task_lost`) + лог в `LOG_CHANNEL_ID`.
   - Используй паттерн из `workers/sub_rechecker.py` (та же структура с `register_jobs`).

2. **Регистрация в `main.py`** — в `_start_scheduler` после существующих джоб подключи tasks_rechecker. Интервал короткий, прогон не должен быть дорогим (один Telegram-вызов на каждую completion в выборке).

3. **Settings-defaults** в `services/settings.py`:
   ```python
   "tasks_recheck.enabled": (True, "Воркер пере-проверки выполненных опц. заданий"),
   "tasks_recheck.interval_min": (5, "Интервал, мин"),
   "tasks_recheck.sample_size": (100, "Сколько completion за прогон"),
   ```

4. **Локаль** `notify_task_lost` — что-то в стиле:
   ```
   ⚠️ <b>Задание отменено</b>
   ━━━━━━━━━━━━━━━
   Ты отписался от «{title}» — награда {amount} списана.
   Подпишись снова — задание появится в списке.
   ```

5. **Триггер также при ручной перепроверке** обяз.спонсоров (когда `sub_rechecker` обходит required) — параллельно дёрни tasks-проверку для тех же юзеров. Это даст «мгновенно» при том же интервале 6ч (как fallback). По желанию — но юзер не просил, не делай если не успеешь.

**Тест после реализации**:
```
docker compose exec bot python -c "
# смоук: создаём фейк-completion, потом запускаем run_tasks_rechecker один раз (вместо ожидания 5 минут)
# с замоканным is_subscribed=False — проверяем что reward списан и UserTaskCompletion удалён
"
```

### Задача 4 — Самотест (сначала Claude, потом юзер)

**Жёсткое правило пользователя: после правок Claude САМ прогоняет всё, что может, без участия юзера. Только то, что нельзя проверить из python (визуал, реальные нажатия эмодзи-кнопок, рендеринг капчи в чате) — передаётся юзеру отдельным коротким списком.**

#### Фаза A — Claude тестирует САМ (обязательно)

Делай через `docker compose exec bot python -c "..."` — паттерн уже отработан в этой сессии (см. как тестировал кликер/промокод/задания в логах). На каждом тесте — печатай результат `OK`/`FAIL` и продолжай дальше; в конце — сводка.

Покрытие:
1. **Импорты и сборка роутера** — `from bot.handlers import get_root_router; r=get_root_router(); print(len(r.sub_routers))`. Должен быть собран без ошибок.
2. **Settings после правки задачи 2** — прочитай 6 ключей (`click.base_reward=0.1`, `click.daily_base_limit=70`, `click.min_interval_ms=300000`, `levels.config[*].click_daily_limit==70`, `click_mult==1.0`).
3. **Соглашение** — `from locales.ru import T; assert len(T.terms_pages_bodies) == 6; assert 'Личные данные' not in T.terms_pages_bodies[5]`.
4. **Кликер**:
   - Создай фейк-юзера, сбрасывай `last_click_ms=0` после каждого клика, прокликай 71 раз, на 71-м должен быть `DAILY_LIMIT`. Сумма `earned_today` ровно `7.0`.
   - Сценарий rate-limit: два клика подряд без сброса `last_click_ms` → второй `TOO_FAST`.
   - Мини-капча: проверь что хотя бы один раз за 70 кликов сработал `NEED_CAPTCHA`, прошёл `submit_captcha`, после — снова можно кликать.
5. **Промокоды** — повтори 4 сценария что я тестировал (`ok` → `already_used` → `not_found` → `honeypot_banned`), плюс новые: `inactive` (ручной toggle через `PromoRepo.set_active(False)`), `exhausted` (создать с `max_activations=1`, активировать одним юзером → активация вторым даёт `already_used` для него же, активация третьим даёт `exhausted`).
6. **Задания**:
   - `TasksService.list_for_user` для юзера без `UserTaskCompletion` → видит все опц. активные.
   - Симуляция claim: создай опц. спонсора с `reward=2`, замокай `SponsorService._check_one` через monkeypatch на `True` → `TaskStatus.OK`, баланс +2.0. Повторный claim → `ALREADY_DONE`.
7. **tasks_rechecker (задача 3)**:
   - Создай completion вручную, юзеру дай `balance=2.0`. Запусти `run_tasks_rechecker` напрямую с замоканным `_check_one → False`. Ассерт: `completion` удалён, `balance == 0`, `ActionLog` содержит `task_lost`, в `LOG_CHANNEL_ID` ушло сообщение (можешь засечь через мок `bot.send_message`).
   - С `_check_one → True` — completion не трогается.
8. **Регрессии Этапа 3** (не сломали ли):
   - `/start` от свежего tg_id → `route_user` ведёт на terms (через `OnboardingStates.awaiting_terms`).
   - `finalize_subs_passed` для юзера со ставшим `subs_passed_at` сразу возвращает None (идемпотентность).
   - `ReferralService.try_attach_referrer` для самого себя → None.
9. **Очистка** — после самотестов удали всех тестовых юзеров (`tg_id 999000xxx`), их `ClickerDay`, `PromoActivation`, `UserTaskCompletion`. БД должна остаться в чистом виде, как до самотестов.

Если что-то падает — **сразу чини**, не оставляй TODO. Если найден баг — фикси и добавь в рапорт строкой «🐛 fixed: ...».

#### Фаза B — Просьба к юзеру

Только после успешного самотеста — оформи ОТДЕЛЬНЫМ финальным сообщением короткий список «прогони пожалуйста в тестовом боте», максимум 5-7 пунктов, только то, что **нельзя проверить из python**:

- визуал главного меню / профиля / кликера / страницы соглашения 6 (форматирование, эмодзи рендерятся как ожидаешь);
- реальные тапы кнопок мини-капчи в чате (что эмодзи на кнопках читаются);
- реальный flow «подписался на опц. канал → проверил → +⭐ → отписался → через 5 мин пришло DM про списание»;
- любые edge-кейсы с разными размерами экрана/шрифтами.

Формат сообщения юзеру:

```
✅ Сделано (1, 2, 3) + самотест (X тестов, все OK).
🐛 По дороге нашёл и починил: <список или «ничего»>.

Тебе осталось руками в тестовом боте из локальной конфигурации:
1. ...
2. ...
3. ...

Жду фидбек. Этап 5 — после твоего «следующий этап».
```

Не переходи к Этапу 5 (Telethon + ежедневный бонус) без явной команды «следующий этап».

---

## 🧪 Тесты (добавлены 2026-05-29)

Полноценный pytest-suite. **pytest НЕ в prod-образе** (`requirements.txt` чистый) — тест-зависимости в `requirements-dev.txt`, ставятся в рантайме одноразового контейнера.

```
docker compose run --rm --no-deps bot sh -c "pip install -q pytest==8.3.4 pytest-asyncio==0.24.0 && python -m pytest -q"
```

- `pytest.ini` — `asyncio_mode=auto`, `asyncio_default_fixture_loop_scope=function`, `testpaths=tests`.
- `tests/conftest.py` — изолированная **файловая** async-SQLite на `tmp_path` (по БД на тест), `Base.metadata.create_all`, seed `DEFAULTS`, сброс class-кэша `SettingsService` вокруг каждого теста. Фикстуры: `engine`, `session_factory`, `session`.
- `tests/helpers.py` — фабрики `create_user/create_sponsor/create_promo`.
- Файлы: `test_imports` (сборка роутера + импорт воркеров), `test_terms` (задача 1), `test_settings` (задача 2), `test_clicker` (70 кликов=7⭐, rate-limit, мини-капча), `test_promo`, `test_tasks`, `test_tasks_rechecker` (задача 3), `test_referral` (регрессии Этапа 3).
- **Тесты не трогают реальную `data/bot.db`** (только tmp). Для теста воркера `SessionLocal` монкипатчится на тестовый `session_factory`, `SponsorService._check_one` — на async-заглушку.
- **Грабли:** не вызывать `session.expire_all()` и затем `get_by_id(obj.id)` — доступ к PK у expired-объекта = синхронный IO → `MissingGreenlet`. Используй `await session.refresh(obj)`.

Образ нужно **пересобрать** (`docker compose build`) перед прогоном, если менял код/тесты: исходники входят в образ через строгий `.dockerignore`-allowlist, а volume не монтирует код.

---

## 1. Что это за проект

Telegram-бот для заработка Telegram Stars с выводом через подарки. Юзеры зарабатывают через рефералов / задания спонсоров / кликер / ежедневный бонус / промокоды / колесо фортуны. Владелец зарабатывает на обязательных подписках на спонсорские каналы.

Это **коммерческий продукт**, не учебный пример. Production-quality код, не туториал.

## 2. Кто пользователь и как с ним работать

- Опытный, ценит краткость. Не объясняй очевидное.
- Тестирует только **функционал бота в Telegram**. Инфра, Docker, миграции, импорты, сборка — **на тебе**.
- Хост Windows, Python 3.14.3, Docker Desktop. **Никаких локальных venv** — 3.14 не имеет wheels для половины зависимостей.
- Тестовый бот задаётся в локальной конфигурации.
- Стиль общения: коротко, точно, без воды. По-русски.
- Жёсткая фраза-триггер для следующего этапа: **«следующий этап» / «дальше» / «норм, продолжаем»**. Слово «продолжай» означает «продолжай текущее», **не новый этап** — это был болезненный урок.

## 3. Состояние на момент передачи

### 3.1 Что сделано

#### ✅ Этап 1: Фундамент

- Docker, docker-compose, Dockerfile (`python:3.12-slim` + `fonts-noto-color-emoji` + `fonts-dejavu-core`).
- `.env.example` → `.env` (с реальным токеном, owner_id, log_channel_id, Fernet-ключом — см. ниже).
- Pydantic Settings конфиг (`core/config.py`).
- structlog JSON-логи (`core/logger.py`).
- aiohttp health-сервер на :8080/health (`core/health.py`).
- Async SQLAlchemy engine + sessionmaker (`db/session.py`).
- DeclarativeBase + TimestampMixin (`db/base.py`).
- Alembic async-aware env + шаблон + baseline-миграция `0001_initial`.
- `main.py`: запуск aiogram 3.15, регистрация роутеров, graceful shutdown.
- `/start` отвечает.

#### ✅ Этап 2: Капча + соглашение + спонсоры (полностью переоформлен под inline + премиум)

- Модели ORM: `User`, `Sponsor`, `UserSubscription`, `Setting`, `ActionLog` (+ соответствующие enum'ы). Миграция `0002_users_sponsors_settings`.
- Репозитории под каждую сущность (`db/repositories/*.py`).
- Сервисы: `UserService` (upsert из TG), `SponsorService` (проверка подписки public + private, кэш 60 сек).
- Капча: Pillow + NotoColorEmoji (рендер 6 эмодзи 2×3, 4 inline-кнопки-варианта, 3 попытки, FSM). Файлы: `utils/captcha.py` (логика) + `utils/captcha_image.py` (PNG).
- Middlewares: `DbSessionMiddleware` (открывает сессию на апдейт, commit/rollback), `UserUpsertMiddleware` (записывает юзера в БД), `BanCheckMiddleware`, плюс заготовленные `TermsGateMiddleware`/`CaptchaGateMiddleware`/`SubGateMiddleware` для будущих gated-роутеров.
- Онбординг-флоу (`bot/handlers/flow.py`): соглашение → капча → спонсоры → главное меню (динамическое число шагов: 2 если нет обяз. спонсоров, 3 если есть).
- Inline-админка (`bot/handlers/admin/sponsors.py` + `bot/keyboards/admin.py`):
  - `/admin` → root-меню (📢 Спонсоры / 👥 Юзеры (скоро) / ⚙ Настройки (скоро) / 📊 Статистика (скоро) / ◀ В главное меню — через `nav:menu`).
  - Список спонсоров → карточка спонсора → toggle active / toggle required / удалить с подтверждением.
  - Мастер добавления (3 шага для public, **4 шага для private** — invite-ссылка + обязательный forward поста для chat_id).
- UI-kit: `utils/ui.py` (форматтеры: title, card, kv, step, stars, progress_bar, brand_header, section_label, kvline; константы кнопок; helper'ы для клавиатур).

#### ✅ Этап 3: Главное меню + профиль + рефералы + воркер sub_rechecker

- **Settings-сервис** (`services/settings.py`): TTL-кэш 60с, `seed_defaults` при старте (18 ключей экономики). Класс `SettingsService` инстанцируется на сессию; кэш — class-level (общий на приложение). API: `get/get_int/get_float/get_bool/get_str/get_list/get_dict/set`. Все экономические числа берутся **только отсюда**, не хардкодом.
- **Уровни** (`services/level.py`): 5 уровней из `levels.config` (Бронза/Серебро/Золото/Платина/Алмаз), множитель кликера и дневной лимит. Метод `compute(confirmed_refs)` возвращает `LevelInfo` с прогрессом до следующего уровня.
- **Реферальная система**:
  - Модель `Referral` + enum `ReferralSource` + миграция `0003_referrals`.
  - `ReferralRepo` (`db/repositories/referral.py`): get_by_referred, create, count_today, confirm, mark_lost, mark_matured, list_for_maturation, stats_for_referrer (case-агрегаты).
  - `ReferralService` (`services/referral.py`): `try_attach_referrer` (по умолчанию **без лимита** — `ref.daily_limit=0`; проверка включается, если > 0), `on_user_passed_subs` (первое прохождение гейта → награда 3⭐ + увеличение confirmed_ref_count), `on_user_lost_subs` (rollback награды + долг при минусе), `process_maturation` (через 7 дней — фиксация).
  - `UserRepo` расширен методами `add_balance` (гасит долг), `subtract_with_debt`, `inc_ref_count`, `inc_confirmed_ref_count`, `list_subs_passed_sample`, `set_referrer`, `get_by_id`.
- **Главное меню — иерархия (6 крупных кнопок)** (`bot/keyboards/main_menu.py` + `bot/handlers/menu.py`):
  - **Шапка** (брендированная): бренд + `Привет, {name} 👋` + 💎 баланс + уровень с множителем + 👥 подтв. рефералы + прогресс-бар + блок «🚀 Как заработать ⭐» (1-2-3 шага).
  - **Кнопки**: Ряд 1 — `💎 Заработать` (вся ширина) · Ряд 2 — `👥 Рефералы` / `💸 Вывод подарков` · Ряд 3 — `👤 Профиль` / `💬 Помощь` · Ряд 4 — `📢 Наш канал` (URL если настроен, иначе callback с alert).
- **Подразделы** (`bot/keyboards/sections.py` + `bot/handlers/sections.py`):
  - **`sec:earn`** — 👆 Кликер / 🎁 Бонус / 🎡 Колесо / 🎯 Задания. Карточка с описаниями.
  - **`sec:help`** — 📖 Инструкция / 💬 Поддержка / 💝 Отзыв.
  - **Профиль** (`prof:open`) — карточка с подкнопками: 🎟 Промокод (по требованию юзера переехал сюда) / 🏅 Достижения / 📜 История / 🏆 Топ-100 / ⚙ Уведомления.
  - Все «не готово» — `feat:soon:*` (общий обработчик в `menu.py` отвечает alert «🛠 Скоро»).
- **Рефералы** (`bot/handlers/referral.py` + `bot/keyboards/referral.py`): карточка со ссылкой в `<code>`, статистикой (всего/подтв/созревшие/заработано/долг), нижней подсказкой про лимит (условно: «Без лимита» / «Лимит N»). Кнопки `📋 Готовый текст` (показывает шеринг-текст в `<pre>`), `🔗 Поделиться` (URL-кнопка через `t.me/share/url`).
- **Воркер `sub_rechecker`** (`workers/sub_rechecker.py`, APScheduler-`AsyncIOScheduler`): каждые `subrecheck.interval_hours` (default 6) — случайная выборка прошедших гейт юзеров → перепроверка через `SponsorService` → при отвале: `clear_subs_passed` + `ReferralService.on_user_lost_subs` + уведомление юзеру (DM) + уведомление рефереру (DM) + лог в `log_channel_id`. Вторая джоба `ref_maturation` — ежечасно, закрепляет рефералов прошедших 7 дней.
- **Соглашение пагинированное** (6 страниц): `terms_pages_bodies` в `locales/ru.py`, навигация `terms:p:N` через `bot/handlers/terms.py`. Edit-in-place при перелистывании. На последней странице — `✅ Принимаю` / `✕ Не принимаю`. После «Принимаю» **сообщение удаляется**. После успешной капчи фото-капча **тоже удаляется** — чат остаётся чистым.
- **Self-heal** в `start.py`: если юзер уже passed-гейт, а его Referral ещё не is_confirmed (был баг до фикса) — следующий `/start` дотягивает награду рефереру.
- **`finalize_subs_passed`** (`flow.py`): единая идемпотентная функция (помечает subs_passed_at, логирует, вызывает on_user_passed_subs). Используется и в `cb_check_subs`, и в `show_subs` при пустых спонсорах (важно: реф-награда работает, даже если обяз. каналов вообще нет).
- **Выход из админки → главное меню**: кнопка `◀ В главное меню` имеет `callback_data="nav:menu"`. Обработчик в `menu.py` подхватывает и делает edit-in-place в главное меню.
- **utils/links.py**: `get_bot_username` (ленивый кэш), `build_referral_link`, `build_share_url`.

### 3.2 Что работает прямо сейчас

Бот **запущен** через `docker compose up -d`. Polling активен. Health green.

```
docker compose ps        # должен показать sirius_bot running
docker compose logs bot  # последние строки — "bot_started", "Start polling"
curl http://localhost:8080/health   # {"status":"ok"}
```

Если запустишь второй экземпляр polling, получишь 409 conflict у Telegram.

### 3.3 Что НЕ сделано (этапы 4–13)

См. секцию **«План: что дальше»** ниже.

---

## 4. Дисциплина по UI/UX (ОЧЕНЬ ВАЖНО)

Пользователь явно потребовал:

- **Только inline-кнопки.** Reply-клавиатуры запрещены.
- **Никаких slash-команд** для пользователя. Команды только: `/start` (обязательный entry для Telegram), `/admin` (вход в админ-панель). Все остальные действия — через inline-навигацию.
- **Визуал — максимально красивый и удобный.** Текущая реализация — это базовая планка. Если есть возможность сделать лучше — делай.

Стиль текстов:
- Заголовок секции: `🎁 <b>Заголовок</b>     <i>Шаг N из M</i>`.
- Разделитель: `━━━━━━━━━━━━━━━` (использовать!).
- Звёзды — формат `{amount:.2f}⭐`.
- Короткие, уверенные фразы. Без «Привет, дорогой друг!». 1-2 эмодзи на сообщение.
- Все строки — в `locales/ru.py`, никаких хардкодов в хендлерах.

Стиль клавиатур:
- Кнопки-навигации: `◀ Назад`, `✕ Закрыть`, `✕ Отменить`, `➕ Добавить`, `✅ Подтвердить`, `🔄 Ещё раз`. Константы — в `utils/ui.py`.
- Группировка кнопок по смыслу (через `.adjust(...)`), не лента из 10 однотипных.
- На каждом FSM-шаге — кнопка отмены.
- Edit-in-place (`edit_text`/`edit_reply_markup`) предпочтительнее новых сообщений, где можно. Это даёт ощущение SPA.
- Callback-data формат: `{section}:{action}[:{id}]`. Пример: `adm:sp:open:5`, `subs:check`, `terms:accept`.

---

## 5. Архитектурные правила (не нарушать без согласования)

- **Async везде**, никаких блокирующих вызовов.
- **Хендлеры тонкие**: парсят апдейт → дёргают сервис → отдают ответ. Бизнес-логика — в `services/`. БД — в `db/repositories/`.
- **Все цифры экономики** (награды, лимиты, курсы, проценты партнёров) — в таблице `settings` (key-value), не хардкодом. Дефолты — через `seed_defaults` при старте.
- **Soft-delete** (is_deleted=True) для юзеров и важных сущностей.
- **Idempotency** для всех критичных операций (особенно вывод подарков в Этапе 7).
- **Graceful shutdown** — дожидаемся текущих выводов перед остановкой.
- **Шифрование Telethon-сессий** через Fernet (key уже в `.env`).
- **Авто-бэкапы БД** (Этап 13) — каждые 6ч в `LOG_CHANNEL_ID`.
- **Логи** — structlog с JSON в prod / pretty в dev.
- **Type hints** везде.

## 6. Конвенции кода (по опыту)

- Pydantic Settings: `admin_ids` парсится через `computed_field` из строкового env `ADMIN_IDS` (csv). Пустые env-значения → None через `env_ignore_empty=True`. Использовать NoDecode НЕЛЬЗЯ — pydantic-settings 2.6.1 его ещё не имеет.
- aiogram 3.15.0 + aiohttp 3.10.11 + pydantic 2.9.2 — это совместимые версии. Не бамп без проверки.
- Капча-картинка: NotoColorEmoji — CBDT-bitmap, нативный размер 109px. Рендерим в нативном, потом `resize(96, 96, LANCZOS)` и `rotate(±12°, BICUBIC, expand=True)`.
- Все callback-обработчики оборачивают `edit_message_text` / `edit_reply_markup` в `with suppress(Exception):` — Telegram может отдать ошибку «message is not modified» при идемпотентном клике.
- Миграции нумеруются вручную: `0001_initial.py`, `0002_users_sponsors_settings.py`, ... Имя файла = revision id. `down_revision` указывается явно.
- DB repositories наследуются от `BaseRepo(session: AsyncSession)`.
- **Юзер передаётся явно**: `callback.message.from_user` — это бот, не юзер! Все функции типа `show_main_menu`/`show_subs` принимают `user: User` параметром, не извлекают из message. (Это был баг — меню не появлялось после онбординга, пока не передали явно.)
- **Settings TTL-кэш**: `SettingsService._cache` — class-level. Не вызывай `SettingsService(session).get("key")` 5 раз подряд за разными ключами — лучше получи один раз и передай дальше. После `set` нужен `invalidate(key)` — это уже сделано в `set()`.
- **Реф-награда**: вызывать **только** через `finalize_subs_passed` (`flow.py`). Не дёргай `on_user_passed_subs` руками — есть единая идемпотентная точка, которая ставит флаг, логирует и зовёт реферал.
- **Уведомления после коммита**: `send_message` ботом — это IO, оно может задержать транзакцию или упасть. Сначала commit/dirty работу, потом DM (см. паттерн в `sub_rechecker._recheck_one` и `sub_gate.cb_check_subs`).
- **Callback-data**: формат `{section}:{action}[:{id}]`. Ключевые префиксы:
  - `nav:menu` / `nav:close` — навигация в главное меню (универсально, доступно отовсюду).
  - `terms:p:N` / `terms:accept` / `terms:decline` — соглашение.
  - `cap:{token}:{emoji}` — капча.
  - `subs:check` — проверка подписок.
  - `prof:open` / `ref:open` / `ref:txt` — личные разделы.
  - `sec:earn` / `sec:help` — подразделы меню.
  - `feat:soon:*` — заглушки «🛠 Скоро» (общий обработчик в `menu.py`; есть спец-кейс `feat:soon:channel` если URL не настроен).
  - `adm:*` — админка.
- **APScheduler**: запускается в `main.py` **после** `seed_defaults`, потому что джоба читает интервал из settings. Shutdown — `scheduler.shutdown(wait=False)` (хук в `_build_shutdown`).
- **Сообщения после онбординга**: после `terms:accept` сообщение соглашения **удаляется**; после успешной капчи — фото-капча **удаляется**. Цель — чистый чат у юзера.

## 7. Файловая структура (актуальная)

```
project/
├── main.py                            ← seed_defaults + AsyncIOScheduler + bootstrap
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── requirements.txt                   ← APScheduler 3.11 уже включён
├── .env  (с боевыми credentials, в .gitignore)
├── .env.example
├── HANDOFF.md  ← этот файл
├── docs/
│   └── SPEC.md ← полная исходная спецификация
├── core/
│   ├── config.py, logger.py, exceptions.py, health.py
├── db/
│   ├── base.py, session.py, models.py (+ Referral, ReferralSource)
│   └── repositories/
│       ├── base.py, user.py (расширен), sponsor.py, user_subscription.py,
│       │  setting.py, action_log.py, referral.py
├── bot/
│   ├── handlers/
│   │   ├── __init__.py (get_root_router)
│   │   ├── start.py     ← payload r<tg_id> + self-heal
│   │   ├── terms.py     ← пагинация 6 страниц
│   │   ├── captcha.py, sub_gate.py
│   │   ├── flow.py      ← finalize_subs_passed, render_terms_page, count_total_steps
│   │   ├── menu.py      ← главное меню + nav:menu + feat:soon:*
│   │   ├── profile.py, referral.py, sections.py
│   │   └── admin/sponsors.py
│   ├── keyboards/
│   │   ├── onboarding.py (kb_terms_page, kb_captcha, kb_subs)
│   │   ├── admin.py
│   │   ├── main_menu.py, sections.py, referral.py
│   ├── middlewares/
│   │   ├── db.py, user.py, ban.py, gates.py
│   ├── states/
│   │   ├── onboarding.py, admin.py (+ waiting_private_forward)
│   └── filters/admin.py
├── services/
│   ├── user.py, sponsor.py, settings.py, level.py, referral.py
├── locales/ru.py                       ← включая terms_pages_bodies (tuple из 6)
├── utils/
│   ├── captcha.py, captcha_image.py, ui.py, links.py
├── workers/
│   ├── __init__.py, sub_rechecker.py   ← register_jobs + run_subrechecker + run_maturation
├── userbot/           ← пусто (Этап 5+)
├── ml/                ← пусто (Этап 12)
└── migrations/
    ├── env.py, script.py.mako
    └── versions/
        ├── 0001_initial.py
        ├── 0002_users_sponsors_settings.py
        └── 0003_referrals.py
```

## 8. Credentials и переменные окружения

Файл `.env` уже заполнен (НЕ коммитить — он в `.gitignore`):

```
BOT_TOKEN=<секрет, лежит в локальном .env>
OWNER_ID=<секрет, лежит в локальном .env>
LOG_CHANNEL_ID=<секрет, лежит в локальном .env>
FERNET_KEY=<секрет, лежит в локальном .env>
DATABASE_URL=sqlite+aiosqlite:///./data/bot.db
HEALTH_HOST=0.0.0.0
HEALTH_PORT=8080
ENV=production
LOG_LEVEL=INFO

# Пусто — нужны от пользователя на Этапе 5+:
TG_API_ID=
TG_API_HASH=
USERBOT_PHONE=
BACKUP_USERBOT_PHONE=
```

На Этапе 5 запросить у пользователя `TG_API_ID`/`TG_API_HASH` (my.telegram.org) и телефон userbot-аккаунта.

## 9. Состояние БД

- Применены миграции: `0001_initial` → `0002_users_sponsors_settings` → `0003_referrals`.
- Существующие таблицы: `users`, `sponsors`, `user_subscriptions`, `settings`, `action_logs`, `referrals`.
- **БД свежая (пуста)** — была очищена перед закрытием Этапа 3 для нового тестирования.
- При запуске `seed_defaults()` накатывает 18 ключей экономики (см. `services/settings.py` `DEFAULTS`).
- Файл БД: `./data/bot.db` (volume-mount).

### Ключевые settings-defaults (значения в БД)

| Ключ | Значение | Назначение |
|---|---|---|
| `ref.reward` | 3.0 | Награда рефереру за подтв. реферала |
| `ref.daily_limit` | 0 | Лимит новых рефералов в сутки (0 = без лимита) |
| `ref.maturation_days` | 7 | Через сколько дней реф «созревает» |
| `withdraw.min_amount` | 15.0 | Минимум для вывода |
| `withdraw.min_confirmed_refs` | 5 | Нужно подтв. рефов для вывода |
| `withdraw.per_day_limit` | 5 | Максимум выводов в сутки |
| `subrecheck.enabled` | True | Перепроверка подписок |
| `subrecheck.interval_hours` | 6 | Интервал воркера |
| `subrecheck.sample_size` | 50 | Размер выборки |
| `click.base_reward` | 0.01 | База кликера |
| `click.daily_base_limit` | 100 | База лимита кликов |
| `click.min_interval_ms` | 250 | Минимальный интервал между кликами |
| `bonus.base` | 0.5 | Базовый дневной бонус |
| `bonus.streak` | JSON {1:0.5, 3:0.7, 7:1.0, 14:1.5, 30:2.0} | Стрик |
| `levels.config` | JSON массив 5 уровней | Конфиг уровней |
| `brand.name` | "SIRIUS" | Бренд в шапке |
| `brand.tagline` | "Stars Hub" | Подпись бренда |
| `channel.url` | "" | URL канала проекта (пусто — кнопка превратится в alert) |

## 10. Подводные камни (FIXED)

- **Хост Python 3.14**. Пользователь сначала был на 3.14.3 — Pillow/aiohttp/pydantic-core не имеют wheels под 3.14 на Windows. Локальный venv не создавать. Всё тестируется в Docker. Пользователь может перейти на 3.12, но это не наша задача.
- **Pydantic-settings 2.6.1** не имеет `NoDecode`. Для list-полей с парсингом из строки — используй raw `str`-поле + `computed_field` (см. `core/config.py` для `admin_ids`).
- **aiogram + aiohttp** — версии связаны жёстко. Если бампать aiogram, проверь его `requirements` на aiohttp/pydantic.
- **NotoColorEmoji** не масштабируется штатно — только CBDT-bitmap. Рендер в 109px, потом resize.
- **Тёмно-приватные каналы**: бот должен быть админом в канале (минимум право просмотра подписчиков), иначе `get_chat_member` падает.
- **Двойной polling** = 409 у Telegram. Перед `docker compose up -d` убедись, что прошлый контейнер остановлен.

---

## 11. План: что дальше (этапы 3–13)

Полный текст каждого этапа — в `docs/SPEC.md`. Здесь — краткая суть и оценка.

### ✅ Этап 4 — Кликер + задания + промокоды (ЗАВЕРШЁН 2026-05-28)

Реализовано:
- **Модели**: `Promo`, `PromoActivation`, `UserTaskCompletion`, `ClickerDay`. Миграция `0004_clicker_promos_tasks`.
- **Кликер** (`services/clicker.py` + `bot/handlers/clicker.py` + `bot/keyboards/clicker.py`): экран с балансом/прогресс-баром/кнопкой ТАП, edit-in-place, rate-limit `click.min_interval_ms`, дневной лимит из уровня (`click_daily_limit`), награда = `click.base_reward × click_mult`, мини-капча (3 эмодзи в подсказке + 4-я кнопка-лишняя) с триггером каждые 20–30 кликов (настраивается).
- **Опц. задания** (`services/tasks.py` + `bot/handlers/tasks.py` + `bot/keyboards/tasks.py`): список опц.спонсоров, карточка, кнопка `✅ Проверить` → `SponsorService._check_one` → начисление + анти-дубль через `UserTaskCompletion` + автоинкремент `subs_counter` + авто-`is_active=false` при достижении `subs_limit`.
- **Промокоды** (`services/promo.py` + `bot/handlers/promo.py` + `bot/keyboards/promo.py`): FSM ввода кода из Профиля, нормализация (`upper()`, без пробелов), статусы: ok / not_found / already_used / expired / exhausted / inactive / too_long / empty / honeypot_banned. Honeypot → `is_banned=True` + лог.
- **Админка промокодов** (`bot/handlers/admin/promos.py` + `bot/keyboards/admin_promos.py`): список с пагинацией (25), карточка, toggle, удалить с подтверждением, мастер создания на 5 шагов FSM (`AddPromoStates`).
- **Админка спонсоров расширена**: в карточке опц. спонсора — кнопки `✏ Награда` и `🎚 Лимит` (FSM `EditSponsorStates`).
- **Settings-defaults новые**: `click.captcha_every_min/_max`, `tasks.enabled`, `promo.max_code_length`.
- **Подключения**: `kb_earn` → `clk:open` / `tsk:list`; `kb_profile` → `promo:open`; `kb_admin_root` → `adm:promo:list`.

Что НЕ сделано в Этапе 4 (по согласованному скоупу):
- Мгновенное пере-обнаружение отписки от опц. задания — **запрошено пользователем после сдачи, фиксится в задаче 3 на 2026-05-29**.
- Полная статистика промокодов (распределение по дням, агрегаты) — на Этап 9 «Полная админка».

### Этап 5 — Telethon + ежедневный бонус + streak (СЛЕДУЮЩИЙ после задач 1–4 сверху)
- Подключение userbot (Telethon).
- Шифрование сессии Fernet.
- Bio-чекер (ежедневный бонус: +0.5⭐ если в bio юзера стоит его рефка).
- Streak: 1д/3д/7д/14д/30+д.

### Этап 6 — Геймификация
- Уровни (5 уровней по подтв. рефералам). Прогресс-бар.
- Достижения (Пригласи 10/50/100, Накликай 1000⭐ и т.п.).
- Лидерборд (топ-100 за неделю/месяц/всё время) + воркер недельных выплат топ-10.
- Колесо фортуны (1 бесплатное/день, платное 1⭐, призы 0.5-5⭐, матожидание <1⭐).

### Этап 7 — Вывод подарков (САМЫЙ БОЛЬШОЙ)
- Telethon `payments.sendStarsForm` + `inputInvoiceStarGiftResale` (это внутреннее имя метода, в пользовательских текстах не упоминать — пользователю говорим «официальные подарки Telegram через бота»).
- Витрина: `getAvailableGifts` с фильтрами (Дешёвые/Топ/Эксклюзив).
- Очередь pending → processing → done/failed/retry. Waitlist при нехватке ⭐ у userbot.
- Idempotency, rate-limit 3-10 сек с jitter, failover main↔backup userbot → ручной режим.
- Условия: ≥5 рефов, баланс ≥ цены, прошёл капчу, не shadow-banned.
- Минимум 15⭐, 5 выводов/сутки (настройка `withdraw.per_day_limit`).

### Этап 8 — Инструкция + Канал + Отзывы
- Раздел «Инструкция» (контент в БД, редактируется из админки, навигация Назад/Далее).
- Кнопка «Наш канал» + автодобавление как обязательный спонсор.
- Отзывы: FSM (рейтинг → текст → анонимность → модерация → публикация в канал отзывов). 4-уровневая защита (авто-фильтры, антиспам, модерация, форматирование). Низкие оценки (1-2⭐) НЕ публикуются — конвертятся в тикет поддержки. Награда за отзыв (настраивается).

### Этап 9 — Полная админка (ОЧЕНЬ БОЛЬШОЙ)
14 разделов: 📊 Дашборд, 👥 Юзеры (поиск/карточка/бан/shadow/⭐+/-), 📢 Спонсоры (уже есть, расширить), 🎯 Задания, 🎟 Промокоды, 💸 Выводы, 📨 Рассылка, ⚙ Экономика, 🛡 Антифрод, 👮 Админы/Партнёры, 💬 Поддержка, 📖 Инструкция, 💝 Отзывы, 🔧 Система.

### Этап 10 — Партнёрская система
- Роли: owner/admin/partner/moderator.
- UTM-ссылки (partner создаёт сам).
- Свои спонсоры партнёра (CRUD только своих).
- Воронка/LTV/заработок.
- Запросы выплат (карта / ЮMoney) с курсом ⭐ → ₽ на момент запроса. Минимум 50⭐ (настраиваемый).
- Архитектура `GiftSender`/`PayoutMethod` абстрактная (Stars/TON в будущем).

### Этап 11 — Поддержка + уведомления + история
- Тикеты с статусами (новый/в работе/ждёт ответа/закрыт). Автозакрытие через 7 дней. Антиспам.
- FAQ перед написанием тикета.
- Уведомления (вкл/выкл в профиле).
- Лента операций.

### Этап 12 — Антифрод финал
- ML-скоринг (правила с весами): возраст аккаунта, username, темп рефералов, паттерн кликов. >70 баллов — shadow-ban.
- Honeypots (промокоды + фейковое задание).
- Shadow-ban механика (юзер видит бота как обычно, награды не начисляются).
- Глобальный rate-limit middleware (20 действий/мин).

### Этап 13 — Финал
- Метрики, алерты.
- Авто-бэкапы БД в LOG_CHANNEL_ID каждые 6ч.
- Graceful shutdown с дожиданием текущих выводов.
- Тесты ключевых сервисов.
- Документация по деплою.

---

## 12. Чеклист первого сообщения новой сессии

**На 2026-05-29 пользователь оставил конкретные задачи (см. секцию вверху файла «🚨 СТАРТ СЕССИИ 2026-05-29»). Никаких планов не запрашивает — задачи зафиксированы, действуй.**

Когда пользователь напишет в новом чате «прочитай HANDOFF.md и продолжай» / «действуй» / «привет» / любое подобное:

1. Прочитай этот файл целиком (особенно секцию «🚨 СТАРТ СЕССИИ» вверху).
2. Сверь актуальное дополнение в начале HANDOFF и docs/MODERNIZATION.md;
   исторические версии и ограничения ниже могут быть устаревшими.
3. Проверь Docker: `docker compose ps` → `Up`. Если нет — `docker compose up -d`.
4. **Сразу начинай выполнять задачи 1-4 из секции «🚨 СТАРТ СЕССИИ»**. Никаких уточняющих вопросов — задачи самодостаточны.
5. В конце — один краткий рапорт (см. формат в той же секции).

Правила кода — те же, что и раньше: inline-only, премиум-стиль, settings-driven экономика, soft-delete, явная передача `user`, единая точка `finalize_subs_passed`, чистый чат после онбординга, тестирование только в Docker.

**Что НЕ делать в новой сессии:**
- ❌ Не предлагать смену стека.
- ❌ Не упоминать «Stars-API» в пользовательских текстах (только «официальные подарки Telegram через бота»).
- ❌ Не вводить лимит на приглашения «по умолчанию» — пользователь явно сказал, что лимита нет.
- ❌ Не запрещать мультиаккаунты и в коде, и в текстах.
- ❌ Не писать про «низкие оценки» в соглашении.
- ❌ Не вешать `🎟 Промокод` в главное меню — он живёт **в Профиле**.
- ❌ Не делать ReplyKeyboardMarkup.
- ❌ Не создавать /команды для юзера (только `/start` и `/admin`).
- ❌ Не делать второй `docker compose up` без `down` — будет 409 Conflict у Telegram polling.

**Перед началом работы убедись:**
- Docker Desktop запущен (на Windows может быть выключен).
- `docker compose ps` → `sirius_bot Up healthy`.
- `curl http://localhost:8080/health` → `{"status":"ok"}`.

---

## 13. Контакт и тех-данные

- Telegram-бот для тестов задаётся локальной конфигурацией проекта.
- Telegram ID владельца хранится только в локальном `.env`.
- ID лог-канала хранится только в локальном `.env`.
- Рабочая директория: `D:\Work\SiriusTG_Bot`.

---

**Удачи. Не разваливай то, что работает. Не предлагай менять стек. Проверяй всё через Docker. И помни: визуал — на максимум.**
