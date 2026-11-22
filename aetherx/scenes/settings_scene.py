# -*- coding: utf-8 -*-
"""
AYARLAR — kategorili, ayrıntılı oyuncu ayarları.
  GÖRÜNTÜ · SES · OYUN · ERİŞİLEBİLİRLİK · DİL · KONTROLLER · VERİ
Her denetim aetherx/settings.py'deki gerçek bir ayarı değiştirir ve anında uygulanır (yalnız yıldız yoğunluğu yeni açılan
ekranlarda görünür; ekranda belirtilir). Ayarlar kampanyadan bağımsız tercih dosyasında saklanır.
"""
import pygame

from . import Scene
from .. import i18n
from .. import settings as SET
from ..config import C, H, SAVE_FILE, W
from ..fx import scale_color
from ..i18n import tr
from ..ui import Button, Slider, Toggle, draw_paragraph, draw_text, glass_panel

CATS = [("gfx", "GÖRÜNTÜ", "eye"), ("audio", "SES", "nova"), ("game", "OYUN", "rocket"), ("access", "ERİŞİLEBİLİRLİK", "astro"),
        ("lang", "DİL", "planet"), ("keys", "KONTROLLER", "wrench"), ("data", "VERİ", "save")]
PX, PY = 340, 168                       # sağ panel
PW, PH = W - PX - 40, H - PY - 96
ROW = 62
CX = PX + PW - 470                       # denetimlerin x'i
KEYS = [("Her yer", "Fare", "Düğmeler, kartlar, binalar"), ("Her yer", "F11", "Tam ekran"), ("Her yer", "F3", "FPS göstergesi"),
        ("Her yer", "ESC", "Geri dön / duraklat"), ("Hangar", "SPACE", "Fırlat"), ("Hangar", "N", "NOVA'ya sor"),
        ("Yolculuk", "Fare / W-S", "Roketi yukarı-aşağı oynat"), ("Yolculuk", "SPACE / sol tık", "Lazer ile asteroit kır"),
        ("Yolculuk", "A / D", "Yavaşla / hızlan"), ("Yolculuk", "R", "Tamir et (Mühendis gerekir)"),
        ("Yolculuk", "F", "Fotoğraf çek (Kamera gerekir)"), ("Yolculuk", "TAB", "Büyük Görev Kontrol haritası"),
        ("İniş", "W / SPACE", "Ana motor itkisi"), ("İniş", "A / D", "RCS ile dönüş"), ("İniş", "S", "Dönüşü durdur (SAS)")]


def pct(v):
    return i18n.pct(v * 100)


