# -*- coding: utf-8 -*-
# /// script
# dependencies = [
#     "pygame-ce",
#     "numpy",
# ]
# ///
"""
AETHER-X  //  Uzay Ajansı Komuta Simülasyonu

En kolay başlatma:
    Windows : BASLAT.bat dosyasına çift tıkla
    macOS / Linux : terminalde  sh baslat.sh

Elle:
    python -m pip install -r requirements.txt
    python main.py

Bu dosya açılışta gereken kütüphaneleri (pygame-ce, numpy) kontrol eder, eksikse
kurar; oyun bir hatayla kapanırsa nedenini ekranda gösterir ve aetherx_hata.txt
dosyasına yazar.
"""
import os
import subprocess
import sys
import traceback

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "aetherx_hata.txt")


def say(msg):
    try:
        print(msg, flush=True)
    except Exception:
        try:
            print(msg.encode("ascii", "replace").decode(), flush=True)
        except Exception:
            pass


def pause():
    """Çift tıklamayla açılan konsol penceresi hemen kapanmasın."""
    try:
        if sys.stdin and sys.stdin.isatty():
            input("\nKapatmak için Enter'a bas...")
    except Exception:
        pass


def popup(title, text):
    try:
        import tkinter
        from tkinter import messagebox
        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror(title, text)
        root.destroy()
    except Exception:
        pass


def pip_install(*pkgs):
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", *pkgs]
    say("Kuruluyor: " + " ".join(pkgs) + "  (internet bağlantısı gerekir, bir dakika sürebilir)")
    try:
        r = subprocess.call(cmd)
        if r != 0:
            subprocess.call([sys.executable, "-m", "ensurepip", "--upgrade"])
            r = subprocess.call(cmd + ["--user"])
        return r == 0
    except Exception as ex:
        say(f"pip çalıştırılamadı: {ex}")
        return False


def ensure_deps():
    if sys.version_info < (3, 8):
        msg = (f"Python {sys.version.split()[0]} çok eski. AETHER-X için Python 3.8 veya üstü gerekir.\n"
               "https://www.python.org/downloads/ adresinden güncel sürümü kur.")
        say(msg)
        popup("AETHER-X", msg)
        pause()
        sys.exit(1)
    need = []
    try:
        import pygame  # noqa: F401
    except Exception:
        # Python 3.14+ için klasik pygame paketi yok; pygame-ce her sürümde kurulabiliyor
        need.append("pygame-ce")
    try:
        import numpy  # noqa: F401
    except Exception:
        need.append("numpy")
    if need:
        say("Eksik kütüphaneler bulundu: " + ", ".join(need))
        if not pip_install(*need):
            msg = ("Gerekli kütüphaneler kurulamadı.\nKomut satırında şunu çalıştır:\n\n"
                   f'  "{sys.executable}" -m pip install pygame-ce numpy\n\nsonra oyunu yeniden aç.')
            say(msg)
            popup("AETHER-X", msg)
            pause()
            sys.exit(1)
        import importlib
        importlib.invalidate_caches()
        try:
            import pygame  # noqa: F401,F811
            import numpy  # noqa: F401,F811
        except Exception:
            msg = ("Kütüphaneler kuruldu ama yüklenemedi. Oyunu kapatıp yeniden aç.\n"
                   "Sorun sürerse:  python -m pip uninstall -y pygame  ve ardından  python -m pip install pygame-ce numpy")
            say(msg)
            popup("AETHER-X", msg)
            pause()
            sys.exit(1)


def main():
    ensure_deps()
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    try:
        from aetherx.app import App
        frames = int(os.environ.get("AETHERX_TEST_FRAMES", "0") or 0) or None    # otomatik test için
        App(max_frames=frames).run()
    except SystemExit:
        raise
    except BaseException:
        tb = traceback.format_exc()
        try:
            import platform
            import pygame
            info = (f"Python {platform.python_version()} · {platform.platform()} · "
                    f"pygame {getattr(pygame.version, 'ver', '?')}\n\n")
        except Exception:
            info = ""
        try:
            with open(LOG, "w", encoding="utf-8") as f:
                f.write(info + tb)
        except Exception:
            pass
        say("\nAETHER-X bir hatayla kapandı:\n" + tb)
        say(f"Ayrıntılar şu dosyaya yazıldı: {LOG}")
        popup("AETHER-X hata", "Oyun bir hatayla kapandı.\n\n" + tb.strip().splitlines()[-1] +
              f"\n\nAyrıntılar: {LOG}\nBu dosyayı geliştiriciyle paylaşabilirsin.")
        try:
            import pygame
            pygame.quit()
        except Exception:
            pass
        pause()
        sys.exit(1)


async def main_web():
    """Tarayıcı sürümü (pygbag / WebAssembly). GitHub Pages'te çalışır."""
    import asyncio  # noqa: F401
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    from aetherx.app import App
    app = App()
    await app.run_async()


if sys.platform == "emscripten":
    import asyncio
    import numpy  # noqa: F401  (pygbag paket önyüklemesi için)
    import pygame  # noqa: F401
    asyncio.run(main_web())
elif __name__ == "__main__":
    main()
