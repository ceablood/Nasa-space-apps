// KOZMOGENİS web köprüsü: KozmoCore (Unreal sürümüyle AYNI C++ çekirdek) WebAssembly'ye derlenir; tarayıcıdaki
// Three.js istemcisi bu C arayüzünü çağırır. Komutlar ve durum JSON metniyle, arazi mesh'i Float32 tamponla taşınır.
// Bu katman Unreal'daki UKozmoSubsystem + AKozmoExpeditionScene'in karşılığıdır.
#include <cstdint>
#include <cstring>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "kozmo/agency.hpp"
#include "kozmo/civ.hpp"
#include "kozmo/contracts.hpp"
#include "kozmo/crew.hpp"
#include "kozmo/defense.hpp"
#include "kozmo/dialogue.hpp"
#include "kozmo/nav.hpp"
#include "kozmo/nova.hpp"
#include "kozmo/planner.hpp"
#include "kozmo/progression.hpp"
#include "kozmo/satellites.hpp"
#include "kozmo/savefmt.hpp"
#include "kozmo/settings.hpp"
#include "kozmo/solar.hpp"
#include "kozmo/station.hpp"
#include "kozmo/terrain.hpp"
#include "kozmo/world.hpp"

#ifdef __EMSCRIPTEN__
#include <emscripten/emscripten.h>
#define KZ_API extern "C" EMSCRIPTEN_KEEPALIVE
#else
#define KZ_API extern "C"
#endif

using namespace kozmo;
using json::Value;

namespace {

struct Session {
    std::unique_ptr<Game> game;
    std::unique_ptr<world::Expedition> exp;
    std::unique_ptr<nova::Nova> nova;
    std::optional<dialogue::Conversation> conv;
    terrain::Heightmap terrain;
    agency::Base base;
    contracts::Board board;
    sats::Fleet fleet;
    crew::Roster roster;
    civ::Civilization civ;
    std::unique_ptr<station::Station> station;
    progress::Tracker achievements;
    progress::Tutorial tutorial;
    progress::News news;
    settings::Settings settings;
    Rng rng{20300101};
    double last_day = 0;
    std::string body;
    bool walked = false, reached_orbit = false, docked = false, landed_moon = false, landed_mars = false, built = false;
    std::vector<float> mesh_v, mesh_n;
    std::vector<std::uint32_t> mesh_t;
};

Session* S = nullptr;
std::string g_out;

const char* out(const Value& v) {
    g_out = v.dump();
    return g_out.c_str();
}

Value okv(const std::string& msg = "") {
    Value v = Value::object();
    v.set("ok", true);
    v.set("msg", msg);
    return v;
}
Value errv(const std::string& msg) {
    Value v = Value::object();
    v.set("ok", false);
    v.set("msg", msg);
    return v;
}
template <class R>
Value from(const R& r, const std::string& okmsg = "") {
    return r.ok() ? okv(okmsg) : errv(r.error().message);
}

void manage_daily() {
    Game& g = *S->game;
    const double day = g.day();
    if (day - S->last_day < 1.0) return;
    const double dd = day - S->last_day;
    for (const auto& m : S->base.advance(day, g.wallet())) S->news.report(m, day);
    (void)S->board.expire(day, g.wallet());
    S->board.refresh(day, S->base.capabilities().contract_slots, S->rng);
    const double solar = solar::density_factor(solar::year_from_game_day(day));
    const double inc = S->fleet.advance(dd, solar, S->rng);
    if (inc > 0) g.wallet().earn(inc, "Uydu geliri", day);
    if (S->station) (void)S->station->advance_days(dd, solar);
    (void)S->civ.update(g);
    (void)S->roster.train(8.0 * dd * S->base.capabilities().training_speed);
    S->roster.rest(16.0 * dd);
    S->last_day = day;
}

void achievements_tick() {
    progress::Snapshot s;
    const Game& g = *S->game;
    s.colonies = static_cast<int>(g.colonies().size());
    for (const auto& [id, c] : g.colonies()) s.population += c.population();
    s.missions = static_cast<int>(g.missions().size());
    s.research_done = static_cast<int>(g.research().unlocked_list().size());
    for (const auto& c : S->fleet.constellations()) s.satellites += c.active;
    s.max_base = S->base.max_base();
    s.credits = g.wallet().balance();
    s.landed_moon = S->landed_moon;
    s.landed_mars = S->landed_mars;
    s.reached_orbit = S->reached_orbit;
    s.docked = S->docked;
    s.walked_on_surface = S->walked;
    s.built_module = S->built;
    if (S->exp) s.quests_done = static_cast<int>(S->exp->completed_quests().size());
    for (const auto& k : S->achievements.update(s))
        for (const auto& a : progress::achievements())
            if (a.key == k) S->news.report("BAŞARIM: " + a.title, g.day(), a.description);
}

void build_terrain() {
    auto env = challenge::body_environment(S->body);
    if (!env) return;
    S->terrain = terrain::Heightmap::generate(env.value(), 4242, 1600.0, 8.0);
    // koloni ve iniş alanı düzleştirilir (inşaat alanı hazırlığı)
    S->terrain.flatten(0, 0, 95.0);
    if (const auto* pad = S->exp->settlement().find(life::District::LandingPad)) S->terrain.flatten(pad->x, pad->y, 40.0);
    else S->terrain.flatten(130, 0, 40.0);
    const auto m = S->terrain.mesh(2);
    S->mesh_v = m.vertices;
    S->mesh_n = m.normals;
    S->mesh_t.assign(m.triangles.begin(), m.triangles.end());
}

Value buildings_json() {
    Value a = Value::array();
    for (const auto& b : S->exp->settlement().buildings()) {
        Value o = Value::object();
        o.set("id", b.id);
        o.set("name", b.name);
        o.set("district", static_cast<int>(b.district));
        o.set("x", b.x);
        o.set("y", b.y);
        o.set("w", b.w);
        o.set("d", b.d);
        o.set("h", b.h);
        o.set("dx", b.door_x);
        o.set("dy", b.door_y);
        o.set("built", b.built);
        o.set("floors", b.floors);
        o.set("elevator", b.elevator);
        o.set("pressurized", b.pressurized);
        o.set("z", S->terrain.side() ? S->terrain.height(b.x, b.y) : 0.0);
        Value rooms = Value::array();
        for (const auto& r : b.rooms) {
            Value ro = Value::object();
            ro.set("name", r.name);
            ro.set("floor", r.floor);
            Value items = Value::array();
            for (const auto& it : r.items) {
                Value io = Value::object();
                io.set("id", it.id);
                io.set("name", it.name);
                items.push(io);
            }
            ro.set("items", items);
            rooms.push(ro);
        }
        o.set("rooms", rooms);
        a.push(o);
    }
    return a;
}

}  // namespace

