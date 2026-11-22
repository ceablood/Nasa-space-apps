# -*- coding: utf-8 -*-
"""
AETHER-X // 3B SÜRÜŞ ÇİZİCİSİ (numpy, pygame; tarayıcıda da çalışır)

Arazi: yükseklik haritası ışın yürütme (voxel space). Her ekran sütunu için kameradan uzaklaşan derinlik
katmanlarında yükseklik ve renk örneklenir, ekran yüksekliğine izdüşürülür; "en yakın kapatan" kuralı
kümülatif minimumla, satır -> katman eşlemesi aramayla bulunur (sütun başına vektörel). Sonuç ayrıca bir
derinlik tamponu verir: araç, kaya, iz ve parçacıklar araziye göre doğru örtülür.
Nesneler (araç gövdesi, tekerlekler, süspansiyon, direk, panel, kayalar): dünya -> kamera -> ekran izdüşümü,
arka yüz ayıklama, Lambert gölgeleme, ressam algoritması.
"""
import math

import numpy as np
import pygame

F32 = np.float32


class Camera:
    def __init__(self):
        self.x = self.y = 0.0
        self.z = 3.0
        self.yaw = 0.0          # bakış yönü (rad), dünya xy
        self.pitch = -0.12      # aşağı bakış (rad)
        self.roll = 0.0
        self.fov = math.radians(70)
        self.shake = (0.0, 0.0)

    def basis(self):
        f = (math.cos(self.yaw), math.sin(self.yaw))
        r = (math.sin(self.yaw), -math.cos(self.yaw))
        return f, r


