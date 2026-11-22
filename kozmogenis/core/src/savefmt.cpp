#include "kozmo/savefmt.hpp"

#include <cstdint>
#include <cstdio>

namespace kozmo::savefmt {

namespace {
std::uint64_t fnv(const std::string& s) {
    std::uint64_t h = 0xcbf29ce484222325ull;
    for (unsigned char c : s) {
        h ^= c;
        h *= 0x100000001b3ull;
    }
    return h;
}
std::string hex(std::uint64_t v) {
    char b[24];
    std::snprintf(b, sizeof(b), "%016llx", static_cast<unsigned long long>(v));
    return b;
}
}  // namespace

std::string wrap(const json::Value& payload) {
    const std::string body = payload.dump();
    json::Value v = json::Value::object();
    v.set("format", kFormat);
    v.set("version", kVersion);
    v.set("checksum", hex(fnv(body)));
    v.set("payload", payload);
    return v.dump();
}

Result<Loaded> unwrap(const std::string& text) {
    auto parsed = json::parse(text);
    if (!parsed) return make_error(ErrorCode::Parse, "Kayıt okunamadı: " + parsed.error().message);
    Loaded L;
    json::Value v = parsed.value();
    if (!v.is_object()) return make_error(ErrorCode::Parse, "Kayıt nesne değil");
    if (!v.has("payload")) {
        // v1: zarfsız, doğrudan Game::save() çıktısı (format/version 1 alanlarıyla ya da onlarsız)
        if (v.has("format") && v["format"].as_string() != kFormat) return make_error(ErrorCode::Parse, "Başka bir oyunun kaydı");
        if (!v.has("day") && !v.has("colonies")) return make_error(ErrorCode::Parse, "Tanınmayan kayıt biçimi");
        json::Value p = json::Value::object();
        p.set("game", v);
        v = json::Value::object();
        v.set("format", kFormat);
        v.set("version", 1);
        v.set("payload", p);
        L.notes.push_back("v1 (zarfsız) kayıt tanındı");
    } else {
        if (v["format"].as_string() != kFormat) return make_error(ErrorCode::Parse, "Başka bir oyunun kaydı");
        if (v.has("checksum") && v["checksum"].as_string() != hex(fnv(v["payload"].dump())))
            return make_error(ErrorCode::Parse, "Sağlama toplamı tutmuyor: kayıt bozuk ya da elle değiştirilmiş");
    }
    L.original_version = v["version"].as_int(1);
    if (L.original_version > kVersion) return make_error(ErrorCode::Parse, "Kayıt daha yeni bir sürümden (v" + std::to_string(L.original_version) + ")");
    json::Value p = v["payload"];
    int ver = L.original_version;
    if (ver < 2) {
        if (!p.has("agency")) p.set("agency", json::Value::object());
        if (!p.has("satellites")) p.set("satellites", json::Value::object());
        if (!p.has("contracts")) p.set("contracts", json::Value::object());
        L.notes.push_back("v1 -> v2: ajans/uydu/sözleşme alanları eklendi");
        ver = 2;
    }
    if (ver < 3) {
        if (!p.has("settings")) p.set("settings", json::Value::object());
        if (!p.has("progress")) p.set("progress", json::Value::object());
        L.notes.push_back("v2 -> v3: ayar ve ilerleme alanları eklendi");
        ver = 3;
    }
    L.migrated = L.original_version != kVersion;
    L.payload = p;
    return L;
}

}  // namespace kozmo::savefmt
