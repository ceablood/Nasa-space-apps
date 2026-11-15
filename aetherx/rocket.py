# -*- coding: utf-8 -*-
"""
AETHER-X // ROKET TASARIM ANALİZİ
Kütle, taşıma kapasitesi, kaldırma gücü, roket sınıfı (küçük/orta/dev),
yakıt ihtiyacı, elektrik dengesi, iletişim menzili, oksijen, mürettebat rolleri
ve 3 barlı risk paneli (başarısızlık / kısmi / tam başarı).

Risk; Dayanıklılık + Motor + Yakıt + Elektrik (+ menzil, mürettebat, fırtına)
bileşenlerinden hesaplanır. Can barı yoktur.
"""
import random

from . import data as D
from .config import GAME_MIN_PER_SEC, MARKET_FUEL_PRICE

BURN_K = 0.55          # kg/sn çarpanı (motor.burn * BURN_K)
RETURN_RESERVE = 1.2   # dönüş için yakıt payı


def empty_design(planet="moon"):
    return {"planet": planet, "mode": "kesif", "hull": "orbiter", "engine": "liquid", "power": "solar",
            "antenna": "low", "payloads": ["camera"], "fuel_pct": 0.7, "crew": []}


def _p(slot, key):
    return D.PART[slot].get(key) if key else None


def sun_avg(planet):
    return (1.0 + D.PLANET[planet]["sun"]) / 2.0


def dark_fraction(planet):
    return sum(b - a for a, b, k in D.PLANET[planet]["zones"] if k == "dark")


def zone_center(planet, kinds):
    zs = [(a + b) / 2 for a, b, k in D.PLANET[planet]["zones"] if k in kinds]
    return zs[0] if zs else 0.5


def engine_speed(engine, planet):
    if engine["key"] == "ion":
        return (engine["speed"] + engine["speed_max"]) / 2 * 0.92
    if engine.get("solar"):
        return max(0.45, min(2.4, engine["speed"] * sun_avg(planet) ** 0.85))
    return engine["speed"]