KZ_API const char* kz_version() { return "KOZMOGENİS web 1.0 (KozmoCore)"; }

// body: "moon" (8 kişilik koloni), "mars" (kuruluş senaryosu), "titan" (buz araştırması)
KZ_API const char* kz_new(const char* body_c, int in_orbit) {
    delete S;
    S = new Session();
    S->body = body_c ? body_c : "moon";
    S->game = std::make_unique<Game>(41);
    S->game->new_game("KOZMOGENİS", 3e6);
    for (const char* k : {"cryo", "methalox"}) {
        (void)S->game->research().start(k);
        S->game->research().add_points(1e6, nullptr);
    }
    if (S->body == "moon") {
        auto st = S->game->found_outpost("moon", vertical_slice_outpost());
        if (!st) return out(errv(st.error().message));
        S->game->advance(9.375);   // Ay sabahı, mürettebat 09:00
    }
    craft::Spacecraft c = craft::preset(S->body == "mars" ? "mars_lander" : "lander");
    if (S->body == "titan") (void)c.install("science_lab");
    S->exp = std::make_unique<world::Expedition>(*S->game, S->body, c);
    auto st = S->exp->init(in_orbit != 0);
    if (!st) return out(errv(st.error().message));
    if (S->body == "titan") S->exp->player().eq.thermal_suit = true;
    S->nova = std::make_unique<nova::Nova>(*S->game);
    S->nova->attach(S->exp.get());
    S->station = std::make_unique<station::Station>(station::iss_like());
    for (const char* n : {"Ayşe Yıldız", "Burak Demir", "Cemre Kaya", "Deniz Aksoy"}) (void)S->roster.hire(n, S->rng);
    S->board.refresh(S->game->day(), S->base.capabilities().contract_slots, S->rng);
    S->last_day = S->game->day();
    build_terrain();
    S->news.report("Sefer başladı: " + S->exp->env().name, S->game->day());
    Value v = okv("Sefer hazır");
    v.set("buildings", buildings_json());
    return out(v);
}

