# -*- coding: utf-8 -*-
"""
AETHER-X // GERÇEKÇİ 3B CANLI ÇİZİCİSİ
Görülen (keşfedilen) hayvan türleri genomlarından 3B olarak kurulur ve piksel başına ışıklandırılır.
  * Gövde planı genomdan: yaşam alanı (kara / su / hava / yeraltı / buzaltı), beden boyu (log10 m), beslenme (etçil: çene,
    diş), savunma (sırt plakaları, dikenler), duyular (büyük göz, kulak, anten), sosyallik ve hız (bacak uzunluğu),
    sıcaklık optimumu (kürk / pul / deri dokusu ve renk). Kurgusal türlerde biyolüminesan benekler.
  * Çizim: dik izdüşümde elipsoidlerin ışın kesişimi (numpy, z-tamponu), Blinn-Phong parlaklık, Fresnel kenar ışığı,
    yarım küre ortam ışığı, ekran uzayı ortam gölgesi (AO), 3B prosedürel desen (çizgi, benek, pul), zemine düşen yumuşak
    gölge, 2x süper örnekleme.
  * Sonuçlar (tür, boyut, açı) için önbelleğe alınır; dönen görünüm açı adımlarıyla bir kez çizilir.
Çizimler temsilîdir: genomdan üretilir, bilinen gerçek uzaylı yaşamı değildir.
"""
import math
from collections import OrderedDict

import numpy as np

F32 = np.float32


def _h(s):
    v = 2166136261
    for ch in s:
        v = ((v ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return v


def _rot(yaw=0.0, pitch=0.0, roll=0.0):
    cy, sy, cp, sp, cr, sr = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch), math.cos(roll), math.sin(roll)
    Ry = np.array(((cy, 0, sy), (0, 1, 0), (-sy, 0, cy)), F32)
    Rx = np.array(((1, 0, 0), (0, cp, -sp), (0, sp, cp)), F32)
    Rz = np.array(((cr, -sr, 0), (sr, cr, 0), (0, 0, 1)), F32)
    return Ry @ Rz @ Rx


class Part:
    __slots__ = ("c", "r", "R", "col", "pat", "spec", "emit")

    def __init__(self, c, r, col, R=None, pat=0, spec=0.25, emit=0.0):
        self.c = np.asarray(c, F32)
        self.r = np.asarray(r, F32)
        self.R = np.eye(3, dtype=F32) if R is None else np.asarray(R, F32)
        self.col = np.asarray(col, F32) / 255.0
        self.pat = pat            # 0 düz, 1 çizgi, 2 benek, 3 pul, 4 kürk
        self.spec = spec
        self.emit = emit


def _hsv(h, s, v):
    import colorsys
    return tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h % 1.0, max(0, min(1, s)), max(0, min(1, v))))


def palette(sp):
    """Doğal (gerçek gruplar) ya da egzotik (kurgusal) renkler; sıcak iklim: kum/pas, soğuk: açık gri/beyaz."""
    g = sp.genome
    j = (_h(sp.name) % 1000) / 1000.0
    k = (_h(sp.name + "b") % 1000) / 1000.0
    if sp.real:
        if g.habitat in ("su", "buzaltı"):
            base = _hsv(0.55 + (j - 0.5) * 0.15, 0.45, 0.55 + k * 0.25)
        elif g.habitat == "hava":
            base = _hsv(0.08 + j * 0.6, 0.35 + k * 0.3, 0.45 + k * 0.35)
        else:
            warm = g.temp_opt > 15
            base = _hsv(0.07 + (j - 0.5) * 0.06, 0.45 if warm else 0.12, 0.42 + k * 0.3 if warm else 0.78)
        accent = _hsv(0.08 + k * 0.1, 0.5, 0.3)
    else:
        base = _hsv(0.45 + j * 0.45, 0.5 + k * 0.2, 0.5 + k * 0.25)
        accent = _hsv(0.45 + j * 0.45 + 0.5, 0.7, 0.9)
    belly = tuple(min(255, int(c * 0.55 + 255 * 0.4)) for c in base)
    return base, belly, accent