def analyze(game, d):
    """Tam tasarım raporu döndürür."""
    rep = {"blockers": [], "warnings": [], "issues": [], "components": []}
    planet = d.get("planet", "moon")
    pl = D.PLANET[planet]
    hull = _p("hull", d.get("hull"))
    eng = _p("engine", d.get("engine"))
    pwr = _p("power", d.get("power"))
    ant = _p("antenna", d.get("antenna"))
    pls = [D.PART["payload"][k] for k in d.get("payloads", []) if k in D.PART["payload"]][:D.MAX_PAYLOADS]
    mode = d.get("mode", "kesif")
    crew_ids = list(d.get("crew", []))
    rep.update(planet=planet, mode=mode, hull=hull, engine=eng, power=pwr, antenna=ant, payloads=pls)

    def issue(code, slot=None, sev=1, **kw):
        rep["issues"].append({"code": code, "slot": slot, "sev": sev, **kw})

    # --- eksik / kilitli / satın alınmamış ---------------------------------
    for slot, part, label in (("hull", hull, "Gövde"), ("engine", eng, "Motor"), ("power", pwr, "Elektrik"),
                              ("antenna", ant, "Anten")):
        if not part:
            rep["blockers"].append(f"{label} seçilmedi.")
            issue("missing", slot, 3)
    for slot, part in (("hull", hull), ("engine", eng), ("power", pwr), ("antenna", ant)):
        if part and not game.part_owned(slot, part["key"]):
            if not game.part_unlocked(slot, part["key"]):
                rep["blockers"].append(f"{part['name']} araştırılmadı.")
            else:
                rep["blockers"].append(f"{part['name']} satın alınmadı ({part['cost']} Para).")
            issue("not_owned", slot, 3, name=part["name"])
    for p in pls:
        if not game.part_owned("payload", p["key"]):
            rep["blockers"].append(f"{p['name']} satın alınmadı ({p['cost']} Para).")
            issue("not_owned", "payload", 3, name=p["name"])
    if not game.planet_unlocked(planet):
        rep["blockers"].append(f"{pl['name']} henüz açılmadı: {game.req_text(pl['unlock'])}.")
    if not (hull and eng and pwr and ant):
        rep.update(_empty_numbers())
        _finalize_risk(rep)
        return rep

    # --- mürettebat --------------------------------------------------------
    seats = hull["seats"]
    crew = [game.crew_by_id(c) for c in crew_ids]
    crew = [c for c in crew if c]
    if len(crew) > seats:
        rep["blockers"].append(f"{hull['name']} en fazla {seats} astronot taşır.")
    for c in crew:
        if c["status"] not in ("ready", "mission"):
            rep["blockers"].append(f"{c['name']} şu an {game.crew_status_label(c).lower()}.")
    roles = game.crew_roles([c["id"] for c in crew])
    tired = [c for c in crew if c["tired"]]
    rep["roles"] = roles
    rep["crew_n"] = len(crew)
    if mode in ("inis", "koloni") and not hull["land"]:
        rep["blockers"].append(f"{hull['name']} iniş yapamaz (Kapsül, İniş Modülü veya üstü gerekli).")
        issue("no_land", "hull", 3)
    if mode == "koloni" and hull["key"] not in ("station", "cargo"):
        rep["blockers"].append("Koloni seferi için İstasyon Modülü veya Kargo Gövdesi gerekli.")
        issue("colony_hull", "hull", 3)
    if mode == "inis" and seats > 0 and len(crew) == 0:
        rep["blockers"].append("İnsanlı gövdeyle iniş için en az 1 astronot gerekli.")
        issue("need_crew", "crew", 3)
    if mode == "koloni" and len(crew) < 2:
        rep["blockers"].append("Koloni seferi için en az 2 astronot gerekli.")
        issue("need_crew", "crew", 3)
    heat_ok = game.has_tech("heatshield") or hull.get("heat_shield")
    if pl.get("hot") and mode != "kesif" and not heat_ok:
        rep["blockers"].append("Venüs'e iniş için Sıcaklık Kalkanı araştırması veya Ağır Zırhlı Gövde gerekli.")
        issue("heat", "hull", 3)

    # --- kütle ---------------------------------------------------------------
    fuel_pct = max(0.0, min(1.0, float(d.get("fuel_pct", 0.7))))
    fuel_kg = round(hull["tank"] * fuel_pct, 1)
    mounted = eng["mass"] + pwr["mass"] + ant["mass"] + sum(p["mass"] for p in pls) + fuel_kg
    total = hull["mass"] + mounted
    cap = hull["capacity"]
    lift_bonus = 1.1 if game.has_tech("aero") else 1.0
    size = max(hull["size"], 1 if total <= 150 else 2 if total <= 320 else 3)
    lift = D.PAD_LIFT[size] * eng["lift"] * lift_bonus
    rep.update(fuel_pct=fuel_pct, fuel_kg=fuel_kg, mounted=round(mounted, 1), total=round(total, 1),
               capacity=cap, lift=round(lift), size=size)
    if mounted > cap:
        rep["blockers"].append(f"Taşıma kapasitesi aşıldı: {mounted:.0f}/{cap} kg.")
        issue("overload", "fuel", 3, mounted=mounted, cap=cap)
    elif fuel_pct >= 0.98 or mounted > cap * 0.94:
        rep["warnings"].append("Çok ağır oldun!")
        issue("heavy", "fuel", 1)
    if total > lift:
        rep["blockers"].append(f"Kalkış kütlesi {total:.0f} kg, kaldırma gücü {lift:.0f} kg.")
        issue("lift", "engine", 3, total=total, lift=lift)
    if game.lvl("hangar") < size:
        rep["blockers"].append(f"{D.ROCKET_SIZE_NAME[size]} roket için Montaj Hangarı Seviye {size} gerekli.")
        issue("hangar", "hull", 3, size=size)
    if game.lvl("pads") < size:
        rep["blockers"].append(f"{D.ROCKET_SIZE_NAME[size]} roket için {D.PAD_NAME[size]} açılmalı (Rampa Sv{size}).")
        issue("pad", "hull", 3, size=size)
    elif game.pad_free(size) is None:
        rep["blockers"].append("Uygun rampaların hepsi dolu. Hazırdaki roketi fırlat veya iptal et.")

    # --- hız / süre ---------------------------------------------------------
    pilot = roles.get("pilot", 0.0)
    speed = hull["speed"] * engine_speed(eng, planet)
    if not pilot:
        speed *= 0.85
    flight_sec = pl["dist"] / max(0.2, speed)
    rep.update(speed=round(speed, 2), flight_sec=flight_sec, pilot=pilot,
               dodge=(1.0 + 0.15 * (pilot - 1)) if pilot else 0.45)

    # --- yakıt ----------------------------------------------------------------
    burn = eng["burn"] * BURN_K * (0.9 if game.has_tech("fuelchem") else 1.0)
    cell_use = pwr.get("fuel_use", 0.0)
    fuel_need = (burn + cell_use) * flight_sec
    margin = fuel_kg / (fuel_need * RETURN_RESERVE) if fuel_need > 0.01 else (9.9 if cell_use == 0 else 0.0)
    rep.update(burn=burn, fuel_need=round(fuel_need, 1), fuel_margin=round(margin, 2))
    if fuel_need > 0.01 and margin < 1.0:
        issue("fuel_low", "fuel", 2 if margin > 0.75 else 3, margin=margin, need=fuel_need * RETURN_RESERVE)
    if eng.get("solar") and planet == "jupiter":
        issue("sail_far", "engine", 2)

    # --- elektrik ------------------------------------------------------------
    draw = D.BASE_DRAW + eng["draw"] + ant["draw"] + sum(p["draw"] for p in pls) + 0.15 * len(crew)
    dark = dark_fraction(planet)
    if pwr["kind"] == "solar":
        gen = pwr["gen"] * sun_avg(planet) * (1 - dark)
    elif pwr["kind"] == "fuelcell":
        gen = pwr["gen"] if fuel_kg > 0 else 0.0
    else:
        gen = pwr["gen"]
    balance = gen - draw
    if balance >= 0:
        e_frac = 1.0
    else:
        e_frac = min(1.0, (pwr["cap"] / -balance) / flight_sec)
    rep.update(draw=round(draw, 2), gen=round(gen, 2), e_balance=round(balance, 2), e_frac=e_frac,
               e_cap=pwr["cap"])
    if e_frac < 1.0:
        issue("power_low", "power", 3 if e_frac < 0.5 else 2, frac=e_frac)
    if pwr["kind"] == "solar" and dark > 0:
        issue("dark", "power", 1)
    if eng["key"] == "ion" and pwr["kind"] in ("battery",):
        issue("ion_power", "power", 3)

    # --- iletişim ------------------------------------------------------------
    need_r = pl["range"]
    ant_ok = ant["range"] >= need_r
    tower_ok = game.comms_range() >= need_r
    link_ok = ant_ok and tower_ok
    rep.update(link_ok=link_ok, ant_ok=ant_ok, tower_ok=tower_ok)
    if not ant_ok:
        issue("antenna_range", "antenna", 2, need=need_r)
    if not tower_ok:
        issue("tower_range", "antenna", 2, need=need_r)

    # --- oksijen -------------------------------------------------------------
    if crew:
        o2_sec = hull["o2"] * 3 / max(1, len(crew)) * game.o2_mult()
        o2_ratio = o2_sec / (flight_sec * 1.15)
    else:
        o2_sec, o2_ratio = 0, 9.9
    rep.update(o2_sec=o2_sec, o2_ratio=o2_ratio)
    if crew and o2_ratio < 1.0:
        issue("o2_low", "hull", 3, ratio=o2_ratio)

    # --- rol uyarıları ------------------------------------------------------
    if eng.get("radiation") and crew and "doctor" not in roles:
        issue("need_doctor", "crew", 2)
    if crew and "pilot" not in roles:
        issue("no_pilot", "crew", 1)
    if not crew:
        issue("no_pilot_probe", "crew", 0)
    if crew and "engineer" not in roles:
        issue("no_engineer", "crew", 1)
    if tired:
        issue("tired", "crew", 1, names=[c["name"] for c in tired])
    if not pls:
        issue("no_payload", "payload", 1)
    has = {p["key"] for p in pls}
    if "magneto" not in has:
        issue("no_magneto", "payload", 0)
    if "spectro" not in has and mode == "kesif":
        issue("no_spectro", "payload", 0)

    # --- fırtına -------------------------------------------------------------
    flight_min = flight_sec * GAME_MIN_PER_SEC
    storms = game.storms_between(game.minutes, game.minutes + flight_min)
    rep["storms"] = storms
    rep["flight_min"] = flight_min
    if storms:
        issue("storm", None, 2, start=storms[0]["start"] - game.minutes)

    # --- maliyet -------------------------------------------------------------
    parts_value = hull["cost"] + eng["cost"] + pwr["cost"] + ant["cost"] + sum(p["cost"] for p in pls)
    assembly = parts_value * 0.08
    pad_fee = D.PAD_FEE[size] * (0.9 if game.has_pact("ISRO") else 1.0) * (0.85 if game.focus() == "explore" else 1.0)
    short = max(0.0, fuel_kg - game.s["fuel"])
    fuel_cost = short * MARKET_FUEL_PRICE
    cost = int(round(assembly + pad_fee + fuel_cost))
    rep.update(cost=cost, assembly=int(assembly), pad_fee=int(pad_fee), fuel_cost=int(fuel_cost),
               fuel_short=round(short, 1), parts_value=parts_value)
    if cost > game.money:
        rep["blockers"].append(f"Bütçe yetersiz: {cost} Para gerekli.")

    # --- risk bileşenleri ---------------------------------------------------
    comps = rep["components"]
    dur = hull["dur"]
    hz = pl["risk"] * (1.3 - 0.17 * dur)
    if game.has_tech("aero"):
        hz -= 0.02
    if game.lvl("control") >= 3:
        hz -= 0.02
    if not pilot:
        hz *= 1.25
    hz = max(0.01, hz)
    eng_k = 0.7 if roles.get("engineer") else 1.0
    hz_frac = zone_center(planet, ("asteroids", "belt"))
    comps.append(("fail", hz * 0.45 * eng_k, "Asteroit çarpması: motor kaybı", hz_frac))
    comps.append(("partial", hz * 0.55 + hz * 0.45 * (1 - eng_k), "Asteroit çarpması: anten hasarı", hz_frac))
    if fuel_need > 0.01:
        if margin < 1.0:
            out_ratio = fuel_kg / max(0.1, fuel_need)
            comps.append(("fail", min(0.95, (1 - margin) * 1.5), "Yakıt bitti", min(0.98, out_ratio)))
        elif margin < 1.15:
            comps.append(("partial", 0.05, "Dönüş yakıtı sınırda", 0.95))
    if e_frac < 1.0:
        p = (1 - e_frac) * 0.6
        if eng["key"] == "ion":
            comps.append(("fail", p * 0.8, "Elektrik bitti: iyon motoru durdu", e_frac))
        comps.append(("partial", p, "Elektrik bitti: sistemler karardı", e_frac))
    if not link_ok:
        reach = min(ant["range"], game.comms_range())
        lost_at = {0: 0.15, 1: 0.35, 2: 0.6, 3: 0.8}.get(reach, 0.3)
        rep["link_lost_at"] = lost_at
        comps.append(("partial", 0.55, "Bağlantı koptu: veri alınamadı", lost_at))
    if crew and o2_ratio < 1.0:
        comps.append(("fail", min(0.95, (1 - o2_ratio) * 2.0), "Oksijen bitti", o2_ratio))
    if eng.get("radiation") and crew and "doctor" not in roles:
        comps.append(("partial", min(0.4, 0.12 * game.sick_mult()), "Radyasyon: mürettebat hastalandı", 0.6))
    if pl.get("hot") and not heat_ok:
        comps.append(("partial", 0.2, "Aşırı ısı: sensörler yandı", zone_center(planet, ("heat",))))
    if storms:
        pw = max(s["power"] for s in storms)
        k = 0.5 if "magneto" in has else 1.0
        sfrac = min(0.95, max(0.05, (storms[0]["start"] - game.minutes) / max(1, flight_min)))
        comps.append(("partial", 0.09 * pw * k, "Güneş Fırtınası: elektronik arıza", sfrac))
        comps.append(("fail", 0.03 * pw * k, "Güneş Fırtınası: kontrol kaybı", sfrac))
    if mounted > cap * 0.94 or total > lift * 0.92:
        comps.append(("fail", 0.05, "Kalkışta aşırı yük", 0.02))
    if tired:
        comps.append(("partial", 0.03 * len(tired), "Yorgun mürettebat hatası", 0.5))
    if crew and mode != "kesif":
        sp = max(0.0, (pl["diff"] - 1) * 0.02 * (4 - game.suit_stats()["dur"]))
        if sp > 0:
            comps.append(("partial", sp, "Yüzey koşulları: kıyafet hasarı", 0.97))
        if sp >= 0.06:
            issue("suit_weak", "crew", 1)
    if pilot:
        comps[:] = [(k, p * (1 - 0.2 * min(1.0, pilot)), r, f) for k, p, r, f in comps]
    _finalize_risk(rep)
    return rep


