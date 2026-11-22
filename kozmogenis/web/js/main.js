// KOZMOGENİS — tarayıcı girişi: yükleme sekansı, menü, kontroller ve oyun döngüsü.
// Unreal'daki AKozmogenisGameMode + AKozmogenisPlayerController karşılığı.
import { Core } from './core.js';
import { SpaceBackdrop, FACTS } from './loading.js';

const $ = (id) => document.getElementById(id);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const touch = matchMedia('(pointer: coarse)').matches || 'ontouchstart' in window;
if (touch) document.body.classList.add('touch');

const QUALITY = {
  low: { antialias: false, shadows: 0, maxPixelRatio: 1, rocks: 250 },
  medium: { antialias: true, shadows: 1024, maxPixelRatio: 1.5, rocks: 900 },
  high: { antialias: true, shadows: 2048, maxPixelRatio: 2, rocks: 2200 },
};
const store = {
  get(k, d) { try { const v = localStorage.getItem('kozmo.' + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem('kozmo.' + k, JSON.stringify(v)); return true; } catch { return false; } },
};

// ===================================================================== YÜKLEME
const STAGES = [
  ['ui', 'Arayüz ve yazı tipleri', 0.06],
  ['wasm', 'KozmoCore indiriliyor (WebAssembly)', 0.5],
  ['init', 'C++ çekirdeği başlatılıyor', 0.08],
  ['gl', '3B motor (Three.js / WebGL)', 0.16],
  ['self', 'Fizik öz-sınaması: Ay inişi başlangıcı', 0.12],
  ['nova', 'NOVA çevrimdışı bilgi tabanı', 0.08],
];
const stageEl = {};
$('loadStages').innerHTML = STAGES.map(([k, n]) => `<div class="stage" id="st_${k}">${n}</div>`).join('');
STAGES.forEach(([k]) => (stageEl[k] = $('st_' + k)));
let progress = 0, shown = 0;
const backdrop = new SpaceBackdrop($('loadCanvas'), { planet: 'earth' });
function setStage(k, frac, label) {
  let p = 0;
  for (const [key, , w] of STAGES) {
    if (key === k) { p += w * frac; break; }
    p += w;
  }
  progress = Math.max(progress, p);
  STAGES.forEach(([key]) => {
    const idx = STAGES.findIndex((s) => s[0] === key), cur = STAGES.findIndex((s) => s[0] === k);
    stageEl[key].className = 'stage' + (idx < cur || (idx === cur && frac >= 1) ? ' done' : idx === cur ? ' run' : '');
  });
  if (label && label !== lastLabel) {
    lastLabel = label;
    $('loadLabel').textContent = label;
    if (!/\d+%$/.test(label) || frac >= 1) logLine(label);
  }
}
let lastLabel = '';
const t0 = performance.now();
function logLine(text) {
  const d = document.createElement('div');
  d.innerHTML = `<b>[${((performance.now() - t0) / 1000).toFixed(3)}]</b> ${text.replace(/[<>&]/g, '')}`;
  const log = $('loadLog');
  log.append(d);
  while (log.children.length > 14) log.firstChild.remove();
}
(function animateBar() {
  shown += (progress - shown) * 0.12;
  $('loadFill').style.width = (shown * 100).toFixed(1) + '%';
  $('loadGlow').style.left = (shown * 100).toFixed(1) + '%';
  $('loadPct').textContent = Math.round(shown * 100) + '%';
  backdrop.speed = 0.15 + shown * 2.2;
  if ($('loading').classList.contains('active')) requestAnimationFrame(animateBar);
})();
let factI = Math.floor(Math.random() * FACTS.length);
function showFact() {
  const [t, src] = FACTS[factI++ % FACTS.length];
  const el = $('loadFact');
  el.classList.remove('show');
  setTimeout(() => { el.innerHTML = `${t}<small>Kaynak: ${src}</small>`; el.classList.add('show'); }, 350);
}
showFact();
const factTimer = setInterval(showFact, 5200);

async function boot() {
  setStage('ui', 0, 'Arayüz hazırlanıyor…');
  await Promise.race([document.fonts?.ready, sleep(1500)]);
  setStage('ui', 1);
  const core = await Core.load((f) => setStage('wasm', f, `KozmoCore indiriliyor… ${Math.round(f * 100)}%`));
  setStage('wasm', 1, `kozmo.wasm alındı · ${(core.m.HEAPF32.byteLength / 1048576).toFixed(0)} MB yığın`);
  setStage('init', 0.5, 'C++ çekirdeği başlatılıyor…');
  await sleep(30);
  setStage('init', 1, core.version);
  setStage('gl', 0.2, 'WebGL bağlamı açılıyor…');
  const probe = document.createElement('canvas').getContext('webgl2');
  if (!probe) throw new Error('Bu tarayıcı WebGL2 desteklemiyor.');
  const [{ World }, { Hud }] = await Promise.all([import('./scene.js'), import('./hud.js')]);
  setStage('gl', 1, `WebGL2 · ${probe.getParameter(probe.VERSION)}`);
  setStage('self', 0.3, 'Öz-sınama: Ay seferi kuruluyor…');
  await sleep(20);
  const r = core.start('moon', true);
  const st = core.state();
  if (!r.ok || !st.ok || st.craft.alt < 10000) throw new Error('Çekirdek öz-sınaması başarısız: ' + (r.msg || st.msg));
  setStage('self', 1, `Öz-sınama tamam: ${(st.craft.alt / 1000).toFixed(1)} km irtifa, ${Math.round(st.craft.speed)} m/s, ${st.npcs.length} NPC`);
  setStage('nova', 0.5, 'NOVA hazırlanıyor…');
  const n = core.cmd({ op: 'nova', text: 'durum raporu' });
  if (!n.ok) throw new Error('NOVA yanıt vermedi');
  setStage('nova', 1, 'Hazır. Tüm sistemler nominal.');
  progress = 1;
  await sleep(600);
  return { core, World, Hud };
}

// ===================================================================== OYUN
class Game {
  constructor(core, World, Hud) {
    this.core = core;
    this.qualityName = store.get('quality', touch ? 'low' : 'medium');
    this.world = new World($('gl'), QUALITY[this.qualityName] || QUALITY.medium);
    this.hud = new Hud(this);
    this.yaw = 0; this.pitch = -0.05;
    this.view = 'chase';
    this.keys = new Set();
    this.scale = 1;
    this.paused = false;
    this.panelOpen = false;
    this.vz = 0; this.jumpZ = 0;
    this.lastPos = 0; this.lastState = 0;
    this.pos = { x: 0, y: 0 };
    this.coreSettings = store.get('settings', null);
    this.running = false;
    this.bindInput();
  }

  start(body, fromSave) {
    let r;
    if (fromSave) r = this.core.loadSave(fromSave);
    else r = this.core.start(body, true);
    if (!r.ok) { this.hud.toast(r.msg, 'err'); return false; }
    if (this.coreSettings) this.core.cmd({ op: 'settings', value: this.coreSettings });
    this.coreSettings = this.core.cmd({ op: 'settings' }).settings;
    this.buildingData = r.buildings || this.core.buildings();
    this.state = this.core.state();
    this.body = this.state.body;
    this.world.build(this.core, this.body, this.buildingData);
    this.pos = { x: this.state.player.x, y: this.state.player.y };
    this.yaw = this.state.player.mode_id >= 2 ? Math.PI / 2 : -Math.PI / 2;   // araçta iniş yönüne (+x), yürürken koloniye bak
    this.view = 'chase';
    this.hud.closeAll();
    this.hud.lastLog = 0;
    this.hud.actKey = '';
    this.dead = false;
    this.setScale(1);
    $('fade').classList.add('on');
    setTimeout(() => $('fade').classList.remove('on'), 60);
    if (!this.running) { this.running = true; this.last = performance.now(); requestAnimationFrame((t) => this.frame(t)); }
    this.hud.toast(fromSave ? r.msg : 'Sefer hazır: ' + this.state.env, 'ok');
    return true;
  }

  refresh() {
    const prevBuilt = this.buildingData.map((b) => b.built).join();
    this.state = this.core.state();
    if (this.state.buildings) this.buildingData = this.state.buildings;
    if (this.buildingData.map((b) => b.built).join() !== prevBuilt) this.world.setColony(this.buildingData);
  }

  cmd(c) {
    const r = this.core.cmd(c);
    this.hud.result(r);
    if (r.buildings) {
      // koloni kuruldu: arazi yeniden üretildi -> dünyayı baştan kur
      this.buildingData = r.buildings;
      this.world.build(this.core, this.body, this.buildingData);
    }
    const before = this.state?.player.mode_id;
    this.refresh();
    const after = this.state.player.mode_id;
    if (before !== after) this.onModeChange(before, after);
    this.hud.update(this.state);   // eylem çubuğu hemen yeni duruma geçsin
    return r;
  }

  onModeChange(before, after) {
    if (after === 2) {
      this.pos = { x: this.state.player.x, y: this.state.player.y };
      if (before === 1) { this.pos.x -= 7; this.yaw = Math.PI / 2; } // kapaktan merdivenle in
      if (before === 3) {
        const b = this.buildingData.find((x) => x.id === this.lastBuilding);
        if (b) { this.pos = { x: b.dx + Math.sign(-b.x || 1) * 2.5, y: b.dy + Math.sign(-b.y || 0) * 2.5 }; }
      }
      this.core.cmd({ op: 'pos', x: this.pos.x, y: this.pos.y });
    }
    if (after === 3) { this.lastBuilding = this.state.player.building; this.hud.openInterior(this.state); }
    if (after !== 3) this.hud.close('interior');
    $('fade').classList.add('on');
    setTimeout(() => $('fade').classList.remove('on'), 220);
  }

  setScale(s) {
    this.scale = s;
    document.querySelectorAll('#timebar button').forEach((b) => b.classList.toggle('on', +b.dataset.scale === s));
  }
  toggleView() { this.view = this.view === 'chase' ? 'cockpit' : 'chase'; }
  pause(on) {
    this.paused = on;
    if (on) { document.exitPointerLock?.(); $('pauseMenu').classList.add('open'); this.onPanel(true); }
    else { $('pauseMenu').classList.remove('open'); this.onPanel(this.hud.anyOpen()); }
  }
  onPanel(open) { this.panelOpen = open; if (open) document.exitPointerLock?.(); }

  interact() {
    const s = this.state, m = s.player.mode_id;
    if (m === 0) return this.cmd({ op: 'stand' });
    if (m === 1) return this.cmd({ op: 'sit' });
    if (m === 3) return this.hud.openInterior(s);
    const t = this.target;
    if (!t) return this.hud.toast('Yakında etkileşim yok', 'err');
    if (t.type === 'hatch') return this.cmd({ op: 'enter_craft' });
    if (t.type === 'door') return this.cmd({ op: 'enter', id: t.id });
    if (t.type === 'npc') {
      const npc = s.npcs.find((n) => n.id === t.id);
      return this.hud.openDialog(npc, this.core.cmd({ op: 'talk_start', id: t.id }));
    }
  }

  // ----------------------------------------------------------------- girdi
  bindInput() {
    const cv = $('gl');
    cv.addEventListener('click', () => { if (!touch && !this.panelOpen && this.running) cv.requestPointerLock?.(); });
    addEventListener('mousemove', (e) => {
      if (document.pointerLockElement !== cv) return;
      this.look(e.movementX, e.movementY, 0.0022);
    });
    addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
      const k = e.key.length === 1 ? e.key.toUpperCase() : e.key;
      if (k === 'Escape') {
        if (this.hud.anyOpen()) this.hud.closeAll(); else this.pause(!this.paused);
        this.paused = $('pauseMenu').classList.contains('open');
        return;
      }
      if (!this.running || this.paused) return;
      if (this.panelOpen && !['N', 'J', 'M'].includes(k)) return;
      this.keys.add(e.code);
      const s = this.state;
      if (k === 'N') return this.hud.toggle('novaPanel');
      if (k === 'J') return $('questPanel').classList.contains('open') ? this.hud.close('questPanel') : this.hud.openQuests();
      if (k === 'M') return $('mgmtPanel').classList.contains('open') ? this.hud.close('mgmtPanel') : this.hud.openMgmt();
      if (k === ' ' && s.player.mode_id === 2 && this.jumpZ <= 0.001) { this.vz = Math.min(3.2, 1.2 + 2.2 / Math.sqrt(s.gravity / 1.62)); return; }
      if (s.player.mode_id === 0 && /^[1-6]$/.test(k)) return this.cmd({ op: 'mode', mode: +k - 1 });
      if (k === 'E') return this.interact();
      if (k === 'V') return this.toggleView();
      this.hud.actionByKey(k);
    });
    addEventListener('keyup', (e) => this.keys.delete(e.code));
    addEventListener('blur', () => this.keys.clear());
    document.querySelectorAll('#timebar button').forEach((b) => (b.onclick = () => this.setScale(+b.dataset.scale)));
    // dokunmatik: sol yarı joystick, sağ yarı bakış
    this.stick = { x: 0, y: 0, id: null };
    const stickEl = $('stick'), knob = stickEl.querySelector('.knob');
    let lookId = null, lx = 0, ly = 0;
    cv.addEventListener('touchstart', (e) => {
      for (const t of e.changedTouches) {
        if (t.clientX < innerWidth * 0.4 && this.stick.id === null) {
          this.stick.id = t.identifier; this.stick.ox = t.clientX; this.stick.oy = t.clientY;
          stickEl.style.left = t.clientX - 60 + 'px'; stickEl.style.top = t.clientY - 60 + 'px'; stickEl.style.bottom = 'auto';
        } else if (lookId === null) { lookId = t.identifier; lx = t.clientX; ly = t.clientY; }
      }
      e.preventDefault();
    }, { passive: false });
    cv.addEventListener('touchmove', (e) => {
      for (const t of e.changedTouches) {
        if (t.identifier === this.stick.id) {
          let dx = t.clientX - this.stick.ox, dy = t.clientY - this.stick.oy;
          const L = Math.hypot(dx, dy), M = 50;
          if (L > M) { dx *= M / L; dy *= M / L; }
          this.stick.x = dx / M; this.stick.y = dy / M;
          knob.style.transform = `translate(${dx}px, ${dy}px)`;
        } else if (t.identifier === lookId) {
          this.look(t.clientX - lx, t.clientY - ly, 0.005);
          lx = t.clientX; ly = t.clientY;
        }
      }
      e.preventDefault();
    }, { passive: false });
    const end = (e) => {
      for (const t of e.changedTouches) {
        if (t.identifier === this.stick.id) { this.stick = { x: 0, y: 0, id: null }; knob.style.transform = ''; stickEl.removeAttribute('style'); }
        if (t.identifier === lookId) lookId = null;
      }
    };
    cv.addEventListener('touchend', end);
    cv.addEventListener('touchcancel', end);
  }

  look(dx, dy, k) {
    const sens = (this.coreSettings?.mouse ?? 1) * k;
    const inv = this.coreSettings?.invert_y ? -1 : 1;
    this.yaw -= dx * sens;
    this.pitch = Math.max(-1.45, Math.min(1.45, this.pitch - dy * sens * inv));
  }

  // ----------------------------------------------------------------- döngü
  frame(now) {
    requestAnimationFrame((t) => this.frame(t));
    const dt = Math.min(0.1, (now - this.last) / 1000);
    this.last = now;
    if (!this.state) return;
    const s = this.state;
    if (!this.paused && !this.dead) {
      // simülasyon: uçuşta en çok ×10 (çekirdek 0,1 s alt adımla integrasyon yapar)
      let scale = this.scale;
      if (s.craft.phase_id === 1 && scale > 10) { scale = 10; if (!this.capWarned) { this.hud.toast('Uçuşta zaman en çok ×10 hızlanır', 'err'); this.capWarned = true; } }
      let sim = dt * scale;
      while (sim > 0) { const step = Math.min(sim, 60); this.core.tick(step); sim -= step; }
      this.control(dt, s);
      if (now - this.lastState > 50) {
        this.lastState = now;
        const before = s.player.mode_id;
        this.refresh();
        if (this.state.player.mode_id !== before) this.onModeChange(before, this.state.player.mode_id);
        this.world.syncNpcs(this.state.npcs, this.state.near_npcs);
        this.world.updateConstruction(this.state);
        this.hud.update(this.state);
        this.checkDeath(this.state);
      }
    }
    this.camera(dt, this.state);
    this.world.update(this.state, dt, this.world.camera);
    this.world.render();
  }

  control(dt, s) {
    const k = this.keys, m = s.player.mode_id;
    const fwd = (k.has('KeyW') || k.has('ArrowUp') ? 1 : 0) - (k.has('KeyS') || k.has('ArrowDown') ? 1 : 0) - this.stick.y;
    const side = (k.has('KeyD') || k.has('ArrowRight') ? 1 : 0) - (k.has('KeyA') || k.has('ArrowLeft') ? 1 : 0) + this.stick.x;
    if (m === 0 && s.craft.phase_id === 1 && s.craft.mode === 'Manuel') {
      // manuel uçuş: W/S itki, A/D yunuslama
      const th = Math.max(0, Math.min(1, s.craft.throttle + fwd * dt * 0.5));
      if (Math.abs(th - s.craft.throttle) > 0.005) { this.core.cmd({ op: 'throttle', value: th }); s.craft.throttle = th; }
      if (side) { this.manPitch = Math.max(0, Math.min(90, (this.manPitch ?? 90) - side * dt * 25)); this.core.cmd({ op: 'pitch', value: this.manPitch }); }
    }
    if (m !== 2) { this.target = null; this.hud.prompt(m === 1 ? '<kbd>E</kbd> koltuğa otur' : ''); return; }
    // yürüyüş: düşük yerçekiminde adım uzar ama sınırlıdır
    const run = k.has('ShiftLeft') || k.has('ShiftRight');
    const speed = (run ? 3.2 : 1.6) * Math.min(1.3, 0.85 + 0.25 * (1.62 / Math.max(0.5, s.gravity)));
    const len = Math.hypot(fwd, side);
    if (len > 0.05) {
      // Three kamera: yaw=0 -> -Z (plan +y). İleri vektör plan düzleminde (-sin(yaw), cos(yaw)).
      const fx = -Math.sin(this.yaw), fy = Math.cos(this.yaw), rx = Math.cos(this.yaw), ry = Math.sin(this.yaw);
      let nx = this.pos.x + (fwd * fx + side * rx) / Math.max(1, len) * speed * dt;
      let ny = this.pos.y + (fwd * fy + side * ry) / Math.max(1, len) * speed * dt;
      [nx, ny] = this.collide(nx, ny);
      this.pos.x = Math.max(-780, Math.min(780, nx));
      this.pos.y = Math.max(-780, Math.min(780, ny));
      this.bob = (this.bob || 0) + dt * speed * 3.2;
    }
    // zıplama
    if (this.vz || this.jumpZ > 0) {
      this.jumpZ += this.vz * dt;
      this.vz -= s.gravity * dt;
      if (this.jumpZ <= 0) { this.jumpZ = 0; this.vz = 0; }
    }
    const t = performance.now();
    if (t - this.lastPos > 100) { this.lastPos = t; this.core.cmd({ op: 'pos', x: this.pos.x, y: this.pos.y }); }
    // en yakın etkileşim hedefi
    let best = null, bd = Infinity;
    const px = this.pos.x, py = this.pos.y;
    for (const tg of this.world.targets) {
      if (tg.type === 'console' || tg.type === 'floor') continue;
      const d = Math.hypot(tg.pos.x - px, -tg.pos.z - py);
      if (d < tg.radius && d < bd) { bd = d; best = tg; }
    }
    this.target = best;
    if (best) {
      const verb = best.type === 'npc' ? 'konuş' : best.type === 'hatch' ? 'araca bin' : 'içeri gir';
      this.hud.prompt(`<kbd>E</kbd> ${verb} — ${best.label}`);
    } else this.hud.prompt('');
  }

  collide(x, y) {
    for (const b of this.buildingData) {
      if (!b.built || b.district === 0) continue;
      const hw = b.w / 2 + 0.4, hd = b.d / 2 + 0.4;
      const lx = x - b.x, ly = y - b.y;
      if (Math.abs(lx) < hw && Math.abs(ly) < hd) {
        const ox = hw - Math.abs(lx), oy = hd - Math.abs(ly);
        if (ox < oy) x = b.x + Math.sign(lx || 1) * hw; else y = b.y + Math.sign(ly || 1) * hd;
      }
    }
    const lp = this.world.lander.position, ldx = x - lp.x, ldy = y + lp.z, ld = Math.hypot(ldx, ldy);
    if (ld < 3.2 && this.state.craft.phase_id === 0) { x = lp.x + ldx / (ld || 1) * 3.2; y = -lp.z + ldy / (ld || 1) * 3.2; }
    return [x, y];
  }

  camera(dt, s) {
    const cam = this.world.camera, m = s.player.mode_id, L = this.world.lander.position;
    const shake = (this.coreSettings?.reduce_motion ? 0 : this.coreSettings?.camera_shake ?? 1);
    if (m === 2) {
      const ground = this.core.height(this.pos.x, this.pos.y);
      const bob = shake * Math.sin(this.bob || 0) * 0.035;
      cam.position.set(this.pos.x, ground + 1.65 + this.jumpZ + bob, -this.pos.y);
      cam.rotation.set(this.pitch, this.yaw, 0, 'YXZ');
    } else if (m === 3) {
      const b = this.buildingData.find((x) => x.id === s.player.building);
      if (b) {
        const fh = b.h / b.floors;
        const tx = b.x + b.w * 0.25, ty = b.y - b.d * 0.25;
        cam.position.set(tx, b.z + s.player.floor * fh + 1.6, -ty);
        cam.rotation.set(this.pitch, this.yaw, 0, 'YXZ');
      }
    } else if (this.view === 'cockpit') {
      cam.position.set(L.x + 0.6, L.y + 8.9, L.z);
      cam.rotation.set(this.pitch, this.yaw, 0, 'YXZ');
      if (s.craft.phase_id === 1 && shake) {
        const k = s.craft.engines_on ? 0.02 * s.craft.throttle * shake : 0;
        cam.position.x += (Math.random() - 0.5) * k; cam.position.y += (Math.random() - 0.5) * k;
      }
    } else {
      // takip kamerası: irtifayla uzaklaşır, fareyle etrafında döner
      const dist = 26 + Math.min(420, s.craft.alt * 0.06);
      const p = Math.max(-0.2, Math.min(1.2, 0.25 - this.pitch));
      const target = L.clone(); target.y += 6;
      const want = target.clone().add({ x: Math.sin(this.yaw) * Math.cos(p) * dist, y: Math.sin(p) * dist, z: Math.cos(this.yaw) * Math.cos(p) * dist });
      const gnd = this.core.height(want.x, -want.z) + 2;
      if (want.y < gnd) want.y = gnd;
      cam.position.copy(want);   // araç km/s hızla giderken gecikmesiz takip
      cam.lookAt(target);
    }
    cam.far = Math.max(30000, s.craft.alt * 8);
    cam.updateProjectionMatrix();
  }

  checkDeath(s) {
    let why = null;
    if (!s.player.alive) why = 'Hayatını kaybettin: ' + (s.player.cause || 'bilinmeyen neden');
    else if (s.craft.phase_id === 2) why = `Araç yüzeye ${Math.round(s.craft.touchdown || 0)} m/s hızla çarptı. Güvenli temas için dikey hız 3 m/s altında olmalı (iniş desteği modu bunu otomatik yapar).`;
    if (why && !this.dead) {
      this.dead = true;
      $('deathText').textContent = why;
      $('deathPanel').classList.add('open');
      this.onPanel(true);
    }
  }

  save() {
    const r = this.core.save();
    if (!r.ok) return this.hud.toast(r.msg, 'err');
    if (store.set('save', r.data)) this.hud.toast(`Kaydedildi (${Math.round(r.data.length / 1024)} KB, sağlama toplamlı)`, 'ok');
    else this.hud.toast('Tarayıcı depolaması kullanılamıyor', 'err');
  }

  applySettings({ quality, core }) {
    const r = this.core.cmd({ op: 'settings', value: core });
    if (r.ok) { this.coreSettings = r.settings; store.set('settings', r.settings); }
    document.documentElement.style.fontSize = (16 * (this.coreSettings.text_scale || 1)) + 'px';
    document.body.dataset.cv = this.coreSettings.color_vision || 0;
    if (quality !== this.qualityName) {
      store.set('quality', quality);
      this.hud.toast('Grafik kalitesi yeniden yüklemeden sonra tam uygulanır', 'ok');
      this.qualityName = quality;
    }
  }
}