class TerrainRenderer:
    def __init__(self, terrain, w=480, h=270, layers=200, far=520.0):
        self.t = terrain
        self.resize(w, h, layers, far)
        p = terrain.p
        self.sky_top, self.sky_bot = p["sky"]
        self.fog = p["fog"]
        self.visibility = 1.0
        self.light_on = False
        self._stars = None
        if terrain.planet == "moon":
            rng = np.random.default_rng(5)
            self._stars = (rng.uniform(0, 2 * math.pi, 700), rng.uniform(0, 1, 700) ** 1.5, rng.integers(110, 255, 700))

    def resize(self, w, h, layers, far):
        self.w, self.h, self.L, self.far = w, h, layers, far
        near = 1.2
        k = np.linspace(0, 1, layers, dtype=F32)
        self.depths = (near * (far / near) ** k).astype(F32)          # yakında sık, uzakta seyrek
        self.rows = np.arange(h, dtype=F32)

    # ----------------------------------------------------------------- arazi
    def render(self, cam, fog_dist=None):
        w, h, L = self.w, self.h, self.L
        focal = (w / 2) / math.tan(cam.fov / 2)
        self.focal = focal
        horizon = h / 2 + math.tan(cam.pitch) * focal        # aşağı bakınca ufuk yukarı kayar
        self.horizon = horizon
        f, r = cam.basis()
        u = (np.arange(w, dtype=F32) - w / 2) / focal                 # sütun başına yatay ışın eğimi
        dirx = f[0] + u * r[0]
        diry = f[1] + u * r[1]
        d = self.depths[:, None]
        px = cam.x + dirx[None, :] * d
        py = cam.y + diry[None, :] * d
        hs = self.t.heights(px, py)
        sy = horizon - (hs - cam.z) * focal / d                          # (L, W) ekran satırı
        n, c = self.t.n, self.t.cell
        ii = np.mod((px / c).astype(np.int32), n)
        jj = np.mod((py / c).astype(np.int32), n)
        col = self.t.color[jj, ii].astype(F32)                           # (L, W, 3)
        # yakın plan ayrıntı: ince taneli parlaklık değişimi (doku), uzakta sis/pus
        fine = (np.sin(px * 3.1) * np.sin(py * 2.7) * 0.06 + 1.0)[..., None]
        near_k = np.clip(1 - d / 40.0, 0, 1)[..., None]
        col = col * (1 + (fine - 1) * near_k)
        fd = fog_dist if fog_dist else self.far
        if self.fog is not None or fog_dist:
            fogc = np.array(self.fog or (0, 0, 0), dtype=F32)
            fk = np.clip((d / fd) ** 1.3, 0, 1)[..., None]
            col = col * (1 - fk) + fogc * fk
        if self.light_on:          # farlar: ileri yöndeki yakın zemini aydınlatır
            beam = np.clip(1 - np.abs(u)[None, :] / 0.55, 0, 1) * np.clip(1 - d / 45.0, 0, 1)
            col = col + (beam[..., None] * np.array((150, 145, 130), dtype=F32))
        ymin = np.minimum.accumulate(np.clip(sy, -1, h + 1), axis=0)     # (L, W) kümülatif kapatma
        self.ymin = ymin
        # satır -> ilk kapatan katman (sütun başına arama); L = gökyüzü
        neg = -ymin
        idx = np.empty((h, w), dtype=np.int32)
        rows = -self.rows
        for x in range(w):
            idx[:, x] = np.searchsorted(neg[:, x], rows, side="left")
        sky = idx >= L
        idxc = np.minimum(idx, L - 1)
        img = col[idxc, np.arange(w)[None, :]]
        img[sky] = self._sky(cam, horizon)[sky]
        self.depth_rows = idx
        arr = np.clip(img, 0, 255).astype(np.uint8)
        return pygame.surfarray.make_surface(arr.transpose(1, 0, 2))

    def _sky(self, cam, horizon):
        h, w = self.h, self.w
        t = np.clip((self.rows - (horizon - h * 0.9)) / (h * 0.9), 0, 1)[:, None]
        top, bot = np.array(self.sky_top, dtype=F32), np.array(self.sky_bot, dtype=F32)
        sky = top + (bot - top) * t[..., None]
        sky = np.broadcast_to(sky, (h, w, 3)).copy()
        if self.visibility < 1 and self.fog:
            sky = sky * self.visibility + np.array(self.fog, dtype=F32) * (1 - self.visibility)
        if self._stars is not None:          # Ay: atmosfer yok -> gündüz de yıldızlar
            ang, el, br = self._stars
            rel = (ang - cam.yaw + math.pi) % (2 * math.pi) - math.pi
            x = (w / 2 - np.tan(np.clip(rel, -1.2, 1.2)) * self.focal).astype(np.int32)
            y = (horizon - el * h * 1.2).astype(np.int32)
            ok = (np.abs(rel) < cam.fov / 2) & (x >= 0) & (x < w) & (y >= 0) & (y < h)
            sky[y[ok], x[ok]] = br[ok, None]
        return sky

    # ---------------------------------------------------------------- izdüşüm
    def project(self, cam, P):
        """P: (N,3) dünya -> (sx, sy, derinlik)."""
        f, r = cam.basis()
        rx, ry, rz = P[:, 0] - cam.x, P[:, 1] - cam.y, P[:, 2] - cam.z
        dep = rx * f[0] + ry * f[1]
        lat = rx * r[0] + ry * r[1]
        dd = np.maximum(dep, 0.05)
        sx = self.w / 2 + lat / dd * self.focal
        sy = self.horizon - rz / dd * self.focal
        return sx, sy, dep

    def visible(self, sx, sy, dep):
        """Arazi derinlik tamponuna göre görünürlük (noktasal)."""
        x = np.clip(sx.astype(np.int32), 0, self.w - 1)
        y = np.clip(sy.astype(np.int32), 0, self.h - 1)
        li = np.searchsorted(self.depths, dep) - 1                       # bu derinlikten yakın son katman
        li = np.clip(li, -1, self.L - 1)
        ybuf = np.where(li >= 0, self.ymin[np.maximum(li, 0), x], self.h + 1)
        inside = (sx >= 0) & (sx < self.w) & (sy >= -50) & (sy < self.h + 50) & (dep > 0.3)
        return inside & (y < ybuf)


# ===================================================================== modeller
def rot(yaw, pitch, roll):
    cy, sy, cp, sp, cr, sr = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch), math.cos(roll), math.sin(roll)
    Rz = np.array(((cy, -sy, 0), (sy, cy, 0), (0, 0, 1)), dtype=F32)
    Ry = np.array(((cp, 0, sp), (0, 1, 0), (-sp, 0, cp)), dtype=F32)
    Rx = np.array(((1, 0, 0), (0, cr, -sr), (0, sr, cr)), dtype=F32)
    return Rz @ Ry @ Rx


def box(cx, cy, cz, lx, ly, lz):
    xs, ys, zs = (cx - lx / 2, cx + lx / 2), (cy - ly / 2, cy + ly / 2), (cz - lz / 2, cz + lz / 2)
    V = [(x, y, z) for x in xs for y in ys for z in zs]
    F = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return V, F


