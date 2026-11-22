// KOZMOGENİS — Three.js 3B dünya. Unreal'daki AKozmoExpeditionScene + AKozmogenisColony + AKozmogenisNPC +
// AKozmogenisSpacecraft + AKozmoTerrainActor karşılığı. Bütün konumlar ve durumlar KozmoCore'dan gelir;
// burada yalnız çizim ve görsel ara değer (yumuşatma) yapılır.
import * as THREE from '../vendor/three.module.min.js';

// çekirdek planı (x doğu, y kuzey, z yukarı, metre) -> Three (x, y yukarı, z güney)
export const T = (x, y, z = 0) => new THREE.Vector3(x, z, -y);

const JOB_COLORS = [0x4f9a3a, 0xd9822b, 0x8a6a4c, 0x3a6ad0, 0xd8dde6, 0x2b3245, 0xb52a2a];

function canvasTexture(size, paint) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  paint(c.getContext('2d'), size);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

function labelSprite(text, opts = {}) {
  const pad = 14, fs = opts.size || 40;
  const c = document.createElement('canvas');
  const g = c.getContext('2d');
  g.font = `600 ${fs}px Inter, sans-serif`;
  const lines = String(text).split('\n');
  const w = Math.ceil(Math.max(...lines.map((l) => g.measureText(l).width))) + pad * 2;
  const h = lines.length * fs * 1.25 + pad * 1.4;
  c.width = w; c.height = h;
  g.font = `600 ${fs}px Inter, sans-serif`;
  g.fillStyle = opts.bg || 'rgba(6,10,20,0.72)';
  const r = 14;
  g.beginPath(); g.roundRect(0, 0, w, h, r); g.fill();
  g.strokeStyle = opts.border || 'rgba(62,230,255,0.45)'; g.lineWidth = 2; g.stroke();
  g.fillStyle = opts.color || '#d8f4ff';
  lines.forEach((l, i) => g.fillText(l, pad, pad * 0.7 + fs * (i + 0.95) * 1.18));
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthWrite: false, transparent: true }));
  const k = (opts.scale || 1) * 0.012;
  s.scale.set(w * k, h * k, 1);
  s.renderOrder = 10;
  return s;
}

