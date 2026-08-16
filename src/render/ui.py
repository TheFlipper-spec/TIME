"""Reusable UI widgets drawn on the design-resolution canvas."""
from __future__ import annotations

import math
import pygame

from ..audio import play
from .text import draw_text, wrap_text

ACCENT = (212, 175, 55)          # warm gold
ACCENT_DIM = (150, 122, 44)
BLUE = (58, 96, 160)
DARK = (16, 20, 32)
PANEL = (24, 30, 48)
PANEL_EDGE = (70, 84, 120)
TEXT = (232, 232, 235)
TEXT_DIM = (150, 155, 170)
DANGER = (196, 64, 64)
OK = (86, 170, 96)


class Widget:
    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = pygame.Rect(rect)
        self.visible = True
        self.enabled = True

    def handle(self, event: pygame.event.Event) -> bool:
        return False

    def update(self, dt: float, mouse: tuple[int, int]) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        pass


class Button(Widget):
    def __init__(self, rect, label: str = "", on_click=None, style: str = "default",
                 size: int = 26, icon=None) -> None:
        super().__init__(rect)
        self.label = label
        self.on_click = on_click
        self.style = style
        self.size = size
        self.icon = icon
        self.hover = 0.0
        self.hovered = False

    def handle(self, event) -> bool:
        if not (self.visible and self.enabled):
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                play("click")
                if self.on_click:
                    self.on_click()
                return True
        if event.type == pygame.KEYDOWN and self.hovered:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                play("click")
                if self.on_click:
                    self.on_click()
                return True
        return False

    def update(self, dt, mouse) -> None:
        self.hovered = self.visible and self.enabled and self.rect.collidepoint(mouse)
        target = 1.0 if self.hovered else 0.0
        self.hover = self.hover + (target - self.hover) * min(1.0, dt * 10)

    def draw(self, surface) -> None:
        if not self.visible:
            return
        r = self.rect
        if self.style == "ghost":
            bg = (30, 38, 60)
            edge = (90, 105, 150)
            txt = TEXT
            hover_edge = ACCENT
        elif self.style == "danger":
            bg = (64, 26, 26)
            edge = (140, 60, 60)
            txt = (240, 190, 190)
            hover_edge = (220, 90, 90)
        elif self.style == "gold":
            bg = (48, 40, 16)
            edge = ACCENT
            txt = (245, 226, 170)
            hover_edge = (255, 220, 120)
        else:
            bg = (34, 42, 68)
            edge = (84, 100, 150)
            txt = TEXT
            hover_edge = ACCENT
        if self.hover > 0:
            bg = tuple(min(255, int(c + 16 * self.hover)) for c in bg)
        if not self.enabled:
            bg = tuple(int(c * 0.55) for c in bg)
            txt = TEXT_DIM
        edge_c = tuple(
            int(edge[i] + (hover_edge[i] - edge[i]) * self.hover) for i in range(3)
        )
        shadow = pygame.Rect(r.x + 3, r.y + 4, r.w, r.h)
        pygame.draw.rect(surface, (0, 0, 0), shadow, border_radius=10)
        pygame.draw.rect(surface, bg, r, border_radius=10)
        pygame.draw.rect(surface, edge_c, r, width=2, border_radius=10)
        if self.icon is not None:
            surface.blit(self.icon, (r.x + 10, r.centery - self.icon.get_height() // 2))
            tx = r.x + 24
        else:
            tx = r.centerx
        draw_text(surface, self.label, (tx, r.centery - self.size // 2),
                  size=self.size, color=txt, align="center" if self.icon is None else "left",
                  shadow=False)


class IconButton(Button):
    """Round/square icon button (arrows, close, etc.)."""

    def __init__(self, rect, glyph: str, on_click=None, size: int = 30,
                 kind: str = "sans_bold") -> None:
        super().__init__(rect, "", on_click, size=size)
        self.glyph = glyph
        self.kind = kind

    def draw(self, surface) -> None:
        if not self.visible:
            return
        r = self.rect
        bg = (38, 46, 76) if self.enabled else (26, 30, 46)
        if self.hover > 0:
            bg = tuple(min(255, int(c + 20 * self.hover)) for c in bg)
        pygame.draw.rect(surface, (0, 0, 0), pygame.Rect(r.x + 2, r.y + 3, r.w, r.h), border_radius=8)
        pygame.draw.rect(surface, bg, r, border_radius=8)
        edge = ACCENT if self.hover > 0.5 else (84, 100, 150)
        pygame.draw.rect(surface, edge, r, width=2, border_radius=8)
        draw_text(surface, self.glyph, (r.centerx, r.centery - self.size // 2),
                  size=self.size, color=(235, 235, 235) if self.enabled else TEXT_DIM,
                  align="center", kind=self.kind, shadow=False)


class Slider(Widget):
    def __init__(self, rect, value: float = 0.5, on_change=None, fmt=lambda v: f"{int(v*100)}%") -> None:
        super().__init__(rect)
        self.value = max(0.0, min(1.0, value))
        self.on_change = on_change
        self.fmt = fmt
        self.dragging = False

    def handle(self, event) -> bool:
        if not (self.visible and self.enabled):
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.dragging = True
            self._set_from_x(event.pos[0])
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        if event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_x(event.pos[0])
            return True
        return False

    def _set_from_x(self, x: int) -> None:
        v = (x - self.rect.x) / max(1, self.rect.w)
        v = max(0.0, min(1.0, v))
        self.value = v
        if self.on_change:
            self.on_change(v)

    def draw(self, surface) -> None:
        if not self.visible:
            return
        r = self.rect
        pygame.draw.rect(surface, (18, 22, 36), r, border_radius=r.h // 2)
        filled = pygame.Rect(r.x, r.y, int(r.w * self.value), r.h)
        if filled.w > 2:
            pygame.draw.rect(surface, ACCENT, filled, border_radius=r.h // 2)
        knob_x = r.x + int(r.w * self.value)
        pygame.draw.circle(surface, (240, 240, 240), (knob_x, r.centery), r.h // 2 + 3)
        pygame.draw.circle(surface, (60, 70, 100), (knob_x, r.centery), r.h // 2 + 3, 2)
        draw_text(surface, self.fmt(self.value), (r.right + 14, r.centery - 11),
                  size=18, color=TEXT_DIM, shadow=False)


class InputBox(Widget):
    def __init__(self, rect, text: str = "", on_submit=None, placeholder: str = "",
                 max_len: int = 64, secret: bool = False) -> None:
        super().__init__(rect)
        self.text = text
        self.on_submit = on_submit
        self.placeholder = placeholder
        self.max_len = max_len
        self.secret = secret
        self.active = False
        self._blink = 0.0

    def handle(self, event) -> bool:
        if not (self.visible and self.enabled):
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            return self.active
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                if self.on_submit:
                    self.on_submit(self.text)
                return True
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
                return True
            if event.key == pygame.K_v and (event.mod & pygame.KMOD_CTRL):
                try:
                    clip = pygame.scrap.get(pygame.SCRAP_TEXT).decode("utf-8", "ignore")
                    self.text = (self.text + clip)[: self.max_len]
                except Exception:
                    pass
                return True
            if event.unicode and event.unicode.isprintable():
                self.text = (self.text + event.unicode)[: self.max_len]
                return True
        return False

    def update(self, dt, mouse) -> None:
        self._blink += dt

    def draw(self, surface) -> None:
        if not self.visible:
            return
        r = self.rect
        bg = (14, 18, 30) if self.active else (18, 24, 40)
        pygame.draw.rect(surface, (0, 0, 0), pygame.Rect(r.x + 2, r.y + 2, r.w, r.h), border_radius=8)
        pygame.draw.rect(surface, bg, r, border_radius=8)
        edge = ACCENT if self.active else (70, 84, 120)
        pygame.draw.rect(surface, edge, r, width=2, border_radius=8)
        shown = "•" * len(self.text) if self.secret else self.text
        if shown:
            draw_text(surface, shown, (r.x + 12, r.centery - 13), size=22, shadow=False)
        elif self.placeholder:
            draw_text(surface, self.placeholder, (r.x + 12, r.centery - 13),
                      size=22, color=TEXT_DIM, shadow=False)
        if self.active and int(self._blink * 2) % 2 == 0:
            w = pygame.font.Font.size(pygame.font.Font(None, 1), "")[0]
            del w
            from .fonts import get as _get
            f = _get("sans", 22)
            tw = f.size(shown)[0]
            pygame.draw.rect(surface, (240, 240, 240), (r.x + 12 + tw + 2, r.centery - 13, 2, 22))


class Dropdown(Widget):
    def __init__(self, rect, options: list[tuple[str, str]], selected: str = "",
                 on_select=None, size: int = 20) -> None:
        super().__init__(rect)
        self.options = options            # list of (value, label)
        self.selected = selected
        self.on_select = on_select
        self.size = size
        self.open = False

    def handle(self, event) -> bool:
        if not (self.visible and self.enabled):
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.open = not self.open
                return True
            if self.open:
                for i, (val, label) in enumerate(self.options):
                    item = pygame.Rect(self.rect.x, self.rect.bottom + i * 30, self.rect.w, 30)
                    if item.collidepoint(event.pos):
                        self.selected = val
                        self.open = False
                        play("click")
                        if self.on_select:
                            self.on_select(val)
                        return True
                self.open = False
        return False

    def draw(self, surface) -> None:
        if not self.visible:
            return
        r = self.rect
        pygame.draw.rect(surface, (0, 0, 0), pygame.Rect(r.x + 2, r.y + 2, r.w, r.h), border_radius=8)
        pygame.draw.rect(surface, (24, 30, 48), r, border_radius=8)
        pygame.draw.rect(surface, ACCENT if self.open else (70, 84, 120), r, width=2, border_radius=8)
        label = next((l for v, l in self.options if v == self.selected), "")
        draw_text(surface, label, (r.x + 12, r.centery - 12), size=self.size, shadow=False)
        draw_text(surface, "▾", (r.right - 22, r.centery - 12), size=self.size,
                  color=ACCENT, shadow=False)
        if self.open:
            for i, (val, label) in enumerate(self.options):
                item = pygame.Rect(r.x, r.bottom + i * 30, r.w, 30)
                pygame.draw.rect(surface, (28, 36, 58), item, border_radius=6)
                pygame.draw.rect(surface, (60, 72, 108), item, width=1, border_radius=6)
                col = ACCENT if val == self.selected else TEXT
                draw_text(surface, label, (item.x + 12, item.centery - 11),
                          size=self.size, color=col, shadow=False)


class ProgressBar(Widget):
    def __init__(self, rect, value: float = 0.0, color=(86, 170, 96),
                 bg=(20, 26, 42), label: str = "") -> None:
        super().__init__(rect)
        self.value = max(0.0, min(1.0, value))
        self.color = color
        self.bg = bg
        self.label = label

    def set(self, v: float) -> None:
        self.value = max(0.0, min(1.0, v))

    def draw(self, surface) -> None:
        if not self.visible:
            return
        r = self.rect
        pygame.draw.rect(surface, self.bg, r, border_radius=r.h // 2)
        w = int(r.w * self.value)
        if w > 2:
            pygame.draw.rect(surface, self.color, pygame.Rect(r.x, r.y, w, r.h),
                             border_radius=r.h // 2)
        pygame.draw.rect(surface, (60, 70, 100), r, width=1, border_radius=r.h // 2)


class Panel:
    """Rounded translucent panel with optional title bar."""

    def __init__(self, rect, title: str = "", title_size: int = 30) -> None:
        self.rect = pygame.Rect(rect)
        self.title = title
        self.title_size = title_size
        self.alpha = 232

    def draw(self, surface, bg: tuple[int, int, int] | None = None) -> None:
        panel = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (*((bg or PANEL)), self.alpha), panel.get_rect(), border_radius=16)
        pygame.draw.rect(panel, (*PANEL_EDGE, 255), panel.get_rect(), width=2, border_radius=16)
        surface.blit(panel, self.rect.topleft)
        if self.title:
            draw_text(surface, self.title, (self.rect.centerx, self.rect.y + 18),
                      size=self.title_size, color=(240, 240, 245), align="center",
                      kind="sans_bold", shadow=True)


class Toast:
    """Transient tutorial/notice message that fades in/out."""

    def __init__(self, text: str, icon: str = "💡", duration: float = 6.0) -> None:
        self.text = text
        self.icon = icon
        self.duration = duration
        self.age = 0.0

    @property
    def done(self) -> bool:
        return self.age >= self.duration

    def update(self, dt: float) -> None:
        self.age += dt

    def draw(self, surface) -> None:
        alpha = 1.0
        if self.age < 0.4:
            alpha = self.age / 0.4
        if self.duration - self.age < 0.6:
            alpha = max(0.0, (self.duration - self.age) / 0.6)
        from .text import draw_wrapped, wrap_text
        max_w = 760
        lines = wrap_text(self.text, max_w - 90, 20)
        h = 24 + len(lines) * 28
        rect = pygame.Rect(0, 0, max_w, h)
        rect.centerx = surface.get_width() // 2
        rect.y = 86
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (14, 30, 52, int(235 * alpha)), panel.get_rect(), border_radius=14)
        pygame.draw.rect(panel, (90, 130, 190, int(255 * alpha)), panel.get_rect(), width=2, border_radius=14)
        surface.blit(panel, rect.topleft)
        # icon: glowing dot
        pygame.draw.circle(surface, (255, 214, 90), (rect.x + 34, rect.centery), 9)
        pygame.draw.circle(surface, (255, 240, 180), (rect.x + 34, rect.centery), 4)
        y = rect.y + 12
        for ln in lines:
            draw_text(surface, ln, (rect.x + 60, y), size=20, color=(226, 233, 244), shadow=False)
            y += 28


def rounded_rect(surface, rect, color, radius: int = 12, width: int = 0) -> None:
    pygame.draw.rect(surface, color, rect, width=width, border_radius=radius)
