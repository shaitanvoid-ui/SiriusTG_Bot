from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from utils.keyboards import SiriusKeyboardBuilder as InlineKeyboardBuilder

from db.models import Sponsor, SponsorKind
from locales.ru import T
from services.sponsor import SponsorService
from utils.ui import button_text


# ---------- root ----------

def kb_admin_root() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_admin_dash, callback_data="adm:dash")
    b.button(text=T.btn_admin_system, callback_data="adm:sys")
    b.button(text=T.btn_admin_users, callback_data="adm:usr")
    b.button(text=T.btn_admin_economy, callback_data="adm:eco")
    b.button(text=T.btn_admin_gifts, callback_data="adm:gift:open")
    b.button(text=T.btn_admin_sponsors, callback_data="adm:sponsors:list")
    b.button(text=T.btn_admin_promos, callback_data="adm:promo:list")
    b.button(text=T.btn_admin_reviews, callback_data="adm:rev:list")
    b.button(text=T.btn_admin_stop_words, callback_data="adm:sw")
    b.button(text=T.btn_admin_instructions, callback_data="adm:ins:list")
    b.button(text=T.btn_admin_channel, callback_data="adm:ch")
    b.button(text=T.btn_admin_broadcast, callback_data="adm:bc")
    b.button(text=T.btn_admin_support, callback_data="adm:sup")
    b.button(text=T.btn_admin_partners, callback_data="adm:pa")
    b.button(text=T.btn_back_menu, callback_data="nav:menu")
    b.adjust(2, 2, 1, 2, 2, 2, 1, 2, 1)
    return b.as_markup()


# ---------- sponsors list ----------

def _sponsor_row_text(s: Sponsor) -> str:
    status = "✅" if s.is_active else "⏸"
    kind = "🔒" if s.kind == SponsorKind.PRIVATE.value else "🌐"
    req = "🔴" if s.is_required else "🟢"
    return button_text(f"{status}{kind}{req} {s.title}")


def kb_sponsors_list(sponsors: list[Sponsor], limit: int = 25) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in sponsors[:limit]:
        b.button(text=_sponsor_row_text(s), callback_data=f"adm:sp:open:{s.id}")
    b.button(text="＋ Добавить спонсора", callback_data="adm:sp:add")
    b.button(text=T.btn_back_admin, callback_data="adm:root")
    rows_count = min(len(sponsors), limit)
    b.adjust(*([1] * rows_count), 2)
    return b.as_markup()


# ---------- sponsor card ----------

def kb_sponsor_card(s: Sponsor) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    url = SponsorService.display_link(s)
    if url:
        b.button(text=T.btn_sponsor_open, url=url)
    toggle_active = "⏸ На паузу" if s.is_active else "▶ Активировать"
    b.button(text=toggle_active, callback_data=f"adm:sp:toggle_active:{s.id}")
    toggle_req = "🟢 Сделать опц." if s.is_required else "🔴 Сделать обяз."
    b.button(text=toggle_req, callback_data=f"adm:sp:toggle_req:{s.id}")

    edit_rows = 0
    if not s.is_required:
        b.button(text=T.btn_sponsor_edit_reward, callback_data=f"adm:sp:edit_rw:{s.id}")
        b.button(text=T.btn_sponsor_edit_limit, callback_data=f"adm:sp:edit_lm:{s.id}")
        edit_rows = 1

    b.button(text=T.btn_sponsor_delete, callback_data=f"adm:sp:del_ask:{s.id}")
    b.button(text="‹ К списку", callback_data="adm:sponsors:list")

    rows: list[int] = []
    if url:
        rows.append(1)
    rows.append(2)
    if edit_rows:
        rows.append(2)
    rows.extend([1, 1])
    b.adjust(*rows)
    return b.as_markup()


def kb_sponsor_delete_confirm(sponsor_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=T.btn_sponsor_delete_confirm,
                    callback_data=f"adm:sp:del_yes:{sponsor_id}",
                ),
                InlineKeyboardButton(
                    text=T.btn_sponsor_delete_cancel,
                    callback_data=f"adm:sp:open:{sponsor_id}",
                ),
            ]
        ]
    )


# ---------- add wizard ----------

def kb_add_kind() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=T.addsp_kind_public_btn, callback_data="adm:sp:add_kind:public"),
                InlineKeyboardButton(text=T.addsp_kind_private_btn, callback_data="adm:sp:add_kind:private"),
            ],
            [InlineKeyboardButton(text=T.btn_cancel, callback_data="adm:sp:add_cancel")],
        ]
    )


def kb_add_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=T.btn_cancel, callback_data="adm:sp:add_cancel")]]
    )