KZ_API void kz_tick(double dt_s) {
    if (!S || !S->exp) return;
    const auto before = S->exp->craft().phase();
    const bool docked_before = S->exp->craft().docking().docked;
    S->exp->tick(dt_s);
    const auto after = S->exp->craft().phase();
    if (before != after) {
        if (after == craft::FlightPhase::Landed) {
            if (S->body == "moon") S->landed_moon = true;
            if (S->body == "mars") S->landed_mars = true;
            S->tutorial.on("landed");
            S->news.report(S->body == "moon" ? "landed_moon" : (S->body == "mars" ? "landed_mars" : "İniş başarılı"), S->game->day());
        }
        if (after == craft::FlightPhase::Orbit) {
            S->reached_orbit = true;
            S->news.report("orbit", S->game->day());
        }
    }
    if (!docked_before && S->exp->craft().docking().docked) {
        S->docked = true;
        S->news.report("docked", S->game->day());
    }
    if (S->exp->player().mode == world::PlayerMode::OnFoot) S->walked = true;
    for (const auto& p : S->exp->construction().projects()) S->built |= p.state == build::State::Done;
    manage_daily();
    static double acc = 0;
    acc += dt_s;
    if (acc > 5) {
        acc = 0;
        achievements_tick();
    }
}

KZ_API float* kz_mesh_vertices() { return S ? S->mesh_v.data() : nullptr; }
KZ_API float* kz_mesh_normals() { return S ? S->mesh_n.data() : nullptr; }
KZ_API std::uint32_t* kz_mesh_indices() { return S ? S->mesh_t.data() : nullptr; }
KZ_API int kz_mesh_vertex_count() { return S ? static_cast<int>(S->mesh_v.size() / 3) : 0; }
KZ_API int kz_mesh_index_count() { return S ? static_cast<int>(S->mesh_t.size()) : 0; }
KZ_API double kz_height(double x, double y) { return S && S->terrain.side() ? S->terrain.height(x, y) : 0.0; }

