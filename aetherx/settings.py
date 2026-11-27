# -*- coding: utf-8 -*-
"""
AETHER-X // OYUNCU AYARLARI
Bütün ayarlar burada tanımlıdır ve tercih dosyasında (i18n.PREFS["settings"]) saklanır; kampanyadan bağımsızdır
(ana menüden de değiştirilebilir). Her ayarın oyunda gerçek bir etkisi vardır; bağlandığı yer yanında yazılı.
"""
from . import i18n

DEFAULTS = {
    # görüntü
    "fps_cap": 0,             # app.App.run / run_async: clock.tick(fps_cap); 0 = sınırsız (varsayılan)
    "boot_max": True,         # app.App: her açılışta Ultra kalite + sınırsız FPS
    "dyn_quality": False,     # app.App.update: FPS uzun süre 30'un altındaysa kaliteyi bir kademe düşür
    "perf_graph": False,      # app.App.draw: kare süresi grafiği
    "ss": 0.0,                # i18n.quality(): 3B koloni süper örnekleme (0 = kademeye göre)
    "brightness": 1.0,        # app.App.draw: ekran parlaklığı (0,6..1,4)
    "show_fps": False,        # app.App.draw: FPS göstergesi (F3 ile de)
    "bloom_k": 1.0,           # i18n.quality(): parlama şiddeti çarpanı
    "motes": True,            # i18n.quality(): süzülen toz zerreleri
    "stars_k": 1.0,           # i18n.quality(): arka plan yıldız sayısı çarpanı (yeni açılan ekranlarda)
    "fx_k": 1.0,              # i18n.quality(): parçacık (toz, kıvılcım) çarpanı
    # erişilebilirlik / arayüz
    "shake": 1.0,             # fx.Shake.add: ekran sarsıntısı şiddeti
    "reduce_motion": False,   # fx.Transition.start (anında geçiş) + sarsıntı kapalı
    "tooltips": True,         # ui.draw_tooltip
    "custom_cursor": True,    # ui.draw_cursor; kapalıyken sistem imleci
    "nova_hints": True,       # app.App.say: öncelikli olmayan NOVA ipuçları
    "high_contrast": False,   # ui.glass_surface: paneller daha opak (okunabilirlik)
    "toast_k": 1.0,           # ui.Toasts.push: bildirimlerin ekranda kalma süresi çarpanı
    # oyun
    "autosave_min": 3,        # app.App: dakikada bir otomatik kayıt (0 = yalnız olaylarda)
    "game_speed": 1.0,        # game.Game.update: oyun saatinin hızı (ekonomi, günlük olaylar)
    "lb_url": "",             # online.py: çevrimiçi sıralama sunucusu (anahtarsız); boş = yalnız yerel
    # ses
    "audio": {"enabled": True, "master": 1.0, "music": 0.55, "sfx": 0.8, "amb": 0.8, "ui": 0.8, "voice": 0.8,
              "mute_unfocused": True},
}

FPS_CHOICES = (30, 60, 120, 144, 0)
SPEED_CHOICES = (0.5, 1.0, 2.0, 4.0)
SS_CHOICES = (0.0, 1.0, 1.5, 2.0)

# kategori -> sıfırlanacak anahtarlar (AYARLAR ekranındaki "kategoriyi sıfırla")
GROUPS = {"gfx": ("bloom_k", "motes", "stars_k", "fx_k", "brightness"),
          "perf": ("fps_cap", "boot_max", "dyn_quality", "show_fps", "perf_graph", "ss"),
          "game": ("nova_hints", "autosave_min", "tooltips", "game_speed", "toast_k"),
          "access": ("reduce_motion", "shake", "custom_cursor", "high_contrast")}

# hazır profiller: (kalite, ayarlar)
PRESETS = {
    "perf": ("low", {"fps_cap": 60, "bloom_k": 0.0, "motes": False, "stars_k": 0.5, "fx_k": 0.5, "ss": 1.0}, False),
    "balanced": ("medium", {"fps_cap": 60, "bloom_k": 1.0, "motes": True, "stars_k": 1.0, "fx_k": 1.0, "ss": 0.0}, True),
    "high": ("high", {"fps_cap": 120, "bloom_k": 1.0, "motes": True, "stars_k": 1.0, "fx_k": 1.0, "ss": 0.0}, True),
    "ultra": ("ultra", {"fps_cap": 0, "bloom_k": 1.2, "motes": True, "stars_k": 1.5, "fx_k": 1.5, "ss": 2.0}, True),
}


def apply_preset(name):
    q, vals, cine = PRESETS[name]
    i18n.PREFS["quality"] = q
    i18n.PREFS["cinematic"] = cine
    st = _store()
    st.update(vals)
    i18n.save_prefs()


def reset_group(cat):
    st = _store()
    for k in GROUPS.get(cat, ()):
        st.pop(k, None)
    if cat == "gfx":
        i18n.PREFS["cinematic"] = True
    i18n.save_prefs()


def boot():
    """Açılış: 'Açılışta en yüksek ayar' açıksa Ultra kalite + sınırsız FPS (oturum içinde değiştirilebilir)."""
    if get("boot_max"):
        i18n.PREFS["quality"] = "ultra"
        set("fps_cap", 0, save=False)
AUTOSAVE_CHOICES = (0, 1, 3, 5, 10)


def _store():
    st = i18n.PREFS.get("settings")
    if not isinstance(st, dict):
        st = {}
        i18n.PREFS["settings"] = st
    return st


def get(key):
    st = _store()
    if key == "audio":
        a = dict(DEFAULTS["audio"])
        if isinstance(st.get("audio"), dict):
            a.update({k: v for k, v in st["audio"].items() if k in a})
        return a
    return st.get(key, DEFAULTS[key])


def set(key, value, save=True):
    st = _store()
    st[key] = value
    if save:
        i18n.save_prefs()


def set_audio(key, value, save=True):
    a = get("audio")
    a[key] = value
    set("audio", a, save)


def reset():
    i18n.PREFS["settings"] = {}
    i18n.save_prefs()


def shake_k():
    return 0.0 if get("reduce_motion") else float(get("shake"))


def apply_audio(app):
    """Ses ayarlarını eski motora (müzik/efekt/ortam/arayüz/NOVA) ve Kozmik Ses Motoruna uygula."""
    a = get("audio")
    au = app.audio
    if au.enabled != bool(a["enabled"]):
        au.set_enabled(bool(a["enabled"]))
    au.set_volumes(music=a["music"], sfx=a["sfx"], master=a["master"], amb=a["amb"], ui=a["ui"], voice=a["voice"])
    cae = getattr(app, "cae", None)
    if cae is not None:
        v = cae.settings.d["vol"]
        v["ana"], v["ortam"], v["arayüz"], v["müzik"] = a["master"], a["amb"], a["ui"], a["music"]
        cae.settings.save()
        try:
            cae.apply_volumes()
        except Exception:
            pass
    if app.game.s:                      # kampanya kaydındaki eski alanlar da aynı değerde kalsın
        s = app.game.s["settings"]
        s["sound"], s["music"], s["sfx"] = bool(a["enabled"]), a["music"], a["sfx"]
