#include "kozmo/replay.hpp"

namespace kozmo::replay {

const char* to_string(Op o) {
    switch (o) {
        case Op::Advance: return "advance";
        case Op::StartResearch: return "research";
        case Op::LaunchKit: return "launch_kit";
        case Op::FoundOutpost: return "found_outpost";
        case Op::BuildModule: return "build";
        case Op::Trade: return "trade";
    }
    return "?";
}

std::uint64_t fnv1a(const std::string& s) {
    std::uint64_t h = 0xcbf29ce484222325ull;
    for (unsigned char c : s) {
        h ^= c;
        h *= 0x100000001b3ull;
    }
    return h;
}

std::uint64_t state_hash(const Game& g) { return fnv1a(g.save()); }

Recorder::Recorder(std::uint64_t seed, std::string agency, double credits) : seed_(seed), agency_(std::move(agency)), credits_(credits), game_(seed) {
    game_.new_game(agency_, credits_);
}

Status Recorder::exec(Game& g, const Command& c) {
    switch (c.op) {
        case Op::Advance:
            if (c.a <= 0 || c.a > 3650) return make_error(ErrorCode::InvalidArgument, "Gün aralığı 0-3650");
            g.advance(c.a);
            return ok_status();
        case Op::StartResearch: return g.research().start(c.s1);
        case Op::LaunchKit: {
            const Payload kit = standard_colony_kit();
            auto r = g.launch(preset_heavy_rocket(c.s1, payload_mass_t(kit) + 0.5, static_cast<int>(kit.crew.size())), kit);
            if (!r) return r.error();
            return ok_status();
        }
        case Op::FoundOutpost: return g.found_outpost(c.s1, vertical_slice_outpost());
        case Op::BuildModule: {
            const int t = static_cast<int>(c.a);
            if (t < 0 || t > static_cast<int>(colony::ModuleType::WaterRecycler)) return make_error(ErrorCode::InvalidArgument, "Geçersiz modül");
            return g.build_module(c.s1, static_cast<colony::ModuleType>(t));
        }
        case Op::Trade: {
            auto r = g.trade(c.s1, c.s2, c.a, c.flag);
            if (!r) return r.error();
            return ok_status();
        }
    }
    return make_error(ErrorCode::InvalidArgument, "Bilinmeyen komut");
}

Status Recorder::apply(const Command& c) {
    log_.push_back(c);
    return exec(game_, c);
}

json::Value Recorder::to_json() const {
    json::Value v = json::Value::object();
    v.set("seed", std::to_string(seed_));
    v.set("agency", agency_);
    v.set("credits", credits_);
    json::Value a = json::Value::array();
    for (const auto& c : log_) {
        json::Value o = json::Value::object();
        o.set("op", static_cast<int>(c.op));
        o.set("a", c.a);
        o.set("s1", c.s1);
        o.set("s2", c.s2);
        o.set("flag", c.flag);
        a.push(o);
    }
    v.set("log", a);
    v.set("hash", std::to_string(hash()));
    return v;
}

Result<Recorder> Recorder::from_json(const json::Value& v) {
    const std::string seed_s = v["seed"].as_string();
    std::uint64_t seed = 0;
    for (char ch : seed_s) {
        if (ch < '0' || ch > '9') return make_error(ErrorCode::Parse, "Geçersiz tohum");
        seed = seed * 10 + static_cast<std::uint64_t>(ch - '0');
    }
    Recorder r(seed, v["agency"].as_string(), v["credits"].as_number());
    for (const auto& o : v["log"].as_array()) {
        const int op = o["op"].as_int(-1);
        if (op < 0 || op > static_cast<int>(Op::Trade)) return make_error(ErrorCode::Parse, "Geçersiz komut kaydı");
        (void)r.apply({static_cast<Op>(op), o["a"].as_number(), o["s1"].as_string(), o["s2"].as_string(), o["flag"].as_bool()});
    }
    if (v.has("hash") && v["hash"].as_string() != std::to_string(r.hash()))
        return make_error(ErrorCode::Parse, "Senkron hatası: tekrar oynatma karması kayıttakiyle eşleşmiyor");
    return r;
}

std::uint64_t replay(std::uint64_t seed, const std::string& agency, double credits, const std::vector<Command>& log) {
    Recorder r(seed, agency, credits);
    for (const auto& c : log) (void)r.apply(c);
    return r.hash();
}

}  // namespace kozmo::replay
