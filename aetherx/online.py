# -*- coding: utf-8 -*-
"""
AETHER-X // CANLI SIRALAMA (istemci)
  * Skor: kademe (seviye), para, koloniler, başarımlar, başarılı görevler ve keşfedilen türlerden hesaplanır.
  * Yerel sıralama: bu cihazdaki kampanyalar (SAVE_DIR/leaderboard.json).
  * Çevrimiçi sıralama: AYARLAR > OYUN'daki sunucu adresine bağlanır (server/leaderboard_server.py; anahtarsız, CORS açık).
    API anahtarı yoktur, oyun dosyasına gömülmez. Adres boşsa yalnız yerel sıralama kullanılır.
  * Ağ işleri oyunu dondurmaz: masaüstünde arka plan iş parçacığı, tarayıcıda (pygbag) JavaScript fetch + her karede
    sonuç yoklaması.
"""
import json
import secrets
import sys
import threading
import time

from . import i18n
from .config import SAVE_FILE

WEB = sys.platform == "emscripten"
LOCAL_FILE = SAVE_FILE.parent / "leaderboard.json"
VERSION = "3.10"


def campaign_id(game):
    a = game.s["agency"]
    if not a.get("uid"):
        a["uid"] = secrets.token_hex(8)
    return a["uid"]


def score_of(game):
    """Toplam skor: seviye x1000 + para/10 + koloni x2000 + başarım x300 + başarılı görev x150 + koloni seviyeleri x500."""
    s = game.s
    a = s["agency"]
    cols = [c for c in s.get("colonies", {}).values() if c]
    st = s.get("stats", {})
    return int(a.get("level", 1) * 1000 + max(0, a.get("money", 0)) / 10 + len(cols) * 2000
               + len(s.get("achievements", [])) * 300 + st.get("success", 0) * 150
               + sum(c.get("level", 1) for c in cols) * 500)


def entry_of(game):
    a = game.s["agency"]
    return {"id": campaign_id(game), "name": a.get("name", "?")[:24], "score": score_of(game), "money": int(a.get("money", 0)),
            "level": int(a.get("level", 1)), "colonies": len([c for c in game.s.get("colonies", {}).values() if c]),
            "color": list(a.get("color", (62, 230, 255)))[:3], "ver": VERSION}


# ------------------------------------------------------------------ yerel sıralama
def local_load():
    try:
        rows = json.load(open(LOCAL_FILE, encoding="utf-8"))
        return [r for r in rows if isinstance(r, dict) and "id" in r]
    except Exception:
        return []


def local_update(game):
    if not game.s:
        return
    rows = {r["id"]: r for r in local_load()}
    e = entry_of(game)
    e["t"] = int(time.time())
    rows[e["id"]] = e
    try:
        LOCAL_FILE.parent.mkdir(parents=True, exist_ok=True)
        json.dump(list(rows.values()), open(LOCAL_FILE, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass


def sorted_rows(rows, key):
    k = key if key in ("score", "money", "level") else "score"
    return sorted(rows, key=lambda r: (-r.get(k, 0), -r.get("score", 0)))


# ------------------------------------------------------------------ çevrimiçi
def server_url():
    st = i18n.PREFS.get("settings") or {}
    u = str(st.get("lb_url", "") or "").strip().rstrip("/")
    if u and not u.startswith(("http://", "https://")):
        u = "https://" + u
    return u


class Online:
    """Tek bekleyen istek; sonuç .result / .error'a düşer. update() her karede çağrılır (tarayıcıda yoklama)."""

    def __init__(self):
        self.busy = False
        self.result = None
        self.error = None
        self.last_ok = 0.0
        self.kind = None
        self._tag = 0

    def _done(self, data, err):
        self.busy = False
        if err:
            self.error = err
        else:
            self.error = None
            self.result = (self.kind, data)
            self.last_ok = time.time()

    def request(self, kind, method, path, body=None):
        url = server_url()
        if not url or self.busy:
            return False
        self.busy, self.kind = True, kind
        full = url + path
        if WEB:
            self._tag += 1
            tag = f"__aetherx_lb{self._tag}"
            opts = {"method": method, "headers": {"Content-Type": "application/json"}}
            if body is not None:
                opts["body"] = json.dumps(body)
            js = (f"window.{tag}=null;fetch({json.dumps(full)},{json.dumps(opts)})"
                  f".then(r=>r.text()).then(t=>{{window.{tag}={{ok:true,t:t}}}})"
                  f".catch(e=>{{window.{tag}={{ok:false,t:String(e)}}}});")
            try:
                import platform as _pf
                _pf.window.eval(js)
                self._web = (tag, time.time())
            except Exception as ex:
                self._done(None, f"web: {ex}")
            return True

        def work():
            try:
                import urllib.request
                req = urllib.request.Request(full, method=method, data=None if body is None else json.dumps(body).encode("utf-8"),
                                             headers={"Content-Type": "application/json", "User-Agent": "aetherx-game"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    self._done(json.loads(r.read().decode("utf-8")), None)
            except Exception as ex:
                self._done(None, str(ex)[:120])
        threading.Thread(target=work, daemon=True).start()
        return True

    def update(self):
        if not (WEB and self.busy and getattr(self, "_web", None)):
            return
        tag, t0 = self._web
        try:
            import platform as _pf
            v = getattr(_pf.window, tag)
            if v is not None and v is not False:
                ok, txt = bool(v.ok), str(v.t)
                self._web = None
                if ok:
                    try:
                        self._done(json.loads(txt), None)
                    except Exception:
                        self._done(None, "bad json")
                else:
                    self._done(None, txt[:120])
            elif time.time() - t0 > 10:
                self._web = None
                self._done(None, "timeout")
        except Exception as ex:
            self._web = None
            self._done(None, str(ex)[:120])

    def submit(self, game):
        return self.request("submit", "POST", "/scores", entry_of(game))

    def fetch(self, sort="score"):
        return self.request("list", "GET", f"/scores?sort={sort}&limit=50")


ONLINE = Online()