class SettingsScene(Scene):
    title = "AYARLAR"
    title_icon = "settings"
    accent = C["violet"]
    music = None
    ambient = None

    def __init__(self, app):
        super().__init__(app)
        self.ensure_bg("violet", 29, 0.7)
        self.cat = "gfx"
        self.back = "intro"
        self.rows = []
        self.confirm = None
        self.flash = {}

    def enter(self, cat=None, back=None, **kw):
        if cat:
            self.cat = cat
        if back:
            self.back = back
        elif not self.game.s:
            self.back = "intro"
        self.confirm = None
        self.rebuild()

    # ------------------------------------------------------------------ yardımcı
    def row(self, label, desc=None):
        y = PY + 70 + len(self.rows) * ROW
        self.rows.append((y, label, desc))
        return y

    def toggle(self, label, desc, value, fn):
        y = self.row(label, desc)
        self.add(Toggle((CX, y + 6, 440, 36), value, fn, "AÇIK" if value else "KAPALI", C["violet"]))

    def slider(self, label, desc, value, fn, lo=0.0, hi=1.0, fmt=None, color=None):
        y = self.row(label, desc)
        k = (value - lo) / (hi - lo)
        self.add(Slider((CX, y + 22, 440, 18), max(0.0, min(1.0, k)), lambda v: fn(lo + v * (hi - lo)), color or C["cyan"], "",
                        fmt=(lambda v: fmt(lo + v * (hi - lo))) if fmt else (lambda v: pct(lo + v * (hi - lo)))))

    def choice(self, label, desc, options, current, fn, w=None):
        y = self.row(label, desc)
        n = len(options)
        bw = w or (440 - (n - 1) * 8) // n
        for i, (val, lab) in enumerate(options):
            b = self.add(Button((CX + i * (bw + 8), y + 6, bw, 38), lab, (lambda v=val: fn(v)), accent=C["gold"], size=13, style="tab"))
            b.selected = val == current

    # ------------------------------------------------------------------ arayüz
    def rebuild(self):
        self.widgets = []
        self.rows = []
        for i, (k, lab, ic) in enumerate(CATS):
            b = self.add(Button((40, PY + i * 58, 270, 50), lab, (lambda k=k: self.set_cat(k)), accent=C["violet"], icon=ic, size=15,
                                style="tab"))
            b.selected = k == self.cat
        self.add(Button((24, H - 70, 170, 48), "GERİ", lambda: self.app.go(self.back), icon="arrow_left", accent=C["text_dim"],
                        size=17, hotkey=pygame.K_ESCAPE))
        getattr(self, "build_" + self.cat)()

    def set_cat(self, k):
        self.cat = k
        self.confirm = None
        self.rebuild()

    def sset(self, key, v):
        SET.set(key, v, save=False)
        self._dirty = True

    def changed(self, msg=None, rebuild=True):
        self.app.audio.play("click", 0.6)
        if rebuild:
            self.rebuild()

    # --- GÖRÜNTÜ
    def build_gfx(self):
        q = i18n.PREFS.get("quality", "high")
        self.choice("Grafik kalitesi", i18n.QUALITY_LABEL.get(q, ("", ""))[1], [(k, i18n.QUALITY_LABEL[k][0]) for k in i18n.QUALITY_ORDER],
                    q, self.set_quality, 104)
        self.slider("Parlama (bloom)", "Parlak ışıkların çevresindeki ışıma. 0 = kapalı.", SET.get("bloom_k"),
                    lambda v: self.sset("bloom_k", round(v, 2)), 0.0, 1.5, lambda v: f"×{v:.2f}", C["gold"])
        self.toggle("Süzülen toz zerreleri", "Sinematik ışık huzmelerindeki toz parçacıkları.", SET.get("motes"),
                    lambda v: (SET.set("motes", v), self.changed()))
        self.slider("Yıldız yoğunluğu", "Arka plandaki yıldız sayısı (yeni açılan ekranlarda uygulanır).", SET.get("stars_k"),
                    lambda v: self.sset("stars_k", round(v, 2)), 0.25, 1.5, lambda v: f"×{v:.2f}")
        self.slider("Parçacık miktarı", "Toz, kıvılcım, iniş bulutu gibi parçacık efektleri.", SET.get("fx_k"),
                    lambda v: self.sset("fx_k", round(v, 2)), 0.25, 1.5, lambda v: f"×{v:.2f}")
        self.toggle("Sinematik efektler", "Işık huzmeleri, pus, kenar ışığı, fırça dokusu. Yavaş cihazlarda kapat.",
                    i18n.PREFS.get("cinematic", True), self.set_cinema)
        self.choice("Kare hızı sınırı", "Daha düşük sınır pil ve işlemci tasarrufu sağlar.",
                    [(f, f"{f} FPS" if f else "SINIRSIZ") for f in SET.FPS_CHOICES], SET.get("fps_cap"),
                    lambda v: (SET.set("fps_cap", v), self.changed()))
        self.toggle("FPS göstergesi", "Sağ altta kare hızı (kısayol: F3).", self.app.fps_show, self.set_fps_show)
        y = self.row("Tam ekran", "Kısayol: F11. Tarayıcıda sayfanın tam ekran düğmesini de kullanabilirsin.")
        self.add(Button((CX, y + 6, 440, 38), "TAM EKRANA GEÇ / ÇIK", self.app.toggle_fullscreen, accent=C["violet"], size=14))

    def set_quality(self, q):
        i18n.PREFS["quality"] = q
        i18n.save_prefs()
        self.changed()

    def set_cinema(self, v):
        i18n.PREFS["cinematic"] = v
        i18n.save_prefs()
        self.changed()

    def set_fps_show(self, v):
        self.app.fps_show = v
        SET.set("show_fps", v)
        self.changed()

    # --- SES
    def build_audio(self):
        a = SET.get("audio")
        self.toggle("Ses ve müzik", "Bütün sesleri aç / kapat.", a["enabled"], lambda v: self.set_audio("enabled", v, True))
        for key, lab, desc, col in (("master", "Ana ses", "Bütün seslerin ortak düzeyi.", C["violet"]),
                                    ("music", "Müzik", "Sahne müzikleri ve dinamik müzik.", C["cyan"]),
                                    ("sfx", "Efektler", "Fırlatma, patlama, iniş, keşif sesleri.", C["orange"]),
                                    ("amb", "Ortam", "Rüzgâr, okyanus, üs ve kabin uğultusu, canlı sesleri.", C["green"]),
                                    ("ui", "Arayüz", "Düğme tıklamaları ve bildirimler.", C["gold"]),
                                    ("voice", "NOVA sesi", "NOVA konuşurken çıkan robot sesi.", C["pink"])):
            self.slider(lab, desc, a[key], (lambda v, k=key: self.set_audio(k, round(v, 2))), color=col)
        self.toggle("Arka planda sustur", "Pencere odağını kaybedince ses duraklar.", a["mute_unfocused"],
                    lambda v: self.set_audio("mute_unfocused", v, True))
        y = self.row("Ses testi", "Ayarları dinleyerek dene.")
        for i, (lab, fn) in enumerate((("EFEKT", lambda: self.app.audio.play("success")),
                                       ("ARAYÜZ", lambda: self.app._ui_sound("click")),
                                       ("NOVA", lambda: self.app.audio.speak("Merhaba, ses ayarlarin hazir.")),
                                       ("ORTAM", lambda: self.app.audio.play("whoosh")))):
            self.add(Button((CX + i * 112, y + 6, 104, 38), lab, fn, accent=C["cyan"], size=13))

    def set_audio(self, k, v, rebuild=False):
        SET.set_audio(k, v, save=rebuild)
        SET.apply_audio(self.app)
        if rebuild:
            self.changed()
        else:
            self._dirty = True

    # --- OYUN
    def build_game(self):
        self.toggle("NOVA ipuçları", "NOVA'nın öneri ve hatırlatmaları. Kapalıyken yalnız önemli uyarılar gösterilir.",
                    SET.get("nova_hints"), lambda v: (SET.set("nova_hints", v), self.changed()))
        self.choice("Otomatik kayıt", "Belirlenen aralıkta kampanya kaydedilir. Fırlatma, koloni, araştırma gibi olaylarda her zaman kaydedilir.",
                    [(m, f"{m} dk" if m else "KAPALI") for m in SET.AUTOSAVE_CHOICES], SET.get("autosave_min"),
                    lambda v: (SET.set("autosave_min", v), self.changed()), 82)
        self.toggle("Açıklama balonları", "Fare bir düğmenin üstünde durunca çıkan açıklamalar.", SET.get("tooltips"),
                    lambda v: (SET.set("tooltips", v), self.changed()))
        if self.game.s:
            y = self.row("Ajans adı", "Adı AJANS > AYARLAR'dan değiştirebilirsin (Para gerektirir).")
            self.add(Button((CX, y + 6, 440, 38), "AJANS EKRANINA GİT", lambda: self.app.go("agency", tab=3), accent=C["gold"], size=14))

    # --- ERİŞİLEBİLİRLİK
    def build_access(self):
        cs = self.app.cae.settings
        self.toggle("Hareketi azalt", "Ekran geçişleri neredeyse anında olur, ekran sarsıntısı kapanır.", SET.get("reduce_motion"),
                    lambda v: (SET.set("reduce_motion", v), self.changed()))
        self.slider("Ekran sarsıntısı", "Çarpışma, iniş ve patlamalardaki kamera sarsıntısı.", SET.get("shake"),
                    lambda v: self.sset("shake", round(v, 2)), color=C["orange"])
        self.toggle("Altyazılar", "Önemli sesler ekranda yazıyla da gösterilir (gök gürültüsü, keşif, uyarı).", cs["captions"],
                    lambda v: self.set_cae("captions", v))
        self.toggle("Mono ses", "Sol ve sağ kanal birleşir (tek kulaklık / işitme kaybı).", cs["mono"], lambda v: self.set_cae("mono", v))
        self.toggle("Yüksek frekansları azalt", "Tiz sesler yumuşatılır (4 kHz üstü).", cs["reduce_high"],
                    lambda v: self.set_cae("reduce_high", v, True))
        self.toggle("Ani yüksek sesleri sınırla", "Patlama gibi sesler tavanı aşmaz (bozulmasız sınırlayıcı).", cs["limit_loud"],
                    lambda v: self.set_cae("limit_loud", v, True))
        self.toggle("Oyun imleci", "Kapalıyken işletim sisteminin standart imleci kullanılır.", SET.get("custom_cursor"),
                    lambda v: (SET.set("custom_cursor", v), self.changed()))

    def set_cae(self, k, v, resynth=False):
        cae = self.app.cae
        cae.settings.set(k, v)
        i18n.save_prefs()
        if resynth:                          # süzgeçler sentez sırasında uygulanır: önbellek yenilenir
            cae.assets.cache.clear()
            cae.assets.bytes = 0
            if cae.world is not None:
                cae.refresh_ambience()
        self.changed()

    # --- DİL
    def build_lang(self):
        self.row("Dil", "Oyun her açılışta İngilizce başlar; burada bu oturum için dili değiştirebilirsin.")
        for i, (code, label) in enumerate(i18n.LANGS):
            b = self.add(Button((PX + 30 + (i % 3) * 300, PY + 150 + (i // 3) * 70, 280, 56), label, (lambda c=code: self.set_lang(c)),
                                accent=C["cyan"], size=17, style="tab"))
            b.selected = i18n.LANG == code

    def set_lang(self, code):
        i18n.set_lang(code)
        if self.game.s:
            self.app.on_game_ready()
        self.changed()

    # --- KONTROLLER
    def build_keys(self):
        pass

    # --- VERİ
    def build_data(self):
        has = bool(self.game.s)
        y = self.row("Kampanyayı kaydet", "Şu anki ilerlemeyi hemen kaydeder.")
        b = self.add(Button((CX, y + 6, 440, 38), "ŞİMDİ KAYDET", self.save_now, accent=C["green"], icon="save", size=14))
        b.set_enabled(has, "Açık bir kampanya yok")
        y = self.row("Ana menü", "Kampanya kaydedilir ve ana menüye dönülür.")
        b = self.add(Button((CX, y + 6, 440, 38), "ANA MENÜYE DÖN", self.to_menu, accent=C["cyan"], icon="home", size=14))
        b.set_enabled(has, "Açık bir kampanya yok")
        y = self.row("Ayarları sıfırla", "Görüntü, ses, oyun ve erişilebilirlik ayarları varsayılana döner (kampanya etkilenmez).")
        self.add(Button((CX, y + 6, 440, 38), "EMİN MİSİN? TEKRAR TIKLA" if self.confirm == "reset" else "VARSAYILANLARA DÖN",
                        self.reset, accent=C["orange"], size=14))
        y = self.row("Kampanyayı sil", "Kayıt dosyası kalıcı olarak silinir. Geri alınamaz.")
        b = self.add(Button((CX, y + 6, 440, 38), "EMİN MİSİN? TEKRAR TIKLA" if self.confirm == "delete" else "KAYDI SİL", self.delete,
                            accent=C["red"], icon="cross", size=14, style="danger"))
        b.set_enabled(has or self.game.has_save(), "Kayıt yok")
        b.pulse = self.confirm == "delete"

    def save_now(self):
        ok = self.game.save()
        self.app.toast("Kampanya kaydedildi" if ok else "Kayıt başarısız: " + str(self.game.save_error), "green" if ok else "red", "save")

    def to_menu(self):
        self.game.save()
        self.app.go("intro")

    def reset(self):
        if self.confirm != "reset":
            self.confirm = "reset"
            self.rebuild()
            return
        SET.reset()
        cae = self.app.cae.settings
        cae.d.update({k: v for k, v in cae.DEFAULT.items() if k != "vol"})
        cae.d["vol"] = dict(cae.DEFAULT["vol"])
        cae.save()
        i18n.PREFS["cinematic"] = True
        i18n.save_prefs()
        SET.apply_audio(self.app)
        self.app.fps_show = False
        self.confirm = None
        self.app.toast("Ayarlar varsayılana döndü", "orange", "settings")
        self.rebuild()

    def delete(self):
        if self.confirm != "delete":
            self.confirm = "delete"
            self.rebuild()
            return
        self.game.delete_save()
        self.game.s = None
        self.confirm = None
        self.app.go("intro")

    # ------------------------------------------------------------------- döngü
    def update(self, dt):
        super().update(dt)
        if getattr(self, "_dirty", False) and not pygame.mouse.get_pressed()[0]:
            self._dirty = False
            i18n.save_prefs()            # kaydırıcı bırakılınca diske yaz

    def draw(self, surf):
        self.bg.draw(surf)
        self.draw_title(surf, sub="Görüntü · ses · oyun · erişilebilirlik · dil · kontroller · veri")
        r = pygame.Rect(PX, PY, PW, PH)
        glass_panel(surf, r, C["violet"], 180, 18)
        lab = dict((k, l) for k, l, _ in CATS)[self.cat]
        draw_text(surf, lab, (r.x + 28, r.y + 22), 20, C["text"], bold=True, glow=scale_color(C["violet"], 0.4))
        for y, label, desc in self.rows:
            pygame.draw.line(surf, (40, 46, 74), (r.x + 24, y + ROW - 4), (r.right - 24, y + ROW - 4), 1)
            draw_text(surf, label, (r.x + 30, y + 6), 16, C["text"], bold=True)
            if desc:
                draw_paragraph(surf, desc, (r.x + 30, y + 28), CX - r.x - 60, 12, C["text_dim"], max_lines=2)
        if self.cat == "keys":
            self.draw_keys(surf, r)
        elif self.cat == "data":
            draw_text(surf, tr("Kayıt dosyası") + f": {SAVE_FILE}", (r.x + 30, r.bottom - 64), 12, C["text_mute"], raw=True, max_w=r.w - 60)
            draw_text(surf, "Ayarlar kampanyadan ayrı saklanır; kaydı silmek ayarları değiştirmez.", (r.x + 30, r.bottom - 40), 12,
                      C["text_dim"])
        elif self.cat == "audio":
            self.draw_meter(surf, r)
        self.draw_widgets(surf)

    def draw_keys(self, surf, r):
        draw_text(surf, "Tuşlar sabittir; bu liste başvuru içindir.", (r.x + 30, r.y + 58), 13, C["text_dim"])
        y = r.y + 92
        for i, (where, key, what) in enumerate(KEYS):
            if i % 2 == 0:
                pygame.draw.rect(surf, (18, 22, 42), (r.x + 20, y - 4, r.w - 40, 30), border_radius=6)
            draw_text(surf, where, (r.x + 34, y), 14, C["cyan"], bold=True)
            draw_text(surf, key, (r.x + 260, y), 14, C["gold"], bold=True)
            draw_text(surf, what, (r.x + 520, y), 14, C["text"])
            y += 32

    def draw_meter(self, surf, r):
        """Canlı çıkış göstergesi: o an çalan kanal sayısı (karıştırma payı)."""
        try:
            busy = sum(1 for i in range(pygame.mixer.get_num_channels()) if pygame.mixer.Channel(i).get_busy())
        except Exception:
            busy = 0
        x, y = r.right - 300, r.y + 24
        draw_text(surf, tr("Çalan ses kanalı") + f": {busy}", (x, y), 13, C["text_dim"], raw=True)
        for i in range(16):
            col = C["green"] if i < 10 else C["gold"] if i < 14 else C["red"]
            on = i < busy
            pygame.draw.rect(surf, col if on else (30, 36, 56), (x + i * 16, y + 22, 12, 10), border_radius=2)