KZ_API const char* kz_state() {
    if (!S || !S->exp) return out(errv("Oturum yok"));
    const auto& e = *S->exp;
    const auto& c = e.craft();
    const auto in = c.instruments();
    Value v = Value::object();
    v.set("ok", true);
    v.set("body", S->body);
    v.set("env", e.env().name);
    v.set("day", S->game->day());
    v.set("hours", e.hours());
    v.set("local_hour", e.local_hour());
    v.set("crew_hour", e.crew_hour());
    v.set("credits", S->game->wallet().balance());
    v.set("surface_c", challenge::surface_temp_c(e.env(), e.local_hour()));
    v.set("gravity", e.env().gravity_ms2);
    v.set("pressure", e.env().pressure_kpa);
    // araç ve kokpit
    Value cr = Value::object();
    cr.set("model", c.model());
    cr.set("phase", craft::to_string(c.phase()));
    cr.set("phase_id", static_cast<int>(c.phase()));
    cr.set("alt", in.altitude_m);
    cr.set("speed", in.speed_ms);
    cr.set("vv", in.vertical_ms);
    cr.set("vh", in.horizontal_ms);
    cr.set("downrange", c.downrange());
    cr.set("remaining", c.has_landing_target() ? c.landing_target() - c.downrange() : 0.0);
    cr.set("fuel", in.fuel_t);
    cr.set("fuel_frac", in.fuel_fraction);
    cr.set("o2_days", in.oxygen_days);
    cr.set("engine_k", in.engine_temp_k);
    cr.set("cabin_kpa", in.cabin_pressure_kpa);
    cr.set("power_kw", in.power_kw_net);
    cr.set("battery", in.battery_fraction);
    cr.set("shield", in.shield_fraction);
    cr.set("hull", in.hull_fraction);
    cr.set("engine", in.engine_fraction);
    cr.set("nav", in.navigation);
    cr.set("radar", in.radar.empty() ? std::string("-") : in.radar.front());
    cr.set("engines_on", in.engines_on);
    cr.set("seated", in.seated);
    cr.set("mode", craft::to_string(in.mode));
    cr.set("throttle", in.throttle);
    cr.set("cockpit", static_cast<int>(c.cockpit()));
    cr.set("tier", craft::to_string(c.tier()));
    cr.set("lights", c.cabin_lights());
    cr.set("decel", c.decelerator_deployed());
    cr.set("heat", c.max_heat_flux());
    cr.set("touchdown", c.touchdown_speed());
    Value dk = Value::object();
    dk.set("active", c.docking().active);
    dk.set("range", c.docking().range_m);
    dk.set("closing", c.docking().closing_ms);
    dk.set("docked", c.docking().docked);
    cr.set("docking", dk);
    Value warn = Value::array();
    for (const auto& w : c.warnings()) {
        Value o = Value::object();
        o.set("msg", w.message);
        o.set("proc", w.procedure);
        o.set("sev", w.severity);
        warn.push(o);
    }
    cr.set("warnings", warn);
    v.set("craft", cr);
    // oyuncu
    const auto& p = e.player();
    Value pl = Value::object();
    pl.set("mode", world::to_string(p.mode));
    pl.set("mode_id", static_cast<int>(p.mode));
    pl.set("x", p.x);
    pl.set("y", p.y);
    pl.set("building", p.building);
    pl.set("floor", p.floor);
    pl.set("health", p.body.health);
    pl.set("o2_h", p.body.suit_o2_h);
    pl.set("dose", p.body.dose_msv);
    pl.set("alive", p.body.alive);
    pl.set("cause", p.body.last_cause);
    pl.set("samples", p.samples);
    pl.set("thermal", p.eq.thermal_suit);
    v.set("player", pl);
    // NPC'ler
    Value np = Value::array();
    if (const colony::Colony* col = e.colony()) {
        for (const auto& n : e.society().npcs()) {
            const colony::Colonist* k = nullptr;
            for (const auto& x : col->colonists())
                if (x.id == n.id) k = &x;
            if (!k) continue;
            Value o = Value::object();
            o.set("id", n.id);
            o.set("name", k->name);
            o.set("job", colony::job_name(k->job));
            o.set("job_id", static_cast<int>(k->job));
            o.set("x", n.x);
            o.set("y", n.y);
            o.set("intent", life::to_string(n.intent));
            o.set("reason", n.reason);
            o.set("at", n.at);
            o.set("lod", static_cast<int>(n.lod));
            o.set("hunger", k->needs.hunger);
            o.set("fatigue", k->needs.fatigue);
            o.set("morale", k->needs.morale);
            o.set("health", k->needs.health);
            np.push(o);
        }
        v.set("colony", e.colony_report());
        v.set("population", col->population());
    }
    v.set("npcs", np);
    Value near = Value::array();
    for (int id : e.npcs_here()) near.push(id);
    v.set("near_npcs", near);
    // hava, görevler, inşaat, günlük
    Value we = Value::array();
    for (const auto& w : e.weather()) {
        Value o = Value::object();
        o.set("kind", challenge::to_string(w.kind));
        o.set("kind_id", static_cast<int>(w.kind));
        o.set("visibility", w.visibility);
        o.set("solar", w.solar_factor);
        we.push(o);
    }
    v.set("weather", we);
    Value ts = Value::array();
    for (const auto& t : e.tasks()) ts.push(t);
    v.set("tasks", ts);
    v.set("quests", e.quests().summary());
    Value pr = Value::array();
    for (const auto& q : e.construction().projects()) {
        Value o = Value::object();
        o.set("module", q.reinforce ? std::string("Güçlendirme") : std::string(colony::module_name(q.module)));
        o.set("progress", q.progress());
        o.set("state", build::to_string(q.state));
        o.set("site", build::site_district(q.module));
        o.set("reinforce", q.reinforce);
        pr.push(o);
    }
    v.set("construction", pr);
    Value lg = Value::array();
    const auto& L = e.log();
    for (std::size_t i = L.size() > 8 ? L.size() - 8 : 0; i < L.size(); ++i) lg.push(L[i]);
    v.set("log", lg);
    v.set("water_found", e.water_found());
    v.set("has_colony", e.colony() != nullptr);
    v.set("tutorial", S->tutorial.hint());
    v.set("achievements", S->achievements.count());
    Value news = Value::array();
    for (const auto& n : S->news.latest(4)) {
        Value o = Value::object();
        o.set("h", n.headline);
        o.set("b", n.body);
        o.set("real", n.real);
        news.push(o);
    }
    v.set("news", news);
    return out(v);
}

