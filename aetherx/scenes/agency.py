# -*- coding: utf-8 -*-
"""
AJANS: genel durum, diplomasi (NASA, ESA, JAXA, ISRO, TUA), günlük ve
ayarlar (ajans adını 500 Para'ya değiştirme, ses, müzik, tam ekran, kayıt).
"""
import math

import pygame

from . import Scene
from .. import data as D
from ..config import C, H, RENAME_COST, TOPBAR_H, W, SAVE_FILE
from ..fx import draw_glow, scale_color
from ..ui import (Button, Tabs, TextInput, chip, draw_bar, draw_icon, draw_paragraph, draw_text,
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
        self.add(Tabs((40, TOPBAR_H + 100, 1020, 46), ["GENEL", "DİPLOMASİ", "GÜNLÜK", "AYARLAR", "DAHA FAZLA"], self.set_tab,
                      C["violet"], self.tab, ["flag", "handshake", "chart", "settings", "star"]))
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
            x = 40
            self.name_input = self.add(TextInput((x, TOPBAR_H + 210, 560, 64), g.name, "Yeni ajans adı", 28,
                                                 on_submit=lambda t: self.rename(), accent=g.color, size=26))
            self.name_input.active = False
            rb = self.add(Button((x + 580, TOPBAR_H + 212, 280, 60), f"ADI DEĞİŞTİR · {RENAME_COST} P", self.rename,
                                 accent=C["gold"], icon="flag", size=15))
            rb.set_enabled(g.money >= RENAME_COST, f"{RENAME_COST} Para gerekli")
            self.add(Button((x, TOPBAR_H + 330, 560, 64), "TÜM AYARLAR", lambda: self.app.go("settings", back="agency"),
                            accent=C["violet"], icon="settings", size=19, style="big"))
            for i, (cat, lab, ic) in enumerate((("gfx", "GÖRÜNTÜ", "eye"), ("audio", "SES", "nova"),
                                                 ("access", "ERİŞİLEBİLİRLİK", "astro"), ("lang", "DİL", "planet"))):
                self.add(Button((x + (i % 2) * 284, TOPBAR_H + 410 + (i // 2) * 58, 276, 50), lab,
                                (lambda c=cat: self.app.go("settings", cat=c, back="agency")), accent=C["violet"], icon=ic,
                                size=14, style="tab"))
            self.add(Button((x + 640, TOPBAR_H + 510, 360, 50), "SIRALAMA", lambda: self.app.go("leaderboard", back="agency"),
                            accent=C["gold"], icon="trophy", size=15, style="gold"))
            self.add(Button((x + 640, TOPBAR_H + 330, 360, 50), "ŞİMDİ KAYDET", self.save_now, accent=C["green"],
                            icon="save", size=15))
            self.add(Button((x + 640, TOPBAR_H + 390, 360, 50), "ANA MENÜYE DÖN", self.to_menu, accent=C["cyan"],
                            icon="home", size=15))
            db = self.add(Button((x + 640, TOPBAR_H + 450, 360, 50),
                                 "EMİN MİSİN? TEKRAR TIKLA" if self.confirm_delete else "KAYDI SİL", self.delete,
                                 accent=C["red"], icon="cross", size=15, style="danger"))
            db.pulse = self.confirm_delete

    # ---------------------------------------------------------------- eylemler
    def rename(self):
        new = self.name_input.text.strip() if self.name_input else ""
        if self.act(self.game.rename, new, ok_sound="success"):
            self.app.say(f"Merhaba {self.game.name}! Yeni adın tabelada, roketlerde ve bayraklarda.", "happy")

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

    # ----------------------------------------------------------------- 3B ajans merkezi (Dünya)
    _EARTH = {"frames": [], "halo": None}
    N_EARTH = 60

    @staticmethod
    def _build_earth(n_max, chunk):
        import numpy as np
        from .. import space3d as S3
        E = AgencyScene._EARTH
        R = 78
        M = S3.rot_z(math.radians(-23.4)) @ S3.rot_x(0.32)
        L = S3.norm3(np.array((-0.62, 0.38, 0.69), dtype=np.float32))
        for _ in range(chunk):
            i = len(E["frames"])
            if i >= n_max:
                break
            E["frames"].append(S3.to_surface(S3.render_body("earth", R, M, L, i * math.tau / n_max, i * 0.5, 512)))
        if E["halo"] is None:
            E["halo"] = S3.atmo_halo("earth", R, L)

    def earth_frame(self):
        """Dönen 3B Dünya: 60 karelik dönüş bir kez hesaplanır ve oynatılır. Masaüstünde arka plan iş parçacığında
        (açılışta takılma yok), tarayıcıda karede 2 kare üretilir. Hazır olana kadar None."""
        E = AgencyScene._EARTH
        if len(E["frames"]) < self.N_EARTH:
            import sys as _sys
            if _sys.platform == "emscripten":
                self._build_earth(self.N_EARTH, 2)
            elif not E.get("thread"):
                import threading
                E["thread"] = threading.Thread(target=self._build_earth, args=(self.N_EARTH, self.N_EARTH), daemon=True)
                E["thread"].start()
        fr = list(E["frames"])
        if not fr:
            return None, None
        k = int(self.t * 6) % self.N_EARTH
        return fr[min(k, len(fr) - 1)], E["halo"]

    def draw_0(self, surf):
        g = self.game
        a = g.s["agency"]
        col = g.color
        r = pygame.Rect(40, TOPBAR_H + 170, 560, 300)
        glass_panel(surf, r, col, 200, 20, strong=True)
        # ajans merkezi: dönen Dünya + seviye halkası + yörüngede ajans roketi
        cx, cy = r.x + 112, r.y + 122
        img, halo = self.earth_frame()
        if halo is not None:
            surf.blit(halo, (cx - halo.get_width() // 2, cy - halo.get_height() // 2))
        if img is not None:
            surf.blit(img, (cx - img.get_width() // 2, cy - img.get_height() // 2))
        else:
            draw_glow(surf, (cx, cy), 90, (90, 150, 255), 0.5)
        xp, need, frac = g.xp_progress()
        ring = pygame.Rect(0, 0, 196, 196)
        ring.center = (cx, cy)
        pygame.draw.arc(surf, (40, 48, 72), ring, 0, math.tau, 4)
        if frac > 0:
            pygame.draw.arc(surf, col, ring, math.pi / 2 - frac * math.tau, math.pi / 2, 5)
        ang = self.t * 0.9
        ox, oy = cx + math.cos(ang) * 108, cy + math.sin(ang) * 40
        if math.sin(ang) < 0:                                   # Dünya'nın arkasındayken sönük
            draw_icon(surf, "rocket", (ox, oy), 14, scale_color(col, 0.45))
        else:
            draw_glow(surf, (ox, oy), 14, col, 0.6)
            draw_icon(surf, "rocket", (ox, oy), 16, col)
        draw_text(surf, "ajans merkezi · Dünya", (cx, r.bottom - 54), 12, C["text_mute"], anchor="midtop")
        tx = r.x + 236
        draw_text(surf, g.name.upper(), (tx, r.y + 34), 28, C["text"], bold=True, glow=col, max_w=r.right - tx - 20)
        draw_text(surf, g.badge(), (tx, r.y + 76), 18, col, bold=True)
        draw_bar(surf, (tx, r.y + 128, r.right - tx - 30, 12), frac, col, label=f"SEVİYE {a['level']}", value=f"{xp}/{need} XP")
        draw_bar(surf, (tx, r.y + 178, r.right - tx - 30, 10), a["rep"] / 100, C["gold"], label="İTİBAR", value=f"{a['rep']}/100")
        draw_text(surf, f"Kuruluş: Gün 1 · Şimdi: {g.time_label()}", (tx, r.bottom - 44), 14, C["text_dim"])
        # istatistikler: görev sonuçları halkası + ikonlu kutular
        st = g.s["stats"]
        r2 = pygame.Rect(630, TOPBAR_H + 170, W - 670, 300)
        glass_panel(surf, r2, C["cyan"], 180, 20)
        dc = (r2.x + 130, r2.y + 132)
        parts = [(st["success"], C["green"]), (st["partial"], C["gold"]), (st["fail"], C["red"])]
        tot = sum(v for v, _ in parts)
        dr = pygame.Rect(0, 0, 170, 170)
        dr.center = dc
        if tot:
            a0 = math.pi / 2
            for v, c in parts:
                if v:
                    a1 = a0 - v / tot * math.tau
                    pygame.draw.arc(surf, c, dr, a1, a0, 16)
                    a0 = a1
            rate = st["success"] / tot * 100
            from .. import i18n as _i18n
            draw_text(surf, _i18n.pct(rate), dc, 34, C["text"], bold=True,
                      anchor="center", raw=True)
            draw_text(surf, "başarı", (dc[0], dc[1] + 26), 13, C["text_dim"], anchor="midtop")
        else:
            pygame.draw.arc(surf, (40, 48, 72), dr, 0, math.tau, 16)
            draw_text(surf, "henüz görev yok", dc, 14, C["text_dim"], anchor="center")
        lx = r2.x + 40
        for i, (lab, v, c) in enumerate((("Başarılı", st["success"], C["green"]), ("Kısmi", st["partial"], C["gold"]),
                                         ("Başarısız", st["fail"], C["red"]))):
            yy = r2.bottom - 64 + i * 18
            pygame.draw.circle(surf, c, (lx + 6, yy + 7), 5)
            draw_text(surf, f"{v}", (lx + 18, yy), 13, C["text"], bold=True, raw=True)
            draw_text(surf, lab, (lx + 50, yy), 13, C["text_dim"])
        tiles = [("rocket", "Fırlatma", st["launches"]), ("dust", "Kırılan asteroit", st["asteroids"]),
                 ("star", "Yıldız Tozu", st["stardust"]), ("camera", "Fotoğraf", st["photos"]),
                 ("satellite", "Kurtarılan uydu", st["rescues"]), ("money", "Toplam kazanç", fmt_num(st["earned"])),
                 ("chart", "Toplam harcama", fmt_num(st["spent"])),
                 ("flask", "Araştırma", f"{len(g.s['research']['done'])}/{len(D.RESEARCH)}"),
                 ("trophy", "Başarım", f"{len(g.s['achievements'])}/{len(D.ACHIEVEMENTS)}")]
        gx0, gw = r2.x + 280, r2.w - 300
        tw_, th_ = (gw - 2 * 12) / 3, 82
        for i, (ic, k, v) in enumerate(tiles):
            tr_ = pygame.Rect(gx0 + (i % 3) * (tw_ + 12), r2.y + 20 + (i // 3) * (th_ + 10), tw_, th_)
            pygame.draw.rect(surf, (12, 18, 34), tr_, border_radius=12)
            pygame.draw.rect(surf, (34, 48, 80), tr_, 1, border_radius=12)
            draw_icon(surf, ic, (tr_.x + 26, tr_.centery), 22, C["cyan"])
            draw_text(surf, str(v), (tr_.x + 52, tr_.y + 14), 24, C["text"], bold=True, raw=True, max_w=tr_.w - 60)
            draw_text(surf, k, (tr_.x + 52, tr_.y + 48), 13, C["text_dim"], max_w=tr_.w - 60)
        # zafer yolu (sıradaki adım nabız gibi atar)
        r3 = pygame.Rect(40, TOPBAR_H + 494, W - 80, 156)
        glass_panel(surf, r3, C["gold"], 180, 20)
        draw_text(surf, "NİHAİ HEDEF: GÜNEŞ SİSTEMİ'Nİ AÇ, JÜPİTER'DE DEV KOLONİYİ KUR", (r3.x + 24, r3.y + 16), 16,
                  C["gold"], bold=True)
        steps = g.victory_progress()
        n = len(steps)
        nxt = next((i for i, (_, ok) in enumerate(steps) if not ok), None)
        for i, (lab, ok) in enumerate(steps):
            x = r3.x + 80 + i * (r3.w - 160) / (n - 1)
            y = r3.y + 82
            if i < n - 1:
                nx = r3.x + 80 + (i + 1) * (r3.w - 160) / (n - 1)
                pygame.draw.line(surf, C["gold"] if ok else (60, 70, 90), (x + 22, y), (nx - 22, y), 3)
            pulse = i == nxt
            if pulse:
                draw_glow(surf, (x, y), 34 + 6 * math.sin(self.t * 4), C["cyan"], 0.45)
            pygame.draw.circle(surf, scale_color(C["gold"], 0.3) if ok else (20, 26, 44), (int(x), y), 22)
            pygame.draw.circle(surf, C["gold"] if ok else (C["cyan"] if pulse else (70, 80, 100)), (int(x), y), 22, 3)
            if ok:
                draw_glow(surf, (x, y), 30, C["gold"], 0.5)
            draw_icon(surf, "check" if ok else ("play" if pulse else "lock"), (x, y), 18,
                      C["white"] if ok else (C["cyan"] if pulse else (90, 100, 125)))
            draw_text(surf, lab, (x, y + 32), 13, C["text"] if (ok or pulse) else C["text_dim"], bold=True, anchor="midtop")
            if pulse:
                draw_text(surf, "SIRADAKİ", (x, y - 44), 11, C["cyan"], bold=True, anchor="midtop")
        # ajans karnesi: gerçek değerlerden
        from .. import online as ON
        r4 = pygame.Rect(40, TOPBAR_H + 662, W - 80, 64)
        glass_panel(surf, r4, C["violet"], 170, 16)
        rows = ON.sorted_rows(ON.local_load(), "score")
        me = ON.campaign_id(g)
        rank = next((i + 1 for i, rw in enumerate(rows) if rw.get("id") == me), None)
        cols_ = sum(1 for c in g.s["colonies"].values() if c)
        items = [("trophy", "Skor", fmt_num(ON.score_of(g)), C["gold"]),
                 ("chart", "Bu cihazda sıra", f"{rank}/{len(rows)}" if rank else "–", C["violet"]),
                 ("money", "Kasa", fmt_num(g.money), C["gold"]), ("rp", "Araştırma puanı", fmt_num(g.rp), C["cyan"]),
                 ("flag", "Koloni", str(cols_), C["green"]), ("astro", "Ekip", f"{len(g.s['crew'])}/{g.crew_cap()}", C["cyan"])]
        cw = r4.w / len(items)
        for i, (ic, lab, val, c) in enumerate(items):
            x = r4.x + i * cw
            if i:
                pygame.draw.line(surf, (40, 48, 80), (x, r4.y + 12), (x, r4.bottom - 12), 1)
            draw_icon(surf, ic, (x + 34, r4.centery), 20, c)
            draw_text(surf, val, (x + 58, r4.y + 10), 20, C["text"], bold=True, raw=True, max_w=cw - 66)
            draw_text(surf, lab, (x + 58, r4.y + 38), 12, C["text_dim"], max_w=cw - 66)

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
        draw_text(surf, "AJANS ADI", (40, TOPBAR_H + 180), 14, C["text_dim"], bold=True)
        draw_paragraph(surf, "Görüntü kalitesi, ses düzeyleri, oyun seçenekleri, erişilebilirlik ve dil artık ayrı AYARLAR "
                             "ekranında. Ana menüden de açılır.", (40, TOPBAR_H + 540), 560, 13, C["text_dim"])
        draw_text(surf, f"Kayıt dosyası: {SAVE_FILE}", (40, H - 130), 12, C["text_mute"])
        draw_text(surf, "Oyun otomatik kaydedilir: her fırlatma, koloni, araştırma, NOVA seviyesi ve ajans adı.",
                  (40, H - 108), 13, C["text_dim"])

    def draw_4(self, surf):
        """DAHA FAZLA: kaynaklar ve eklenemeyenler (6 dilde, lang/t_more.py)."""
        from ..lang import t_more
        rows = [r_[0] for r_ in t_more.ROWS]
        src, lim = rows[6:15], rows[15:]
        top = TOPBAR_H + 170
        hh = H - top - 96
        for i, (title, sub, items, col) in enumerate((("KAYNAKLAR", rows[4], src, C["cyan"]),
                                                       ("EKLENEMEYENLER VE SINIRLAR", rows[5], lim, C["orange"]))):
            r = pygame.Rect(40 + i * ((W - 100) // 2 + 20), top, (W - 100) // 2, hh)
            glass_panel(surf, r, col, 185, 18)
            draw_text(surf, title, (r.x + 22, r.y + 16), 18, col, bold=True)
            draw_paragraph(surf, sub, (r.x + 22, r.y + 44), r.w - 44, 13, C["text_dim"], max_lines=2)
            y = r.y + 82
            for it in items:
                pygame.draw.circle(surf, col, (r.x + 28, y + 9), 4)
                n = draw_paragraph(surf, it, (r.x + 42, y), r.w - 66, 14, C["text"], max_lines=3)
                y += (n if isinstance(n, int) and n > 10 else 40) + 10