// ===================================================================== AKIŞ
function show(id) {
  document.querySelectorAll('.screen').forEach((s) => s.classList.toggle('active', s.id === id));
}

boot().then(({ core, World, Hud }) => {
  clearInterval(factTimer);
  $('loadLabel').textContent = 'Hazır';
  const tap = $('tapStart');
  tap.classList.remove('hidden');
  tap.focus();
  let menuBg = null, game = null;
  const toMenu = () => {
    show('menu');
    if (!menuBg) menuBg = new SpaceBackdrop($('menuCanvas'), { planet: 'moon', pos: [0.98, 1.08, 0.55] });
    else { menuBg.running = true; menuBg.last = performance.now(); requestAnimationFrame(function l(t) { if (!menuBg.running) return; menuBg.draw(Math.min(0.05, (t - menuBg.last) / 1000)); menuBg.last = t; requestAnimationFrame(l); }); }
    menuBg.speed = 0.12;
    $('btnLoadGame').disabled = !store.get('save', null);
  };
  const play = (body, saveText) => {
    if (!game) game = new Game(core, World, Hud);
    show('game');
    if (menuBg) menuBg.stop();
    requestAnimationFrame(() => {
      game.world.resize();
      if (!game.start(body, saveText)) toMenu();
      else game.paused = false;
    });
  };
  tap.onclick = () => {
    backdrop.speed = 6;
    $('loading').classList.add('warp');
    if (touch) document.documentElement.requestFullscreen?.().catch(() => {});
    setTimeout(() => { backdrop.stop(); toMenu(); }, 650);
  };
  document.querySelectorAll('.mission-card').forEach((c) => (c.onclick = () => play(c.dataset.body)));
  $('btnLoadGame').onclick = () => { const s = store.get('save', null); if (s) play(null, s); };
  $('btnMenuSettings').onclick = () => {
    if (!game) game = new Game(core, World, Hud);
    game.hud.openSettings(game.qualityName, (v) => game.applySettings(v));
  };
  $('btnResume').onclick = () => game.pause(false);
  $('btnSave').onclick = () => game.save();
  $('btnSettings').onclick = () => game.hud.openSettings(game.qualityName, (v) => game.applySettings(v));
  $('btnToMenu').onclick = () => { game.pause(false); game.paused = true; game.hud.closeAll(); toMenu(); };
  $('btnRetry').onclick = () => { $('deathPanel').classList.remove('open'); play(game.body); };
  $('btnDeathMenu').onclick = () => { $('deathPanel').classList.remove('open'); game.paused = true; toMenu(); };
  window.__kozmo = { core, get game() { return game; }, play };
}).catch((err) => {
  console.error(err);
  clearInterval(factTimer);
  $('loadLabel').textContent = 'Hata: ' + err.message;
  $('loadLabel').style.color = 'var(--red)';
  $('loadFact').innerHTML = `Oyun başlatılamadı. Tarayıcı WebAssembly ve WebGL2 desteklemeli.<small>${String(err.message)}</small>`;
  $('loadFact').classList.add('show');
});