# ======================================================================== gövde planları
def build(sp):
    """Türün parçaları (model uzayı: x ileri, y yukarı, z sağ; boy ~1 birim). Döner: parça listesi."""
    g = sp.genome
    base, belly, accent = palette(sp)
    rng = np.random.default_rng(_h(sp.name) % (2 ** 32))
    exotic = not sp.real
    pat = 1 if g.diet == "etçil" and g.habitat == "kara" else (2 if exotic or rng.random() < 0.4 else (4 if g.temp_opt < 5 else 0))
    P = []
    eye_s = 0.035 + 0.03 * max(0.0, g.sense)
    carn = g.diet == "etçil"
    hab = g.habitat if g.habitat in ("kara", "su", "hava", "yeraltı", "buzaltı") else "kara"
    nm = sp.name.lower()
    # ---------- gerçek Dünya gruplarına özel gövde planları (ada göre)
    if "kril" in nm or "zooplankton" in nm:                          # kabuklu: kıvrık parçalı gövde, ince bacaklar
        shell = (240, 150, 130) if "kril" in nm else (150, 200, 230)
        for i in range(7):
            a = -0.5 + i * 0.16
            P.append(Part((0.3 - i * 0.1, 0.25 + math.sin(a) * 0.08, 0), (0.08, 0.07 - i * 0.004, 0.065 - i * 0.003), shell,
                          R=_rot(0, 0, a * 0.6), spec=0.9))
            for sz in (-1, 1):
                if i < 5:
                    P.append(Part((0.28 - i * 0.1, 0.13, sz * 0.03), (0.006, 0.06, 0.006), shell, R=_rot(0, sz * 0.4, 0.3)))
        P.append(Part((-0.42, 0.2, 0), (0.07, 0.015, 0.06), shell, spec=0.8))
        for sz in (-1, 1):
            P.append(Part((0.48, 0.38, sz * 0.03), (0.2, 0.005, 0.005), shell, R=_rot(sz * 0.25, 0, 0.5)))
            P.append(Part((0.36, 0.3, sz * 0.05), (0.025, 0.025, 0.02), (16, 16, 18), spec=1.5))
        return P
    if "köpekbal" in nm:                                         # köpekbalığı
        grey, white = (110, 124, 140), (226, 230, 236)
        P.append(Part((0, 0.3, 0), (0.55, 0.15, 0.13), grey, spec=0.5))
        P.append(Part((0.05, 0.24, 0), (0.48, 0.08, 0.11), white, spec=0.4))
        P.append(Part((0.48, 0.29, 0), (0.18, 0.08, 0.08), grey, R=_rot(0, 0, -0.1), spec=0.5))
        P.append(Part((0.0, 0.5, 0), (0.12, 0.14, 0.015), grey, R=_rot(0, 0, -0.45)))                    # sırt yüzgeci
        P.append(Part((-0.62, 0.42, 0), (0.06, 0.16, 0.015), grey, R=_rot(0, 0, -0.55)))                 # kuyruk üst lob
        P.append(Part((-0.6, 0.2, 0), (0.05, 0.1, 0.015), grey, R=_rot(0, 0, 0.6)))                      # alt lob
        for sz in (-1, 1):
            P.append(Part((0.18, 0.18, sz * 0.18), (0.14, 0.02, 0.1), grey, R=_rot(sz * 0.5, 0, -0.3)))
            P.append(Part((0.5, 0.31, sz * 0.07), (0.02, 0.02, 0.015), (10, 10, 12), spec=1.5))
        return P
    if "fok" in nm:                                                 # fok: yağlı iğ biçimli gövde, yüzgeç ayaklar
        base, belly = (118, 112, 104), (176, 170, 160)
        P.append(Part((0, 0.22, 0), (0.46, 0.18, 0.17), base, pat=2, spec=0.7))
        P.append(Part((0.43, 0.27, 0), (0.12, 0.11, 0.1), base, pat=2, spec=0.7))
        P.append(Part((0.53, 0.25, 0), (0.06, 0.05, 0.06), belly, spec=0.6))
        for sz in (-1, 1):
            P.append(Part((0.2, 0.08, sz * 0.15), (0.1, 0.02, 0.06), base, R=_rot(sz * 0.6, 0, 0.3), spec=0.5))
            P.append(Part((-0.5, 0.2, sz * 0.06), (0.12, 0.02, 0.06), base, R=_rot(sz * 0.3, 0, 0), spec=0.5))
            P.append(Part((0.49, 0.3, sz * 0.06), (0.022, 0.022, 0.018), (10, 10, 12), spec=1.6))
        return P
    if hab in ("su", "buzaltı"):                                   # ---------- balık / deniz canlısı
        L = 1.0
        P.append(Part((0, 0, 0), (0.5 * L, 0.17, 0.13), base, pat=3 if not exotic else 2, spec=0.6))
        P.append(Part((0.02, -0.05, 0), (0.42, 0.1, 0.1), belly, spec=0.5))
        P.append(Part((0.36, 0.0, 0), (0.17, 0.13, 0.11), base, spec=0.6))
        P.append(Part((-0.55, 0, 0), (0.12, 0.2, 0.02), accent, R=_rot(0, 0, 0.0), spec=0.3))         # kuyruk yüzgeci
        P.append(Part((-0.05, 0.19, 0), (0.18, 0.08, 0.015), accent, R=_rot(0, 0, -0.35), spec=0.3))   # sırt yüzgeci
        for sz in (-1, 1):
            P.append(Part((0.18, -0.07, sz * 0.12), (0.1, 0.03, 0.05), accent, R=_rot(sz * 0.6, 0, -0.4)))
            P.append(Part((0.42, 0.04, sz * 0.085), (eye_s, eye_s, eye_s * 0.6), (20, 20, 24), spec=1.4))
        if carn:
            P.append(Part((0.5, -0.04, 0), (0.06, 0.03, 0.06), (230, 230, 220), spec=0.8))
        if exotic:
            for i in range(6):
                P.append(Part((0.25 - i * 0.12, 0.06, 0.12 * (1 if i % 2 else -1)), (0.018, 0.018, 0.018), accent, emit=1.0))
        return P
    if hab == "hava":                                               # ---------- kuş / uçan
        P.append(Part((0, 0.35, 0), (0.28, 0.16, 0.14), base, pat=4, spec=0.15))
        P.append(Part((0.02, 0.3, 0), (0.22, 0.12, 0.12), belly, pat=4, spec=0.1))
        P.append(Part((0.3, 0.47, 0), (0.11, 0.1, 0.09), base, pat=4, spec=0.15))
        P.append(Part((0.43, 0.45, 0), (0.08, 0.025, 0.025), (230, 170, 60), spec=0.6))                  # gaga
        for sz in (-1, 1):
            P.append(Part((0.0, 0.42, sz * 0.32), (0.16, 0.025, 0.28), base, R=_rot(0, sz * 0.25, 0), pat=4, spec=0.1))   # kanat
            P.append(Part((-0.12, 0.4, sz * 0.5), (0.1, 0.02, 0.12), accent, R=_rot(0, sz * 0.35, 0), pat=4))
            P.append(Part((0.36, 0.5, sz * 0.06), (0.025, 0.025, 0.02), (16, 16, 18), spec=1.4))
            P.append(Part((0.02, 0.12, sz * 0.05), (0.015, 0.12, 0.015), (200, 150, 70)))                   # bacak
        P.append(Part((-0.33, 0.36, 0), (0.14, 0.02, 0.09), accent, R=_rot(0, 0, 0.2), pat=4))           # kuyruk
        return P
    small = hab == "yeraltı" or g.size < -0.5
    bear = "ayı" in nm
    lizard = "kertenkele" in nm or "sürüngen" in nm
    if g.size < -1.8:                                               # ---------- böcek / eklem bacaklı
        sh = accent if exotic else (40, 36, 30)
        P.append(Part((-0.2, 0.18, 0), (0.24, 0.13, 0.15), base, spec=0.9))                              # karın
        P.append(Part((0.08, 0.18, 0), (0.12, 0.1, 0.11), sh, spec=0.9))                                  # göğüs
        P.append(Part((0.25, 0.18, 0), (0.08, 0.08, 0.09), sh, spec=0.9))                                 # baş
        for sz in (-1, 1):
            for i, dx in enumerate((0.15, 0.06, -0.04)):
                P.append(Part((dx, 0.11, sz * 0.16), (0.012, 0.012, 0.11), sh, R=_rot(0, 0, 0.0) @ _rot(0, sz * (0.5 - i * 0.4), 0)))
                P.append(Part((dx + 0.02, 0.05, sz * 0.27), (0.01, 0.07, 0.01), sh))
            P.append(Part((0.37, 0.27, sz * 0.05), (0.13, 0.008, 0.008), sh, R=_rot(sz * 0.4, 0, 0.5)))    # anten
            P.append(Part((0.3, 0.21, sz * 0.06), (0.03, 0.03, 0.025), (16, 16, 18), spec=1.4))
            if g.speed > 0.4:
                P.append(Part((-0.05, 0.3, sz * 0.14), (0.22, 0.01, 0.09), (200, 220, 240), R=_rot(sz * 0.3, 0, 0.1), spec=1.0))
        return P
    # ---------- kara hayvanı: dört ayaklı (büyük) ya da kısa bacaklı (küçük)
    leg = 0.32 + 0.18 * max(0.0, g.speed) if not small else 0.12
    body_l = 0.42 if not small else 0.5
    if bear:
        leg, body_l = 0.24, 0.46
    if lizard:
        leg, body_l, pat = 0.08, 0.36, 3
    by = leg + 0.17
    thick = 1.25 if bear else 1.0
    P.append(Part((0, by, 0), (body_l, 0.19 * thick, 0.17 * thick), base, pat=pat if not bear else 4, spec=0.2))   # gövde
    P.append(Part((0.02, by - 0.08, 0), (body_l * 0.85, 0.12, 0.14), belly, spec=0.15))                    # karın
    P.append(Part((0.3, by + 0.03, 0), (0.2, 0.18, 0.16), base, pat=pat, spec=0.2))                         # göğüs/omuz
    nx, ny = (0.5, by + 0.2) if not small else (0.52, by + 0.02)
    P.append(Part(((nx + 0.3) / 2, (ny + by) / 2, 0), (0.15, 0.08, 0.08), base, R=_rot(0, 0, 0.7 if not small else 0.1), pat=pat))  # boyun
    P.append(Part((nx, ny, 0), (0.14, 0.11, 0.1), base, pat=pat, spec=0.25))                                 # baş
    P.append(Part((nx + 0.13, ny - 0.03, 0), (0.09, 0.06, 0.07), belly, spec=0.3))                           # burun
    P.append(Part((nx + 0.21, ny - 0.02, 0), (0.02, 0.02, 0.03), (24, 20, 20), spec=1.0))                   # burun ucu
    for sz in (-1, 1):
        P.append(Part((nx + 0.06, ny + 0.04, sz * 0.075), (eye_s, eye_s, eye_s * 0.7), (14, 14, 16), spec=1.5))
        ear = 0.05 + 0.06 * max(0.0, g.sense)
        P.append(Part((nx - 0.04, ny + 0.1, sz * 0.06), (0.03, ear, 0.02), base, R=_rot(0, 0, -0.3 * sz * 0 - 0.2)))
        for fx in ((0.26, -0.26) if not small else (0.22, -0.22)):
            lz = sz * (0.1 * thick if not lizard else 0.2)
            lw_ = 0.065 * thick
            P.append(Part((fx, by - 0.05, sz * 0.09 * thick), (lw_ * 1.25, 0.12, lw_ * 1.15), base, pat=pat))  # kalça/omuz kası
            P.append(Part((fx, leg * 0.62 + 0.05, lz), (lw_, leg * 0.42 + 0.02, lw_ * 0.9), base, pat=pat,
                          R=_rot(0, sz * 0.5 if lizard else 0, 0)))                                         # üst bacak
            P.append(Part((fx + 0.01, leg * 0.24, lz), (lw_ * 0.7, leg * 0.3 + 0.01, lw_ * 0.65), base))     # alt bacak
            P.append(Part((fx + 0.03, 0.025, lz), (0.06 * thick, 0.025, 0.045 * thick), accent, spec=0.4))  # pati / toynak
    if carn:
        for sz in (-1, 1):
            P.append(Part((nx + 0.15, ny - 0.08, sz * 0.03), (0.01, 0.025, 0.01), (240, 236, 220), spec=0.9))   # diş
    tail = 0.25 + 0.2 * (1 - max(0.0, g.social))
    if lizard:
        tail = 0.6
    if not bear:                                                                                             # kuyruk: üst üste binen konik zincir
        nseg = 8
        for i in range(nseg):
            k = i / (nseg - 1)
            rr_ = 0.07 * (1 - k * 0.8) * (1.2 if lizard else 1.0)
            P.append(Part((-body_l + 0.02 - k * tail, by + 0.03 - k * (0.1 if not lizard else 0.15), 0),
                          (rr_ * 1.6, rr_, rr_), base, R=_rot(0, 0, 0.15 + k * 0.2), pat=pat))
    else:
        P.append(Part((-body_l - 0.02, by + 0.05, 0), (0.05, 0.05, 0.05), base, pat=4))
    if g.defense > 0.5:                                                                                      # sırt plakaları / dikenler
        n = 5
        for i in range(n):
            x = 0.25 - i * (0.5 / (n - 1))
            P.append(Part((x, by + 0.19, 0), (0.05, 0.08, 0.012), accent, R=_rot(0, 0, 0.1), spec=0.5))
    if exotic:
        for i in range(8):
            P.append(Part((0.25 - i * 0.08, by + 0.12, (0.15 if i % 2 else -0.15)), (0.02, 0.02, 0.02), accent, emit=1.0))
    return P


