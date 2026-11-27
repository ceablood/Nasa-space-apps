# -*- coding: utf-8 -*-
"""
NOVA OYUN DURUMU ANALİZİ — kampanyanın canlı verisini okuyup somut, sayılı yanıtlar üretir.
Yalnız okur; hiçbir şeyi değiştirmez. Oyun içi adlar (araştırma, maden, parça) i18n.tr ile oyunun diline çevrilir.
"""
from .. import data as D
from .. import i18n
from . import physics as P


def _tr(s):
    return i18n.tr(s)


def _L(ai, pair):
    return ai.L(pair)


def _num(ai, x, d=0):
    return P.fmt_num(x, d, ai.tr_)


def depot(ai, g):
    inv = g.s["inventory"]
    rows = []
    worth = 0
    for k, m in D.MINERAL.items():
        n = int(inv.get(k, 0))
        if n:
            rows.append(f"{_tr(m['name'])} ×{n}")
            worth += n * m.get("price", 0)
    kits = int(inv.get("repair_kit", 0))
    used, cap = g.depot_used(), g.depot_cap()
    head = _L(ai, (f"Depo: {_num(ai, used)}/{_num(ai, cap)} dolu.", f"Depot: {_num(ai, used)}/{_num(ai, cap)} used."))
    if not rows:
        body = _L(ai, (" Satılacak maden yok.", " No minerals to sell."))
    else:
        body = " " + ", ".join(rows) + "." + _L(ai, (f" Hepsinin taban değeri ~{_num(ai, worth)} Para.",
                                                     f" Base value of everything: ~{_num(ai, worth)} credits."))
    tail = _L(ai, (f" Onarım kiti: {kits}.", f" Repair kits: {kits}."))
    if cap and used / cap > 0.85:
        tail += _L(ai, (" Depo dolmak üzere; DEPO ekranından satış yap ya da depoyu yükselt.",
                        " The depot is nearly full; sell from the DEPOT screen or upgrade it."))
    return head + body + tail


def fuel(ai, g):
    f, cap, rate = g.s["fuel"], g.fuel_cap(), g.fuel_rate()
    full_h = (cap - f) / rate if rate > 0 else None
    out = _L(ai, (f"Yakıt: {_num(ai, f)}/{_num(ai, cap)} kg; saatte {_num(ai, rate, 1)} kg üretiliyor.",
                  f"Fuel: {_num(ai, f)}/{_num(ai, cap)} kg; production {_num(ai, rate, 1)} kg per hour."))
    if full_h and full_h > 0.05:
        out += _L(ai, (f" Tam dolması için ~{_num(ai, full_h, 1)} oyun saati gerekir.", f" It will be full in ~{_num(ai, full_h, 1)} game hours."))
    return out


def crew(ai, g):
    cs = g.s["crew"]
    if not cs:
        return _L(ai, ("Henüz ekibin yok. UZAY ÇALIŞANLARI ekranından İŞE AL.", "You have no crew yet. HIRE on the SPACE CREW screen."))
    by = {}
    for c in cs:
        by.setdefault(g.crew_status_label(c), []).append(c["name"])
    parts = [f"{_tr(k)}: {len(v)}" for k, v in by.items()]
    out = _L(ai, (f"Ekip {len(cs)}/{g.crew_cap()} kişi — ", f"Crew {len(cs)}/{g.crew_cap()} — ")) + ", ".join(parts) + "."
    sick = [c["name"] for c in cs if c["status"] == "sick"]
    tired = [c["name"] for c in cs if c["status"] == "ready" and c["tired"]]
    if sick:
        out += _L(ai, (f" Hasta: {', '.join(sick[:4])}; dinlendir ya da sağlık binasını yükselt.",
                       f" Sick: {', '.join(sick[:4])}; let them rest or upgrade medical care."))
    if tired:
        out += _L(ai, (f" Yorgun: {', '.join(tired[:4])}; yorgun astronot görevde daha riskli.",
                       f" Tired: {', '.join(tired[:4])}; tired astronauts are riskier on missions."))
    best = max(cs, key=lambda c: c.get("rank", 1))
    out += _L(ai, (f" En deneyimli: {best['name']} (rütbe {best['rank']}).", f" Most experienced: {best['name']} (rank {best['rank']})."))
    return out


