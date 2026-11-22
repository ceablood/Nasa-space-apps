// KOZMOGENİS — HUD ve paneller. Unreal'daki SKozmoCockpitHUD / SKozmoNovaPanel / SKozmoManagementPanel karşılığı.
// Bütün sayılar KozmoCore durumundan okunur; burada hesap yok, yalnız gösterim.

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const fmt = (v, d = 0) => (Number.isFinite(v) ? v.toLocaleString('tr-TR', { minimumFractionDigits: d, maximumFractionDigits: d }) : '—');
const pct = (v) => fmt((v || 0) * 100) + '%';

export const MODULES = ['Habitat', 'Sera', 'Elektrolizör', 'Güneş paneli', 'Fisyon reaktörü', 'Maden', 'Sabatier', 'Laboratuvar', 'Klinik', 'Su geri dönüşüm'];
export const FLIGHT_MODES = ['Manuel', 'Destekli', 'Otopilot', 'İniş desteği', 'Kenetlenme', 'Acil'];
const POLICIES = ['Yok', 'Karne', 'Araştırma odağı', 'Önce güvenlik', 'Festival', 'Genişleme'];
const QUESTS = [
  ['power_crisis', 'Enerji krizi'], ['sample_hunt', 'Numune avı'], ['new_home', 'Yeni yuva'],
  ['health_check', 'Sağlık taraması'], ['security_round', 'Güvenlik turu'], ['orbit_test', 'Yörünge testi'],
];
const NOVA_QUICK = ['Durum raporu', 'Gezegen riski ne?', 'Yakıt yeterli mi?', 'Görevlerim neler?', 'Asteroit tehdidi var mı?', "Mars'a görev planla"];

// yalnız değişince DOM'a yaz: 20 Hz innerHTML yeniden yerleşim (layout) maliyetini keser
function setHTML(el, html) { if (el._h !== html) { el._h = html; el.innerHTML = html; } }
function setText(el, t) { if (el._t !== t) { el._t = t; el.textContent = t; } }

export class Hud {
  constructor(game) {
    this.g = game;
    this.toastsEl = $('toasts');
    this.lastLog = 0;
    this.mgmtTab = 'agency';
    this.mm = $('minimap').getContext('2d');
    document.querySelectorAll('[data-close]').forEach((b) => b.addEventListener('click', () => this.close(b.dataset.close)));
    $('btnNova').onclick = () => this.toggle('novaPanel');
    $('btnQuests').onclick = () => this.openQuests();
    $('btnMgmt').onclick = () => this.openMgmt();
    $('btnPause').onclick = () => this.g.pause(true);
    $('novaForm').addEventListener('submit', (e) => { e.preventDefault(); const t = $('novaInput').value.trim(); if (t) { this.ask(t); $('novaInput').value = ''; } });
    $('novaQuick').innerHTML = NOVA_QUICK.map((q) => `<button type="button">${esc(q)}</button>`).join('');
    $('novaQuick').querySelectorAll('button').forEach((b) => (b.onclick = () => this.ask(b.textContent)));
    this.novaMsg('ai', 'Ben NOVA. Gerçek NASA/ESA verisiyle konuşurum; kaynak gösteririm. Kaynak harcayan ya da kritik bir işlemi senin onayın olmadan yapmam.', []);
  }

  anyOpen() { return !!document.querySelector('.modal.open, .drawer.open'); }
  open(id) { $(id).classList.add('open'); this.g.onPanel(true); }
  close(id) {
    $(id).classList.remove('open');
    if (id === 'interior' && this.g.state?.player.mode_id === 3) { /* bina içinde panel kapandı: bakmaya devam */ }
    if (id === 'pauseMenu') this.g.pause(false);
    this.g.onPanel(this.anyOpen());
  }
  toggle(id) { $(id).classList.contains('open') ? this.close(id) : this.open(id); if (id === 'novaPanel' && $(id).classList.contains('open')) setTimeout(() => $('novaInput').focus(), 50); }
  closeAll() { document.querySelectorAll('.modal.open, .drawer.open').forEach((m) => m.classList.remove('open')); this.g.onPanel(false); }

  toast(msg, kind = '') {
    if (!msg) return;
    const t = document.createElement('div');
    t.className = 'toast ' + kind;
    t.textContent = msg;
    this.toastsEl.prepend(t);
    while (this.toastsEl.children.length > 5) this.toastsEl.lastChild.remove();
    setTimeout(() => t.remove(), 5200);
  }
  // hatalar her zaman; başarılı kısa onaylar ("Motorlar") gösterilmez, çünkü sefer günlüğü aynı olayı zaten bildirir
  result(r, okKind = 'ok') { if (r && r.msg && (!r.ok || r.msg.length > 24)) this.toast(r.msg, r.ok ? okKind : 'err'); return r; }

