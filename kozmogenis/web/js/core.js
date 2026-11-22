// KOZMOGENİS — KozmoCore (WebAssembly) bağlantısı. Unreal sürümündeki UKozmoSubsystem ile aynı çekirdek.
// Komutlar JSON, arazi mesh'i Float32/Uint32 tamponları olarak taşınır.

export class Core {
  constructor(mod) {
    this.m = mod;
    const c = (name, ret, args) => mod.cwrap(name, ret, args);
    this._new = c('kz_new', 'string', ['string', 'number']);
    this._tick = c('kz_tick', null, ['number']);
    this._state = c('kz_state', 'string', []);
    this._cmd = c('kz_cmd', 'string', ['string']);
    this._buildings = c('kz_buildings', 'string', []);
    this._env = c('kz_environment', 'string', []);
    this._mgmt = c('kz_management', 'string', []);
    this._pork = c('kz_porkchop', 'string', ['string', 'number', 'number']);
    this._save = c('kz_save', 'string', []);
    this._load = c('kz_load', 'string', ['string']);
    this._height = c('kz_height', 'number', ['number', 'number']);
    this.version = c('kz_version', 'string', [])();
  }
  static async load(onProgress) {
    // wasm'ı akışla indir: gerçek bayt ilerlemesi yükleme ekranına gider
    const url = new URL('../dist/kozmo.wasm', import.meta.url);
    const res = await fetch(url);
    if (!res.ok) throw new Error('kozmo.wasm indirilemedi (' + res.status + ')');
    const total = Number(res.headers.get('Content-Length')) || 1200000;
    const reader = res.body.getReader();
    const chunks = [];
    let got = 0;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
      got += value.length;
      onProgress && onProgress(Math.min(1, got / total));
    }
    const bytes = new Uint8Array(got);
    let o = 0;
    for (const ch of chunks) { bytes.set(ch, o); o += ch.length; }
    const { default: factory } = await import('../dist/kozmo.js');
    const mod = await factory({ wasmBinary: bytes.buffer });
    return new Core(mod);
  }
  start(body, inOrbit = true) { return JSON.parse(this._new(body, inOrbit ? 1 : 0)); }
  tick(dt) { this._tick(dt); }
  state() { return JSON.parse(this._state()); }
  cmd(obj) { return JSON.parse(this._cmd(JSON.stringify(obj))); }
  buildings() { return JSON.parse(this._buildings()).buildings || []; }
  environment() { return JSON.parse(this._env()); }
  management() { return JSON.parse(this._mgmt()); }
  porkchop(target, span = 780, step = 20) { return JSON.parse(this._pork(target, span, step)); }
  save() { return JSON.parse(this._save()); }
  loadSave(text) { return JSON.parse(this._load(text)); }
  height(x, y) { return this._height(x, y); }
  mesh() {
    const m = this.m;
    const nv = m._kz_mesh_vertex_count(), ni = m._kz_mesh_index_count();
    const pv = m._kz_mesh_vertices() >> 2, pn = m._kz_mesh_normals() >> 2, pi = m._kz_mesh_indices() >> 2;
    return {
      positions: m.HEAPF32.slice(pv, pv + nv * 3),
      normals: m.HEAPF32.slice(pn, pn + nv * 3),
      indices: m.HEAPU32.slice(pi, pi + ni),
    };
  }
}
