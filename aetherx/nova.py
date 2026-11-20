# -*- coding: utf-8 -*-
"""
KOZMOGENİS // NOVA
AI Kontrol Merkezi'nde yaşayan yapay zekâ. Oyuncunun kişisel adını asla
kullanmaz; her cümlede AJANS ADINI kullanır.

  Seviye 1 : basit tavsiye
  Seviye 2 : detaylı, sayısal tavsiye ("%15 daha az yakarsın")
  Seviye 3 : geleceği tahmin eder ("2 saat sonra Güneş Fırtınası geliyor, bekle")

Bu dosyada hem diyalog üretimi (saf mantık) hem de NOVA'nın yüzü ve konuşma
balonu (pygame çizimi) bulunur.
"""
import math
import random

import pygame

from . import data as D
from .config import C, GAME_MIN_PER_SEC, W, H
from .fx import draw_glow, scale_color, lerp_color, ease_out_back, clamp
from .i18n import tr
from .ui import UI, draw_text, glass_panel, wrap_text, font


def _h(minutes):
    """Oyun dakikasını okunur süreye çevirir."""
    minutes = max(0, minutes)
    if minutes < 60:
        return f"{int(minutes)} dakika"
    h = minutes / 60
    if abs(h - round(h)) < 0.15:
        return f"{int(round(h))} saat"
    return f"{h:.1f} saat"


