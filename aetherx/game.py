# -*- coding: utf-8 -*-
"""
KOZMOGENİS // OYUN MANTIĞI
Ajans durumu, saat, üs binaları, araştırma, astronotlar, depo, yakıt,
koloniler, günlük/haftalık görevler, başarımlar, güneş fırtınası takvimi,
rastgele olaylar, diplomasi ve kayıt sistemi.

Bu modül pygame kullanmaz; tamamen test edilebilir saf Python'dur.
"""
import copy
import json
import math
import random
import time

from . import data as D
from .config import (AUTOSAVE_SEC, GAME_MIN_PER_SEC, MARKET_FUEL_PRICE, MIN_PER_DAY,
                     MIN_PER_HOUR, RENAME_COST, REPAIR_KIT_PRICE, SAVE_DIR, SAVE_FILE,
                     SAVE_VERSION, START_MONEY, START_RP, STARDUST_TO_RP)

START_OWNED = ["probe", "orbiter", "capsule", "solid", "liquid", "battery", "solar", "low", "high", "camera"]


def _clamp(v, a, b):
    return a if v < a else b if v > b else v


# ===========================================================================
# YENİ DURUM
# ===========================================================================
def new_state(name="AETHER", color=(62, 230, 255)):
    rng = random.Random()
    st = {
        "version": SAVE_VERSION,
        "created": time.time(),
        "seed": rng.randint(1, 10 ** 9),
        "agency": {
            "name": name.strip() or "AETHER",
            "color": list(color),
            "level": 1, "xp": 0,
            "money": START_MONEY, "rp": START_RP,
            "rep": 10, "renames": 0, "income_mod": 0, "focus": "science",
        },
        "suit": {"type": "balanced", "dur": 0, "mob": 0, "life": 0},
        "clock": {"minutes": 8 * 60},
        "buildings": {b["key"]: b["start"] for b in D.BUILDINGS},
        "research": {"done": [], "active": None},
        "owned": list(START_OWNED),
        "crew": [],
        "next_crew_id": 1,
        "inventory": {"moon_rock": 0, "red_ore": 0, "sulfur": 0, "gas": 0, "astro_ore": 0,
                      "stardust": 0, "repair_kit": 2},
        "fuel": 80.0,
        "visits": {p: 0 for p in D.PLANET_ORDER},
        "landings": {p: 0 for p in D.PLANET_ORDER},
        "colonies": {p: None for p in D.PLANET_ORDER},
        "trade": False,
        "quests": {"daily": [], "weekly": [], "day": -1, "week": -1},
        "achievements": [],
        "stats": {"launches": 0, "success": 0, "partial": 0, "fail": 0, "asteroids": 0, "stardust": 0,
                  "photos": 0, "rescues": 0, "earned": 0, "spent": 0, "sold": 0, "flawless": 0,
                  "research_done": 0, "distance": 0},
        "storms": [],
        "event": {"pending": None, "next_min": 8 * 60 + 18 * 60, "seen": []},
        "diplomacy": {p["key"]: {"relation": p["relation"], "pact": False} for p in D.PARTNERS},
        "pads": [None, None, None],
        "history": [],
        "log": [],
        "last_design": None,
        "settings": {"sound": True, "music": 0.55, "sfx": 0.8, "fullscreen": False, "animations": True,
                     "show_fps": False},
        "flags": {"victory": False, "victory_seen": False, "tutorial": 0, "first_base": True},
    }
    # başlangıç kadrosu: plan gereği her yolculuğa 3 astronot alınabilir
    return st


