"""Persistent conservative rule scoring and a sliding-window action limit.

All operations use server-resolved users and marked DB entities. The middleware
owns a short transaction and commits before dispatching any Telegram handler.
Domain callers retain ownership of their reward transaction.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update, func
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings as app_settings
from db.antifraud_models import AntifraudEvent, AntifraudRateState, AntifraudSnapshot
from db.base import utcnow
from db.models import Promo, PromoActivation, Sponsor, User
from ml.risk import RiskResult, regular_click_pattern, score_rules
from services.settings import DEFAULTS, SettingsService


@dataclass(frozen=True)
class ActionAdmission:
    allowed: bool
    retry_seconds: int = 0
    first_notice: bool = False


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class AntifraudService:
    def __init__(self, session: AsyncSession, settings: SettingsService | None = None):
        self.session = session
        self.settings = settings or SettingsService(session)

    async def _policy(self):
        return await self.settings.get_many({
            key: value for key, (value, _) in DEFAULTS.items() if key.startswith("antifraud.")
        })

    async def _lock_snapshot(self, user_id: int, now: datetime) -> AntifraudSnapshot:
        await self.session.execute(insert(AntifraudSnapshot).values(
            user_id=user_id, score=0, reasons_json="[]", strong_signals_json="[]",
            generation=0, evaluated_at=now,
        ).on_conflict_do_nothing(index_elements=["user_id"]))
        await self.session.execute(update(AntifraudSnapshot).where(
            AntifraudSnapshot.user_id == user_id,
        ).values(score=AntifraudSnapshot.score).execution_options(synchronize_session=False))
        return await self.session.get(AntifraudSnapshot, user_id, populate_existing=True)

    async def observe(self, *, actor_tg_id: int, click: bool = False, now: datetime | None = None) -> ActionAdmission:
        """First statement is a write, so parallel processes cannot overspend the limit."""
        now = _aware(now or utcnow())
        stamp = int(now.timestamp() * 1000)
        await self.session.execute(insert(AntifraudRateState).values(
            tg_id=actor_tg_id, accepted_times_json="[]", click_times_json="[]", updated_at=now,
        ).on_conflict_do_update(index_elements=["tg_id"], set_={"updated_at": now}))
        policy = await self._policy()
        if not policy["antifraud.enabled"]:
            return ActionAdmission(True)
        row = await self.session.get(AntifraudRateState, actor_tg_id, populate_existing=True)
        try:
            accepted = json.loads(row.accepted_times_json)
            clicks = json.loads(row.click_times_json)
            if not all(isinstance(value, int) and not isinstance(value, bool) for value in accepted + clicks):
                raise ValueError("invalid persisted action timestamps")
        except (ValueError, TypeError):
            # Corrupt safety state is never treated as a fresh allowance.
            return ActionAdmission(False, int(policy["antifraud.window_seconds"]))
        window_ms = int(policy["antifraud.window_seconds"]) * 1000
        accepted = [value for value in accepted if value > stamp - window_ms]
        clicks = [value for value in clicks if value > stamp - int(policy["antifraud.pattern_window_seconds"]) * 1000]
        first_notice = False
        allowed = len(accepted) < int(policy["antifraud.actions_per_minute"])
        if allowed:
            accepted.append(stamp)
            if click:
                clicks.append(stamp)
        else:
            result = await self.session.execute(insert(AntifraudEvent).values(
                tg_id=actor_tg_id, kind="rate_limit", created_at=now,
                source_key=f"rate:{actor_tg_id}:{accepted[0]}",
                details_json=json.dumps({"window_seconds": window_ms // 1000, "limit": policy["antifraud.actions_per_minute"]}),
            ).on_conflict_do_nothing(index_elements=["source_key"]).returning(AntifraudEvent.id))
            first_notice = result.scalar_one_or_none() is not None
        row.accepted_times_json = json.dumps(accepted)
        row.click_times_json = json.dumps(clicks[-int(policy["antifraud.pattern_samples"]):])
        await self.session.flush()
        user = await self.session.scalar(select(User).where(User.tg_id == actor_tg_id))
        if user is not None:
            snapshot = await self._lock_snapshot(user.id, now)
            await self._evaluate(user, snapshot, policy, now, clicks)
        retry = max(1, math.ceil((accepted[0] + window_ms - stamp) / 1000)) if not allowed else 0
        return ActionAdmission(allowed, retry, first_notice)

    async def _evaluate(self, user: User, snapshot: AntifraudSnapshot, policy, now: datetime, clicks=()) -> RiskResult:
        since = now - timedelta(hours=int(policy["antifraud.evidence_hours"]))
        if snapshot.reset_at is not None:
            since = max(since, _aware(snapshot.reset_at))
        kinds = set((await self.session.scalars(select(AntifraudEvent.kind).where(
            AntifraudEvent.tg_id == user.tg_id, AntifraudEvent.created_at > since,
        ))).all())
        refs_since = now - timedelta(minutes=int(policy["antifraud.ref_window_minutes"]))
        if snapshot.reset_at is not None:
            refs_since = max(refs_since, _aware(snapshot.reset_at))
            reset_ms = int(_aware(snapshot.reset_at).timestamp() * 1000)
            clicks = [value for value in clicks if value > reset_ms]
        recent_refs = await self.session.scalar(select(func.count(User.id)).where(
            User.referrer_tg_id == user.tg_id, User.created_at > refs_since,
        ))
        age_hours = max(0.0, (now - _aware(user.created_at)).total_seconds() / 3600)
        signals = {
            "honeypot_promo": "honeypot_promo" in kinds,
            "honeypot_task": "honeypot_task" in kinds,
            "rate_limit": "rate_limit" in kinds,
            "ref_velocity": recent_refs >= int(policy["antifraud.ref_velocity_count"]),
            "young_first_seen": age_hours < int(policy["antifraud.young_first_seen_hours"]),
            "no_username": not bool(user.username),
            "click_pattern": regular_click_pattern(clicks, minimum=int(policy["antifraud.pattern_min_clicks"]),
                variation_permille=int(policy["antifraud.pattern_variation_permille"])),
        }
        weights = {name: int(policy[f"antifraud.weight_{name}"]) for name in signals}
        result = score_rules(signals, weights, threshold=int(policy["antifraud.shadow_threshold"]))
        snapshot.score = result.score
        snapshot.reasons_json = json.dumps(result.reasons)
        snapshot.strong_signals_json = json.dumps(result.strong_signals)
        snapshot.evaluated_at = now
        if result.should_shadow and policy["antifraud.enabled"] and policy["antifraud.auto_shadow"] and user.tg_id != app_settings.owner_id:
            changed = await self.session.execute(update(User).where(
                User.id == user.id, User.is_shadow_banned.is_(False), User.is_deleted.is_(False),
            ).values(is_shadow_banned=True).returning(User.id))
            if changed.scalar_one_or_none() is not None:
                self.session.add(AntifraudEvent(
                    tg_id=user.tg_id, user_id=user.id, kind="auto_shadow", created_at=now,
                    details_json=json.dumps({"score": result.score, "reasons": result.reasons,
                        "strong_signals": result.strong_signals, "generation": snapshot.generation}),
                ))
        await self.session.flush()
        return result

    async def honeypot_hit(self, *, user: User, kind: str, source_id: int) -> RiskResult:
        """A supplied callback/payload is insufficient: validate the actual marked entity."""
        if kind == "promo":
            marked = await self.session.scalar(select(Promo.id).where(Promo.id == source_id, Promo.is_honeypot.is_(True)))
            activation = await self.session.scalar(select(PromoActivation.id).where(
                PromoActivation.promo_id == source_id, PromoActivation.user_id == user.id,
                PromoActivation.is_honeypot_hit.is_(True),
            ))
            if not activation:
                raise ValueError("honeypot promo activation evidence required")
        elif kind == "task":
            marked = await self.session.scalar(select(Sponsor.id).where(
                Sponsor.id == source_id, Sponsor.is_honeypot.is_(True), Sponsor.is_required.is_(False), Sponsor.is_active.is_(True),
            ))
        else:
            raise ValueError("unknown honeypot evidence type")
        if not marked:
            raise ValueError("marked database entity required")
        now = utcnow()
        snapshot = await self._lock_snapshot(user.id, now)
        await self.session.execute(insert(AntifraudEvent).values(
            tg_id=user.tg_id, user_id=user.id, kind=f"honeypot_{kind}", created_at=now,
            source_key=f"honeypot:{kind}:{user.id}:{source_id}:g{snapshot.generation}",
            details_json=json.dumps({"source_id": source_id, "generation": snapshot.generation}),
        ).on_conflict_do_nothing(index_elements=["source_key"]))
        policy = await self._policy()
        return await self._evaluate(user, snapshot, policy, now)

    async def reset(self, *, user_id: int, actor_tg_id: int, reason: str, decision_token: str | None = None) -> None:
        if actor_tg_id != app_settings.owner_id:
            raise PermissionError("owner-only antifraud reset")
        reason = reason.strip()
        if not 8 <= len(reason) <= 500:
            raise ValueError("reset reason must contain 8..500 characters")
        if decision_token is not None and (len(decision_token) != 32 or any(char not in "0123456789abcdef" for char in decision_token)):
            raise ValueError("invalid owner decision nonce")
        source_key = f"owner-reset:{actor_tg_id}:{decision_token}" if decision_token else None
        now = utcnow()
        target = await self.session.execute(update(User).where(User.id == user_id).values(
            is_shadow_banned=User.is_shadow_banned,
        ).returning(User.tg_id).execution_options(synchronize_session=False))
        if target.scalar_one_or_none() in {None, app_settings.owner_id}:
            raise ValueError("invalid antifraud reset target")
        if source_key and await self.session.scalar(select(AntifraudEvent.id).where(AntifraudEvent.source_key == source_key)):
            return
        user = await self.session.get(User, user_id, populate_existing=True)
        snapshot = await self._lock_snapshot(user_id, now)
        self.session.add(AntifraudEvent(
            tg_id=user.tg_id, user_id=user.id, kind="owner_reset", actor_tg_id=actor_tg_id, created_at=now, source_key=source_key,
            details_json=json.dumps({"reason": reason, "previous_score": snapshot.score,
                "previous_reasons": json.loads(snapshot.reasons_json), "previous_shadow": user.is_shadow_banned,
                "generation": snapshot.generation}),
        ))
        await self.session.execute(update(User).where(User.id == user_id).values(is_shadow_banned=False))
        snapshot.score = 0
        snapshot.reasons_json = "[]"
        snapshot.strong_signals_json = "[]"
        snapshot.reset_at = now
        snapshot.generation += 1
        snapshot.evaluated_at = now
        await self.session.flush()

    async def review_queue(self, *, actor_tg_id: int, page: int = 0):
        if actor_tg_id != app_settings.owner_id:
            raise PermissionError("owner-only antifraud review")
        threshold = await self.settings.get_int("antifraud.review_threshold", 40)
        rows = (await self.session.execute(select(User, AntifraudSnapshot).outerjoin(
            AntifraudSnapshot, AntifraudSnapshot.user_id == User.id,
        ).where((User.is_shadow_banned.is_(True)) | (AntifraudSnapshot.score >= threshold))
            .order_by(User.is_shadow_banned.desc(), AntifraudSnapshot.score.desc(), User.id)
            .limit(21).offset(max(0, page) * 20))).all()
        return rows[:20], len(rows) > 20

    async def review_detail(self, *, actor_tg_id: int, user_id: int):
        if actor_tg_id != app_settings.owner_id:
            raise PermissionError("owner-only antifraud review")
        user = await self.session.get(User, user_id, populate_existing=True)
        if user is None:
            raise ValueError("antifraud user not found")
        snapshot = await self.session.get(AntifraudSnapshot, user_id, populate_existing=True)
        events = (await self.session.scalars(select(AntifraudEvent).where(
            AntifraudEvent.tg_id == user.tg_id,
        ).order_by(AntifraudEvent.id.desc()).limit(12))).all()
        return user, snapshot, events

    async def create_hidden_task(self, *, actor_tg_id: int, decision_token: str | None = None) -> Sponsor:
        if actor_tg_id != app_settings.owner_id:
            raise PermissionError("owner-only honeypot creation")
        if decision_token is not None and (len(decision_token) != 32 or any(char not in "0123456789abcdef" for char in decision_token)):
            raise ValueError("invalid owner decision nonce")
        event_id = None
        if decision_token:
            source_key = f"owner-create:{actor_tg_id}:{decision_token}"
            inserted = await self.session.execute(insert(AntifraudEvent).values(
                tg_id=actor_tg_id, actor_tg_id=actor_tg_id, kind="owner_create_task", source_key=source_key,
                details_json="{}", created_at=utcnow(),
            ).on_conflict_do_nothing(index_elements=["source_key"]).returning(AntifraudEvent.id))
            event_id = inserted.scalar_one_or_none()
            if event_id is None:
                previous = await self.session.scalar(select(AntifraudEvent).where(AntifraudEvent.source_key == source_key))
                return await self.session.get(Sponsor, json.loads(previous.details_json)["sponsor_id"])
        from locales.ru import T
        sponsor = Sponsor(title=T.antifraud_hidden_task_title, kind="public", is_required=False,
            is_active=True, is_honeypot=True, reward=0, username=None, chat_id=None, invite_link=None)
        self.session.add(sponsor)
        await self.session.flush()
        details = json.dumps({"sponsor_id": sponsor.id, "hidden": True})
        if event_id is None:
            self.session.add(AntifraudEvent(tg_id=actor_tg_id, kind="owner_create_task", actor_tg_id=actor_tg_id, details_json=details))
        else:
            await self.session.execute(update(AntifraudEvent).where(AntifraudEvent.id == event_id).values(details_json=details))
        await self.session.flush()
        return sponsor