# ===========================================================================
# DİYALOG
# ===========================================================================
class NovaBrain:
    def __init__(self, game):
        self.g = game

    @property
    def n(self):
        return self.g.name

    @property
    def lv(self):
        return max(1, self.g.nova_level)

    # ------------------------------------------------------------- selamlar
    def greet(self):
        h = self.g.hour_of_day()
        if h < 6:
            opts = [f"Merhaba {self.n}, gece vardiyasındayız. Yıldızlar çok net, bugün ne yapalım?"]
        elif h < 12:
            opts = [f"Günaydın {self.n}, bugün ne yapalım?", f"Merhaba {self.n}, fırlatmaya hazır mısın?"]
        elif h < 18:
            opts = [f"Merhaba {self.n}, bugün ne yapalım?", f"{self.n}, tüm sistemler çevrimiçi. Emrinizdeyim."]
        else:
            opts = [f"İyi akşamlar {self.n}, bugün ne yapalım?", f"Merhaba {self.n}, akşam penceresi açık."]
        return random.choice(opts)

    def welcome_new(self):
        return (f"Merhaba {self.n}! Ben NOVA, ajansının yapay zekâsıyım. Gelişmiş bir üssün var ama binaların "
                f"çoğu Seviye 1. İlk hedefimiz Ay. Montaj Hangarı'na git, ilk roketini tasarla.")

    # ------------------------------------------------------------- tasarım
    def review(self, rep):
        """[(cümle, vurgulanacak_slot)] döndürür."""
        n, lv, g = self.n, self.lv, self.g
        pl = D.PLANET[rep["planet"]]
        pname = pl["name"]
        to = D.TO[rep["planet"]]
        out = []
        eng = rep.get("engine")
        pwr = rep.get("power")
        for it in sorted(rep["issues"], key=lambda i: -i["sev"]):
            c = it["code"]
            s = None
            if c == "missing":
                s = f"{n}, eksik parça var. Tüm aşamaları doldurmalısın."
            elif c == "not_owned":
                s = f"{n}, {it['name']} henüz satın alınmadı. Hangardan satın alabilirsin."
            elif c == "fuel_low":
                if lv >= 2:
                    s = (f"{n}, bu yakıtla dönüş dahil rotanın yaklaşık %{int(min(1, it['margin']) * 100)}'ini "
                         f"karşılarsın. En az {it['need']:.0f} kg yakıt lazım.")
                else:
                    s = f"{n}, yakıtın yetmeyebilir. Yakıt kaydırıcısını artır."
                if eng and eng["key"] in ("solid",) and lv >= 2:
                    s += " Katı yakıtlı motor çok yakıyor, sıvı yakıta geçmeyi düşün."
            elif c == "power_low":
                if eng and eng["key"] == "ion" and pwr and pwr["kind"] != "solar":
                    s = f"{n}, İyon motoru seçmişsin ama elektriğin yetersiz, Güneş Paneli de yok."
                elif eng and eng["key"] == "ion":
                    s = f"{n}, İyon motoru çok elektrik çekiyor; daha büyük panel ya da RTG gerekli."
                elif lv >= 2:
                    s = (f"{n}, elektrik yolculuğun %{int(it['frac'] * 100)}'inde biter. "
                         f"Sonra ışıklar söner, radar kapanır.")
                else:
                    s = f"{n}, elektriğin yolda bitecek. Güneş Paneli veya RTG kullan."
            elif c == "ion_power":
                s = f"{n}, İyon motoru küçük bataryayla çalışmaz. Güneş Paneli tak."
            elif c == "dark" and lv >= 2:
                s = f"{n}, rotada karanlık bölge var; orada güneş paneli 0 üretir. RTG her zaman çalışır."
            elif c == "antenna_range":
                s = f"{n}, antenin menzili {to} yetmez. Daha güçlü bir anten seç."
            elif c == "tower_range":
                s = f"{n}, İletişim Kulesi {pname} menziline ulaşamıyor. Kuleyi yükseltmezsen {pname}'daki rokete sesimiz gitmez." \
                    if rep["planet"] != "venus" else f"{n}, İletişim Kulesi Venüs'e ulaşamıyor. Kuleyi yükselt."
            elif c == "need_doctor":
                s = f"{n}, Nükleer motor seçmişsin ama Doktor almamışsın."
            elif c == "o2_low":
                s = f"{n}, oksijen yolculuğa yetmiyor! Daha az astronot al veya daha büyük gövde seç."
            elif c == "heavy":
                s = f"{n}, çok ağır oldun! Kalkışta risk artıyor."
            elif c == "overload":
                s = f"{n}, gövde taşıma kapasitesi aşıldı: {it['mounted']:.0f}/{it['cap']} kg. Yakıtı azalt ya da yük çıkar."
            elif c == "lift":
                s = f"{n}, roket kalkamaz: {it['total']:.0f} kg kütleye {it['lift']:.0f} kg kaldırma gücü var."
                if lv >= 2:
                    s += " Katı yakıtlı motor kalkışta en güçlüsü."
            elif c == "hangar":
                s = f"{n}, bu roket için Montaj Hangarı Seviye {it['size']} gerekli."
            elif c == "pad":
                s = f"{n}, bu boyuttaki roket için {D.PAD_NAME[it['size']]} açılmalı."
            elif c == "no_land":
                s = f"{n}, seçtiğin gövde iniş yapamaz. Kapsül veya İniş Modülü seç."
            elif c == "colony_hull":
                s = f"{n}, koloni seferi için İstasyon Modülü veya Kargo Gövdesi lazım."
            elif c == "need_crew":
                s = f"{n}, bu görev için astronot seçmelisin."
            elif c == "heat":
                s = f"{n}, Venüs yüzeyi 460 derece! Sıcaklık Kalkanı olmadan inemeyiz."
            elif c == "no_pilot":
                s = f"{n}, pilotsuz roket yavaş gider ve asteroitlerden kaçamaz. Pilot riski %20 düşürür."
            elif c == "no_engineer" and lv >= 2:
                s = f"{n}, Mühendis almazsan yolda bozulan parçayı tamir edemezsin."
            elif c == "tired":
                s = f"{n}, {', '.join(it['names'][:2])} yorgun. Verimi düşük; Eğlence Alanı'nda dinlendir."
            elif c == "no_payload":
                s = f"{n}, araştırma yükü yok. Kamera takarsan her fotoğraf +20 Puan."
            elif c == "storm":
                if lv >= 3:
                    s = f"{n}, {_h(it['start'])} sonra Güneş Fırtınası geliyor ve uçuşa denk geliyor. Bekle."
                elif lv >= 2:
                    s = f"{n}, uçuş penceresinde fırtına ihtimali yüksek. Manyetometre takmanı öneririm."
            elif c == "no_magneto" and lv >= 2 and rep.get("storms"):
                s = f"{n}, Manyetometre olmadan fırtına aniden gelir."
            elif c == "suit_weak":
                s = (f"{n}, {pname} yüzeyi için kıyafetler yeterince dayanıklı değil. "
                     f"Araştırma Merkezi'nde Zırh Katmanı'nı geliştir.")
            elif c == "sail_far":
                s = f"{n}, Güneş Yelkeni Jüpiter'de çok yavaşlar; Güneş orada çok zayıf."
            if s:
                out.append((s, it["slot"]))
        # seviye 2+: tasarruf önerileri
        if lv >= 2 and eng and rep.get("fuel_need", 0) > 0:
            for alt in ("ion", "nuclear", "plasma"):
                ae = D.PART["engine"][alt]
                if ae["key"] != eng["key"] and g.part_unlocked("engine", alt) and ae["burn"] < eng["burn"]:
                    pct = int(round((1 - ae["burn"] / eng["burn"]) * 100))
                    out.append((f"{n}, {ae['name']} kullanırsan %{pct} daha az yakarsın.", "engine"))
                    break
        if lv >= 3 and rep.get("flight_min"):
            best = g.best_launch_time(rep["flight_min"])
            if best - g.minutes > 5:
                out.append((f"{n}, en iyi fırlatma saati {g.time_label(best)[-5:]}. O zaman fırtınasız bir pencere var.", None))
            else:
                out.append((f"{n}, şu an fırlatma için temiz bir pencere. Hava açık.", None))
        if not out or all(sl is None for _, sl in out[:1]) and rep["ok"]:
            r = rep["risk"]
            if rep["ok"] and r["success"] > 0.8:
                out.insert(0, (f"{n}, tasarım sağlam görünüyor. Tam başarı şansı %{int(r['success'] * 100)}. "
                               f"Fırlatmaya hazırım.", None))
            elif rep["ok"]:
                out.insert(0, (f"{n}, fırlatabiliriz ama risk {rep['risk_label'].lower()}. "
                               f"Tam başarı şansı %{int(r['success'] * 100)}.", None))
        return out[:6]

    # ------------------------------------------------------------- tahmin
    def forecast(self):
        n, lv, g = self.n, self.lv, self.g
        act = g.storm_active()
        nxt = g.next_storm()
        if act:
            left = act["start"] + act["dur"] - g.minutes
            if lv >= 2:
                return f"{n}, şu an Güneş Fırtınası aktif! {_h(left)} daha sürecek. Fırlatma yapma."
            return f"{n}, şu an Güneş Fırtınası var. Beklemek en iyisi."
        if lv >= 3 and nxt:
            dt = nxt["start"] - g.minutes
            return (f"{n}, {_h(dt)} sonra Güneş Fırtınası geliyor, {_h(nxt['dur'])} sürecek. "
                    f"Gücü %{int(nxt['power'] * 100)}. Uzun görevler için bekle.")
        if lv >= 2 and nxt:
            dt = nxt["start"] - g.minutes
            band = "yakında" if dt < 240 else "birkaç saat içinde"
            return f"{n}, manyetik veriler {band} fırtına olabileceğini gösteriyor. Kesin zaman için beni Seviye 3'e yükselt."
        return f"{n}, uzay havası şu an sakin görünüyor. Fırtınaları önceden görmek için beni yükseltebilirsin."

    def best_time_text(self, flight_sec=60):
        n, g = self.n, self.g
        if self.lv < 3:
            return f"{n}, en iyi fırlatma saatini hesaplamak için Seviye 3 NOVA gerekli."
        fm = flight_sec * GAME_MIN_PER_SEC
        best = g.best_launch_time(fm)
        if best - g.minutes < 5:
            return f"{n}, şimdi fırlat! Önümüzdeki {_h(fm)} boyunca fırtına yok."
        return f"{n}, en iyi fırlatma saati {g.time_label(best)[-5:]} ({_h(best - g.minutes)} sonra)."

    # ------------------------------------------------------------- görev öner
    def suggest(self):
        n, g = self.n, self.g
        s = g.s
        v = s["visits"]
        if v["moon"] == 0:
            return f"{n}, ilk hedefimiz Ay. Orbiter + Sıvı Yakıt + Güneş Paneli + Kamera ile güvenli bir başlangıç yap.", "moon"
        if s["landings"]["moon"] == 0:
            return f"{n}, Ay'a iniş yapma zamanı! Kapsül Gövdesi ve 3 astronotla in, ilk inişte +200 Puan var.", "moon"
        if not g.colony("moon"):
            return f"{n}, Ay'a iniş yaptık. Bir sonraki inişte koloni kurabilirsin.", "moon"
        if v["mars"] == 0:
            mc = g.colony("moon")
            if mc and mc["storage"] < 10:
                return f"{n}, Ay'da maden azaldı, Mars'a gitmeyi öneriyorum.", "mars"
            return f"{n}, Mars'a hazırız. Yüksek Kazançlı Anten ve İletişim Kulesi Sv2 lazım.", "mars"
        if not g.colony("mars"):
            return f"{n}, Mars'ta koloni kurmak ajansı gerçek bir gezegenler arası güç yapar.", "mars"
        if v["venus"] == 0 and g.planet_unlocked("venus"):
            return f"{n}, Venüs'teki sülfür çok değerli. Ama Sıcaklık Kalkanı şart.", "venus"
        if v["jupiter"] == 0:
            return f"{n}, final hedefi Jüpiter! Lazer İletişim ve Kule Sv3 olmadan bağlantı kuramayız.", "jupiter"
        if not g.colony("jupiter"):
            return f"{n}, Jüpiter'de dev koloniyi kurma vakti. İstasyon Modülü ile git.", "jupiter"
        return f"{n}, Güneş Sistemi bizim! Kolonileri büyütmeye devam et.", "jupiter"

    # ------------------------------------------------------------- danışman
    def advisor(self):
        """Ana ekran için en önemli tek tavsiye: (başlık, metin, hedef_sahne)."""
        g, n = self.g, self.n
        s = g.s
        if s["research"]["active"] is None:
            avail = [r for r in D.RESEARCH if g.research_state(r["key"]) == "available"]
            afford = [r for r in avail if g.rp >= g.research_cost(r["key"])[0]]
            if afford:
                return ("Laboratuvar boş", f"{n}, {afford[0]['name']} araştırmasını başlatabilirsin.", "research")
        if g.unclaimed_quests():
            return ("Ödül bekliyor", f"{n}, Görev Tahtası'nda alınmamış ödüller var.", "quests")
        if s["inventory"]["stardust"] >= 5:
            return ("Yıldız Tozu", f"{n}, depoda {s['inventory']['stardust']} Yıldız Tozu var. Araştırma Merkezi'nde işle.", "research")
        minerals = sum(s["inventory"][m["key"]] * m["price"] for m in D.MINERALS)
        if minerals >= 200:
            return ("Satılık maden", f"{n}, depodaki madenlerin değeri {minerals} Para. Satabilirsin.", "depot")
        sick = [c for c in s["crew"] if c["status"] == "sick"]
        if sick:
            return ("Hasta astronot", f"{n}, {sick[0]['name']} Sağlık Merkezi'nde.", "crew")
        for p, c in s["colonies"].items():
            if c and c["happiness"] < 35:
                return ("Koloni mutsuz", f"{n}, {D.AT[p]} mutluluk düştü. Yemek gönder veya film gecesi yap.", "colony")
        txt, planet = self.suggest()
        return ("Sıradaki hedef", txt, "hangar")

    # ------------------------------------------------------------- uçuş
    def flight_tip(self, threat):
        n = self.n
        k = threat.get("kind")
        if k == "asteroid":
            dirw = "yukarı" if threat.get("dy", 0) > 0 else "aşağı"
            return f"{n}, dikkat, sağdan asteroit geliyor! {dirw.capitalize()} kaç."
        if k == "big":
            return f"{n}, dev asteroit! Lazerle kırmaya çalışma, kaç!"
        if k == "gold":
            return f"{n}, altın asteroit tespit ettim. Lazerle kır, maden topla!"
        if k == "storm":
            return f"{n}, Güneş Fırtınası yaklaşıyor! Elektrik dalgalanacak."
        if k == "fuel":
            return f"{n}, yakıt azaldı. Yavaşla veya yakıt istasyonuna yanaş."
        if k == "power":
            return f"{n}, elektrik kritik! Lazeri kullanma."
        if k == "o2":
            return f"{n}, oksijen azalıyor, hızlanmamız lazım!"
        if k == "broken":
            return f"{n}, {threat.get('part', 'bir parça')} bozuk. Mühendis tamir edebilir: R tuşu."
        if k == "station":
            return f"{n}, ileride yakıt istasyonu var. Yakıt alabiliriz."
        if k == "satellite":
            return f"{n}, kayıp bir uydu sinyali! Yanaşırsan kurtarırız: +100 Puan."
        if k == "photo":
            return f"{n}, fotoğraf fırsatı! F tuşuna bas."
        if k == "nolink":
            return f"{n}... sinyal... zayıf..."
        return f"{n}, rota temiz. Devam."

    # ------------------------------------------------------------- kutlama
    def celebrate(self, planet, outcome, first=False):
        n = self.n
        pn = D.PLANET[planet]["name"]
        if outcome == "success":
            if first:
                return f"Tebrikler {n}! {D.TO[planet]} ilk varışını kutluyorum."
            return f"Harika iş {n}! {pn} görevi kusursuz tamamlandı."
        if outcome == "partial":
            return f"{n}, kısmi başarı. Veriler eksik ama değerli şeyler öğrendik."
        return f"{n}, görev başarısız oldu ama mürettebat güvende. Bir sonraki tasarımı birlikte güçlendirelim."

    def ask_menu(self):
        return [
            ("Ne yapmalıyım?", "advice"),
            ("Görev öner", "suggest"),
            ("Uzay havası / Fırtına", "forecast"),
            ("En iyi fırlatma saati", "best"),
            ("Ajans durumu", "status"),
            ("Koloniler nasıl?", "colonies"),
        ]

    def answer(self, key):
        g, n = self.g, self.n
        if key == "advice":
            t, txt, _ = self.advisor()
            return txt
        if key == "suggest":
            return self.suggest()[0]
        if key == "forecast":
            return self.forecast()
        if key == "best":
            d = g.s.get("last_design")
            fs = 60
            if d:
                from . import rocket as R
                fs = R.analyze(g, d).get("flight_sec", 60) or 60
            return self.best_time_text(fs)
        if key == "status":
            st = g.s["stats"]
            rate = (st["success"] / st["launches"] * 100) if st["launches"] else 0
            return (f"{n}: Seviye {g.s['agency']['level']} ({g.badge()}). Kasada {g.money} Para, {g.rp} Puan. "
                    f"{st['launches']} fırlatma, başarı oranı %{rate:.0f}. {g.colony_count()} koloni.")
        if key == "colonies":
            cols = [(p, c) for p, c in g.s["colonies"].items() if c]
            if not cols:
                return f"{n}, henüz koloni yok. Bir gezegene iniş yap ve koloni kur."
            parts = [f"{D.PLANET[p]['name']}: Sv{c['level']}, {int(c['pop'])} kişi, mutluluk %{int(c['happiness'])}" for p, c in cols]
            return f"{n}, " + " · ".join(parts) + "."
        return self.greet()