# ===========================================================================
# OYUN
# ===========================================================================
class Game:
    def __init__(self):
        self.s = None
        self.notes = []            # (metin, renk_anahtarı, ikon, ses)
        self.autosave_t = 0.0
        self.rng = random.Random()
        self.last_day = None
        self.save_error = None
        self.renamed = False

    # ------------------------------------------------------------------ kayıt
    def new(self, name, color, suit="balanced", focus="science"):
        self.s = new_state(name, color)
        self.s["suit"]["type"] = suit if suit in D.SUIT else "balanced"
        self.s["agency"]["focus"] = focus if focus in D.FOCUS_BY_KEY else "science"
        self.rng.seed(self.s["seed"])
        for t in ("pilot", "engineer", "scientist"):
            self._add_crew(t)
        self._ensure_storms()
        self._refresh_quests(force=True)
        self.log(f"{self.name} kuruldu. Başlangıç bütçesi {START_MONEY} Para.", "good")
        self.save()
        return self.s

    def has_save(self):
        try:
            return SAVE_FILE.exists()
        except Exception:
            return False

    def save_summary(self):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                s = json.load(f)
            a = s.get("agency", {})
            cols = [p for p, c in s.get("colonies", {}).items() if c]
            day = int(s.get("clock", {}).get("minutes", 0) // MIN_PER_DAY) + 1
            return {"name": a.get("name", "?"), "level": a.get("level", 1), "money": a.get("money", 0),
                    "rp": a.get("rp", 0), "day": day, "colonies": cols,
                    "color": tuple(a.get("color", (62, 230, 255)))}
        except Exception:
            return None

    def save(self):
        if not self.s:
            return False
        try:
            SAVE_DIR.mkdir(parents=True, exist_ok=True)
            tmp = SAVE_FILE.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.s, f, ensure_ascii=False, indent=1)
            tmp.replace(SAVE_FILE)
            self.save_error = None
            return True
        except Exception as e:  # pragma: no cover
            self.save_error = str(e)
            return False

    def load(self):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                s = json.load(f)
        except Exception:
            return False
        if not isinstance(s, dict) or "agency" not in s:
            return False
        self.s = self._normalize(s)
        self.rng.seed(self.s["seed"] + int(self.s["clock"]["minutes"]))
        self._ensure_storms()
        self._refresh_quests()
        return True

    def delete_save(self):
        try:
            if SAVE_FILE.exists():
                SAVE_FILE.unlink()
            return True
        except Exception:
            return False

    @staticmethod
    def _deep_fill(dst, default):
        """Eksik anahtarları varsayılanla doldurur (eski kayıtlar NaN üretmesin)."""
        for k, v in default.items():
            if k not in dst:
                dst[k] = copy.deepcopy(v)
            elif isinstance(v, dict) and isinstance(dst[k], dict):
                Game._deep_fill(dst[k], v)
            elif isinstance(v, (int, float)) and not isinstance(v, bool) and not isinstance(dst[k], (int, float)):
                dst[k] = copy.deepcopy(v)
        return dst

    def _normalize(self, s):
        base = new_state(s.get("agency", {}).get("name", "AETHER"))
        # koloniler ve pad'ler None olabilir; onları koru
        cols = s.get("colonies") if isinstance(s.get("colonies"), dict) else {}
        pads = s.get("pads") if isinstance(s.get("pads"), list) else [None, None, None]
        self._deep_fill(s, base)
        s["colonies"] = {p: cols.get(p) for p in D.PLANET_ORDER}
        s["pads"] = (pads + [None, None, None])[:3]
        for p, c in s["colonies"].items():
            if c:
                c.setdefault("buildings", {})
                for b in D.COLONY_BUILDINGS:
                    c["buildings"].setdefault(b["key"], 0)
                c.setdefault("storage", 0.0)
                c.setdefault("food", 60.0)
                c.setdefault("happy_buff", 0.0)
                c.setdefault("level", 1)
                c.setdefault("pop", 6.0)
                c.setdefault("happiness", 65.0)
        for c in s["crew"]:
            c.setdefault("rank", 1)
            c.setdefault("streak", 0)
            c.setdefault("tired", False)
            c.setdefault("status", "ready")
            c.setdefault("timer", 0.0)
            c.setdefault("trips", 0)
        s["version"] = SAVE_VERSION
        return s

    # ------------------------------------------------------------- kısayollar
    @property
    def name(self):
        return self.s["agency"]["name"]

    @property
    def color(self):
        return tuple(self.s["agency"]["color"])

    @property
    def money(self):
        return self.s["agency"]["money"]

    @property
    def rp(self):
        return self.s["agency"]["rp"]

    def lvl(self, key):
        return int(self.s["buildings"].get(key, 0))

    @property
    def nova_level(self):
        return self.lvl("nova")

    def notify(self, text, color="cyan", icon="check", sound=None):
        self.notes.append((text, color, icon, sound))

    def log(self, text, tone="info"):
        self.s["log"].insert(0, {"text": text, "tone": tone, "time": self.time_label()})
        del self.s["log"][120:]

    def spend(self, amount):
        amount = int(round(amount))
        if self.s["agency"]["money"] < amount:
            return False
        self.s["agency"]["money"] -= amount
        self.s["stats"]["spent"] += amount
        return True

    def earn(self, amount, rp=0):
        amount = int(round(amount))
        self.s["agency"]["money"] += amount
        self.s["stats"]["earned"] += max(0, amount)
        if rp:
            self.s["agency"]["rp"] += int(round(rp))
        self._check_achievements()

    # ------------------------------------------------------------------ zaman
    @property
    def minutes(self):
        return self.s["clock"]["minutes"]

    @property
    def day(self):
        return int(self.minutes // MIN_PER_DAY) + 1

    @property
    def week(self):
        return (self.day - 1) // 7 + 1

    def hour_of_day(self):
        return (self.minutes % MIN_PER_DAY) / MIN_PER_HOUR

    def time_label(self, minutes=None):
        m = self.minutes if minutes is None else minutes
        d = int(m // MIN_PER_DAY) + 1
        hh = int((m % MIN_PER_DAY) // 60)
        mm = int(m % 60)
        return f"Gün {d}  {hh:02d}:{mm:02d}"

    def is_night(self):
        h = self.hour_of_day()
        return h < 6.5 or h > 19.5

    def update(self, dt):
        """Gerçek saniye ile ilerler."""
        if not self.s:
            return
        from . import settings as _SET
        dm = dt * GAME_MIN_PER_SEC * float(_SET.get("game_speed"))        # AYARLAR > OYUN: oyun hızı
        old_min = self.minutes
        self.s["clock"]["minutes"] += dm
        new_min = self.minutes
        # saatlik işler
        if int(new_min // 60) != int(old_min // 60):
            for _ in range(int(new_min // 60) - int(old_min // 60)):
                self._hourly()
        # günlük işler
        if int(new_min // MIN_PER_DAY) != int(old_min // MIN_PER_DAY):
            self._daily()
        self._update_research(dt)
        self._update_crew(dt, dm)
        self._update_fuel(dm)
        self._update_pads(dt)
        self._ensure_storms()
        self._update_events()
        self.autosave_t += dt
        if self.autosave_t >= AUTOSAVE_SEC:
            self.autosave_t = 0.0
            self.save()

    def _hourly(self):
        self._tick_colonies()

    def _daily(self):
        a = self.s["agency"]
        grant = 140 + a["level"] * 18 + a["rep"] * 3 + a["income_mod"]
        pacts = sum(60 for p in self.s["diplomacy"].values() if p["pact"])
        total = max(0, int(grant + pacts))
        self.earn(total)
        self.log(f"Günlük devlet desteği ve ortaklıklar: +{total} Para", "good")
        self.notify(f"Yeni gün! Günlük gelir +{total} Para", "gold", "money", "coin")
        self._refresh_quests()

    # ---------------------------------------------------------------- XP/Level
    def add_xp(self, n):
        a = self.s["agency"]
        a["xp"] += int(n)
        ups = 0
        while a["xp"] >= D.xp_needed(a["level"]) and a["level"] < 60:
            a["xp"] -= D.xp_needed(a["level"])
            a["level"] += 1
            ups += 1
        if ups:
            self.notify(f"Ajans seviyesi {a['level']}! {self.badge()}", "gold", "star", "levelup")
            self.log(f"Ajans seviyesi {a['level']} oldu.", "good")
        return ups

    def badge(self):
        name = D.BADGES[0][1]
        for lv, n in D.BADGES:
            if self.s["agency"]["level"] >= lv:
                name = n
        return name

    def xp_progress(self):
        a = self.s["agency"]
        need = D.xp_needed(a["level"])
        return a["xp"], need, a["xp"] / need

    # ---------------------------------------------------------------- binalar
    def upgrade_cost(self, key):
        b = D.BUILDING[key]
        nxt = self.lvl(key) + 1
        if nxt > b["max"]:
            return None
        cost = b["costs"].get(nxt, 0)
        return cost

    def can_upgrade(self, key):
        cost = self.upgrade_cost(key)
        if cost is None:
            return False, "Maksimum seviye"
        if self.money < cost:
            return False, f"{cost} Para gerekli"
        return True, ""

    def upgrade(self, key):
        ok, why = self.can_upgrade(key)
        if not ok:
            return False, why
        cost = self.upgrade_cost(key)
        self.spend(cost)
        self.s["buildings"][key] = self.lvl(key) + 1
        b = D.BUILDING[key]
        lv = self.lvl(key)
        self.add_xp(40 + lv * 20)
        self.log(f"{b['name']} Seviye {lv} oldu ({cost} Para).", "good")
        self.notify(f"{b['name']} > Seviye {lv}", "cyan", b["icon"], "levelup")
        self._check_achievements()
        return True, ""

    # ------------------------------------------------------------- araştırma
    def req_met(self, req):
        if not req:
            return True
        kind, planet, n = req
        if kind == "visit":
            return self.s["visits"].get(planet, 0) >= n
        return True

    def req_text(self, req):
        if not req:
            return "-"
        kind, planet, n = req
        have = self.s["visits"].get(planet, 0)
        return f"{D.TO[planet]} {n} kez git ({min(have, n)}/{n})"

    def research_state(self, key):
        r = self.s["research"]
        if key in r["done"]:
            return "done"
        if r["active"] and r["active"]["key"] == key:
            return "active"
        if self.req_met(D.RESEARCH_BY_KEY[key]["req"]):
            return "available"
        return "locked"

    def has_tech(self, key):
        return key is None or key in self.s["research"]["done"]

    def research_duration(self):
        d = D.RESEARCH_TIME[self.lvl("research")]
        if self.has_pact("ESA"):
            d *= 0.9
        return d

    def research_cost(self, key):
        r = D.RESEARCH_BY_KEY[key]
        disc = D.RESEARCH_DISCOUNT[self.lvl("research")]
        return r["rp"], int(round(r["money"] * (1 - disc)))

    def start_research(self, key):
        st = self.research_state(key)
        if st == "done":
            return False, "Zaten tamamlandı"
        if st == "locked":
            return False, "Şart sağlanmadı: " + self.req_text(D.RESEARCH_BY_KEY[key]["req"])
        if self.s["research"]["active"]:
            return False, "Laboratuvar meşgul"
        rp, money = self.research_cost(key)
        if self.rp < rp:
            return False, f"{rp} Araştırma Puanı gerekli"
        if self.money < money:
            return False, f"{money} Para gerekli"
        self.s["agency"]["rp"] -= rp
        self.spend(money)
        dur = self.research_duration()
        self.s["research"]["active"] = {"key": key, "t": 0.0, "dur": dur}
        self.log(f"Araştırma başladı: {D.RESEARCH_BY_KEY[key]['name']} ({int(dur)} sn)", "info")
        return True, ""

    def research_progress(self):
        a = self.s["research"]["active"]
        if not a:
            return None
        return a["key"], a["t"] / a["dur"], a["dur"] - a["t"]

    def _update_research(self, dt):
        a = self.s["research"]["active"]
        if not a:
            return
        a["t"] += dt
        if a["t"] >= a["dur"]:
            key = a["key"]
            self.s["research"]["done"].append(key)
            self.s["research"]["active"] = None
            self.s["stats"]["research_done"] += 1
            r = D.RESEARCH_BY_KEY[key]
            self.add_xp(80)
            self.log(f"Araştırma tamamlandı: {r['name']}", "good")
            self.notify(f"Araştırma tamamlandı: {r['name']}", "green", "flask", "success")
            self.track("research")
            self._check_achievements()

    def process_stardust(self, n=None):
        have = self.s["inventory"]["stardust"]
        n = have if n is None else min(n, have)
        if n <= 0:
            return 0
        self.s["inventory"]["stardust"] -= n
        gain = n * STARDUST_TO_RP
        self.s["agency"]["rp"] += gain
        self.notify(f"{n} Yıldız Tozu işlendi: +{gain} Puan", "cyan", "dust", "pickup")
        return gain

    # ---------------------------------------------------------------- kıyafet
    def suit_stats(self):
        su = self.s["suit"]
        base = D.SUIT.get(su["type"], D.SUIT["balanced"])
        return {"dur": base["dur"] + su["dur"], "mob": base["mob"] + su["mob"], "life": su["life"]}

    def sick_mult(self):
        """Radyasyon / hastalık birikimi çarpanı (dayanıklılık arttıkça düşer)."""
        return max(0.4, 1.25 - 0.15 * self.suit_stats()["dur"])

    def injury_chance(self):
        """Çarpışmada her astronot için yaralanma olasılığı."""
        return max(0.0, 0.2 - 0.045 * self.suit_stats()["dur"])

    def repair_mult(self):
        return max(0.55, 1.3 - 0.12 * self.suit_stats()["mob"])

    def mining_mult(self):
        return 0.8 + 0.1 * self.suit_stats()["mob"]

    def o2_mult(self):
        return 1.0 + 0.12 * self.suit_stats()["life"]

    def focus(self):
        return self.s["agency"].get("focus", "science")

    def suit_upgrade_cost(self, track):
        lv = self.s["suit"][track]
        if lv >= D.SUIT_TRACK[track]["max"]:
            return None
        return 120 + 110 * lv, 400 + 350 * lv

    def suit_upgrade(self, track):
        cost = self.suit_upgrade_cost(track)
        if cost is None:
            return False, "Maksimum seviye"
        if self.lvl("research") < 1:
            return False, "Araştırma Merkezi gerekli"
        rp, money = cost
        if self.rp < rp:
            return False, f"{rp} Araştırma Puanı gerekli"
        if self.money < money:
            return False, f"{money} Para gerekli"
        self.s["agency"]["rp"] -= rp
        self.spend(money)
        self.s["suit"][track] += 1
        tr_ = D.SUIT_TRACK[track]
        self.add_xp(50)
        self.log(f"Kıyafet geliştirildi: {tr_['name']} Seviye {self.s['suit'][track]}", "good")
        self.notify(f"Kıyafet geliştirildi: {tr_['name']} Seviye {self.s['suit'][track]}", "green", tr_["icon"], "levelup")
        return True, ""

    # ----------------------------------------------------------------- parçalar
    def part_unlocked(self, slot, key):
        p = D.PART[slot][key]
        return self.has_tech(p.get("research"))

    def part_owned(self, slot, key):
        return key in self.s["owned"]

    def buy_part(self, slot, key):
        p = D.PART[slot][key]
        if self.part_owned(slot, key):
            return False, "Zaten sahipsin"
        if not self.part_unlocked(slot, key):
            r = D.RESEARCH_BY_KEY.get(p.get("research"), {})
            return False, f"Araştırma gerekli: {r.get('name', '?')}"
        if not self.spend(p["cost"]):
            return False, f"{p['cost']} Para gerekli"
        self.s["owned"].append(key)
        self.log(f"Parça satın alındı: {p['name']} ({p['cost']} Para)", "good")
        self.notify(f"{p['name']} satın alındı", "cyan", "box", "clunk")
        return True, ""

    # --------------------------------------------------------------- astronot
    def crew_cap(self):
        return D.ASTRO_CAP[self.lvl("astro")]

    def _add_crew(self, ctype):
        cid = self.s["next_crew_id"]
        self.s["next_crew_id"] += 1
        name = f"{self.rng.choice(D.FIRST_NAMES)} {self.rng.choice(D.LAST_NAMES)}"
        c = {"id": cid, "name": name, "type": ctype, "rank": 1, "streak": 0, "tired": False,
             "status": "ready", "timer": 0.0, "trips": 0}
        self.s["crew"].append(c)
        return c

    def crew_by_id(self, cid):
        for c in self.s["crew"]:
            if c["id"] == cid:
                return c
        return None

    def hire(self, ctype):
        t = D.CREW_TYPE[ctype]
        if len(self.s["crew"]) >= self.crew_cap():
            return False, "Kadro dolu (Astronot Merkezi'ni yükselt)"
        if not self.spend(t["hire"]):
            return False, f"{t['hire']} Para gerekli"
        c = self._add_crew(ctype)
        self.add_xp(15)
        self.log(f"{t['name']} işe alındı: {c['name']}", "good")
        self.notify(f"Yeni {t['name']}: {c['name']}", "cyan", "astro", "pickup")
        self._check_achievements()
        return True, ""

    def dismiss(self, cid):
        c = self.crew_by_id(cid)
        if not c:
            return False, "Bulunamadı"
        if c["status"] == "mission":
            return False, "Görevdeki astronot ayrılamaz"
        self.s["crew"].remove(c)
        self.log(f"{c['name']} ajanstan ayrıldı.", "warn")
        return True, ""

    def train(self, cid):
        c = self.crew_by_id(cid)
        if not c:
            return False, "Bulunamadı"
        if c["rank"] >= D.MAX_RANK:
            return False, "Maksimum rütbe"
        if c["status"] != "ready":
            return False, "Astronot meşgul"
        cost = D.TRAIN_COST * c["rank"]
        if not self.spend(cost):
            return False, f"{cost} Para gerekli"
        c["status"] = "training"
        c["timer"] = D.TRAIN_SEC / D.TRAIN_SPEED[self.lvl("astro")]
        self.log(f"{c['name']} eğitime başladı.", "info")
        return True, ""

    def rest(self, cid):
        c = self.crew_by_id(cid)
        if not c:
            return False, "Bulunamadı"
        if c["status"] != "ready":
            return False, "Astronot meşgul"
        if not c["tired"] and c["streak"] == 0:
            return False, "Zaten dinç"
        c["status"] = "resting"
        c["timer"] = D.REST_HOURS[self.lvl("rec")] * 60.0       # oyun dakikası
        self.log(f"{c['name']} Eğlence Alanı'nda dinleniyor.", "info")
        return True, ""

    def make_sick(self, c, reason="Hastalandı"):
        if c["status"] in ("sick",):
            return
        c["status"] = "sick"
        c["timer"] = D.HEAL_HOURS[self.lvl("medical")] * 60.0
        c["reason"] = reason
        self.notify(f"{c['name']} hastalandı: Sağlık Merkezi'ne alındı", "red", "medic", "alarm")

    def crew_status_label(self, c):
        st = c["status"]
        if st == "ready":
            return "YORGUN" if c["tired"] else "HAZIR"
        return {"sick": "HASTA", "resting": "DİNLENİYOR", "training": "EĞİTİMDE", "mission": "GÖREVDE"}.get(st, st)

    def crew_available(self):
        return [c for c in self.s["crew"] if c["status"] == "ready"]

    def _update_crew(self, dt, dm):
        for c in self.s["crew"]:
            st = c["status"]
            if st == "training":
                c["timer"] -= dt
                if c["timer"] <= 0:
                    c["rank"] = min(D.MAX_RANK, c["rank"] + 1)
                    c["status"] = "ready"
                    self.notify(f"{c['name']} eğitimi bitirdi: Rütbe {c['rank']}", "green", "star", "success")
            elif st in ("sick", "resting"):
                c["timer"] -= dm
                if c["timer"] <= 0:
                    if st == "sick":
                        self.notify(f"{c['name']} iyileşti", "green", "heart", "pickup")
                    else:
                        self.notify(f"{c['name']} dinlendi", "green", "heart", "pickup")
                    c["status"] = "ready"
                    c["tired"] = False
                    c["streak"] = 0

    def crew_roles(self, ids):
        roles = {}
        for cid in ids:
            c = self.crew_by_id(cid)
            if not c:
                continue
            k = c["type"]
            eff = (0.5 if c["tired"] else 1.0) * (1 + 0.12 * (c["rank"] - 1))
            roles[k] = max(roles.get(k, 0.0), eff)
        return roles

    # -------------------------------------------------------------- depo/yakıt
    def depot_cap(self):
        return D.DEPOT_CAP[self.lvl("depot")]

    def depot_used(self):
        inv = self.s["inventory"]
        return sum(inv.get(m["key"], 0) for m in D.MINERALS) + inv.get("stardust", 0) + inv.get("repair_kit", 0)

    def add_item(self, key, n):
        n = int(n)
        if n <= 0:
            return 0
        free = max(0, self.depot_cap() - self.depot_used())
        put = min(free, n)
        self.s["inventory"][key] = self.s["inventory"].get(key, 0) + put
        if put < n:
            self.notify(f"Depo dolu! {n - put} birim kayboldu", "red", "box", "deny")
        return put

    def sell(self, key, n=None):
        have = self.s["inventory"].get(key, 0)
        n = have if n is None else min(n, have)
        if n <= 0:
            return 0
        price = D.MINERAL[key]["price"]
        total = int(round(n * price * (1.15 if self.focus() == "commerce" else 1.0)))
        self.s["inventory"][key] -= n
        self.earn(total)
        self.s["stats"]["sold"] += total
        self.track("sell", amount=total)
        self.log(f"{n} {D.MINERAL[key]['name']} satıldı: +{total} Para", "good")
        self.notify(f"{n} {D.MINERAL[key]['name']} satıldı: +{total} Para", "gold", "money", "coin")
        return total

    def sell_all(self):
        total = 0
        for m in D.MINERALS:
            total += self.sell(m["key"]) or 0
        return total

    def buy_repair_kit(self, n=1):
        cost = REPAIR_KIT_PRICE * n
        if self.depot_used() + n > self.depot_cap():
            return False, "Depo dolu"
        if not self.spend(cost):
            return False, f"{cost} Para gerekli"
        self.s["inventory"]["repair_kit"] += n
        self.notify(f"{n} Tamir Kiti alındı", "orange", "wrench", "clunk")
        return True, ""

    def fuel_cap(self):
        return D.FUEL_CAP[self.lvl("fuel")]

    def fuel_rate(self):
        return D.FUEL_RATE[self.lvl("fuel")]

    def _update_fuel(self, dm):
        self.s["fuel"] = min(self.fuel_cap(), self.s["fuel"] + self.fuel_rate() * dm / 60.0)

    def buy_fuel(self, kg):
        kg = int(kg)
        space = int(self.fuel_cap() - self.s["fuel"])
        kg = min(kg, space)
        if kg <= 0:
            return False, "Tank dolu"
        cost = kg * MARKET_FUEL_PRICE
        if not self.spend(cost):
            return False, f"{cost} Para gerekli"
        self.s["fuel"] += kg
        self.notify(f"Marketten {kg} kg yakıt alındı (-{cost} Para)", "orange", "fuel", "coin")
        return True, ""

    # ---------------------------------------------------------- güneş fırtınası
    def _ensure_storms(self):
        st = self.s["storms"]
        now = self.minutes
        st[:] = [x for x in st if x["start"] + x["dur"] > now - 60]
        last = st[-1]["start"] + st[-1]["dur"] if st else now + 60 * self.rng.uniform(3, 6)
        while len(st) < 5:
            start = last + 60 * self.rng.uniform(5, 13)
            dur = 60 * self.rng.uniform(1.2, 2.6)
            st.append({"start": start, "dur": dur, "power": round(self.rng.uniform(0.5, 1.0), 2)})
            last = start + dur

    def next_storm(self, after=None):
        t = self.minutes if after is None else after
        for x in self.s["storms"]:
            if x["start"] + x["dur"] > t:
                return x
        return None

    def storm_active(self, at=None):
        t = self.minutes if at is None else at
        for x in self.s["storms"]:
            if x["start"] <= t <= x["start"] + x["dur"]:
                return x
        return None

    def storms_between(self, a, b):
        return [x for x in self.s["storms"] if x["start"] < b and x["start"] + x["dur"] > a]

    def best_launch_time(self, flight_min):
        """Fırtınaya denk gelmeyen en yakın fırlatma zamanı (oyun dakikası)."""
        t = self.minutes
        for _ in range(200):
            if not self.storms_between(t, t + flight_min):
                return t
            t += 15
        return t

    # ------------------------------------------------------------- koloniler
    def colony(self, planet):
        return self.s["colonies"].get(planet)

    def colony_count(self):
        return sum(1 for c in self.s["colonies"].values() if c)

    def colony_found_cost(self, planet, discount=0.0):
        return int(D.PLANET[planet]["colony_cost"] * (1 - discount))

    def found_colony(self, planet, discount=0.0):
        if self.colony(planet):
            return False, "Koloni zaten var"
        cost = self.colony_found_cost(planet, discount)
        if not self.spend(cost):
            return False, f"{cost} Para gerekli"
        self.s["colonies"][planet] = {
            "planet": planet, "founded": self.day, "level": 1, "pop": 6.0, "happiness": 70.0,
            "buildings": {b["key"]: (1 if b["key"] in ("house", "mine", "hut") else 0) for b in D.COLONY_BUILDINGS},
            "storage": 0.0, "food": 60.0, "happy_buff": 0.0,
        }
        pname = D.PLANET[planet]["name"]
        self.add_xp(300)
        self.log(f"{pname} kolonisi kuruldu! Bayrakta {self.name} yazıyor.", "good")
        self.notify(f"{pname} kolonisi kuruldu!", "green", "flag", "success")
        self.track("colony", planet)
        if planet == "jupiter" and not self.s["flags"]["victory"]:
            self.s["flags"]["victory"] = True
            self.log("ZAFER: Jüpiter'de koloni kuruldu!", "good")
        self._check_achievements()
        return True, ""

    def colony_capacity(self, c):
        return 4 + c["buildings"]["house"] * 6 + (c["level"] - 1) * 4

    def colony_storage_cap(self, c):
        return 60 + 40 * c["level"] + 20 * c["buildings"]["mine"]

    def colony_happy_target(self, c):
        b = c["buildings"]
        t = 55 + b["gym"] * 8 + b["hospital"] * 6 + b["park"] * 10
        if c["pop"] > self.colony_capacity(c):
            t -= 18
        if c["food"] <= 0:
            t -= 25
        if self.s["trade"] and c["planet"] == "mars" and self.colony("moon"):
            t += 5
        return _clamp(t, 5, 100)

    def colony_work_factor(self, c):
        h = c["happiness"]
        if h < 25:
            return 0.0
        return 0.5 + h / 100.0

    def colony_rates(self, c):
        """Saatlik üretimler."""
        b = c["buildings"]
        mult = D.COLONY_PLANET_MULT[c["planet"]]
        wf = self.colony_work_factor(c)
        pop_k = min(1.0, c["pop"] / 6.0)
        mine = b["mine"] * 1.6 * wf * pop_k
        rp = b["hut"] * 0.7 * (1 + 0.4 * b["school"]) * wf * pop_k * mult
        food_prod = 1.6 + b["house"] * 0.5 * (2.0 if c["planet"] == "mars" else 1.0)
        food_use = c["pop"] * 0.32
        return {"mine": mine, "rp": rp, "food": food_prod - food_use, "food_prod": food_prod, "food_use": food_use}

    def _tick_colonies(self):
        moon = self.colony("moon")
        mars = self.colony("mars")
        trade = self.s["trade"] and moon and mars
        for p, c in self.s["colonies"].items():
            if not c:
                continue
            r = self.colony_rates(c)
            c["storage"] = min(self.colony_storage_cap(c), c["storage"] + r["mine"])
            if r["rp"] > 0:
                c.setdefault("rp_acc", 0.0)
                c["rp_acc"] += r["rp"]
                if c["rp_acc"] >= 1:
                    whole = int(c["rp_acc"])
                    c["rp_acc"] -= whole
                    self.s["agency"]["rp"] += whole
            c["food"] = _clamp(c["food"] + r["food"], 0, 200)
            target = self.colony_happy_target(c) + c["happy_buff"]
            c["happy_buff"] = max(0.0, c["happy_buff"] - 0.8)
            c["happiness"] = _clamp(c["happiness"] + (target - c["happiness"]) * 0.18, 0, 100)
            cap = self.colony_capacity(c)
            if c["happiness"] > 50 and c["food"] > 10 and c["pop"] < cap:
                c["pop"] = min(cap, c["pop"] + 0.18 + c["level"] * 0.05)
            elif c["food"] <= 0 and not c["buildings"]["hospital"]:
                c["pop"] = max(2.0, c["pop"] - 0.2)
        if trade:
            give = min(3.0, mars["food"])
            mars["food"] -= give
            moon["food"] = min(200, moon["food"] + give)

    def colony_build(self, planet, key):
        c = self.colony(planet)
        if not c:
            return False, "Koloni yok"
        b = D.COLONY_BUILDING[key]
        if c["level"] < b["level_req"]:
            return False, f"Koloni Seviye {b['level_req']} gerekli"
        cost = self.colony_build_cost(planet, key)
        if not self.spend(cost):
            return False, f"{cost} Para gerekli"
        c["buildings"][key] += 1
        if key == "gym":
            c["happy_buff"] += 4
        self.add_xp(30)
        self.notify(f"{D.PLANET[planet]['name']}: {b['name']} inşa edildi", "green", b["icon"], "clunk")
        return True, ""

    def colony_build_cost(self, planet, key):
        c = self.colony(planet)
        b = D.COLONY_BUILDING[key]
        n = c["buildings"][key] if c else 0
        mult = D.COLONY_PLANET_MULT[planet]
        disc = 0.85 if (self.s["trade"] and planet == "mars" and self.colony("moon")) else 1.0
        return int(b["cost"] * mult * (1.35 ** n) * disc)

    def colony_action(self, planet, key):
        c = self.colony(planet)
        if not c:
            return False, "Koloni yok"
        a = next(x for x in D.COLONY_ACTIONS if x["key"] == key)
        cost = int(a["cost"] * D.COLONY_PLANET_MULT[planet])
        if not self.spend(cost):
            return False, f"{cost} Para gerekli"
        c["happy_buff"] += a["happy"]
        c["happiness"] = min(100, c["happiness"] + a["happy"] * 0.5)
        if key == "food":
            c["food"] = min(200, c["food"] + 60)
        self.notify(f"{D.PLANET[planet]['name']}: {a['name']}", "pink", a["icon"], "pickup")
        return True, ""

    def colony_level_cost(self, planet):
        c = self.colony(planet)
        return int(1000 * c["level"] * D.COLONY_PLANET_MULT[planet])

    def colony_level_up(self, planet):
        c = self.colony(planet)
        if not c:
            return False, "Koloni yok"
        if c["level"] >= 3:
            return False, "Maksimum seviye"
        need = D.COLONY_LEVEL_POP[c["level"] + 1]
        if c["pop"] < need:
            return False, f"Nüfus {need} olmalı"
        cost = self.colony_level_cost(planet)
        if not self.spend(cost):
            return False, f"{cost} Para gerekli"
        c["level"] += 1
        self.add_xp(200)
        self.notify(f"{D.PLANET[planet]['name']} kolonisi Seviye {c['level']}!", "gold", "star", "levelup")
        self._check_achievements()
        return True, ""

    def toggle_trade(self):
        if not (self.colony("moon") and self.colony("mars")):
            return False, "Ay ve Mars kolonisi gerekli"
        self.s["trade"] = not self.s["trade"]
        return True, ""

    # ----------------------------------------------------------------- görevler
    def _pick_quests(self, templates, n, key):
        avail = [t for t in templates if self.req_met(t.get("req"))]
        self.rng.shuffle(avail)
        out = []
        for t in avail[:n]:
            out.append({"id": t["id"], "text": t["text"], "event": t["event"], "planet": t.get("planet"),
                        "n": t["n"], "p": 0, "money": t["money"], "rp": t["rp"], "done": False, "claimed": False})
        return out

    def _refresh_quests(self, force=False):
        q = self.s["quests"]
        dn, wn = D.BOARD_SLOTS[self.lvl("board")]
        if force or q["day"] != self.day:
            q["daily"] = self._pick_quests(D.DAILY_TEMPLATES, dn, "daily")
            q["day"] = self.day
        if force or q["week"] != self.week:
            q["weekly"] = self._pick_quests(D.WEEKLY_TEMPLATES, wn, "weekly")
            q["week"] = self.week

    def track(self, event, planet=None, amount=1):
        q = self.s["quests"]
        for lst in (q["daily"], q["weekly"]):
            for it in lst:
                if it["done"] or it["event"] != event:
                    continue
                if it["planet"] and it["planet"] != planet:
                    continue
                it["p"] = min(it["n"], it["p"] + amount)
                if it["p"] >= it["n"]:
                    it["done"] = True
                    self.notify(f"Görev tamamlandı: {it['text']}", "lime", "check", "success")

    def claim_quest(self, kind, idx):
        lst = self.s["quests"][kind]
        if idx >= len(lst):
            return False, ""
        it = lst[idx]
        if not it["done"] or it["claimed"]:
            return False, "Henüz tamamlanmadı"
        it["claimed"] = True
        self.earn(it["money"], it["rp"])
        self.add_xp(40 if kind == "daily" else 140)
        self.notify(f"Ödül: +{it['money']} Para, +{it['rp']} Puan", "gold", "money", "coin")
        return True, ""

    def unclaimed_quests(self):
        q = self.s["quests"]
        return sum(1 for lst in (q["daily"], q["weekly"]) for it in lst if it["done"] and not it["claimed"])

    # --------------------------------------------------------------- başarımlar
    def _ach_checks(self):
        s = self.s
        st = s["stats"]
        return {
            "first_launch": st["launches"] >= 1,
            "moon_landing": s["landings"]["moon"] >= 1,
            "asteroid_100": st["asteroids"] >= 100,
            "mars_arrival": s["visits"]["mars"] >= 1,
            "mars_colony": bool(s["colonies"]["mars"]),
            "venus_land": s["landings"]["venus"] >= 1,
            "jupiter_arrival": s["visits"]["jupiter"] >= 1,
            "jupiter_colony": bool(s["colonies"]["jupiter"]) and s["colonies"]["jupiter"]["level"] >= 3,
            "nova3": self.lvl("nova") >= 3,
            "flawless": st["flawless"] >= 1,
            "rescue_10": st["rescues"] >= 10,
            "dust_500": st["stardust"] >= 500,
            "rich": s["agency"]["money"] >= 20000,
            "all_research": len(s["research"]["done"]) >= len(D.RESEARCH),
            "full_crew": len({c["type"] for c in s["crew"]}) >= 5,
            "max_base": all(self.lvl(b["key"]) >= 3 for b in D.BUILDINGS),
            "photographer": st["photos"] >= 50,
            "four_colonies": self.colony_count() >= 4,
        }

    def _check_achievements(self):
        if not self.s:
            return
        got = self.s["achievements"]
        for key, ok in self._ach_checks().items():
            if ok and key not in got:
                got.append(key)
                a = D.ACHIEVEMENT[key]
                if a["money"]:
                    self.s["agency"]["money"] += a["money"]
                self.add_xp(120)
                self.log(f"{self.name}, '{a['name']}' başarımını kazandı!", "good")
                self.notify(f"{self.name}, '{a['name']}' başarımını kazandı!", "gold", "trophy", "levelup")

    # ---------------------------------------------------------------- olaylar
    def _update_events(self):
        ev = self.s["event"]
        if ev["pending"]:
            return
        if self.minutes >= ev["next_min"]:
            seen = ev["seen"]
            pool = [e for e in D.EVENTS if e["id"] not in seen] or D.EVENTS
            if len(pool) == len(D.EVENTS):
                ev["seen"] = []
            e = self.rng.choice(pool)
            ev["pending"] = e["id"]
            ev["next_min"] = self.minutes + MIN_PER_DAY * self.rng.uniform(1.2, 2.4)

    def pending_event(self):
        pid = self.s["event"]["pending"]
        if not pid:
            return None
        for e in D.EVENTS:
            if e["id"] == pid:
                return e
        self.s["event"]["pending"] = None       # bilinmeyen olay kilitlemesin
        return None

    def resolve_event(self, idx):
        e = self.pending_event()
        if not e:
            return None
        ch = e["choices"][idx] if 0 <= idx < len(e["choices"]) else e["choices"][0]
        self.s["event"]["pending"] = None
        self.s["event"]["seen"].append(e["id"])
        notes = self.apply_effects(ch["effects"])
        self.log(f"Karar: {e['title']} - {ch['label']}", "info")
        return notes

    def apply_effects(self, fx):
        a = self.s["agency"]
        notes = []
        if fx.get("money"):
            a["money"] = max(0, a["money"] + fx["money"])
            notes.append(f"Para {fx['money']:+d}")
        if fx.get("rp"):
            a["rp"] = max(0, a["rp"] + fx["rp"])
            notes.append(f"Puan {fx['rp']:+d}")
        if fx.get("rep"):
            a["rep"] = _clamp(a["rep"] + fx["rep"], 0, 100)
            notes.append(f"İtibar {fx['rep']:+d}")
        if fx.get("xp"):
            self.add_xp(fx["xp"])
            notes.append(f"XP +{fx['xp']}")
        if fx.get("income"):
            a["income_mod"] += fx["income"]
            notes.append(f"Günlük gelir {fx['income']:+d}")
        if fx.get("fuel"):
            self.s["fuel"] = _clamp(self.s["fuel"] + fx["fuel"], 0, self.fuel_cap())
            notes.append(f"Yakıt {fx['fuel']:+d} kg")
        if fx.get("stardust"):
            self.add_item("stardust", fx["stardust"])
            notes.append(f"Yıldız Tozu +{fx['stardust']}")
        if fx.get("repair_kit"):
            self.add_item("repair_kit", fx["repair_kit"])
            notes.append(f"Tamir Kiti +{fx['repair_kit']}")
        if fx.get("sick"):
            ready = self.crew_available()
            if ready:
                self.make_sick(self.rng.choice(ready), "Grip")
                notes.append("1 astronot hastalandı")
        return notes

    # -------------------------------------------------------------- diplomasi
    def has_pact(self, key):
        p = self.s["diplomacy"].get(key)
        return bool(p and p["pact"])

    def improve_relation(self, key):
        p = self.s["diplomacy"][key]
        if p["relation"] >= 100:
            return False, "İlişki maksimumda"
        if not self.spend(D.RELATION_COST):
            return False, f"{D.RELATION_COST} Para gerekli"
        p["relation"] = min(100, p["relation"] + 6)
        self.add_xp(10)
        return True, ""

    def sign_pact(self, key):
        p = self.s["diplomacy"][key]
        meta = D.PARTNER[key]
        if p["pact"]:
            return False, "Zaten anlaşma var"
        if p["relation"] < D.PACT_MIN:
            return False, f"İlişki en az {D.PACT_MIN} olmalı"
        if not self.spend(meta["cost"]):
            return False, f"{meta['cost']} Para gerekli"
        p["pact"] = True
        self.add_xp(150)
        self.log(f"{key} ile anlaşma: {meta['perk']}", "good")
        self.notify(f"{key} ile stratejik anlaşma: {meta['perk']}", "gold", "handshake", "success")
        return True, ""

    # ------------------------------------------------------------------ ajans
    def rename(self, new_name):
        new_name = new_name.strip()
        if not new_name:
            return False, "İsim boş olamaz"
        if new_name == self.name:
            return False, "Aynı isim"
        if not self.spend(RENAME_COST):
            return False, f"{RENAME_COST} Para gerekli"
        old = self.name
        self.s["agency"]["name"] = new_name
        self.s["agency"]["renames"] += 1
        self.renamed = True
        self.log(f"Ajans adı değişti: {old} > {new_name}", "info")
        self.notify(f"Yeni ajans adı: {new_name}", "cyan", "flag", "success")
        return True, ""

    # -------------------------------------------------------------- rampalar
    def pad_free(self, size):
        """Bu boyuttaki roket için boş ve açık rampa indeksi (0..2)."""
        lv = self.lvl("pads")
        for i in range(size - 1, lv):
            if self.s["pads"][i] is None:
                return i
        return None

    def _update_pads(self, dt):
        for p in self.s["pads"]:
            if p and p["prep"] > 0:
                p["prep"] = max(0.0, p["prep"] - dt)
                if p["prep"] == 0:
                    self.notify(f"{D.PAD_NAME[p['pad'] + 1]}: roket fırlatmaya hazır!", "orange", "rocket", "beep")

    def reserve_pad(self, design, report, prep=True):
        """Masrafları öder, astronotları ve yakıtı ayırır, rampaya yerleştirir."""
        idx = self.pad_free(report["size"])
        if idx is None:
            return None, "Uygun boş rampa yok"
        if report["blockers"]:
            return None, report["blockers"][0]
        cost = report["cost"]
        if not self.spend(cost):
            return None, f"{cost} Para gerekli"
        use_depot = min(self.s["fuel"], report["fuel_kg"])
        self.s["fuel"] -= use_depot
        for cid in design.get("crew", []):
            c = self.crew_by_id(cid)
            if c:
                c["status"] = "mission"
        pad = {"pad": idx, "design": copy.deepcopy(design), "prep": D.PAD_PREP_SEC[idx + 1] if prep else 0.0,
               "cost": cost}
        self.s["pads"][idx] = pad
        self.s["last_design"] = copy.deepcopy(design)
        self.log(f"{D.PAD_NAME[idx + 1]}: {D.PLANET[design['planet']]['name']} roketi yerleştirildi ({cost} Para).", "info")
        return idx, ""

    def scrub_pad(self, idx):
        p = self.s["pads"][idx]
        if not p:
            return False
        for cid in p["design"].get("crew", []):
            c = self.crew_by_id(cid)
            if c and c["status"] == "mission":
                c["status"] = "ready"
        refund = int(p["cost"] * 0.5)
        self.earn(refund)
        self.s["pads"][idx] = None
        self.notify(f"Fırlatma iptal edildi: +{refund} Para iade", "orange", "cross", "deny")
        return True

    def take_pad(self, idx):
        p = self.s["pads"][idx]
        self.s["pads"][idx] = None
        if p:
            self.s["stats"]["launches"] += 1
            self.track("launch")
            # bu görevde olmayan astronotlar bir tur dinlenmiş sayılır
            on = set(p["design"].get("crew", []))
            for c in self.s["crew"]:
                if c["id"] not in on and c["status"] == "ready" and c["streak"] > 0:
                    c["streak"] = 0
                    c["tired"] = False
            self._check_achievements()
        return p

    # -------------------------------------------------------- görev sonucu
    def complete_mission(self, res):
        """
        res: planet, mode, outcome (success/partial/fail), reason, photos, stardust, rescues,
             asteroids, minerals{}, crew[], damage, landed, radiation, sick_ids[]
        """
        s = self.s
        planet = res["planet"]
        pl = D.PLANET[planet]
        out = res["outcome"]
        mode = res["mode"]
        summary = {"money": 0, "rp": 0, "lines": [], "first_landing": False, "first_visit": False,
                   "minerals": {}, "can_found": False}
        td = res.get("touchdown")
        if td and res.get("landed"):
            line = f"Motorlu iniş: temas {td[0]:.1f} m/s, hedefe {td[3]:.0f} m"
            if res.get("landing_bonus"):
                line += f" · hassas iniş +{res['landing_bonus']} kargo"
            summary["lines"].append(line)

        reached = out in ("success", "partial")
        if reached:
            if s["visits"][planet] == 0:
                summary["first_visit"] = True
            s["visits"][planet] += 1
            self.track("visit", planet)
        base_money = {"moon": 300, "mars": 750, "venus": 950, "jupiter": 2200}[planet]
        mode_k = {"kesif": 1.0, "inis": 1.35, "koloni": 1.15}[mode]
        out_k = {"success": 1.0, "partial": 0.4, "fail": 0.0}[out]
        money = base_money * mode_k * out_k
        if self.has_pact("TUA"):
            money *= 1.1
        rp = 0
        if res["photos"]:
            rp += res["photos"] * 20
            summary["lines"].append(f"{res['photos']} fotoğraf: +{res['photos'] * 20} Puan")
        if res["rescues"]:
            rp += res["rescues"] * 100
            summary["lines"].append(f"{res['rescues']} uydu kurtarma: +{res['rescues'] * 100} Puan")
        roles = self.crew_roles(res["crew"])
        if "scientist" in roles and reached:
            rp += 50
            summary["lines"].append("Bilim İnsanı bonusu: +50 Puan")
        if res.get("landed"):
            if s["landings"][planet] == 0:
                summary["first_landing"] = True
                rp += 200
                summary["lines"].append(f"{D.TO[planet]} ilk iniş: +200 Puan")
            s["landings"][planet] += 1
            self.track("land", planet)
            if not self.colony(planet):
                summary["can_found"] = True
        if summary["first_visit"] and not res.get("landed"):
            rp += 60
            summary["lines"].append(f"{D.TO[planet]} ilk varış: +60 Puan")
        if self.has_pact("NASA"):
            rp *= 1.1
        if self.focus() == "science":
            rp *= 1.2
        rp = int(round(rp))
        money = int(round(money))
        if money:
            summary["lines"].insert(0, f"Görev ödemesi: +{money} Para")
        self.earn(money, rp)
        summary["money"] = money
        summary["rp"] = rp
        # eşyalar
        if res["stardust"]:
            put = self.add_item("stardust", res["stardust"])
            s["stats"]["stardust"] += res["stardust"]
            summary["lines"].append(f"{put} Yıldız Tozu depoya")
            self.track("stardust", amount=res["stardust"])
        for k, n in res.get("minerals", {}).items():
            n = int(n)
            if n > 0:
                put = self.add_item(k, n)
                summary["minerals"][k] = put
                summary["lines"].append(f"{put} {D.MINERAL[k]['name']} depoya")
        # istatistik
        st = s["stats"]
        st["success" if out == "success" else "partial" if out == "partial" else "fail"] += 1
        st["asteroids"] += res["asteroids"]
        st["photos"] += res["photos"]
        st["rescues"] += res["rescues"]
        if res["asteroids"]:
            self.track("asteroid", amount=res["asteroids"])
        if res["photos"]:
            self.track("photo", planet, amount=res["photos"])
        if res["rescues"]:
            self.track("rescue", amount=res["rescues"])
        if out == "success" and res["damage"] == 0:
            st["flawless"] += 1
            self.track("flawless")
        # astronotlar
        for cid in res["crew"]:
            c = self.crew_by_id(cid)
            if not c:
                continue
            c["status"] = "ready"
            c["trips"] += 1
            c["streak"] += 1
            if c["streak"] >= 2:
                c["tired"] = True
            if cid in res.get("sick_ids", []):
                self.make_sick(c, "Radyasyon" if res.get("radiation") else "Uzay hastalığı")
        # XP
        self.add_xp(60 + pl["diff"] * 40 + (60 if out == "success" else 20 if out == "partial" else 5))
        word = {"success": "BAŞARILI", "partial": "KISMİ BAŞARI", "fail": "BAŞARISIZ"}[out]
        s["history"].insert(0, {"planet": planet, "mode": mode, "outcome": out, "day": self.day,
                                "money": money, "rp": rp, "reason": res.get("reason", ""),
                                "photos": res["photos"], "asteroids": res["asteroids"]})
        del s["history"][40:]
        self.log(f"{pl['name']} görevi {word}. +{money} Para, +{rp} Puan.",
                 "good" if out == "success" else "warn" if out == "partial" else "bad")
        self._check_achievements()
        self.save()
        return summary

    def supply_colony(self, planet, crew_n=2):
        """Koloni seferi: mevcut koloniye ikmal ve yeni sakinler."""
        c = self.colony(planet)
        if not c:
            return False
        c["pop"] = min(self.colony_capacity(c) + 4, c["pop"] + 2 + crew_n)
        c["food"] = min(200, c["food"] + 80)
        c["happy_buff"] += 15
        self.add_xp(120)
        self.notify(f"{D.PLANET[planet]['name']} kolonisine ikmal ulaştı!", "green", "box", "success")
        return True

    def pickup_colony_storage(self, planet, cargo_cap):
        """İniş yapan roket koloni deposundaki madeni yüklenebildiği kadar alır."""
        c = self.colony(planet)
        if not c:
            return 0
        n = int(min(c["storage"], cargo_cap))
        c["storage"] -= n
        return n

    # ----------------------------------------------------------- yardımcılar
    def planet_unlocked(self, key):
        return self.req_met(D.PLANET[key]["unlock"])

    def comms_range(self):
        return D.COMMS_RANGE[self.lvl("comms")]

    def victory_progress(self):
        steps = [
            ("Ay'a ulaş", self.s["visits"]["moon"] > 0),
            ("Ay kolonisi", bool(self.colony("moon"))),
            ("Mars'a ulaş", self.s["visits"]["mars"] > 0),
            ("Mars kolonisi", bool(self.colony("mars"))),
            ("Jüpiter'e ulaş", self.s["visits"]["jupiter"] > 0),
            ("Jüpiter'de dev koloni", bool(self.colony("jupiter"))),
        ]
        return steps