KZ_API const char* kz_buildings() {
    if (!S || !S->exp) return out(errv("Oturum yok"));
    Value v = okv();
    v.set("buildings", buildings_json());
    return out(v);
}

KZ_API const char* kz_environment() {
    if (!S || !S->exp) return out(errv("Oturum yok"));
    Value v = okv(S->exp->environment_report());
    const auto& e = S->exp->env();
    v.set("pressure", e.pressure_kpa);
    v.set("class", challenge::to_string(e.cls));
    v.set("dust", e.dust_level);
    v.set("radius_km", e.radius_km);
    v.set("terrain_size", S->terrain.size());
    v.set("pits", static_cast<int>(S->terrain.pits().size()));
    v.set("craters", static_cast<int>(S->terrain.craters().size()));
    Value sites = Value::array();
    for (const auto& s : S->terrain.find_landing_sites(20, 12, 1.5, 3)) {
        Value o = Value::object();
        o.set("x", s.x);
        o.set("y", s.y);
        o.set("z", s.height_m);
        o.set("reason", s.reason);
        sites.push(o);
    }
    v.set("sites", sites);
    Value pits = Value::array();
    for (const auto& p : S->terrain.pits()) {
        Value o = Value::object();
        o.set("x", p.x);
        o.set("y", p.y);
        o.set("d", p.diameter_m);
        o.set("len", p.cave_length_m);
        pits.push(o);
    }
    v.set("pit_list", pits);
    return out(v);
}

