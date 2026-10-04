from __future__ import annotations

from types import SimpleNamespace


T = SimpleNamespace(
    # ---------- общие ----------
    health_ok="ok",
    banned="Доступ к боту ограничен.",
    error_generic="Не удалось выполнить действие. Попробуй ещё раз чуть позже.",
    forbidden="Это действие недоступно для твоего аккаунта.",
    closed="Окно закрыто.",
    stale_screen_alert="Этот экран устарел. Открой раздел заново.",
    private_chat_only="Открой SIRIUS в личном чате с ботом. Здесь личные разделы недоступны.",
    navigation_hint="Выбери раздел на кнопках ниже.",
    text_input_required="Пришли текст одним сообщением.",

    # ---------- единая навигация ----------
    btn_back="‹ Назад",
    btn_back_menu="‹ Главная",
    btn_back_earn="‹ Награды",
    btn_back_help="‹ Помощь",
    btn_back_profile="‹ Профиль",
    btn_back_admin="‹ Управление",
    btn_cancel="✕ Отменить",
    btn_refresh="↻ Обновить",

    # ---------- gates (текст для middleware-блокировок будущих этапов) ----------
    gate_terms_required="Сначала прими соглашение. /start",
    gate_captcha_required="Сначала пройди проверку. /start",
    gate_subs_required="Сначала подпишись на каналы. /start",

    # ---------- /start заглушка / финал онбординга ----------
    main_menu_stub=(
        "<b>Добро пожаловать, {name}</b>\n"
        "──────────────\n"
        "\n"
        "Проверки пройдены. Открой главное меню, чтобы увидеть доступные действия."
    ),

    # ---------- MAIN MENU (премиум-панель) ----------
    greeting_morning="Доброе утро",
    greeting_day="Добрый день",
    greeting_evening="Добрый вечер",
    greeting_night="Доброй ночи",
    menu_caption=(
        "{brand}\n"
        "──────────────\n"
        "\n"
        "{greeting}, <b>{name}</b>\n"
        "\n"
        "╭ Доступно  <b>{balance}</b>\n"
        "│ Уровень  <b>{level_emoji} {level_name}</b>\n"
        "╰ Подтверждённых друзей  <b>{confirmed_refs}</b>\n"
        "\n"
        "❖ <b>Следующий шаг</b>\n"
        "<b>{today_action}</b>\n"
        "{today_hint}\n"
        "\n"
        "<blockquote expandable><b>Уровень и награды</b>\n"
        "{progress_bar}\n"
        "{progress_text}\n"
        "За подтверждённого друга — {ref_reward}. Условия — в «Моя команда».</blockquote>\n"
        "\n"
        "⟡ <i>Баланс — внутренние единицы SIRIUS, отдельно от Stars Telegram.</i>"
    ),
    menu_progress_to_next="<i>До уровня «{next_name}» — ещё <b>{to_next_text}</b></i>",
    menu_progress_max="<i>Достигнут максимальный уровень.</i>",

    # Главное меню — 6 крупных хабов
    btn_menu_earn="✨ Награды",
    btn_menu_referrals="👥 Моя команда",
    # Этап 7 не начат: кнопку не показываем, ключ оставлен для совместимости.
    btn_menu_withdraw="Получение пока недоступно",
    btn_menu_profile="👤 Профиль",
    btn_menu_help="💬 Помощь",
    btn_menu_channel="📣 Канал SIRIUS",

    # Подраздел «Заработать»
    section_earn_caption=(
        "✨ <b>Награды</b>\n"
        "──────────────\n"
        "\n"
        "Выбери доступное действие. Сумма и условия показаны до получения.\n"
        "\n"
        "<b>Каждый день</b>\n"
        "Бонус за серию посещений · кликер\n"
        "\n"
        "<b>Другие способы</b>\n"
        "Задания · колесо · приглашения\n"
        "\n"
        "⟡ <i>В «Мой день» видно, что доступно сейчас. Начисления — во внутренних единицах.</i>"
    ),
    btn_earn_clicker="👆 Кликер",
    btn_earn_bonus="🎁 Бонус дня",
    btn_earn_wheel="🎡 Колесо",
    btn_earn_tasks="🎯 Задания",

    # Подраздел «Помощь»
    section_help_caption=(
        "💬 <b>Помощь</b>\n"
        "──────────────\n"
        "\n"
        "<b>Инструкция</b>\n"
        "Условия наград и работа бота.\n"
        "\n"
        "<b>Поддержка</b>\n"
        "Вопрос, ответ и история обращения.\n"
        "\n"
        "<b>Отзыв</b>\n"
        "Поделись впечатлением о SIRIUS."
    ),
    btn_help_instructions="Инструкция",
    btn_help_support="Поддержка",
    btn_help_review="Оставить отзыв",

    # Подменю Профиля
    btn_profile_promo="Промокод",
    btn_profile_achievements="Достижения",
    btn_profile_history="История счёта",
    btn_profile_top="Рейтинг",
    btn_profile_notifications="Уведомления",

    # ---------- SUPPORT (Этап 11, юзер-сайд) ----------
    support_disabled_alert="Поддержка временно недоступна. Загляни позже.",
    support_home=(
        "💬 <b>Поддержка</b>\n"
        "──────────────\n"
        "\n"
        "Создай обращение или продолжи переписку. Ответ придёт в этот чат.\n"
        "\n"
        "Частые вопросы — в «Вопросы и ответы».\n"
        "\n"
        "⟡ <i>Не присылай пароль, код входа или данные сессии.</i>"
    ),
    btn_support_faq="Вопросы и ответы",
    btn_support_new="Задать вопрос",
    btn_support_my="Мои обращения",
    btn_support_back="‹ В поддержку",

    support_faq_home=(
        "❓ <b>Вопросы и ответы</b>\n"
        "──────────────\n"
        "\n"
        "Выбери вопрос на кнопках ниже.\n"
        "\n"
        "⟡ <i>Если ответа нет, создай обращение в поддержку.</i>"
    ),
    support_faq_empty=(
        "<b>Вопросы и ответы</b>\n"
        "──────────────\n"
        "\n"
        "Готовых ответов пока нет. Создай обращение — поддержка ответит в этом чате."
    ),
    support_faq_answer=(
        "<b>Вопросы и ответы</b>\n"
        "──────────────\n"
        "\n"
        "<b>{question}</b>\n"
        "\n"
        "{answer}"
    ),
    btn_support_faq_back="‹ К вопросам",

    support_new_prompt=(
        "<b>Новое обращение</b>\n"
        "──────────────\n"
        "\n"
        "Опиши вопрос одним сообщением: что произошло и на каком экране.\n"
        "\n"
        "⟡ <i>От {min_len} до {max_len} символов.</i>"
    ),
    support_too_many_alert="Лимит обращений за час исчерпан. Попробуй позже.",
    support_text_too_short="Добавь подробности: нужно от {min_len} символов.",
    support_text_too_long="Сократи сообщение до {max_len} символов.",
    support_reply_empty="Сообщение не может быть пустым.",
    support_reply_too_long="Сообщение слишком длинное. Максимум — {max_len} символов.",
    support_created=(
        "<b>Обращение #{id} принято</b>\n"
        "──────────────\n"
        "\n"
        "Ответ придёт в этот чат. Переписка и статус доступны в «Мои обращения»."
    ),

    support_my_list=(
        "<b>Мои обращения</b>\n"
        "──────────────\n"
        "\n"
        "Выбери обращение, чтобы открыть статус и переписку."
    ),
    support_my_empty=(
        "💬 <b>Мои обращения</b>\n"
        "──────────────\n"
        "\n"
        "Обращений пока нет. Если нужна помощь, нажми «Задать вопрос»."
    ),
    support_ticket_row="{status} #{id} · {subject}",
    support_ticket_card=(
        "<b>Обращение #{id}</b>\n"
        "──────────────\n"
        "\n"
        "╭ Статус  <b>{status}</b>\n"
        "╰ Создано  <b>{created}</b>\n"
        "\n"
        "❖ <b>Переписка</b>\n"
        "{thread}"
    ),
    support_thread_user_line=(
        "<b>Пользователь</b>\n"
        "{text}"
    ),
    support_thread_admin_line=(
        "<b>Поддержка</b>\n"
        "{text}"
    ),
    support_thread_older_omitted="<i>Более ранние сообщения сохранены в истории обращения.</i>",
    # статусы глазами юзера
    support_status_new="На рассмотрении",
    support_status_in_progress="На рассмотрении",
    support_status_awaiting="Есть ответ",
    support_status_closed="Закрыто",
    btn_support_reply="Ответить",
    btn_support_close="✓ Закрыть обращение",
    btn_support_to_my="Мои обращения",
    btn_support_close_confirm="✓ Да, закрыть",
    btn_support_close_cancel="Оставить открытым",
    support_close_confirm=(
        "<b>Закрыть обращение #{id}?</b>\n"
        "──────────────\n"
        "\n"
        "После закрытия добавить сообщение в эту переписку не получится. Для нового вопроса можно создать обращение."
    ),
    support_reply_prompt=(
        "<b>Ответ в обращение #{id}</b>\n"
        "──────────────\n"
        "\n"
        "Пришли сообщение одним текстом. Оно сохранится в переписке."
    ),
    support_reply_sent_alert="Сообщение отправлено в поддержку.",
    support_closed_alert="Обращение закрыто.",
    support_ticket_closed_alert="Это обращение уже закрыто.",
    notify_support_reply=(
        "<b>Ответ по обращению #{id}</b>\n"
        "──────────────\n"
        "\n"
        "{text}\n"
        "\n"
        "Ответить можно в карточке обращения."
    ),
    notify_support_closed=(
        "<b>Обращение #{id} закрыто</b>\n"
        "──────────────\n"
        "\n"
        "Если вопрос остался, создай новое обращение в «Поддержка»."
    ),
    btn_support_open_ticket="Открыть обращение",
    log_support_new_ticket="Новое обращение <b>#{id}</b> от <code>{tg_id}</code>: {subject}",
    log_support_user_reply="Пользователь <code>{tg_id}</code> дописал в обращение <b>#{id}</b>",

    # ---------- NOTIFICATIONS (Этап 11) ----------
    notifications_card=(
        "🔔 <b>Уведомления</b>\n"
        "──────────────\n"
        "\n"
        "Нажми на категорию, чтобы включить или отключить сообщения.\n"
        "\n"
        "{rows}\n"
        "\n"
        "⟡ <i>Сообщения об операциях и ответы поддержки приходят всегда.</i>"
    ),
    notifications_row_on=(
        "{emoji} <b>{name}</b> · включены\n"
        "<i>{hint}</i>"
    ),
    notifications_row_off=(
        "{emoji} <b>{name}</b> · отключены\n"
        "<i>{hint}</i>"
    ),
    btn_notifications_on="{emoji} {name} · вкл",
    btn_notifications_off="{emoji} {name} · выкл",
    notifications_toggled_on_alert="Включено",
    notifications_toggled_off_alert="Выключено",

    # ---------- HISTORY (Этап 11) ----------
    history_card=(
        "📋 <b>История счёта</b>\n"
        "──────────────\n"
        "\n"
        "<i>Страница {page} из {total_pages}</i>\n"
        "\n"
        "{rows}\n"
        "\n"
        "⟡ <i>Начисления и списания во внутренних единицах. Отдельные нажатия кликера здесь не показаны.</i>"
    ),
    history_empty=(
        "📋 <b>История счёта</b>\n"
        "──────────────\n"
        "\n"
        "Операций пока нет. Первые начисления появятся после получения награды."
    ),
    history_row=(
        "{emoji} <b>{amount}</b> · {title}\n"
        "<i>{when}</i>"
    ),
    btn_history_prev="‹ Назад",
    btn_history_next="Вперёд ›",

    # ---------- INSTRUCTIONS (Этап 8) ----------
    ins_page_template=(
        "<b>{title}</b>\n"
        "──────────────\n"
        "\n"
        "<i>{step} из {total}</i>\n"
        "\n"
        "{body}"
    ),
    ins_empty_alert="Инструкция пока недоступна. Загляни позже.",
    btn_ins_back="‹ Помощь",

    # ---------- REVIEWS (Этап 8) ----------
    reviews_disabled=(
        "💝 <b>Отзывы</b>\n"
        "──────────────\n"
        "\n"
        "Раздел временно выключен."
    ),
    reviews_disabled_alert="Раздел отзывов временно выключен.",

    review_intro=(
        "💝 <b>Оставить отзыв</b>\n"
        "──────────────\n"
        "\n"
        "За публикацию — <b>{reward} ед.</b> на внутренний счёт.\n"
        "\n"
        "Выбери оценку, напиши отзыв и проверь его перед отправкой.\n"
        "\n"
        "<blockquote expandable><b>Условия публикации</b>\n"
        "От {min_len} до {max_len} символов.\n"
        "Не менее {min_refs} подтверждённых друзей.\n"
        "Один отзыв в {cooldown_days} дней.\n"
        "Без ссылок, мата и капса более 30%.\n"
        "Перед публикацией отзыв проходит модерацию.</blockquote>"
    ),
    btn_review_start="Написать отзыв",
    btn_review_cancel="✕ Отменить",
    btn_review_back="‹ Назад",
    btn_review_next="Продолжить ›",
    btn_review_confirm="✓ Отправить на модерацию",

    review_rating_page=(
        "<b>Оценка бота</b>\n"
        "──────────────\n"
        "\n"
        "<i>Шаг 1 из 4</i>\n"
        "\n"
        "Выбери оценку от 1 до 5."
    ),
    review_text_page=(
        "<b>Текст отзыва</b>\n"
        "──────────────\n"
        "\n"
        "<i>Шаг 2 из 4</i>\n"
        "\n"
        "{rating_line}\n"
        "\n"
        "Расскажи, что понравилось и что стоит улучшить.\n"
        "\n"
        "⟡ <i>От {min_len} до {max_len} символов. Без ссылок, мата и капса более 30%.</i>"
    ),
    review_anonymity_page=(
        "<b>Подпись отзыва</b>\n"
        "──────────────\n"
        "\n"
        "<i>Шаг 3 из 4</i>\n"
        "\n"
        "{rating_line}\n"
        "{text_preview}\n"
        "\n"
        "Выбери: твоё имя или анонимная публикация."
    ),
    btn_review_public="Моим именем",
    btn_review_anonymous="Анонимно",

    review_confirm_page=(
        "<b>Проверка отзыва</b>\n"
        "──────────────\n"
        "\n"
        "<i>Шаг 4 из 4</i>\n"
        "\n"
        "{rating_line}\n"
        "{text_preview}\n"
        "Автор: <b>{anon_line}</b>\n"
        "\n"
        "Если всё верно, отправь отзыв на модерацию."
    ),
    review_anon_public="моё имя",
    review_anon_anon="анонимно",
    review_rating_stars="{stars} <b>{rating} из 5</b>",

    review_success=(
        "<b>Отзыв на модерации</b>\n"
        "──────────────\n"
        "\n"
        "Результат придёт в этот чат.{reward_line}"
    ),
    review_success_reward=(
        "\n"
        "\n"
        "После публикации: <b>{reward} ед.</b> на внутренний счёт."
    ),
    review_filter_fail=(
        "<b>Отзыв не отправлен</b>\n"
        "──────────────\n"
        "\n"
        "{reason}\n"
        "\n"
        "Исправь текст и попробуй ещё раз."
    ),
    # плоские варианты для callback-алертов: Telegram не рендерит HTML в alert
    review_filter_fail_alert="{reason}. Попробуй ещё раз.",
    review_rating_required_alert="ед. Сначала выбери оценку от 1 до 5.",
    review_text_input_required="Пришли текст отзыва одним сообщением.",
    review_submit_failed_alert="Не получилось отправить отзыв. Открой раздел и попробуй ещё раз.",
    review_antispam_fail=(
        "<b>Отправка пока недоступна</b>\n"
        "──────────────\n"
        "\n"
        "{reason}\n"
        "\n"
        "Вернись к отзыву позже."
    ),
    review_antispam_fail_alert="{reason}. Попробуй позже.",

    log_review_submitted="💝 Отзыв от <code>{tg_id}</code> · {rating}⭐ · pending",
    review_channel_post=(
        "💝 <b>Отзыв</b>\n"
        "──────────────\n"
        "\n"
        "{stars}\n"
        "\n"
        "{text}\n"
        "\n"
        "⟡ <i>{author}</i>"
    ),
    review_channel_anon="Аноним",
    notify_review_approved=(
        "<b>Отзыв опубликован</b>\n"
        "──────────────\n"
        "\n"
        "Спасибо! Твой отзыв прошёл модерацию.{reward_line}"
    ),
    notify_review_reward_part=(
        "\n"
        "\n"
        "Начислено: <b>+{reward} ед.</b> на внутренний счёт."
    ),
    log_review_approved="Отзыв одобрен <code>{id}</code>",
    log_review_rejected="Отзыв отклонён <code>{id}</code>",
    log_review_converted="Из отзыва создано обращение <code>{id}</code>",

    # ---------- REVIEWS (moderation — админ) ----------
    review_mod_card=(
        "<b>Отзыв #{id}</b>\n"
        "──────────────\n"
        "\n"
        "Автор: {user_info}\n"
        "Оценка: {rating_stars}\n"
        "Анонимно: {is_anon}\n"
        "Создан: {date}\n"
        "\n"
        "❖ <b>Текст</b>\n"
        "{text}"
    ),
    review_mod_anonymous="Да",
    review_mod_public="Нет",
    btn_review_approve="Опубликовать",
    btn_review_reject="Отклонить",
    btn_review_convert="В поддержку",
    btn_review_mod_back="‹ К списку",

    review_reject_confirm=(
        "<b>Отклонить отзыв #{id}?</b>\n"
        "──────────────\n"
        "\n"
        "Отзыв не будет опубликован. Награда не начисляется."
    ),
    review_convert_confirm=(
        "<b>Создать обращение из отзыва #{id}?</b>\n"
        "──────────────\n"
        "\n"
        "Текст сохранится в поддержке. Отзыв не будет опубликован."
    ),
    review_reject_done="Отзыв отклонён.",
    review_convert_done="Из отзыва создано обращение в поддержку.",
    review_already_done="Отзыв уже обработан.",
    review_not_found="Отзыв не найден.",

    btn_admin_reviews="Отзывы",
    admin_reviews_empty=(
        "<b>Отзывы</b>\n"
        "──────────────\n"
        "\n"
        "Отзывов на модерации пока нет."
    ),
    admin_review_approved="✓ Отзыв опубликован.",
    btn_admin_stop_words="Фильтр отзывов",
    btn_admin_back_from_reviews="‹ Управление",
    channel_unset_alert="Ссылка на канал ещё не настроена.",
    soon_alert="Раздел пока недоступен.",

    # ---------- PROFILE ----------
    profile_caption=(
        "👤 <b>Профиль</b>\n"
        "──────────────\n"
        "\n"
        "╭ Доступно  <b>{balance}</b>{debt_part}\n"
        "│ Уровень  <b>{level_emoji} {level_name}</b>\n"
        "╰ Серия бонусов  <b>{streak} дн.</b>\n"
        "\n"
        "{progress_bar}\n"
        "{progress_text}\n"
        "\n"
        "<blockquote expandable><b>Аккаунт и команда</b>\n"
        "<b>{name}</b>\n"
        "{username_line}<code>ID {tg_id}</code>\n"
        "В SIRIUS с {join_date}.\n"
        "\n"
        "Приглашено: <b>{ref_total}</b>\n"
        "Подтверждено: <b>{ref_confirmed}</b>\n"
        "Закрепилось: <b>{ref_matured}</b></blockquote>\n"
        "\n"
        "⟡ <i>История, достижения и настройки — на кнопках ниже.</i>"
    ),
    profile_debt_part=(
        "\n"
        "Долг: <b>{debt}</b>"
    ),
    profile_no_username_line="",
    profile_username_line=(
        "@{username}\n"
    ),

    # ---------- REFERRALS ----------
    referral_caption=(
        "👥 <b>Моя команда</b>\n"
        "──────────────\n"
        "\n"
        "За подтверждённого друга — <b>{reward}</b>.\n"
        "\n"
        "╭ Подтверждено  <b>{confirmed}</b>\n"
        "│ Приглашено  <b>{total}</b>\n"
        "│ Закрепилось  <b>{matured}</b>\n"
        "╰ Начислено всего  <b>{earned}</b>{debt_part}\n"
        "\n"
        "❖ <b>Твоя ссылка</b>\n"
        "<code>{link}</code>\n"
        "\n"
        "Скопируй ссылку или отправь готовое приглашение.\n"
        "\n"
        "<blockquote expandable><b>Условия награды</b>\n"
        "Друг должен пройти обязательные проверки.\n"
        "Если он отпишется до закрепления ({maturation_text}), награда спишется. При нехватке средств появится долг; следующие начисления сначала погасят его.\n"
        "{limit_part}</blockquote>"
    ),
    referral_debt_part=(
        "\n"
        "Долг: <b>{debt}</b>"
    ),
    referral_no_limit="Дневной лимит новых приглашений не установлен.",
    referral_with_limit="Лимит новых приглашений: <b>{daily_limit}</b> за сутки.",

    btn_ref_copy_text="Готовое приглашение",
    btn_ref_share="↗ Пригласить друга",

    ref_share_view_caption=(
        "<b>Приглашение другу</b>\n"
        "──────────────\n"
        "\n"
        "Скопируй текст ниже или отправь его кнопкой «Пригласить друга».\n"
    ),
    ref_share_text=(
        "Я пользуюсь SIRIUS — ботом с заданиями и внутренними наградами в Telegram.\n"
        "\n"
        "Присоединяйся по моей ссылке:"
    ),
    btn_ref_back="‹ Моя команда",

    # ---------- REWARD / LOST уведомления (Этап 3 — простые) ----------
    notify_ref_reward=(
        "<b>Начислено +{amount}</b>\n"
        "──────────────\n"
        "\n"
        "Друг прошёл обязательные проверки. Награда учтена на внутреннем счёте; при наличии долга сначала погашает его."
    ),
    notify_ref_lost=(
        "<b>Награда за друга списана</b>\n"
        "──────────────\n"
        "\n"
        "Друг отписался от обязательных каналов до закрепления.\n"
        "\n"
        "Списано: <b>{amount}</b>{debt_part}"
    ),
    notify_ref_lost_debt=", в долг — <b>{debt}</b>",

    notify_self_subs_lost=(
        "<b>Нужно восстановить подписки</b>\n"
        "──────────────\n"
        "\n"
        "Обязательные подписки не подтверждены. Открой /start, чтобы проверить каналы и вернуть доступ."
    ),

    notify_task_lost=(
        "<b>Награда за задание списана</b>\n"
        "──────────────\n"
        "\n"
        "Подписка на «{title}» больше не подтверждена.\n"
        "Списано: <b>{amount}</b>.\n"
        "\n"
        "После новой подписки задание снова появится в списке."
    ),
    log_task_lost="Задание потеряно у <code>{tg_id}</code> · «{title}» · −{amount}{debt_part}",

    # ---------- лог-канал (для админа) ----------
    log_ref_attached="Привязка: <code>{user_tg_id}</code> → реферер <code>{referrer_tg_id}</code> ({source})",
    log_ref_confirmed="Друг подтверждён для <code>{referrer_tg_id}</code> · +{reward}",
    log_ref_lost="Награда за друга списана у <code>{referrer_tg_id}</code> · −{amount}{debt_part}",
    log_subrecheck_summary="sub-rechecker: проверено <b>{checked}</b>, отвалов <b>{lost}</b>",
    log_tasks_recheck_summary="tasks-rechecker: проверено <b>{checked}</b>, потеряно <b>{lost}</b>",

    # ---------- TERMS (Шаг 1) ----------
    # Шапка + тело страницы (тело — индекс из terms_pages_bodies).
    terms_page_template=(
        "<b>Соглашение</b> <i>{step}</i>\n"
        "──────────────\n"
        "{dots} <i>стр. {page} из {total}</i>\n"
        "\n"
        "{body}"
    ),
    terms_pages_bodies=(
        (
            "<b>Что такое SIRIUS</b>\n"
            "\n"
            "Бот с заданиями и игровыми способами получать внутренние единицы. Это счёт SIRIUS; начисления не пополняют Stars-баланс твоего Telegram-аккаунта.\n"
            "\n"
            "Доступные способы: приглашения друзей, задания каналов, кликер, ежедневный бонус, промокоды и колесо. Суммы и условия показаны в карточках.\n"
            "\n"
            "<i>Прочитай все страницы, затем нажми «Принимаю».</i>"
        ),
        (
            "<b>Награды и уровень</b>\n"
            "\n"
            "Внутренние единицы учитываются на счёте SIRIUS. Размеры наград и условия могут меняться; актуальные значения — в боте и канале проекта.\n"
            "\n"
            "Часть способов зависит от уровня. Он растёт с подтверждёнными друзьями и увеличивает дневной лимит кликера."
        ),
        (
            "<b>Приглашения друзей</b>\n"
            "\n"
            "Награда начисляется за друга, который пришёл по твоей ссылке и прошёл обязательные проверки, включая подписки.\n"
            "\n"
            "Срок закрепления и дневной лимит показаны в «Моя команда». Если друг отпишется до закрепления, награда спишется. При нехватке средств появится долг; следующие начисления сначала погасят его.\n"
            "\n"
            "Друг остаётся связан с пригласившим аккаунтом. Общий счётчик приглашений не уменьшается."
        ),
        (
            "<b>Счёт и операции</b>\n"
            "\n"
            "Начисления доступны только за предусмотренные в боте действия. Сумма показывается до действия и может меняться администрацией. При нарушении условий ранее выданная награда может быть списана.\n"
            "\n"
            "История показывает начисления и списания, кроме отдельных нажатий кликера. При подтверждении подарка сумма переводится в резерв. Настоящие Stars отправителя учитываются отдельно.\n"
            "\n"
            "<i>Функции вне текущего меню недоступны и не входят в соглашение.</i>"
        ),
        (
            "<b>Ограничения</b>\n"
            "\n"
            "Скрипты, эмуляторы, прокси-фермы, автокликеры и накрутка ботами приводят к блокировке без возврата.\n"
            "\n"
            "Закрытые коды-ловушки и фальшивые задания запрещены. Не вводи коды, которых нет в открытых источниках. Подозрительная активность может привести к ручной проверке и ограничению доступа.\n"
            "\n"
            "В отзывах и поддержке запрещены мат, реклама и ссылки на сторонние сервисы."
        ),
        (
            "<b>Ответственность</b>\n"
            "\n"
            "SIRIUS — частный проект, не официальный сервис Telegram. При техническом сбое обращайся в поддержку. Компенсация массовых сбоев остаётся на усмотрение администрации.\n"
            "\n"
            "<b>Изменения</b>\n"
            "\n"
            "Правила могут меняться. Актуальная версия доступна здесь; существенные изменения сообщаются в канале.\n"
            "\n"
            "<i>Нажимая «Принимаю», ты подтверждаешь, что прочитал соглашение и согласен с ним.</i>"
        ),
    ),
    terms_accept_btn="Принимаю",
    terms_decline_btn="✕ Не принимаю",
    terms_next_btn="Далее ▶",
    terms_prev_btn="‹ Назад",
    terms_declined="Без согласия бот недоступен. Возвращайся, когда будешь готов.",

    # ---------- CAPTCHA (Шаг 2) ----------
    captcha_caption=(
        "<b>Проверка доступа</b>\n"
        "──────────────\n"
        "\n"
        "<i>{step}</i>\n"
        "\n"
        "Выбери эмодзи, который есть на картинке. Один из четырёх вариантов верный."
    ),
    captcha_wrong="Ответ не совпал. Осталось попыток: {left}.",
    captcha_failed="Слишком много неудачных попыток. Подожди и нажми /start.",
    captcha_ok="Готово.",

    # ---------- SUBS (Шаг 3) ----------
    subs_caption=(
        "<b>Обязательные подписки</b>\n"
        "──────────────\n"
        "\n"
        "<i>{step}</i>\n"
        "\n"
        "Открой каналы ниже и подпишись. Затем нажми «Проверить подписку».\n"
        "\n"
        "⟡ <i>Эти подписки нужны для доступа к наградам.</i>"
    ),
    subs_check_btn="↻ Проверить подписку",
    subs_not_subscribed="Подписался не на все каналы.",
    subs_check_unavailable="⏳ Не удалось проверить подписку. Попробуй чуть позже.",
    subs_all_ok="Все подписки на месте.",
    subs_open_btn_prefix="↗",

    # ---------- ADMIN ----------
    admin_only="Только для администраторов.",
    admin_root=(
        "⚙️ <b>Управление SIRIUS</b>\n"
        "──────────────\n"
        "\n"
        "Выбери раздел. Статистика, операции и настройки доступны на отдельных экранах."
    ),

    # ---------- ADMIN: DASHBOARD (Этап 9) ----------
    btn_admin_dash="Обзор",
    btn_admin_system="Система",
    btn_admin_economy="Экономика",
    btn_admin_broadcast="Рассылка",
    btn_admin_instructions="Инструкция",
    btn_admin_channel="Канал",
    btn_admin_refresh="↻ Обновить",
    admin_dash=(
        "📊 <b>Обзор</b>\n"
        "──────────────\n"
        "\n"
        "╭ Балансы пользователей  <b>{balance_total}</b>\n"
        "│ Долги  <b>{debt_total}</b>\n"
        "╰ Отзывы на модерации  <b>{reviews_pending}</b>\n"
        "\n"
        "❖ <b>Пользователи</b>\n"
        "Всего: <b>{users_total}</b> · доступ открыт: <b>{users_passed}</b>\n"
        "Новых сегодня: <b>{users_new_today}</b> · ограничены: <b>{users_banned}</b>\n"
        "\n"
        "<blockquote expandable><b>Активность за сутки МСК</b>\n"
        "Нажатия кликера: <b>{clicks_today}</b>\n"
        "Бонусы: <b>{bonuses_today}</b>\n"
        "Вращения: <b>{spins_today}</b>\n"
        "Задания: <b>{tasks_today}</b>\n"
        "Подтверждённые друзья: <b>{refs_today}</b></blockquote>\n"
        "\n"
        "⟡ <i>Суммы — во внутренних единицах. Stars отправителя — в «Выдача подарков».</i>"
    ),
    admin_system=(
        "🔧 <b>Система</b>\n"
        "──────────────\n"
        "\n"
        "Аккаунт отправителя: {userbot_state}\n"
        "Канал проекта: {channel_state}\n"
        "Лог-канал: {log_channel}\n"
        "\n"
        "<blockquote expandable><b>Расписание проверок</b>\n"
        "Обязательные подписки: каждые {sub_interval} ч.\n"
        "Задания: каждые {tasks_interval} мин.\n"
        "Закрепление друзей: ежечасно.\n"
        "Награды рейтинга: понедельник, 03:05 МСК.</blockquote>"
    ),
    admin_userbot_on="Настроен; реальная авторизация — в «Выдача подарков»",
    admin_userbot_off="Параметры подключения не настроены",
    admin_channel_unset="<i>не настроен</i>",

    # ---------- ADMIN: USERS (Этап 9) ----------
    admin_users_intro=(
        "<b>Найти пользователя</b>\n"
        "──────────────\n"
        "\n"
        "Пришли <code>tg_id</code> или <code>@username</code> одним сообщением."
    ),
    admin_user_not_found="Пользователь не найден. Проверь ID или username.",
    admin_user_card=(
        "<b>Пользователь · {tg_id}</b>\n"
        "──────────────\n"
        "\n"
        "<b>{name}</b>\n"
        "{username_line}\n"
        "\n"
        "╭ Доступно  <b>{balance}</b>\n"
        "│ Долг  <b>{debt}</b>\n"
        "╰ Доступ ограничен  <b>{banned}</b>\n"
        "\n"
        "<blockquote expandable><b>Аккаунт и активность</b>\n"
        "Проверки пройдены: {passed}\n"
        "Приглашено: {refs} · подтверждено: {confirmed}\n"
        "Серия бонусов: {streak} дн.\n"
        "Зарегистрирован: {created}\n"
        "\n"
        "<b>Последние действия</b>\n"
        "{actions}</blockquote>"
    ),
    admin_user_actions_empty="<i>пока пусто</i>",
    admin_user_action_row="· {action} <i>{when}</i>",
    btn_admin_user_ban="Ограничить доступ",
    btn_admin_user_unban="Восстановить доступ",
    btn_admin_user_shadow_on="Shadow-ban",
    btn_admin_user_shadow_off="Снять shadow",
    btn_admin_user_balance="Баланс ±",
    btn_admin_user_search="Найти другого",
    admin_user_balance_prompt=(
        "<b>Изменить счёт · {tg_id}</b>\n"
        "──────────────\n"
        "\n"
        "Доступно: <b>{balance}</b>\n"
        "\n"
        "Пришли сумму в единицах SIRIUS:\n"
        "<code>5</code> — начислить · <code>-3.5</code> — списать.\n"
        "\n"
        "⟡ <i>При нехватке средств списание создаст долг.</i>"
    ),
    admin_user_balance_invalid="Нужно число, например <code>5</code> или <code>-3.5</code>.",
    admin_user_balance_done="Готово: {delta} → баланс <b>{balance}</b>",
    admin_user_banned_alert="Доступ пользователя ограничен.",
    admin_user_unbanned_alert="Доступ пользователя восстановлен.",
    admin_user_shadow_on_alert="Shadow-ban включён.",
    admin_user_shadow_off_alert="Shadow-ban снят.",
    admin_owner_protected="Владелец защищён: ограничить его доступ нельзя.",

    # ---------- ADMIN: ECONOMY (Этап 9) ----------
    admin_eco_root=(
        "⚙️ <b>Экономика</b>\n"
        "──────────────\n"
        "\n"
        "Выбери группу настроек, затем нужный параметр. Текущее значение и описание появятся перед изменением."
    ),
    admin_eco_group=(
        "<b>Экономика · {group}</b>\n"
        "──────────────\n"
        "\n"
        "{rows}\n"
        "\n"
        "⟡ <i>Нажми параметр, чтобы изменить его значение.</i>"
    ),
    admin_eco_row="<code>{key}</code> = <b>{value}</b>",
    admin_eco_edit_prompt=(
        "<b>Изменить параметр</b>\n"
        "──────────────\n"
        "\n"
        "<code>{key}</code>\n"
        "{description}\n"
        "\n"
        "Текущее значение: <b>{value}</b>\n"
        "Тип: <b>{type}</b>\n"
        "\n"
        "Пришли новое значение одним сообщением.\n"
        "\n"
        "⟡ <i>Для структурированных настроек нужен корректный JSON.</i>"
    ),
    admin_eco_invalid="Не удалось разобрать значение типа <b>{type}</b>. Попробуй ещё раз.",
    admin_eco_validation_error=(
        "<b>Значение не сохранено</b>\n"
        "──────────────\n"
        "\n"
        "{error}\n"
        "\n"
        "⟡ <i>Исправь значение и отправь его ещё раз</i>"
    ),
    admin_eco_saved="<code>{key}</code> = <b>{value}</b>",

    # ---------- ADMIN: BROADCAST (Этап 9) ----------
    admin_bc_intro=(
        "<b>Новая рассылка</b>\n"
        "──────────────\n"
        "\n"
        "Получателей: <b>{count}</b>\n"
        "\n"
        "Пришли текст одним сообщением. Затем появится предпросмотр и подтверждение отправки.\n"
        "\n"
        "⟡ <i>Поддерживается HTML-разметка.</i>"
    ),
    admin_bc_preview=(
        "<b>Проверка рассылки</b>\n"
        "──────────────\n"
        "\n"
        "Получателей: <b>{count}</b>\n"
        "\n"
        "❖ <b>Текст</b>\n"
        "{text}\n"
        "\n"
        "Нажми «Отправить», если всё верно."
    ),
    btn_admin_bc_send="Отправить",
    btn_admin_bc_cancel="✕ Отменить",
    admin_bc_progress="Рассылка… <b>{done}</b> / {total}",
    admin_bc_busy_alert="⏳ Рассылка уже выполняется. Дождись итогового отчёта.",
    admin_bc_failed=(
        "<b>Рассылка приостановлена</b>\n"
        "──────────────\n"
        "\n"
        "Произошла техническая ошибка. Детали сохранены в журнале; повторный запуск уже доступен."
    ),
    admin_bc_done=(
        "<b>Рассылка завершена</b>\n"
        "──────────────\n"
        "\n"
        "╭ Доставлено  <b>{sent}</b>\n"
        "│ Недоступно  <b>{failed}</b>\n"
        "╰ Всего  <b>{total}</b>"
    ),
    admin_bc_cancelled="Рассылка отменена.",
    admin_bc_empty="Пустой текст. Пришли текст рассылки.",
    admin_bc_too_long=(
        "<b>Текст слишком длинный</b>\n"
        "\n"
        "Сократи сообщение до {max_len} символов, чтобы предпросмотр и отправка корректно открывались на всех устройствах."
    ),

    # ---------- ADMIN: INSTRUCTIONS (Этап 8 доделка) ----------
    admin_ins_root=(
        "<b>Инструкция</b>\n"
        "──────────────\n"
        "\n"
        "Страниц: <b>{count}</b>\n"
        "\n"
        "Выбери страницу для просмотра и редактирования или добавь новую."
    ),
    admin_ins_card=(
        "<b>Страница #{id}</b>\n"
        "──────────────\n"
        "\n"
        "<b>{title}</b>\n"
        "\n"
        "{body}"
    ),
    admin_ins_new_title_prompt=(
        "<b>Новая страница</b> <i>Шаг 1 из 2</i>\n"
        "──────────────\n"
        "\n"
        "Пришли заголовок страницы."
    ),
    admin_ins_new_body_prompt=(
        "<b>Новая страница</b> <i>Шаг 2 из 2</i>\n"
        "──────────────\n"
        "\n"
        "Заголовок: <b>{title}</b>\n"
        "\n"
        "Теперь пришли текст страницы.\n"
        "⟡ <i>HTML-разметка поддерживается</i>"
    ),
    admin_ins_edit_title_prompt=(
        "<b>Новый заголовок</b>\n"
        "──────────────\n"
        "\n"
        "Текущий: <b>{title}</b>\n"
        "Пришли новый заголовок."
    ),
    admin_ins_edit_body_prompt=(
        "<b>Новый текст</b>\n"
        "──────────────\n"
        "\n"
        "Страница: <b>{title}</b>\n"
        "Пришли новый текст.\n"
        "⟡ <i>HTML-разметка поддерживается</i>"
    ),
    admin_ins_created="Страница <b>{title}</b> добавлена.",
    admin_ins_saved="Сохранено.",
    admin_ins_deleted="Страница удалена.",
    admin_ins_invalid="Текст не может быть пустым.",
    admin_ins_title_invalid="Заголовок должен содержать от 1 до {max_len} символов.",
    admin_ins_body_invalid="Текст страницы должен содержать от 1 до {max_len} символов.",
    btn_admin_ins_add="Добавить страницу",
    btn_admin_ins_edit_title="Заголовок",
    btn_admin_ins_edit_body="Текст",
    btn_admin_ins_delete="Удалить",

    # ---------- ADMIN: CHANNEL (Этап 8 доделка) ----------
    admin_channel_card=(
        "<b>Канал проекта</b>\n"
        "──────────────\n"
        "\n"
        "Текущий канал: {current}\n"
        "\n"
        "Чтобы изменить, пришли <code>@username</code> публичного канала, где бот — администратор.\n"
        "\n"
        "<blockquote expandable><b>Что изменится</b>\n"
        "Канал появится в главном меню и будет добавлен в обязательные подписки.</blockquote>"
    ),
    admin_channel_invalid="Не получилось. Пришли <code>@username</code> публичного канала, где бот — админ.",
    admin_channel_set="Канал <b>{title}</b> установлен и добавлен обязательным спонсором.",

    # ---------- ADMIN: STOP WORDS (Этап 8 доделка) ----------
    admin_sw_root=(
        "<b>Фильтр отзывов</b>\n"
        "──────────────\n"
        "\n"
        "Слов в фильтре: <b>{count}</b>\n"
        "\n"
        "{words}\n"
        "\n"
        "⟡ <i>Отзыв с одним из этих слов не проходит автоматическую проверку.</i>"
    ),
    admin_sw_empty="<i>список пуст</i>",
    admin_sw_add_prompt="Пришли слово (или несколько через запятую) для добавления.",
    admin_sw_remove_prompt="Пришли слово для удаления.",
    admin_sw_added="Добавлено: <b>{count}</b>",
    admin_sw_removed="Удалено.",
    admin_sw_not_found="Такого слова нет в списке.",
    btn_admin_sw_add="Добавить",
    btn_admin_sw_remove="Удалить",
    admin_sponsors_root=(
        "<b>Спонсоры</b>\n"
        "──────────────\n"
        "{count_line}"
    ),
    admin_sponsors_empty="Каналов пока нет. Нажми «Добавить канал».",
    admin_sponsors_count=(
        "Всего: <b>{total}</b> · активных: <b>{active}</b>\n"
        "Обязательных: <b>{required}</b>"
    ),

    admin_sponsor_card=(
        "<b>{title}</b>\n"
        "──────────────\n"
        "\n"
        "Статус: <b>{status}</b>\n"
        "Обязательная подписка: {required}\n"
        "{stats_line}\n"
        "\n"
        "<blockquote expandable><b>Данные канала</b>\n"
        "ID: <code>{id}</code>\n"
        "Тип: {kind}\n"
        "{ident_line}</blockquote>"
    ),
    admin_sponsor_stats="Подписалось через бота: <b>{counter}</b>{limit_part}",
    admin_sponsor_kind_public="Публичный",
    admin_sponsor_kind_private="Приватный",
    admin_sponsor_status_active="Активен",
    admin_sponsor_status_paused="⏸ На паузе",
    admin_sponsor_required_yes="Да",
    admin_sponsor_required_no="Нет",
    admin_sponsor_deleted="Спонсор удалён.",
    admin_sponsor_toggled_on="▶ Активирован.",
    admin_sponsor_toggled_off="⏸ Приостановлен.",
    admin_sponsor_required_toggled="Обязательность переключена.",

    btn_admin_users="Пользователи",
    btn_admin_sponsors="Спонсоры",
    btn_admin_settings="Настройки",
    btn_admin_stats="Статистика",
    btn_admin_section_soon="(скоро)",

    btn_sponsor_toggle_active="Пауза / запуск",
    btn_sponsor_toggle_required="Обязательная подписка",
    btn_sponsor_delete="Удалить",
    btn_sponsor_delete_confirm="✓ Подтвердить удаление",
    btn_sponsor_delete_cancel="Отменить удаление",
    btn_sponsor_open="Открыть канал",

    # ---------- ADD SPONSOR (мастер на inline) ----------
    addsp_step1=(
        "<b>Новый спонсор</b> <i>Шаг 1 из 3</i>\n"
        "──────────────\n"
        "Выбери тип канала."
    ),
    addsp_step2_public=(
        "<b>Новый спонсор</b> <i>Шаг 2 из 3</i>\n"
        "──────────────\n"
        "Публичный канал.\n"
        "\n"
        "Перешли любой пост из канала <b>боту</b> или пришли <code>@username</code>.\n"
        "<i>Бот должен быть админом этого канала.</i>"
    ),
    addsp_step2_private=(
        "<b>Новый спонсор</b> <i>Шаг 2 из 4</i>\n"
        "──────────────\n"
        "Приватный канал.\n"
        "\n"
        "Пришли invite-ссылку: <code>https://t.me/+...</code>"
    ),
    addsp_step2b_private=(
        "<b>Новый спонсор</b> <i>Шаг 3 из 4</i>\n"
        "──────────────\n"
        "Приватный канал.\n"
        "\n"
        "Теперь <b>перешли любой пост</b> из этого канала боту — чтобы получить ID и проверять подписки.\n"
        "\n"
        "<i>Бот обязан быть админом в канале.</i>"
    ),
    addsp_private_forward_invalid="Не похоже на пост из канала. Перешли любое сообщение из приватного канала.",
    addsp_step3=(
        "<b>Новый спонсор</b> <i>Шаг 3 из 3</i>\n"
        "──────────────\n"
        "Пришли название канала (отобразится на кнопке)."
    ),
    addsp_step4_private=(
        "<b>Новый спонсор</b> <i>Шаг 4 из 4</i>\n"
        "──────────────\n"
        "Пришли название канала (отобразится на кнопке)."
    ),
    addsp_kind_public_btn="Публичный",
    addsp_kind_private_btn="Приватный",
    addsp_chat_invalid=(
        "Не удалось получить канал. Перешли пост из канала или пришли <code>@username</code>.\n"
        "Бот должен быть админом."
    ),
    addsp_invite_invalid="Это не похоже на invite-ссылку. Пример: <code>https://t.me/+abc...</code>",
    addsp_bot_not_admin=(
        "Бот не админ в этом канале — он не сможет проверять подписки.\n"
        "Сделай бота администратором и попробуй снова."
    ),
    addsp_title_invalid="Название не может быть пустым.",
    addsp_cancelled="Добавление отменено.",
    addsp_created="Спонсор <b>{title}</b> добавлен.",

    # ---------- ADMIN: edit OPTIONAL sponsor ----------
    btn_sponsor_edit_reward="Награда",
    btn_sponsor_edit_limit="Лимит",
    editsp_reward_prompt=(
        "<b>Награда · {title}</b>\n"
        "──────────────\n"
        "\n"
        "Сейчас: <b>{current:.2f} ед.</b>\n"
        "\n"
        "Пришли новую сумму, например <code>1.5</code>.\n"
        "\n"
        "⟡ <i>Ноль отключает задание.</i>"
    ),
    editsp_reward_invalid="Нужно число от 0 до 1 000 000. Пример: <code>1.5</code>",
    editsp_reward_saved="Награда сохранена: <b>{reward:.2f} ед.</b> · {title}",
    editsp_limit_prompt=(
        "<b>Лимит · {title}</b>\n"
        "──────────────\n"
        "\n"
        "Сейчас: <b>{current}</b>\n"
        "\n"
        "Пришли число подписок, после которого задание отключится.\n"
        "\n"
        "⟡ <i>Ноль означает отсутствие лимита.</i>"
    ),
    editsp_limit_invalid="Нужно целое неотрицательное число.",
    editsp_limit_saved="Лимит обновлён: <b>{limit}</b> ({title})",

    # ---------- ADMIN: PROMOS ----------
    btn_admin_promos="Промокоды",
    btn_admin_promo_add="Создать",
    btn_admin_back="‹ Управление",
    btn_admin_promo_pause="⏸ На паузу",
    btn_admin_promo_resume="▶ Активировать",
    btn_admin_promo_delete="Удалить",
    btn_admin_promo_delete_confirm="✓ Подтвердить удаление",
    btn_admin_promo_delete_cancel="Отменить удаление",
    btn_admin_promo_back_list="‹ К списку",
    btn_admin_promo_add_cancel="✕ Отменить",
    btn_admin_promo_honeypot_yes="Honeypot",
    btn_admin_promo_honeypot_no="Обычный",

    admin_promos_root=(
        "<b>Промокоды</b>\n"
        "──────────────\n"
        "{count_line}"
    ),
    admin_promos_empty="Список пуст. Создай первый.",
    admin_promos_count="Всего: <b>{total}</b> · Активных: <b>{active}</b> · Ловушек: <b>{honeypots}</b>",

    admin_promo_card=(
        "<b>Промокод · {code}</b>\n"
        "──────────────\n"
        "\n"
        "Статус: <b>{status}</b>\n"
        "Награда: <b>{reward}</b>\n"
        "Активации: {usage}\n"
        "Срок: {expires}\n"
        "\n"
        "Тип: {kind}"
    ),
    admin_promo_kind_normal="Обычный",
    admin_promo_kind_honeypot="Honeypot (бан при вводе)",
    admin_promo_status_active="Активен",
    admin_promo_status_paused="⏸ На паузе",
    admin_promo_usage_unlimited="<b>{used}</b> (безлимит)",
    admin_promo_usage_limited="<b>{used}</b> / <b>{max}</b>",
    admin_promo_expires_never="без срока",
    admin_promo_deleted="Промокод удалён.",
    admin_promo_toggled_on="▶ Активирован.",
    admin_promo_toggled_off="⏸ Приостановлен.",

    # ADD PROMO wizard
    addpromo_step1=(
        "<b>Новый промокод</b> <i>Шаг 1 из 5</i>\n"
        "──────────────\n"
        "Пришли код: латиница, цифры, <code>_</code>, <code>-</code>.\n"
        "<i>Будет нормализован к верхнему регистру.</i>"
    ),
    addpromo_step2=(
        "<b>Новый промокод</b>\n"
        "──────────────\n"
        "\n"
        "<i>Шаг 2 из 5</i>\n"
        "\n"
        "Код: <code>{code}</code>\n"
        "\n"
        "Пришли награду во внутренних единицах, например <code>1.5</code>.\n"
        "\n"
        "Для кода-ловушки укажи <code>0</code>."
    ),
    addpromo_step3=(
        "<b>Новый промокод</b> <i>Шаг 3 из 5</i>\n"
        "──────────────\n"
        "Сколько максимум активаций?\n"
        "<i>0 — без лимита.</i>"
    ),
    addpromo_step4=(
        "<b>Новый промокод</b> <i>Шаг 4 из 5</i>\n"
        "──────────────\n"
        "Срок действия в днях.\n"
        "<i>0 — без срока.</i>"
    ),
    addpromo_step5=(
        "<b>Новый промокод</b> <i>Шаг 5 из 5</i>\n"
        "──────────────\n"
        "Это <b>honeypot</b>?\n"
        "<i>Honeypot — ловушка: кто введёт, получит бан без награды.</i>"
    ),
    addpromo_code_invalid="Неверный код. Допустимы латиница, цифры, <code>_</code>, <code>-</code>. Длина 1–64.",
    addpromo_code_duplicate="Такой код уже существует. Выбери другой.",
    addpromo_reward_invalid="Нужно число от 0 до 1 000 000.",
    addpromo_max_invalid="Нужно неотрицательное целое число.",
    addpromo_expires_invalid="Нужно неотрицательное целое число дней.",
    addpromo_created="Промокод <b>{code}</b> создан.",
    addpromo_created_alert="Промокод создан",
    addpromo_cancelled="Создание отменено.",

    # ---------- CLICKER (user) ----------
    clicker_caption=(
        "👆 <b>Кликер</b>\n"
        "──────────────\n"
        "\n"
        "За нажатие: <b>{reward_per_click}</b>\n"
        "{cooldown_line}\n"
        "\n"
        "╭ Сегодня  <b>{clicks} / {daily_limit}</b>\n"
        "│ Начислено  <b>{earned_today}</b>\n"
        "╰ Доступно  <b>{balance}</b>\n"
        "\n"
        "{progress_bar}\n"
        "\n"
        "<blockquote expandable><b>Лимит и уровень</b>\n"
        "{level_emoji} {level_name}\n"
        "Чем выше уровень, тем больше дневной лимит. Он обновляется в 00:00 МСК.</blockquote>"
    ),
    clicker_cooldown_line="Следующее нажатие через <b>{left}</b>.",
    clicker_ready_line="Можно получить награду сейчас.",
    clicker_limit_line="Дневной лимит исчерпан. Обновление — в 00:00 МСК.",
    btn_click_tap="Получить награду",
    btn_click_cooldown="Через {time}",
    btn_click_limit_reached="Лимит получен",
    btn_click_refresh="↻ Обновить",
    btn_click_cancel="‹ Награды",
    clicker_tick_alert="+{reward}",
    clicker_milestone_alert="Сегодня {clicks} нажатий · начислено +{reward}.",
    clicker_finish_alert=(
        "Дневной лимит получен.\n"
        "Начислено за сегодня: +{earned}.\n"
        "Новый лимит — в 00:00 МСК."
    ),
    clicker_too_fast_alert="Следующее нажатие через {left}.",
    clicker_daily_limit_alert="Дневной лимит исчерпан. Обновится в 00:00 МСК.",
    clicker_captcha_required_alert="Сначала пройди мини-проверку.",
    clicker_captcha_triggered_alert="Мини-проверка — выбери лишний эмодзи.",

    # CLICKER captcha (mini)
    clicker_captcha_caption=(
        "<b>Проверка кликера</b>\n"
        "──────────────\n"
        "\n"
        "Подсказка: <b>{hint}</b>\n"
        "\n"
        "Выбери лишний эмодзи на кнопках ниже. После проверки можно продолжить."
    ),
    clicker_captcha_wrong_prefix=(
        "<b>Не то.</b> Попробуй ещё раз.\n"
        "\n"
    ),
    clicker_captcha_ok_alert="Готово, продолжай.",
    clicker_captcha_wrong_alert="Не то — попробуй ещё.",
    clicker_captcha_expired_alert="Капча устарела — обновлено.",

    # ---------- DAILY BONUS (user) ----------
    bonus_caption=(
        "🎁 <b>Бонус дня</b>\n"
        "──────────────\n"
        "\n"
        "╭ Награда сегодня  <b>{today_amount}</b>\n"
        "│ Серия  <b>{streak} дн.</b>\n"
        "╰ Доступно  <b>{balance}</b>\n"
        "\n"
        "{claim_note}\n"
        "\n"
        "{bio_block}\n"
        "\n"
        "<blockquote expandable><b>Награды за серию</b>\n"
        "{ladder}\n"
        "\n"
        "{next_line}</blockquote>"
    ),
    bonus_ladder_done="✓ День {days} · {amount}",
    bonus_ladder_next="День {days} · <b>{amount}</b> · следующая ступень",
    bonus_ladder_locked="День {days} · {amount}",
    bonus_next_line="До бонуса <b>{amount}</b> — ещё <b>{days}</b> дн. подряд.",
    bonus_next_max="Достигнута максимальная ступень серии.",
    bonus_bio_block=(
        "<blockquote expandable><b>Условие получения</b>\n"
        "Добавь эту ссылку в Telegram → Изменить профиль → О себе:\n"
        "<code>{link}</code>\n"
        "\n"
        "Затем нажми «Забрать награду». Ссылка должна оставаться в профиле.</blockquote>"
    ),
    bonus_bio_off="Нажми «Забрать награду», если она ещё доступна. Новый бонус — в 00:00 МСК.",
    btn_bonus_claim="Забрать награду",
    btn_bonus_claimed="✓ Сегодня уже получено",
    btn_bonus_refresh="↻ Обновить",
    bonus_ok_alert="Начислено +{amount} · серия {streak} дн.",
    bonus_already_alert="Сегодня бонус уже получен. Возвращайся завтра.",
    bonus_bio_missing_alert="В разделе «О себе» нет твоей ссылки. Добавь её и повтори проверку.",
    bonus_unavailable_alert="⏳ Проверка временно недоступна. Попробуй чуть позже.",

    # ---------- TASKS (user) ----------
    tasks_list_caption=(
        "🎯 <b>Задания</b>\n"
        "──────────────\n"
        "\n"
        "Доступно: <b>{active}</b>\n"
        "\n"
        "Выбери канал. Награда начисляется после проверки подписки.\n"
        "\n"
        "⟡ <i>Отписка от канала приводит к списанию награды.</i>"
    ),
    tasks_empty=(
        "<b>Задания</b>\n"
        "──────────────\n"
        "\n"
        "Доступных заданий пока нет. Обнови список позже или выбери другой способ в «Награды»."
    ),
    tasks_disabled=(
        "<b>Задания спонсоров</b>\n"
        "──────────────\n"
        "\n"
        "Раздел временно выключен."
    ),
    tasks_disabled_alert="Раздел временно выключен.",
    btn_tasks_refresh="↻ Обновить",
    btn_tasks_back="‹ К списку",

    task_card=(
        "<b>{title}</b>\n"
        "──────────────\n"
        "\n"
        "Награда: <b>{reward}</b>\n"
        "{status_line}\n"
        "\n"
        "Открой канал и подпишись. Затем вернись сюда и нажми «Проверить подписку».\n"
        "\n"
        "⟡ <i>Если подписка не сохранится, награда будет списана.</i>"
    ),
    task_card_pending="Статус: <b>не выполнено</b>",
    task_card_completed="Статус: <b>выполнено</b>",
    btn_task_open_channel="Открыть канал",
    btn_task_check="Проверить подписку",
    task_claim_ok_alert="+{reward}",
    task_not_subscribed_alert="Не вижу подписки. Подпишись и нажми «Проверить».",
    task_check_unavailable_alert="⏳ Проверка подписки временно недоступна. Попробуй ещё раз.",
    task_already_done_alert="✓ Уже выполнено.",
    task_limit_reached_alert="Лимит этого задания исчерпан.",
    task_not_found_alert="Задание больше недоступно. Обнови список.",
    task_no_reward_alert="У этого задания не задана награда.",

    # ---------- PROMO (user) ----------
    promo_intro=(
        "<b>Промокод</b>\n"
        "──────────────\n"
        "\n"
        "Введи код из официального источника SIRIUS. Награда поступит на внутренний счёт.\n"
        "\n"
        "<blockquote expandable><b>Условия активации</b>\n"
        "До {max_len} символов. Каждый код доступен один раз на пользователя; регистр не важен.\n"
        "Не вводи непубличные коды-ловушки: по правилам они ограничивают доступ к боту.</blockquote>"
    ),
    promo_waiting=(
        "<b>Промокод</b>\n"
        "──────────────\n"
        "\n"
        "Пришли промокод одним сообщением.\n"
        "\n"
        "⟡ <i>Регистр не важен</i>"
    ),
    btn_promo_enter="Ввести код",
    btn_promo_cancel="✕ Отменить",
    btn_promo_again="↻ Ввести другой код",
    btn_promo_back_profile="‹ В профиль",
    promo_ok=(
        "<b>Промокод применён</b>\n"
        "──────────────\n"
        "\n"
        "<code>{code}</code>\n"
        "\n"
        "╭ Начислено  <b>{reward}</b>\n"
        "╰ Доступно  <b>{balance}</b>"
    ),
    promo_not_found=(
        "<b>Код не найден</b>\n"
        "──────────────\n"
        "\n"
        "Проверь написание и источник кода, затем попробуй ещё раз."
    ),
    promo_already_used=(
        "<b>Код уже использован</b>\n"
        "──────────────\n"
        "\n"
        "Один промокод доступен один раз на пользователя. Можно ввести другой код."
    ),
    promo_expired=(
        "⏱ <b>Срок истёк</b>\n"
        "──────────────\n"
        "\n"
        "Этот код больше не активен."
    ),
    promo_exhausted=(
        "<b>Активации закончились</b>\n"
        "──────────────\n"
        "\n"
        "Лимит активаций достигнут."
    ),
    promo_inactive=(
        "⏸ <b>Код не активен</b>\n"
        "──────────────\n"
        "\n"
        "Этот код временно отключён."
    ),
    promo_too_long=(
        "<b>Слишком длинный</b>\n"
        "──────────────\n"
        "\n"
        "Промокод должен быть короче. Проверь ещё раз."
    ),
    promo_empty=(
        "<b>Пустой код</b>\n"
        "──────────────\n"
        "\n"
        "Пришли непустой текст."
    ),
    promo_honeypot_banned=(
        "<b>Доступ закрыт</b>\n"
        "──────────────\n"
        "\n"
        "Ты ввёл закрытый код, помеченный как ловушка.\n"
        "По правилам аккаунт заблокирован."
    ),

    # ---------- WHEEL (user) ----------
    wheel_caption=(
        "🎡 <b>Колесо</b>\n"
        "──────────────\n"
        "\n"
        "╭ Бесплатное вращение  <b>{free_state}</b>\n"
        "│ Платное вращение  <b>{cost}</b>\n"
        "╰ Доступно  <b>{balance}</b>\n"
        "\n"
        "{result_line}\n"
        "\n"
        "<blockquote expandable><b>Призы и условия</b>\n"
        "{sectors}\n"
        "\n"
        "Приз выбирается случайно и может быть нулевым. Бесплатное вращение не расходует баланс. Платное спишет указанную сумму после подтверждения.</blockquote>"
    ),
    wheel_free_yes="доступно",
    wheel_free_no="уже использовано",
    wheel_spin_frames=(
        (
            "<b>Колесо</b>\n"
            "──────────────\n"
            "\n"
            "<i>Определяем результат…</i>"
        ),
        (
            "<b>Колесо</b>\n"
            "──────────────\n"
            "\n"
            "<i>Результат выбран. Ещё мгновение…</i>"
        ),
    ),
    wheel_idle_line="Выбери бесплатное или платное вращение.",
    wheel_win_line="Начислено: <b>+{prize}</b>",
    wheel_empty_line="Выпал нулевой приз. Начисления нет.",
    wheel_sectors_empty="скоро",
    btn_wheel_free="Вращать бесплатно",
    btn_wheel_paid="Вращать за {cost}",
    btn_wheel_refresh="↻ Обновить",
    btn_wheel_locked="Недостаточно единиц",
    wheel_win_alert="+{prize}",
    wheel_empty_alert="Выпал нулевой приз. Начисления нет.",
    wheel_no_free_alert="Бесплатное вращение уже использовано. Можно выбрать платное после подтверждения стоимости.",
    wheel_not_enough_alert="Недостаточно внутренних единиц для платного вращения.",
    wheel_price_changed_alert="Цена изменилась. Открой колесо и подтверди новую стоимость.",
    btn_wheel_confirm="Вращать за {cost}",
    wheel_paid_confirmation=(
        "<b>Платное вращение</b>\n"
        "──────────────\n"
        "\n"
        "╭ Спишется  <b>{cost}</b>\n"
        "╰ Доступно  <b>{balance}</b>\n"
        "\n"
        "Приз выбирается случайно и может быть нулевым. Подтверди указанную стоимость кнопкой ниже.\n"
        "\n"
        "⟡ <i>Подтверждение действует 2 минуты.</i>"
    ),
    wheel_disabled_alert="Колесо временно недоступно.",

    # ---------- ACHIEVEMENTS (user) ----------
    ach_caption=(
        "🏆 <b>Достижения</b>\n"
        "──────────────\n"
        "\n"
        "Открыто: <b>{unlocked} из {total}</b>\n"
        "{summary_bar}\n"
        "\n"
        "{rows}\n"
        "\n"
        "⟡ <i>Каждая награда начисляется один раз на внутренний счёт.</i>"
    ),
    ach_empty=(
        "<b>Достижения</b>\n"
        "──────────────\n"
        "\n"
        "Достижения сейчас недоступны. Загляни позже."
    ),
    ach_row_unlocked="✓ {emoji} <b>{name}</b> · +{reward}",
    ach_row_locked=(
        "{emoji} <b>{name}</b> · +{reward}\n"
        "{bar} <i>{current}/{threshold} {unit}</i>"
    ),
    ach_unlocked_alert="Открыто: {names} · +{total}",
    btn_ach_refresh="↻ Обновить",
    btn_ach_back="‹ В профиль",

    # ---------- LEADERBOARD (user) ----------
    top_caption=(
        "🏆 <b>Рейтинг друзей</b>\n"
        "──────────────\n"
        "\n"
        "<i>{period_name}</i>\n"
        "\n"
        "{your_line}\n"
        "\n"
        "{rows}\n"
        "\n"
        "<blockquote expandable><b>Условия рейтинга</b>\n"
        "Не менее {min_confirmed} подтверждённых друзей. Первые 10 мест недельного рейтинга получают награды на внутренний счёт.</blockquote>"
    ),
    top_empty=(
        "<b>Рейтинг друзей</b>\n"
        "──────────────\n"
        "\n"
        "<i>{period_name}</i>\n"
        "\n"
        "{your_line}\n"
        "\n"
        "В рейтинге пока нет участников с {min_confirmed} подтверждёнными друзьями."
    ),
    top_row="{medal} <b>{name}</b> — <b>{score}</b>",
    top_your_ranked="Твоё место: <b>#{rank}</b> · подтверждённых друзей: {score}",
    top_your_unranked="До участия: <b>{score} / {min_confirmed}</b> подтверждённых друзей",
    top_period_week="Неделя",
    top_period_month="Месяц",
    top_period_all="Всё время",
    top_disabled_alert="Топ временно недоступен.",
    btn_top_refresh="↻ Обновить",
    btn_top_back="‹ В профиль",

    notify_top_reward=(
        "<b>Награда за недельный рейтинг</b>\n"
        "──────────────\n"
        "\n"
        "Место: <b>#{rank}</b>\n"
        "Начислено: <b>{amount}</b> на внутренний счёт."
    ),
    log_top_payout="Топ-выплаты за {week}: награждено <b>{count}</b>",

    # ---------- PARTNER (Этап 10, юзер-сайд) ----------
    btn_profile_partner="Партнёрская панель",
    partner_paused_alert="⏸ Партнёрский доступ на паузе. Напиши владельцу.",
    partner_caption=(
        "🤝 <b>Партнёрская панель</b>\n"
        "──────────────\n"
        "\n"
        "╭ Доступно  <b>{balance}</b>\n"
        "╰ Начислено всего  <b>{total_earned}</b>\n"
        "\n"
        "Выбери ссылки, каналы или заявку на выплату.\n"
        "\n"
        "<blockquote expandable><b>Статистика и условия</b>\n"
        "Ссылки: {links_count}\n"
        "Переходы: {clicks}\n"
        "Регистрации: {joins}\n"
        "Прошли проверки: {passed}\n"
        "\n"
        "За пользователя: {cpa}\n"
        "Со спонсоров: {percent}%\n"
        "Курс выплаты: 1 ед. = {rate} ₽\n"
        "Минимум: {min_payout}\n"
        "Способы: карта или ЮMoney.</blockquote>"
    ),
    btn_partner_links="Мои ссылки",
    btn_partner_sponsors="Мои каналы",
    btn_partner_payout="Выплата",
    btn_partner_history="История выплат",
    btn_partner_back="‹ В партнёрскую панель",

    partner_links_caption=(
        "<b>Мои ссылки</b>\n"
        "──────────────\n"
        "\n"
        "{rows}\n"
        "\n"
        "⟡ <i>До {max_links} ссылок. Жми на ссылку — детали и удаление</i>"
    ),
    partner_links_empty="Ссылок пока нет. Нажми «Создать ссылку».",
    partner_link_row=(
        "<b>{title}</b>\n"
        "Переходы: {clicks} · регистрации: {joins} · проверки: {passed}"
    ),
    partner_link_card=(
        "<b>{title}</b>\n"
        "──────────────\n"
        "\n"
        "<code>{url}</code>\n"
        "\n"
        "╭ Переходы  <b>{clicks}</b>\n"
        "│ Регистрации  <b>{joins}</b>\n"
        "╰ Прошли проверки  <b>{passed}</b>\n"
        "\n"
        "⟡ <i>Пользователь учитывается один раз, до завершения проверок доступа.</i>"
    ),
    btn_partner_link_add="Создать ссылку",
    btn_partner_link_del="Удалить",
    partner_link_title_prompt=(
        "<b>Новая ссылка</b>\n"
        "──────────────\n"
        "\n"
        "<b>1</b> › Пришли название (до 64 символов).\n"
        "\n"
        "⟡ <i>Например: «Тикток-кампания» или «Чат N»</i>"
    ),
    partner_link_created_alert="Ссылка создана",
    partner_link_title_invalid="Название должно содержать от 1 до 64 символов.",
    partner_link_limit_alert="Лимит ссылок: {max_links}.",
    partner_link_deleted_alert="Ссылка удалена",

    partner_sponsors_caption=(
        "<b>Мои каналы</b>\n"
        "──────────────\n"
        "\n"
        "{rows}\n"
        "\n"
        "⟡ <i>Канал попадает в «Задания» после проверки владельцем</i>"
    ),
    partner_sponsors_empty="Каналов пока нет. Нажми «Добавить канал».",
    partner_sponsor_row="{status} <b>{title}</b> · {reward} / подписка",
    partner_sponsor_status_active="Активен",
    partner_sponsor_status_pending="На проверке",
    partner_sponsor_status_paused="На паузе",
    btn_partner_sponsor_add="Добавить канал",
    partner_sponsor_prompt=(
        "<b>Новый канал</b>\n"
        "──────────────\n"
        "\n"
        "<b>1</b> › Добавь бота админом в свой канал.\n"
        "<b>2</b> › Пришли @username канала.\n"
        "\n"
        "⟡ <i>Без прав админа бот не сможет проверять подписки</i>"
    ),
    partner_sponsor_invalid="Не вижу такой канал или бот в нём не админ. Проверь и пришли ещё раз.",
    partner_sponsor_exists="Этот канал уже добавлен.",
    partner_sponsor_created=(
        "<b>Канал отправлен на проверку</b>\n"
        "──────────────\n"
        "\n"
        "«{title}» появится в заданиях после активации владельцем."
    ),

    partner_payout_intro=(
        "<b>Партнёрская выплата</b>\n"
        "──────────────\n"
        "\n"
        "╭ Сумма  <b>{balance}</b>\n"
        "╰ К получению  <b>{rub} ₽</b>\n"
        "\n"
        "Курс: 1 ед. = {rate} ₽\n"
        "\n"
        "Выбери способ получения."
    ),
    btn_payout_card="Карта",
    btn_payout_yoomoney="ЮMoney",
    partner_payout_requisites_prompt=(
        "<b>Реквизиты выплаты</b>\n"
        "──────────────\n"
        "\n"
        "Сумма: <b>{amount}</b>\n"
        "\n"
        "Пришли {what} одним сообщением. Сумма будет зарезервирована до обработки."
    ),
    partner_payout_what_card="номер карты",
    partner_payout_what_yoomoney="номер кошелька ЮMoney",
    partner_payout_created=(
        "<b>Заявка на выплату принята</b>\n"
        "──────────────\n"
        "\n"
        "╭ Зарезервировано  <b>{amount}</b>\n"
        "╰ К получению  <b>{rub} ₽</b>\n"
        "\n"
        "Владелец обработает заявку вручную. Результат придёт в этот чат."
    ),
    partner_payout_too_small_alert="Минимальная сумма выплаты — {min_amount}.",
    partner_payout_pending_alert="У тебя уже есть заявка в обработке.",
    partner_payout_not_active_alert="⏸ Партнёрский доступ на паузе.",
    partner_payout_secure_error=(
        "<b>Заявка не создана</b>\n"
        "──────────────\n"
        "\n"
        "Защищённое хранилище временно недоступно. Баланс не списан — попробуй позже."
    ),
    partner_payout_requisites_invalid="Проверь реквизиты: нужно от 4 до 255 символов.",
    partner_history_caption=(
        "<b>История выплат</b>\n"
        "──────────────\n"
        "\n"
        "{rows}"
    ),
    partner_history_empty="Выплат пока не было.",
    partner_history_row="{status} <b>{stars}</b> → {rub}₽ · <i>{date}</i>",
    payout_status_pending="В обработке",
    payout_status_paid="Выплачено",
    payout_status_rejected="Отклонено",

    notify_partner_assigned=(
        "<b>Партнёрский доступ открыт</b>\n"
        "──────────────\n"
        "\n"
        "В профиле появилась «Партнёрская панель»: ссылки, статистика и выплаты."
    ),
    notify_payout_paid=(
        "<b>Выплата отправлена</b>\n"
        "──────────────\n"
        "\n"
        "<b>{stars}</b> → <b>{rub}₽</b> ушли на твои реквизиты."
    ),
    notify_payout_rejected=(
        "<b>Заявка на выплату отклонена</b>\n"
        "──────────────\n"
        "\n"
        "Возвращено на партнёрский счёт: <b>{stars}</b>.{note_part}"
    ),
    notify_payout_note_part=(
        "\n"
        "Комментарий: <i>{note}</i>"
    ),

    # ---------- PARTNER (Этап 10, админка) ----------
    btn_admin_partners="Партнёры",
    admin_pa_root=(
        "<b>Партнёры</b>\n"
        "──────────────\n"
        "Активных: <b>{active}</b> · Заявок на выплату: <b>{pending}</b>\n"
        "\n"
        "Выбери партнёра или назначь нового."
    ),
    admin_pa_row="{status} {name} · {balance}",
    btn_admin_pa_add="Назначить",
    btn_admin_pa_payouts="Заявки ({pending})",
    admin_pa_add_prompt=(
        "<b>Новый партнёр</b>\n"
        "──────────────\n"
        "Пришли <code>tg_id</code> или @username пользователя."
    ),
    admin_pa_user_not_found="Пользователь не найден. Он должен хотя бы раз запустить бота.",
    admin_pa_assigned="Партнёр назначен: {name}",
    admin_pa_card=(
        "<b>Партнёр #{id}</b>\n"
        "──────────────\n"
        "\n"
        "{user_info}\n"
        "Статус: <b>{status}</b>\n"
        "\n"
        "╭ Доступно  <b>{balance}</b>\n"
        "╰ Начислено всего  <b>{total_earned}</b>\n"
        "\n"
        "<blockquote expandable><b>Трафик и ставки</b>\n"
        "Ссылки: {links_count}\n"
        "Переходы: {clicks}\n"
        "Регистрации: {joins}\n"
        "Прошли проверки: {passed}\n"
        "\n"
        "За пользователя: {cpa}{cpa_mark}\n"
        "Со спонсоров: {percent}%{percent_mark}</blockquote>"
    ),
    admin_pa_custom_mark="· <i>персонально</i>",
    btn_admin_pa_pause="⏸ На паузу",
    btn_admin_pa_activate="▶ Активировать",
    btn_admin_pa_cpa="CPA",
    btn_admin_pa_percent="Процент",
    admin_pa_cpa_prompt=(
        "<b>Ставка партнёра</b>\n"
        "──────────────\n"
        "\n"
        "Сейчас: <b>{current}</b>{mark}\n"
        "\n"
        "Пришли сумму во внутренних единицах, например <code>1.5</code>.\n"
        "<code>-</code> вернёт стандартную ставку."
    ),
    admin_pa_percent_prompt=(
        "<b>Процент со спонсоров</b>\n"
        "──────────────\n"
        "Сейчас: <b>{current}%</b>{mark}\n"
        "Пришли новый % (например <code>40</code>) или <code>-</code> — вернуть дефолт."
    ),
    admin_pa_rate_invalid="Нужно число (или «-» для сброса).",
    admin_pa_rate_saved="Сохранено.",
    admin_pa_payouts_caption=(
        "<b>Заявки на выплату</b>\n"
        "──────────────\n"
        "\n"
        "{rows}"
    ),
    admin_pa_payouts_empty="Очередь пуста.",
    admin_pa_payout_row="#{id} · {name} · {stars} → {rub}₽",
    admin_pa_payout_card=(
        "<b>Выплата #{id}</b>\n"
        "──────────────\n"
        "\n"
        "Сумма: <b>{stars}</b> → <b>{rub} ₽</b>\n"
        "Курс: {rate}\n"
        "Партнёр: {user_info}\n"
        "\n"
        "Способ: <b>{method}</b>\n"
        "Реквизиты: <code>{requisites}</code>\n"
        "Создана: {date}\n"
        "\n"
        "Отметь выплату после фактического перевода или отклони заявку с возвратом резерва."
    ),
    btn_admin_pa_paid="Выплачено",
    btn_admin_pa_reject="Отклонить",
    admin_pa_payout_done_alert="Помечено выплаченным",
    admin_pa_payout_rejected_alert="Заявка отклонена. Резерв возвращён.",
    admin_pa_payout_gone_alert="Заявка уже обработана.",
    admin_pa_requisites_unavailable="защищённые данные недоступны",
    payout_method_card="Карта",
    payout_method_yoomoney="ЮMoney",
    log_partner_payout_requested="Партнёрская заявка #{id}: {name} · {stars} → {rub}₽",

    # ---------- SUPPORT (Этап 11, админка) ----------
    btn_admin_support="Поддержка",
    admin_sup_root=(
        "<b>Поддержка</b>\n"
        "──────────────\n"
        "\n"
        "╭ Новые  <b>{new}</b>\n"
        "│ Новые сообщения  <b>{in_progress}</b>\n"
        "│ Ожидают пользователя  <b>{awaiting}</b>\n"
        "╰ Закрытые  <b>{closed}</b>\n"
        "\n"
        "{hint}"
    ),
    admin_sup_root_hint="Открой обращение, чтобы прочитать переписку и ответить.",
    admin_sup_root_empty="Открытых обращений нет.",
    admin_sup_row="{status} #{id} · {user} · {subject}",
    btn_admin_sup_archive="Архив",
    btn_admin_sup_open="Открытые",
    admin_sup_archive_caption=(
        "<b>Архив поддержки</b>\n"
        "──────────────\n"
        "\n"
        "{hint}"
    ),
    admin_sup_archive_empty="Закрытых обращений пока нет.",
    admin_sup_card=(
        "<b>Обращение #{id}</b>\n"
        "──────────────\n"
        "\n"
        "Статус: <b>{status}</b>\n"
        "Пользователь: {user_info}\n"
        "Создано: {created}\n"
        "\n"
        "❖ <b>Переписка</b>\n"
        "{thread}"
    ),
    # статусы глазами админа
    admin_sup_status_new="Новый",
    admin_sup_status_in_progress="Новое сообщение",
    admin_sup_status_awaiting="Ожидает пользователя",
    admin_sup_status_closed="Закрыт",
    btn_admin_sup_reply="Ответить",
    btn_admin_sup_close="✓ Закрыть",
    admin_sup_reply_prompt=(
        "<b>Ответ по обращению #{id}</b>\n"
        "──────────────\n"
        "\n"
        "Пришли текст одним сообщением. Пользователь получит его в этом чате бота; ответ сохранится в обращении."
    ),
    admin_sup_reply_sent="Ответ отправлен пользовательу.",
    admin_sup_reply_empty="Ответ не может быть пустым.",
    admin_sup_reply_too_long="Ответ слишком длинный. Максимум — {max_len} символов.",
    admin_sup_close_confirm=(
        "<b>ЗАКРЫТЬ ОБРАЩЕНИЕ #{id}?</b>\n"
        "──────────────\n"
        "\n"
        "Пользователь получит уведомление, а переписка уйдёт в архив."
    ),
    admin_sup_closed_alert="✓ Обращение закрыто",
    admin_sup_not_found_alert="Обращение не найдено. Обнови список.",
    admin_sup_already_closed_alert="Обращение уже закрыто.",

    # ---------- Этап 13: бэкапы, дайджест, алерты ----------
    log_backup_caption="Бэкап БД · {stamp} МСК · {size_kb} КБ",
    log_daily_digest=(
        "<b>Обзор за сутки</b>\n"
        "──────────────\n"
        "\n"
        "Пользователи: <b>{users_total}</b> · новых: {users_new_today}\n"
        "Прошли проверки: {users_passed}\n"
        "\n"
        "Балансы: <b>{balance_total} ед.</b>\n"
        "Долги: <b>{debt_total} ед.</b>\n"
        "\n"
        "За сутки МСК: {clicks_today} нажатий · {bonuses_today} бонусов · {spins_today} вращений\n"
        "{tasks_today} заданий · {refs_today} друзей\n"
        "Отзывов на модерации: {reviews_pending}"
    ),
    log_worker_error="Воркер <code>{job_id}</code> упал: {error}",
    # Personal daily route and native clipboard actions.
    daily_reminder=(
        "<b>Бонус дня ещё доступен</b>\n"
        "──────────────\n"
        "\n"
        "Сегодняшний бонус пока не получен. Открой «Мой день», чтобы проверить условия и продолжить серию.\n"
        "\n"
        "⟡ <i>Вечернее напоминание можно отключить в «Уведомления».</i>"
    ),
    btn_menu_daily="☀️ Мой день",
    btn_ref_copy_link="⧉ Скопировать ссылку",
    daily_bonus_label="Бонус дня",
    daily_notification_name="Мой день",
    daily_notification_hint="Напоминание вечером, если бонус ещё не получен",
    daily_wheel_label="Бесплатное вращение",
    daily_clicker_label="Кликер",
    daily_tasks_label="Задания",
    daily_team_label="Приглашение друга",
    daily_done="Получено сегодня",
    daily_bonus_available="До {amount:.2f} ед. · условия в карточке бонуса",
    daily_bonus_unavailable="Проверка условий временно недоступна · попытка не расходуется",
    daily_wheel_available="Есть бесплатное вращение",
    daily_clicks="Нажатия: {current} из {total}",
    daily_cooldown="· следующий через {minutes} мин",
    daily_tasks_available="Доступно заданий: {count}",
    daily_team_hint="Подтверждённые друзья повышают уровень и лимит кликера",
    daily_action_row=(
        "{marker} <b>{label}</b>\n"
        "{detail}"
    ),
    daily_caption=(
        "☀️ <b>Мой день</b>\n"
        "──────────────\n"
        "\n"
        "Что доступно сейчас:\n"
        "\n"
        "{rows}\n"
        "\n"
        "⟡ <i>Лимиты обновятся <tg-time unix=\"{reset_unix}\" format=\"r\">в {reset} МСК</tg-time>. Условия — в карточке каждого действия.</i>"
    ),

    # ---------- Этап 7: подарки и очередь ----------
    btn_menu_gifts="🎁 Подарки",
    gift_internal_units="{amount} ед.",
    reward_restricted="Получение наград сейчас недоступно для этого аккаунта. За подробностями обратись в поддержку.",
    gift_notification=(
        "<b>Подарок · заявка #{request_id}</b>\n"
        "──────────────\n"
        "\n"
        "Статус: <b>{status}</b>\n"
        "\n"
        "Открой «Мои заявки», чтобы увидеть результат и доступные действия."
    ),
    gift_owner_alert=(
        "Заявка на подарок #{request_id}\n"
        "Статус: {status}.\n"
        "Открой выдачу подарков в админ-панели и проверь аккаунт, бюджет или результат операции."
    ),
    gift_owner_receipt_conflict="После ручного решения получено подтверждение Telegram. Нужна сверка учёта владельцем.",
    gift_statuses={
        "pending": "В очереди",
        "waiting_funds": "Ожидает условий отправки",
        "processing": "Отправляется",
        "succeeded": "Выдан",
        "failed": "Не выдан",
        "cancelled": "Отменена",
        "reconciliation_required": "Результат на проверке",
    },
    gift_premium_condition="Для отправки этого подарка требуется Telegram Premium у отправителя.",
    gift_limited_condition="Недоступен для отправки в SIRIUS. Остаток по данным Telegram: {count}.",
    btn_gift_history="Мои заявки",
    btn_gift_catalogue="‹ Каталог подарков",
    btn_gift_refresh="↻ Обновить",
    btn_gift_quote="Получить подарок",
    btn_gift_confirm="✓ Подтвердить · {cost}",
    btn_gift_cancel="✕ Отменить заявку",
    btn_gift_cancel_confirm="✓ Отменить и вернуть резерв",
    gift_catalogue=(
        "🎁 <b>Подарки</b>\n"
        "──────────────\n"
        "\n"
        "Здесь доступны обычные подарки Telegram. Выбери подарок, затем проверь стоимость и условия.\n"
        "\n"
        "{rows}\n"
        "\n"
        "<blockquote expandable><b>Как это работает</b>\n"
        "Стоимость заявки резервируется из внутреннего счёта SIRIUS после подтверждения. Настоящие Stars для оплаты находятся на аккаунте отправителя. Начисления в боте не пополняют твой Stars-баланс Telegram.</blockquote>"
    ),
    gift_catalogue_row=(
        "{marker} <b>{title}</b> · {stars} Stars\n"
        "{availability}"
    ),
    gift_catalogue_empty="Сейчас нет доступных обычных подарков. Обнови каталог позже.",
    gift_available="Доступен · проверим цену перед отправкой",
    gift_unavailable="Пока недоступен для отправки",
    gift_sold_out="Распродан",
    gift_unsupported="Этот подарок не входит в каталог обычных подарков. Выбери другой.",
    gift_restricted="Есть ограничения аккаунта или доступности",
    gift_card=(
        "<b>{title}</b>\n"
        "──────────────\n"
        "\n"
        "╭ Из счёта SIRIUS  <b>{cost}</b>\n"
        "╰ Цена Telegram  <b>{stars} Stars</b>\n"
        "\n"
        "{availability}\n"
        "\n"
        "Получатель: твой текущий аккаунт Telegram. Нажми «Получить подарок», чтобы проверить заявку.\n"
        "\n"
        "<blockquote expandable><b>Условия получения</b>\n"
        "{conditions}\n"
        "Выдаём обычные подарки Telegram.</blockquote>"
    ),
    gift_conditions="Условия допуска и дневной лимит проверяются при создании заявки.",
    gift_admission_rules=(
        "Минимальная стоимость: <b>{minimum}</b>\n"
        "Подтверждённых друзей: <b>{refs}</b>\n"
        "Заявок за сутки МСК: <b>{limit}</b>\n"
        "\n"
        "Нужны завершённые проверки доступа, обязательные подписки и отсутствие долга."
    ),
    gift_unlimited="без ограничения",
    gift_catalogue_page="Страница {page} из {pages}",
    btn_gift_page_back="‹ Предыдущие",
    btn_gift_page_next="Следующие ›",
    gift_confirmation=(
        "🎁 <b>Подтверждение подарка</b>\n"
        "──────────────\n"
        "\n"
        "<b>{title}</b>\n"
        "\n"
        "╭ В резерв SIRIUS  <b>{cost}</b>\n"
        "╰ Цена Telegram  <b>{stars} Stars</b>\n"
        "\n"
        "Получатель: твой текущий аккаунт Telegram.\n"
        "\n"
        "Подтверди заявку. До начала отправки её можно отменить и вернуть резерв с учётом долга.\n"
        "\n"
        "<blockquote expandable><b>Срок и повторная проверка</b>\n"
        "Заявка попадёт в очередь. Срок зависит от доступности подарка, бюджета и Stars отправителя. Подтверждение действует ограниченное время; цена и условия проверяются заново.</blockquote>"
    ),
    gift_request=(
        "🎁 <b>Подарок · заявка #{id}</b>\n"
        "──────────────\n"
        "\n"
        "Статус: <b>{status}</b>\n"
        "<b>{title}</b>\n"
        "\n"
        "╭ Стоимость SIRIUS  <b>{cost}</b>\n"
        "│ Средства  <b>{reserve}</b>\n"
        "╰ Цена Telegram  <b>{stars} Stars</b>\n"
        "\n"
        "{detail}\n"
        "{confirmation}\n"
        "\n"
        "⟡ <i>Создана: {created}.</i>"
    ),
    gift_history=(
        "📋 <b>Мои заявки</b>\n"
        "──────────────\n"
        "\n"
        "{rows}\n"
        "\n"
        "⟡ <i>Открой заявку, чтобы увидеть статус и действия.</i>"
    ),
    gift_history_empty="Пока нет заявок. Выбери подарок в каталоге.",
    gift_history_row=(
        "<b>#{id}</b> · {title}\n"
        "{status} · {cost}"
    ),
    gift_status_pending="В очереди",
    gift_status_waiting_funds="Ожидает условий отправки",
    gift_status_processing="Отправляется",
    gift_status_succeeded="Выдан",
    gift_status_failed="Не выдан",
    gift_status_cancelled="Отменена",
    gift_status_reconciliation_required="Результат на проверке",
    gift_status_unknown="Требует проверки",
    gift_reserve_held="Зарезервированы",
    gift_reserve_consumed="Учтены за выданный подарок",
    gift_reserve_released="Возвращены на внутренний счёт с учётом долга",
    gift_reserve_unknown="Требует проверки",
    gift_queue_detail="Место в очереди: <b>{position}</b>. Точное время отправки пока неизвестно.",
    gift_waiting_detail="На аккаунте отправителя недостаточно Stars. Резерв сохранён. После пополнения заявка сможет продолжиться; до отправки её можно отменить.",
    gift_budget_detail="Ожидаем доступного бюджета SIRIUS. Резерв сохранён. Точное время отправки неизвестно; до её начала заявку можно отменить.",
    gift_processing_detail="Отправка уже началась. Отмена недоступна — дождись результата.",
    gift_reconciliation_detail="Результат отправки пока неизвестен. Владелец проверяет его; резерв сохранён. Повторная покупка и возврат до сверки не запускаются.",
    gift_succeeded_detail="Подарок отправлен на твой аккаунт Telegram.",
    gift_failed_detail="Подарок не выдан. При подтверждённой неудаче резерв возвращается на счёт с учётом долга.",
    gift_cancelled_detail="Заявка отменена. Повторного списания по ней не будет.",
    gift_confirmation_telegram="✓ Выдача подтверждена Telegram.",
    gift_confirmation_manual="✓ Владелец подтвердил выдачу вручную.",
    gift_confirmation_unverified="Подтверждение выдачи отсутствует.",
    gift_cancel_prompt=(
        "✕ <b>Отменить заявку #{id}?</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Отмена доступна, пока отправка ещё не началась. Резерв вернётся на внутренний счёт: если появился долг, сначала погасит его."
    ),
    gift_error_unavailable="Подарки временно недоступны. Попробуй позже; существующие заявки сохранены.",
    gift_error_account="Аккаунт отправителя сейчас недоступен. Владелец проверяет подключение; заявки сохранены.",
    gift_error_recipient="Отправитель пока не может найти твой аккаунт Telegram. Напиши в поддержку — владелец поможет связать аккаунты.",
    gift_error_recipient_sender="Напиши любое сообщение аккаунту {sender}, затем повтори заявку. Это позволит отправителю найти тебя; username необязателен.",
    gift_error_price="Цена или доступность подарка изменилась. Обнови каталог и подтверди новую стоимость.",
    gift_error_funds="Недостаточно доступного внутреннего баланса для подарка.",
    gift_error_debt="Сначала нужно погасить долг внутри SIRIUS.",
    gift_error_refs="Недостаточно подтверждённых друзей. Проверь условия в карточке подарка и открой «Моя команда».",
    gift_error_minimum="Стоимость подарка ниже установленного минимума заявки. Выбери другой подарок.",
    gift_error_accounting="Операцию по заявке не удалось подтвердить. Обратись в поддержку: владельцу нужно проверить учёт средств.",
    gift_error_limit="Дневной лимит заявок исчерпан. Он обновится в полночь по Москве.",
    gift_error_access="Получение подарков сейчас недоступно для этого аккаунта.",
    gift_error_gates="Сначала заверши проверку доступа и обязательные подписки.",
    gift_error_not_found="Не удалось открыть подарок или заявку. Обнови каталог либо список своих заявок.",
    gift_error_cancel="Отмена уже недоступна. Открой заявку и проверь текущий статус.",
    gift_error_retry="Продолжить заявку сейчас нельзя. Неизвестный результат требует сверки.",
    gift_error_evidence="Для решения нужны проверяемые доказательства результата отправки.",
    gift_error_confirmation="Подтверждение устарело. Открой карточку заново.",
    gift_unavailable_alert="Подарок сейчас недоступен. Обнови каталог.",
    btn_admin_gifts="Выдача подарков",
    btn_admin_gift_queue="Очередь",
    btn_admin_gift_waiting="Ожидание",
    btn_admin_gift_reconciliation="Сверка",
    btn_admin_gift_history="История",
    btn_admin_gift_account="Аккаунт и бюджет",
    btn_admin_gift_retry="Продолжить ожидание",
    btn_admin_gift_success="✓ Подтвердить ручную выдачу",
    btn_admin_gift_failure="✕ Подтвердить неудачу и возврат",
    btn_admin_gift_back="‹ Выдача подарков",
    btn_admin_gift_decide="✓ Зафиксировать решение",
    admin_gift_root=(
        "🎁 <b>Выдача подарков</b>\n"
        "──────────────\n"
        "\n"
        "Выбери очередь, ожидание или сверку результата. Аккаунт отправителя и бюджет — на отдельной карточке.\n"
        "\n"
        "<blockquote expandable><b>Правила решения</b>\n"
        "Неизвестный результат сохраняет резерв. Повторная покупка и возврат запрещены до достоверной сверки. Ручные решения доступны только владельцу и сохраняются в аудите.</blockquote>"
    ),
    admin_gift_list=(
        "<b>{title}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "{rows}"
    ),
    admin_gift_empty="Заявок в этом разделе пока нет.",
    admin_gift_row=(
        "<b>#{id}</b> · {title}\n"
        "{status} · получатель <code>{recipient}</code>"
    ),
    admin_gift_detail=(
        "{card}\n"
        "\n"
        "<blockquote expandable><b>Данные владельца</b>\n"
        "Получатель: <code>{recipient}</code>\n"
        "Попытки: {attempts}\n"
        "{operations}\n"
        "{audit}</blockquote>"
    ),
    admin_gift_attempt="#{id}: {state}",
    admin_gift_operations="Подтверждение операции: {kind}",
    admin_gift_proof="Идентификаторы Telegram: <code>{reference}</code>",
    admin_gift_evidence="Основание владельца: {evidence}",
    admin_gift_money_row="#{id} · {reason} · баланс {balance} · резерв {reserve}",
    admin_gift_money_journal=(
        "Журнал внутреннего счёта:\n"
        "{rows}"
    ),
    admin_gift_money_reserve="Резервирование",
    admin_gift_money_release="Возврат резерва",
    admin_gift_money_consume="Учёт выдачи",
    admin_gift_audit="Последние решения: {rows}",
    admin_gift_audit_empty="Ручных решений ещё нет.",
    admin_gift_account=(
        "💳 <b>Аккаунт и бюджет</b>\n"
        "──────────────\n"
        "\n"
        "Статус: <b>{status}</b>\n"
        "\n"
        "╭ Stars отправителя  <b>{stars}</b>\n"
        "│ Расход за сутки МСК  <b>{spent} Stars</b>\n"
        "╰ Дневной бюджет  <b>{limit} Stars</b>\n"
        "\n"
        "{detail}\n"
        "\n"
        "<blockquote expandable><b>Раздельный учёт</b>\n"
        "Начисления SIRIUS не пополняют этот аккаунт. Расходы вне бота могут изменить настоящий Stars-баланс; перед покупкой он проверяется заново.</blockquote>"
    ),
    admin_gift_account_ready="Авторизован",
    admin_gift_account_offline="Не подключён / авторизация не подтверждена",
    admin_gift_account_unknown="Нет актуальных данных",
    admin_gift_account_ready_detail="Пополнение настоящих Stars выполняется владельцем. Перед покупкой проверяется фактический баланс.",
    admin_gift_account_offline_detail="Выполни вход через CLI userbot в интерактивном терминале. Код и пароль вводятся в терминале; затем нужна проверка реальной авторизации.",
    admin_gift_owner_only="Этот раздел доступен только владельцу.",
    admin_gift_evidence_prompt=(
        "<b>Сверка заявки #{id}</b>\n"
        "──────────────\n"
        "\n"
        "Действие: <b>{action}</b>\n"
        "\n"
        "Пришли проверяемое основание: идентификатор подтверждённой операции или проверки, однозначно доказывающие результат. Затем появится отдельное подтверждение.\n"
        "\n"
        "⟡ <i>Не присылай ключи, сессию, пароль или код входа.</i>"
    ),
    admin_gift_evidence_invalid="Основание должно содержать 12–1000 символов и объяснять подтверждённый результат.",
    admin_gift_action_retry="Продолжить заявку в ожидании",
    admin_gift_action_manual_success="Зафиксировать выдачу вручную",
    admin_gift_action_proven_failure="Подтвердить окончательную неудачу и вернуть резерв",
    admin_gift_decision_prompt=(
        "<b>Решение по заявке #{id}</b>\n"
        "──────────────\n"
        "\n"
        "<b>{action}</b>\n"
        "\n"
        "Основание:\n"
        "{evidence}\n"
        "\n"
        "Нажми «Зафиксировать решение», если данные проверены. Решение и владелец сохранятся в аудите.\n"
        "\n"
        "⟡ <i>Это подтверждение само по себе не совершает покупку.</i>"
    ),
    admin_gift_retry_evidence="Владелец подтвердил продолжение заявки после проверки Stars отправителя.",
    admin_gift_decision_saved="✓ Решение зафиксировано",
    profile_reserved_part=(
        "\n"
        "В резерве: <b>{reserved}</b>"
    ),
    profile_balance_note="Внутренние единицы SIRIUS. Начисления не пополняют Stars-баланс Telegram.",
    antifraud_rate_limited="Слишком много действий. Подожди {seconds} сек. и попробуй снова.",
    antifraud_owner_only="Антифрод и решения доступны только владельцу.",
    btn_admin_antifraud="🛡 Антифрод",
    btn_admin_antifraud_user="🛡 Сигналы риска",
    btn_antifraud_user="{tg_id} · риск {score}/100",
    btn_antifraud_new_task="＋ Скрытая ловушка",
    btn_antifraud_back="‹ Антифрод",
    btn_antifraud_reset="Пересмотреть ограничение",
    btn_antifraud_reset_confirm="Снять ограничение",
    btn_antifraud_create_confirm="Создать скрытое задание",
    antifraud_on="включено",
    antifraud_off="выключено",
    antifraud_root=(
        "🛡 <b>Антифрод</b>\n──────────────\n\n"
        "Лимит: {limit} действий за {window} сек.\nАвтоограничение: {auto}. Порог: строго выше {threshold}/100.\n\n"
        "{rows}\n\n"
        "Оценка — сумма наблюдаемых правил. Регулярные клики, новые рефералы, недавний первый вход и отсутствие username "
        "по отдельности и вместе не включают ограничение наград. Нужен отмеченный honeypot-сигнал.\n\n"
        "Ловушка может сработать ошибочно: проверь события и при необходимости сними ограничение с основанием."
    ),
    antifraud_empty="Нет пользователей в очереди проверки.",
    antifraud_queue_count="На этой странице: {count} пользователей.",
    antifraud_card=(
        "🛡 <b>Сигналы пользователя {tg_id}</b>\n──────────────\n\n"
        "Оценка: <b>{score}/100</b>\nРежим: {status}\n\n<b>Причины</b>\n{reasons}\n\n"
        "<b>Последние события</b>\n{events}\n\n"
        "Это наблюдение бота, а не доказательство личности или возраста Telegram-аккаунта."
    ),
    antifraud_restricted="награды ограничены",
    antifraud_observation="наблюдение; ограничение не включено",
    antifraud_no_signals="Пока нет активных сигналов.",
    antifraud_no_events="Пока нет событий.",
    antifraud_reason_row="• {name}: +{weight}",
    antifraud_event_row="• {when} · {name} · владелец {actor}\n{detail}",
    antifraud_signal_honeypot_promo="Отмеченный honeypot-промокод",
    antifraud_signal_honeypot_task="Claim скрытого honeypot-задания",
    antifraud_signal_rate_limit="Превышен лимит действий",
    antifraud_signal_ref_velocity="Быстрый приток рефералов",
    antifraud_signal_young_first_seen="Недавно впервые появился в боте",
    antifraud_signal_no_username="Нет username",
    antifraud_signal_click_pattern="Регулярные интервалы кликов",
    antifraud_signal_auto_shadow="Включено ограничение наград",
    antifraud_signal_owner_reset="Владелец пересмотрел ограничение",
    antifraud_signal_owner_create_task="Владелец создал скрытое задание",
    antifraud_reset_reason=(
        "🛡 <b>Пересмотр ограничения</b>\n──────────────\n\n"
        "Напиши основание проверки: что подтвердилось и почему ограничение нужно снять (8–500 символов). "
        "Следующим шагом будет отдельное подтверждение."
    ),
    antifraud_reason_invalid="Основание должно содержать 8–500 символов.",
    antifraud_reset_preview=(
        "<b>Подтверди пересмотр</b>\n──────────────\n\n{reason}\n\n"
        "Ограничение наград будет снято, старые сигналы останутся в аудите. Баланс, резерв, обычный бан и заявки подарков не меняются. "
        "Новые сильные события могут снова включить ограничение."
    ),
    antifraud_reset_saved="Ограничение снято; основание сохранено.",
    antifraud_hidden_task_title="Скрытая проверка антифрода",
    antifraud_create_preview=(
        "<b>Создать скрытую ловушку?</b>\n──────────────\n\n"
        "Будет добавлено отдельное синтетическое задание без канала, ссылки и награды. "
        "Оно не появится в обычном списке. Запрос claim его ID станет honeypot-сигналом. "
        "Существующие задания не меняются."
    ),
    antifraud_task_created="Скрытое задание #{id} создано; событие сохранено.",
    bonus_claim_ready="Нажми «Забрать награду», чтобы проверить условия и получить бонус.",
    bonus_claim_done="Награда за сегодня уже получена. Следующий бонус — после 00:00 МСК.",
    bot_public_name="SIRIUS · Подарки и награды",
    bot_public_short="Ежедневные награды, задания и друзья. Обмен внутреннего баланса на обычные Telegram-подарки.",
    bot_public_description=(
        "SIRIUS — твои награды в Telegram.\n\n"
        "Выполняй задания, приглашай друзей и собирай ежедневные бонусы. Обменивай внутренний баланс на обычные Telegram-подарки.\n\n"
        "Каталог, условия, статус заявки и поддержка — прямо в боте. Коллекционные и NFT-подарки не выдаются.\n\n"
        "Внутренний баланс SIRIUS учитывается отдельно от настоящих Telegram Stars."
    ),
)