# ======================================================================== çizim
def _noise3(p, scale, seed):
    q = p * scale
    i = np.floor(q)
    f = q - i
    f = f * f * (3 - 2 * f)

    def hsh(ix, iy, iz):
        v = np.sin(ix * 127.1 + iy * 311.7 + iz * 74.7 + seed * 13.7) * 43758.5453
        return v - np.floor(v)
    x0, y0, z0 = i[:, 0], i[:, 1], i[:, 2]
    fx, fy, fz = f[:, 0], f[:, 1], f[:, 2]
    acc = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (fx if dx else 1 - fx) * (fy if dy else 1 - fy) * (fz if dz else 1 - fz)
                acc = acc + w * hsh(x0 + dx, y0 + dy, z0 + dz)
    return acc


def render(parts, size, yaw=0.6, pitch=-0.32, seed=0, ss=2, ground=True):
    """RGBA uint8 (size x size). yaw: dönüş açısı. Ortografik, ışık sol-üst-önden."""
    N = size * ss
    V = _rot(yaw, 0, 0)
    V = _rot(0, 0, 0) @ V
    P = np.array(((1, 0, 0), (0, math.cos(pitch), -math.sin(pitch)), (0, math.sin(pitch), math.cos(pitch))), F32) @ V
    # model sınırları -> ölçek
    pts = np.array([p.c for p in parts]) @ P.T
    ext = np.array([float(np.max(p.r)) for p in parts])
    lo = (pts[:, :2] - ext[:, None]).min(0)
    hi = (pts[:, :2] + ext[:, None]).max(0)
    span = float(max(hi - lo)) * 1.12
    cxy = (lo + hi) / 2
    cxy[1] -= span * 0.04
    px = (np.arange(N, dtype=F32) + 0.5) / N
    U = cxy[0] + (px - 0.5) * span
    Vv = cxy[1] - (px - 0.5) * span
    depth = np.full((N, N), -1e9, F32)
    nrm = np.zeros((N, N, 3), F32)
    alb = np.zeros((N, N, 3), F32)
    spec = np.zeros((N, N), F32)
    emit = np.zeros((N, N), F32)
    posm = np.zeros((N, N, 3), F32)
    patm = np.zeros((N, N), np.int8)
    for p in parts:
        cv = P @ p.c
        rr = float(np.max(p.r))
        x0 = int(max(0, np.floor(((cv[0] - rr) - cxy[0]) / span * N + N / 2)))
        x1 = int(min(N, np.ceil(((cv[0] + rr) - cxy[0]) / span * N + N / 2)))
        y0 = int(max(0, np.floor((cxy[1] - (cv[1] + rr)) / span * N + N / 2)))
        y1 = int(min(N, np.ceil((cxy[1] - (cv[1] - rr)) / span * N + N / 2)))
        if x1 <= x0 or y1 <= y0:
            continue
        uu, vv = np.meshgrid(U[x0:x1], Vv[y0:y1])
        M = np.diag(1.0 / p.r) @ p.R.T @ P.T            # görüş -> yerel birim küre
        o = np.stack([uu - cv[0], vv - cv[1], np.zeros_like(uu)], -1) @ M.T
        d = M @ np.array((0, 0, -1), F32)
        a = float(d @ d)
        b = (o @ d)
        c = (o * o).sum(-1) - 1.0
        disc = b * b - a * c
        hit = disc > 0
        if not hit.any():
            continue
        t = np.where(hit, (-b - np.sqrt(np.maximum(disc, 0))) / a, 0)
        z = cv[2] - t
        sub = depth[y0:y1, x0:x1]
        win = hit & (z > sub)
        if not win.any():
            continue
        loc = o + t[..., None] * d                       # yerel birim küre noktası
        nl = loc / p.r                                   # elipsoid normali (yerel, ölçekli)
        nw = nl @ (P @ p.R).T
        nw /= np.linalg.norm(nw, axis=-1, keepdims=True) + 1e-9
        pm = (loc * p.r) @ p.R.T + p.c                    # model uzayı noktası (desen için)
        sub[win] = z[win]
        nrm[y0:y1, x0:x1][win] = nw[win]
        alb[y0:y1, x0:x1][win] = p.col
        spec[y0:y1, x0:x1][win] = p.spec
        emit[y0:y1, x0:x1][win] = p.emit
        posm[y0:y1, x0:x1][win] = pm[win]
        patm[y0:y1, x0:x1][win] = p.pat
    mask = depth > -1e8
    if not mask.any():
        return np.zeros((size, size, 4), np.uint8)
    # desen dokusu (model uzayında: dönünce kaymaz)
    idx = np.nonzero(mask)
    pm = posm[idx]
    pt = patm[idx]
    n1 = _noise3(pm, 9.0, seed)
    n2 = _noise3(pm, 26.0, seed + 3)
    k = np.ones(len(pm), F32) * (0.92 + 0.16 * n2)
    st = pt == 1
    k[st] *= 0.55 + 0.45 * (np.sin(pm[st, 0] * 38 + n1[st] * 6) > -0.2)
    sp_ = pt == 2
    k[sp_] *= np.where(n1[sp_] > 0.62, 0.5, 1.0)
    sc = pt == 3
    k[sc] *= 0.8 + 0.2 * np.abs(np.sin(pm[sc, 0] * 70) * np.sin(pm[sc, 1] * 70 + pm[sc, 2] * 40))
    fu = pt == 4
    k[fu] *= 0.82 + 0.3 * _noise3(pm[fu], 70.0, seed + 7) if fu.any() else 1
    alb[idx] *= k[:, None]
    # ışık
    Lk = np.array((-0.45, 0.65, 0.6), F32)
    Lk /= np.linalg.norm(Lk)
    Lf = np.array((0.7, 0.1, 0.4), F32)
    Lf /= np.linalg.norm(Lf)
    Vd = np.array((0, 0, 1), F32)
    n = nrm[idx]
    dk = np.clip(n @ Lk, 0, 1)
    df = np.clip(n @ Lf, 0, 1)
    hemi = 0.5 + 0.5 * n[:, 1]
    amb = 0.18 + 0.22 * hemi
    Hh = (Lk + Vd) / np.linalg.norm(Lk + Vd)
    s = np.clip(n @ Hh, 0, 1) ** 40 * spec[idx]
    fres = (1 - np.clip(n @ Vd, 0, 1)) ** 3
    # ekran uzayı ortam gölgesi: komşuları öndeyse karart
    dd = np.where(mask, depth, depth[mask].min())
    kk = max(3, N // 40)
    cs = np.cumsum(np.cumsum(np.pad(dd, ((kk, kk), (kk, kk)), mode="edge"), 0), 1)
    blur = (cs[2 * kk:, 2 * kk:] - cs[:-2 * kk, 2 * kk:] - cs[2 * kk:, :-2 * kk] + cs[:-2 * kk, :-2 * kk]) / ((2 * kk) ** 2)
    blur = blur[:N, :N]
    ao = np.clip(1 - np.maximum(0, (blur - dd))[idx] * (6.0 / max(1e-6, float(np.ptp(dd[mask])) + 0.2)), 0.45, 1)
    a = alb[idx]
    sss = np.array((0.12, 0.04, 0.02), F32) * (1 - dk)[:, None] * dk[:, None] * 4         # alt yüzey saçılması (sıcak terminatör)
    col = a * (dk * 1.05 + df * 0.25 + amb)[:, None] * ao[:, None] + s[:, None] * 0.9 + fres[:, None] * 0.18 * (0.6 + a) + sss
    col += a * emit[idx][:, None] * 1.4
    col = col / (1 + col * 0.35) * 1.25                                                       # yumuşak ton eşleme
    out = np.zeros((N, N, 4), F32)
    out[..., :3][idx] = np.clip(col, 0, 1)
    out[..., 3][idx] = 1.0
    if ground:                                                                                 # yumuşak zemin gölgesi
        ys = np.nonzero(mask.any(1))[0]
        base_y = ys.max() if len(ys) else N - 1
        sil = mask.astype(F32)
        sh = np.zeros_like(sil)
        rows = np.linspace(0, N - 1, N // 5).astype(int)
        squash = sil[rows].max(0)
        w = squash > 0
        if w.any():
            xs = np.nonzero(w)[0]
            cxp, hw = (xs.min() + xs.max()) / 2 + N * 0.03, (xs.max() - xs.min()) / 2 * 1.05
            yy, xx = np.mgrid[0:N, 0:N]
            e = ((xx - cxp) / max(1, hw)) ** 2 + ((yy - base_y) / max(1, N * 0.045)) ** 2
            sh = np.clip(1 - e, 0, 1) ** 1.5 * 0.55
        sa = sh * (1 - out[..., 3])
        out[..., 3] = np.maximum(out[..., 3], sa)
    if ss > 1:                                                                                 # süper örnekleme
        out = out.reshape(size, ss, size, ss, 4).mean((1, 3))
        rgb = out[..., :3] / np.maximum(out[..., 3:4], 1e-6)
        out = np.concatenate([np.clip(rgb, 0, 1) * (out[..., 3:4] > 0), out[..., 3:4]], -1)
    return (out * 255).astype(np.uint8)


# ======================================================================== önbellek
_CACHE = OrderedDict()
_PARTS = {}


def surface(sp, size, angle_step=0, steps=24, pitch=-0.32, ss=2):
    """Türün (boyut, açı adımı) için pygame yüzeyi; önbellekli."""
    import pygame
    key = (sp.name, sp.sid, size, angle_step % steps, steps, round(pitch, 2), ss)
    hit = _CACHE.get(key)
    if hit is not None:
        _CACHE.move_to_end(key)
        return hit
    parts = _PARTS.get((sp.name, sp.sid))
    if parts is None:
        parts = _PARTS[(sp.name, sp.sid)] = build(sp)
    yaw = 0.6 + (angle_step % steps) / steps * math.tau
    arr = render(parts, size, yaw, pitch, _h(sp.name) % 97, ss)
    srf = pygame.image.frombuffer(np.ascontiguousarray(arr).tobytes(), (size, size), "RGBA").copy()
    _CACHE[key] = srf
    while len(_CACHE) > 260:
        _CACHE.popitem(last=False)
    return srf


def is_cached(sp, size, angle_step=0, steps=24, pitch=-0.32, ss=2):
    return (sp.name, sp.sid, size, angle_step % steps, steps, round(pitch, 2), ss) in _CACHE
