# -*- coding: utf-8 -*-
"""Sahne taban sınıfı ve ortak ekran yardımcıları."""
import math

import pygame

from ..config import C, W, H, TOPBAR_H
from ..fx import SpaceBackground, draw_glow, scale_color
from ..ui import Button, UI, draw_text, glass_panel, draw_icon


class Scene:
    music = "base"
    ambient = None
    show_topbar = True
    allow_events = True
    background = "deep"
    title = ""
    title_icon = None
    accent = C["cyan"]
    bloom_k = 1.0            # ekran başına parlama (bloom) şiddeti; zaten çok parlak sahnelerde düşürülür

    def __init__(self, app):
        self.app = app
        self.game = app.game
        self.widgets = []
        self.t = 0.0
        self.bg = None

    # --- yaşam döngüsü ------------------------------------------------------
    def enter(self, **kw):
        pass

    def exit(self):
        pass

    def rebuild(self):
        """Durum değiştiğinde widget'ları yeniden oluşturmak için."""
        pass

    # --- yardımcılar ---------------------------------------------------------
    def ensure_bg(self, palette=None, seed=11, density=1.0):
        if self.bg is None:
            from .. import i18n
            n = int(380 * i18n.quality().get("stars", 900) / 900)       # yıldız sayısı grafik kademesine göre
            self.bg = SpaceBackground(palette or self.background, seed, n, density)
        return self.bg

    def add(self, w):
        self.widgets.append(w)
        return w

    def act(self, fn, *args, ok_sound=None):
        """Oyun eylemini çağırır; hata metnini NOVA/toast ile gösterir."""
        ok, why = fn(*args)
        if not ok and why:
            self.app.toast(why, "red", "warning")
            self.app.audio.play("deny")
        elif ok and ok_sound:
            self.app.audio.play(ok_sound)
        self.rebuild()
        return ok

    def back_button(self, target="base", label="ÜS"):
        return self.add(Button((24, H - 70, 150, 48), label, lambda: self.app.go(target), icon="arrow_left",
                               accent=C["text_dim"], size=17, hotkey=pygame.K_ESCAPE))

    def draw_title(self, surf, text=None, icon=None, sub=None, accent=None):
        text = text or self.title
        icon = icon or self.title_icon
        acc = accent or self.accent
        y = TOPBAR_H + 20
        x = 40
        if icon:
            draw_glow(surf, (x + 16, y + 20), 34, acc, 0.6)
            draw_icon(surf, icon, (x + 16, y + 20), 28, acc)
            x += 46
        draw_text(surf, text, (x, y), 34, C["text"], bold=True, glow=scale_color(acc, 0.6))
        if sub:
            draw_text(surf, sub, (x + 2, y + 44), 16, C["text_dim"])
        pygame.draw.line(surf, scale_color(acc, 0.5), (40, y + 70), (W - 40, y + 70), 1)
        draw_glow(surf, (40 + (self.t * 220) % (W - 80), y + 70), 18, acc, 0.6)

    # --- döngü ----------------------------------------------------------------
    def handle(self, e):
        for w in reversed(self.widgets):
            if w.visible and w.handle(e):
                return True
        return False

    def update(self, dt):
        self.t += dt
        if self.bg:
            self.bg.update(dt)
        for w in self.widgets:
            w.update(dt)

    def draw_widgets(self, surf):
        for w in self.widgets:
            w.draw(surf)

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        self.draw_widgets(surf)
