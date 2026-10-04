"""Export actual bot templates and keyboards for offline visual QA.

This is a reference rendering, not a Telegram client emulator. All data is synthetic.
Run inside the test image with an output directory mounted at /preview.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
import sys
from datetime import datetime, timezone
from types import SimpleNamespace

from bot.handlers.bonus import _render as render_bonus
from bot.keyboards.bonus import kb_bonus
from bot.keyboards.clicker import kb_clicker
from bot.keyboards.wheel import kb_wheel
from bot.keyboards.tasks import kb_task_card
from bot.keyboards.achievements import kb_achievements
from bot.keyboards.support import kb_support_home, kb_ticket_card
from bot.keyboards.admin_panel import kb_dash
from bot.keyboards.daily import kb_daily
from bot.keyboards.main_menu import kb_main_menu
from bot.keyboards.referral import kb_referral
from bot.handlers.gifts import render_gift, render_request
from bot.keyboards.gifts import kb_catalogue, kb_confirmation, kb_gift, kb_request, kb_admin_gifts, kb_gift_notification
from bot.keyboards.sections import kb_profile
from locales.ru import T
from services.bonus import BonusView
from services.dashboard import DailyAction
from utils.rich import render_rich_html
from utils.ui import brand_header, progress_bar, stars


CSS = """
*{box-sizing:border-box}body{margin:0;background:#0b101a;color:#eaf1fb;font:14px/1.5 'Segoe UI',Arial,sans-serif}
header{max-width:1560px;margin:0 auto;padding:44px 34px 22px}.eyebrow{color:#a8b7d0;font-size:11px;letter-spacing:3px;text-transform:uppercase}
header h1{font-size:38px;font-weight:600;letter-spacing:-1.4px;margin:12px 0 6px}header p{color:#9aa9bf;max-width:750px;margin:0}
.gallery{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:22px;max-width:1560px;margin:0 auto;padding:22px 34px 40px}
.phone{border:1px solid #303b4c;border-radius:30px;background:#151e2c;overflow:hidden;box-shadow:0 22px 60px #0004;min-width:0}
.status{padding:10px 20px 2px;font-size:11px;color:#b4c2d7;display:flex;justify-content:space-between}
.appbar{display:flex;gap:10px;align-items:center;padding:13px 16px;border-bottom:1px solid #ffffff0a;background:#172230}
.avatar{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:#a8c5ea22;color:#d5e4fa;font-size:25px}.appbar strong{display:block;letter-spacing:1px;font-size:13px}.appbar small{color:#8fa3ba;font-size:11px}
.screen{height:700px;overflow:auto;padding:14px 10px 20px;background:radial-gradient(ellipse at 10% 20%,#26334470,transparent 65%),#101922;scrollbar-width:thin;scrollbar-color:#334456 transparent}
.date{font-size:10px;background:#ffffff08;border-radius:14px;padding:3px 10px;margin:0 auto 14px;width:max-content;color:#a1b0c0}
.bubble{background:#1c2b3a;border-radius:16px 16px 16px 5px;padding:16px 15px 11px;overflow-wrap:anywhere;font-size:13px;line-height:1.5}
h2{font-size:17px;line-height:1.3;margin:0 0 14px;font-weight:600;letter-spacing:-.3px}h3{font-size:13px;margin:18px 0 8px;color:#dce7f4;font-weight:600}h2 b,h3 b{font-weight:600}
p{margin:10px 0}b{font-weight:600}i{font-style:normal;color:#a5b7ca}footer{display:block;color:#90a7bc;font-size:11px;margin-top:16px;line-height:1.5}
table{border-collapse:collapse;width:100%;margin:13px 0;border:1px solid #ffffff0d;border-radius:10px}td{padding:9px 8px;border-bottom:1px solid #ffffff0a;font-size:12px;vertical-align:middle}td:first-child{color:#9fb2c6}td:last-child{text-align:right;color:#f0f5fc}
code{font-family:Consolas,monospace;background:#ffffff08;color:#accef3;border-radius:4px;font-size:11px;padding:2px 4px}details{border-left:3px solid #77b2e2;padding:8px 11px;background:#142431;border-radius:5px;margin:16px 0;font-size:12px}summary{cursor:pointer;color:#c4d8eb;font-weight:600}details p{color:#aebfd1;margin:8px 0 2px}
.time{text-align:right;font-size:9px;color:#7e97ad;margin-top:8px}.keys{margin-top:5px;display:flex;flex-direction:column;gap:5px}.row{display:flex;gap:5px}.row button{flex:1;min-width:0;border:0;border-radius:8px;padding:11px 5px;background:#ffffff0b;color:#dce8f6;font:600 11px/1.3 'Segoe UI',Arial,sans-serif;cursor:pointer;white-space:normal}
.row button.primary{background:#315985}.row button.success{background:#297855}.row button.danger{background:#974949}.row button:disabled{background:#ffffff05;color:#61778b;cursor:default}.row button.copied{background:#297855}
.label{text-align:center;padding:16px 10px 18px;font-size:11px;color:#9badc4;letter-spacing:.6px}.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:#28435a;border:1px solid #80a7cd55;border-radius:12px;padding:12px 20px;box-shadow:0 8px 40px #0006;display:none;color:#e4f0fc;max-width:90%;z-index:10}
@media(max-width:1200px){.gallery{grid-template-columns:repeat(2,minmax(0,1fr));max-width:860px}.screen{height:710px}}
@media(max-width:540px){header{padding:28px 18px 8px}header h1{font-size:30px}.gallery{grid-template-columns:1fr;padding:16px 18px 28px;max-width:420px}.screen{height:700px}.phone{border-radius:25px}}
"""


def keyboard_html(markup) -> str:
    rows = []
    for row in markup.inline_keyboard:
        buttons = []
        for button in row:
            clipboard = escape(button.copy_text.text, quote=True) if button.copy_text else ""
            buttons.append(f'<button class="{button.style or ""}" data-copy="{clipboard}" '
                           f'{"disabled" if button.disabled is not None else ""}>{escape(button.text)}</button>')
        rows.append('<div class="row">' + ''.join(buttons) + '</div>')
    return '<div class="keys">' + ''.join(rows) + '</div>'


def build_screens() -> list[tuple[str, str, object]]:
    """Build synthetic examples through the application's templates and renderers."""
    link = "https://t.me/sirius_demo_bot?start=r42"
    home = T.menu_caption.format(brand=brand_header("SIRIUS", "Награды в Telegram"), greeting=T.greeting_evening,
        name="Анна", balance=stars(28.4), level_emoji="🥈", level_name="Серебро", confirmed_refs=8,
        progress_bar=progress_bar(3,10), progress_text=T.menu_progress_to_next.format(next_name="Золото", to_next_text="7 друзей"),
        ref_reward=stars(3), today_action=T.daily_bonus_label, today_hint="До 1 ед. · условия на карточке бонуса")
    bonus = render_bonus(BonusView(streak=7, today_amount=1.0, claimed_today=True, balance=29.4, bio_required=True,
                                  next_threshold=14, next_amount=1.5), link=link, tiers={1:0.5,3:0.7,7:1.0,14:1.5,30:2.0})
    actions = (DailyAction(T.daily_bonus_label,"bns:open",T.daily_done,True),
               DailyAction(T.daily_wheel_label,"whl:open",T.daily_wheel_available),
               DailyAction(T.daily_clicker_label,"clk:open",T.daily_clicks.format(current=12, total=55) + T.daily_cooldown.format(minutes=4),False,False),
               DailyAction(T.daily_tasks_label,"tsk:list","Доступно заданий: 3"),
               DailyAction(T.daily_team_label,"ref:open",T.daily_team_hint))
    rows = "\n\n".join(T.daily_action_row.format(marker="✓" if a.complete else "○",label=a.label,detail=a.detail) for a in actions)
    daily = T.daily_caption.format(rows=rows, reset="00:00",reset_unix=1790888400)
    referral = T.referral_caption.format(reward=stars(3),link=link,total=12,confirmed=8,matured=5,earned=stars(24),
                                          debt_part="",maturation_text="7 дней",limit_part=T.referral_no_limit)
    profile = T.profile_caption.format(name="Анна", username_line=T.profile_username_line.format(username="anna_demo"),
        tg_id=42, balance=stars(28.4), debt_part=T.profile_reserved_part.format(reserved=stars(15)) + "\n\n" + T.profile_balance_note,
        level_emoji="🥈", level_name="Серебро", progress_bar=progress_bar(3, 10),
        progress_text=T.menu_progress_to_next.format(next_name="Золото", to_next_text="7 друзей"),
        ref_total=12, ref_confirmed=8, ref_matured=5, join_date="01.10.2026", streak=7)
    gift = SimpleNamespace(id=1, title="💝 Сердце с лентой", stars=15, available=True, kind="ordinary", reason=None,
        limited=False, availability_remains=None, requires_premium=False)
    catalogue_gifts = [gift, SimpleNamespace(id=2, title="🧸 Мишка", stars=15),
        SimpleNamespace(id=3, title="🎁 Подарочная коробка", stars=25),
        SimpleNamespace(id=4, title="💍 Кольцо", stars=100)]
    request = SimpleNamespace(id=42, title=gift.title, stars=15, cost_units=150000, status="waiting_funds",
        reserve_state="held", created_at=datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc),
        confirmation_kind=None, error_code="budget")
    clicker = T.clicker_caption.format(level_emoji="🥈", level_name="Серебро", reward_per_click=stars(0.1),
        clicks=12, daily_limit=55, earned_today=stars(1.2), balance=stars(28.4),
        progress_bar=progress_bar(12,55), cooldown_line=T.clicker_cooldown_line.format(left="4:00"))
    wheel = T.wheel_caption.format(free_state=T.wheel_free_yes, cost=stars(1), balance=stars(28.4),
        sectors="0 ед. · 0,5 ед. · 1 ед. · 3 ед.", result_line=T.wheel_idle_line)
    task = T.task_card.format(title="Канал о книгах", reward=stars(2), status_line=T.task_card_pending)
    achievement_rows = T.ach_row_unlocked.format(emoji="", name="Первый бонус", reward=stars(1)) + "\n\n" + T.ach_row_locked.format(
        emoji="", name="Команда из 10 друзей", reward=stars(3), bar=progress_bar(8,10), current=8, threshold=10, unit="друзей")
    achievements = T.ach_caption.format(unlocked=3, total=8, summary_bar=progress_bar(3,8), rows=achievement_rows)
    ticket = SimpleNamespace(id=42, status="awaiting", subject="Вопрос о подарке")
    thread = T.support_thread_user_line.format(text="Как проверить статус заявки?") + "\n\n" + T.support_thread_admin_line.format(
        text="Открой «Подарки» → «Мои заявки». Если отправка ожидает бюджет, резерв остаётся на счёте.")
    support_ticket = T.support_ticket_card.format(id=ticket.id, status=T.support_status_awaiting, created="03.10.2026 15:00", thread=thread)
    account = T.admin_gift_account.format(status=T.admin_gift_account_ready, stars=4, spent=0, limit=0,
        detail="Оплата выключена. Назначь бюджет и включи выдачу после проверки аккаунта.")
    reconciliation = SimpleNamespace(**vars(request))
    reconciliation.status = "reconciliation_required"
    reconciliation.error_code = "payment_unknown"
    screens = [
        ("Главная · персональный следующий шаг", home, kb_main_menu(next_label=T.daily_bonus_label,next_callback="bns:open")),
        ("Мой день · доступность в реальном времени", daily, kb_daily(actions)),
        ("Награда дня · серия и раскрывающиеся условия", bonus, kb_bonus(can_claim=False)),
        ("Команда · копирование одним нажатием", referral, kb_referral(share_url="https://t.me/share/url?url=demo",invite_link=link)),
        ("Профиль · баланс и резерв", profile, kb_profile(is_partner=False)),
        ("Каталог · узнаваемые обычные подарки", T.gift_catalogue.format(rows=T.gift_catalogue_summary.format(count=4)), kb_catalogue(catalogue_gifts)),
        ("Подарок · цена и условия", render_gift(gift, conditions={"minimum_units":150000, "min_refs":5, "daily_limit":5}), kb_gift(1, available=True)),
        ("Подтверждение · понятная сумма", T.gift_confirmation.format(title=gift.title, stars=15, cost=stars(15)), kb_confirmation("preview-only", cost=stars(15))),
        ("Уведомление · переход к заявке", T.gift_notification.format(title=gift.title, request_id=42, status=T.gift_status_succeeded), kb_gift_notification(42)),
        ("Заявка · честный статус ожидания", render_request(request), kb_request(request)),
        ("Владелец · очередь подарков", T.admin_gift_root, kb_admin_gifts()),
        ("Кликер · таймер и лимит", clicker, kb_clicker(can_click=True, cooldown_ms_left=240000)),
        ("Колесо · сумма и случайный приз", wheel, kb_wheel(free_available=True, can_pay=True, cost=1)),
        ("Задание · награда и проверка подписки", task, kb_task_card(3,"https://t.me/demo_books",is_completed=False)),
        ("Достижения · получено и прогресс", achievements, kb_achievements()),
        ("Поддержка · вход в переписку", T.support_home, kb_support_home()),
        ("Обращение · сохранённая переписка", support_ticket, kb_ticket_card(ticket)),
        ("Владелец · Stars и бюджет", account, kb_dash("adm:gift:account")),
        ("Заявка · результат на сверке", render_request(reconciliation), kb_request(reconciliation)),
    ]
    return screens


def export(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    screens = build_screens()
    phones = []
    for label, text, markup in screens:
        body = render_rich_html(text)
        phones.append('<article class="phone"><div class="status"><span>20:14</span><span>▂▄▆ · 87%</span></div>'
            '<div class="appbar"><div class="avatar">✦</div><div><strong>SIRIUS</strong><small>бот</small></div></div>'
            '<div class="screen"><div class="date">Сегодня</div><div class="bubble">' + body +
            '<div class="time">20:14</div></div>' + keyboard_html(markup) + '</div><div class="label">' + escape(label) + '</div></article>')
    script = """document.querySelectorAll('.row button').forEach(b=>b.addEventListener('click',async()=>{let t=document.querySelector('.toast');if(b.dataset.copy){try{await navigator.clipboard.writeText(b.dataset.copy);t.textContent='Ссылка скопирована';}catch{t.textContent=b.dataset.copy;}}else{t.textContent='Демонстрационный экран: переходы проверены отдельно через Dispatcher';}t.style.display='block';setTimeout(()=>t.style.display='none',2800);}));"""
    page = '<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SIRIUS · Предпросмотр</title><style>'+CSS+'</style><body><header><div class="eyebrow">Sirius / Native Telegram / 2026</div><h1>SIRIUS · нативные экраны</h1><p>Предпросмотр настоящих шаблонов и клавиатур бота с демонстрационными данными. Это макет рендера: оформление в Telegram зависит от клиента и выбранной темы.</p></header><main class="gallery">'+''.join(phones)+'</main><div class="toast" role="status"></div><script>'+script+'</script></body></html>'
    (folder / "index.html").write_text(page,encoding="utf-8")
    print(f"Exported {len(screens)} screens to {folder / 'index.html'}")


if __name__ == "__main__":
    export(Path(sys.argv[1]))
