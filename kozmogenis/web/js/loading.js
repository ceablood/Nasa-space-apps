// KOZMOGENİS — sinematik yükleme / menü arka planı (Canvas 2D, harici görsel yok).
// Derinlikli yıldız alanı (paralaks + yükleme hızıyla "warp"), nebula, prosedürel yüzeyli dönen gezegen
// (gece-gündüz sınırı, atmosfer halkası, şehir ışıkları), yörüngede iz bırakan araç.

const TAU = Math.PI * 2;

function hash(x, y) {
  const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
  return s - Math.floor(s);
}
function noise(x, y) {
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = hash(xi, yi), b = hash(xi + 1, yi), c = hash(xi, yi + 1), d = hash(xi + 1, yi + 1);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
function fbm(x, y) {
  let s = 0, a = 0.5, f = 1;
  for (let i = 0; i < 5; i++) { s += a * noise(x * f, y * f); a *= 0.5; f *= 2; }
  return s;
}

// eşdikdörtgen gezegen dokusu (bir kez üretilir): okyanus/kara/buz ya da kraterli/tozlu tonlar
function planetTexture(kind, w = 512, h = 256) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const g = c.getContext('2d');
  const img = g.createImageData(w, h);
  for (let y = 0; y < h; y++) {
    const lat = (y / h - 0.5) * Math.PI;
    for (let x = 0; x < w; x++) {
      const lon = (x / w) * TAU;
      // küre üzerinde dikiş olmayan gürültü: 3B koordinattan
      const cx = Math.cos(lat) * Math.cos(lon), cy = Math.sin(lat), cz = Math.cos(lat) * Math.sin(lon);
      const n = fbm(cx * 2.2 + 10, cz * 2.2 + cy * 1.3 + 5);
      const m = fbm(cx * 6 + 3, cz * 6 - cy * 4);
      let r, gg, b;
      if (kind === 'earth') {
        const land = n > 0.52;
        const ice = Math.abs(cy) > 0.86 - m * 0.08;
        if (ice) { r = 205; gg = 214; b = 222; }
        else if (land) { const t = (n - 0.52) * 4; r = 70 + 90 * t + 30 * m; gg = 95 + 50 * t; b = 50 + 20 * t; }
        else { const t = n * 1.6; r = 12 + 20 * t; gg = 42 + 50 * t; b = 92 + 70 * t; }
        const cloud = fbm(cx * 3.1 - 7, cz * 3.1 + cy * 2.4 + 2);
        if (cloud > 0.56) { const k = Math.min(1, (cloud - 0.56) * 4); r += (222 - r) * k; gg += (226 - gg) * k; b += (232 - b) * k; }
      } else if (kind === 'mars') {
        r = 150 + 70 * n; gg = 70 + 35 * n; b = 38 + 15 * n;
        if (Math.abs(cy) > 0.9) { r = 220; gg = 214; b = 206; }
        const dark = m < 0.38 ? 0.6 : 1; r *= dark; gg *= dark; b *= dark;
      } else { // moon
        const k = Math.min(1, Math.max(0, (m - 0.5) / 0.18)), mare = k * k * (3 - 2 * k);   // yumuşak kenarlı denizler
        const v = 128 + 95 * n - 52 * mare;
        r = v; gg = v; b = v * 0.97;
      }
      const i = (y * w + x) * 4;
      img.data[i] = r; img.data[i + 1] = gg; img.data[i + 2] = b; img.data[i + 3] = 255;
    }
  }
  g.putImageData(img, 0, 0);
  return c;
}