# ===========================================================================
# NOVA YÜZÜ
# ===========================================================================
def draw_nova_face(surf, center, size, t, talk=0.0, mood="calm", level=1):
    """Simsiyah ekranda mavi göz gibi parlayan yüz; konuşurken ağzı oynar."""
    x, y = int(center[0]), int(center[1])
    s = size
    col = {"calm": C["cyan"], "alert": C["red"], "happy": C["green"], "think": C["violet"]}.get(mood, C["cyan"])
    # dış halkalar
    draw_glow(surf, (x, y), s * 1.25, scale_color(col, 0.7), 0.55 + 0.15 * math.sin(t * 2))
    pygame.draw.circle(surf, (4, 6, 14), (x, y), int(s * 0.95))
    for i in range(level):
        r = int(s * (0.98 + i * 0.09))
        a0 = t * (0.8 + i * 0.4) * (1 if i % 2 == 0 else -1)
        for k in range(3):
            st = a0 + k * math.tau / 3
            pygame.draw.arc(surf, scale_color(col, 0.9 - i * 0.2), (x - r, y - r, r * 2, r * 2), st, st + 1.4, 2)
    pygame.draw.circle(surf, scale_color(col, 0.55), (x, y), int(s * 0.95), 2)
    # ekran
    sr = pygame.Rect(0, 0, int(s * 1.3), int(s * 1.0))
    sr.center = (x, y)
    pygame.draw.rect(surf, (2, 8, 18), sr, border_radius=int(s * 0.25))
    pygame.draw.rect(surf, scale_color(col, 0.35), sr, 2, border_radius=int(s * 0.25))
    # gözler
    blink = 1.0
    bp = (t % 4.3)
    if bp < 0.12:
        blink = max(0.08, abs(bp - 0.06) / 0.06)
    ex = s * 0.3
    ey = y - s * 0.12
    look = math.sin(t * 0.7) * s * 0.05
    for side in (-1, 1):
        cx = x + side * ex + look
        eh = max(2, int(s * 0.2 * blink))
        er = pygame.Rect(0, 0, int(s * 0.24), eh)
        er.center = (int(cx), int(ey))
        draw_glow(surf, er.center, s * 0.3, col, 0.9)
        pygame.draw.ellipse(surf, lerp_color(col, C["white"], 0.5), er)
        if mood == "happy":
            pygame.draw.rect(surf, (2, 8, 18), (er.x, er.centery, er.w, er.h))
    # ağız (ses dalgası)
    my = y + s * 0.22
    n = 9
    w = s * 0.7
    for i in range(n):
        px = x - w / 2 + w * i / (n - 1)
        amp = talk * (0.35 + 0.65 * abs(math.sin(t * 17 + i * 1.3))) * s * 0.14
        amp *= 1 - abs(i - (n - 1) / 2) / n
        h = max(2, int(amp * 2 + 2))
        pygame.draw.rect(surf, col, (int(px) - 2, int(my - h / 2), 4, h), border_radius=2)
    if talk > 0.05:
        draw_glow(surf, (x, my), s * 0.4, col, 0.4 * talk)
    # tarama çizgisi
    sy = sr.y + (t * 40) % sr.h
    pygame.draw.line(surf, scale_color(col, 0.25), (sr.x + 6, sy), (sr.right - 6, sy))