// komut: {"op": "...", ...}
KZ_API const char* kz_cmd(const char* text) {
    if (!S || !S->exp) return out(errv("Oturum yok: önce sefer başlat"));
    auto pj = json::parse(text ? text : "{}");
    if (!pj) return out(errv("Geçersiz komut"));
    const Value& a = pj.value();
    const std::string op = a["op"].as_string();
    auto& e = *S->exp;
    auto& c = e.craft();
    if (op == "sit") {
        auto st = e.sit();
        if (st) S->tutorial.on("sit");
        return out(from(st, "Kokpitte oturuyorsun"));
    }
    if (op == "stand") return out(from(e.stand(), "Ayağa kalktın"));
    if (op == "descent") {
        auto st = e.begin_descent();
        if (st) S->tutorial.on("descent");
        return out(from(st, "İniş başladı"));
    }
    if (op == "engines") return out(from(c.set_engines(a["on"].as_bool(!c.instruments().engines_on)), "Motorlar"));
    if (op == "mode") {
        const int m = a["mode"].as_int(0);
        if (m < 0 || m > 5) return out(errv("Geçersiz mod"));
        return out(from(c.set_mode(static_cast<craft::FlightMode>(m)), craft::to_string(static_cast<craft::FlightMode>(m))));
    }
    if (op == "throttle") {
        c.set_throttle(a["value"].as_number());
        return out(okv());
    }
    if (op == "pitch") {
        c.set_pitch_deg(a["value"].as_number(90));
        return out(okv());
    }
    if (op == "lights") {
        c.set_cabin_lights((c.cabin_lights() + 1) % 4);
        return out(okv("Kabin ışığı " + std::to_string(c.cabin_lights())));
    }
    if (op == "procedure") {
        auto w = c.warnings();
        if (w.empty()) return out(okv("Etkin arıza yok"));
        auto st = c.apply_procedure(w.front().fault);
        return out(st ? okv("Prosedür uygulandı: " + w.front().procedure) : errv(st.error().message));
    }
    if (op == "exit") {
        auto st = e.exit_craft();
        if (st) S->tutorial.on("exit");
        return out(from(st, "Araçtan çıktın"));
    }
    if (op == "enter_craft") return out(from(e.enter_craft(), "Araca bindin"));
    if (op == "pos") {
        e.set_player_position(a["x"].as_number(), a["y"].as_number());
        return out(okv());
    }
    if (op == "enter") {
        auto st = e.enter_building(a["id"].as_string());
        if (st) S->tutorial.on("enter");
        return out(from(st, "İçeri girdin"));
    }
    if (op == "leave") return out(from(e.leave_building(), "Dışarı çıktın"));
    if (op == "floor") {
        auto r = e.change_floor(a["floor"].as_int(), a["elevator"].as_bool(true));
        return out(r ? okv(r.value()) : errv(r.error().message));
    }
    if (op == "use") {
        auto r = e.use(a["id"].as_string());
        if (r) S->tutorial.on("use");
        return out(r ? okv(r.value()) : errv(r.error().message));
    }
    if (op == "sample") {
        auto st = e.collect_sample();
        if (st) S->tutorial.on("sample");
        return out(from(st, "Numune toplandı"));
    }
    if (op == "talk_start") {
        auto r = e.converse(a["id"].as_int());
        if (!r) return out(errv(r.error().message));
        S->conv.emplace(std::move(r.value()));
        S->tutorial.on("talk");
        Value v = okv(S->conv->text());
        Value o = Value::array();
        for (const auto& s : S->conv->options()) o.push(s);
        v.set("options", o);
        return out(v);
    }
    if (op == "talk_choose") {
        if (!S->conv || !S->conv->active()) return out(errv("Konuşma yok"));
        auto r = S->conv->choose(static_cast<std::size_t>(a["index"].as_int()));
        if (!r) return out(errv(r.error().message));
        Value v = okv(r.value());
        Value o = Value::array();
        if (S->conv->active())
            for (const auto& s : S->conv->options()) o.push(s);
        v.set("options", o);
        v.set("active", S->conv->active());
        return out(v);
    }
    if (op == "nova") {
        auto rep = S->nova->ask(a["text"].as_string());
        S->tutorial.on("nova");
        Value v = okv(rep.text);
        Value src = Value::array();
        for (const auto& s : rep.sources) src.push(s);
        v.set("sources", src);
        v.set("pending", rep.pending_action.has_value());
        return out(v);
    }
    if (op == "scan_water") {
        auto r = e.scan_water();
        return out(r ? okv(r.value()) : errv(r.error().message));
    }
    if (op == "found") {
        auto st = e.found_colony();
        if (st) {
            build_terrain();
            S->news.report("colony_founded", S->game->day());
        }
        Value v = from(st, "Koloni kuruldu");
        if (st) v.set("buildings", buildings_json());
        return out(v);
    }
    if (op == "build") {
        const int m = a["module"].as_int(-1);
        if (m < 0 || m > static_cast<int>(colony::ModuleType::WaterRecycler)) return out(errv("Geçersiz modül"));
        auto r = e.build(static_cast<colony::ModuleType>(m));
        return out(r ? okv("İnşaat başladı") : errv(r.error().message));
    }
    if (op == "reinforce") {
        auto r = e.reinforce();
        return out(r ? okv("Güçlendirme başladı") : errv(r.error().message));
    }
    if (op == "take_off") return out(from(e.take_off(a["alt"].as_number(15000)), "Kalkış"));
    if (op == "dock") {
        (void)c.set_target("istasyon Kapı");
        (void)c.set_mode(craft::FlightMode::DockingAssist);
        return out(from(c.begin_docking(a["range"].as_number(500), 0.0), "Kenetlenme yaklaşması başladı"));
    }
    if (op == "analyze_onboard") {
        auto r = e.analyze_onboard();
        return out(r ? okv(r.value()) : errv(r.error().message));
    }
    if (op == "quest") {
        auto r = e.accept_quest(a["key"].as_string());
        return out(r ? okv("Görev alındı") : errv(r.error().message));
    }
    if (op == "fail_power") {
        e.fail_power();
        return out(okv("Enerji tesisi arızalandı"));
    }
    if (op == "thermal") {
        e.player().eq.thermal_suit = !e.player().eq.thermal_suit;
        return out(okv(e.player().eq.thermal_suit ? "Termal giysi giyildi" : "Termal giysi çıkarıldı"));
    }
    // --- yönetim
    if (op == "upgrade") {
        const int f = a["facility"].as_int(-1);
        if (f < 0 || f >= agency::kFacilityCount) return out(errv("Geçersiz tesis"));
        return out(from(S->base.upgrade(static_cast<agency::Facility>(f), S->game->wallet(), S->game->day()), "Yükseltme başladı"));
    }
    if (op == "accept_contract") return out(from(S->board.accept(a["id"].as_int(), S->base.capabilities().concurrent_missions), "Sözleşme kabul edildi"));
    if (op == "policy") {
        const int p = a["policy"].as_int(0);
        if (p < 0 || p > static_cast<int>(civ::Policy::Expansion)) return out(errv("Geçersiz politika"));
        (void)S->civ.set_policy(static_cast<civ::Policy>(p));
        return out(okv(civ::describe(S->civ.policy())));
    }
    if (op == "plan") {
        auto r = planner::plan(*S->game, (a.has("target") ? a["target"].as_string() : std::string("mars")), a["crew"].as_int(4), 10, 30, true);
        return out(r ? okv(r.value().summary()) : errv(r.error().message));
    }
    if (op == "settings") {
        // ayarlar çekirdek doğrulayıcısından geçer (aralık dışı değerler sınırlanır)
        if (a.has("value")) {
            auto r = settings::Settings::from_json(a["value"]);
            if (!r) return out(errv(r.error().message));
            S->settings = r.value();
            (void)S->settings.validate();
        }
        Value v = okv();
        v.set("settings", S->settings.to_json());
        return out(v);
    }
    if (op == "time") return out(okv());
    return out(errv("Bilinmeyen komut: " + op));
}

