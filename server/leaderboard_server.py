# -*- coding: utf-8 -*-
"""
AETHER-X — ÇEVRİMİÇİ SIRALAMA SUNUCUSU (anahtarsız, yalnız Python standart kütüphanesi)

Çalıştırma:
    python server/leaderboard_server.py --port 8790 --data scores.json
Sonra oyunda: AYARLAR > OYUN > "Çevrimiçi sıralama sunucusu" = https://senin-sunucun.example  (ya da http://127.0.0.1:8790)

Uç noktalar (CORS açık: GitHub Pages'teki oyun doğrudan bağlanır):
    GET  /scores?sort=score|money|level&limit=50   -> {"ok": true, "scores": [...], "total": N}
    POST /scores   gövde JSON: {"id", "name", "score", "money", "level", "colonies", "color", "ver"}
         -> aynı kampanya kimliği (id) varsa kaydı günceller (en iyi değerler korunur)
Güvenlik: API anahtarı yok (oyun dosyasına gömülmez). Bunun yerine: alan doğrulaması (uzunluk, aralık), IP başına
istek sınırı (5 sn'de 1 gönderim), en çok 5000 kayıt, ad temizleme. Skorlar istemcide hesaplanır; hile koruması sınırlıdır.
"""
import argparse
import json
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

LOCK = threading.Lock()
LAST = {}
MAX_ROWS = 5000
FIELDS = {"score": (0, 10 ** 10), "money": (-10 ** 9, 10 ** 10), "level": (1, 1000), "colonies": (0, 50)}


def clean(rec):
    """Gelen kaydı doğrula; geçersizse None."""
    if not isinstance(rec, dict):
        return None
    rid = str(rec.get("id", ""))
    if not re.fullmatch(r"[0-9a-f]{8,32}", rid):
        return None
    name = re.sub(r"[\x00-\x1f<>]", "", str(rec.get("name", "")))[:24].strip() or "?"
    out = {"id": rid, "name": name, "ver": str(rec.get("ver", ""))[:12], "t": int(time.time())}
    for k, (lo, hi) in FIELDS.items():
        try:
            v = int(rec.get(k, 0))
        except Exception:
            return None
        if not lo <= v <= hi:
            return None
        out[k] = v
    col = rec.get("color", [62, 230, 255])
    out["color"] = [max(0, min(255, int(c))) for c in col[:3]] if isinstance(col, list) and len(col) >= 3 else [62, 230, 255]
    return out


class Store:
    def __init__(self, path):
        self.path = path
        self.rows = {}
        if os.path.exists(path):
            try:
                self.rows = {r["id"]: r for r in json.load(open(path, encoding="utf-8"))}
            except Exception:
                self.rows = {}

    def upsert(self, rec):
        with LOCK:
            old = self.rows.get(rec["id"])
            if old:
                for k in ("score", "money", "level", "colonies"):
                    rec[k] = max(rec[k], old.get(k, 0)) if k != "money" else rec[k]
            self.rows[rec["id"]] = rec
            if len(self.rows) > MAX_ROWS:
                worst = sorted(self.rows.values(), key=lambda r: r["score"])[: len(self.rows) - MAX_ROWS]
                for w in worst:
                    self.rows.pop(w["id"], None)
            tmp = self.path + ".tmp"
            json.dump(list(self.rows.values()), open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
            os.replace(tmp, self.path)

    def top(self, sort, limit):
        key = sort if sort in FIELDS else "score"
        with LOCK:
            rows = sorted(self.rows.values(), key=lambda r: (-r[key], -r["score"], r["t"]))
        return rows[:limit], len(rows)


def make_handler(store):
    class H(BaseHTTPRequestHandler):
        def _send(self, code, obj):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

        def do_OPTIONS(self):
            self._send(204, {})

        def do_GET(self):
            u = urlparse(self.path)
            if u.path.rstrip("/") != "/scores":
                return self._send(404, {"ok": False, "error": "not found"})
            q = parse_qs(u.query)
            lim = max(1, min(100, int((q.get("limit") or ["50"])[0] or 50)))
            rows, total = store.top((q.get("sort") or ["score"])[0], lim)
            self._send(200, {"ok": True, "scores": rows, "total": total})

        def do_POST(self):
            if urlparse(self.path).path.rstrip("/") != "/scores":
                return self._send(404, {"ok": False, "error": "not found"})
            ip = self.client_address[0]
            now = time.time()
            if now - LAST.get(ip, 0) < 5:
                return self._send(429, {"ok": False, "error": "too many requests"})
            LAST[ip] = now
            n = int(self.headers.get("Content-Length", 0) or 0)
            if n <= 0 or n > 2048:
                return self._send(400, {"ok": False, "error": "bad size"})
            try:
                rec = clean(json.loads(self.rfile.read(n).decode("utf-8")))
            except Exception:
                rec = None
            if rec is None:
                return self._send(400, {"ok": False, "error": "invalid"})
            store.upsert(rec)
            rows, total = store.top("score", 100000)
            rank = next((i + 1 for i, r in enumerate(rows) if r["id"] == rec["id"]), None)
            self._send(200, {"ok": True, "rank": rank, "total": total})
    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8790)
    ap.add_argument("--data", default="scores.json")
    a = ap.parse_args()
    srv = ThreadingHTTPServer((a.host, a.port), make_handler(Store(a.data)))
    print(f"AETHER-X sıralama sunucusu: http://{a.host}:{a.port}/scores")
    srv.serve_forever()


if __name__ == "__main__":
    main()