class VehicleModel:
    """Araç türüne göre gövde parçaları (gövde çerçevesinde, metre): kutular + yüzeyler + renkler."""

    def __init__(self, spec):
        s = spec
        self.spec = s
        parts = []
        L, T, H = s.wheelbase + 0.6, s.track - 0.25, max(0.35, s.cg_h * 0.6)
        base_z = s.clearance - (s.cg_h) + H / 2        # ağırlık merkezi = 0 düzlemi
        col = s.color
        if s.key == "lrv":       # açık şasi: düz platform, iki koltuk, konsol, şemsiye anten
            parts += [(box(0, 0, base_z, L, T, 0.12), (150, 150, 156)),
                      (box(0.2, -0.38, base_z + 0.35, 0.45, 0.45, 0.6), (70, 70, 76)),
                      (box(0.2, 0.38, base_z + 0.35, 0.45, 0.45, 0.6), (70, 70, 76)),
                      (box(0.75, 0, base_z + 0.45, 0.25, 0.7, 0.5), (190, 165, 90)),
                      (box(-0.9, 0, base_z + 0.25, 0.6, 1.1, 0.35), (205, 180, 100)),
                      (box(-0.9, 0, base_z + 1.25, 0.05, 0.05, 1.6), (180, 180, 186)),
                      (box(-0.9, 0, base_z + 2.05, 0.9, 0.9, 0.04), (220, 220, 226))]
        elif s.key in ("sev", "mars_rover"):     # basınçlı kabin: büyük gövde, cam, panel, kapı
            parts += [(box(0.1, 0, base_z + 0.55, L, T, 1.6), col),
                      (box(L / 2 - 0.05, 0, base_z + 0.95, 0.12, T * 0.85, 0.7), (40, 70, 96)),
                      (box(-0.2, 0, base_z + 1.42, L * 0.7, T * 1.25, 0.05), (36, 52, 110)),
                      (box(L / 2 - 0.4, T / 2 + 0.02, base_z + 0.55, 0.5, 0.04, 1.0), (120, 124, 132)),
                      (box(-L / 2 + 0.3, 0, base_z + 1.6, 0.06, 0.06, 0.6), (180, 180, 186))]
        elif s.key == "titan_crawler":            # yalıtımlı gövde, RTG, palet kasaları
            parts += [(box(0, 0, base_z + 0.35, L, T * 0.8, 0.9), col),
                      (box(L / 2 - 0.1, 0, base_z + 0.55, 0.1, T * 0.6, 0.4), (40, 60, 80)),
                      (box(-L / 2 + 0.2, 0, base_z + 0.95, 0.4, 0.4, 0.5), (70, 70, 76)),
                      (box(0, -T / 2 - 0.15, base_z - 0.2, L + 0.4, 0.4, 0.5), (50, 46, 42)),
                      (box(0, T / 2 + 0.15, base_z - 0.2, L + 0.4, 0.4, 0.5), (50, 46, 42)),
                      (box(0.6, 0, base_z + 1.1, 0.06, 0.06, 0.9), (180, 180, 186))]
        else:                    # LTV: açık kabin, iki koltuk, roll bar, panel
            parts += [(box(0, 0, base_z, L, T, 0.18), col),
                      (box(0.1, -0.45, base_z + 0.4, 0.5, 0.5, 0.65), (60, 62, 70)),
                      (box(0.1, 0.45, base_z + 0.4, 0.5, 0.5, 0.65), (60, 62, 70)),
                      (box(-0.35, 0, base_z + 1.0, 0.08, T, 0.08), (200, 200, 206)),
                      (box(-0.9, 0, base_z + 0.35, 0.8, T * 0.9, 0.4), (150, 154, 162)),
                      (box(-0.9, 0, base_z + 0.58, 0.9, T * 1.1, 0.04), (36, 52, 110))]
        self.parts = parts
        self.lamps = [(L / 2 + 0.02, -T * 0.35, base_z + 0.3), (L / 2 + 0.02, T * 0.35, base_z + 0.3)]
        self.seat = (0.25 if s.key not in ("sev", "mars_rover") else L / 2 - 0.5, 0.0, base_z + 1.2)

    def draw(self, surf, rend, cam, rover, sun, scale=1.0, damage=0.0, lights=False):
        s = self.spec
        R = rot(rover.yaw, rover.pitch, rover.roll)
        pos = np.array((rover.x, rover.y, rover.z), dtype=F32)
        polys = []
        f, rr = cam.basis()
        camp = np.array((cam.x, cam.y, cam.z), dtype=F32)
        for (V, Fc), color in self.parts:
            Vw = (np.array(V, dtype=F32) @ R.T) + pos
            sx, sy, dep = rend.project(cam, Vw)
            for face in Fc:
                if (dep[list(face)] < 0.3).any():
                    continue
                a, b, cc = Vw[face[0]], Vw[face[1]], Vw[face[2]]
                nrm = np.cross(b - a, cc - a)
                nn = np.linalg.norm(nrm)
                if nn < 1e-9:
                    continue
                nrm /= nn
                center = Vw[list(face)].mean(axis=0)
                if np.dot(nrm, center - camp) > 0:
                    continue                           # arka yüz
                lam = max(0.0, float(np.dot(nrm, sun)))
                k = 0.28 + 0.72 * lam
                c = tuple(int(min(255, ch * k * (1 - 0.35 * damage))) for ch in color)
                polys.append((float(dep[list(face)].mean()), [(float(sx[i]) * scale, float(sy[i]) * scale) for i in face], c))
        # tekerlekler (ya da palet makaraları): dönen jant çizgileriyle
        for i, (lx, ly) in enumerate(rover.wpos):
            wx, wy = rover.wheel_world(i)
            gz = rover.t.height(wx, wy) + s.wheel_r
            az = rover.z - lx * math.tan(rover.pitch) + ly * math.tan(rover.roll) - (s.cg_h - s.wheel_r)
            cz = min(az, gz) if rover.contact[i] else az - s.travel * 0.4
            heading = rover.yaw + (rover.steer_ang if lx > 0.1 and not s.tracked else 0.0)
            ang = rover.wheel_ang[i]
            ring = []
            for k in range(12):
                a = k / 12 * 2 * math.pi
                ring.append((wx + math.cos(heading) * math.cos(a) * s.wheel_r, wy + math.sin(heading) * math.cos(a) * s.wheel_r,
                             cz + math.sin(a) * s.wheel_r))
            P = np.array(ring, dtype=F32)
            sx, sy, dep = rend.project(cam, P)
            if (dep < 0.3).any():
                continue
            pts = [(float(a) * scale, float(b) * scale) for a, b in zip(sx, sy)]
            tire = (40, 40, 44) if not rover.wheel_fail[i] else (90, 30, 26)
            hub = np.array(((wx, wy, cz),), dtype=F32)
            hx, hy, hd = rend.project(cam, hub)
            spokes = []
            for k in range(3):
                a = ang + k * 2 * math.pi / 3
                Q = np.array(((wx + math.cos(heading) * math.cos(a) * s.wheel_r * 0.85, wy + math.sin(heading) * math.cos(a) * s.wheel_r * 0.85,
                               cz + math.sin(a) * s.wheel_r * 0.85),), dtype=F32)
                qx, qy, _ = rend.project(cam, Q)
                spokes.append(((float(hx[0]) * scale, float(hy[0]) * scale), (float(qx[0]) * scale, float(qy[0]) * scale)))
            # süspansiyon dikmesi: gövde bağlantısından tekerlek göbeğine
            att = (np.array(((lx, ly * 0.8, -(s.cg_h - s.clearance) + 0.05),), dtype=F32) @ R.T) + pos
            ax_, ay_, _ = rend.project(cam, att)
            polys.append((float(dep.mean()) + 0.01, pts, tire, spokes, ((float(ax_[0]) * scale, float(ay_[0]) * scale),
                                                                         (float(hx[0]) * scale, float(hy[0]) * scale))))
        polys.sort(key=lambda p: -p[0])
        for item in polys:
            if len(item) == 3:
                _, pts, c = item
                if len(pts) >= 3:
                    pygame.draw.polygon(surf, c, pts)
            else:
                _, pts, c, spokes, strut = item
                pygame.draw.line(surf, (150, 152, 160), strut[0], strut[1], max(1, int(2 * scale)))
                pygame.draw.polygon(surf, c, pts)
                pygame.draw.polygon(surf, (90, 92, 100), pts, max(1, int(1 * scale)))
                for a, b in spokes:
                    pygame.draw.line(surf, (170, 172, 180), a, b, max(1, int(1 * scale)))
        if lights:
            L = (np.array(self.lamps, dtype=F32) @ R.T) + pos
            sx, sy, dep = rend.project(cam, L)
            for x, y, d in zip(sx, sy, dep):
                if d > 0.3:
                    rad = max(2, int(6 * scale * 4 / max(1.0, d)))
                    pygame.draw.circle(surf, (255, 250, 220), (int(x * scale), int(y * scale)), rad)
