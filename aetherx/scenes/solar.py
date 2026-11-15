# -*- coding: utf-8 -*-
"""
GÜNEŞ SİSTEMİ + GEZEGEN ATLASI

GENEL GÖRÜNÜM: Güneş merkezde; gezegenler Kepler yasalarına göre (eliptik
yörünge, günberide hızlı, gerçek periyot oranları) Güneş'in çevresinde döner.
Yörüngeler, uydu yörüngeleri, asteroit kuşağı, Jüpiter'in Truva kümeleri ve
Kuiper Kuşağı derinlikle birlikte görünür. Her gezegenin yalnızca Güneş'e
bakan yüzü aydınlıktır.

GEZEGEN GÖRÜNÜMÜ: Seçilen gezegen büyük ve dönerek gösterilir; gündüz, gece
ve alacakaranlık kuşakları, uydular ve yörüngeleri, Satürn'ün halkaları ve
halkayı oluşturan kaya parçaları, Dünya'nın yapay uyduları.

Sürükle: kamerayı döndür · Tekerlek: yakınlaş/uzaklaş · Tıkla: seç
"""
import math
import random

import numpy as np
import pygame

from . import Scene
from .. import art
from .. import atlas as A
from .. import i18n
from .. import cinema
from .. import space3d as S3
from ..config import C, H, TOPBAR_H, W
from ..fx import Spring, clamp, draw_glow, ease_out_cubic, scale_color
from ..i18n import pick, tr
from ..ui import UI, Button, chip, draw_icon, draw_paragraph, draw_text, glass_panel, wrap_text, font

CX, CY = 716, 492
VIEW = pygame.Rect(300, TOPBAR_H, 830, H - TOPBAR_H)
CAM_D = 2600.0
# dış merkezlik, günberi boylamı, eğiklik, düğüm boylamı (derece)
ORB = {"mercury": (0.2056, 77.5, 7.0, 48.3), "venus": (0.0068, 131.5, 3.4, 76.7), "earth": (0.0167, 102.9, 0.0, 0.0),
       "mars": (0.0934, 336.0, 1.85, 49.6), "jupiter": (0.0484, 14.7, 1.3, 100.5), "saturn": (0.0542, 92.4, 2.49, 113.7),
       "uranus": (0.0472, 170.9, 0.77, 74.0), "neptune": (0.0086, 44.9, 1.77, 131.8)}
ROLL = {"saturn": -12, "uranus": 80, "earth": -14, "mars": -12, "neptune": -14, "jupiter": -3, "venus": 3}
SYS_MOONS = {"earth": ["moon"], "mars": ["phobos", "deimos"], "jupiter": ["io", "europa", "ganymede", "callisto"],
             "saturn": ["rhea", "titan", "iapetus"], "uranus": ["titania", "oberon"], "neptune": ["triton"]}
SPEEDS = [0, 1, 5, 25, 100]
YEAR_SEC = 24.0          # 1x hızda Dünya yılı (saniye)
SPIN_T0 = 16.0           # 1 günlük periyodun görsel süresi (saniye)
LIGHT_I = S3.norm3((-0.82, 0.14, 0.55))


def orbit_r(au):
    return 60 + 500 * math.log(au / 0.3) / math.log(30.07 / 0.3)


def vis_omega(period_days):
    """Görsel açısal hız: periyotlar sıkıştırılmış ölçekte (P^0.6), yön korunur."""
    if not period_days:
        return 0.0
    return math.copysign(math.tau / (SPIN_T0 * abs(period_days) ** 0.6), period_days)


def kepler(a, e, m):
    ea = m
    for _ in range(5):
        ea -= (ea - e * math.sin(ea) - m) / (1 - e * math.cos(ea))
    return a * (math.cos(ea) - e), a * math.sqrt(1 - e * e) * math.sin(ea)