export class World {
  constructor(canvas, quality) {
    this.canvas = canvas;
    this.quality = quality;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: quality.antialias, powerPreference: 'high-performance' });
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.0;
    this.renderer.shadowMap.enabled = quality.shadows > 0;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.pixelRatio = Math.min(window.devicePixelRatio || 1, quality.maxPixelRatio);
    this.renderer.setPixelRatio(this.pixelRatio);
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(72, 1, 0.1, 60000);
    this.clock = new THREE.Clock();
    this.npcs = new Map();
    this.targets = [];      // etkileşim hedefleri
    this.buildings = new Map();
    this.resize();
    addEventListener('resize', () => this.resize());
    this.frameTimes = [];
  }

  resize() {
    const w = this.canvas.clientWidth || innerWidth, h = this.canvas.clientHeight || innerHeight;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  // ---------------------------------------------------------------- kurulum
  build(core, body, buildings) {
    this.core = core;
    this.body = body;
    this.scene.clear();
    this.npcs.clear();
    this.buildings.clear();
    this.targets = [];
    this.setupSky(body);
    this.setupTerrain(core.mesh(), body);
    this.setupRocks(core, body);
    this.colony = new THREE.Group();
    this.scene.add(this.colony);
    this.setColony(buildings);
    this.setupLander();
    this.setupDust();
    // gölgelendiricileri yükleme perdesi arkasında derle: ilk saniyelerdeki takılmayı önler
    this.renderer.compile(this.scene, this.camera);
  }

  setupSky(body) {
    const s = this.scene;
    const sunDir = new THREE.Vector3(-0.55, 0.42, -0.35).normalize();
    this.sunDir = sunDir;
    if (body === 'moon') {
      s.background = new THREE.Color(0x000000);
      s.fog = null;
      this.ambient = new THREE.HemisphereLight(0x8090a8, 0x2a2824, 0.45);   // gökyüzü ışığı yok: zemin yansıması + Dünya ışığı (oynanabilirlik için yükseltilmiş)
      this.sun = new THREE.DirectionalLight(0xfff4e6, 3.6);
    } else if (body === 'mars') {
      s.fog = new THREE.FogExp2(0xc8926a, 0.0016);
      this.ambient = new THREE.HemisphereLight(0xe8b48a, 0x3a1c10, 0.55);
      this.sun = new THREE.DirectionalLight(0xffe2c4, 2.2);              // 1,52 AU: ~%43 güneş
    } else {
      s.fog = new THREE.FogExp2(0xb07a3a, 0.006);                        // Titan tolin pusu
      this.ambient = new THREE.HemisphereLight(0xd8a45a, 0x2a1a0a, 0.7);
      this.sun = new THREE.DirectionalLight(0xffc888, 0.55);
    }
    s.add(this.ambient);
    // dolgu ışığı: güneşin karşısından zayıf (Ay'da Dünya ışığı + regolit yansıması; diğerlerinde gök ışığı)
    const fill = new THREE.DirectionalLight(body === 'moon' ? 0x9fb4d8 : 0xd8b090, body === 'moon' ? 0.55 : 0.35);
    fill.position.copy(sunDir.clone().multiplyScalar(-300).setY(160));
    s.add(fill);
    this.sun.position.copy(sunDir.clone().multiplyScalar(400));
    this.sun.castShadow = this.quality.shadows > 0;
    if (this.sun.castShadow) {
      this.sun.shadow.mapSize.set(this.quality.shadows, this.quality.shadows);
      const sc = this.sun.shadow.camera;
      sc.left = -160; sc.right = 160; sc.top = 160; sc.bottom = -160; sc.near = 1; sc.far = 1200;
      this.sun.shadow.bias = -0.0004;
      this.sun.shadow.normalBias = 0.6;
    }
    s.add(this.sun);
    s.add(this.sun.target);
    // gök kubbesi
    const skyGeo = new THREE.SphereGeometry(20000, 48, 24);
    const top = body === 'moon' ? new THREE.Color(0x000000) : (body === 'mars' ? new THREE.Color(0xb98a66) : new THREE.Color(0xc0883c));
    const horizon = body === 'moon' ? new THREE.Color(0x000000) : (body === 'mars' ? new THREE.Color(0xe7b48a) : new THREE.Color(0xe2a454));
    const glowC = body === 'mars' ? new THREE.Color(0x9cb8d8) : new THREE.Color(0xfff0d0);   // Mars'ta güneş çevresi mavimsi (gözlenen)
    this.skyMat = new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: false, fog: false,
      uniforms: { top: { value: top }, horizon: { value: horizon }, sun: { value: sunDir }, glow: { value: glowC }, dust: { value: 0 }, spread: { value: body === 'moon' ? 0.0 : 1.0 } },
      vertexShader: 'varying vec3 vDir; void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
      fragmentShader: `uniform vec3 top; uniform vec3 horizon; uniform vec3 sun; uniform vec3 glow; uniform float dust; uniform float spread; varying vec3 vDir;
        void main(){ float h = clamp(vDir.y, 0.0, 1.0); vec3 c = mix(horizon, top, pow(h, 0.55));
          float s = max(dot(normalize(vDir), normalize(sun)), 0.0);
          c += spread * glow * pow(s, 24.0) * 0.6 + glow * pow(s, 3000.0) * 0.8 + vec3(1.0,0.97,0.9) * smoothstep(0.99995, 0.99998, s) * 4.0;
          c = mix(c, horizon * 0.9, dust);
          gl_FragColor = vec4(c, 1.0); }`,
    });
    const sky = new THREE.Mesh(skyGeo, this.skyMat);
    sky.frustumCulled = false;
    sky.renderOrder = -10;
    this.sky = sky;
    this.skyGroup = new THREE.Group();
    this.skyGroup.add(sky);
    s.add(this.skyGroup);
    if (body === 'moon') {
      // yıldızlar (atmosfer yok: gündüz de görünür) ve gökte Dünya
      const n = 2600, pos = new Float32Array(n * 3), col = new Float32Array(n * 3);
      for (let i = 0; i < n; i++) {
        const u = Math.random() * 2 - 1, th = Math.random() * Math.PI * 2, r = 18000;
        const q = Math.sqrt(1 - u * u);
        pos.set([r * q * Math.cos(th), r * Math.abs(u) * 0.98 + 200, r * q * Math.sin(th)], i * 3);
        const k = 0.6 + Math.random() * 0.4, warm = Math.random() < 0.2;
        col.set(warm ? [k, k * 0.85, k * 0.7] : [k * 0.9, k * 0.95, k], i * 3);
      }
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      g.setAttribute('color', new THREE.BufferAttribute(col, 3));
      this.skyGroup.add(new THREE.Points(g, new THREE.PointsMaterial({ size: 22, sizeAttenuation: true, vertexColors: true, fog: false, depthWrite: false })));
      const earthTex = canvasTexture(256, (gg, sz) => {
        const grad = gg.createRadialGradient(sz * 0.4, sz * 0.4, sz * 0.05, sz / 2, sz / 2, sz / 2);
        grad.addColorStop(0, '#9fd0ff'); grad.addColorStop(0.5, '#2f6fc0'); grad.addColorStop(1, '#0a1a38');
        gg.fillStyle = grad; gg.beginPath(); gg.arc(sz / 2, sz / 2, sz / 2, 0, Math.PI * 2); gg.fill();
        gg.fillStyle = 'rgba(90,140,70,0.85)';
        for (let i = 0; i < 9; i++) { gg.beginPath(); gg.ellipse(40 + Math.random() * 170, 40 + Math.random() * 170, 20 + Math.random() * 30, 10 + Math.random() * 20, Math.random() * 3, 0, Math.PI * 2); gg.fill(); }
        gg.fillStyle = 'rgba(235,240,245,0.75)';
        for (let i = 0; i < 14; i++) { gg.beginPath(); gg.ellipse(Math.random() * sz, Math.random() * sz, 18 + Math.random() * 30, 5 + Math.random() * 8, Math.random() * 3, 0, Math.PI * 2); gg.fill(); }
      });
      const earth = new THREE.Mesh(new THREE.SphereGeometry(520, 48, 32), new THREE.MeshStandardMaterial({ map: earthTex, emissive: 0x0a1630, roughness: 0.6, fog: false }));
      earth.position.set(5200, 7600, -11000);   // Ay'dan Dünya ~2° çapında (görsel ölçek)
      this.skyGroup.add(earth);
    }
  }

  setupTerrain(mesh, body) {
    const g = new THREE.BufferGeometry();
    const p = mesh.positions, n = mesh.normals;
    const pos = new Float32Array(p.length), nor = new Float32Array(n.length), col = new Float32Array(p.length), uv = new Float32Array((p.length / 3) * 2);
    const base = body === 'mars' ? [0.50, 0.27, 0.15] : (body === 'titan' ? [0.36, 0.26, 0.14] : [0.42, 0.41, 0.40]);
    let hmin = Infinity, hmax = -Infinity;
    for (let i = 0; i < p.length; i += 3) { hmin = Math.min(hmin, p[i + 2]); hmax = Math.max(hmax, p[i + 2]); }
    for (let i = 0, j = 0; i < p.length; i += 3, j += 2) {
      pos[i] = p[i]; pos[i + 1] = p[i + 2]; pos[i + 2] = -p[i + 1];
      nor[i] = n[i]; nor[i + 1] = n[i + 2]; nor[i + 2] = -n[i + 1];
      const slope = 1 - n[i + 2];                       // 0 düz .. 1 dik
      const ht = (p[i + 2] - hmin) / Math.max(1, hmax - hmin);
      const k = 0.82 + 0.35 * ht + 0.5 * slope;        // dik yamaçlar ve tepeler daha açık (taze malzeme)
      col[i] = base[0] * k; col[i + 1] = base[1] * k; col[i + 2] = base[2] * k;
      uv[j] = p[i] / 6; uv[j + 1] = p[i + 1] / 6;
    }
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
    g.setIndex(new THREE.BufferAttribute(mesh.indices, 1));
    // regolit ayrıntı dokusu: çakıl ve küçük çukurlar (prosedürel)
    const detail = canvasTexture(512, (c, sz) => {
      const im = c.createImageData(sz, sz);
      for (let i = 0; i < sz * sz; i++) { const v = 200 + Math.random() * 55; im.data[i * 4] = v; im.data[i * 4 + 1] = v; im.data[i * 4 + 2] = v; im.data[i * 4 + 3] = 255; }
      c.putImageData(im, 0, 0);
      for (let i = 0; i < 260; i++) {
        const x = Math.random() * sz, y = Math.random() * sz, r = 1 + Math.random() * 6;
        c.fillStyle = `rgba(0,0,0,${0.1 + Math.random() * 0.25})`; c.beginPath(); c.arc(x, y, r, 0, Math.PI * 2); c.fill();
        c.fillStyle = `rgba(255,255,255,${0.08 + Math.random() * 0.15})`; c.beginPath(); c.arc(x - r * 0.3, y - r * 0.3, r * 0.6, 0, Math.PI * 2); c.fill();
      }
    });
    detail.wrapS = detail.wrapT = THREE.RepeatWrapping;
    const mat = new THREE.MeshStandardMaterial({ vertexColors: true, map: detail, roughness: 0.97, metalness: 0.0 });
    this.terrain = new THREE.Mesh(g, mat);
    this.terrain.receiveShadow = true;
    this.scene.add(this.terrain);
    // uzak zemin: yüksek irtifadan (yörünge 15 km) bakınca ufka kadar uzanan düzlem. Ayrıntılı arazi yalnız
    // koloni çevresindeki 1,6 km'lik yamadır; dışarısı aynı tonda tekrar eden krater dokusu.
    const farTex = canvasTexture(1024, (c, sz) => {
      // düşük kontrastlı regolit: değer gürültüsü + seyrek küçük kraterler (halka deseni tekrar ederken göze batmasın)
      const im = c.createImageData(sz, sz);
      const cell = 64, grid = [];
      for (let i = 0; i < (sz / cell + 1) ** 2; i++) grid.push(Math.random());
      const at = (x, y) => grid[(y % (sz / cell)) * (sz / cell + 1) + (x % (sz / cell))];
      for (let y = 0; y < sz; y++) for (let x = 0; x < sz; x++) {
        const gx = x / cell, gy = y / cell, ix = gx | 0, iy = gy | 0, fx = gx - ix, fy = gy - iy;
        const u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy);
        const n = at(ix, iy) * (1 - u) * (1 - v) + at(ix + 1, iy) * u * (1 - v) + at(ix, iy + 1) * (1 - u) * v + at(ix + 1, iy + 1) * u * v;
        const k = 200 + n * 30 + Math.random() * 14, i = (y * sz + x) * 4;
        im.data[i] = im.data[i + 1] = im.data[i + 2] = k; im.data[i + 3] = 255;
      }
      c.putImageData(im, 0, 0);
      for (let i = 0; i < 160; i++) {
        const x = Math.random() * sz, y = Math.random() * sz, r = 3 + Math.pow(Math.random(), 3) * 28;
        c.fillStyle = 'rgba(0,0,0,0.13)'; c.beginPath(); c.arc(x + r * 0.15, y + r * 0.15, r, 0, Math.PI * 2); c.fill();
        c.strokeStyle = 'rgba(255,255,255,0.12)'; c.lineWidth = Math.max(1, r * 0.15); c.beginPath(); c.arc(x, y, r, Math.PI * 0.9, Math.PI * 1.9); c.stroke();
      }
    });
    farTex.wrapS = farTex.wrapT = THREE.RepeatWrapping;
    farTex.repeat.set(1500, 1500);
    const far = new THREE.Mesh(new THREE.CircleGeometry(600000, 64), new THREE.MeshStandardMaterial({ color: new THREE.Color(base[0] * 1.05, base[1] * 1.05, base[2] * 1.05), map: farTex, roughness: 1 }));
    far.rotation.x = -Math.PI / 2;
    far.position.y = hmin - 0.5;
    this.scene.add(far);
  }

  setupRocks(core, body) {
    if (!this.quality.rocks) return;
    const geo = new THREE.DodecahedronGeometry(1, 0);
    const mat = new THREE.MeshStandardMaterial({ color: body === 'mars' ? 0x6e3a22 : (body === 'titan' ? 0x5a4020 : 0x5c5b58), roughness: 0.95, flatShading: true });
    const count = this.quality.rocks;
    const inst = new THREE.InstancedMesh(geo, mat, count);
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), sc = new THREE.Vector3();
    let k = 0;
    for (let i = 0; i < count * 3 && k < count; i++) {
      const x = (Math.random() - 0.5) * 1500, y = (Math.random() - 0.5) * 1500;
      if (Math.hypot(x, y) < 110 || Math.hypot(x - 130, y) < 45) continue;   // koloni ve iniş alanı temiz
      const s = Math.pow(Math.random(), 3) * 2.2 + 0.15;
      q.setFromEuler(new THREE.Euler(Math.random() * 3, Math.random() * 3, Math.random() * 3));
      sc.set(s, s * (0.5 + Math.random() * 0.5), s);
      m.compose(T(x, y, core.height(x, y) + s * 0.2), q, sc);
      inst.setMatrixAt(k++, m);
    }
    inst.count = k;
    inst.castShadow = true;
    inst.receiveShadow = true;
    this.scene.add(inst);
  }

  // ---------------------------------------------------------------- koloni
  setColony(buildings) {
    this.colony.clear();
    this.buildings.clear();
    this.targets = this.targets.filter((t) => t.type === 'hatch' || t.type === 'npc');
    if (!buildings || !buildings.length) return;
    this.buildingData = buildings;
    const wallMat = new THREE.MeshStandardMaterial({ color: 0x9aa0a8, roughness: 0.65, metalness: 0.15 });
    const floorMat = new THREE.MeshStandardMaterial({ color: 0x3a3d44, roughness: 0.85 });
    const pathMat = new THREE.MeshStandardMaterial({ color: 0x4a4b4e, roughness: 0.95 });
    const glassMat = new THREE.MeshPhysicalMaterial({ color: 0xbfd8e8, roughness: 0.08, metalness: 0, transparent: true, opacity: 0.22, depthWrite: false });
    const regolithMat = new THREE.MeshStandardMaterial({ color: this.body === 'mars' ? 0x7a4a30 : 0x5f5d59, roughness: 1 });
    const windowMat = new THREE.MeshBasicMaterial({ color: 0xffd49a });
    const consoleMat = new THREE.MeshStandardMaterial({ color: 0x14202e, emissive: 0x1a8fb0, emissiveIntensity: 0.6, roughness: 0.4 });
    const underground = this.body === 'moon';
    // meydan
    const plaza = new THREE.Mesh(new THREE.CylinderGeometry(22, 22, 0.15, 48), pathMat);
    plaza.position.copy(T(0, 0, this.core.height(0, 0) + 0.06));
    plaza.receiveShadow = true;
    this.colony.add(plaza);
    for (const b of buildings) {
      const grp = new THREE.Group();
      const z0 = b.z;
      grp.position.copy(T(b.x, b.y, z0));
      this.colony.add(grp);
      this.buildings.set(b.id, { data: b, group: grp });
      if (b.district === 0) { // iniş alanı
        const pad = new THREE.Mesh(new THREE.CylinderGeometry(b.w / 2, b.w / 2 + 1, 0.4, 64), new THREE.MeshStandardMaterial({ color: 0x6a6964, roughness: 0.9 }));
        pad.position.y = 0.2; pad.receiveShadow = true; grp.add(pad);
        const ring = new THREE.Mesh(new THREE.RingGeometry(b.w * 0.33, b.w * 0.36, 64), new THREE.MeshBasicMaterial({ color: 0xffb347, side: THREE.DoubleSide }));
        ring.rotation.x = -Math.PI / 2; ring.position.y = 0.42; grp.add(ring);
        const lbl = labelSprite('İNİŞ ALANI', { color: '#ffd08a', border: 'rgba(255,179,71,0.5)', scale: 1.4 });
        lbl.position.set(0, 6, 0); grp.add(lbl);
        continue;
      }
      // kapıya giden yol
      const door = T(b.dx, b.dy, 0), center = T(b.x, b.y, 0);
      const len = Math.hypot(b.dx, b.dy) - 22;
      if (len > 0) {
        const path = new THREE.Mesh(new THREE.BoxGeometry(len, 0.1, 2.6), pathMat);
        const mid = T(b.dx * (0.5 + 11 / Math.hypot(b.dx, b.dy)) * 1, b.dy * (0.5 + 11 / Math.hypot(b.dx, b.dy)), 0);
        path.position.copy(T((b.dx * (22 + len / 2)) / Math.hypot(b.dx, b.dy), (b.dy * (22 + len / 2)) / Math.hypot(b.dx, b.dy), this.core.height(b.dx * 0.5, b.dy * 0.5) + 0.06));
        path.rotation.y = Math.atan2(-(b.dy), b.dx) * -1;
        path.rotation.y = -Math.atan2(-b.dy, b.dx) + 0; // Three Y dönüşü
        path.rotation.y = Math.atan2(b.dy, b.dx);
        path.receiveShadow = true;
        this.colony.add(path);
        void mid;
      }
      if (!b.built) {
        // arsa: köşe kazıkları + etiket
        for (let k = 0; k < 4; k++) {
          const st = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 1.2, 6), new THREE.MeshStandardMaterial({ color: 0xffa040, emissive: 0x552000 }));
          st.position.set((k & 1 ? 1 : -1) * b.w / 2, 0.6, (k & 2 ? 1 : -1) * b.d / 2);
          grp.add(st);
        }
        const lbl = labelSprite(b.name + '\n(arsa)', { color: '#ffcf9a', border: 'rgba(255,160,64,0.4)', scale: 0.8 });
        lbl.position.set(0, 3, 0); grp.add(lbl);
        this.buildings.get(b.id).site = grp;
        continue;
      }
      const H = b.h, W = b.w, D = b.d, t = 0.3;
      // yerel eksenler: Three X = plan x, Three Z = -plan y; kapı yönü (meydana doğru)
      const toPlaza = new THREE.Vector2(-b.x, -b.y).normalize();
      const doorOnX = Math.abs(toPlaza.x) > Math.abs(toPlaza.y);
      const floor = new THREE.Mesh(new THREE.BoxGeometry(W, 0.2, D), floorMat);
      floor.position.y = 0.1; floor.receiveShadow = true; grp.add(floor);
      const wall = (cx, cz, sx, sz) => {
        const m = new THREE.Mesh(new THREE.BoxGeometry(sx, H, sz), wallMat);
        m.position.set(cx, H / 2, cz); m.castShadow = true; m.receiveShadow = true; grp.add(m);
      };
      const gap = 2.6;
      for (const side of [0, 1, 2, 3]) {
        const alongX = side < 2, sign = side % 2 === 0 ? 1 : -1;
        const span = alongX ? D : W;
        const cx = alongX ? sign * W / 2 : 0, cz = alongX ? 0 : -sign * D / 2;   // plan y -> -z
        const hasDoor = doorOnX ? (alongX && Math.sign(toPlaza.x) === sign) : (!alongX && Math.sign(toPlaza.y) === sign);
        if (!hasDoor) {
          alongX ? wall(cx, cz, t, span) : wall(cx, cz, span, t);
          // pencere bantları yalnız dış yüzde (sıcak iç ışık); iç hacmin içinden geçmez
          for (let f = 0; f < b.floors; f++) {
            const wy = (f + 0.6) * (H / b.floors);
            const strip = new THREE.Mesh(new THREE.PlaneGeometry(span * 0.7, 0.32), windowMat);
            const out = t / 2 + 0.02;
            if (alongX) { strip.position.set(cx + sign * out, wy, cz); strip.rotation.y = sign * Math.PI / 2; }
            else { strip.position.set(cx, wy, cz - sign * out); strip.rotation.y = sign > 0 ? Math.PI : 0; }
            grp.add(strip);
          }
          continue;
        }
        const seg = (span - gap) / 2;
        for (const k of [-1, 1]) {
          const off = k * (gap / 2 + seg / 2);
          alongX ? wall(cx, cz + off, t, seg) : wall(cx + off, cz, seg, t);
        }
        const lintel = new THREE.Mesh(new THREE.BoxGeometry(alongX ? t : gap, H * 0.3, alongX ? gap : t), wallMat);
        lintel.position.set(cx, H * 0.85, cz); grp.add(lintel);
        // kapı ışığı
        const dl = new THREE.Mesh(new THREE.BoxGeometry(alongX ? 0.05 : gap, 0.08, alongX ? gap : 0.05), new THREE.MeshBasicMaterial({ color: 0x3ee6ff }));
        dl.position.set(cx + (alongX ? sign * 0.2 : 0), H * 0.69, cz + (alongX ? 0 : -sign * 0.2)); grp.add(dl);
      }
      // ara kat
      const floorH = H / b.floors;
      for (let f = 1; f < b.floors; f++) {
        const slab = new THREE.Mesh(new THREE.BoxGeometry(W * 0.78, 0.18, D * 0.95), floorMat);
        slab.position.set(W * 0.1, f * floorH, 0); slab.receiveShadow = true; grp.add(slab);
      }
      // çatı: yer altında regolit örtüsü (radyasyon kalkanı), yüzeyde kubbe
      if (underground && b.pressurized) {
        const mound = new THREE.Mesh(new THREE.SphereGeometry(1, 28, 14, 0, Math.PI * 2, 0, Math.PI / 2), regolithMat);
        // regolit örtüsü duvarların üstüne oturur (kapı önünde kamerayı içine almasın)
        mound.scale.set(W * 0.56, H * 0.75, D * 0.56); mound.position.y = H; mound.castShadow = true; mound.receiveShadow = true; grp.add(mound);
        const roof = new THREE.Mesh(new THREE.BoxGeometry(W, 0.25, D), wallMat); roof.position.y = H; grp.add(roof);
      } else {
        const dome = new THREE.Mesh(new THREE.SphereGeometry(1, 36, 18, 0, Math.PI * 2, 0, Math.PI / 2), glassMat);
        dome.scale.set(W * 0.62, H * 0.7, D * 0.62); dome.position.y = H; grp.add(dome);
        const roof = new THREE.Mesh(new THREE.BoxGeometry(W, 0.2, D), wallMat);
        roof.position.y = H; grp.add(roof);
      }
      // nokta ışığı yok: 18 bina x ışık her pikselde hesaplanır ve tablette kare hızını çökertir.
      // İç aydınlık pencere bantlarının ışıyan (emissive) malzemesiyle verilir.
      const lbl = labelSprite(b.name, { scale: 1.6 });
      lbl.position.set(0, H + (underground ? H * 0.9 : H * 0.8) + 1.2, 0); grp.add(lbl);
      // etkileşim: kapı
      this.targets.push({ type: 'door', id: b.id, label: b.name, pos: T(b.dx, b.dy, z0 + 1.2), radius: 3.5 });
      // iç konsollar (katlarına göre)
      let n = 0;
      for (const room of b.rooms) {
        for (const it of room.items) {
          const a = (n++ / 6) * Math.PI * 2;
          const lx = Math.cos(a) * W * 0.28, ly = Math.sin(a) * D * 0.28;
          const cy = room.floor * floorH + 0.7;
          const box = new THREE.Mesh(new THREE.BoxGeometry(0.9, 1.1, 0.5), consoleMat);
          box.position.set(lx, cy, -ly); grp.add(box);
          const scr = new THREE.Mesh(new THREE.PlaneGeometry(0.75, 0.45), new THREE.MeshBasicMaterial({ color: 0x3ee6ff, transparent: true, opacity: 0.75 }));
          scr.position.set(lx, cy + 0.35, -ly + 0.26); grp.add(scr);
          this.targets.push({ type: 'console', id: it.id, building: b.id, floor: room.floor, label: it.name, pos: T(b.x + lx, b.y + ly, z0 + cy), radius: 2.2 });
        }
      }
      if (b.floors > 1) {
        const lp = T(b.x - W * 0.4, b.y + D * 0.35, z0);
        const shaft = new THREE.Mesh(new THREE.BoxGeometry(1.4, H, 1.4), new THREE.MeshStandardMaterial({ color: b.elevator ? 0x2b6b46 : 0x6b5a2b, transparent: true, opacity: 0.6 }));
        shaft.position.set(-W * 0.4, H / 2, -D * 0.35); grp.add(shaft);
        this.targets.push({ type: 'floor', id: b.id, label: b.elevator ? 'Asansör' : 'Merdiven', pos: lp.clone().setY(z0 + 1.2), radius: 2.4, elevator: b.elevator, floors: b.floors });
      }
    }
  }

  updateConstruction(state) {
    // inşaat sahalarında yükselen iskele + ilerleme etiketi
    if (!this.buildingData) return;
    const active = (state.construction || []).find((p) => p.state === 'İnşa ediliyor');
    for (const [id, b] of this.buildings) {
      if (b.data.built || b.data.district === 0) continue;
      const isSite = active && !active.reinforce && b.data.district === active.site;
      if (isSite && (!b.scaffold || b.progressShown !== Math.round(active.progress * 20))) {
        if (b.scaffold) b.group.remove(b.scaffold);
        const s = new THREE.Group();
        const h = Math.max(0.3, b.data.h * active.progress);
        const body = new THREE.Mesh(new THREE.BoxGeometry(b.data.w * 0.9, h, b.data.d * 0.9), new THREE.MeshStandardMaterial({ color: 0x8b8e94, roughness: 0.8 }));
        body.position.y = h / 2; body.castShadow = true; s.add(body);
        for (let k = 0; k < 8; k++) {
          const a = k / 8 * Math.PI * 2;
          const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, b.data.h + 1, 6), new THREE.MeshStandardMaterial({ color: 0xd6a020, metalness: 0.6, roughness: 0.4 }));
          pole.position.set(Math.cos(a) * b.data.w * 0.55, (b.data.h + 1) / 2, Math.sin(a) * b.data.d * 0.55); s.add(pole);
        }
        const lbl = labelSprite(`${active.module} — İNŞAAT %${Math.round(active.progress * 100)}`, { color: '#ffd08a', border: 'rgba(255,179,71,0.6)' });
        lbl.position.y = b.data.h + 3; s.add(lbl);
        b.group.add(s);
        b.scaffold = s;
        b.progressShown = Math.round(active.progress * 20);
      } else if (!isSite && b.scaffold) {
        b.group.remove(b.scaffold);
        b.scaffold = null;
      }
    }
  }

  // ---------------------------------------------------------------- araç
  setupLander() {
    const g = new THREE.Group();
    const foil = new THREE.MeshStandardMaterial({ color: 0xb08a2e, metalness: 0.9, roughness: 0.32 });
    const white = new THREE.MeshStandardMaterial({ color: 0xc8cbd0, roughness: 0.5, metalness: 0.2 });
    const dark = new THREE.MeshStandardMaterial({ color: 0x1a1a1e, metalness: 0.85, roughness: 0.35 });
    const tank = new THREE.Mesh(new THREE.CylinderGeometry(2.25, 2.4, 6, 24), foil); tank.position.y = 4.2; g.add(tank);
    const cabin = new THREE.Mesh(new THREE.CylinderGeometry(1.8, 2.1, 2.6, 24), white); cabin.position.y = 8.5; g.add(cabin);
    const nose = new THREE.Mesh(new THREE.ConeGeometry(1.8, 1.6, 24), white); nose.position.y = 10.6; g.add(nose);
    // pencereler
    for (let i = 0; i < 4; i++) {
      const w = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.5), new THREE.MeshBasicMaterial({ color: 0x8fd8ff, transparent: true, opacity: 0.8 }));
      const a = i / 4 * Math.PI * 2 + 0.4;
      w.position.set(Math.cos(a) * 1.97, 9.0, Math.sin(a) * 1.97); w.lookAt(w.position.clone().multiplyScalar(2).setY(9)); g.add(w);
    }
    for (const a of [0.6, 2.2, 3.8, 5.4]) {
      const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 3.4, 8), white);
      leg.position.set(Math.cos(a) * 2.7, 1.6, Math.sin(a) * 2.7);
      leg.rotation.z = Math.cos(a) * 0.45; leg.rotation.x = -Math.sin(a) * 0.45; g.add(leg);
      const foot = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.55, 0.12, 16), white);
      foot.position.set(Math.cos(a) * 3.5, 0.06, Math.sin(a) * 3.5); g.add(foot);
    }
    for (const x of [-0.8, 0.8]) {
      const bell = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.75, 1.3, 20, 1, true), dark); bell.position.set(x, 0.9, 0); g.add(bell);
    }
    for (const s of [-1, 1]) {
      const p = new THREE.Mesh(new THREE.BoxGeometry(0.05, 1.6, 3.2), new THREE.MeshStandardMaterial({ color: 0x142048, metalness: 0.5, roughness: 0.3, emissive: 0x050a20 }));
      p.position.set(s * 4.6, 6, 0); g.add(p);
    }
    g.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    // alev: iki katmanlı ek renkli koni + ışık
    const flameMat = new THREE.MeshBasicMaterial({ color: 0xffb066, transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false });
    const coreMat = new THREE.MeshBasicMaterial({ color: 0xbfe6ff, transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending, depthWrite: false });
    this.flame = new THREE.Group();
    const outer = new THREE.Mesh(new THREE.ConeGeometry(1.1, 7, 20, 1, true), flameMat); outer.rotation.x = Math.PI; outer.position.y = -3.3;
    const inner = new THREE.Mesh(new THREE.ConeGeometry(0.5, 3.5, 16, 1, true), coreMat); inner.rotation.x = Math.PI; inner.position.y = -1.6;
    this.flame.add(outer, inner);
    this.flame.visible = false;
    g.add(this.flame);
    this.flameLight = new THREE.PointLight(0xffa860, 0, 140, 1.6);
    this.flameLight.position.y = -1;
    g.add(this.flameLight);
    this.lander = g;
    this.scene.add(g);
    // iç mekân aydınlatması: bina içindeyken kamerayı izleyen tek ışık (bina başına ışık yerine)
    this.indoor = new THREE.PointLight(0xffe2c0, 0, 22, 1.4);
    this.scene.add(this.indoor);
    this.targets.push({ type: 'hatch', id: 'hatch', label: 'Araç kapağı', pos: new THREE.Vector3(), radius: 6 });
  }

  setupDust() {
    // inişte yükselen toz halkası + fırtına partikülleri
    const n = 600;
    const geo = new THREE.BufferGeometry();
    this.dustPos = new Float32Array(n * 3);
    this.dustVel = new Float32Array(n * 3);
    geo.setAttribute('position', new THREE.BufferAttribute(this.dustPos, 3));
    const col = this.body === 'mars' ? 0xc08a60 : (this.body === 'titan' ? 0xb08040 : 0x9a9894);
    this.dust = new THREE.Points(geo, new THREE.PointsMaterial({ color: col, size: 0.6, transparent: true, opacity: 0.55, depthWrite: false }));
    this.dust.frustumCulled = false;
    this.scene.add(this.dust);
    this.dustLife = new Float32Array(n);
  }

  // ---------------------------------------------------------------- canlı güncelleme
  syncNpcs(npcs, nearIds) {
    const alive = new Set();
    for (const n of npcs) {
      alive.add(n.id);
      let o = this.npcs.get(n.id);
      if (!o) {
        const g = new THREE.Group();
        const mat = new THREE.MeshStandardMaterial({ color: JOB_COLORS[n.job_id] || 0x888888, roughness: 0.6 });
        const bodyM = new THREE.Mesh(new THREE.CapsuleGeometry(0.28, 0.95, 4, 12), mat); bodyM.position.y = 0.85; bodyM.castShadow = true;
        const head = new THREE.Mesh(new THREE.SphereGeometry(0.2, 16, 12), new THREE.MeshStandardMaterial({ color: 0xc8a080, roughness: 0.7 })); head.position.y = 1.62;
        const visor = new THREE.Mesh(new THREE.SphereGeometry(0.205, 16, 8, -0.9, 1.8, 1.2, 0.7), new THREE.MeshStandardMaterial({ color: 0x0a1a2a, metalness: 0.9, roughness: 0.1 })); visor.position.y = 1.62;
        g.add(bodyM, head, visor);
        this.scene.add(g);
        o = { group: g, tx: n.x, ty: n.y, label: null, text: '' };
        g.position.copy(T(n.x, n.y, this.core.height(n.x, n.y)));
        this.npcs.set(n.id, o);
        this.targets.push({ type: 'npc', id: n.id, label: n.name, pos: g.position, radius: 2.6 });
      }
      o.tx = n.x; o.ty = n.y; o.data = n;
      const near = nearIds && nearIds.includes(n.id);
      const txt = near || n.lod === 0 ? `${n.name} · ${n.job}\n${n.intent}` : n.name;
      if (txt !== o.text) {
        if (o.label) o.group.remove(o.label);
        o.label = labelSprite(txt, { scale: 0.3, size: 34 });
        o.label.position.y = 2.25;
        o.group.add(o.label);
        o.text = txt;
      }
    }
    for (const [id, o] of this.npcs) if (!alive.has(id)) { this.scene.remove(o.group); this.npcs.delete(id); }
    this.targets = this.targets.filter((t) => t.type !== 'npc' || alive.has(t.id));
  }

  landerPose(state) {
    // iniş alanı + kalan menzil (çekirdekteki gerçek konum güdümü) + irtifa
    const pad = (this.buildingData || []).find((b) => b.district === 0) || { x: 130, y: 0, z: 0 };
    const c = state.craft;
    const rem = c.remaining || 0;
    const x = pad.x - rem, y = pad.y;
    const ground = this.core.height(Math.max(-790, Math.min(790, x)), y);
    return { pos: T(x, y, Math.max(ground, (pad.z || 0) + 0.4) + c.alt), x, y, ground };
  }

  update(state, dt, camera) {
    const t = this.clock.elapsedTime;
    // araç
    const lp = this.landerPose(state);
    this.lander.position.copy(lp.pos);
    const pitch = state.craft.phase_id === 1 ? Math.atan2(-state.craft.vh, 600) * 0.4 : 0;
    this.lander.rotation.z = THREE.MathUtils.lerp(this.lander.rotation.z, pitch, Math.min(1, dt * 2));
    const burning = state.craft.engines_on && state.craft.fuel > 0 && state.craft.phase_id !== 0;
    this.flame.visible = burning;
    if (burning) {
      const f = 0.85 + Math.sin(t * 40) * 0.08 + Math.random() * 0.07;
      this.flame.scale.set(f, 0.7 + state.craft.throttle * 0.6 * f, f);
    }
    this.flameLight.intensity = burning ? 260 * (0.4 + state.craft.throttle) : 0;
    const hatch = this.targets.find((x) => x.type === 'hatch');
    if (hatch) hatch.pos.copy(this.lander.position).add(new THREE.Vector3(2.6, 1.2, 0));
    // iniş tozu: motor yere yakınsa
    const nearGround = burning && state.craft.alt < 40;
    const dp = this.dustPos, dv = this.dustVel;
    for (let i = 0; i < this.dustLife.length; i++) {
      if (this.dustLife[i] <= 0 && nearGround && Math.random() < 0.25) {
        const a = Math.random() * Math.PI * 2;
        dp[i * 3] = this.lander.position.x; dp[i * 3 + 1] = lp.ground + 0.3; dp[i * 3 + 2] = this.lander.position.z;
        const sp = (12 + Math.random() * 18) * (1 - state.craft.alt / 45);
        dv[i * 3] = Math.cos(a) * sp; dv[i * 3 + 1] = Math.random() * 2; dv[i * 3 + 2] = Math.sin(a) * sp;
        this.dustLife[i] = 1.5 + Math.random();
      }
      if (this.dustLife[i] > 0) {
        this.dustLife[i] -= dt;
        const drag = this.body === 'moon' ? 0 : 1.4;   // vakumda balistik (Apollo videolarındaki gibi), atmosferde yavaşlar
        for (let k = 0; k < 3; k++) { dv[i * 3 + k] *= 1 - drag * dt; dp[i * 3 + k] += dv[i * 3 + k] * dt; }
        dv[i * 3 + 1] -= state.gravity * dt;
        if (this.dustLife[i] <= 0) dp[i * 3 + 1] = -9999;
      } else dp[i * 3 + 1] = -9999;
    }
    this.dust.geometry.attributes.position.needsUpdate = true;
    // NPC'ler: çekirdek konumuna yumuşak yaklaş, yürürken salın
    for (const [, o] of this.npcs) {
      const target = T(o.tx, o.ty, this.core.height(o.tx, o.ty));
      const d = o.group.position.distanceTo(target);
      if (d > 0.05) {
        const dir = target.clone().sub(o.group.position);
        o.group.rotation.y = Math.atan2(dir.x, dir.z);
        o.group.position.lerp(target, Math.min(1, dt * 3));
        o.group.children[0].position.y = 0.85 + Math.abs(Math.sin(t * 7 + o.data.id)) * 0.06;
      }
    }
    // gölge kamerası oyuncuyu izler
    if (this.sun.castShadow) {
      this.sun.target.position.copy(camera.position);
      this.sun.position.copy(camera.position).add(this.sunDir.clone().multiplyScalar(400));
    }
    this.skyGroup.position.copy(camera.position);
    const inside = state.player.mode_id === 3;
    this.indoor.intensity = inside ? 60 : 0;
    if (inside) this.indoor.position.copy(camera.position).add(new THREE.Vector3(0, 0.8, 0));
    // hava: toz fırtınası sisi koyulaştırır
    const vis = Math.min(1, ...(state.weather || []).map((w) => w.visibility), 1);
    if (this.scene.fog) {
      const base = this.body === 'mars' ? 0.0016 : 0.006;
      this.scene.fog.density = THREE.MathUtils.lerp(this.scene.fog.density, base + (1 - vis) * 0.02, Math.min(1, dt));
      this.skyMat.uniforms.dust.value = 1 - vis;
    }
  }

  render() {
    const t0 = performance.now();
    this.renderer.render(this.scene, this.camera);
    // uyarlanabilir çözünürlük: kare süresi yüksekse piksel oranını düşür, rahatsa yükselt
    this.frameTimes.push(performance.now() - t0);
    if (this.frameTimes.length >= 90) {
      const avg = this.frameTimes.reduce((a, b) => a + b, 0) / this.frameTimes.length;
      this.frameTimes.length = 0;
      const maxPr = Math.min(window.devicePixelRatio || 1, this.quality.maxPixelRatio);
      if (this.lastFrameMs > 22 && this.pixelRatio > 0.6) this.pixelRatio = Math.max(0.6, this.pixelRatio - 0.15);
      else if (this.lastFrameMs < 12 && this.pixelRatio < maxPr) this.pixelRatio = Math.min(maxPr, this.pixelRatio + 0.1);
      this.renderer.setPixelRatio(this.pixelRatio);
      this.resize();
      void avg;
    }
  }
}