export class SpaceBackdrop {
  constructor(canvas, opts = {}) {
    this.c = canvas;
    this.g = canvas.getContext('2d');
    this.kind = opts.planet || 'earth';
    this.pos = opts.pos;     // [x, y, yarıçap] ekran oranı
    this.speed = 0.15;       // warp hızı (yükleme ilerledikçe artar)
    this.t = 0;
    this.running = true;
    this.stars = [];
    for (let i = 0; i < 900; i++) this.stars.push({ x: Math.random() * 2 - 1, y: Math.random() * 2 - 1, z: Math.random(), hue: Math.random() });
    this.tex = planetTexture(this.kind);
    this.resize();
    addEventListener('resize', () => this.resize());
    this.last = performance.now();
    const loop = (now) => {
      if (!this.running) return;
      const dt = Math.min(0.05, (now - this.last) / 1000);
      this.last = now;
      this.draw(dt);
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }
  resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 1.75);
    this.w = this.c.clientWidth; this.h = this.c.clientHeight;
    this.c.width = Math.max(1, this.w * dpr); this.c.height = Math.max(1, this.h * dpr);
    this.g.setTransform(dpr, 0, 0, dpr, 0, 0);
    // nebula katmanı (bir kez)
    this.neb = document.createElement('canvas');
    this.neb.width = 512; this.neb.height = 288;
    const n = this.neb.getContext('2d');
    const im = n.createImageData(512, 288);
    for (let y = 0; y < 288; y++) for (let x = 0; x < 512; x++) {
      const v = fbm(x / 120, y / 120);
      const k = Math.max(0, v - 0.45) * 2.2;
      const i = (y * 512 + x) * 4;
      im.data[i] = 40 * k + 80 * k * fbm(x / 60 + 9, y / 60);
      im.data[i + 1] = 30 * k;
      im.data[i + 2] = 110 * k;
      im.data[i + 3] = 255 * Math.min(1, k * 0.9);
    }
    n.putImageData(im, 0, 0);
  }
  stop() { this.running = false; }
  draw(dt) {
    const g = this.g, w = this.w, h = this.h;
    this.t += dt;
    g.fillStyle = '#04060c';
    g.fillRect(0, 0, w, h);
    g.globalAlpha = 0.55;
    g.drawImage(this.neb, -w * 0.1, -h * 0.05, w * 1.2, h * 1.1);
    g.globalAlpha = 1;
    // yıldızlar: merkezden dışa akış (warp), hızla çizgi uzar
    const cx = w * 0.62, cy = h * 0.46, sp = this.speed;
    for (const s of this.stars) {
      s.z -= dt * sp * 0.35;
      if (s.z <= 0.02) { s.z = 1; s.x = Math.random() * 2 - 1; s.y = Math.random() * 2 - 1; }
      const k = 1 / s.z;
      const x = cx + s.x * w * 0.5 * k * 0.35, y = cy + s.y * h * 0.5 * k * 0.35;
      if (x < -50 || x > w + 50 || y < -50 || y > h + 50) { s.z = 1; continue; }
      const k2 = 1 / (s.z + dt * sp * 0.35 * 6);
      const px = cx + s.x * w * 0.5 * k2 * 0.35, py = cy + s.y * h * 0.5 * k2 * 0.35;
      const a = Math.min(1, (1 - s.z) * 1.4);
      g.strokeStyle = s.hue > 0.85 ? `rgba(255,200,150,${a})` : (s.hue > 0.7 ? `rgba(170,200,255,${a})` : `rgba(225,232,245,${a})`);
      g.lineWidth = Math.max(0.6, (1 - s.z) * 2.2);
      g.beginPath(); g.moveTo(px, py); g.lineTo(x, y); g.stroke();
    }
    this.drawPlanet(g, w, h);
  }
  planetRes() {
    const N = 300;
    if (this.pp) return N;
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = N;
    const ctx = canvas.getContext('2d');
    const img = ctx.createImageData(N, N);
    const tw = this.tex.width, th = this.tex.height;
    this.texData = this.tex.getContext('2d').getImageData(0, 0, tw, th).data;
    // şehir ışıkları: karada seyrek noktalar (yalnız Dünya)
    this.city = new Uint8Array(tw * th);
    if (this.kind === 'earth') for (let i = 0; i < tw * th; i++) {
      const r = this.texData[i * 4], gg = this.texData[i * 4 + 1], b = this.texData[i * 4 + 2];
      if (r > b && gg > b && r < 190 && hash(i % tw, (i / tw) | 0) > 0.93) this.city[i] = 1;
    }
    const sun = [-0.62, -0.42, 0.66];   // ışık sol üstten, izleyiciye doğru
    const sl = Math.hypot(...sun); sun[0] /= sl; sun[1] /= sl; sun[2] /= sl;
    const idx = [], lat = [], lon = [], light = [], night = [], alpha = [];
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
      const nx = (x + 0.5) / N * 2 - 1, ny = (y + 0.5) / N * 2 - 1, d2 = nx * nx + ny * ny;
      if (d2 > 1) continue;
      const nz = Math.sqrt(1 - d2);
      // eksen eğikliği ~23°
      const tilt = 0.4, cy = ny * Math.cos(tilt) - nz * Math.sin(tilt), cz = ny * Math.sin(tilt) + nz * Math.cos(tilt);
      const la = Math.asin(Math.max(-1, Math.min(1, cy))), lo = Math.atan2(nx, cz);
      idx.push(y * N + x);
      lat.push(Math.min(th - 1, Math.max(0, Math.floor((la / Math.PI + 0.5) * th))));
      lon.push(((Math.floor((lo / TAU + 0.5) * tw) % tw) + tw) % tw);
      const dot = nx * sun[0] + ny * sun[1] + nz * sun[2];
      const day = Math.max(0, Math.min(1, dot * 2.2 + 0.25));
      const limb = 0.55 + 0.45 * Math.pow(nz, 0.5);   // kenar kararması
      light.push((0.04 + 0.96 * day * day) * limb);
      night.push(day < 0.2 ? (0.2 - day) * 3.5 * 0.55 : 0);
      alpha.push(d2 > 0.985 ? Math.round((1 - d2) / 0.015 * 255) : 255);
    }
    this.pp = { canvas, ctx, img, idx: Int32Array.from(idx), lat: Int32Array.from(lat), lon: Int32Array.from(lon),
      light: Float32Array.from(light), night: Float32Array.from(night), alpha: Uint8Array.from(alpha) };
    return N;
  }
  drawPlanet(g, w, h) {
    const P0 = this.pos || [0.8, 0.8, 0.36];
    const R = Math.min(w, h) * P0[2];
    const px = w * P0[0], py = h * P0[1];
    // atmosfer dış parıltısı
    const atm = this.kind === 'mars' ? '255,150,90' : (this.kind === 'moon' ? '170,180,200' : '90,180,255');
    const glow = g.createRadialGradient(px, py, R * 0.95, px, py, R * 1.35);
    glow.addColorStop(0, `rgba(${atm},0.35)`);
    glow.addColorStop(1, `rgba(${atm},0)`);
    g.fillStyle = glow;
    g.beginPath(); g.arc(px, py, R * 1.35, 0, TAU); g.fill();
    // yüzey: piksel başına ortografik izdüşüm (enlem sıkışması doğru, dikiş yok). Enlem/boylam ve aydınlatma
    // bir kez hesaplanır; her karede yalnız boylam kaydırılır.
    this.planetRes();
    const P = this.pp, tex = this.texData, tw = this.tex.width, th = this.tex.height;
    const shift = Math.floor((this.t * 0.012 % 1) * tw);
    const out = P.img.data;
    for (let k = 0, n = P.idx.length; k < n; k++) {
      const j = P.idx[k];
      let tx = P.lon[k] + shift; if (tx >= tw) tx -= tw;
      const ti = (P.lat[k] * tw + tx) * 4, o = j * 4;
      const L = P.light[k];
      let r = tex[ti] * L, gg = tex[ti + 1] * L, b = tex[ti + 2] * L;
      if (P.night[k] > 0 && this.city[P.lat[k] * tw + tx]) { const c = P.night[k] * 255; r += c; gg += c * 0.72; b += c * 0.4; }
      out[o] = r; out[o + 1] = gg; out[o + 2] = b; out[o + 3] = P.alpha[k];
    }
    P.ctx.putImageData(P.img, 0, 0);
    g.drawImage(P.canvas, px - R, py - R, R * 2, R * 2);
    // ince atmosfer halkası (ışık tarafı parlak)
    const rim = g.createLinearGradient(px - R, py - R, px + R, py + R);
    rim.addColorStop(0, `rgba(${atm},0.85)`);
    rim.addColorStop(0.55, `rgba(${atm},0.08)`);
    rim.addColorStop(1, `rgba(${atm},0)`);
    g.strokeStyle = rim; g.lineWidth = R * 0.035;
    g.beginPath(); g.arc(px, py, R * 1.01, 0, TAU); g.stroke();
    // yörüngedeki araç ve izi (eğik elips)
    const ot = this.t * 0.35;
    g.save();
    g.translate(px, py); g.rotate(-0.42);
    g.strokeStyle = 'rgba(62,230,255,0.18)'; g.lineWidth = 1;
    g.beginPath(); g.ellipse(0, 0, R * 1.55, R * 0.42, 0, 0, TAU); g.stroke();
    for (let k = 0; k < 26; k++) {
      const a = ot - k * 0.02;
      const x = Math.cos(a) * R * 1.55, y = Math.sin(a) * R * 0.42;
      const behind = Math.sin(a) < 0 && Math.abs(x) < R;   // gezegenin arkasında
      if (behind) continue;
      g.fillStyle = `rgba(160,240,255,${(1 - k / 26) * 0.8})`;
      g.beginPath(); g.arc(x, y, k === 0 ? 2.6 : 1.6 * (1 - k / 26) + 0.4, 0, TAU); g.fill();
    }
    g.restore();
  }
}

