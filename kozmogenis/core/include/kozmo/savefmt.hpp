// KozmoCore — sürümlü kayıt biçimi (V30 §19.3): zarf {format, version, checksum, payload}. Eski sürümler
// adım adım taşınır (v1: yalnız Game kaydı -> v2: ajans/uydu/sözleşme alanları -> v3: ayar ve ilerleme alanları).
// Sağlama toplamı (FNV-1a 64) bozuk/elle değiştirilmiş kayıtları yakalar; oyuncunun izni olmadan kayıt
// değiştirilmez — taşıma yalnız bellekte yapılır, diske yazmak çağıranın kararıdır (NOVA kuralı).
#pragma once

#include <string>
#include <vector>

#include "kozmo/core.hpp"
#include "kozmo/json.hpp"

namespace kozmo::savefmt {

constexpr int kVersion = 3;
constexpr const char* kFormat = "kozmogenis-save";

std::string wrap(const json::Value& payload);             // zarf + sağlama toplamı
struct Loaded {
    json::Value payload;
    int original_version = 0;
    bool migrated = false;
    std::vector<std::string> notes;
};
Result<Loaded> unwrap(const std::string& text);            // doğrula, gerekirse taşı

}  // namespace kozmo::savefmt