  // ---------------------------------------------------------------- her kare (≈20 Hz)
  update(s) {
    this.envBar(s);
    setHTML($('creditChip'), `<b>${fmt(s.credits / 1e6, 2)} M₺</b> kredi`);
    setText($('tutorial'), s.tutorial || '');
    const seated = s.player.mode_id === 0, inCraft = s.player.mode_id <= 1;
    $('cockpit').classList.toggle('hidden-panel', !inCraft);
    if (inCraft) this.cockpit(s);
    this.vitals(s);
    this.warnings(s);
    this.actions(s);
    this.minimap(s);
    const day = s.day, h = s.crew_hour;
    setText($('clock'), `Gün ${fmt(day, 0)} · ${String(Math.floor(h)).padStart(2, '0')}:${String(Math.floor((h % 1) * 60)).padStart(2, '0')}`);
    // yeni günlük satırları -> bildirim
    if (s.log && s.log.length) {
      if (this.lastLog > s.log.length) this.lastLog = 0;
      for (let i = this.lastLog; i < s.log.length; i++) if (this.lastLog) this.toast(String(s.log[i]).replace(/^\[[^\]]*\]\s*/, ''), 'log');
      this.lastLog = s.log.length;
    }
    void seated;
  }

  envBar(s) {
    const w = (s.weather || []).map((x) => `<span class="pill ${x.visibility < 0.5 ? 'bad' : 'warn'}">${esc(x.kind)}</span>`).join('');
    const p = s.pressure < 0.01 ? 'vakum' : `${fmt(s.pressure, s.pressure < 10 ? 2 : 0)} kPa`;
    setHTML($('envBar'), `<div class="title">${esc(s.env)}</div><div class="chips">
      <span class="pill">${fmt(s.gravity, 2)} m/s²</span><span class="pill">${p}</span>
      <span class="pill ${s.surface_c < -100 || s.surface_c > 80 ? 'warn' : ''}">${fmt(s.surface_c, 0)} °C</span>
      <span class="pill">yerel ${fmt(s.local_hour, 1)} sa</span>${s.population ? `<span class="pill">${s.population} kişi</span>` : ''}${w}</div>`);
  }

  cockpit(s) {
    const c = s.craft;
    const el = $('cockpit');
    if (!this.gauges) {
      // göstergeler bir kez kurulur; sonra yalnız değer/çubuk/sınıf güncellenir
      const keys = ['İRTİFA', 'DİKEY HIZ', 'YATAY HIZ', 'HEDEFE', 'YAKIT', 'İTKİ', 'MOTOR ISI', 'KABİN', 'O₂', 'GÜÇ', 'GÖVDE', 'KALKAN'];
      el.innerHTML = '<div class="mode" id="ckTop"></div>' + keys.map((k) => `<div class="gauge"><div class="k">${k}</div><div class="v"></div><div class="bar"></div></div>`).join('') + '<div class="mode" id="ckBot"></div>';
      this.gauges = [...el.querySelectorAll('.gauge')].map((g) => ({ g, v: g.querySelector('.v'), bar: g.querySelector('.bar') }));
    }
    const set = (i, v, unit, frac, cls = '') => {
      const G = this.gauges[i];
      setHTML(G.v, `${v}<small> ${unit}</small>`);
      const w = frac == null ? '0%' : `${(Math.max(0, Math.min(1, frac)) * 100).toFixed(1)}%`;
      if (G.w !== w) { G.w = w; G.bar.style.width = w; }
      const k = 'gauge ' + cls;
      if (G.g.className !== k) G.g.className = k;
    };
    const vvBad = c.phase_id === 1 && c.alt < 300 && c.vv < -4;
    const fuelCls = c.fuel_frac < 0.1 ? 'bad' : c.fuel_frac < 0.25 ? 'warn' : '';
    const manual = c.mode === 'Manuel' || c.mode === 'Destekli';
    set(0, c.alt >= 10000 ? fmt(c.alt / 1000, 2) : fmt(c.alt, 0), c.alt >= 10000 ? 'km' : 'm', null, c.alt < 50 && c.phase_id === 1 ? 'warn' : '');
    set(1, fmt(c.vv, 1), 'm/s', null, vvBad ? 'bad' : '');
    set(2, fmt(c.vh, 1), 'm/s');
    set(3, c.remaining ? fmt(c.remaining / 1000, 2) : '—', 'km');
    set(4, fmt(c.fuel, 2), 't', c.fuel_frac, fuelCls);
    if (manual) set(5, pct(c.throttle), c.engines_on ? 'AÇIK' : 'kapalı', c.throttle, c.engines_on ? '' : 'warn');
    else set(5, c.engines_on ? 'GÜDÜM' : 'kapalı', '', null, c.engines_on ? '' : 'warn');
    set(6, fmt(c.engine_k, 0), 'K', c.engine_k / 3200, c.engine_k > 2900 ? 'bad' : '');
    set(7, fmt(c.cabin_kpa, 1), 'kPa', c.cabin_kpa / 101, c.cabin_kpa < 60 ? 'bad' : '');
    set(8, fmt(c.o2_days, 1), 'gün', Math.min(1, c.o2_days / 10), c.o2_days < 1 ? 'bad' : '');
    set(9, fmt(c.power_kw, 1), 'kW', c.battery, c.power_kw < 0 ? 'warn' : '');
    set(10, pct(c.hull), '', c.hull, c.hull < 0.5 ? 'bad' : '');
    set(11, pct(c.shield), '', c.shield);
    setHTML($('ckTop'), `<b>${esc(c.model)}</b><span>${esc(c.phase)}${c.seated ? '' : ' · <i>koltukta değil</i>'}</span><b>${esc(c.mode)}</b>`);
    setHTML($('ckBot'), `<span>NAV ${c.nav ? 'tamam' : '<b style="color:var(--red)">ARIZA</b>'} · Radar: ${esc(c.radar)}</span><span>${c.docking.active ? `Kenetlenme ${fmt(c.docking.range, 0)} m, ${fmt(c.docking.closing, 2)} m/s` : ''}${c.touchdown ? `temas ${fmt(c.touchdown, 1)} m/s` : ''}</span>`);
  }

  vitals(s) {
    const p = s.player;
    const m = (k, v, frac, warn) => `<div class="row"><span>${k}</span><b>${v}</b></div><div class="meter"><i class="${warn ? 'warn' : ''}" style="width:${Math.max(0, Math.min(1, frac)) * 100}%"></i></div>`;
    const where = p.mode_id === 3 ? `${esc(p.building)} · kat ${p.floor}` : esc(p.mode);
    setHTML($('vitals'), `<div class="row"><span>Konum</span><b>${where}</b></div>
      ${m('Sağlık', pct(p.health), p.health, p.health < 0.5)}
      ${m('Giysi O₂', fmt(p.o2_h, 1) + ' sa', p.o2_h / 8, p.o2_h < 1.5)}
      ${m('Doz', fmt(p.dose, 1) + ' mSv', p.dose / 600, p.dose > 250)}
      <div class="row"><span>Numune</span><b>${p.samples}</b></div>${p.thermal ? '<div class="row"><span>Termal giysi</span><b>açık</b></div>' : ''}`);
  }

  warnings(s) {
    const w = s.craft.warnings || [];
    const inCraft = s.player.mode_id <= 1;
    setHTML($('warnings'), (inCraft ? w : []).slice(0, 3).map((x) => `<div class="warn-item sev${x.sev}">⚠ ${esc(x.msg)}<br><small>Prosedür (P): ${esc(x.proc)}</small></div>`).join(''));
  }

  actions(s) {
    const g = this.g, mode = s.player.mode_id, c = s.craft;
    const list = [];
    if (mode === 0) {
      if (c.phase_id === 3) list.push(['B', 'İnişi başlat', () => g.cmd({ op: 'descent' }), 'primary']);
      if (c.phase_id === 1) {
        list.push(['F', c.engines_on ? 'Motoru kapat' : 'Motoru yak', () => g.cmd({ op: 'engines', on: !c.engines_on })]);
        list.push(['L', 'İniş desteği + motor', () => { g.cmd({ op: 'mode', mode: 3 }); if (!c.engines_on) g.cmd({ op: 'engines', on: true }); }, c.mode === FLIGHT_MODES[3] && c.engines_on ? '' : 'primary']);
      }
      if (c.phase_id === 0) list.push(['T', 'Kalkış (15 km)', () => g.cmd({ op: 'take_off', alt: 15000 })]);
      if (c.warnings && c.warnings.length) list.push(['P', 'Prosedür', () => g.cmd({ op: 'procedure' }), 'danger']);
      list.push(['E', 'Kalk', () => g.cmd({ op: 'stand' })]);
      list.push(['V', 'Kamera', () => g.toggleView()]);
    } else if (mode === 1) {
      list.push(['E', 'Koltuğa otur', () => g.cmd({ op: 'sit' }), 'primary']);
      list.push(['V', 'Kamera', () => g.toggleView()]);
      if (c.phase_id === 0) list.push(['X', 'Araçtan çık', () => g.cmd({ op: 'exit' })]);
      if (s.body === 'titan') list.push(['Y', 'Araçta analiz', () => g.cmd({ op: 'analyze_onboard' })]);
    } else if (mode === 2) {
      const t = g.target;
      if (t) list.push(['E', t.type === 'npc' ? 'Konuş: ' + t.label : t.type === 'hatch' ? 'Araca bin' : 'Gir: ' + t.label, () => g.interact(), 'primary']);
      list.push(['G', 'Numune al', () => g.cmd({ op: 'sample' })]);
      if (!s.has_colony) {
        list.push(['K', 'Su tara', () => g.cmd({ op: 'scan_water' })]);
        if (s.water_found) list.push(['O', 'Koloni kur', () => g.cmd({ op: 'found' }), 'primary']);
      } else list.push(['C', 'İnşa et', () => this.openMgmt('build')]);
      if (s.body === 'titan') list.push(['H', 'Termal giysi', () => g.cmd({ op: 'thermal' })]);
    } else if (mode === 3) {
      list.push(['E', 'Bina paneli', () => this.openInterior(s)]);
      list.push(['Q', 'Dışarı çık', () => g.cmd({ op: 'leave' })]);
    }
    list.push(['N', 'NOVA', () => this.toggle('novaPanel')]);
    const key = list.map((a) => a[0] + a[1] + (a[3] || '')).join('|');
    if (key !== this.actKey) {
      this.actKey = key;
      const bar = $('actionbar');
      bar.innerHTML = list.map((a, i) => `<button class="act ${a[3] || ''}" data-i="${i}"><kbd>${a[0]}</kbd>${esc(a[1])}</button>`).join('');
      bar.querySelectorAll('button').forEach((b) => (b.onclick = () => this.actList[+b.dataset.i][2]()));
    }
    this.actList = list;
  }
  actionByKey(k) {
    const a = (this.actList || []).find((x) => x[0] === k);
    if (a) { a[2](); return true; }
    return false;
  }

  minimap(s) {
    const g = this.mm, W = 200, sc = 200 / 420;   // ±210 m
    const px = s.player.x, py = s.player.y;
    g.clearRect(0, 0, W, W);
    g.save();
    g.translate(W / 2, W / 2);
    g.beginPath(); g.arc(0, 0, W / 2 - 2, 0, Math.PI * 2); g.clip();
    g.fillStyle = 'rgba(8,14,26,0.85)'; g.fillRect(-W, -W, W * 2, W * 2);
    g.strokeStyle = 'rgba(62,230,255,0.12)';
    for (let r = 50; r < 220; r += 50) { g.beginPath(); g.arc(0, 0, r * sc, 0, Math.PI * 2); g.stroke(); }
    for (const b of this.g.buildingData || []) {
      const x = (b.x - px) * sc, y = -(b.y - py) * sc;
      g.fillStyle = b.district === 0 ? 'rgba(255,179,71,0.6)' : b.built ? 'rgba(180,200,220,0.75)' : 'rgba(255,160,64,0.25)';
      if (b.district === 0) { g.beginPath(); g.arc(x, y, (b.w / 2) * sc, 0, Math.PI * 2); g.fill(); }
      else g.fillRect(x - (b.w / 2) * sc, y - (b.d / 2) * sc, b.w * sc, b.d * sc);
    }
    g.fillStyle = '#7dffa8';
    for (const n of s.npcs || []) { g.beginPath(); g.arc((n.x - px) * sc, -(n.y - py) * sc, 2.2, 0, Math.PI * 2); g.fill(); }
    // oyuncu: bakış yönlü ok
    g.rotate(-this.g.yaw);
    g.fillStyle = '#3ee6ff';
    g.beginPath(); g.moveTo(0, -7); g.lineTo(5, 5); g.lineTo(0, 2); g.lineTo(-5, 5); g.closePath(); g.fill();
    g.restore();
    g.fillStyle = 'rgba(216,244,255,0.7)'; g.font = '600 10px Inter'; g.fillText('K', W / 2 - 3, 12);
  }

  prompt(text) { $('prompt').innerHTML = text || ''; }

  // ---------------------------------------------------------------- NOVA
  novaMsg(who, text, sources, pending) {
    const d = document.createElement('div');
    d.className = 'msg ' + who + (pending ? ' pending' : '');
    d.innerHTML = esc(text).replace(/\n/g, '<br>') + (sources && sources.length ? `<div class="src">Kaynak: ${sources.map(esc).join(' · ')}</div>` : '') +
      (pending ? '<div class="src">Bu işlem onay bekliyor: NOVA kendiliğinden uygulamaz.</div>' : '');
    $('novaLog').append(d);
    $('novaLog').scrollTop = 1e9;
  }
  ask(text) {
    this.novaMsg('me', text);
    const r = this.g.core.cmd({ op: 'nova', text });
    this.novaMsg('ai', r.msg || '(yanıt yok)', r.sources, r.pending);
  }

  // ---------------------------------------------------------------- diyalog
  openDialog(npc, r) {
    if (!r.ok) { this.toast(r.msg, 'err'); return; }
    $('dlgName').textContent = npc.name;
    $('dlgJob').textContent = `${npc.job} · ${npc.intent}${npc.reason ? ' — ' + npc.reason : ''}`;
    $('dlgPortrait').textContent = npc.name.split(' ').map((x) => x[0]).join('').slice(0, 2);
    this.dialogStep(r);
    this.open('dialog');
  }
  dialogStep(r) {
    $('dlgText').textContent = r.msg;
    const opts = r.options || [];
    $('dlgOptions').innerHTML = opts.length ? opts.map((o, i) => `<button><span>${i + 1}</span>${esc(o)}</button>`).join('') : '<button><span>×</span>Konuşmayı bitir</button>';
    $('dlgOptions').querySelectorAll('button').forEach((b, i) => (b.onclick = () => {
      if (!opts.length || r.active === false) { this.close('dialog'); return; }
      const n = this.g.core.cmd({ op: 'talk_choose', index: i });
      if (!n.ok) { this.toast(n.msg, 'err'); this.close('dialog'); return; }
      this.dialogStep(n);
    }));
  }

  // ---------------------------------------------------------------- bina içi
  openInterior(s) {
    const b = (this.g.buildingData || []).find((x) => x.id === s.player.building);
    if (!b) return;
    $('intName').textContent = b.name;
    $('intMeta').textContent = `${b.floors} kat · ${b.elevator ? 'asansörlü' : 'yalnız merdiven'} · ${b.pressurized ? 'basınçlı' : 'basınçsız'}`;
    const floors = [];
    for (let f = 0; f < b.floors; f++) {
      const items = b.rooms.filter((r) => r.floor === f).flatMap((r) => r.items.map((it) => ({ ...it, room: r.name })));
      const here = f === s.player.floor;
      floors.push(`<div class="int-floor"><h4>${f === 0 ? 'Zemin kat' : (s.body === 'moon' ? '-' : '') + f + '. kat'} ${here ? '· <b>buradasın</b>' : `<button class="btn small" data-floor="${f}">${b.elevator ? 'Asansör' : 'Merdiven'}</button>`}</h4>
        <div class="int-items">${items.map((it) => `<button data-use="${esc(it.id)}" ${here ? '' : 'disabled'} title="${esc(it.room)}">${esc(it.name)}<small> · ${esc(it.room)}</small></button>`).join('') || '<span class="muted">konsol yok</span>'}</div></div>`);
    }
    $('intBody').innerHTML = floors.join('') + '<div class="row-wrap"><button class="btn ghost" id="btnLeave">Binadan çık</button></div>';
    $('intOut').textContent = '';
    $('intBody').querySelectorAll('[data-floor]').forEach((x) => (x.onclick = () => {
      let r = this.g.core.cmd({ op: 'floor', floor: +x.dataset.floor, elevator: true });
      if (!r.ok && /merdiven/i.test(r.msg)) r = this.g.core.cmd({ op: 'floor', floor: +x.dataset.floor, elevator: false });
      this.result(r);
      this.g.refresh();
      this.openInterior(this.g.state);
    }));
    $('intBody').querySelectorAll('[data-use]').forEach((x) => (x.onclick = () => {
      const r = this.g.core.cmd({ op: 'use', id: x.dataset.use });
      $('intOut').textContent = r.msg;
      if (!r.ok) $('intOut').classList.add('err'); else $('intOut').classList.remove('err');
    }));
    $('btnLeave').onclick = () => { this.g.cmd({ op: 'leave' }); this.close('interior'); };
    this.open('interior');
  }

  // ---------------------------------------------------------------- görevler
  openQuests() {
    const s = this.g.state;
    $('questText').textContent = (s.quests || 'Etkin görev yok') + (s.tasks && s.tasks.length ? '\n\nSefer görevleri:\n' + s.tasks.map((t) => '• ' + t).join('\n') : '');
    $('questOffers').innerHTML = s.has_colony ? QUESTS.map(([k, n]) => `<button class="btn small ghost" data-q="${k}">+ ${esc(n)}</button>`).join('') : '<span class="muted">Koloni görevleri koloni kurulunca açılır.</span>';
    $('questOffers').querySelectorAll('[data-q]').forEach((b) => (b.onclick = () => { this.result(this.g.core.cmd({ op: 'quest', key: b.dataset.q })); this.g.refresh(); this.openQuests(); }));
    this.open('questPanel');
  }

  // ---------------------------------------------------------------- yönetim
  openMgmt(tab) {
    if (tab) this.mgmtTab = tab;
    const tabs = [['agency', 'Ajans'], ['build', 'İnşaat'], ['contracts', 'Sözleşmeler'], ['civ', 'Medeniyet'], ['crew', 'Mürettebat'], ['station', 'İstasyon'], ['neo', 'Gezegen savunması'], ['orbit', 'Yörünge planı'], ['news', 'Haberler']];
    $('mgmtTabs').innerHTML = tabs.map(([k, n]) => `<button class="${k === this.mgmtTab ? 'on' : ''}" data-t="${k}">${n}</button>`).join('');
    $('mgmtTabs').querySelectorAll('button').forEach((b) => (b.onclick = () => this.openMgmt(b.dataset.t)));
    const m = this.g.core.management();
    const body = $('mgmtBody');
    const t = this.mgmtTab;
    const refresh = (r) => { this.result(r); this.g.refresh(); this.openMgmt(); };
    if (t === 'agency') {
      const c = m.caps;
      body.innerHTML = `<p class="muted">Kapasite: kalkış ${fmt(c.max_liftoff_t)} t · eşzamanlı görev ${c.missions} · araştırma ×${fmt(c.research, 2)} · iletişim ${fmt(c.comms_mkm, 0)} milyon km · NOVA seviye ${c.nova} · günlük gider ${fmt(c.upkeep)} ₺ · başarım ${m.achievements}/${m.achievements_total}</p>
        <div class="grid-cards">${m.facilities.map((f) => `<div class="card"><h5>${esc(f.name)}</h5><div class="lvl">${[...Array(f.max + 1).keys()].slice(1).map((i) => `<i class="${i <= f.level ? 'on' : ''}"></i>`).join('')}</div><p>${esc(f.desc)}</p>
        ${f.level < f.max ? `<button class="btn small" data-up="${f.id}">Yükselt · ${fmt(f.next_cost / 1e6, 2)} M₺</button>` : '<span class="muted">en üst seviye</span>'}</div>`).join('')}</div>`;
      body.querySelectorAll('[data-up]').forEach((b) => (b.onclick = () => {
        if (confirm('Bu yükseltme kredi harcar. Onaylıyor musun?')) refresh(this.g.core.cmd({ op: 'upgrade', facility: +b.dataset.up }));
      }));
    } else if (t === 'build') {
      const s = this.g.state;
      const proj = (s.construction || []).map((p) => `<tr><td>${esc(p.module)}</td><td>${esc(p.state)}</td><td>${pct(p.progress)}</td></tr>`).join('');
      body.innerHTML = s.has_colony
        ? `<p class="muted">İnşaatı mühendis NPC'ler yapar: malzeme taşır, iskele kurar. Süre ve maliyet çekirdekteki modül tablosundan gelir.</p>
          <div class="row-wrap">${MODULES.map((n, i) => `<button class="btn small" data-b="${i}">${esc(n)}</button>`).join('')}<button class="btn small ghost" id="btnReinforce">Habitatı güçlendir</button></div>
          <table class="t"><tr><th>Proje</th><th>Durum</th><th>İlerleme</th></tr>${proj || '<tr><td colspan="3" class="muted">proje yok</td></tr>'}</table>`
        : `<p>Bu gökcisminde henüz koloni yok. Araçtan çık, <b>K</b> ile yeraltı suyu tara, su bulunursa <b>O</b> ile koloniyi kur.</p>`;
      body.querySelectorAll('[data-b]').forEach((b) => (b.onclick = () => { if (confirm(MODULES[+b.dataset.b] + ' inşaatı kredi ve malzeme harcar. Onaylıyor musun?')) refresh(this.g.core.cmd({ op: 'build', module: +b.dataset.b })); }));
      const rb = $('btnReinforce'); if (rb) rb.onclick = () => refresh(this.g.core.cmd({ op: 'reinforce' }));
    } else if (t === 'contracts') {
      body.innerHTML = `<p class="muted">İtibar: ${fmt(m.reputation, 2)}. Sözleşmeler oyun içi ekonomidir (oyun varsayımı).</p><table class="t"><tr><th>Müşteri</th><th>Hedef</th><th>Yük</th><th>Ödül</th><th>Son gün</th><th>Durum</th><th></th></tr>
        ${m.contracts.map((c) => `<tr><td>${esc(c.client)}</td><td>${esc(c.dest)}</td><td>${fmt(c.t, 1)} t</td><td>${fmt(c.reward / 1e6, 2)} M₺</td><td>${fmt(c.deadline)}</td><td>${esc(c.status)}</td><td>${c.status === 'Teklif' ? `<button class="btn small" data-c="${c.id}">Kabul</button>` : ''}</td></tr>`).join('')}</table>`;
      body.querySelectorAll('[data-c]').forEach((b) => (b.onclick = () => refresh(this.g.core.cmd({ op: 'accept_contract', id: +b.dataset.c }))));
    } else if (t === 'civ') {
      const c = m.civ;
      body.innerHTML = `<div class="grid-cards"><div class="card"><h5>Çağ</h5><p><b>${esc(c.era)}</b></p></div><div class="card"><h5>Nüfus</h5><p><b>${c.population}</b></p></div>
        <div class="card"><h5>İstikrar</h5><p><b>${pct(c.stability)}</b></p></div><div class="card"><h5>Mutluluk</h5><p><b>${pct(c.happiness)}</b></p></div><div class="card"><h5>Gıda</h5><p><b>${fmt(c.food_days, 0)} gün</b></p></div></div>
        <h4>Politika: ${esc(c.policy)}</h4><div class="row-wrap">${POLICIES.map((p, i) => `<button class="btn small ${p === c.policy ? '' : 'ghost'}" data-p="${i}">${p}</button>`).join('')}</div>`;
      body.querySelectorAll('[data-p]').forEach((b) => (b.onclick = () => refresh(this.g.core.cmd({ op: 'policy', policy: +b.dataset.p }))));
    } else if (t === 'crew') {
      body.innerHTML = `<table class="t"><tr><th>Ad</th><th>Rütbe</th><th>Eğitim</th><th>Kümülatif doz</th></tr>${m.crew.map((c) => `<tr><td>${esc(c.name)}</td><td>${esc(c.rank)}</td><td>${pct(c.training)}</td><td>${fmt(c.dose, 1)} mSv</td></tr>`).join('')}</table>
        <p class="muted">Doz sınırı NASA kariyer standardı 600 mSv (NASA-STD-3001).</p>
        <h4>Görev planlayıcı</h4><div class="row-wrap"><button class="btn small" data-plan="mars">Mars (4 kişi)</button><button class="btn small" data-plan="moon">Ay (4 kişi)</button><button class="btn small ghost" data-plan="titan">Titan (2 kişi)</button></div><pre id="planOut"></pre>`;
      body.querySelectorAll('[data-plan]').forEach((b) => (b.onclick = () => { const r = this.g.core.cmd({ op: 'plan', target: b.dataset.plan, crew: b.dataset.plan === 'titan' ? 2 : 4 }); $('planOut').textContent = r.msg; }));
    } else if (t === 'station') {
      const st = m.station;
      body.innerHTML = st ? `<div class="grid-cards"><div class="card"><h5>${esc(st.name)}</h5><p>İrtifa <b>${fmt(st.alt_km, 1)} km</b><br>Periyot <b>${fmt(st.period, 1)} dk</b><br>İkmal <b>${fmt(st.supplies, 0)} gün</b></p></div></div>
        <p class="muted">Yörünge bozunumu atmosfer sürüklenmesiyle hesaplanır (ISS benzeri ~100 m/gün). Kenetlenme için kokpitte "Kenetlenme" modunu kullan.</p>
        <button class="btn small" id="btnDock">Kenetlenme yaklaşması başlat (500 m)</button>` : '<p>İstasyon yok.</p>';
      const d = $('btnDock'); if (d) d.onclick = () => refresh(this.g.core.cmd({ op: 'dock', range: 500 }));
    } else if (t === 'neo') {
      body.innerHTML = `<table class="t"><tr><th>Cisim</th><th>Çap</th><th>Enerji</th><th>Olasılık</th><th>Palermo</th><th>Torino</th><th>Not</th></tr>
        ${m.neo.map((x) => `<tr><td>${esc(x.name)}${x.real ? '' : ' <small class="muted">(kurgu)</small>'}</td><td>${fmt(x.d, 0)} m</td><td>${fmt(x.e, 0)} Mt</td><td>${x.p.toExponential(1)}</td><td>${fmt(x.palermo, 2)}</td><td>${x.torino}</td><td><small>${esc(x.note)}</small></td></tr>`).join('')}</table>
        <p class="muted">Gerçek cisimler NASA CNEOS Sentry verisinden; kurgusal olanlar işaretli.</p>`;
    } else if (t === 'orbit') {
      body.innerHTML = `<p class="muted">Dünya → hedef transferi: her hücre gerçek Lambert çözümünden (C3, km²/s²). Koyu = düşük enerji.</p>
        <div class="row-wrap"><button class="btn small" data-tg="mars">Mars</button><button class="btn small ghost" data-tg="venus">Venüs</button></div><canvas class="pork" id="pork" width="720" height="360"></canvas><div id="porkInfo" class="muted"></div>`;
      const draw = (tg) => {
        const p = this.g.core.porkchop(tg, 780, 20);
        if (!p.ok) { $('porkInfo').textContent = p.msg; return; }
        this.drawPork(p);
        $('porkInfo').textContent = `En iyi: ${fmt(p.best_depart, 0)}. günde kalkış, ${fmt(p.best_tof, 0)} gün yolculuk, C3 = ${fmt(p.best_c3, 1)} km²/s²`;
      };
      body.querySelectorAll('[data-tg]').forEach((b) => (b.onclick = () => draw(b.dataset.tg)));
      draw('mars');
    } else if (t === 'news') {
      const n = this.g.state.news || [];
      body.innerHTML = n.length ? n.slice().reverse().map((x) => `<div class="card"><h5>${esc(x.h)}${x.real ? ' <small class="muted">· gerçek olaya dayalı</small>' : ''}</h5><p>${esc(x.b)}</p></div>`).join('') : '<p class="muted">Haber yok.</p>';
    }
    this.open('mgmtPanel');
  }

  drawPork(p) {
    const cv = $('pork'), g = cv.getContext('2d');
    const rows = p.c3, ny = rows.length, nx = rows[0]?.length || 0;
    const W = cv.width, H = cv.height, L = 48, B = 30;
    g.clearRect(0, 0, W, H);
    let lo = Infinity, hi = 0;
    for (const r of rows) for (const v of r) if (v > 0 && v < 200) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
    hi = Math.min(hi, lo * 6);
    const cw = (W - L) / nx, ch = (H - B) / ny;
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
      const v = rows[j][i];
      if (!(v > 0) || v > hi) { g.fillStyle = 'rgba(20,24,34,1)'; }
      else {
        const k = (v - lo) / (hi - lo);
        g.fillStyle = `hsl(${190 - k * 190}, 85%, ${18 + (1 - k) * 42}%)`;
      }
      g.fillRect(L + i * cw, H - B - (j + 1) * ch, cw + 0.5, ch + 0.5);
    }
    g.fillStyle = '#9fb3c8'; g.font = '11px Inter';
    g.fillText('kalkış günü →', W - 90, H - 8);
    g.save(); g.translate(12, H / 2 + 30); g.rotate(-Math.PI / 2); g.fillText('uçuş süresi (gün) →', 0, 0); g.restore();
    for (let i = 0; i < nx; i += Math.ceil(nx / 8)) g.fillText(String(p.depart0 + i * p.step), L + i * cw, H - B + 14);
    for (let j = 0; j < ny; j += Math.ceil(ny / 6)) g.fillText(String(p.tof0 + j * p.tof_step), 18, H - B - j * ch - 2);
  }

  // ---------------------------------------------------------------- ayarlar
  openSettings(q, apply) {
    const s = this.g.coreSettings || {};
    const row = (label, html) => `<div class="set-row"><span>${label}</span>${html}</div>`;
    const range = (id, min, max, step, v) => `<input type="range" id="${id}" min="${min}" max="${max}" step="${step}" value="${v}">`;
    $('settingsBody').innerHTML =
      row('Grafik kalitesi', `<select id="setQ"><option value="low">Düşük (tablet)</option><option value="medium">Orta</option><option value="high">Yüksek</option></select>`) +
      row('Fare / dokunma hassasiyeti', range('setMouse', 0.2, 3, 0.1, s.mouse ?? 1)) +
      row('Y eksenini ters çevir', `<input type="checkbox" id="setInv" ${s.invert_y ? 'checked' : ''}>`) +
      row('Kamera sarsıntısı', range('setShake', 0, 1, 0.05, s.camera_shake ?? 1)) +
      row('Hareketi azalt', `<input type="checkbox" id="setRm" ${s.reduce_motion ? 'checked' : ''}>`) +
      row('Ana ses', range('setVol', 0, 1, 0.05, s.master ?? 0.8)) +
      row('Renk körlüğü', `<select id="setCv"><option value="0">Normal</option><option value="1">Protanopi</option><option value="2">Döteranopi</option><option value="3">Tritanopi</option></select>`) +
      row('Yazı ölçeği', range('setText', 0.75, 1.5, 0.05, s.text_scale ?? 1)) +
      row('Zorluk', `<select id="setDiff"><option value="0">Hikâye</option><option value="1">Standart</option><option value="2">Gerçekçi</option></select>`) +
      `<p class="muted">Zorluk yalnız oyuncuya verilen payı değiştirir; bilimsel değerler değişmez.</p><div class="row-wrap"><button class="btn" id="setApply">Uygula</button></div>`;
    $('setQ').value = q;
    $('setCv').value = String(s.color_vision ?? 0);
    $('setDiff').value = String(s.difficulty ?? 1);
    $('setApply').onclick = () => {
      apply({
        quality: $('setQ').value,
        core: { ...s, mouse: +$('setMouse').value, invert_y: $('setInv').checked, camera_shake: +$('setShake').value, reduce_motion: $('setRm').checked,
          master: +$('setVol').value, color_vision: +$('setCv').value, text_scale: +$('setText').value, difficulty: +$('setDiff').value },
      });
      this.close('settingsPanel');
    };
    this.open('settingsPanel');
  }
}
