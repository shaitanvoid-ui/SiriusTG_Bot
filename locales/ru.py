from __future__ import annotations

from types import SimpleNamespace


T = SimpleNamespace(
    # ---------- общие ----------
    health_ok="ok",
    banned="🚫 Доступ закрыт.",
    error_generic="⚠️ Что-то пошло не так. Попробуй ещё раз.",
    forbidden="⛔ Недостаточно прав.",
    closed="Окно закрыто.",

    # ---------- gates (текст для middleware-блокировок будущих этапов) ----------
    gate_terms_required="Сначала прими соглашение. /start",
    gate_captcha_required="Сначала пройди проверку. /start",
    gate_subs_required="Сначала подпишись на каналы. /start",

    # ---------- /start заглушка / финал онбординга ----------
    main_menu_stub=(
        "✨ <b>Готово, {name}</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Аккаунт активирован. Главное меню откроется на следующем этапе разработки."
    ),

    # ---------- MAIN MENU (премиум-панель) ----------
    greeting_morning="☀️ Доброе утро",
    greeting_day="🌤 Добрый день",
    greeting_evening="🌇 Добрый вечер",
    greeting_night="🌙 Доброй ночи",
    menu_caption=(
        "{brand}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "{greeting}, <b>{name}</b>!\n"
        "\n"
        "╭  💎  Баланс       <b>{balance}</b>\n"
        "│  {level_emoji}  Уровень      <b>{level_name}</b>\n"
        "╰  👥  Рефералы    <b>{confirmed_refs}</b>\n"
        "\n"
        "     {progress_bar}\n"
        "     {progress_text}\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "❖  <b>ТРИ ШАГА К ЗВЁЗДАМ</b>\n"
        "\n"
        "   <b>1</b> ›  «👥 Рефералы» — твоя личная ссылка\n"
        "   <b>2</b> ›  Зови друзей — <b>{ref_reward}</b> за каждого\n"
        "   <b>3</b> ›  Меняй ⭐ на подарки — «💸 Вывод»\n"
        "\n"
        "⟡ <i>Кликер, бонус и колесо ждут в «💎 Заработать»</i>"
    ),
    menu_progress_to_next="<i>До «{next_name}» — ещё <b>{to_next}</b> реф.</i>",
    menu_progress_max="<i>Максимальный уровень. Так держать!</i>",

    # Главное меню — 6 крупных хабов
    btn_menu_earn="💎 Заработать",
    btn_menu_referrals="👥 Рефералы",
    btn_menu_withdraw="💸 Вывод подарков",
    btn_menu_profile="👤 Профиль",
    btn_menu_help="💬 Помощь",
    btn_menu_channel="📢 Наш канал",

    # Подраздел «Заработать»
    section_earn_caption=(
        "💎  <b>ЗАРАБОТАТЬ STARS</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Выбери свой способ:\n"
        "\n"
        "╭  👆  <b>Кликер</b>\n"
        "│      <i>Тапай — собирай ⭐ каждый день</i>\n"
        "│\n"
        "│  🎁  <b>Ежедневный бонус</b>\n"
        "│      <i>Стрик растёт — награда тоже</i>\n"
        "│\n"
        "│  🎡  <b>Колесо фортуны</b>\n"
        "│      <i>Бесплатное вращение каждый день</i>\n"
        "│\n"
        "╰  🎯  <b>Задания спонсоров</b>\n"
        "        <i>Подписка — мгновенная награда</i>\n"
        "\n"
        "⟡ <i>Все способы суммируются — комбинируй</i>"
    ),
    btn_earn_clicker="👆 Кликер",
    btn_earn_bonus="🎁 Ежедневный бонус",
    btn_earn_wheel="🎡 Колесо фортуны",
    btn_earn_tasks="🎯 Задания спонсоров",

    # Подраздел «Помощь»
    section_help_caption=(
        "💬  <b>ПОМОЩЬ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Чем тебе помочь?\n"
        "\n"
        "╭  📖  <b>Инструкция</b>\n"
        "│      <i>Как здесь всё устроено</i>\n"
        "│\n"
        "│  💬  <b>Поддержка</b>\n"
        "│      <i>Личный вопрос — пиши сюда</i>\n"
        "│\n"
        "╰  💝  <b>Оставить отзыв</b>\n"
        "        <i>Поделись впечатлением</i>"
    ),
    btn_help_instructions="📖 Инструкция",
    btn_help_support="💬 Поддержка",
    btn_help_review="💝 Оставить отзыв",

    # Подменю Профиля
    btn_profile_promo="🎟 Промокод",
    btn_profile_achievements="🏅 Достижения",
    btn_profile_history="📜 История",
    btn_profile_top="🏆 Топ-100",
    btn_profile_notifications="⚙ Уведомления",

    # ---------- SUPPORT (Этап 11, юзер-сайд) ----------
    support_disabled_alert="🛠 Поддержка временно недоступна. Загляни позже.",
    support_home=(
        "💬  <b>ПОДДЕРЖКА</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Мы на связи и поможем разобраться.\n"
        "\n"
        "╭  ❓  <b>FAQ</b>\n"
        "│      <i>Быстрые ответы на частые вопросы</i>\n"
        "│\n"
        "│  ✍️  <b>Новый вопрос</b>\n"
        "│      <i>Опиши проблему — ответим лично</i>\n"
        "│\n"
        "╰  📨  <b>Мои обращения</b>\n"
        "        <i>Статусы и переписка</i>\n"
        "\n"
        "⟡ <i>Загляни в FAQ — часто ответ уже там</i>"
    ),
    btn_support_faq="❓ FAQ",
    btn_support_new="✍️ Задать вопрос",
    btn_support_my="📨 Мои обращения",
    btn_support_back="◀ В поддержку",

    support_faq_home=(
        "❓  <b>FAQ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Выбери вопрос — покажу ответ.\n"
        "\n"
        "⟡ <i>Не нашёл своего? Жми «✍️ Задать вопрос»</i>"
    ),
    support_faq_answer=(
        "❓  <b>FAQ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "❖  <b>{question}</b>\n"
        "\n"
        "{answer}"
    ),
    btn_support_faq_back="◀ К вопросам",

    support_new_prompt=(
        "✍️  <b>НОВЫЙ ВОПРОС</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "<b>1</b> ›  Опиши проблему одним сообщением.\n"
        "\n"
        "⟡ <i>От {min_len} до {max_len} символов. Чем подробнее — тем быстрее поможем</i>"
    ),
    support_too_many_alert="⏳ Слишком много обращений за час. Передохни и попробуй позже.",
    support_text_too_short="⚠️ Коротковато. Опиши подробнее — от {min_len} символов.",
    support_text_too_long="⚠️ Слишком длинно. Уложись в {max_len} символов.",
    support_created=(
        "✅  <b>ОБРАЩЕНИЕ ПРИНЯТО</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Номер: <b>#{id}</b>\n"
        "\n"
        "Ответ придёт сюда, в этот чат.\n"
        "Статус — в «📨 Мои обращения»."
    ),

    support_my_list=(
        "📨  <b>МОИ ОБРАЩЕНИЯ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Выбери обращение — покажу переписку."
    ),
    support_my_empty=(
        "📨  <b>МОИ ОБРАЩЕНИЯ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Обращений пока нет.\n"
        "\n"
        "⟡ <i>Появился вопрос — жми «✍️ Задать вопрос»</i>"
    ),
    support_ticket_row="{status} #{id} · {subject}",
    support_ticket_card=(
        "📨  <b>ОБРАЩЕНИЕ #{id}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "╭  Статус       <b>{status}</b>\n"
        "╰  Создано     <b>{created}</b>\n"
        "\n"
        "❖  <b>ПЕРЕПИСКА</b>\n"
        "\n"
        "{thread}"
    ),
    support_thread_user_line="👤  {text}",
    support_thread_admin_line="🛡  {text}",
    # статусы глазами юзера
    support_status_new="🕓 На рассмотрении",
    support_status_in_progress="🕓 На рассмотрении",
    support_status_awaiting="💬 Есть ответ",
    support_status_closed="✔️ Закрыт",
    btn_support_reply="✍️ Дописать",
    btn_support_close="✔️ Закрыть вопрос",
    btn_support_to_my="📨 Мои обращения",
    support_reply_prompt=(
        "✍️  <b>ОТВЕТ В ОБРАЩЕНИЕ #{id}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "<b>1</b> ›  Напиши сообщение — добавлю его в переписку."
    ),
    support_reply_sent_alert="✅ Добавлено. Поддержка увидит твоё сообщение.",
    support_closed_alert="✔️ Обращение закрыто. Спасибо!",
    support_ticket_closed_alert="✔️ Это обращение уже закрыто.",
    notify_support_reply=(
        "💬  <b>ОТВЕТ ПОДДЕРЖКИ</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "\n"
        "По обращению <b>#{id}</b>:\n"
        "\n"
        "<i>{text}</i>"
    ),
    notify_support_closed=(
        "✔️  <b>ОБРАЩЕНИЕ #{id} ЗАКРЫТО</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "\n"
        "Если вопрос остался — напиши нам снова через «💬 Поддержка»."
    ),
    btn_support_open_ticket="📨 Открыть обращение",
    log_support_new_ticket="💬 Новое обращение <b>#{id}</b> от <code>{tg_id}</code>: {subject}",
    log_support_user_reply="💬 Юзер <code>{tg_id}</code> дописал в обращение <b>#{id}</b>",

    # ---------- NOTIFICATIONS (Этап 11) ----------
    notifications_card=(
        "⚙️  <b>УВЕДОМЛЕНИЯ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Выбери, о чём писать тебе в личку:\n"
        "\n"
        "{rows}\n"
        "\n"
        "⟡ <i>Сервисные сообщения и ответы поддержки приходят всегда</i>"
    ),
    notifications_row_on="{emoji}  <b>{name}</b> — вкл\n        <i>{hint}</i>",
    notifications_row_off="{emoji}  <b>{name}</b> — выкл\n        <i>{hint}</i>",
    btn_notifications_on="{emoji} {name} · ✅",
    btn_notifications_off="{emoji} {name} · ❌",
    notifications_toggled_on_alert="🔔 Включено",
    notifications_toggled_off_alert="🔕 Выключено",

    # ---------- HISTORY (Этап 11) ----------
    history_card=(
        "📜  <b>ИСТОРИЯ ОПЕРАЦИЙ</b>     <i>стр. {page} из {total_pages}</i>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "{rows}\n"
        "\n"
        "⟡ <i>Все начисления и списания, кроме тапов кликера</i>"
    ),
    history_empty=(
        "📜  <b>ИСТОРИЯ ОПЕРАЦИЙ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Пока пусто.\n"
        "\n"
        "⟡ <i>Самое время заработать первые ⭐ — раздел «💎 Заработать»</i>"
    ),
    history_row="{emoji}  <b>{amount}</b> — {title}\n        <i>{when}</i>",
    btn_history_prev="‹ Назад",
    btn_history_next="Вперёд ›",

    # ---------- INSTRUCTIONS (Этап 8) ----------
    ins_page_template=(
        "📖  <b>{title}</b>     <i>{step} из {total}</i>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "{body}"
    ),
    btn_ins_back="◀ В меню",

    # ---------- REVIEWS (Этап 8) ----------
    reviews_disabled="💝  <b>ОТЗЫВЫ</b>\n━━━━━━━━━━━━━━━━━━━\n\nРаздел временно выключен.",
    reviews_disabled_alert="🛠 Раздел отзывов временно выключен.",

    review_intro=(
        "💝  <b>ОСТАВИТЬ ОТЗЫВ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Расскажи, как тебе бот. Твой отзыв увидят другие.\n\n"
        "<b>Условия:</b>\n"
        "• Минимум {min_refs} подтверждённых рефералов\n"
        "• Отзыв не чаще раза в {cooldown_days} дней\n"
        "• Без ссылок, мата и капса >30%\n"
        "• Длина {min_len}–{max_len} символов\n\n"
        "За опубликованный отзыв — <b>{reward}⭐</b>.\n\n"
        "⟡ <i>Жми «Написать отзыв» — займёт минуту</i>"
    ),
    btn_review_start="💝 Написать отзыв",
    btn_review_cancel="✕ Отменить",
    btn_review_back="◀ Назад",
    btn_review_next="Далее ▶",
    btn_review_confirm="✅ Отправить",

    review_rating_page=(
        "💝 <b>Оцени по шкале</b>     <i>Шаг 1 из 4</i>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Как бы ты оценил наш бот?\n"
        "\n"
        "Нажми нужное количество звёзд на кнопках ниже."
    ),
    review_text_page=(
        "💝 <b>Напиши отзыв</b>     <i>Шаг 2 из 4</i>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "{rating_line}\n\n"
        "Расскажи подробнее:\n"
        "<i>Без ссылок, мата, капса >30%. "
        "Длина {min_len}–{max_len} символов.</i>"
    ),
    review_anonymity_page=(
        "💝 <b>Анонимность</b>     <i>Шаг 3 из 4</i>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "{rating_line}\n"
        "{text_preview}\n\n"
        "Показать твой username?"
    ),
    btn_review_public="✅ Да, с username",
    btn_review_anonymous="🔒 Нет, анонимно",

    review_confirm_page=(
        "💝 <b>Подтверди</b>     <i>Шаг 4 из 4</i>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "{rating_line}\n"
        "{text_preview}\n"
        "Анонимность: {anon_line}\n\n"
        "Отправить?"
    ),
    review_anon_public="публичный (с username)",
    review_anon_anon="анонимный",
    review_rating_stars="{stars}  <b>{rating} из 5</b>",

    review_success=(
        "✅ <b>Спасибо за отзыв!</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Твой отзыв отправлен на модерацию.\n"
        "После проверки он появится в канале.\n"
        "{reward_line}"
    ),
    review_success_reward="\n\n🏅 После публикации получишь: <b>{reward}⭐</b>",
    review_filter_fail=(
        "⚠️ <b>Не прошло проверку</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "{reason}\n\n"
        "Попробуй ещё раз."
    ),
    # плоские варианты для callback-алертов: Telegram не рендерит HTML в alert
    review_filter_fail_alert="⚠️ {reason}. Попробуй ещё раз.",
    review_antispam_fail=(
        "⚠️ <b>Пока нельзя</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "{reason}\n\n"
        "Попробуй позже."
    ),
    review_antispam_fail_alert="⚠️ {reason}. Попробуй позже.",

    log_review_submitted="💝 Отзыв от <code>{tg_id}</code> · {rating}⭐ · pending",
    review_channel_post=(
        "💝  <b>ОТЗЫВ</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "\n"
        "{stars}\n"
        "\n"
        "{text}\n"
        "\n"
        "⟡ <i>{author}</i>"
    ),
    review_channel_anon="Аноним",
    notify_review_approved=(
        "✅  <b>ОТЗЫВ ОПУБЛИКОВАН</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "\n"
        "Спасибо! Твой отзыв прошёл модерацию.{reward_line}"
    ),
    notify_review_reward_part="\n\n🏅 Награда: <b>+{reward}⭐</b>",
    log_review_approved="✅ Отзыв одобрен <code>{id}</code>",
    log_review_rejected="❌ Отзыв отклонён <code>{id}</code>",
    log_review_converted="📝 Отзыв конвертирован в тикет <code>{id}</code>",

    # ---------- REVIEWS (moderation — админ) ----------
    review_mod_card=(
        "💝 <b>Отзыв #{id}</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Юзер: {user_info}\n"
        "Рейтинг: {rating_stars}\n"
        "Анонимный: {is_anon}\n"
        "Дата: {date}\n\n"
        "<b>Текст:</b>\n{text}"
    ),
    review_mod_anonymous="✅ Да",
    review_mod_public="🔒 Нет",
    btn_review_approve="✅ Опубликовать",
    btn_review_reject="❌ Отклонить",
    btn_review_convert="📝 В тикет",
    btn_review_mod_back="◀ К списку",

    review_reject_confirm=(
        "❌ <b>Отклонить отзыв #{id}</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Пришли комментарий для модератора (не обязательно):"
    ),
    review_convert_confirm=(
        "📝 <b>Конвертировать в тикет #{id}</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Пришли комментарий для тикета:"
    ),
    review_reject_done="❌ Отзыв отклонён.",
    review_convert_done="📝 Отзыв конвертирован в тикет поддержки.",
    review_already_done="⚠️ Отзыв уже обработан.",
    review_not_found="🚫 Отзыв не найден.",

    btn_admin_reviews="💝 Отзывы",
    btn_admin_stop_words="🛡 Стоп-слова",
    btn_admin_back_from_reviews="◀ В админку",
    channel_unset_alert="📢 Ссылка на канал ещё не настроена.",
    soon_alert="🛠 Скоро появится.",

    # ---------- PROFILE ----------
    profile_caption=(
        "👤  <b>ПРОФИЛЬ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "<b>{name}</b>\n"
        "{username_line}"
        "<code>ID {tg_id}</code>\n"
        "\n"
        "❖  <b>КАПИТАЛ</b>\n"
        "╭  💎  Баланс        <b>{balance}</b>{debt_part}\n"
        "╰  🔥  Стрик          <b>{streak} дн.</b>\n"
        "\n"
        "❖  <b>УРОВЕНЬ</b>\n"
        "   {level_emoji}  <b>{level_name}</b>\n"
        "   {progress_bar}\n"
        "   {progress_text}\n"
        "\n"
        "❖  <b>РЕФЕРАЛЫ</b>\n"
        "╭  Всего            <b>{ref_total}</b>\n"
        "│  Подтверждено     <b>{ref_confirmed}</b>\n"
        "╰  Закрепилось      <b>{ref_matured}</b>\n"
        "\n"
        "⟡ <i>С нами с {join_date}</i>"
    ),
    profile_debt_part="  ·  долг <b>{debt}</b>",
    profile_no_username_line="",
    profile_username_line="@{username}\n",

    # ---------- REFERRALS ----------
    referral_caption=(
        "👥  <b>РЕФЕРАЛЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "За каждого активного друга — <b>{reward}</b>.\n"
        "Друг засчитывается после подписки на обязательные каналы.\n"
        "\n"
        "❖  <b>ТВОЯ ССЫЛКА</b>\n"
        "<code>{link}</code>\n"
        "\n"
        "❖  <b>СТАТИСТИКА</b>\n"
        "╭  Приглашено       <b>{total}</b>\n"
        "│  Подтверждено     <b>{confirmed}</b>\n"
        "│  Закрепилось      <b>{matured}</b>\n"
        "╰  Заработано       <b>{earned}</b>{debt_part}\n"
        "\n"
        "⟡ <i>Реф остаётся за тобой навсегда. Если друг отпишется до созревания "
        "({maturation_days} дн.) — звёзды снимутся. {limit_part}</i>"
    ),
    referral_debt_part="  ·  долг <b>{debt}</b>",
    referral_no_limit="Лимита на приглашения нет — зови сколько хочешь.",
    referral_with_limit="Лимит — <b>{daily_limit}</b> новых в сутки.",

    btn_ref_copy_text="📋 Готовый текст",
    btn_ref_share="🔗 Поделиться",

    ref_share_view_caption=(
        "📋  <b>ГОТОВЫЙ ТЕКСТ ДЛЯ ДРУЗЕЙ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Зажми, скопируй и вставь куда хочешь:\n"
    ),
    ref_share_text=(
        "✨ Зарабатывай Stars в Telegram\n"
        "\n"
        "Я качаю звёзды и меняю их на подарки прямо в Telegram. Подключайся:\n"
        "{link}"
    ),
    btn_ref_back="◀ К рефералам",

    # ---------- REWARD / LOST уведомления (Этап 3 — простые) ----------
    notify_ref_reward=(
        "🎉  <b>+{amount}</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Твой реферал прошёл проверку.\n"
        "Награда уже на балансе. Так держать!"
    ),
    notify_ref_lost=(
        "⚠️ <b>Реф отвалился</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Один из твоих друзей отписался от каналов раньше срока.\n"
        "Списано: <b>{amount}</b>{debt_part}"
    ),
    notify_ref_lost_debt=", в долг — <b>{debt}</b>",

    notify_self_subs_lost=(
        "⚠️ <b>Проверь подписки</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Похоже, ты отписался от обязательных каналов.\n"
        "Нажми /start, чтобы вернуть доступ."
    ),

    notify_task_lost=(
        "⚠️ <b>Задание отменено</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Ты отписался от «{title}» — награда <b>{amount}</b> списана.\n"
        "Подпишись снова — задание появится в списке."
    ),
    log_task_lost="⚠️ Задание потеряно у <code>{tg_id}</code> · «{title}» · −{amount}{debt_part}",

    # ---------- лог-канал (для админа) ----------
    log_ref_attached="🔗 Привязка: <code>{user_tg_id}</code> → реферер <code>{referrer_tg_id}</code> ({source})",
    log_ref_confirmed="✅ Подтверждён реф для <code>{referrer_tg_id}</code> · +{reward}",
    log_ref_lost="⚠️ Реф отвалился у <code>{referrer_tg_id}</code> · −{amount}{debt_part}",
    log_subrecheck_summary="🔍 sub-rechecker: проверено <b>{checked}</b>, отвалов <b>{lost}</b>",
    log_tasks_recheck_summary="🎯 tasks-rechecker: проверено <b>{checked}</b>, потеряно <b>{lost}</b>",

    # ---------- TERMS (Шаг 1) ----------
    # Шапка + тело страницы (тело — индекс из terms_pages_bodies).
    terms_page_template=(
        "📜  <b>СОГЛАШЕНИЕ</b>     <i>{step}</i>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "{dots}   <i>стр. {page} из {total}</i>\n"
        "\n"
        "{body}"
    ),
    terms_pages_bodies=(
        # ---- 1/6 ----
        "🚀  <b>Что это за бот</b>\n"
        "\n"
        "<b>SIRIUS</b> — бот для заработка Telegram Stars (⭐).\n"
        "Звёзды можно копить и менять на подарки Telegram прямо здесь.\n"
        "\n"
        "Заработок:\n"
        "•  Приглашение друзей\n"
        "•  Задания спонсоров (подписки за награду)\n"
        "•  Кликер\n"
        "•  Ежедневный бонус и стрик\n"
        "•  Промокоды\n"
        "•  Колесо фортуны\n"
        "\n"
        "<i>Дальше — как всё устроено. Прочитай до конца — потом нажми «Принимаю».</i>",
        # ---- 2/6 ----
        "💎  <b>Как зарабатывать</b>\n"
        "\n"
        "▸  Звёзды (⭐) — внутренняя валюта бота. Внутри бота можно обменять на подарки Telegram.\n"
        "\n"
        "▸  Размеры наград и условия могут меняться. Свежие значения — в боте и в нашем канале.\n"
        "\n"
        "▸  Часть способов открывается по мере роста уровня. Уровень растёт с подтверждёнными рефералами.\n"
        "\n"
        "<i>Уровни дают множители на кликер и больший дневной лимит.</i>",
        # ---- 3/6 ----
        "👥  <b>Рефералы</b>\n"
        "\n"
        "▸  За каждого друга, который придёт по твоей ссылке и подпишется на обязательные каналы — награда тебе.\n"
        "\n"
        "▸  <b>Лимита на приглашения нет.</b> Зови сколько хочешь.\n"
        "\n"
        "▸  Реф «созревает» через 7 дней. Если друг отпишется от обязательных каналов до этого срока — звёзды снимаются с тебя.\n"
        "\n"
        "▸  Если на балансе меньше, чем нужно списать — уйдёт в долг. Следующие награды сперва погасят долг.\n"
        "\n"
        "▸  Сам счётчик рефералов не уменьшается — друг закреплён за тобой навсегда.",
        # ---- 4/6 ----
        "💸  <b>Вывод подарков</b>\n"
        "\n"
        "▸  Минимум для вывода — <b>15⭐</b> (значение может меняться).\n"
        "\n"
        "▸  Вывод — официальными подарками Telegram через нашего бота. Подарок придёт тебе в Telegram, дальше — на твоё усмотрение.\n"
        "\n"
        "▸  Не более <b>5 выводов в сутки</b> на юзера.\n"
        "\n"
        "▸  Условия: пройдена капча, есть подтверждённые рефералы, нет shadow-бана.\n"
        "\n"
        "▸  При нехватке внутреннего запаса ⭐ — заявка ждёт в очереди, тебе показывается позиция.",
        # ---- 5/6 ----
        "🛡  <b>Что нельзя</b>\n"
        "\n"
        "▸  Скрипты, эмуляторы, прокси-фермы, авто-кликеры, накрутка ботами — <b>бан без возврата</b>.\n"
        "\n"
        "▸  Honeypot-промокоды и фейковые задания. Не вводи код, которого нет в открытых источниках.\n"
        "\n"
        "▸  Подозрительная активность → shadow-ban: бот выглядит как обычно, но награды не начисляются.\n"
        "\n"
        "▸  В отзывах и поддержке — без мата, рекламы, ссылок на сторонние сервисы.\n"
        "\n"
        "<i>Главное — никаких скриптов и фрод-активности.</i>",
        # ---- 6/6 ----
        "📌  <b>Ответственность</b>\n"
        "\n"
        "•  Бот — частный проект, <b>не официальный сервис Telegram</b>.\n"
        "•  При сбоях вывода — поддержка решает индивидуально.\n"
        "•  Массовые сбои — компенсация на усмотрение администрации.\n"
        "\n"
        "📝  <b>Изменения</b>\n"
        "\n"
        "•  Правила могут меняться. Свежая версия — всегда здесь.\n"
        "•  Существенные изменения анонсим в канале.\n"
        "\n"
        "<i>Нажимая «Принимаю», ты подтверждаешь, что прочитал и согласен.</i>",
    ),
    terms_accept_btn="✅ Принимаю",
    terms_decline_btn="✕ Не принимаю",
    terms_next_btn="Далее ▶",
    terms_prev_btn="◀ Назад",
    terms_declined="Без согласия бот недоступен. Возвращайся, когда будешь готов.",

    # ---------- CAPTCHA (Шаг 2) ----------
    captcha_caption=(
        "🤖  <b>ПРОВЕРКА</b>     <i>{step}</i>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Какой эмодзи <b>есть на картинке</b>?\n"
        "\n"
        "⟡ <i>Подсказка: один из четырёх ниже</i>"
    ),
    captcha_wrong="❌ Не то. Осталось попыток: {left}",
    captcha_failed="Слишком много неудачных попыток. Подожди и нажми /start.",
    captcha_ok="✅ Готово.",

    # ---------- SUBS (Шаг 3) ----------
    subs_caption=(
        "📢  <b>ПОДПИСКИ</b>     <i>{step}</i>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Финал. Подпишись на каналы ниже — и нажми «Проверить».\n"
        "\n"
        "⟡ <i>Каналы — основа экономики бота. Они оплачивают твои звёзды</i>"
    ),
    subs_check_btn="🔄 Проверить",
    subs_not_subscribed="❌ Подписался не на все каналы.",
    subs_all_ok="✅ Все подписки на месте.",
    subs_open_btn_prefix="📢",

    # ---------- ADMIN ----------
    admin_only="⛔ Только для администраторов.",
    admin_root=(
        "🛠  <b>АДМИН-ПАНЕЛЬ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Выбери раздел."
    ),

    # ---------- ADMIN: DASHBOARD (Этап 9) ----------
    btn_admin_dash="📊 Дашборд",
    btn_admin_system="🔧 Система",
    btn_admin_economy="⚙ Экономика",
    btn_admin_broadcast="📨 Рассылка",
    btn_admin_instructions="📖 Инструкция",
    btn_admin_channel="📣 Канал",
    btn_admin_refresh="🔄 Обновить",
    admin_dash=(
        "📊  <b>ДАШБОРД</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "❖  <b>ЮЗЕРЫ</b>\n"
        "╭  Всего            <b>{users_total}</b>\n"
        "│  Прошли гейт      <b>{users_passed}</b>\n"
        "│  Новых сегодня    <b>{users_new_today}</b>\n"
        "╰  Бан / shadow     <b>{users_banned}</b> / <b>{users_shadow}</b>\n"
        "\n"
        "❖  <b>ОБЯЗАТЕЛЬСТВА</b>\n"
        "╭  Балансы          <b>{balance_total}</b>\n"
        "╰  Долги            <b>{debt_total}</b>\n"
        "\n"
        "❖  <b>СЕГОДНЯ (МСК)</b>\n"
        "╭  Тапов            <b>{clicks_today}</b>\n"
        "│  Бонусов          <b>{bonuses_today}</b>\n"
        "│  Спинов колеса    <b>{spins_today}</b>\n"
        "│  Заданий          <b>{tasks_today}</b>\n"
        "╰  Новых рефов      <b>{refs_today}</b>\n"
        "\n"
        "⟡ <i>Отзывов на модерации: {reviews_pending}</i>"
    ),
    admin_system=(
        "🔧  <b>СИСТЕМА</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "❖  <b>ВОРКЕРЫ</b>\n"
        "╭  sub_rechecker      каждые <b>{sub_interval}ч</b>\n"
        "│  tasks_rechecker    каждые <b>{tasks_interval}м</b>\n"
        "│  ref_maturation     ежечасно\n"
        "╰  top_payout         пн 03:05 МСК\n"
        "\n"
        "❖  <b>USERBOT</b>\n"
        "   {userbot_state}\n"
        "\n"
        "❖  <b>КАНАЛ ПРОЕКТА</b>\n"
        "   {channel_state}\n"
        "\n"
        "⟡ <i>Лог-канал: {log_channel}</i>"
    ),
    admin_userbot_on="✅ подключён",
    admin_userbot_off="❌ не подключён (нет TG_API_ID/HASH)",
    admin_channel_unset="<i>не настроен</i>",

    # ---------- ADMIN: USERS (Этап 9) ----------
    admin_users_intro=(
        "👥  <b>ЮЗЕРЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Пришли <code>tg_id</code> или <code>@username</code> юзера\n"
        "одним сообщением — открою карточку."
    ),
    admin_user_not_found="🔍 Юзер не найден. Проверь ID/username.",
    admin_user_card=(
        "👤  <b>ЮЗЕР</b>  <code>{tg_id}</code>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "<b>{name}</b>\n"
        "{username_line}"
        "\n"
        "❖  <b>СОСТОЯНИЕ</b>\n"
        "╭  💎  Баланс       <b>{balance}</b>\n"
        "│  💸  Долг          <b>{debt}</b>\n"
        "│  👥  Рефералов    <b>{refs}</b> (подтв. {confirmed})\n"
        "╰  🔥  Стрик         <b>{streak} дн.</b>\n"
        "\n"
        "❖  <b>СТАТУСЫ</b>\n"
        "╭  Гейт пройден     {passed}\n"
        "│  Бан              {banned}\n"
        "╰  Shadow-ban       {shadow}\n"
        "\n"
        "❖  <b>ПОСЛЕДНИЕ ДЕЙСТВИЯ</b>\n"
        "{actions}\n"
        "\n"
        "⟡ <i>Зарегистрирован {created}</i>"
    ),
    admin_user_actions_empty="   <i>пока пусто</i>",
    admin_user_action_row="   ·  {action}  <i>{when}</i>",
    btn_admin_user_ban="🚫 Забанить",
    btn_admin_user_unban="✅ Разбанить",
    btn_admin_user_shadow_on="👻 Shadow-ban",
    btn_admin_user_shadow_off="👻 Снять shadow",
    btn_admin_user_balance="💎 Баланс ±",
    btn_admin_user_search="🔍 Найти другого",
    admin_user_balance_prompt=(
        "💎  <b>БАЛАНС ±</b>  <code>{tg_id}</code>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Текущий: <b>{balance}</b>\n"
        "\n"
        "Пришли число: <code>5</code> — начислить, <code>-3.5</code> — списать.\n"
        "\n"
        "⟡ <i>Списание при нехватке уйдёт в долг</i>"
    ),
    admin_user_balance_invalid="⚠️ Нужно число, например <code>5</code> или <code>-3.5</code>.",
    admin_user_balance_done="✅ Готово: {delta} → баланс <b>{balance}</b>",
    admin_user_banned_alert="🚫 Юзер забанен.",
    admin_user_unbanned_alert="✅ Бан снят.",
    admin_user_shadow_on_alert="👻 Shadow-ban включён.",
    admin_user_shadow_off_alert="👻 Shadow-ban снят.",

    # ---------- ADMIN: ECONOMY (Этап 9) ----------
    admin_eco_root=(
        "⚙  <b>ЭКОНОМИКА</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Все числа экономики живут в settings.\n"
        "Выбери группу ключей."
    ),
    admin_eco_group=(
        "⚙  <b>ЭКОНОМИКА · {group}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "{rows}\n"
        "\n"
        "⟡ <i>Нажми ключ, чтобы изменить значение</i>"
    ),
    admin_eco_row="   <code>{key}</code> = <b>{value}</b>",
    admin_eco_edit_prompt=(
        "⚙  <b>ПРАВКА КЛЮЧА</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "<code>{key}</code>\n"
        "<i>{description}</i>\n"
        "\n"
        "Текущее: <b>{value}</b>  ·  тип <b>{type}</b>\n"
        "\n"
        "Пришли новое значение одним сообщением.\n"
        "⟡ <i>Для JSON-структур — валидный JSON</i>"
    ),
    admin_eco_invalid="⚠️ Не удалось разобрать значение типа <b>{type}</b>. Попробуй ещё раз.",
    admin_eco_saved="✅ <code>{key}</code> = <b>{value}</b>",

    # ---------- ADMIN: BROADCAST (Этап 9) ----------
    admin_bc_intro=(
        "📨  <b>РАССЫЛКА</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Получателей: <b>{count}</b>\n"
        "\n"
        "Пришли текст рассылки одним сообщением.\n"
        "⟡ <i>HTML-разметка поддерживается</i>"
    ),
    admin_bc_preview=(
        "📨  <b>ПРЕДПРОСМОТР</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "{text}\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Получателей: <b>{count}</b>. Отправляем?"
    ),
    btn_admin_bc_send="🚀 Отправить",
    btn_admin_bc_cancel="✕ Отменить",
    admin_bc_progress="📨 Рассылка…  <b>{done}</b> / {total}",
    admin_bc_done=(
        "✅  <b>РАССЫЛКА ЗАВЕРШЕНА</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "╭  Всего          <b>{total}</b>\n"
        "│  Доставлено     <b>{sent}</b>\n"
        "╰  Недоступно     <b>{failed}</b>"
    ),
    admin_bc_cancelled="Рассылка отменена.",
    admin_bc_empty="⚠️ Пустой текст. Пришли текст рассылки.",

    # ---------- ADMIN: INSTRUCTIONS (Этап 8 доделка) ----------
    admin_ins_root=(
        "📖  <b>ИНСТРУКЦИЯ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Страниц: <b>{count}</b>\n"
        "\n"
        "⟡ <i>Нажми страницу для редактирования</i>"
    ),
    admin_ins_card=(
        "📖  <b>СТРАНИЦА #{id}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "<b>{title}</b>\n"
        "\n"
        "{body}"
    ),
    admin_ins_new_title_prompt=(
        "📖  <b>НОВАЯ СТРАНИЦА</b>     <i>Шаг 1 из 2</i>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Пришли заголовок страницы."
    ),
    admin_ins_new_body_prompt=(
        "📖  <b>НОВАЯ СТРАНИЦА</b>     <i>Шаг 2 из 2</i>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Заголовок: <b>{title}</b>\n"
        "\n"
        "Теперь пришли текст страницы.\n"
        "⟡ <i>HTML-разметка поддерживается</i>"
    ),
    admin_ins_edit_title_prompt=(
        "✏  <b>НОВЫЙ ЗАГОЛОВОК</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Текущий: <b>{title}</b>\n"
        "Пришли новый заголовок."
    ),
    admin_ins_edit_body_prompt=(
        "✏  <b>НОВЫЙ ТЕКСТ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Страница: <b>{title}</b>\n"
        "Пришли новый текст.\n"
        "⟡ <i>HTML-разметка поддерживается</i>"
    ),
    admin_ins_created="✅ Страница <b>{title}</b> добавлена.",
    admin_ins_saved="✅ Сохранено.",
    admin_ins_deleted="🗑 Страница удалена.",
    admin_ins_invalid="⚠️ Текст не может быть пустым.",
    btn_admin_ins_add="➕ Добавить страницу",
    btn_admin_ins_edit_title="✏ Заголовок",
    btn_admin_ins_edit_body="✏ Текст",
    btn_admin_ins_delete="🗑 Удалить",

    # ---------- ADMIN: CHANNEL (Этап 8 доделка) ----------
    admin_channel_card=(
        "📣  <b>КАНАЛ ПРОЕКТА</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Текущий: {current}\n"
        "\n"
        "Канал показывается кнопкой в главном меню\n"
        "и автоматически добавляется обязательным спонсором.\n"
        "\n"
        "⟡ <i>Чтобы сменить — пришли</i> <code>@username</code> <i>публичного канала</i>"
    ),
    admin_channel_invalid=(
        "⚠️ Не получилось. Пришли <code>@username</code> публичного канала, "
        "где бот — админ."
    ),
    admin_channel_set="✅ Канал <b>{title}</b> установлен и добавлен обязательным спонсором.",

    # ---------- ADMIN: STOP WORDS (Этап 8 доделка) ----------
    admin_sw_root=(
        "🛡  <b>СТОП-СЛОВА</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Слов в фильтре отзывов: <b>{count}</b>\n"
        "\n"
        "{words}\n"
        "\n"
        "⟡ <i>Отзывы с этими словами не проходят авто-фильтр</i>"
    ),
    admin_sw_empty="   <i>список пуст</i>",
    admin_sw_add_prompt="🛡 Пришли слово (или несколько через запятую) для добавления.",
    admin_sw_remove_prompt="🛡 Пришли слово для удаления.",
    admin_sw_added="✅ Добавлено: <b>{count}</b>",
    admin_sw_removed="✅ Удалено.",
    admin_sw_not_found="🔍 Такого слова нет в списке.",
    btn_admin_sw_add="➕ Добавить",
    btn_admin_sw_remove="➖ Удалить",
    admin_sponsors_root=(
        "📢 <b>Спонсоры</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "{count_line}"
    ),
    admin_sponsors_empty="Список пуст. Добавь первого канала кнопкой ниже.",
    admin_sponsors_count="Всего: <b>{total}</b> · Активных: <b>{active}</b> · Обяз.: <b>{required}</b>",

    admin_sponsor_card=(
        "📢 <b>{title}</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "ID: <code>{id}</code>\n"
        "Тип: {kind}\n"
        "{ident_line}"
        "Статус: {status}\n"
        "Обязательный: {required}\n"
        "{stats_line}"
    ),
    admin_sponsor_stats="Подписалось через бота: <b>{counter}</b>{limit_part}",
    admin_sponsor_kind_public="🌐 Публичный",
    admin_sponsor_kind_private="🔒 Приватный",
    admin_sponsor_status_active="✅ Активен",
    admin_sponsor_status_paused="⏸ На паузе",
    admin_sponsor_required_yes="🔴 Да",
    admin_sponsor_required_no="🟢 Нет (опц.)",
    admin_sponsor_deleted="🗑 Спонсор удалён.",
    admin_sponsor_toggled_on="▶ Активирован.",
    admin_sponsor_toggled_off="⏸ Приостановлен.",
    admin_sponsor_required_toggled="🔁 Обязательность переключена.",

    btn_admin_users="👥 Юзеры",
    btn_admin_sponsors="📢 Спонсоры",
    btn_admin_settings="⚙ Настройки",
    btn_admin_stats="📊 Статистика",
    btn_admin_section_soon=" (скоро)",

    btn_sponsor_toggle_active="⏸ Пауза / ▶ Запуск",
    btn_sponsor_toggle_required="🔁 Переключить обяз.",
    btn_sponsor_delete="🗑 Удалить",
    btn_sponsor_delete_confirm="🗑 Точно удалить?",
    btn_sponsor_delete_cancel="✕ Отмена",
    btn_sponsor_open="🔗 Открыть канал",

    # ---------- ADD SPONSOR (мастер на inline) ----------
    addsp_step1=(
        "➕ <b>Новый спонсор</b>     <i>Шаг 1 из 3</i>\n"
        "━━━━━━━━━━━━━━━\n"
        "Выбери тип канала."
    ),
    addsp_step2_public=(
        "➕ <b>Новый спонсор</b>     <i>Шаг 2 из 3</i>\n"
        "━━━━━━━━━━━━━━━\n"
        "🌐 Публичный канал.\n\n"
        "Перешли любой пост из канала <b>боту</b> или пришли <code>@username</code>.\n"
        "<i>Бот должен быть админом этого канала.</i>"
    ),
    addsp_step2_private=(
        "➕ <b>Новый спонсор</b>     <i>Шаг 2 из 4</i>\n"
        "━━━━━━━━━━━━━━━\n"
        "🔒 Приватный канал.\n\n"
        "Пришли invite-ссылку: <code>https://t.me/+...</code>"
    ),
    addsp_step2b_private=(
        "➕ <b>Новый спонсор</b>     <i>Шаг 3 из 4</i>\n"
        "━━━━━━━━━━━━━━━\n"
        "🔒 Приватный канал.\n\n"
        "Теперь <b>перешли любой пост</b> из этого канала боту — "
        "чтобы получить ID и проверять подписки.\n\n"
        "<i>Бот обязан быть админом в канале.</i>"
    ),
    addsp_private_forward_invalid=(
        "⚠️ Не похоже на пост из канала. Перешли любое сообщение из приватного канала."
    ),
    addsp_step3=(
        "➕ <b>Новый спонсор</b>     <i>Шаг 3 из 3</i>\n"
        "━━━━━━━━━━━━━━━\n"
        "Пришли название канала (отобразится на кнопке)."
    ),
    addsp_step4_private=(
        "➕ <b>Новый спонсор</b>     <i>Шаг 4 из 4</i>\n"
        "━━━━━━━━━━━━━━━\n"
        "Пришли название канала (отобразится на кнопке)."
    ),
    addsp_kind_public_btn="🌐 Публичный",
    addsp_kind_private_btn="🔒 Приватный",
    addsp_chat_invalid=(
        "⚠️ Не удалось получить канал. Перешли пост из канала или пришли <code>@username</code>.\n"
        "Бот должен быть админом."
    ),
    addsp_invite_invalid="⚠️ Это не похоже на invite-ссылку. Пример: <code>https://t.me/+abc...</code>",
    addsp_bot_not_admin=(
        "⛔ Бот не админ в этом канале — он не сможет проверять подписки.\n"
        "Сделай бота администратором и попробуй снова."
    ),
    addsp_title_invalid="⚠️ Название не может быть пустым.",
    addsp_cancelled="Добавление отменено.",
    addsp_created="✅ Спонсор <b>{title}</b> добавлен.",

    # ---------- ADMIN: edit OPTIONAL sponsor ----------
    btn_sponsor_edit_reward="✏ Награда",
    btn_sponsor_edit_limit="🎚 Лимит",
    editsp_reward_prompt=(
        "✏ <b>Награда для «{title}»</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Текущая: <b>{current:.2f}⭐</b>\n\n"
        "Пришли новое число (например <code>1.5</code>).\n"
        "<i>0 — задание выключится.</i>"
    ),
    editsp_reward_invalid="⚠️ Нужно число от 0 до 1 000 000. Пример: <code>1.5</code>",
    editsp_reward_saved="✅ Награда обновлена: <b>{reward:.2f}⭐</b> ({title})",
    editsp_limit_prompt=(
        "🎚 <b>Лимит подписок для «{title}»</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Текущий: <b>{current}</b>\n\n"
        "Пришли число подписок, на котором задание авто-выключится.\n"
        "<i>0 — без лимита.</i>"
    ),
    editsp_limit_invalid="⚠️ Нужно целое неотрицательное число.",
    editsp_limit_saved="✅ Лимит обновлён: <b>{limit}</b> ({title})",

    # ---------- ADMIN: PROMOS ----------
    btn_admin_promos="🎟 Промокоды",
    btn_admin_promo_add="➕ Создать",
    btn_admin_back="◀ В админку",
    btn_admin_promo_pause="⏸ На паузу",
    btn_admin_promo_resume="▶ Активировать",
    btn_admin_promo_delete="🗑 Удалить",
    btn_admin_promo_delete_confirm="🗑 Точно удалить?",
    btn_admin_promo_delete_cancel="✕ Отмена",
    btn_admin_promo_back_list="◀ К списку",
    btn_admin_promo_add_cancel="✕ Отменить",
    btn_admin_promo_honeypot_yes="🪤 Honeypot",
    btn_admin_promo_honeypot_no="🎟 Обычный",

    admin_promos_root=(
        "🎟 <b>Промокоды</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "{count_line}"
    ),
    admin_promos_empty="Список пуст. Создай первый.",
    admin_promos_count="Всего: <b>{total}</b> · Активных: <b>{active}</b> · Ловушек: <b>{honeypots}</b>",

    admin_promo_card=(
        "🎟 <b>{code}</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Тип: {kind}\n"
        "Статус: {status}\n"
        "Награда: <b>{reward}</b>\n"
        "Активаций: {usage}\n"
        "Срок: {expires}"
    ),
    admin_promo_kind_normal="🎟 Обычный",
    admin_promo_kind_honeypot="🪤 Honeypot (бан при вводе)",
    admin_promo_status_active="✅ Активен",
    admin_promo_status_paused="⏸ На паузе",
    admin_promo_usage_unlimited="<b>{used}</b> (безлимит)",
    admin_promo_usage_limited="<b>{used}</b> / <b>{max}</b>",
    admin_promo_expires_never="без срока",
    admin_promo_deleted="🗑 Промокод удалён.",
    admin_promo_toggled_on="▶ Активирован.",
    admin_promo_toggled_off="⏸ Приостановлен.",

    # ADD PROMO wizard
    addpromo_step1=(
        "➕ <b>Новый промокод</b>     <i>Шаг 1 из 5</i>\n"
        "━━━━━━━━━━━━━━━\n"
        "Пришли код: латиница, цифры, <code>_</code>, <code>-</code>.\n"
        "<i>Будет нормализован к верхнему регистру.</i>"
    ),
    addpromo_step2=(
        "➕ <b>Новый промокод</b>     <i>Шаг 2 из 5</i>\n"
        "━━━━━━━━━━━━━━━\n"
        "Код: <code>{code}</code>\n\n"
        "Пришли награду в ⭐ (например <code>1.5</code>).\n"
        "<i>Для honeypot — поставь 0.</i>"
    ),
    addpromo_step3=(
        "➕ <b>Новый промокод</b>     <i>Шаг 3 из 5</i>\n"
        "━━━━━━━━━━━━━━━\n"
        "Сколько максимум активаций?\n"
        "<i>0 — без лимита.</i>"
    ),
    addpromo_step4=(
        "➕ <b>Новый промокод</b>     <i>Шаг 4 из 5</i>\n"
        "━━━━━━━━━━━━━━━\n"
        "Срок действия в днях.\n"
        "<i>0 — без срока.</i>"
    ),
    addpromo_step5=(
        "➕ <b>Новый промокод</b>     <i>Шаг 5 из 5</i>\n"
        "━━━━━━━━━━━━━━━\n"
        "Это <b>honeypot</b>?\n"
        "<i>Honeypot — ловушка: кто введёт, получит бан без награды.</i>"
    ),
    addpromo_code_invalid=(
        "⚠️ Неверный код. Допустимы латиница, цифры, <code>_</code>, <code>-</code>. "
        "Длина 1–64."
    ),
    addpromo_code_duplicate="⚠️ Такой код уже существует. Выбери другой.",
    addpromo_reward_invalid="⚠️ Нужно число от 0 до 1 000 000.",
    addpromo_max_invalid="⚠️ Нужно неотрицательное целое число.",
    addpromo_expires_invalid="⚠️ Нужно неотрицательное целое число дней.",
    addpromo_created="✅ Промокод <b>{code}</b> создан.",
    addpromo_created_alert="✅ Промокод создан",
    addpromo_cancelled="Создание отменено.",

    # ---------- CLICKER (user) ----------
    clicker_caption=(
        "👆  <b>КЛИКЕР</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "   {level_emoji}  <b>{level_name}</b>   ·   за тап <b>{reward_per_click}</b>\n"
        "\n"
        "❖  <b>СЕГОДНЯ</b>\n"
        "╭  Тапов           <b>{clicks}</b> / {daily_limit}\n"
        "╰  Заработано      <b>{earned_today}</b>\n"
        "     {progress_bar}\n"
        "\n"
        "   💎  Баланс      <b>{balance}</b>\n"
        "\n"
        "{cooldown_line}\n"
        "\n"
        "⟡ <i>Жми кнопку — копи звёзды. Лимит растёт с уровнем</i>"
    ),
    clicker_cooldown_line="   ⏳  Следующий тап через  <b>{left}</b>",
    clicker_ready_line="   ⚡  Можно тапать прямо сейчас",
    clicker_limit_line="   🔒  Лимит исчерпан — возвращайся завтра",
    btn_click_tap="👆  ТАП  👆",
    btn_click_cooldown="⏳  {time}",
    btn_click_limit_reached="🔒 Лимит на сегодня",
    btn_click_refresh="🔄 Обновить",
    btn_click_cancel="◀ В меню",
    clicker_tick_alert="+{reward}",
    clicker_milestone_alert="🔥 {clicks} тапов сегодня  ·  +{reward}",
    clicker_finish_alert=(
        "🏁 Дневной максимум добит!\n"
        "Сегодня с кликера: +{earned}\n"
        "Возвращайся завтра — лимит обновится."
    ),
    clicker_too_fast_alert="⏱ Рано! Следующий тап через {left}.",
    clicker_daily_limit_alert="🔒 Дневной лимит исчерпан. Возвращайся завтра.",
    clicker_captcha_required_alert="🤖 Сначала пройди мини-проверку.",
    clicker_captcha_triggered_alert="🤖 Мини-проверка — выбери лишний эмодзи.",

    # CLICKER captcha (mini)
    clicker_captcha_caption=(
        "🤖 <b>Мини-проверка</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "На подсказке:\n"
        "   <b>{hint}</b>\n"
        "\n"
        "Какой эмодзи <b>лишний</b>? Нажми его на кнопке.\n"
        "<i>После проверки можно кликать дальше.</i>"
    ),
    clicker_captcha_wrong_prefix="❌ <b>Не то.</b> Попробуй ещё раз.\n\n",
    clicker_captcha_ok_alert="✅ Готово, продолжай.",
    clicker_captcha_wrong_alert="❌ Не то — попробуй ещё.",
    clicker_captcha_expired_alert="🔄 Капча устарела — обновлено.",

    # ---------- DAILY BONUS (user) ----------
    bonus_caption=(
        "🎁  <b>ЕЖЕДНЕВНЫЙ БОНУС</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "╭  🔥  Стрик        <b>{streak} дн.</b>\n"
        "│  🎁  Сегодня     <b>{today_amount}</b>\n"
        "╰  💎  Баланс      <b>{balance}</b>\n"
        "\n"
        "❖  <b>ЛЕСЕНКА СТРИКА</b>\n"
        "{ladder}\n"
        "{next_line}\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "{bio_block}"
    ),
    bonus_ladder_done="   ✅  День {days}   ·   {amount}",
    bonus_ladder_next="   🎯  День {days}   ·   {amount}   ← цель",
    bonus_ladder_locked="   ⬜  День {days}   ·   {amount}",
    bonus_next_line="   ⬆️  Ещё <b>{days}</b> дн. подряд — бонус <b>{amount}</b>",
    bonus_next_max="   👑  Максимальная ступень стрика. Так держать!",
    bonus_bio_block=(
        "❖  <b>УСЛОВИЕ</b>\n"
        "В твоём bio должна стоять твоя реф-ссылка:\n"
        "<code>{link}</code>\n"
        "\n"
        "⟡ <i>Добавь её в профиль (Telegram → Изменить профиль → О себе)\n"
        "и нажми кнопку. Без перерывов стрик растёт — бонус больше</i>"
    ),
    bonus_bio_off="⟡ <i>Жми кнопку — забирай бонус. Заходи каждый день, чтобы рос стрик</i>",
    btn_bonus_claim="🎁  Получить бонус",
    btn_bonus_claimed="🔒 Уже получено сегодня",
    btn_bonus_refresh="🔄 Обновить",
    bonus_ok_alert="🎉 +{amount}   ·   стрик {streak} 🔥",
    bonus_already_alert="🔒 Сегодня бонус уже получен. Возвращайся завтра.",
    bonus_bio_missing_alert="📝 Не нашёл рефку в твоём bio. Добавь ссылку выше и попробуй снова.",
    bonus_unavailable_alert="⏳ Проверка временно недоступна. Попробуй чуть позже.",

    # ---------- TASKS (user) ----------
    tasks_list_caption=(
        "🎯  <b>ЗАДАНИЯ СПОНСОРОВ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Подпишись на канал — получи звёзды мгновенно.\n"
        "\n"
        "   📋  Активных заданий   <b>{active}</b>\n"
        "\n"
        "⟡ <i>Выбери задание из списка ниже</i>"
    ),
    tasks_empty=(
        "🎯  <b>ЗАДАНИЯ СПОНСОРОВ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Свободных заданий пока нет.\n"
        "\n"
        "⟡ <i>Загляни попозже — новые появляются регулярно</i>"
    ),
    tasks_disabled=(
        "🎯  <b>ЗАДАНИЯ СПОНСОРОВ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Раздел временно выключен."
    ),
    tasks_disabled_alert="🛠 Раздел временно выключен.",
    btn_tasks_refresh="🔄 Обновить",
    btn_tasks_back="◀ К списку",

    task_card=(
        "🎯  <b>{title}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "╭  💰  Награда   <b>{reward}</b>\n"
        "╰  {status_line}\n"
        "\n"
        "❖  <b>КАК ВЫПОЛНИТЬ</b>\n"
        "   <b>1</b> ›  Подпишись на канал\n"
        "   <b>2</b> ›  Вернись и жми «Проверить»\n"
        "\n"
        "⟡ <i>Отписка после — спишет награду</i>"
    ),
    task_card_pending="⏳  Статус     <b>не выполнено</b>",
    task_card_completed="✅  Статус     <b>выполнено</b>",
    btn_task_open_channel="📢 Открыть канал",
    btn_task_check="✅ Проверить",
    task_claim_ok_alert="✅ +{reward}",
    task_not_subscribed_alert="❌ Не вижу подписки. Подпишись и нажми «Проверить».",
    task_already_done_alert="✓ Уже выполнено.",
    task_limit_reached_alert="🔒 Лимит этого задания исчерпан.",
    task_not_found_alert="🚫 Задание не найдено или снято.",
    task_no_reward_alert="🛠 У этого задания не задана награда.",

    # ---------- PROMO (user) ----------
    promo_intro=(
        "🎟  <b>ПРОМОКОД</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Есть промокод? Введи — получи звёзды.\n"
        "\n"
        "⟡ <i>Длина до {max_len} символов. Каждый код — один раз на юзера. "
        "Не вводи коды из тёмных источников — могут быть ловушки</i>"
    ),
    promo_waiting=(
        "🎟  <b>ПРОМОКОД</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Пришли промокод одним сообщением.\n"
        "\n"
        "⟡ <i>Регистр не важен</i>"
    ),
    btn_promo_enter="✏ Ввести код",
    btn_promo_cancel="✕ Отменить",
    btn_promo_again="🔄 Ещё код",
    btn_promo_back_profile="◀ В профиль",
    promo_ok=(
        "✅  <b>ГОТОВО</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Промокод <code>{code}</code> применён.\n"
        "\n"
        "╭  🎁  Получено   <b>{reward}</b>\n"
        "╰  💎  Баланс     <b>{balance}</b>"
    ),
    promo_not_found=(
        "❌  <b>НЕ НАШЛИ ТАКОЙ КОД</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Проверь раскладку и попробуй ещё раз."
    ),
    promo_already_used=(
        "✓  <b>УЖЕ ИСПОЛЬЗОВАН</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Каждый промокод — один раз на юзера."
    ),
    promo_expired=(
        "⏱  <b>СРОК ИСТЁК</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Этот код больше не активен."
    ),
    promo_exhausted=(
        "🔒  <b>АКТИВАЦИИ ЗАКОНЧИЛИСЬ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Лимит активаций достигнут."
    ),
    promo_inactive=(
        "⏸  <b>КОД НЕ АКТИВЕН</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Этот код временно отключён."
    ),
    promo_too_long=(
        "⚠️  <b>СЛИШКОМ ДЛИННЫЙ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Промокод должен быть короче. Проверь ещё раз."
    ),
    promo_empty=(
        "⚠️  <b>ПУСТОЙ КОД</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Пришли непустой текст."
    ),
    promo_honeypot_banned=(
        "🚫  <b>ДОСТУП ЗАКРЫТ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Ты ввёл закрытый код, помеченный как ловушка.\n"
        "По правилам аккаунт заблокирован."
    ),

    # ---------- WHEEL (user) ----------
    wheel_caption=(
        "🎡  <b>КОЛЕСО ФОРТУНЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "╭  🎟  Бесплатное   <b>{free_state}</b>\n"
        "│  💰  Платное      <b>{cost}</b> / вращение\n"
        "╰  💎  Баланс       <b>{balance}</b>\n"
        "\n"
        "❖  <b>ПРИЗЫ</b>\n"
        "   {sectors}\n"
        "\n"
        "{result_line}\n"
        "\n"
        "⟡ <i>Одно бесплатное вращение каждый день</i>"
    ),
    wheel_free_yes="доступно ✅",
    wheel_free_no="на сегодня использовано",
    wheel_spin_frames=(
        "🎡  <b>КОЛЕСО ФОРТУНЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "        ✨  ⭐  ✨\n"
        "     🌀  <b>КРУТИМ</b>  🌀\n"
        "        ✨  ⭐  ✨\n"
        "\n"
        "<i>Разгоняем колесо…</i>",
        "🎡  <b>КОЛЕСО ФОРТУНЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "        ⭐  💫  ⭐\n"
        "     💫  <b>КРУТИМ</b>  💫\n"
        "        ⭐  💫  ⭐\n"
        "\n"
        "<i>Сектора мелькают…</i>",
        "🎡  <b>КОЛЕСО ФОРТУНЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "        💫  ✨  💫\n"
        "     ⚡  <b>КРУТИМ</b>  ⚡\n"
        "        💫  ✨  💫\n"
        "\n"
        "<i>Замедляется… момент истины…</i>",
    ),
    wheel_idle_line="   🎰  Крути — и забирай ⭐",
    wheel_win_line="   🎉  Выпало:  <b>{prize}</b>",
    wheel_empty_line="   🫥  Пусто — в другой раз повезёт",
    wheel_sectors_empty="скоро",
    btn_wheel_free="🎟 Крутить бесплатно",
    btn_wheel_paid="💰 Крутить за {cost}",
    btn_wheel_refresh="🔄 Обновить",
    wheel_win_alert="🎉 +{prize}",
    wheel_empty_alert="🫥 Пусто. В другой раз повезёт!",
    wheel_no_free_alert="🔒 Бесплатное на сегодня использовано. Доступно платное вращение.",
    wheel_not_enough_alert="💎 Не хватает звёзд на платное вращение.",
    wheel_disabled_alert="🛠 Колесо временно недоступно.",

    # ---------- ACHIEVEMENTS (user) ----------
    ach_caption=(
        "🏅  <b>ДОСТИЖЕНИЯ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "   Открыто  <b>{unlocked}</b> из <b>{total}</b>\n"
        "   {summary_bar}\n"
        "\n"
        "{rows}\n"
        "\n"
        "⟡ <i>Награда за каждое достижение — единоразово на баланс</i>"
    ),
    ach_empty=(
        "🏅  <b>ДОСТИЖЕНИЯ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Список достижений скоро появится."
    ),
    ach_row_unlocked="✅  {emoji} <b>{name}</b>  ·  +{reward}",
    ach_row_locked=(
        "🔒  {emoji} {name}  ·  +{reward}\n"
        "      {bar}  <i>{current}/{threshold} {unit}</i>"
    ),
    ach_unlocked_alert="🏅 Открыто: {names}   ·   +{total}",
    btn_ach_refresh="🔄 Обновить",
    btn_ach_back="◀ В профиль",

    # ---------- LEADERBOARD (user) ----------
    top_caption=(
        "🏆  <b>ТОП ПО РЕФЕРАЛАМ</b>  ·  <i>{period_name}</i>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "{rows}\n"
        "\n"
        "{your_line}\n"
        "\n"
        "⟡ <i>Минимум {min_confirmed} подтв. рефералов. Топ-10 недели получает награды ⭐</i>"
    ),
    top_empty=(
        "🏆  <b>ТОП ПО РЕФЕРАЛАМ</b>  ·  <i>{period_name}</i>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Пока никто не набрал <b>{min_confirmed}</b> подтв. рефералов.\n"
        "Зови друзей — и стань первым!\n"
        "\n"
        "{your_line}"
    ),
    top_row="{medal}  <b>{name}</b>  —  <b>{score}</b>",
    top_your_ranked="📍 Ты — <b>#{rank}</b>  ·  {score} подтв. реф.",
    top_your_unranked="📍 Ты пока вне топа: <b>{score}</b> / {min_confirmed} подтв. реф.",
    top_period_week="Неделя",
    top_period_month="Месяц",
    top_period_all="Всё время",
    top_disabled_alert="🛠 Топ временно недоступен.",
    btn_top_refresh="🔄 Обновить",
    btn_top_back="◀ В профиль",

    notify_top_reward=(
        "🏆 <b>Награда за топ недели</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Ты занял <b>#{rank}</b> место — начислено <b>{amount}</b>.\n"
        "Так держать!"
    ),
    log_top_payout="🏆 Топ-выплаты за {week}: награждено <b>{count}</b>",

    # ---------- PARTNER (Этап 10, юзер-сайд) ----------
    btn_profile_partner="🤝 Партнёрка",
    partner_paused_alert="⏸ Партнёрский доступ на паузе. Напиши владельцу.",
    partner_caption=(
        "🤝  <b>ПАРТНЁРСКАЯ ПАНЕЛЬ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "❖  <b>БАЛАНС</b>\n"
        "╭  💎  Доступно      <b>{balance}</b>\n"
        "╰  📈  Всего          <b>{total_earned}</b>\n"
        "\n"
        "❖  <b>ТРАФИК</b>\n"
        "╭  🔗  Ссылок        <b>{links_count}</b>\n"
        "│  👆  Переходов     <b>{clicks}</b>\n"
        "│  👥  Регистраций   <b>{joins}</b>\n"
        "╰  ✅  Прошли гейт   <b>{passed}</b>\n"
        "\n"
        "❖  <b>УСЛОВИЯ</b>\n"
        "╭  За юзера          <b>{cpa}</b>\n"
        "│  Со спонсоров      <b>{percent}%</b>\n"
        "╰  Курс выплат       <b>1⭐ = {rate}₽</b>\n"
        "\n"
        "⟡ <i>Выплата от {min_payout} на карту или ЮMoney</i>"
    ),
    btn_partner_links="🔗 Мои ссылки",
    btn_partner_sponsors="📢 Мои каналы",
    btn_partner_payout="💸 Выплата",
    btn_partner_history="📜 История выплат",
    btn_partner_back="◀ В панель",

    partner_links_caption=(
        "🔗  <b>МОИ ССЫЛКИ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "{rows}\n"
        "\n"
        "⟡ <i>До {max_links} ссылок. Жми на ссылку — детали и удаление</i>"
    ),
    partner_links_empty="Пока нет ни одной ссылки. Создай первую!",
    partner_link_row="•  <b>{title}</b>  ·  👆 {clicks}  ·  👥 {joins}  ·  ✅ {passed}",
    partner_link_card=(
        "🔗  <b>{title}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "<code>{url}</code>\n"
        "\n"
        "╭  👆  Переходов     <b>{clicks}</b>\n"
        "│  👥  Регистраций   <b>{joins}</b>\n"
        "╰  ✅  Прошли гейт   <b>{passed}</b>\n"
        "\n"
        "⟡ <i>Ссылка засчитывает юзера один раз — до прохождения гейта</i>"
    ),
    btn_partner_link_add="➕ Создать ссылку",
    btn_partner_link_del="🗑 Удалить",
    partner_link_title_prompt=(
        "🔗  <b>НОВАЯ ССЫЛКА</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "<b>1</b> ›  Пришли название (до 64 символов).\n"
        "\n"
        "⟡ <i>Например: «Тикток-кампания» или «Чат N»</i>"
    ),
    partner_link_created_alert="✅ Ссылка создана",
    partner_link_limit_alert="🔒 Лимит ссылок: {max_links}.",
    partner_link_deleted_alert="🗑 Ссылка удалена",

    partner_sponsors_caption=(
        "📢  <b>МОИ КАНАЛЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "{rows}\n"
        "\n"
        "⟡ <i>Канал попадает в «Задания» после проверки владельцем</i>"
    ),
    partner_sponsors_empty="Каналов пока нет. Добавь свой первый!",
    partner_sponsor_row="{status}  <b>{title}</b>  ·  {reward} / подписка",
    partner_sponsor_status_active="✅",
    partner_sponsor_status_pending="🕓",
    partner_sponsor_status_paused="⏸",
    btn_partner_sponsor_add="➕ Добавить канал",
    partner_sponsor_prompt=(
        "📢  <b>НОВЫЙ КАНАЛ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "<b>1</b> ›  Добавь бота админом в свой канал.\n"
        "<b>2</b> ›  Пришли @username канала.\n"
        "\n"
        "⟡ <i>Без прав админа бот не сможет проверять подписки</i>"
    ),
    partner_sponsor_invalid="⚠️ Не вижу такой канал или бот в нём не админ. Проверь и пришли ещё раз.",
    partner_sponsor_exists="⚠️ Этот канал уже добавлен.",
    partner_sponsor_created=(
        "✅  <b>КАНАЛ ОТПРАВЛЕН НА ПРОВЕРКУ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "«{title}» появится в заданиях после активации владельцем."
    ),

    partner_payout_intro=(
        "💸  <b>ЗАЯВКА НА ВЫПЛАТУ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "╭  💎  К выплате     <b>{balance}</b>\n"
        "╰  💱  По курсу      <b>{rub}₽</b>  ·  1⭐ = {rate}₽\n"
        "\n"
        "Выбери способ получения."
    ),
    btn_payout_card="💳 Карта",
    btn_payout_yoomoney="🟣 ЮMoney",
    partner_payout_requisites_prompt=(
        "💸  <b>РЕКВИЗИТЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "<b>1</b> ›  Пришли {what}.\n"
        "\n"
        "⟡ <i>Сумма {amount} будет зарезервирована до обработки</i>"
    ),
    partner_payout_what_card="номер карты",
    partner_payout_what_yoomoney="номер кошелька ЮMoney",
    partner_payout_created=(
        "✅  <b>ЗАЯВКА ПРИНЯТА</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "╭  💎  Сумма         <b>{amount}</b>\n"
        "╰  💱  К получению   <b>{rub}₽</b>\n"
        "\n"
        "⟡ <i>Владелец обработает заявку вручную — придёт уведомление</i>"
    ),
    partner_payout_too_small_alert="💎 Минимум для выплаты — {min_amount}. Копим дальше!",
    partner_payout_pending_alert="🕓 У тебя уже есть заявка в обработке.",
    partner_payout_not_active_alert="⏸ Партнёрский доступ на паузе.",
    partner_history_caption=(
        "📜  <b>ИСТОРИЯ ВЫПЛАТ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "{rows}"
    ),
    partner_history_empty="Выплат пока не было.",
    partner_history_row="{status}  <b>{stars}</b> → {rub}₽  ·  <i>{date}</i>",
    payout_status_pending="🕓",
    payout_status_paid="✅",
    payout_status_rejected="❌",

    notify_partner_assigned=(
        "🤝  <b>ТЫ ТЕПЕРЬ ПАРТНЁР</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "\n"
        "В Профиле появилась кнопка «🤝 Партнёрка»: ссылки, статистика и выплаты."
    ),
    notify_payout_paid=(
        "✅  <b>ВЫПЛАТА ОТПРАВЛЕНА</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "\n"
        "<b>{stars}</b> → <b>{rub}₽</b> ушли на твои реквизиты."
    ),
    notify_payout_rejected=(
        "❌  <b>ЗАЯВКА ОТКЛОНЕНА</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "\n"
        "Звёзды ({stars}) вернулись на партнёрский баланс.{note_part}"
    ),
    notify_payout_note_part="\nКомментарий: <i>{note}</i>",

    # ---------- PARTNER (Этап 10, админка) ----------
    btn_admin_partners="🤝 Партнёры",
    admin_pa_root=(
        "🤝  <b>ПАРТНЁРЫ</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Активных: <b>{active}</b>  ·  Заявок на выплату: <b>{pending}</b>\n"
        "\n"
        "Выбери партнёра или назначь нового."
    ),
    admin_pa_row="{status} {name}  ·  💎 {balance}",
    btn_admin_pa_add="➕ Назначить",
    btn_admin_pa_payouts="💸 Заявки ({pending})",
    admin_pa_add_prompt=(
        "➕  <b>НОВЫЙ ПАРТНЁР</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Пришли <code>tg_id</code> или @username юзера."
    ),
    admin_pa_user_not_found="🚫 Юзер не найден. Он должен хотя бы раз запустить бота.",
    admin_pa_assigned="✅ Партнёр назначен: {name}",
    admin_pa_card=(
        "🤝  <b>ПАРТНЁР #{id}</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Юзер: {user_info}\n"
        "Статус: {status}\n"
        "\n"
        "╭  💎  Баланс        <b>{balance}</b>\n"
        "╰  📈  Всего          <b>{total_earned}</b>\n"
        "\n"
        "╭  🔗  Ссылок        <b>{links_count}</b>\n"
        "│  👆  Переходов     <b>{clicks}</b>\n"
        "│  👥  Регистраций   <b>{joins}</b>\n"
        "╰  ✅  Прошли гейт   <b>{passed}</b>\n"
        "\n"
        "╭  За юзера          <b>{cpa}</b>{cpa_mark}\n"
        "╰  Со спонсоров      <b>{percent}%</b>{percent_mark}"
    ),
    admin_pa_custom_mark="  ·  <i>персонально</i>",
    btn_admin_pa_pause="⏸ На паузу",
    btn_admin_pa_activate="▶ Активировать",
    btn_admin_pa_cpa="✏ CPA",
    btn_admin_pa_percent="✏ Процент",
    admin_pa_cpa_prompt=(
        "✏  <b>CPA ПАРТНЁРА</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Сейчас: <b>{current}</b>{mark}\n"
        "Пришли новую ставку в ⭐ (например <code>1.5</code>) или <code>-</code> — вернуть дефолт."
    ),
    admin_pa_percent_prompt=(
        "✏  <b>ПРОЦЕНТ СО СПОНСОРОВ</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Сейчас: <b>{current}%</b>{mark}\n"
        "Пришли новый % (например <code>40</code>) или <code>-</code> — вернуть дефолт."
    ),
    admin_pa_rate_invalid="⚠️ Нужно число (или «-» для сброса).",
    admin_pa_rate_saved="✅ Сохранено.",
    admin_pa_payouts_caption=(
        "💸  <b>ЗАЯВКИ НА ВЫПЛАТУ</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "\n"
        "{rows}"
    ),
    admin_pa_payouts_empty="Очередь пуста.",
    admin_pa_payout_row="#{id}  ·  {name}  ·  {stars} → {rub}₽",
    admin_pa_payout_card=(
        "💸  <b>ЗАЯВКА #{id}</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Партнёр: {user_info}\n"
        "Сумма: <b>{stars}</b> → <b>{rub}₽</b>  ·  курс {rate}\n"
        "Способ: <b>{method}</b>\n"
        "Реквизиты: <code>{requisites}</code>\n"
        "Создана: <i>{date}</i>"
    ),
    btn_admin_pa_paid="✅ Выплачено",
    btn_admin_pa_reject="❌ Отклонить",
    admin_pa_payout_done_alert="✅ Помечено выплаченным",
    admin_pa_payout_rejected_alert="❌ Отклонено, звёзды возвращены",
    admin_pa_payout_gone_alert="⚠️ Заявка уже обработана.",
    payout_method_card="Карта",
    payout_method_yoomoney="ЮMoney",
    log_partner_payout_requested="💸 Партнёрская заявка #{id}: {name} · {stars} → {rub}₽",

    # ---------- SUPPORT (Этап 11, админка) ----------
    btn_admin_support="💬 Поддержка",
    admin_sup_root=(
        "💬  <b>ПОДДЕРЖКА</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "🔴 Новых: <b>{new}</b>  ·  🟠 Дописали: <b>{in_progress}</b>\n"
        "🟢 Ждут юзера: <b>{awaiting}</b>  ·  ✔️ Закрыто: <b>{closed}</b>\n"
        "\n"
        "{hint}"
    ),
    admin_sup_root_hint="Выбери тикет — переписка и ответ.",
    admin_sup_root_empty="Открытых тикетов нет. Тишина и покой.",
    admin_sup_row="{status} #{id} · {user} · {subject}",
    btn_admin_sup_archive="🗂 Архив",
    btn_admin_sup_open="📥 Открытые",
    admin_sup_archive_caption=(
        "🗂  <b>АРХИВ ПОДДЕРЖКИ</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "\n"
        "{hint}"
    ),
    admin_sup_archive_empty="Закрытых тикетов пока нет.",
    admin_sup_card=(
        "💬  <b>ТИКЕТ #{id}</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Юзер: {user_info}\n"
        "Статус: <b>{status}</b>\n"
        "Создан: <i>{created}</i>\n"
        "\n"
        "❖  <b>ПЕРЕПИСКА</b>\n"
        "\n"
        "{thread}"
    ),
    # статусы глазами админа
    admin_sup_status_new="🔴 Новый",
    admin_sup_status_in_progress="🟠 Юзер дописал",
    admin_sup_status_awaiting="🟢 Ждёт юзера",
    admin_sup_status_closed="✔️ Закрыт",
    btn_admin_sup_reply="✍️ Ответить",
    btn_admin_sup_close="✔️ Закрыть",
    admin_sup_reply_prompt=(
        "✍️  <b>ОТВЕТ В ТИКЕТ #{id}</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "Пришли текст — юзер получит его в личку."
    ),
    admin_sup_reply_sent="✅ Ответ отправлен юзеру.",
    admin_sup_closed_alert="✔️ Тикет закрыт",
    admin_sup_not_found_alert="⚠️ Тикет не найден.",
    admin_sup_already_closed_alert="⚠️ Тикет уже закрыт.",

    # ---------- Этап 13: бэкапы, дайджест, алерты ----------
    log_backup_caption="🗄 Бэкап БД · {stamp} МСК · {size_kb} КБ",
    log_daily_digest=(
        "📊 <b>Дайджест за сутки</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "👥 Юзеров: <b>{users_total}</b> (+{users_new_today} сегодня, прошли гейт {users_passed})\n"
        "💎 Обязательства: <b>{balance_total}⭐</b> · долги {debt_total}⭐\n"
        "━━━━━━━━━━━━━━━\n"
        "Сегодня (МСК): 👆 {clicks_today} тапов · 🎁 {bonuses_today} бонусов · "
        "🎡 {spins_today} спинов\n"
        "🎯 {tasks_today} заданий · 👥 {refs_today} рефералов · 💝 {reviews_pending} отзывов в очереди"
    ),
    log_worker_error="⚠️ Воркер <code>{job_id}</code> упал: {error}",
)
