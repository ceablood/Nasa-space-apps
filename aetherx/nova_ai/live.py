# -*- coding: utf-8 -*-
"""
NOVA — CANLI NASA VERİSİ (anahtarsız uç noktalar)
  * JPL SBDB Close Approach API  (ssd-api.jpl.nasa.gov/cad.api)   — Dünya'ya yakın geçecek asteroitler
  * NASA Exoplanet Archive TAP    (exoplanetarchive.ipac.caltech.edu) — doğrulanmış ötegezegen sayısı
  * NASA EONET v3                 (eonet.gsfc.nasa.gov)              — Dünya'daki açık doğa olayları (uydu gözlemli)
Masaüstünde istekler arka plan iş parçacığında yapılır. Tarayıcıda (pygbag) yalnız CORS izni veren EONET canlı
çekilir; diğerleri için oyunla gelen tarihli anlık görüntü (data/nasa_snapshot.json) kullanılır. Ağ yoksa ya da hata
olursa yine anlık görüntüye dönülür ve yanıtta bu açıkça yazılır. API anahtarı kullanılmaz.
"""
import datetime as _dt
import json
import os
import sys
import threading
import time
from .tx import pick as _pick

WEB = sys.platform == "emscripten"
_SNAP_PATH = os.path.join(os.path.dirname(__file__), "data", "nasa_snapshot.json")
_SNAP = None
TTL = 30 * 60


def snapshot():
    global _SNAP
    if _SNAP is None:
        with open(_SNAP_PATH, encoding="utf-8") as fh:
            _SNAP = json.load(fh)
    return _SNAP


def _cad_url():
    today = _dt.date.today()
    end = today + _dt.timedelta(days=60)
    return f"https://ssd-api.jpl.nasa.gov/cad.api?date-min={today.isoformat()}&date-max={end.isoformat()}&dist-max=0.05&sort=date"


URLS = {
    "cad": _cad_url,
    "exo": lambda: ("https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select+count(*)+as+n,"
                    "+count(distinct+hostname)+as+hosts+from+ps+where+default_flag=1&format=json"),
    "eonet": lambda: "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=200&days=60",
}
WEB_OK = {"eonet"}                     # tarayıcıda CORS izni olan uç nokta(lar)


def _parse(kind, raw):
    d = json.loads(raw)
    if kind == "cad":
        F = d.get("fields", [])
        items = []
        for r in d.get("data", []) or []:
            x = dict(zip(F, r))
            items.append({"des": x["des"], "date": x["cd"], "dist_au": float(x["dist"]), "v_rel_kms": float(x["v_rel"]),
                          "h": float(x["h"]) if x.get("h") else None})
        return {"items": items}
    if kind == "exo":
        return {"planets": int(d[0]["n"]), "hosts": int(d[0]["hosts"])}
    if kind == "eonet":
        return {"items": [{"title": v["title"], "cat": v["categories"][0]["title"],
                           "date": v["geometry"][-1]["date"] if v.get("geometry") else None} for v in d.get("events", [])]}
    return None


class Live:
    def __init__(self):
        self.data = {}           # kind -> (veri, zaman, "live")
        self.busy = set()
        self.err = {}
        self._web = {}

    def get(self, kind):
        """(veri, kaynak etiketi 'live'|'snapshot', tarih) — eksikse anlık görüntü; arka planda tazelemeyi tetikler."""
        have = self.data.get(kind)
        if not have or time.time() - have[1] > TTL:
            self.refresh(kind)
        if have:
            return have[0], "live", time.strftime("%Y-%m-%d %H:%M", time.localtime(have[1]))
        s = snapshot()
        snap = {"cad": s["cad"], "exo": {"planets": s["exoplanets"]["planets"], "hosts": s["exoplanets"]["hosts"]},
                "eonet": s["eonet"]}[kind]
        return snap, "snapshot", s["fetched"]

    def refresh(self, kind):
        if kind in self.busy or (WEB and kind not in WEB_OK):
            return
        self.busy.add(kind)
        url = URLS[kind]()
        if WEB:
            try:
                import platform as _pf
                tag = f"__aetherx_live_{kind}"
                _pf.window.eval(f"window.{tag}=null;fetch({json.dumps(url)}).then(r=>r.text())"
                                f".then(t=>{{window.{tag}={{ok:true,t:t}}}}).catch(e=>{{window.{tag}={{ok:false,t:String(e)}}}});")
                self._web[kind] = (tag, time.time())
            except Exception as ex:
                self.err[kind] = str(ex)[:100]
                self.busy.discard(kind)
            return

        def work():
            try:
                import urllib.request
                req = urllib.request.Request(url, headers={"User-Agent": "aetherx-game"})
                with urllib.request.urlopen(req, timeout=12) as r:
                    self.data[kind] = (_parse(kind, r.read().decode("utf-8")), time.time())
                    self.err.pop(kind, None)
            except Exception as ex:
                self.err[kind] = str(ex)[:100]
            finally:
                self.busy.discard(kind)
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        """Tarayıcıda her karede çağrılır: tamamlanan fetch sonuçlarını alır."""
        if not self._web:
            return
        import platform as _pf
        for kind, (tag, t0) in list(self._web.items()):
            try:
                v = getattr(_pf.window, tag)
                if v is not None and v is not False:
                    if bool(v.ok):
                        self.data[kind] = (_parse(kind, str(v.t)), time.time())
                    else:
                        self.err[kind] = str(v.t)[:100]
                    del self._web[kind]
                    self.busy.discard(kind)
                elif time.time() - t0 > 15:
                    self.err[kind] = "timeout"
                    del self._web[kind]
                    self.busy.discard(kind)
            except Exception as ex:
                self.err[kind] = str(ex)[:100]
                del self._web[kind]
                self.busy.discard(kind)


