# -*- coding: utf-8 -*-
"""Kaynak koddaki ekrana yazılabilecek Türkçe metinleri çıkarır -> aetherx/lang/keys.json
f-string'ler {0}, {1} ... yer tutuculu şablona dönüştürülür. Mevcut kimlikler korunur (yeni metinler sona eklenir)."""
import ast, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "aetherx"
OUT = ROOT / "lang" / "keys.json"
SKIP_FILES = {"i18n.py", "config.py"}
SKIP_LANG_DICT = True          # {"tr":..,"en":..,"de":..} sözlükleri zaten çok dilli
TRCH = set("çğıöşüÇĞİÖŞÜ")


def is_text(s):
    if not s or len(s) < 2 or not any(c.isalpha() for c in s):
        return False
    if s.endswith("Scene") or re.fullmatch(r"[,.\d{}f]+", s) or s.isupper() and len(s) <= 6 and s.isascii() and " " not in s \
            and s in ("SCALED", "RGBA", "NASA", "ESA", "JAXA", "ISRO", "TUA", "NOVA", "FPS"):
        return False
    if re.fullmatch(r"[a-z0-9_]+", s):                # anahtar / kimlik
        return False
    if re.fullmatch(r"[a-z_]+\.[a-z_.]+", s) or s.startswith(("aetherx", "#", "%")):
        return False
    if s in ("RGBA", "utf-8", "SRCALPHA", "midtop", "midleft", "midright", "topleft", "topright", "center"):
        return False
    return True


def fstring_template(node):
    parts, n = [], 0
    for v in node.values:
        if isinstance(v, ast.Constant):
            parts.append(str(v.value).replace("{", "{{").replace("}", "}}") if False else str(v.value))
        else:
            parts.append("{%d}" % n)
            n += 1
    return "".join(parts)


def is_lang_dict(node):
    return isinstance(node, ast.Dict) and {getattr(k, "value", None) for k in node.keys} >= {"tr", "en"}


def collect(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = set()
    for node in ast.walk(tree):
        if is_lang_dict(node):
            for sub in ast.walk(node):
                skip.add(id(sub))
        if isinstance(node, (ast.Expr,)) and isinstance(getattr(node, "value", None), ast.Constant) \
                and isinstance(node.value.value, str):
            skip.add(id(node.value))                                   # docstring
        if isinstance(node, ast.JoinedStr):
            for v in node.values:
                skip.add(id(v))
        if isinstance(node, ast.Subscript):                            # d["key"] erişimleri
            skip.add(id(node.slice))
        if isinstance(node, ast.Call):
            fn = getattr(node.func, "attr", getattr(node.func, "id", ""))
            if fn in ("get", "setdefault", "pop", "startswith", "endswith", "split", "replace", "join", "strip",
                      "play", "loop", "music", "ambient", "go", "notify_key", "getattr", "hasattr", "setattr",
                      "act_key", "SysFont", "import_module", "__import__", "Rect", "mkdir", "choice"):
                for a in node.args[:1] if fn in ("get", "setdefault", "pop", "getattr", "hasattr", "setattr") else node.args:
                    if fn in ("play", "loop", "music", "ambient", "go", "SysFont", "import_module", "__import__"):
                        skip.add(id(a))
                    elif fn in ("get", "setdefault", "pop", "getattr", "hasattr", "setattr"):
                        skip.add(id(a))
                    elif fn in ("startswith", "endswith", "split", "replace", "join", "strip"):
                        skip.add(id(a))
            for kw in node.keywords:
                if kw.arg in ("anchor", "icon", "style", "special_flags", "mode", "kind", "ramp", "mood", "tab"):
                    skip.add(id(kw.value))
        if isinstance(node, ast.Compare):
            for c in [node.left] + node.comparators:
                skip.add(id(c))
                if isinstance(c, (ast.Tuple, ast.List, ast.Set)):
                    for e in c.elts:
                        skip.add(id(e))
    out = []
    if path.name == "atlas.py":                     # çok dilli veri: yalnızca bilgi satırı başlıkları
        for node in ast.walk(tree):
            if isinstance(node, ast.Tuple) and node.elts and isinstance(node.elts[0], ast.Constant) \
                    and isinstance(node.elts[0].value, str) and len(node.elts) == 2 and is_text(node.elts[0].value):
                out.append((node.elts[0].value, node.lineno))
        for node in ast.walk(tree):                 # CATS
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.isupper() and " " in node.value:
                out.append((node.value, node.lineno))
        return out
    for node in ast.walk(tree):
        if id(node) in skip:
            continue
        if isinstance(node, ast.JoinedStr):
            s = fstring_template(node)
            if is_text(re.sub(r"\{\d+\}", "", s)):
                out.append((s, node.lineno))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and is_text(node.value):
            out.append((node.value, node.lineno))
    return out


def main():
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    seen = set(old)
    new = []
    report = {}
    for p in sorted(ROOT.rglob("*.py")):
        if p.name in SKIP_FILES or "lang" in p.parts:
            continue
        for s, ln in collect(p):
            report.setdefault(s, f"{p.relative_to(ROOT)}:{ln}")
            if s not in seen:
                seen.add(s)
                new.append(s)
    keys = old + sorted(new, key=lambda s: report[s])
    OUT.write_text(json.dumps(keys, ensure_ascii=False, indent=0), encoding="utf-8")
    if "--dump" in sys.argv:
        for i, k in enumerate(keys):
            print(f"{i}\t{report.get(k, '-')}\t{k!r}")
    print(f"{len(keys)} anahtar ({len(new)} yeni)", file=sys.stderr)


if __name__ == "__main__":
    main()