def _empty_numbers():
    return dict(fuel_pct=0, fuel_kg=0, mounted=0, total=0, capacity=0, lift=0, size=1, speed=0, flight_sec=0,
                pilot=0, dodge=0.45, burn=0, fuel_need=0, fuel_margin=0, draw=0, gen=0, e_balance=0, e_frac=0,
                e_cap=0, link_ok=False, ant_ok=False, tower_ok=False, o2_sec=0, o2_ratio=0, roles={}, crew_n=0,
                storms=[], flight_min=0, cost=0, assembly=0, pad_fee=0, fuel_cost=0, fuel_short=0, parts_value=0)


def _finalize_risk(rep):
    pf, pp = 1.0, 1.0
    for kind, p, reason, frac in rep["components"]:
        p = max(0.0, min(0.97, p))
        if kind == "fail":
            pf *= (1 - p)
        else:
            pp *= (1 - p)
    fail = 1 - pf
    partial = (1 - fail) * (1 - pp)
    if rep["blockers"]:
        fail = max(fail, 0.0)
    success = max(0.0, 1 - fail - partial)
    rep["risk"] = {"fail": fail, "partial": partial, "success": success}
    rep["ok"] = not rep["blockers"]
    level = fail + partial * 0.5
    rep["risk_level"] = level
    rep["risk_label"] = "DÜŞÜK" if level < 0.15 else "ORTA" if level < 0.32 else "YÜKSEK" if level < 0.55 else "KRİTİK"


def simulate(rep, runs=400, accuracy=1.0, seed=None):
    """
    Sanal uçuş. Risk bileşenlerini örnekleyerek dağılım ve olası arıza noktalarını verir.
    accuracy < 1 ise sonuçlara gürültü eklenir (Görev Kontrol seviyesine bağlı).
    """
    rng = random.Random(seed)
    counts = {"success": 0, "partial": 0, "fail": 0}
    points = {}
    for _ in range(runs):
        outcome = "success"
        first = None
        for kind, p, reason, frac in sorted(rep["components"], key=lambda c: c[3]):
            noise = 1.0 + rng.uniform(-0.25, 0.25) * (1 - accuracy)
            if rng.random() < p * noise:
                if kind == "fail":
                    outcome = "fail"
                    first = (reason, frac)
                    break
                elif outcome == "success":
                    outcome = "partial"
                    first = first or (reason, frac)
        counts[outcome] += 1
        if first:
            key = first
            points[key] = points.get(key, 0) + 1
    tot = max(1, runs)
    dist = {k: v / tot for k, v in counts.items()}
    top = sorted(points.items(), key=lambda kv: -kv[1])[:4]
    return {"dist": dist, "points": [(r, f, n / tot) for (r, f), n in top]}