class SolarScene(Scene):
    music = "space"
    ambient = "amb_space"
    accent = C["cyan"]
    bubble_x = 416

    def __init__(self, app):
        super().__init__(app)
        self.ensure_bg("deep", 5, 0.55)
        self.mode = "system"
        self.sel = "sun"
        self.moon_sel = None
        self.yaw, self.pitch, self.zoom = 0.5, 0.62, Spring(1.0, 90, 18)
        self.fyaw, self.fpitch, self.fzoom = 0.0, 0.34, Spring(1.0, 90, 18)
        self.focus_k = Spring(0.0, 60, 14)
        self.sim_t = 40.0        # yıl
        self.vt = 0.0            # görsel dönüş zamanı (sn)
        self.speed_i = 1
        self.drag = None
        self.dragged = False
        self.idle = 9.0
        self.hover = None
        self.scroll = 0
        self.pending = None
        self.cache = {}
        self.rocks = {}
        self.screen_pos = {}
        self.moon_pos = []
        self.pending_shown = False
        self.planets = [b for b in A.BODIES if b["key"] != "sun"]
        self.orbit_m, self.paths = {}, {}
        for b in self.planets:
            e, peri, inc, node = ORB[b["key"]]
            m = S3.rot_y(math.radians(node)) @ S3.rot_x(math.radians(inc)) @ S3.rot_y(math.radians(peri - node))
            self.orbit_m[b["key"]] = m
            a = orbit_r(b["au"])
            pts = np.array([(lambda xz: (xz[0], 0.0, xz[1]))(kepler(a, e, k / 128 * math.tau)) for k in range(129)],
                           dtype=np.float32)
            self.paths[b["key"]] = (m @ pts.T).T
        self._build_asteroids()

    # ------------------------------------------------------------ asteroitler
    def _build_asteroids(self):
        rng = np.random.default_rng(77)
        r_in, r_out = orbit_r(2.1), orbit_r(3.3)
        n = 760
        r = rng.uniform(r_in, r_out, n * 2)
        au = 0.3 * np.exp((r - 60) / 500 * math.log(30.07 / 0.3))
        keep = np.ones(len(r), dtype=bool)
        for gap in (2.5, 2.82, 2.95):                       # Kirkwood boşlukları (Jüpiter rezonansları)
            keep &= np.abs(au - gap) > 0.035
        r = r[keep][:n]
        n = len(r)
        th = rng.uniform(0, math.tau, n)
        clump = rng.random(n) < 0.45                         # asteroit aileleri: belirli yerlerde kümelenme
        centers = rng.uniform(0, math.tau, 7)
        th[clump] = centers[rng.integers(0, 7, clump.sum())] + rng.normal(0, 0.16, clump.sum())
        self.belt = {"r": r.astype(np.float32), "th": th.astype(np.float32),
                     "h": rng.normal(0, 5.0, n).astype(np.float32),
                     "w": (math.tau / (au[keep][:n] ** 1.5)).astype(np.float32),
                     "c": rng.integers(90, 190, n), "big": rng.random(n) < 0.12}
        rj = orbit_r(5.203)
        nt = 150
        self.trojans = {"r": (rj + rng.normal(0, 9, nt)).astype(np.float32),
                        "off": (np.where(np.arange(nt) % 2 == 0, 1, -1) * math.pi / 3 + rng.normal(0, 0.17, nt)).astype(np.float32),
                        "h": rng.normal(0, 6, nt).astype(np.float32), "c": rng.integers(80, 160, nt)}
        nk = 320
        self.kuiper = {"r": rng.uniform(orbit_r(30.07) + 26, orbit_r(30.07) + 86, nk).astype(np.float32),
                       "th": rng.uniform(0, math.tau, nk).astype(np.float32),
                       "h": rng.normal(0, 9, nk).astype(np.float32), "c": rng.integers(70, 150, nk)}

    # ------------------------------------------------------------------ giriş
    def enter(self, focus=None, **kw):
        self.rebuild()
        if focus:
            self.set_focus(focus)

    def rebuild(self):
        self.widgets = []
        self.back_button("base", "ÜS")
        y = TOPBAR_H + 20
        b = self.add(Button((24, y, 262, 40), "GENEL GÖRÜNÜM", self.to_system, accent=C["gold"], icon="sun", size=14,
                            style="tab"))
        b.selected = self.mode == "system"
        y += 48
        self.cat_y = []
        for cat, label in A.CATS:
            self.cat_y.append((y, label))
            y += 24
            for body in A.BODIES:
                if body["cat"] != cat:
                    continue
                bt = self.add(Button((24, y, 262, 32), pick(body["name"]).upper(), (lambda k=body["key"]: self.set_focus(k)),
                                     accent=C["cyan"], size=14, style="tab"))
                bt.selected = (self.sel == body["key"] and self.mode == "focus")
                y += 36
            y += 4
        self.list_y = y + 4
        x = VIEW.centerx - 190
        for i, sp in enumerate(SPEEDS):
            bt = self.add(Button((x + i * 76, H - 62, 70, 40), "II" if sp == 0 else f"{sp}x", (lambda j=i: self.set_speed(j)),
                                 accent=C["cyan"], size=14, style="tab"))
            bt.selected = (i == self.speed_i)

    def set_speed(self, i):
        self.speed_i = i
        self.app.audio.play("tick")
        self.rebuild()

    def to_system(self):
        self.mode = "system"
        self.moon_sel = None
        self.focus_k.target = 0.0
        self.app.audio.play("whoosh", 0.4)
        self.rebuild()

    def set_focus(self, key):
        self.sel = key
        self.mode = "focus"
        self.moon_sel = None
        self.scroll = 0
        self.focus_k.snap(0.0)
        self.focus_k.target = 1.0
        self.fzoom.snap(1.0)
        self.fzoom.target = 1.0
        self.cache.pop("ring", None)
        self.cache.pop("planet", None)
        self.idle = 9.0
        th = i18n.quality()["tex"]
        if not S3.has_texture(key, th):
            self.pending = key
        self.app.audio.play("ping", 0.6)
        self.rebuild()

    def body(self):
        return A.BODY[self.sel]

    # ------------------------------------------------------------------- olay
    def handle(self, e):
        if super().handle(e):
            return True
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.mode == "focus" and self.moon_list_rect().collidepoint(e.pos):
                i = (e.pos[1] - self.moon_list_rect().y + self.scroll) // 27
                moons = self.body()["moons"]
                if 0 <= i < len(moons):
                    self.select_moon(moons[int(i)])
                return True
            if VIEW.collidepoint(e.pos):
                self.drag = e.pos
                self.dragged = False
                return True
        if e.type == pygame.MOUSEMOTION and self.drag:
            dx, dy = e.pos[0] - self.drag[0], e.pos[1] - self.drag[1]
            if abs(dx) + abs(dy) > 3:
                self.dragged = True
            if self.dragged:
                self.drag = e.pos
                self.idle = 0.0
                if self.mode == "system":
                    self.yaw += dx * 0.006
                    self.pitch = clamp(self.pitch + dy * 0.004, 0.14, 1.4)
                else:
                    self.fyaw += dx * 0.007
                    self.fpitch = clamp(self.fpitch + dy * 0.004, 0.06, 1.2)
            return True
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.drag:
            self.drag = None
            if not self.dragged:
                self.click(e.pos)
            return True
        if e.type == pygame.MOUSEWHEEL:
            if self.mode == "focus" and self.moon_list_rect().collidepoint(UI.mouse):
                mx = max(0, len(self.body()["moons"]) * 27 - self.moon_list_rect().h)
                self.scroll = int(clamp(self.scroll - e.y * 54, 0, mx))
                return True
            if VIEW.collidepoint(UI.mouse):
                z = self.zoom if self.mode == "system" else self.fzoom
                lim = (0.55, 2.6) if self.mode == "system" else (0.5, 2.3)
                z.target = clamp(z.target * (1.15 ** e.y), *lim)
                self.idle = 0.0
                return True
        if e.type == pygame.KEYDOWN and e.key == pygame.K_BACKSPACE and self.mode == "focus":
            self.to_system()
            return True
        return False

    def click(self, pos):
        if self.mode == "system":
            best = None
            for key, (x, y, r) in self.screen_pos.items():
                d = math.hypot(pos[0] - x, pos[1] - y)
                if d < r + 10 and (best is None or d < best[0]):
                    best = (d, key)
            if best:
                self.set_focus(best[1])
        else:
            best = None
            for key, x, y, r in self.moon_pos:
                d = math.hypot(pos[0] - x, pos[1] - y)
                if d < r + 9 and (best is None or d < best[0]):
                    best = (d, key)
            if best:
                self.select_moon(next(m for m in self.body()["moons"] if m["key"] == best[1]))
            else:
                self.moon_sel = None

    def select_moon(self, m):
        self.moon_sel = m["key"]
        self.app.audio.play("ping", 0.5)

    def moon_list_rect(self):
        return pygame.Rect(24, self.list_y + 26, 262, H - 76 - self.list_y - 26)

    # --------------------------------------------------------------- güncelle
    def update(self, dt):
        super().update(dt)
        sp = SPEEDS[self.speed_i]
        self.sim_t += dt * sp / YEAR_SEC
        self.vt += dt * min(sp, 5)
        self.idle += dt
        for s in (self.zoom, self.fzoom, self.focus_k):
            s.update(dt)
        if abs(self.fzoom.value - self.fzoom.target) > 0.004 or abs(self.zoom.value - self.zoom.target) > 0.004:
            self.idle = 0.0
        for rk in self.rocks.values():
            rk.update(dt * min(sp, 5), 0.9)
        self.hover = None
        if VIEW.collidepoint(UI.mouse) and not self.drag:
            pool = [(k, *v) for k, v in self.screen_pos.items()] if self.mode == "system" else self.moon_pos
            for key, x, y, r in pool:
                if math.hypot(UI.mouse[0] - x, UI.mouse[1] - y) < r + 9:
                    self.hover = key

    # ------------------------------------------------------------ yardımcılar
    def planet_world(self, b):
        e = ORB[b["key"]][0]
        x, z = kepler(orbit_r(b["au"]), e, self.sim_t / b["period"] * math.tau + sum(map(ord, b["key"])) % 628 / 100.0)
        return self.orbit_m[b["key"]] @ np.array((x, 0.0, z), dtype=np.float32)

    def project(self, pts, cam):
        v = (cam @ np.asarray(pts, dtype=np.float32).T).T
        z = self.zoom.value
        persp = CAM_D / (CAM_D - v[..., 2] * z)
        return CX + v[..., 0] * z * persp, CY - v[..., 1] * z * persp, v[..., 2], persp, v

    # ------------------------------------------------------------------ çizim
    def draw(self, surf):
        self.bg.draw(surf, 0.75)
        k = clamp(self.focus_k.value, 0, 1)
        if self.pending:
            if self.pending_shown:                                # mesaj ekrana çıktıktan sonra üret
                S3.texture(self.pending, i18n.quality()["tex"])
                self.pending, self.pending_shown = None, False
            else:
                self.draw_panels(surf)
                draw_text(surf, "Yüksek çözünürlüklü doku hazırlanıyor...", (CX, CY), 22, C["white"], bold=True,
                          anchor="center")
                self.pending_shown = True
                return
        if self.mode == "system" or k < 0.98:
            self.draw_system(surf, 1 - k)
        if self.mode == "focus":
            self.draw_focus(surf, k)
        # sinematik: güneşten huzmeler, süzülen toz, renk uyumu (yalnızca görüntü alanında)
        if self.mode == "system" and "sun" in getattr(self, "screen_pos", {}):
            sx, sy, sr = self.screen_pos["sun"]
            cinema.god_rays(surf, (sx, sy), (255, 190, 120), 0.32, size=int(max(600, sr * 30)), t=self.t, clip=VIEW)
        elif self.mode == "focus":
            Lf = LIGHT_I
            cinema.god_rays(surf, (CX - Lf[0] * -700 - 520, CY - 420), (255, 210, 160), 0.18, size=1600, t=self.t, clip=VIEW)
        cinema.motes(surf, VIEW, self.t, 35, (190, 210, 255), strength=0.7)
        cinema.grade(surf, VIEW)
        self.draw_panels(surf)

    # ------------------------------------------------------------- genel görünüm
    def draw_system(self, surf, alpha):
        if alpha < 0.03:
            return
        cam = S3.rot_x(self.pitch) @ S3.rot_y(self.yaw)
        zf = self.zoom.value ** 0.6
        t = self.vt
        # yörüngeler
        for b in self.planets:
            sx, sy, vz, pr, _ = self.project(self.paths[b["key"]], cam)
            sx, sy, vz = sx.tolist(), sy.tolist(), vz.tolist()
            hov = self.hover == b["key"]
            for i in range(128):
                kk = 0.34 + 0.3 * clamp(float(vz[i]) / 500 + 0.5, 0, 1)
                col = scale_color((120, 170, 255) if not hov else C["gold"], kk * alpha * (1.5 if hov else 1))
                pygame.draw.line(surf, col, (sx[i], sy[i]), (sx[i + 1], sy[i + 1]), 2 if hov else 1)
        # asteroit kümeleri
        self.draw_rocks_sys(surf, cam, alpha)
        # cisimler (derinlik sıralı)
        items = [("sun", np.zeros(3, dtype=np.float32), A.BODY["sun"])]
        jup = None
        for b in self.planets:
            w = self.planet_world(b)
            items.append((b["key"], w, b))
            if b["key"] == "jupiter":
                jup = w
        self.jup_ang = math.atan2(jup[2], jup[0])
        proj = []
        for key, w, b in items:
            sx, sy, vz, pr, v = self.project(w, cam)
            proj.append((float(vz), key, float(sx), float(sy), float(pr), v, b))
        proj.sort()
        self.screen_pos = {}
        for vz, key, sx, sy, pr, v, b in proj:
            R = max(3, int(b["R"] * zf * pr))
            if not (-80 < sx < W + 80 and -80 < sy < H + 80):
                continue
            self.screen_pos[key] = (sx, sy, R)
            if key == "sun":
                draw_glow(surf, (sx, sy), R * 2.6, (255, 150, 50), 0.34 * alpha)        # güneş: daha az parlak
                draw_glow(surf, (sx, sy), R * 1.5, (255, 214, 140), 0.42 * alpha)
                img = S3.render_body("sun", R, cam, (0, 0, 1), t * 0.05, t, 128, emissive=True)
                self.blit_arr(surf, img, sx, sy, alpha)
            else:
                L = S3.norm3(-v)
                m = cam @ S3.rot_z(math.radians(b["tilt"] if b["tilt"] <= 90 else 180 - b["tilt"]))
                spin = t * vis_omega(b["rot"] / 24.0)
                ring = b["ring"] if b["ring"] in ("saturn", "uranus") and R >= 6 else None
                rl = S3.render_ring(ring, R, m, L, b["obl"]) if ring else None
                if rl:
                    self.blit_arr(surf, rl[0], sx, sy, alpha)
                img = S3.render_body(key, R, m, L, spin, t, 128, ring=ring, obl=b["obl"])
                self.blit_arr(surf, img, sx, sy, alpha)
                if rl:
                    self.blit_arr(surf, rl[1], sx, sy, alpha)
                self.draw_sys_moons(surf, b, sx, sy, R, m, L, alpha)
            hov = self.hover == key
            if hov:
                pygame.draw.circle(surf, C["gold"], (int(sx), int(sy)), R + 9, 1)
            draw_text(surf, pick(b["name"]), (sx, sy + R + (10 if key != "saturn" else R * 0.6 + 8)), 14 if not hov else 16,
                      C["white"], bold=True, anchor="midtop", alpha=int(255 * alpha), raw=True)
        if alpha > 0.6:
            self.draw_sys_labels(surf, cam)

    def blit_arr(self, surf, arr, x, y, alpha=1.0):
        s = S3.to_surface(arr)
        if alpha < 0.97:
            s.set_alpha(int(255 * alpha))
        surf.blit(s, (int(x - arr.shape[1] / 2), int(y - arr.shape[0] / 2)))

    def draw_sys_moons(self, surf, b, sx, sy, R, m, L, alpha):
        names = SYS_MOONS.get(b["key"])
        if not names:
            return
        U, Wv = m[:, 0].tolist(), m[:, 2].tolist()
        for i, name in enumerate(names):
            mo = next(x for x in b["moons"] if x["key"] == name)
            d = R * (1.75 + 0.55 * i) + (R * 1.5 if b["ring"] == "saturn" else 0)
            pts = []
            for k in range(33):
                a = k / 32 * math.tau
                pts.append((sx + d * (math.sin(a) * U[0] + math.cos(a) * Wv[0]),
                            sy - d * (math.sin(a) * U[1] + math.cos(a) * Wv[1])))
            pygame.draw.lines(surf, scale_color((150, 180, 220), 0.4 * alpha), False, pts, 1)
            a = mo["ph"] + self.vt * vis_omega(mo["p"])
            px = sx + d * (math.sin(a) * U[0] + math.cos(a) * Wv[0])
            py = sy - d * (math.sin(a) * U[1] + math.cos(a) * Wv[1])
            pz = d * (math.sin(a) * U[2] + math.cos(a) * Wv[2])
            if pz < 0 and math.hypot(px - sx, py - sy) < R:
                continue
            pygame.draw.circle(surf, scale_color((225, 225, 230), alpha), (int(px), int(py)), 2 if mo["d"] > 2000 else 1)

    def draw_rocks_sys(self, surf, cam, alpha):
        t = self.sim_t
        sets = []
        bl = self.belt
        th = bl["th"] + bl["w"] * t
        sets.append((bl["r"] * np.cos(th), bl["h"], bl["r"] * np.sin(th), bl["c"], bl["big"]))
        tr_ = self.trojans
        ja = getattr(self, "jup_ang", 0.0)
        th = ja + tr_["off"]
        sets.append((tr_["r"] * np.cos(th), tr_["h"], tr_["r"] * np.sin(th), tr_["c"], None))
        ku = self.kuiper
        th = ku["th"] + t * 0.02
        sets.append((ku["r"] * np.cos(th), ku["h"], ku["r"] * np.sin(th), ku["c"], None))
        for x, y, z, c, big in sets:
            sx, sy, vz, pr, _ = self.project(np.stack([x, y, z], axis=1), cam)
            bright = np.clip(0.55 + vz / 900, 0.3, 1.0) * alpha
            ok = (sx > VIEW.x - 300) & (sx < W) & (sy > TOPBAR_H) & (sy < H - 1) & (sx >= 0)
            xi, yi = sx.astype(int), sy.astype(int)
            for i in np.flatnonzero(ok):
                g = int(c[i] * bright[i])
                col = (g, int(g * 0.92), int(g * 0.84))
                if big is not None and big[i]:
                    pygame.draw.circle(surf, col, (int(xi[i]), int(yi[i])), 2)
                else:
                    surf.set_at((int(xi[i]), int(yi[i])), col)

    def draw_sys_labels(self, surf, cam):
        rb = orbit_r(2.7)
        a = -self.yaw + 2.3
        for text, r, ang in (("Asteroit Kuşağı", rb, a), ("Kuiper Kuşağı", orbit_r(30.07) + 56, a + 0.5),
                             ("Truva asteroitleri", orbit_r(5.203), getattr(self, "jup_ang", 0) + math.pi / 3)):
            sx, sy, vz, pr, _ = self.project(np.array((r * math.cos(ang), 0, r * math.sin(ang)), dtype=np.float32), cam)
            sx, sy = float(sx), float(sy)
            if VIEW.collidepoint(sx, sy):
                draw_text(surf, text, (float(sx), float(sy) - 16), 13, C["text_dim"], anchor="midbottom")

    # ------------------------------------------------------------ gezegen görünümü
    def draw_focus(self, surf, k):
        b = self.body()
        key = b["key"]
        t = self.vt
        q = i18n.quality()
        ke = ease_out_cubic(k)
        base_r = 150 if not b["moons"] else 96
        R = int(clamp(base_r * self.fzoom.value * (0.25 + 0.75 * ke), 8, 230))
        moving = self.idle < 0.35
        roll = math.radians(ROLL.get(key, -6))
        M = S3.rot_z(roll) @ S3.rot_x(self.fpitch)
        V = M @ S3.rot_y(self.fyaw)
        L = S3.norm3(V @ LIGHT_I)
        spin = t * vis_omega(b["rot"] / 24.0) + self.fyaw
        obl = b["obl"]
        ring = b["ring"]
        cx, cy = CX, CY
        if key == "sun":
            draw_glow(surf, (cx, cy), R * 2.2, (255, 150, 50), 0.32)
            draw_glow(surf, (cx, cy), R * 1.4, (255, 214, 140), 0.4)
            img = self.cached("planet", (R, round(spin * 30)), 0.08,
                              lambda: S3.to_surface(S3.render_body("sun", R, M, L, t * 0.04 + self.fyaw, t, q["tex"], emissive=True)))
            surf.blit(img, (cx - R, cy - R))
            return
        # ---- halka katmanları -------------------------------------------
        back = front = None
        if ring:
            lod = 3 if (moving and R > 60) else 1
            rkey = (R, round(self.fpitch, 2), tuple(np.round(L, 2)), lod)
            lay = self.cached("ring", rkey, 0.1 if moving else 0.0, lambda: self.make_ring(ring, R, M, L, obl, lod))
            if lay:
                back, front, half = lay
        # ---- uydu konumları ---------------------------------------------
        moons = []
        self.moon_pos = []
        self._labels = []
        ang = {}
        for m in b["moons"]:
            if m.get("lead"):
                a = ang.get(m["lead"][0], 0.0) + m["lead"][1]
            else:
                a = m["ph"] + t * vis_omega(m["p"])
            ang[m["key"]] = a
            inc = math.radians(m.get("inc", 0.0))
            n = m.get("n", 1)
            for j in range(n):
                aj = a + j * math.tau / n
                p = np.array((math.sin(aj), 0.0, math.cos(aj)), dtype=np.float32) * (m["disp"] * R)
                if inc:
                    p = S3.rot_x(inc) @ p
                v = V @ p
                moons.append((float(v[2]), m, float(cx + v[0]), float(cy - v[1]), v, j))
        # ---- yörünge çizgileri -------------------------------------------
        orbit_pts = []
        for m in b["moons"]:
            if m.get("lead"):
                continue
            inc = math.radians(m.get("inc", 0.0))
            a = np.linspace(0, math.tau, 73)
            p = np.stack([np.sin(a), np.zeros_like(a), np.cos(a)], axis=1).astype(np.float32) * (m["disp"] * R)
            if inc:
                p = (S3.rot_x(inc) @ p.T).T
            v = (V @ p.T).T
            orbit_pts.append((m, v))
        self.draw_orbits(surf, orbit_pts, cx, cy, R, False)
        # ---- arka: halka, kayalar, uydular -------------------------------
        if back is not None:
            surf.blit(back, (cx - half, cy - half))
        rocks = self.get_rocks(ring) if ring else None
        rp = rocks.project(R, M, L, self.fyaw, obl) if rocks else None
        if rp:
            self.draw_ring_rocks(surf, rocks, rp, cx, cy, R, False)
        for item in sorted(moons):
            if item[0] < 0:
                self.draw_moon(surf, b, item, cx, cy, R, V, L, t)
        # ---- gezegen ----------------------------------------------------
        interval = clamp(R * R / 90000 * 0.12, 0.0, 0.12)
        pk = (R, round(self.fpitch, 2), round(self.fyaw, 2), i18n.LANG)
        img = self.cached("planet", pk, interval,
                          lambda: S3.to_surface(S3.render_body(key, R, M, L, spin, t, q["tex"], ring=ring if ring in ("saturn", "uranus") else None, obl=obl)),
                          refresh=True)
        surf.blit(img, (cx - R, cy - R))
        # ---- ön: halka, kayalar, yörüngeler, uydular ----------------------
        if front is not None:
            surf.blit(front, (cx - half, cy - half))
        if rp:
            self.draw_ring_rocks(surf, rocks, rp, cx, cy, R, True)
        self.draw_orbits(surf, orbit_pts, cx, cy, R, True)
        for item in sorted(moons):
            if item[0] >= 0:
                self.draw_moon(surf, b, item, cx, cy, R, V, L, t)
        self.draw_labels(surf)

    def cached(self, name, key, interval, fn, refresh=False):
        """Pahalı çizimleri önbellekler; refresh=True ise en geç 'interval' sn'de bir yeniler."""
        c = self.cache.get(name)
        now = self.t
        if c and c[0] == key and (not refresh or now - c[2] < max(interval, 1e-3)):
            return c[1]
        if c and now - c[2] < interval and c[1] is not None and c[0][0] == key[0]:
            return c[1]
        val = fn()
        self.cache[name] = (key, val, now)
        return val

    def make_ring(self, ring, R, M, L, obl, lod):
        lay = S3.render_ring(ring, max(8, R // lod), M, L, obl)
        if not lay:
            return None
        back, front, half = lay
        sb, sf = S3.to_surface(back), S3.to_surface(front)
        if lod > 1:
            half *= lod
            sb = pygame.transform.smoothscale(sb, (half * 2, half * 2))
            sf = pygame.transform.smoothscale(sf, (half * 2, half * 2))
        return sb, sf, half

    def get_rocks(self, ring):
        rk = self.rocks.get(ring)
        if rk is None:
            n = i18n.quality()["rocks"] if ring == "saturn" else 120
            rk = self.rocks[ring] = S3.RingRocks(ring, n)
        return rk

    def draw_ring_rocks(self, surf, rocks, rp, cx, cy, R, front):
        px, py, pz, vis, br = rp
        sc = (R / 100.0) ** 0.8 * 0.72          # gerçek halka parçaları: küçük, yoğun, parlamayan
        sel = np.flatnonzero(vis & ((pz > 0) == front))
        for i in sel:
            x, y = int(cx + px[i]), int(cy + py[i])
            s = rocks.size[i] * sc
            b = float(br[i])
            if s >= 3.0 and b > 0.5 and i % 3 == 0:
                spr = art.asteroid_sprite("ring" if rocks.kind[i] % 2 else "ringice", max(2, int(s)), int(rocks.kind[i]) + int(i) % 7)
                surf.blit(spr, (x - spr.get_width() // 2, y - spr.get_height() // 2))
            else:
                col = tuple(int(clamp(v * b * 0.82, 0, 255)) for v in rocks.col[i])
                if s >= 1.5:
                    pygame.draw.circle(surf, col, (x, y), max(1, int(s * 0.7)))
                elif 0 <= x < W and 0 <= y < H:
                    surf.set_at((x, y), col)

    def draw_orbits(self, surf, orbit_pts, cx, cy, R, front):
        for m, v in orbit_pts:
            v = v.tolist() if hasattr(v, "tolist") else v
            sel = self.moon_sel == m["key"] or self.hover == m["key"]
            base = C["gold"] if sel else ((120, 220, 255) if m["kind"] == "sat" else (170, 190, 225))
            n = len(v) - 1
            for i in range(n):
                zmid = (v[i][2] + v[i + 1][2]) * 0.5
                if (zmid >= 0) != front:
                    continue
                kk = (0.62 if front else 0.28) * (1.5 if sel else 1.0)
                pygame.draw.line(surf, scale_color(base, min(1.0, kk)), (cx + v[i][0], cy - v[i][1]),
                                 (cx + v[i + 1][0], cy - v[i + 1][1]), 2 if sel else 1)

    def draw_moon(self, surf, b, item, cx, cy, R, V, L, t):
        z, m, x, y, v, j = item
        hidden = z < 0 and math.hypot(x - cx, (y - cy) / b["obl"]) < R - 1
        sel = self.moon_sel == m["key"]
        hov = self.hover == m["key"]
        depth = 1 + z / CAM_D * 2.0
        if m["kind"] == "sat":
            r = 5
            if not hidden:
                col = (220, 230, 245)
                pygame.draw.rect(surf, (40, 90, 200), (x - 9, y - 2, 6, 4))
                pygame.draw.rect(surf, (40, 90, 200), (x + 3, y - 2, 6, 4))
                pygame.draw.rect(surf, col, (x - 3, y - 3, 6, 6))
                if (t * 2 + j) % 1 < 0.5:
                    draw_glow(surf, (x, y), 7, (255, 90, 90) if m["key"] != "turksat" else (255, 60, 60), 0.9)
        else:
            r = max(2, int(m["rpx"] * (R / 96.0) ** 0.75 * depth))
            if not hidden:
                pl = float(v[0] * L[0] + v[1] * L[1] + v[2] * L[2])
                perp2 = float(v @ v) - pl * pl
                eclipsed = pl < 0 and perp2 < (R * 0.97) ** 2
                Lm = (0.0, 0.0, -1.0) if eclipsed else L
                spin = math.atan2(v[0], v[2]) + math.pi
                if r >= 3:
                    img = S3.render_body(m["tex"], r, V, Lm, spin + self.fyaw, t, 64 if r < 24 else 128)
                    self.blit_arr(surf, img, x, y)
                else:
                    pygame.draw.circle(surf, (60, 60, 66) if eclipsed else (215, 215, 220), (int(x), int(y)), r)
        self.moon_pos.append((m["key"], x, y, r))
        if hidden:
            return
        if sel or hov:
            pygame.draw.circle(surf, C["gold"], (int(x), int(y)), r + 6, 1)
        big = m["kind"] == "sat" or m.get("d", 0) >= 300
        if (sel or hov or big) and j == 0:
            # etiketler en sonda çizilir: gezegen/uydu üstlerini örtmesin
            self._labels.append((2 if sel else (1 if hov else 0), pick(m["name"]), x, y + r + 6, sel, hov))

    def draw_labels(self, surf):
        placed = []
        for pri, name, x, y, sel, hov in sorted(self._labels, key=lambda a: -a[0]):
            size = 15 if (sel or hov) else 13
            w, h = font(size, sel or hov).size(name)
            rect = pygame.Rect(int(x - w / 2) - 3, int(y) - 1, w + 6, h + 2)
            if pri == 0 and any(rect.colliderect(o) for o in placed):
                continue
            placed.append(rect)
            draw_text(surf, name, (x + 1, y + 1), size, (0, 0, 0), bold=sel or hov, anchor="midtop", raw=True)
            draw_text(surf, name, (x, y), size, C["gold"] if sel else C["white"], bold=sel or hov, anchor="midtop",
                      raw=True)

    # ---------------------------------------------------------------- paneller
    def draw_panels(self, surf):
        g = self.game
        # sol: atlas
        lp = pygame.Rect(12, TOPBAR_H + 8, 286, H - TOPBAR_H - 16)
        pygame.draw.rect(surf, (0, 0, 0), lp, border_radius=16)
        pygame.draw.rect(surf, scale_color(C["cyan"], 0.7), lp, 1, border_radius=16)
        for y, label in self.cat_y:
            draw_text(surf, label, (30, y + 3), 12, C["gold"], bold=True)
        self.draw_widgets(surf)
        if self.mode == "focus" and self.body()["moons"]:
            self.draw_moon_list(surf)
        # sağ: bilgi
        self.draw_info(surf)
        # alt bilgi
        sp = SPEEDS[self.speed_i]
        draw_text(surf, "Sürükle: döndür  ·  Tekerlek: yakınlaş  ·  Tıkla: seç", (VIEW.centerx, H - 84), 13,
                  C["text_dim"], anchor="midbottom")
        if self.mode == "system":
            yr = self.sim_t
            draw_text(surf, f"Yıl {yr:.1f}", (VIEW.x + 16, TOPBAR_H + 14), 16, C["white"], bold=True)
            draw_text(surf, "Yörünge süreleri gerçek oranlardadır (Kepler); uzaklık ve boyutlar ölçeklenmiştir.",
                      (VIEW.x + 16, TOPBAR_H + 40), 12, C["text_dim"])
        else:
            draw_text(surf, "Uzaklıklar ve dönüş süreleri görünürlük için ölçeklenmiştir.",
                      (VIEW.x + 16, TOPBAR_H + 14), 12, C["text_dim"])

    def draw_moon_list(self, surf):
        b = self.body()
        r = self.moon_list_rect()
        n_nat = sum(1 for m in b["moons"] if m["kind"] == "moon")
        title = "UYDULAR" if b["key"] != "earth" else "UYDULAR VE YAPAY UYDULAR"
        draw_text(surf, title, (30, r.y - 22), 12, C["gold"], bold=True)
        draw_text(surf, str(len(b["moons"])), (r.right - 6, r.y - 22), 12, C["white"], bold=True, anchor="topright", raw=True)
        old = surf.get_clip()
        surf.set_clip(r)
        for i, m in enumerate(b["moons"]):
            y = r.y + i * 27 - self.scroll
            if y < r.y - 27 or y > r.bottom:
                continue
            row = pygame.Rect(r.x, y, r.w - 8, 25)
            sel = self.moon_sel == m["key"]
            hov = row.collidepoint(UI.mouse) and r.collidepoint(UI.mouse)
            if sel or hov:
                pygame.draw.rect(surf, scale_color(C["gold"] if sel else C["cyan"], 0.3), row, border_radius=6)
                pygame.draw.rect(surf, C["gold"] if sel else C["cyan"], row, 1, border_radius=6)
            if hov:
                self.hover = m["key"]
            draw_icon(surf, "satellite" if m["kind"] == "sat" else "planet", (row.x + 14, row.centery), 13,
                      (120, 220, 255) if m["kind"] == "sat" else C["white"])
            draw_text(surf, pick(m["name"]), (row.x + 30, row.centery), 14, C["white"], bold=sel, anchor="midleft", raw=True)
            if m["kind"] == "moon":
                draw_text(surf, f"{m['d']:,} km".replace(",", "."), (row.right - 6, row.centery), 12, C["text_dim"],
                          anchor="midright", raw=True)
        surf.set_clip(old)
        total = len(b["moons"]) * 27
        if total > r.h:
            th = r.h * r.h / total
            ty = r.y + (r.h - th) * self.scroll / (total - r.h)
            pygame.draw.rect(surf, C["cyan"], (r.right - 4, ty, 3, th), border_radius=2)

    def draw_info(self, surf):
        b = self.body()
        m = next((x for x in b["moons"] if x["key"] == self.moon_sel), None) if self.mode == "focus" else None
        r = pygame.Rect(W - 462, TOPBAR_H + 8, 450, H - TOPBAR_H - 16)
        pygame.draw.rect(surf, (0, 0, 0), r, border_radius=16)                       # siyah zemin
        acc = C["gold"] if m else C["cyan"]
        pygame.draw.rect(surf, acc, r, 2, border_radius=16)
        x, y, w = r.x + 22, r.y + 18, r.w - 44
        if self.mode == "system":
            b = A.BODY[self.hover] if self.hover in A.BODY else A.BODY[self.sel if self.sel in A.BODY else "sun"]
        if m:
            draw_text(surf, pick(b["name"]).upper() + "  >", (x, y), 13, C["text_dim"], bold=True, raw=True)
            y += 20
            draw_text(surf, pick(m["name"]), (x, y), 32, C["white"], bold=True, raw=True, max_w=w)
            y += 44
            chip(surf, (x, y), "YAPAY UYDU" if m["kind"] == "sat" else "DOĞAL UYDU", acc, 13)
            y += 36
            facts, info = A.moon_facts(m), m["info"]
        else:
            draw_text(surf, pick(b["name"]), (x, y), 34, C["white"], bold=True, raw=True)
            y += 48
            chip(surf, (x, y), dict(A.CATS)[b["cat"]], acc, 13)
            y += 36
            facts, info = b["facts"], b["info"]
        for lab, val in facts:
            draw_text(surf, lab, (x, y), 16, C["white"])
            draw_text(surf, pick(val), (x + w, y), 16, C["white"], bold=True, anchor="topright", raw=True, max_w=w - 170)
            pygame.draw.line(surf, (46, 52, 66), (x, y + 25), (x + w, y + 25))
            y += 30
        y += 8
        h = draw_paragraph(surf, pick(info), (x, y), w, 17, C["white"], gap=7, raw=True)
        y += h + 12
        if not m and self.mode == "focus" and b["moons"]:
            draw_text(surf, "Bir uydu seçmek için soldaki listeyi veya görünümü kullan.", (x, min(y, r.bottom - 34)),
                      13, C["gold"], max_w=w)
        elif self.mode == "system":
            draw_text(surf, "Yakından görmek için gezegene tıkla.", (x, min(y, r.bottom - 34)), 13, C["gold"], max_w=w)