def research_next(ai, g):
    act = g.s["research"]["active"]
    if act:
        r = D.RESEARCH_BY_KEY[act["key"]]
        pct = 100 * act["t"] / max(1e-6, act["dur"])
        return _L(ai, (f"Şu an {_tr(r['name'])} araştırılıyor (%{_num(ai, pct)}). Bitince sana haber veririm.",
                       f"{_tr(r['name'])} is being researched ({_num(ai, pct)}%). I'll tell you when it's done."))
    avail = [r for r in D.RESEARCH if g.research_state(r["key"]) == "available"]
    if not avail:
        locked = [r for r in D.RESEARCH if g.research_state(r["key"]) == "locked"]
        if not locked:
            return _L(ai, ("Bütün araştırmaları tamamladın!", "You have completed all research!"))
        r = locked[0]
        return _L(ai, (f"Şu an açık araştırma yok. Sıradaki ({_tr(r['name'])}) için: {_tr(g.req_text(r['req']))}.",
                       f"No research is available now. For the next one ({_tr(r['name'])}): {_tr(g.req_text(r['req']))}."))
    afford = []
    for r in avail:
        rp, money = g.research_cost(r["key"])
        afford.append((rp <= g.rp and money <= g.money, rp + money / 10, r, rp, money))
    afford.sort(key=lambda x: (not x[0], x[1]))
    ok, _, r, rp, money = afford[0]
    out = _L(ai, (f"Önerim: {_tr(r['name'])} — {_tr(r['effect'])}. Maliyet {_num(ai, rp)} RP + {_num(ai, money)} Para.",
                  f"My pick: {_tr(r['name'])} — {_tr(r['effect'])}. Cost {_num(ai, rp)} RP + {_num(ai, money)} credits."))
    if not ok:
        out += _L(ai, (f" Şu an yetmiyor (sende {_num(ai, g.rp)} RP, {_num(ai, g.money)} Para).",
                       f" You can't afford it yet (you have {_num(ai, g.rp)} RP, {_num(ai, g.money)} credits)."))
    if len(avail) > 1:
        out += _L(ai, (f" Açık {len(avail)} araştırma var; AR-GE ekranında hepsini görebilirsin.",
                       f" {len(avail)} research options are open; see them all on the R&D screen."))
    return out


def design_check(ai, g):
    d = g.s.get("last_design")
    if not d:
        return _L(ai, ("Henüz bir roket tasarlamadın. TASARIM ekranında parçaları seç; sonra tekrar sor.",
                       "You haven't designed a rocket yet. Pick parts in the DESIGN screen, then ask again."))
    from .. import rocket as R
    rep = R.analyze(g, d)
    tgt = _tr(D.PLANET[rep["planet"]]["name"])
    out = _L(ai, (f"Son tasarımın hedefi: {tgt}.", f"Your last design targets {tgt}."))
    if rep["blockers"]:
        out += _L(ai, (" Fırlatmayı engelleyenler: ", " Launch blockers: ")) + "; ".join(_tr(b) for b in rep["blockers"][:3]) + "."
    elif rep["warnings"]:
        out += _L(ai, (" Uyarılar: ", " Warnings: ")) + "; ".join(_tr(w) for w in rep["warnings"][:3]) + "."
    else:
        out += _L(ai, (" Engel yok; fırlatmaya hazır görünüyor.", " No blockers; it looks ready to launch."))
    rk = rep.get("risk")
    if isinstance(rk, dict) and "success" in rk:
        sp = rk["success"] * 100 if rk["success"] <= 1 else rk["success"]
        fp = rk.get("fail", 0) * 100 if rk.get("fail", 0) <= 1 else rk.get("fail", 0)
        out += _L(ai, (f" Başarı olasılığı %{_num(ai, sp)}, başarısızlık %{_num(ai, fp)}.",
                       f" Success chance {_num(ai, sp)}%, failure {_num(ai, fp)}%."))
    fm = rep.get("fuel_margin")
    if isinstance(fm, (int, float)):
        if fm < 1.0:
            out += _L(ai, (" Yakıt hedefe yetmiyor: tank ekle ya da daha verimli motor seç.",
                           " Fuel won't reach the target: add tanks or choose a more efficient engine."))
        elif fm < 1.15:
            out += _L(ai, (f" Yakıt payı dar (×{_num(ai, fm, 2)}); küçük bir sapma sorun olabilir.",
                           f" Fuel margin is tight (×{_num(ai, fm, 2)}); a small deviation could matter."))
    return out