KZ_API const char* kz_management() {
    if (!S) return out(errv("Oturum yok"));
    Value v = okv();
    const auto cap = S->base.capabilities();
    Value fac = Value::array();
    for (int i = 0; i < agency::kFacilityCount; ++i) {
        const auto f = static_cast<agency::Facility>(i);
        const auto& sp = agency::spec(f);
        Value o = Value::object();
        o.set("id", i);
        o.set("name", sp.name);
        o.set("desc", sp.description);
        o.set("level", S->base.level(f));
        o.set("max", sp.max_level);
        o.set("next_cost", S->base.level(f) < sp.max_level ? sp.upgrade_cost[static_cast<std::size_t>(S->base.level(f) + 1)] : 0.0);
        fac.push(o);
    }
    v.set("facilities", fac);
    Value capv = Value::object();
    capv.set("max_liftoff_t", cap.max_liftoff_t);
    capv.set("missions", cap.concurrent_missions);
    capv.set("research", cap.research_speed);
    capv.set("comms_mkm", cap.comms_range_km / 1e6);
    capv.set("nova", cap.nova_level);
    capv.set("upkeep", S->base.upkeep_per_day());
    v.set("caps", capv);
    Value con = Value::array();
    for (const auto& c : S->board.contracts()) {
        if (c.status != contracts::Status_::Offered && c.status != contracts::Status_::Accepted) continue;
        Value o = Value::object();
        o.set("id", c.id);
        o.set("client", c.client);
        o.set("dest", contracts::to_string(c.dest));
        o.set("t", c.payload_t);
        o.set("reward", c.reward);
        o.set("deadline", c.deadline_day);
        o.set("status", contracts::to_string(c.status));
        con.push(o);
    }
    v.set("contracts", con);
    v.set("reputation", S->board.reputation());
    const auto m = S->civ.measure(*S->game);
    Value cv = Value::object();
    cv.set("era", civ::to_string(m.era));
    cv.set("population", m.population);
    cv.set("stability", m.stability);
    cv.set("happiness", m.happiness);
    cv.set("food_days", m.food_days);
    cv.set("policy", civ::to_string(S->civ.policy()));
    v.set("civ", cv);
    Value crew = Value::array();
    for (const auto& x : S->roster.astronauts()) {
        Value o = Value::object();
        o.set("name", x.name);
        o.set("rank", x.rank());
        o.set("training", x.training);
        o.set("dose", x.dose_msv);
        crew.push(o);
    }
    v.set("crew", crew);
    if (S->station) {
        Value st = Value::object();
        st.set("name", S->station->name());
        st.set("alt_km", S->station->altitude() / 1000.0);
        st.set("period", S->station->period_min());
        st.set("supplies", S->station->days_of_supplies());
        v.set("station", st);
    }
    Value neo = Value::array();
    for (const auto& x : defense::catalog()) {
        Value o = Value::object();
        o.set("name", x.name);
        o.set("d", x.diameter_m());
        o.set("e", x.energy_mt());
        o.set("p", x.probability);
        o.set("palermo", x.probability > 0 ? defense::palermo(x.probability, x.energy_mt(), x.years_to_event) : -99.0);
        o.set("torino", defense::torino(x.probability, x.energy_mt(), x.years_to_event));
        o.set("real", x.real);
        o.set("note", x.note);
        neo.push(o);
    }
    v.set("neo", neo);
    v.set("achievements", S->achievements.count());
    v.set("achievements_total", static_cast<int>(progress::achievements().size()));
    return out(v);
}