LIVE = Live()

AU_KM = 149597870.7
LD_KM = 384400.0


def _stamp(tag, when, tr_):
    if tag == "live":
        return _pick(tr_, f"(NASA, canlı veri, {when})", f"(NASA, live data, {when})")
    return _pick(tr_, f"(NASA, oyunla gelen {when} tarihli anlık görüntü)", f"(NASA, bundled snapshot from {when})")


def _n(x, d, tr_):
    s = f"{x:,.{d}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".") if tr_ else s


def asteroids(tr_):
    d, tag, when = LIVE.get("cad")
    items = d["items"]
    now = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    fut = []
    for x in items:
        try:
            t = _dt.datetime.strptime(x["date"], "%Y-%b-%d %H:%M")
        except ValueError:
            continue
        if now - _dt.timedelta(hours=12) <= t <= now + _dt.timedelta(days=60):
            fut.append((t, x))
    if not fut:
        return ((_pick(tr_, "Önümüzdeki dönemde 0,05 AU içinde kayıtlı yakın geçiş görmüyorum. ", "I see no recorded close approach within 0.05 au in the coming period. ")) + _stamp(tag, when, tr_)), 0.8
    closest = min(fut, key=lambda q: q[1]["dist_au"])
    nxt = fut[0]
    def desc(t, x):
        km = x["dist_au"] * AU_KM
        size = ""
        if x.get("h"):
            # mutlak parlaklıktan çap aralığı (albedo 0,25–0,05): D = 1329 km / sqrt(p) * 10^(-H/5)
            lo = 1329 / (0.25 ** 0.5) * 10 ** (-x["h"] / 5) * 1000
            hi = 1329 / (0.05 ** 0.5) * 10 ** (-x["h"] / 5) * 1000
            size = (_pick(tr_, f", tahmini çap {lo:.0f}–{hi:.0f} m", f", estimated size {lo:.0f}–{hi:.0f} m"))
        return (_pick(tr_, f"{x['des']} — {t:%d.%m.%Y %H:%M} UTC, {_n(km, 0, tr_)} km ({_n(km / LD_KM, 1, tr_)} Ay mesafesi), "
                f"{_n(x['v_rel_kms'], 1, tr_)} km/s{size}", f"{x['des']} — {t:%Y-%m-%d %H:%M} UTC, {_n(km, 0, tr_)} km ({_n(km / LD_KM, 1, tr_)} lunar distances), "
                f"{_n(x['v_rel_kms'], 1, tr_)} km/s{size}"))
    same = closest[1]["des"] == nxt[1]["des"]
    cl_tr = "Aynı zamanda dönemin en yakın geçişi bu." if same else f"En yakını: {desc(*closest)}."
    cl_en = "It is also the closest of the period." if same else f"Closest: {desc(*closest)}."
    out = (_pick(tr_, f"Önümüzdeki 60 günde Dünya'ya 0,05 AU'dan yakın {len(fut)} geçiş var. Sıradaki: {desc(*nxt)}. "
           f"{cl_tr} Bu liste yakın geçişleri gösterir; çarpma olasılıkları NASA'nın ayrı Sentry sisteminde izlenir. ", f"There are {len(fut)} approaches closer than 0.05 au in the next 60 days. Next: {desc(*nxt)}. "
           f"{cl_en} This list shows close approaches; impact probabilities are tracked separately by NASA's Sentry system. "))
    return out + _stamp(tag, when, tr_), 0.93


def exoplanets(tr_):
    d, tag, when = LIVE.get("exo")
    return ((_pick(tr_, f"NASA Ötegezegen Arşivi'nde doğrulanmış {_n(d['planets'], 0, tr_)} ötegezegen, {_n(d['hosts'], 0, tr_)} yıldız "
             f"sisteminde kayıtlı. ", f"The NASA Exoplanet Archive lists {_n(d['planets'], 0, tr_)} confirmed exoplanets around {_n(d['hosts'], 0, tr_)} "
             f"host stars. ")) + _stamp(tag, when, tr_)), 0.95


CAT_TR = {"Wildfires": "orman yangını", "Severe Storms": "şiddetli fırtına", "Volcanoes": "yanardağ",
          "Sea and Lake Ice": "deniz/göl buzu", "Floods": "sel", "Earthquakes": "deprem", "Drought": "kuraklık",
          "Dust and Haze": "toz ve pus", "Landslides": "heyelan", "Snow": "kar", "Temperature Extremes": "aşırı sıcaklık",
          "Water Color": "su rengi", "Manmade": "insan kaynaklı"}


def earth_events(tr_, norm=""):
    d, tag, when = LIVE.get("eonet")
    items = d["items"]
    if not items:
        return (_pick(tr_, "Şu an açık doğa olayı kaydı yok. ", "No open natural events right now. ")) + _stamp(tag, when, tr_), 0.8
    from collections import Counter
    cnt = Counter(x["cat"] for x in items)
    parts = ", ".join(f"{(_pick(tr_, CAT_TR.get(c, c), c.lower()))} {n}" for c, n in cnt.most_common())
    turk = [x for x in items if "turkey" in x["title"].lower() or "türkiye" in x["title"].lower() or "turkiye" in x["title"].lower()]
    out = (_pick(tr_, f"NASA EONET şu an {len(items)} açık doğa olayı izliyor: {parts}.", f"NASA EONET is tracking {len(items)} open natural events: {parts}."))
    ex = (turk or items)[:3]
    out += (_pick(tr_, " Örnekler: ", " Examples: ")) + "; ".join(x["title"] for x in ex) + "."
    if turk:
        out += (_pick(tr_, " (Türkiye'de olanlar başta.)", " (Events in Türkiye listed first.)"))
    return out + " " + _stamp(tag, when, tr_), 0.9
