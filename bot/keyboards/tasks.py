from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from utils.keyboards import SiriusKeyboardBuilder as InlineKeyboardBuilder

from locales.ru import T
from services.tasks import TaskItem
from utils.ui import button_text, stars


def kb_tasks_list(items: list[TaskItem], *, limit: int = 25) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    shown = items[:limit]
    for it in shown:
        title = button_text(it.sponsor.title, limit=28)
        if it.is_completed:
            label = f"✅  {title}"
        else:
            label = f"🎯  {title}  ·  +{stars(it.sponsor.reward)}"
        b.button(text=label, callback_data=f"tsk:open:{it.sponsor.id}")
    b.button(text=T.btn_tasks_refresh, callback_data="tsk:list")
    b.footer(text=T.btn_back_earn, callback_data="sec:earn")
    b.adjust(*([1] * len(shown)), 1, 2)
    return b.as_markup()


def kb_task_card(
    sponsor_id: int,
    open_url: str | None,
    *,
    is_completed: bool,
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if open_url:
        b.button(text=T.btn_task_open_channel, url=open_url)
    if not is_completed:
        b.button(text=T.btn_task_check, callback_data=f"tsk:claim:{sponsor_id}")
    b.footer(text=T.btn_tasks_back, callback_data="tsk:list")
    if open_url and not is_completed:
        b.adjust(1, 1, 1)
    elif open_url or not is_completed:
        b.adjust(1, 1)
    else:
        b.adjust(1)
    return b.as_markup()