// Lambert porkchop ızgarası (fırlatma penceresi paneli için): C3 matrisi
KZ_API const char* kz_porkchop(const char* target, double span, double step) {
    auto p = nav::porkchop("earth", target ? target : "mars", S && S->game ? S->game->day() : 0.0, span, step, 120, 400, 10);
    if (!p) return out(errv(p.error().message));
    Value v = okv();
    Value rows = Value::array();
    for (const auto& r : p.value().c3) {
        Value row = Value::array();
        for (double x : r) row.push(x);
        rows.push(row);
    }
    v.set("c3", rows);
    v.set("depart0", p.value().depart_days.front());
    v.set("step", step);
    v.set("tof0", 120);
    v.set("tof_step", 10);
    v.set("best_depart", p.value().best.depart_day);
    v.set("best_tof", p.value().best.tof_days);
    v.set("best_c3", p.value().best.c3_km2s2);
    return out(v);
}

KZ_API const char* kz_save() {
    if (!S || !S->exp) return out(errv("Oturum yok"));
    Value p = Value::object();
    p.set("body", S->body);
    p.set("game", json::parse(S->game->save()).value());
    p.set("expedition", S->exp->to_json());
    p.set("agency", S->base.to_json());
    p.set("satellites", S->fleet.to_json());
    p.set("contracts", S->board.to_json());
    p.set("crew", S->roster.to_json());
    p.set("civ", S->civ.to_json());
    Value prog = Value::object();
    prog.set("achievements", S->achievements.to_json());
    prog.set("tutorial", S->tutorial.to_json());
    p.set("progress", prog);
    p.set("settings", S->settings.to_json());
    Value v = okv();
    v.set("data", savefmt::wrap(p));
    return out(v);
}

KZ_API const char* kz_load(const char* text) {
    auto L = savefmt::unwrap(text ? text : "");
    if (!L) return out(errv(L.error().message));
    const Value& p = L.value().payload;
    const std::string body = p.has("body") ? p["body"].as_string() : std::string("moon");
    const char* r = kz_new(body.c_str(), 0);
    (void)r;
    if (!S) return out(errv("Oturum kurulamadı"));
    auto st = S->game->load(p["game"].dump());
    if (!st) return out(errv(st.error().message));
    // sefer nesnesini yeniden kur (yüklenen oyuna bağlı)
    S->exp = std::make_unique<world::Expedition>(*S->game, body, craft::preset(body == "mars" ? "mars_lander" : "lander"));
    (void)S->exp->init(false);
    if (p.has("expedition")) {
        auto es = S->exp->from_json(p["expedition"]);
        if (!es) return out(errv(es.error().message));
    }
    S->nova = std::make_unique<nova::Nova>(*S->game);
    S->nova->attach(S->exp.get());
    if (p["agency"].has("levels")) (void)S->base.from_json(p["agency"]);
    if (p["satellites"].has("list")) (void)S->fleet.from_json(p["satellites"]);
    if (p["contracts"].has("list")) (void)S->board.from_json(p["contracts"]);
    if (p.has("crew")) (void)S->roster.from_json(p["crew"]);
    if (p.has("civ")) (void)S->civ.from_json(p["civ"]);
    if (p["progress"].has("achievements")) (void)S->achievements.from_json(p["progress"]["achievements"]);
    if (p.has("settings")) {
        auto r = settings::Settings::from_json(p["settings"]);
        if (r) S->settings = r.value();
    }
    S->last_day = S->game->day();
    build_terrain();
    Value v = okv(L.value().migrated ? "Eski kayıt taşındı ve yüklendi" : "Kayıt yüklendi");
    v.set("buildings", buildings_json());
    return out(v);
}