// gerçek, kaynaklı uzay bilgileri (yükleme ekranında döner)
export const FACTS = [
  ['Apollo 11 Ay modülü Eagle, 20 Temmuz 1969\'da Huzur Denizi\'ne indiğinde yaklaşık 45 saniyelik yakıtı kalmıştı.', 'NASA Apollo 11 Görev Raporu'],
  ['Ay yüzeyinde korumasız günlük radyasyon dozu ~1,37 mSv; Dünya\'dakinin yaklaşık 200 katı.', 'Chang\'e-4 LND, Science Advances 2020'],
  ['Mars\'ta ses ~240 m/s hızla yayılır ve aynı kaynak Dünya\'dakinden ~20 dB daha zayıf duyulur.', 'Perseverance SuperCam, Nature 2022'],
  ['DART aracı 2022\'de Dimorphos\'a çarparak asteroitin yörünge periyodunu yaklaşık 33 dakika kısalttı.', 'NASA / JHU APL'],
  ['ISS her gün atmosfer sürtünmesiyle onlarca metre alçalır; düzenli olarak yeniden itkiyle yükseltilir.', 'NASA ISS Trajectory Data'],
  ['ISS\'in su geri kazanım sistemi 2023\'te %98 verime ulaştı: idrar dahil suyun neredeyse tamamı geri dönüştürülüyor.', 'NASA ECLSS, 2023'],
  ['Titan\'a inen Huygens sondası paraşütle ~2,5 saat alçaldı ve yere ~5 m/s hızla değdi.', 'ESA Huygens, 2005'],
  ['Uzay giysisi (EMU) 29,6 kPa saf oksijenle çalışır; vurgun riskine karşı astronotlar önceden saf O₂ solur.', 'NASA-STD-3001'],
  ['Dünya–Mars Hohmann transferi ~259 gün sürer; uygun pencere her ~26 ayda bir açılır.', 'Yörünge mekaniği (Hohmann 1925)'],
  ['Bennu asteroidinin 2300\'e kadar Dünya\'ya çarpma olasılığı yaklaşık 1/2700 olarak hesaplandı.', 'OSIRIS-REx, Icarus 2021'],
];
