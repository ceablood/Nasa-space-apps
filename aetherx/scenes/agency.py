# -*- coding: utf-8 -*-
"""
AJANS: genel durum, diplomasi (NASA, ESA, JAXA, ISRO, TUA), günlük ve
ayarlar (ajans adını 500 Para'ya değiştirme, ses, müzik, tam ekran, kayıt).
"""
import math

import pygame

from . import Scene
from .. import data as D
from .. import i18n
from ..config import C, H, RENAME_COST, TOPBAR_H, W, SAVE_FILE
from ..fx import draw_glow, scale_color
from ..ui import (UI, Button, Slider, Tabs, TextInput, Toggle, chip, draw_bar, draw_icon, draw_paragraph, draw_text,
                  glass_panel, fmt_num)


class AgencyScene(Scene):
    music = "base"
    ambient = "amb_base"
    title = "AJANS"
    title_icon = "settings"
    accent = C["violet"]

    def __init__(self, app):
        super().__init__(app)
        self.ensure_bg("violet", 27, 0.7)
        self.tab = 0
        self.confirm_delete = False
        self.name_input = None

    def enter(self, tab=0, **kw):
        self.tab = tab
        self.confirm_delete = False
        self.rebuild()

    def set_tab(self, i):
        self.tab = i
        self.confirm_delete = False
        self.rebuild()

    def rebuild(self):
        g = self.game
        self.widgets = []
        self.back_button()
        self.add(Tabs((40, TOPBAR_H + 100, 820, 46), ["GENEL", "DİPLOMASİ", "GÜNLÜK", "AYARLAR"], self.set_tab,
                      C["violet"], self.tab, ["flag", "handshake", "chart", "settings"]))
        if self.tab == 1:
            for i, p in enumerate(D.PARTNERS):
                st = g.s["diplomacy"][p["key"]]
                r = pygame.Rect(40 + i * 306, TOPBAR_H + 180, 294, 420)
                b1 = self.add(Button((r.x + 20, r.bottom - 130, r.w - 40, 48), f"İLİŞKİ +6 · {D.RELATION_COST} P",
                                     (lambda k=p["key"]: self.act(g.improve_relation, k, ok_sound="pickup")),
                                     accent=p["color"], size=14, icon="handshake"))
                b1.set_enabled(st["relation"] < 100 and g.money >= D.RELATION_COST,
                               "İlişki maksimumda" if st["relation"] >= 100 else f"{D.RELATION_COST} Para gerekli")
                b2 = self.add(Button((r.x + 20, r.bottom - 70, r.w - 40, 52), "ANLAŞMA İMZALA" if not st["pact"] else "ANLAŞMA AKTİF",
                                     (lambda k=p["key"]: self.act(g.sign_pact, k, ok_sound="success")), accent=C["gold"],
                                     size=15, icon="star", style="big"))
                if st["pact"]:
                    b2.set_enabled(False, "Anlaşma zaten aktif")
                    b2.selected = True
                elif st["relation"] < D.PACT_MIN:
                    b2.set_enabled(False, f"İlişki en az {D.PACT_MIN} olmalı")
                elif g.money < p["cost"]:
                    b2.set_enabled(False, f"{p['cost']} Para gerekli")
                else:
                    b2.pulse = True
        elif self.tab == 3:
            s = g.s["settings"]
            x = 40
            self.name_input = self.add(TextInput((x, TOPBAR_H + 210, 560, 64), g.name, "Yeni ajans adı", 28,
                                                 on_submit=lambda t: self.rename(), accent=g.color, size=26))
            self.name_input.active = False
            rb = self.add(Button((x + 580, TOPBAR_H + 212, 280, 60), f"ADI DEĞİŞTİR · {RENAME_COST} P", self.rename,
                                 accent=C["gold"], icon="flag", size=15))
            rb.set_enabled(g.money >= RENAME_COST, f"{RENAME_COST} Para gerekli")
            self.add(Toggle((x, TOPBAR_H + 320, 380, 40), s.get("sound", True), self.set_sound, "Ses ve müzik"))
            self.add(Slider((x, TOPBAR_H + 410, 380, 24), s.get("music", 0.55), self.set_music, C["cyan"], "MÜZİK"))
            self.add(Slider((x, TOPBAR_H + 480, 380, 24), s.get("sfx", 0.8), self.set_sfx, C["orange"], "EFEKTLER"))
            self.add(Button((x, TOPBAR_H + 540, 380, 50), "TAM EKRAN (F11)", self.app.toggle_fullscreen,
                            accent=C["violet"], size=15))
            self.add(Button((x + 500, TOPBAR_H + 320, 360, 50), "ŞİMDİ KAYDET", self.save_now, accent=C["green"],
                            icon="save", size=15))
            self.add(Button((x + 500, TOPBAR_H + 380, 360, 50), "ANA MENÜYE DÖN", self.to_menu, accent=C["cyan"],
                            icon="home", size=15))
            db = self.add(Button((x + 500, TOPBAR_H + 440, 360, 50),
                                 "EMİN MİSİN? TEKRAR TIKLA" if self.confirm_delete else "KAYDI SİL", self.delete,
                                 accent=C["red"], icon="cross", size=15, style="danger"))
            db.pulse = self.confirm_delete
            for i, (code, label) in enumerate(i18n.LANGS):
                b = self.add(Button((x + 940 + (i % 3) * 170, TOPBAR_H + 200 + (i // 3) * 56, 160, 48), label,
                                    (lambda c=code: self.set_lang(c)),
                                    accent=C["cyan"], size=15, style="tab"))
                b.selected = (i18n.LANG == code)
            on = i18n.PREFS.get("cinematic", True)
            cb = self.add(Button((x + 500, TOPBAR_H + 540, 360, 46), "AÇIK" if on else "KAPALI", self.toggle_cinema,
                                 accent=C["magenta"] if on else C["text_dim"], icon="star", size=15, style="tab"))
            cb.selected = on
            for i, q in enumerate(i18n.QUALITY_ORDER):
                b = self.add(Button((x + 940 + i * 128, TOPBAR_H + 340, 120, 50), i18n.QUALITY_LABEL[q][0],
                                    (lambda qq=q: self.set_quality(qq)), accent=C["gold"], size=13, style="tab"))
                b.selected = (i18n.PREFS.get("quality") == q)

    # ---------------------------------------------------------------- eylemler
    def rename(self):
        new = self.name_input.text.strip() if self.name_input else ""
        if self.act(self.game.rename, new, ok_sound="success"):
            self.app.say(f"Merhaba {self.game.name}! Yeni adın tabelada, roketlerde ve bayraklarda.", "happy")

    def set_lang(self, code):
        i18n.set_lang(code)
        i18n.save_prefs()
        self.app.on_game_ready()
        self.app.audio.play("success", 0.5)
        self.rebuild()

    def toggle_cinema(self):
        i18n.PREFS["cinematic"] = not i18n.PREFS.get("cinematic", True)
        i18n.save_prefs()
        self.app.audio.play("click")
        self.rebuild()

    def set_quality(self, q):
        i18n.PREFS["quality"] = q
        i18n.save_prefs()
        self.app.audio.play("click")
        self.rebuild()

    def set_sound(self, v):
        self.game.s["settings"]["sound"] = v
        self.app.audio.set_enabled(v)

    def set_music(self, v):
        self.game.s["settings"]["music"] = v
        self.app.audio.set_volumes(music=v)

    def set_sfx(self, v):
        self.game.s["settings"]["sfx"] = v
        self.app.audio.set_volumes(sfx=v)

    def save_now(self):
        ok = self.game.save()
        self.app.toast("Kampanya kaydedildi" if ok else "Kayıt başarısız: " + str(self.game.save_error),
                       "green" if ok else "red", "save")

    def to_menu(self):
        self.game.save()
        self.app.go("intro")

    def delete(self):
        if not self.confirm_delete:
            self.confirm_delete = True
            self.rebuild()
            return
        self.game.delete_save()
        self.game.s = None
        self.app.go("intro")

    def update(self, dt):
        super().update(dt)
        if self.tab == 1:
            sig = tuple((v["relation"], v["pact"]) for v in self.game.s["diplomacy"].values()) + (self.game.money // 100,)
            if getattr(self, "_sig", None) != sig:
                self._sig = sig
                self.rebuild()

    # ----------------------------------------------------------------- çizim
    def draw(self, surf):
        g = self.game
        if not g.s:
            return
        self.bg.draw(surf)
        self.draw_title(surf, sub=f"{g.name} · Seviye {g.s['agency']['level']} · {g.badge()}")
        getattr(self, f"draw_{self.tab}")(surf)
        self.draw_widgets(surf)

    def draw_0(self, surf):
        g = self.game
        a = g.s["agency"]
        r = pygame.Rect(40, TOPBAR_H + 170, 560, 300)
        glass_panel(surf, r, g.color, 200, 20, strong=True)
        cx, cy = r.x + 100, r.y + 110
        draw_glow(surf, (cx, cy), 90, g.color, 0.6)
        pygame.draw.circle(surf, (8, 14, 30), (cx, cy), 62)
        pygame.draw.circle(surf, g.color, (cx, cy), 62, 3)
        for i in range(12):
            ang = i * math.pi / 6 + self.t * 0.3
            pygame.draw.line(surf, g.color, (cx + math.cos(ang) * 66, cy + math.sin(ang) * 66),
                             (cx + math.cos(ang) * 76, cy + math.sin(ang) * 76), 2)
        draw_icon(surf, "rocket", (cx, cy), 60, g.color)
        draw_text(surf, g.name.upper(), (r.x + 190, r.y + 40), 28, C["text"], bold=True, glow=g.color)
        draw_text(surf, g.badge(), (r.x + 190, r.y + 82), 18, g.color, bold=True)
        xp, need, frac = g.xp_progress()
        draw_bar(surf, (r.x + 190, r.y + 136, 340, 12), frac, g.color, label=f"SEVİYE {a['level']}", value=f"{xp}/{need} XP")
        draw_bar(surf, (r.x + 190, r.y + 186, 340, 10), a["rep"] / 100, C["gold"], label="İTİBAR", value=f"{a['rep']}/100")
        draw_text(surf, f"Kuruluş: Gün 1 · Şimdi: {g.time_label()}", (r.x + 30, r.bottom - 44), 14, C["text_dim"])
        st = g.s["stats"]
        stats = [("Fırlatma", st["launches"]), ("Başarılı", st["success"]), ("Kısmi", st["partial"]),
                 ("Başarısız", st["fail"]), ("Kırılan asteroit", st["asteroids"]), ("Yıldız Tozu", st["stardust"]),
                 ("Fotoğraf", st["photos"]), ("Kurtarılan uydu", st["rescues"]), ("Toplam kazanç", fmt_num(st["earned"])),
                 ("Toplam harcama", fmt_num(st["spent"])), ("Araştırma", f"{len(g.s['research']['done'])}/{len(D.RESEARCH)}"),
                 ("Başarım", f"{len(g.s['achievements'])}/{len(D.ACHIEVEMENTS)}")]
        r2 = pygame.Rect(630, TOPBAR_H + 170, W - 670, 300)
        glass_panel(surf, r2, C["cyan"], 180, 20)
        for i, (k, v) in enumerate(stats):
            x = r2.x + 30 + (i % 3) * (r2.w - 60) / 3
            y = r2.y + 26 + (i // 3) * 68
            draw_text(surf, str(v), (x, y), 26, C["text"], bold=True)
            draw_text(surf, k, (x, y + 34), 13, C["text_dim"])
        # zafer yolu
        r3 = pygame.Rect(40, TOPBAR_H + 500, W - 80, 170)
        glass_panel(surf, r3, C["gold"], 180, 20)
        draw_text(surf, "NİHAİ HEDEF: GÜNEŞ SİSTEMİ'Nİ AÇ, JÜPİTER'DE DEV KOLONİYİ KUR", (r3.x + 24, r3.y + 16), 16,
                  C["gold"], bold=True)
        steps = g.victory_progress()
        n = len(steps)
        for i, (lab, ok) in enumerate(steps):
            x = r3.x + 80 + i * (r3.w - 160) / (n - 1)
            y = r3.y + 90
            if i < n - 1:
                nx = r3.x + 80 + (i + 1) * (r3.w - 160) / (n - 1)
                pygame.draw.line(surf, C["gold"] if ok else (60, 70, 90), (x + 22, y), (nx - 22, y), 3)
            pygame.draw.circle(surf, scale_color(C["gold"], 0.3) if ok else (20, 26, 44), (int(x), y), 22)
            pygame.draw.circle(surf, C["gold"] if ok else (70, 80, 100), (int(x), y), 22, 3)
            if ok:
                draw_glow(surf, (x, y), 30, C["gold"], 0.5)
            draw_icon(surf, "check" if ok else "lock", (x, y), 18, C["white"] if ok else (90, 100, 125))
            draw_text(surf, lab, (x, y + 32), 13, C["text"] if ok else C["text_dim"], bold=True, anchor="midtop")

    def draw_1(self, surf):
        g = self.game
        draw_text(surf, f"Anlaşma için ilişki en az {D.PACT_MIN} olmalı. Her anlaşma günlük +60 Para getirir.",
                  (40, TOPBAR_H + 160), 15, C["text_dim"])
        for i, p in enumerate(D.PARTNERS):
            st = g.s["diplomacy"][p["key"]]
            r = pygame.Rect(40 + i * 306, TOPBAR_H + 180, 294, 420)
            glass_panel(surf, r, p["color"], 180, 18, strong=st["pact"])
            cx = r.centerx
            draw_glow(surf, (cx, r.y + 80), 60, p["color"], 0.5)
            pygame.draw.circle(surf, (8, 12, 26), (cx, r.y + 80), 46)
            pygame.draw.circle(surf, p["color"], (cx, r.y + 80), 46, 3)
            draw_text(surf, p["name"], (cx, r.y + 80), 24, C["text"], bold=True, anchor="center")
            draw_text(surf, p["perk"], (cx, r.y + 146), 15, p["color"], bold=True, anchor="midtop")
            draw_text(surf, f"Anlaşma bedeli: {fmt_num(p['cost'])} P", (cx, r.y + 172), 13, C["text_dim"], anchor="midtop")
            draw_bar(surf, (r.x + 20, r.y + 226, r.w - 40, 12), st["relation"] / 100,
                     C["green"] if st["relation"] >= D.PACT_MIN else p["color"], label="İLİŞKİ",
                     value=f"{st['relation']}/100")
            mark_x = r.x + 20 + (r.w - 40) * D.PACT_MIN / 100
            pygame.draw.line(surf, C["gold"], (mark_x, r.y + 220), (mark_x, r.y + 244), 2)
            if st["pact"]:
                chip(surf, (cx, r.y + 254), "STRATEJİK ORTAK", C["gold"], 13, anchor="midtop", icon="star")

    def draw_2(self, surf):
        g = self.game
        r = pygame.Rect(40, TOPBAR_H + 170, W - 80, H - TOPBAR_H - 260)
        glass_panel(surf, r, C["violet"], 180, 18)
        for i, e in enumerate(g.s["log"][:22]):
            y = r.y + 18 + i * 24
            col = {"good": C["green"], "warn": C["gold"], "bad": C["red"]}.get(e["tone"], C["cyan"])
            pygame.draw.circle(surf, col, (r.x + 24, y + 9), 4)
            draw_text(surf, e["time"], (r.x + 40, y), 13, C["text_mute"])
            draw_text(surf, e["text"][:120], (r.x + 190, y), 14, C["text"])

    def draw_3(self, surf):
        g = self.game
        draw_text(surf, "AJANS ADI", (40, TOPBAR_H + 180), 14, C["text_dim"], bold=True)
        draw_text(surf, "DİL", (980, TOPBAR_H + 180), 14, C["text_dim"], bold=True)
        draw_text(surf, "GÖRÜNTÜ KALİTESİ", (980, TOPBAR_H + 316), 14, C["text_dim"], bold=True)
        draw_paragraph(surf, i18n.QUALITY_LABEL.get(i18n.PREFS.get("quality"), ("", ""))[1],
                       (980, TOPBAR_H + 404), 520, 14, C["text"], max_lines=4)
        draw_text(surf, "SİNEMATİK EFEKTLER", (540, TOPBAR_H + 516), 14, C["text_dim"], bold=True)
        draw_paragraph(surf, "Işık huzmeleri, süzülen toz, renkli kenar ışığı, mürekkep çizgileri, fırça dokusu ve kenar "
                             "yumuşatma. Yavaş bilgisayarlarda kapatabilirsin.", (980, TOPBAR_H + 520), 520, 13,
                       C["text_dim"])
        draw_text(surf, f"Kayıt dosyası: {SAVE_FILE}", (40, H - 130), 12, C["text_mute"])
        draw_text(surf, "Oyun otomatik kaydedilir: her fırlatma, koloni, araştırma, NOVA seviyesi ve ajans adı.",
                  (40, H - 108), 13, C["text_dim"])
