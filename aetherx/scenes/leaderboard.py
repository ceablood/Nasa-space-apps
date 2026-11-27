# -*- coding: utf-8 -*-
"""
SIRALAMA — canlı skor tablosu: skor · para · kademe.
Çevrimiçi sunucu ayarlıysa (AYARLAR > OYUN) tablo 20 saniyede bir yenilenir ve skorun otomatik gönderilir;
değilse bu cihazdaki kampanyalar sıralanır.
"""
import time

import pygame

from . import Scene
from .. import online as ON
from ..config import C, H, W
from ..fx import draw_glow, scale_color
from ..i18n import tr
from ..ui import Button, chip, draw_icon, draw_text, glass_panel, fmt_num

SORTS = [("score", "SKOR"), ("money", "PARA"), ("level", "SEVİYE")]
MEDAL = {1: (255, 210, 80), 2: (210, 216, 226), 3: (214, 140, 80)}


class LeaderboardScene(Scene):
    title = "SIRALAMA"
    title_icon = "trophy"
    accent = C["gold"]

    def __init__(self, app):
        super().__init__(app)
        self.ensure_bg("violet", 71, 0.7)
        self.sort = "score"
        self.rows = []
        self.source = "local"
        self.msg = ""
        self.next_poll = 0.0
        self.my_rank = None
        self.back = "base"

    def enter(self, back=None, **kw):
        if back:
            self.back = back
        elif not self.game.s:
            self.back = "intro"
        if self.game.s:
            ON.local_update(self.game)
        self.next_poll = 0.0
        self.load_local()
        self.rebuild()

    def rebuild(self):
        self.widgets = []
        for i, (k, lab) in enumerate(SORTS):
            b = self.add(Button((40 + i * 190, 168, 180, 46), lab, (lambda k=k: self.set_sort(k)), accent=C["gold"], size=15, style="tab"))
            b.selected = k == self.sort
        self.add(Button((W - 600, 168, 260, 46), "YENİLE", self.refresh, accent=C["cyan"], icon="play", size=15))
        sb = self.add(Button((W - 330, 168, 290, 46), "SKORUMU GÖNDER", self.submit, accent=C["gold"], icon="trophy", size=15,
                             style="gold"))
        sb.set_enabled(bool(self.game.s and ON.server_url()), "Önce AYARLAR'dan sunucu adresi gir" if self.game.s else "Açık kampanya yok")
        self.add(Button((24, H - 70, 170, 48), "GERİ", lambda: self.app.go(self.back), icon="arrow_left", accent=C["text_dim"],
                        size=17, hotkey=pygame.K_ESCAPE))
        self.add(Button((W - 330, H - 70, 290, 48), "SUNUCU AYARI", lambda: self.app.go("settings", cat="game", back="leaderboard"),
                        accent=C["violet"], icon="settings", size=14))

    def set_sort(self, k):
        self.sort = k
        self.next_poll = 0.0
        if self.source == "local":
            self.load_local()
        self.rebuild()

    def load_local(self):
        self.rows = ON.sorted_rows(ON.local_load(), self.sort)
        self.source = "local"

    def refresh(self):
        self.next_poll = 0.0

    def submit(self):
        if self.game.s and ON.ONLINE.submit(self.game):
            self.msg = tr("Skor gönderiliyor…")

    def update(self, dt):
        super().update(dt)
        ON.ONLINE.update()
        res = ON.ONLINE.result
        if res:
            ON.ONLINE.result = None
            kind, data = res
            if kind == "list" and isinstance(data, dict) and data.get("ok"):
                self.rows = data.get("scores", [])
                self.total = data.get("total", len(self.rows))
                self.source = "online"
                self.msg = ""
            elif kind == "submit" and isinstance(data, dict) and data.get("ok"):
                self.my_rank = data.get("rank")
                self.msg = tr("Skor gönderildi · sıran: {0} / {1}").format(data.get("rank"), data.get("total"))
                self.next_poll = 0.0
        if ON.ONLINE.error and not ON.ONLINE.busy:
            self.msg = tr("Sunucuya ulaşılamadı") + f": {ON.ONLINE.error}"
            ON.ONLINE.error = None
            self.load_local()
        if ON.server_url() and not ON.ONLINE.busy and time.time() > self.next_poll:
            self.next_poll = time.time() + 20                       # canlı: 20 sn'de bir yenile
            if self.game.s and not getattr(self, "_sent", False):
                self._sent = True
                ON.ONLINE.submit(self.game)                         # açılışta skoru otomatik gönder
            else:
                ON.ONLINE.fetch(self.sort)

    def draw(self, surf):
        self.bg.draw(surf)
        online = ON.server_url()
        self.draw_title(surf, sub=(tr("Çevrimiçi") + " · " + online) if online else tr("Bu cihaz · çevrimiçi için AYARLAR'dan sunucu adresi gir"))
        r = pygame.Rect(40, 228, W - 80, H - 228 - 90)
        glass_panel(surf, r, C["gold"], 185, 18)
        live = self.source == "online"
        chip(surf, (r.right - 20, r.y + 16), "CANLI SIRALAMA" if live else "BU CİHAZ", C["green"] if live else C["text_dim"], 12, anchor="topright")
        if live:
            draw_glow(surf, (r.right - 130, r.y + 26), 10, C["green"], 0.4 + 0.3 * abs((self.t * 2) % 2 - 1))
        heads = (("#", 30), ("AJANS", 110), ("SKOR", 640), ("PARA", 860), ("SEVİYE", 1060), ("KOLONİ", 1240))
        for t_, x in heads:
            draw_text(surf, t_, (r.x + x, r.y + 20), 13, C["text_dim"], bold=True)
        me = self.game.s and ON.campaign_id(self.game)
        y = r.y + 54
        for i, row in enumerate(self.rows[:14]):
            rank = i + 1
            mine = row.get("id") == me
            rr = pygame.Rect(r.x + 14, y - 6, r.w - 28, 36)
            if mine:
                pygame.draw.rect(surf, (60, 50, 16), rr, border_radius=8)
                pygame.draw.rect(surf, C["gold"], rr, 2, border_radius=8)
            elif i % 2 == 0:
                pygame.draw.rect(surf, (16, 20, 38), rr, border_radius=8)
            mc = MEDAL.get(rank)
            if mc:
                pygame.draw.circle(surf, mc, (r.x + 40, y + 12), 13)
                draw_text(surf, str(rank), (r.x + 40, y + 12), 14, (30, 20, 6), bold=True, anchor="center", raw=True)
            else:
                draw_text(surf, str(rank), (r.x + 40, y + 12), 15, C["text_dim"], bold=True, anchor="center", raw=True)
            col = tuple(row.get("color", (62, 230, 255)))[:3]
            pygame.draw.circle(surf, col, (r.x + 92, y + 12), 7)
            draw_text(surf, row.get("name", "?") + ("  (" + tr("sen") + ")" if mine else ""), (r.x + 110, y + 2), 17,
                      C["gold"] if mine else C["text"], bold=True, raw=True, max_w=500)
            for k, x in (("score", 640), ("money", 860)):
                draw_text(surf, fmt_num(row.get(k, 0)), (r.x + x, y + 2), 17, C["gold"] if k == self.sort else C["text"], bold=k == self.sort,
                          raw=True)
            draw_text(surf, str(row.get("level", 1)), (r.x + 1060, y + 2), 17, C["gold"] if self.sort == "level" else C["text"], raw=True)
            draw_text(surf, str(row.get("colonies", 0)), (r.x + 1240, y + 2), 17, C["text"], raw=True)
            y += 40
        if not self.rows:
            draw_text(surf, "Henüz kayıt yok. Bir kampanya başlat ya da sunucuya bağlan.", (r.centerx, r.centery), 18, C["text_dim"],
                      anchor="center")
        if self.game.s:
            draw_text(surf, tr("Senin skorun") + f": {fmt_num(ON.score_of(self.game))}", (r.x + 20, r.bottom - 34), 15, C["gold"], bold=True, raw=True)
        draw_text(surf, "Skor = seviye×1000 + para/10 + koloni×2000 + başarım×300 + başarılı görev×150 + koloni seviyesi×500",
                  (r.right - 20, r.bottom - 32), 12, C["text_mute"], anchor="topright")
        if self.msg:
            draw_text(surf, self.msg, (W // 2, H - 60), 14, C["cyan"], anchor="center", raw=True)
        self.draw_widgets(surf)