def target_plan(ai, g, body):
    if body not in D.PLANET:
        return None
    p = D.PLANET[body]
    nm = _tr(p["name"])
    out = []
    if not g.req_met(p["unlock"]):
        out.append(_L(ai, (f"{nm} henüz kilitli: {_tr(g.req_text(p['unlock']))}.", f"{nm} is still locked: {_tr(g.req_text(p['unlock']))}.")))
    else:
        out.append(_L(ai, (f"{nm} açık; gidebilirsin.", f"{nm} is unlocked; you can go.")))
    out.append(_L(ai, (f"Oyunda zorluk: {_tr(p['difficulty'])}, menzil sınıfı {p['range']}, risk %{_num(ai, p['risk'] * 100)}.",
                       f"In-game difficulty: {_tr(p['difficulty'])}, range class {p['range']}, risk {_num(ai, p['risk'] * 100)}%.")))
    if p.get("hot"):
        out.append(_L(ai, ("Isı kalkanı şart.", "A heat shield is required.")))
    out.append(_L(ai, (f"Koloni kurma bedeli {_num(ai, p['colony_cost'])} Para; çıkan maden: {_tr(D.MINERAL[p['mineral']]['name'])}.",
                       f"Founding a colony costs {_num(ai, p['colony_cost'])} credits; it yields {_tr(D.MINERAL[p['mineral']]['name'])}.")))
    if body != "moon":
        t = P.transfer("earth", body)
        if t:
            out.append(_L(ai, (f"Gerçekte Dünya'dan Hohmann transferi ~{P.fmt_dur(t['days'] * P.DAY, True)} sürerdi.",
                               f"In reality a Hohmann transfer from Earth would take ~{P.fmt_dur(t['days'] * P.DAY, False)}.")))
    return " ".join(out)


def colony_detail(ai, g, body):
    c = g.colony(body) if body in D.PLANET else None
    if not c:
        return None
    rates = {}
    try:
        rates = g.colony_rates(c) or {}
    except Exception:
        pass
    nm = _tr(D.PLANET[body]["name"])
    out = _L(ai, (f"{nm} kolonisi: seviye {c['level']}, {int(c['pop'])}/{g.colony_capacity(c)} kişi, mutluluk %{int(c['happiness'])}, "
                  f"yiyecek {int(c.get('food', 0))}.",
                  f"{nm} colony: level {c['level']}, {int(c['pop'])}/{g.colony_capacity(c)} people, happiness {int(c['happiness'])}%, "
                  f"food {int(c.get('food', 0))}."))
    if rates:
        out += _L(ai, (f" Saatte: maden {_num(ai, rates['mine'], 1)}, araştırma {_num(ai, rates['rp'], 1)} RP, yiyecek {_num(ai, rates['food'], 1)}.",
                       f" Per hour: ore {_num(ai, rates['mine'], 1)}, research {_num(ai, rates['rp'], 1)} RP, food {_num(ai, rates['food'], 1)}."))
        if rates["food"] < 0:
            out += _L(ai, (" Yiyecek eksiye düşüyor: Ev ekle (her ev yiyecek üretir).", " Food is negative: add Houses (each house produces food)."))
    if c["happiness"] < 45:
        out += _L(ai, (" Mutluluk düşük: park, spor salonu ya da okul ekle.", " Happiness is low: add a park, gym or school."))
    return out
