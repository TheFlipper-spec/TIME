"""Text drawing helpers: outline, shadow, glow, wrapped paragraphs."""
from __future__ import annotations

import pygame

from . import fonts

OUTLINE = (10, 12, 18)
SHADOW = (0, 0, 0)


def draw_text(surface: pygame.Surface, text: str, pos: tuple[int, int],
              size: int = 20, color=(235, 235, 235), kind: str = "sans",
              align: str = "left", outline: bool = False, shadow: bool = True,
              glow: tuple[int, int, int] | None = None, alpha: int = 255,
              glow_radius: int = 3) -> tuple[int, int]:
    """Draw text; returns its rendered size (w, h)."""
    if fonts.has_cjk(text):
        font = fonts.get_cjk(size)
    else:
        font = fonts.get(kind, size)
    img = font.render(text, True, color)
    if alpha < 255:
        img.set_alpha(alpha)
    rect = img.get_rect()
    if align == "center":
        rect.midtop = (pos[0], pos[1])
    elif align == "right":
        rect.topright = pos
    else:
        rect.topleft = pos

    if glow is not None:
        for dx in range(-glow_radius, glow_radius + 1):
            for dy in range(-glow_radius, glow_radius + 1):
                if dx * dx + dy * dy <= glow_radius * glow_radius:
                    g = font.render(text, True, glow)
                    if alpha < 255:
                        g.set_alpha(alpha // 2)
                    surface.blit(g, (rect.x + dx, rect.y + dy))
    if outline:
        for dx in (-1, 1):
            for dy in (-1, 1):
                o = font.render(text, True, OUTLINE)
                if alpha < 255:
                    o.set_alpha(alpha)
                surface.blit(o, (rect.x + dx, rect.y + dy))
    elif shadow:
        sh = font.render(text, True, SHADOW)
        if alpha < 255:
            sh.set_alpha(alpha)
        surface.blit(sh, (rect.x + 2, rect.y + 2))
    surface.blit(img, rect)
    return img.get_size()


def wrap_text(text: str, max_width: int, size: int = 20, kind: str = "sans") -> list[str]:
    """Word-wrap text into lines that fit max_width."""
    font = fonts.get(kind, size)
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if font.size(trial)[0] <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def draw_wrapped(surface: pygame.Surface, text: str, pos: tuple[int, int],
                 max_width: int, size: int = 20, color=(235, 235, 235),
                 kind: str = "sans", line_spacing: int = 6, align: str = "left",
                 outline: bool = False, alpha: int = 255) -> int:
    """Draw wrapped paragraph; returns total height drawn."""
    lines = wrap_text(text, max_width, size, kind)
    y = pos[1]
    for ln in lines:
        draw_text(surface, ln, (pos[0], y), size=size, color=color, kind=kind,
                  align=align, outline=outline, alpha=alpha)
        y += size + line_spacing
    return y - pos[1]


def draw_centered(surface: pygame.Surface, text: str, cx: int, cy: int,
                  size: int = 20, color=(235, 235, 235), kind: str = "sans",
                  outline: bool = False, glow: tuple[int, int, int] | None = None,
                  alpha: int = 255, shadow: bool = True) -> None:
    w, h = draw_text(surface, text, (cx, cy), size=size, color=color, kind=kind,
                     align="center", outline=outline, glow=glow, alpha=alpha,
                     shadow=shadow)
    # draw_text with align center already centers; nothing else needed.
    del w, h