class NovaBubble:
    """Ekranın sol altında NOVA'nın yüzü ve daktilo efektli konuşma balonu."""

    def __init__(self, audio=None):
        self.audio = audio
        self.queue = []
        self.text = ""
        self.shown = 0.0
        self.timer = 0.0
        self.t = 0.0
        self.show = 0.0
        self.target_show = 0.0
        self.mood = "calm"
        self.level = 1
        self.highlight = None
        self.pos = "bottom"
        self.x = 24

    def say(self, text, mood="calm", highlight=None, priority=False):
        if not text:
            return
        text = tr(text)
        if priority:
            self.queue.insert(0, (text, mood, highlight))
            self.timer = 0
            self.text = ""
        else:
            if self.queue and self.queue[-1][0] == text:
                return
            if text == self.text and self.timer > 0:
                return
            self.queue.append((text, mood, highlight))
        del self.queue[6:]

    def clear(self):
        self.queue.clear()
        self.timer = 0
        self.text = ""
        self.target_show = 0

    def skip(self):
        if self.text and self.shown < len(self.text):
            self.shown = len(self.text)
        else:
            self.timer = 0

    def update(self, dt):
        self.t += dt
        if self.timer <= 0 and self.queue:
            self.text, self.mood, self.highlight = self.queue.pop(0)
            self.shown = 0
            self.timer = 3.2 + len(self.text) * 0.045
            self.target_show = 1
            if self.audio:
                self.audio.speak(self.text)
        if self.text:
            self.shown = min(len(self.text), self.shown + dt * 55)
            self.timer -= dt
            if self.timer <= 0 and not self.queue:
                self.target_show = 0
                if self.show < 0.02:
                    self.text = ""
                    self.highlight = None
        self.show += (self.target_show - self.show) * min(1.0, dt * 9)

    def handle(self, e):
        # Balon tıklamayı yutmaz (altındaki butonlar çalışmaya devam eder);
        # sadece metni hızlandırır.
        if self.show > 0.5 and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.rect().collidepoint(e.pos):
                self.skip()
        return False

    def rect(self):
        return pygame.Rect(self.x, H - 292, 600, 140)

    @property
    def talking(self):
        return bool(self.text) and self.shown < len(self.text)

    def draw(self, surf):
        if self.show < 0.02 or not self.text:
            return
        k = ease_out_back(self.show)
        r = self.rect()
        r.y += int((1 - k) * 80)
        alpha = int(255 * clamp(self.show, 0, 1))
        col = {"alert": C["red"], "happy": C["green"]}.get(self.mood, C["cyan"])
        glass_panel(surf, r, col, 220, 18, glow=True, offset_alpha=alpha)
        talk = 1.0 if self.talking else 0.0
        draw_nova_face(surf, (r.x + 70, r.centery), 46, self.t, talk, self.mood, self.level)
        draw_text(surf, "NOVA", (r.x + 140, r.y + 14), 15, col, bold=True, alpha=alpha)
        draw_text(surf, f"AI · SV{self.level}", (r.right - 18, r.y + 14), 12, C["text_dim"], anchor="topright", alpha=alpha)
        vis = self.text[:int(self.shown)]
        lines = wrap_text(vis, 17, r.w - 170, raw=True)
        for i, ln in enumerate(lines[:4]):
            draw_text(surf, ln, (r.x + 140, r.y + 38 + i * 23), 17, C["text"], alpha=alpha, raw=True)
        if self.queue:
            draw_text(surf, f"+{len(self.queue)}", (r.right - 18, r.bottom - 22), 12, col, anchor="topright", alpha=alpha)
