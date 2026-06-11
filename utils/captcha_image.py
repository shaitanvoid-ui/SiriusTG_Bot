from __future__ import annotations

import io
import random
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# Возможные расположения font-файла на Debian/Ubuntu.
_EMOJI_FONT_CANDIDATES: tuple[Path, ...] = (
    Path("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"),
    Path("/usr/share/fonts/noto/NotoColorEmoji.ttf"),
    Path("/usr/share/fonts/google-noto-color-emoji/NotoColorEmoji.ttf"),
)

# NotoColorEmoji — CBDT-bitmap, нативный размер 109px.
_EMOJI_NATIVE_SIZE: int = 109

CANVAS_W: int = 720
CANVAS_H: int = 300
ROWS: int = 2
COLS: int = 3
BG_COLORS: tuple[tuple[int, int, int], ...] = (
    (245, 235, 220),
    (220, 240, 245),
    (230, 245, 225),
    (250, 230, 235),
    (240, 235, 250),
)


@lru_cache(maxsize=1)
def _load_emoji_font() -> ImageFont.FreeTypeFont | None:
    for path in _EMOJI_FONT_CANDIDATES:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=_EMOJI_NATIVE_SIZE)
            except OSError:
                continue
    return None


def _draw_noise(draw: ImageDraw.ImageDraw, rng: random.Random) -> None:
    # тонкие линии-помехи
    for _ in range(8):
        x1, y1 = rng.randint(0, CANVAS_W), rng.randint(0, CANVAS_H)
        x2, y2 = rng.randint(0, CANVAS_W), rng.randint(0, CANVAS_H)
        color = tuple(rng.randint(140, 210) for _ in range(3))
        draw.line((x1, y1, x2, y2), fill=color, width=2)
    # мелкие точки
    for _ in range(180):
        x, y = rng.randint(0, CANVAS_W - 1), rng.randint(0, CANVAS_H - 1)
        color = tuple(rng.randint(120, 200) for _ in range(3))
        draw.point((x, y), fill=color)


def render(emojis: tuple[str, ...]) -> bytes:
    """Рендерит PNG с эмодзи. Эмодзи случайно перемешиваются по сетке 2x3."""
    rng = random.SystemRandom()
    bg = rng.choice(BG_COLORS)
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), bg)
    draw = ImageDraw.Draw(img)
    _draw_noise(draw, rng)

    font = _load_emoji_font()

    cell_w = CANVAS_W // COLS
    cell_h = CANVAS_H // ROWS
    # размещаем 6 эмодзи (по числу слотов в сетке)
    positions: list[tuple[int, int]] = []
    for r in range(ROWS):
        for c in range(COLS):
            cx = c * cell_w + cell_w // 2
            cy = r * cell_h + cell_h // 2
            positions.append((cx, cy))

    shuffled = list(emojis)
    rng.shuffle(shuffled)

    for (cx, cy), emoji in zip(positions, shuffled):
        # лёгкое случайное смещение и поворот
        dx = rng.randint(-8, 8)
        dy = rng.randint(-8, 8)
        if font is not None:
            # NotoColorEmoji — рисуем в нативном размере и масштабируем вниз
            patch = Image.new("RGBA", (_EMOJI_NATIVE_SIZE, _EMOJI_NATIVE_SIZE), (0, 0, 0, 0))
            pdraw = ImageDraw.Draw(patch)
            pdraw.text(
                (0, 0),
                emoji,
                font=font,
                embedded_color=True,
            )
            target = 96
            patch = patch.resize((target, target), Image.LANCZOS)
            angle = rng.randint(-12, 12)
            patch = patch.rotate(angle, resample=Image.BICUBIC, expand=True)
            img.paste(
                patch,
                (cx - patch.size[0] // 2 + dx, cy - patch.size[1] // 2 + dy),
                patch,
            )
        else:
            # fallback: символ без цветного рендера
            try:
                fallback_font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=64
                )
            except OSError:
                fallback_font = ImageFont.load_default()
            draw.text((cx - 32 + dx, cy - 32 + dy), emoji, font=fallback_font, fill=(40, 40, 40))

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
