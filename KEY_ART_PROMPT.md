# AETHER-X · Anahtar Görsel (Key Art) Promptu

Bu dosyada iki şey var:

1. **Oyuna uyarlanmış görsel üretim promptu.** Oyundan aldığın bir ekran görüntüsünü bir görsel yapay zekâsına
   (Midjourney, DALL·E, Stable Diffusion img2img, Firefly vb.) verip tanıtım görseline çevirmek için kullanılır.
   Prompt İngilizcedir, çünkü bu araçlar İngilizceyi en iyi anlar.
2. **Oyun içi karşılığı.** Aynı yönergenin oyunda kodla nasıl uygulandığı
   (AJANS → Ayarlar → SİNEMATİK EFEKTLER).

---

## 1. Ana prompt (bütün ekranlar için)

```
Transform this raw AETHER-X gameplay screenshot into ultra-high-end, museum-grade stylized 3D promotional key art
for a space-agency command game, blending the hand-painted painterly aesthetics of Arcane (Fortiche) with the
polished, vibrant material depth of modern stylized AAA games. Strictly preserve the exact spatial composition,
camera perspective, UI-free silhouettes of rockets, astronauts, buildings and planets, and the environmental
storytelling of the original image without altering the core layout.

Overhaul flat surfaces into rich, tactile hand-crafted PBR materials: brushed and riveted rocket hull metal with
beveled panel seams and subtle heat scorching, ceramic heat-shield tiles, woven astronaut-suit fabric with stitched
seams and scuffed knee pads, glass helmet visors with soft reflections, dusty regolith and basalt ground, and
painted signage with visible directional brushstrokes and gentle surface wear. Apply stylized subsurface scattering
to astronaut faces, greenhouse foliage, ice and glowing habitat domes for a warm, lifelike glow.

Re-light the scene with theatrical, emotionally resonant illumination: a low sun just outside the frame casting
volumetric god rays through rocket exhaust and dust, soft atmospheric haze toward the horizon, floating dust motes
catching the light, and warm bounce light from the ground. Use strong, colorful rim lighting (warm amber on the
sun side, cool cyan-violet on the shadow side) to separate rockets, astronauts and planets from the starfield,
paired with deep, saturated violet ambient occlusion in contact shadows.

Color grade with rich complementary harmonies — warm sunlit amber and peach against cool teal and indigo shadows —
plus a gentle vignette and soft bloom on engine flames, habitat windows and neon control panels. Cinematic depth of
field: the focal subject razor-sharp, distant nebulae, planets and background structures softly blurred. Clean,
anti-aliased silhouettes; no jagged polygon edges, no pixel stair-stepping, no muddy shading, no text artifacts.
8k resolution, studio-quality concept-art finish, crisp details, vibrant, cohesive, masterpiece.
```

**Negatif prompt (destekleyen araçlar için):**

```
blurry focal subject, jagged edges, pixelation, low-res textures, flat lighting, muddy colors, oversaturated neon,
distorted UI text, extra limbs, deformed rockets, changed composition, watermark, logo, signature
```

> İpucu: Görsel yapay zekâları ekrandaki yazıları genelde bozar. Yazısız ve temiz bir görüntü için oyunda
> `F3` ile FPS göstergesini kapatıp NOVA balonunun kaybolmasını bekle; en iyi sonucu atlas, koloni, fırlatma
> ve yolculuk ekranları verir. img2img kullanıyorsan "denoise / image weight" değerini 0.35–0.5 aralığında
> tutarsan kompozisyon korunur.

## 2. Ekran bazlı ekler

Ana promptun sonuna, ekrana göre şu cümlelerden birini ekle:

| Ekran | Ek cümle |
|---|---|
| Ana menü | `Dawn over Earth's curved horizon seen from orbit, the sun bursting from the limb, city lights glittering on the night side, the Moon hanging in a painted Milky Way.` |
| Fırlatma üssü | `Top-down miniature spaceport diorama at golden hour, glowing launch pads, research dome, mission-control screens and fuel spheres, tilt-shift miniature feel.` |
| Montaj hangarı | `A rocket standing in a dim assembly hangar under hard work lights, holographic blueprints and telemetry panels glowing cyan and amber.` |
| Fırlatma | `A rocket clearing the launch tower, billowing white exhaust clouds lit orange from below, Max-Q condensation cone, the tower left behind on the ground.` |
| Yolculuk | `A small spacecraft cruising through an asteroid field with a blue ion trail, sunlit rocks with warm rim light, Earth's limb glowing at the edge of frame.` |
| Koloni (Ay / Mars) | `A cozy modular colony of domes and towers on regolith, colonists carrying crates, warm window light at dusk, long soft shadows, rover tracks in the dust.` |
| Atlas | `An orrery-like view of the solar system, glowing sun at the center, planets on luminous orbit lines, a dense asteroid belt sparkling in the light.` |
| NOVA odası | `A friendly AI core with a glowing cyan face in a dark control room, light shafts cutting through the haze, holographic chat panels.` |

## 3. Oyun içi karşılığı

Promptun her maddesi oyunda gerçek zamanlı olarak kodla uygulanıyor (`aetherx/cinema.py`).
Hepsi **AJANS → Ayarlar → SİNEMATİK EFEKTLER** ile açılıp kapatılabilir; arayüz yazıları etkilenmez.

| Prompt maddesi | Oyunda |
|---|---|
| Hacimsel ışık huzmeleri (god rays) | Bütün uzay ekranlarında, üste, NOVA odasında, atlasta, kolonide ve fırlatmada ekran dışındaki güneşten gelen huzmeler |
| Atmosferik pus, toz zerreleri | Her sahnede ufka doğru yoğunlaşan pus ve ışıkta parıldayan toz zerreleri |
| Yönlü fırça darbeleri, tuval dokusu | Arka planlarda, sprite'larda ve 3B kolonide çarpma karışımlı fırça dokusu |
| Renkli kenar ışığı (rim light) | Roketler, güçlendiriciler ve asteroitler: güneş tarafında sıcak amber kenar, karşı tarafta soğuk mor AO |
| Doymuş ortam gölgelemesi (AO) | 3B kolonide temas gölgesi; sprite'larda gölge kenarı; ekran kenarlarında mor vinyet |
| Alt yüzey saçılması (SSS) | 3B kolonide yapraklar ve kubbelerde ışık geçirgenliği |
| Tamamlayıcı renk uyumu | Her ekran paletine göre sıcak ışık / soğuk gölge eşleşmesi (deep, ember, teal, violet) |
| Parlama (bloom) | Motor alevleri, pencereler ve neon paneller için tüm ekrana yumuşak, çok kademeli ışık taşması |
| Sinematik alan derinliği | 3B kolonide tilt-shift (minyatür) alan derinliği bulanıklığı |
| Tırtıksız silüetler | 3B kolonide süper örnekleme (kaliteye göre 1.0×–2.0×); menüde Dünya kıyıları pürüzsüzleştirildi |
| 8K | Oyun 1600×900 tuvalde çizilip ekran çözünürlüğüne (4K dahil) ölçeklenir; MAKSİMUM kalitede 2048×4096 gezegen dokuları |
