# -*- coding: utf-8 -*-
"""
AETHER-X // ARAÇ KONTROLLERİ
Klavye eşlemesi oyuncu tarafından değiştirilebilir (PREFS["keys"] içinde saklanır, çakışma denetlenir).
Dokunmatik: sol altta direksiyon (yatay sürükle), sağ altta gaz ve fren pedalları, kamera/bin-in/far/kurtar düğmeleri.
Çoklu dokunuş (pygame FINGER olayları) ve fare yedeği desteklenir.
"""
import math

import pygame

from .physics import Controls

DEFAULT_KEYS = {
    "ileri": "w", "geri": "s", "sol": "a", "sağ": "d", "el freni": "space", "hız modu": "left shift",
    "kamera": "c", "bin/in": "f", "farlar": "l", "kurtar": "r", "otopilot": "p", "numune": "e",
}
ACTION_LABEL = {"ileri": "İleri", "geri": "Geri / fren", "sol": "Sola", "sağ": "Sağa", "el freni": "El freni",
                "hız modu": "Hız modu", "kamera": "Kamera değiştir", "bin/in": "Araca bin / in", "farlar": "Farlar",
                "kurtar": "Kurtar / sıfırla", "otopilot": "Otopilot", "numune": "Numune al"}


class KeyMap:
    def __init__(self, store=None):
        self.store = store if store is not None else {}
        self.keys = dict(DEFAULT_KEYS)
        saved = self.store.get("keys")
        if isinstance(saved, dict):
            for a, k in saved.items():
                if a in self.keys and isinstance(k, str):
                    self.keys[a] = k
        self.codes = {}
        self._rebuild()

    def _rebuild(self):
        self.codes = {}
        for a, name in self.keys.items():
            try:
                self.codes[a] = pygame.key.key_code(name)
            except Exception:
                self.codes[a] = None

    def bind(self, action, keycode):
        """Tuş ata; aynı tuş başka eylemdeyse yer değiştirir (çakışma bırakmaz). Döner: takas edilen eylem ya da None."""
        name = pygame.key.name(keycode)
        swapped = None
        for a, n in self.keys.items():
            if n == name and a != action:
                self.keys[a] = self.keys[action]
                swapped = a
        self.keys[action] = name
        self._rebuild()
        self.store["keys"] = dict(self.keys)
        return swapped

    def reset(self):
        self.keys = dict(DEFAULT_KEYS)
        self._rebuild()
        self.store["keys"] = dict(self.keys)

    def conflicts(self):
        seen, out = {}, []
        for a, n in self.keys.items():
            if n in seen:
                out.append((seen[n], a))
            seen[n] = a
        return out

    def held(self, pressed, action):
        c = self.codes.get(action)
        if c is None:
            return False
        try:
            return bool(pressed[c])
        except (IndexError, KeyError):
            return False

    def is_event(self, e, action):
        return e.type == pygame.KEYDOWN and self.codes.get(action) == e.key


class TouchControls:
    """Ekran alanları (1600x900 mantıksal): direksiyon, gaz, fren, düğmeler. Çıktı: Controls + basılan düğmeler."""

    def __init__(self, W=1600, H=900):
        self.wheel_c = (190, H - 190)
        self.wheel_r = 120
        self.gas = pygame.Rect(W - 210, H - 300, 150, 230)
        self.brake = pygame.Rect(W - 390, H - 230, 150, 160)
        self.buttons = {"kamera": pygame.Rect(W - 210, H - 420, 150, 70), "bin/in": pygame.Rect(W - 390, H - 420, 150, 70),
                        "farlar": pygame.Rect(W - 390, H - 330, 70, 70), "kurtar": pygame.Rect(W - 310, H - 330, 70, 70)}
        self.W, self.H = W, H
        self.touches = {}         # id -> (alan, başlangıç, şimdi)
        self.steer = 0.0
        self.active = False       # dokunmatik kullanıldıysa arayüz çizilir
        self.pressed = []

    def _zone(self, pos):
        if math.dist(pos, self.wheel_c) < self.wheel_r * 1.4:
            return "direksiyon"
        if self.gas.collidepoint(pos):
            return "gaz"
        if self.brake.collidepoint(pos):
            return "fren"
        for k, r in self.buttons.items():
            if r.collidepoint(pos):
                return k
        return None

    def handle(self, e):
        pos = tid = None
        if e.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            pos, tid = (e.x * self.W, e.y * self.H), ("f", e.finger_id)
        elif e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP) and hasattr(e, "pos"):
            if e.type == pygame.MOUSEMOTION and "m" not in [k[0] for k in self.touches]:
                return False
            pos, tid = e.pos, ("m", 0)
        else:
            return False
        if e.type in (pygame.FINGERDOWN, pygame.MOUSEBUTTONDOWN):
            z = self._zone(pos)
            if z is None:
                return False
            self.active = True
            self.touches[tid] = [z, pos, pos]
            if z in self.buttons:
                self.pressed.append(z)
            return True
        if tid not in self.touches:
            return False
        if e.type in (pygame.FINGERMOTION, pygame.MOUSEMOTION):
            self.touches[tid][2] = pos
            return True
        del self.touches[tid]
        return True

    def controls(self):
        c = Controls()
        steer = 0.0
        for z, start, now in self.touches.values():
            if z == "direksiyon":
                steer = max(-1.0, min(1.0, (now[0] - start[0]) / self.wheel_r))
            elif z == "gaz":
                c.throttle = max(c.throttle, min(1.0, 0.4 + (self.gas.bottom - now[1]) / self.gas.h))
            elif z == "fren":
                c.brake = 1.0
        self.steer += (steer - self.steer) * 0.4
        c.steer = self.steer
        return c

    def take_pressed(self):
        out, self.pressed = self.pressed, []
        return out
