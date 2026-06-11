from __future__ import annotations

import random
import secrets
from dataclasses import dataclass


# Пул эмодзи для капчи (Telegram-совместимые, базовые).
EMOJI_POOL: tuple[str, ...] = (
    "🍎", "🍌", "🍇", "🍉", "🍒", "🍓", "🥝", "🍍",
    "🚗", "🚕", "🚙", "🚌", "🚂", "✈️", "🚀", "⛵",
    "⚽", "🏀", "🎾", "🏈", "🎱", "🏓", "🎯", "🥊",
    "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼",
    "🌞", "🌙", "⭐", "🔥", "💧", "❄️", "🌈", "☁️",
    "❤️", "💛", "💚", "💙", "💜", "🖤", "🤍", "💎",
    "🎁", "🎈", "🎉", "🔔", "📱", "💻", "🎵", "🎮",
)

CHOICES_COUNT: int = 4   # сколько кнопок-вариантов показываем
ON_IMAGE_COUNT: int = 6  # сколько эмодзи рисуем на картинке


@dataclass(frozen=True)
class CaptchaTask:
    answer: str            # правильный эмодзи (один из on_image)
    on_image: tuple[str, ...]   # что нарисовано на картинке (6 эмодзи)
    choices: tuple[str, ...]    # варианты для кнопок (4, включая правильный)
    token: str             # токен задачи (для idempotency и проверки)


def generate_task() -> CaptchaTask:
    rng = random.SystemRandom()
    on_image = tuple(rng.sample(EMOJI_POOL, ON_IMAGE_COUNT))
    answer = rng.choice(on_image)
    # 3 фейка не из on_image
    pool_without = [e for e in EMOJI_POOL if e not in on_image]
    fakes = rng.sample(pool_without, CHOICES_COUNT - 1)
    choices = list(fakes) + [answer]
    rng.shuffle(choices)
    return CaptchaTask(
        answer=answer,
        on_image=on_image,
        choices=tuple(choices),
        token=secrets.token_urlsafe(12),
    )
