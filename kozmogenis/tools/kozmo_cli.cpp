// KOZMOGENİS — KozmoCore'un terminalde oynanabilir arayüzü.
// Unreal Engine 5 istemcisi aynı Game API'sini sarmalar; bu araç çekirdeğin bağımsız olarak oynanabildiğini
// ve doğru çalıştığını gösterir.  Kullanım:  kozmo_cli            (etkileşimli)
//                                             kozmo_cli --demo     (otomatik uçtan uca oyun, CI testi)
#include <algorithm>
#include <cmath>
#include <ctime>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

#include "kozmo/game.hpp"

using namespace kozmo;
using colony::Job;
using colony::ModuleType;

namespace {

std::string fmt_g(double v) {
    char b[32];
    std::snprintf(b, sizeof b, "%g", v);
    return b;
}

prop::Design preset(const std::string& name, const std::string& target, double payload, int crew) {
    prop::Design d;
    d.target = target;
    d.payload_t = payload;
    d.crew = crew;
    d.land = true;
    if (name == "hafif") {
        d.name = "Hafif (kerosen, 2 kademe)";
        d.stages = {{"kerolox_gg", 9, 411.0, 0.052}, {"kerolox_vac", 1, 107.5, 0.033}};
    } else {
        d.name = "Ağır (metan/LOX + hidrojen iniş kademesi)";
        d.stages = {{"methalox_fc", 33, 3400.0, 0.06}, {"methalox_vac", 3, 1200.0, 0.06}, {"hydrolox_exp", 4, 140.0, 0.10}};
    }
    return d;
}

Payload colony_kit() {
    Payload p;
    p.modules = {ModuleType::Habitat, ModuleType::Greenhouse, ModuleType::Electrolyzer, ModuleType::SolarArray,
                 ModuleType::SolarArray, ModuleType::Lab};
    p.cargo = {{"water", 3.0}, {"oxygen", 0.3}, {"food", 0.3}};
    p.crew = {{"Ada", Job::Farmer}, {"Can", Job::Engineer}, {"Ece", Job::Scientist}};
    return p;
}

void print_report(const prop::Report& r) {
    std::printf("  Kalkış kütlesi %.0f t | itki/ağırlık %.2f | delta-v %.2f / %.2f km/s (pay %+.0f m/s)\n",
                r.liftoff_mass_t, r.liftoff_twr, r.total_dv_ms / 1000, r.required_dv_ms / 1000, r.margin_ms);
    for (std::size_t i = 0; i < r.stages.size(); ++i)
        std::printf("    Kademe %zu: dv %.2f km/s, Isp %.0f s, TWR %.2f, yanma %.0f s\n", i + 1, r.stages[i].dv_ms / 1000,
                    r.stages[i].isp_used_s, r.stages[i].twr, r.stages[i].burn_s);
    std::printf("  Maliyet %.0f bin kredi | başarı olasılığı %%%.1f | %s\n", r.cost_mcr, r.success_p * 100,
                r.feasible ? "UYGUN" : "UYGUN DEĞİL");
    for (const auto& p : r.problems) std::printf("  ! %s\n", p.c_str());
}

void print_status(Game& g) {
    std::printf("\n== %s | Gün %.1f | Bakiye %.0f kredi ==\n", g.agency().c_str(), g.day(), g.wallet().balance());
    const auto& t = g.research();
    std::printf("Araştırma: %s", t.active().empty() ? "(yok)" : t.active().c_str());
    if (!t.active().empty()) std::printf(" %%%.0f", t.progress() * 100);
    std::printf(" | açık: ");
    for (const auto& k : t.unlocked_list()) std::printf("%s ", k.c_str());
    std::printf("\n");
    for (const auto& m : g.missions()) {
        const char* st = m.state == MissionState::InTransit ? "yolda" : (m.state == MissionState::Arrived ? "vardı" : "KAYIP");
        std::printf("Görev #%d -> %s: %s (varış günü %.1f)\n", m.id, m.target.c_str(), st, m.arrive_day);
    }
    for (const auto& [id, c] : g.colonies()) {
        std::printf("Koloni %s: nüfus %d/%d, moral %.2f, güneş %.0f W/m2\n", id.c_str(), c.population(), c.housing(),
                    c.average_morale(), c.solar_flux());
        for (const char* k : {"oxygen", "water", "food", "iron", "battery_kwh"})
            std::printf("   %-12s %.3f\n", k, c.resource(k));
        for (const auto& col : c.colonists())
            if (col.alive)
                std::printf("   - %-10s %-13s %-10s açlık %.2f yorgunluk %.2f moral %.2f sağlık %.2f\n", col.name.c_str(),
                            colony::job_name(col.job), colony::activity_name(col.activity), col.needs.hunger, col.needs.fatigue,
                            col.needs.morale, col.needs.health);
    }
}

void help() {
    std::printf(
        "Komutlar:\n"
        "  durum                         ajans, görevler, koloniler\n"
        "  gezegen <anahtar>             NASA verileri (ör. gezegen mars)\n"
        "  pencere <hedef>               bir sonraki fırlatma penceresi\n"
        "  analiz <hafif|agir> <hedef> <yük_t> <mürettebat>\n"
        "  koloni_kiti <hedef>           ağır roketle 3 kişilik koloni kiti fırlat\n"
        "  arastir <anahtar>             araştırma başlat (cryo, methalox, isru, fission, ion, nuclear, closed_loop, he3_fusion)\n"
        "  bekle <gün>                   zamanı ilerlet\n"
        "  al|sat <piyasa> <emtia> <miktar>\n"
        "  insa <koloni> <modül_no>      yerinde modül inşa (0 yaşam .. 8 klinik)\n"
        "  kaydet <dosya> | yukle <dosya>\n"
        "  cikis\n");
}

int run_demo() {
    Game g(2026);
    int deaths = 0;
    g.bus().subscribe<colony::ColonistDied>([&](const colony::ColonistDied& e) {
        ++deaths;
        std::printf("  [olay] %s hayatını kaybetti: %s\n", e.name.c_str(), e.cause.c_str());
    });
    g.bus().subscribe<ColonyFounded>([](const ColonyFounded& e) { std::printf("  [olay] Koloni kuruldu: %s\n", e.colony.c_str()); });
    g.bus().subscribe<research::ResearchCompleted>([](const research::ResearchCompleted& e) {
        std::printf("  [olay] Araştırma tamamlandı: %s\n", e.key.c_str());
    });
    g.new_game("AETHER", 3e6);
    // başlangıç araştırmaları (demo: Dünya laboratuvarlarında tamamlanmış sayılır)
    for (const char* k : {"cryo", "methalox"}) {
        g.research().start(k);
        g.research().add_points(1000, nullptr);
    }
    auto kit = colony_kit();
    auto d = preset("agir", "moon", payload_mass_t(kit) + 0.5, 3);
    auto rep = g.evaluate(d);
    if (!rep) {
        std::printf("Analiz hatası: %s\n", rep.error().message.c_str());
        return 1;
    }
    std::printf("Ay koloni görevi analizi:\n");
    print_report(rep.value());
    // fırlatma başarısız olursa (olasılıksal arıza) gerçek bir oyuncu gibi yeniden dener
    bool arrived = false;
    for (int attempt = 1; attempt <= 4 && !arrived; ++attempt) {
        auto id = g.launch(d, kit);
        if (!id) {
            std::printf("Fırlatma hatası: %s\n", id.error().message.c_str());
            return 1;
        }
        arrived = g.missions().back().state != MissionState::Lost;
        std::printf("Deneme %d: %s\n", attempt, arrived ? "görev yolda" : "görev kaybedildi, yeniden deneniyor");
    }
    g.advance(6.0);
    if (!g.research().start("closed_loop")) return 1;
    g.advance(30.0);
    print_status(g);
    const std::string save = g.save();
    Game h(1);
    if (!h.load(save) || h.save() != save) {
        std::printf("Kayıt/yükleme doğrulaması BAŞARISIZ\n");
        return 1;
    }
    auto w = g.window_to("mars");
    std::printf("\nSonraki Mars penceresi: %.0f gün sonra (sinodik periyot %.0f gün)\n", w.value().days_until, w.value().synodic_days);
    const auto* c = g.colonies().empty() ? nullptr : &g.colonies().begin()->second;
    const bool ok = c && c->population() >= 3 && deaths == 0;
    std::printf("\nDEMO %s\n", ok ? "BAŞARILI" : "BAŞARISIZ");
    return ok ? 0 : 1;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc > 1 && std::string(argv[1]) == "--demo") return run_demo();
    Game g(static_cast<std::uint64_t>(std::time(nullptr)));
    g.bus().subscribe<colony::ColonistDied>([](const colony::ColonistDied& e) {
        std::printf("  [!] %s hayatını kaybetti (%s)\n", e.name.c_str(), e.cause.c_str());
    });
    g.bus().subscribe<ColonyFounded>([](const ColonyFounded& e) { std::printf("  [+] Koloni kuruldu: %s\n", e.colony.c_str()); });
    g.bus().subscribe<MissionLost>([](const MissionLost& e) { std::printf("  [!] Görev #%d kaybedildi: %s\n", e.id, e.reason.c_str()); });
    g.bus().subscribe<research::ResearchCompleted>([](const research::ResearchCompleted& e) {
        std::printf("  [+] Araştırma tamamlandı: %s\n", e.key.c_str());
    });
    g.new_game("AETHER");
    std::printf("KOZMOGENİS — çekirdek simülasyon (KozmoCore)\n");
    help();
    std::string line;
    while (std::printf("> "), std::fflush(stdout), std::getline(std::cin, line)) {
        std::istringstream in(line);
        std::string cmd;
        in >> cmd;
        if (cmd.empty()) continue;
        if (cmd == "cikis") break;
        if (cmd == "yardim") help();
        else if (cmd == "durum") print_status(g);
        else if (cmd == "gezegen") {
            std::string k;
            in >> k;
            auto b = astro::find(k);
            if (!b) { std::printf("%s\n", b.error().message.c_str()); continue; }
            const auto& x = *b.value();
            std::printf("%s: çap %.0f km, kütle %.3g x10^24 kg, yerçekimi %.1f m/s2, kaçış %.1f km/s, gün %.1f sa, yıl %.1f gün,\n"
                        "  ort. sıcaklık %.0f °C, basınç %s bar, uydu %d\n  Kaynak: %s\n  %s\n",
                        x.name_tr.c_str(), x.diameter_km, x.mass_1e24kg, x.gravity_ms2, x.escape_kms, x.day_h, x.period_days,
                        x.mean_temp_c, x.has_surface() ? fmt_g(x.surface_pressure_bar).c_str() : "bilinmiyor (gaz devi)",
                        x.moons, astro::to_string(x.source), astro::kMoonsNote);
        } else if (cmd == "pencere") {
            std::string t;
            in >> t;
            auto w = g.window_to(t);
            if (!w) std::printf("%s\n", w.error().message.c_str());
            else std::printf("Faz %.1f° (gereken %.1f°). Sonraki pencere %.0f gün sonra; sinodik periyot %.0f gün\n",
                             w.value().current_phase_deg, w.value().required_phase_deg, w.value().days_until, w.value().synodic_days);
        } else if (cmd == "analiz") {
            std::string kind, t;
            double pay = 1;
            int crew = 0;
            in >> kind >> t >> pay >> crew;
            auto r = g.evaluate(preset(kind, t, pay, crew));
            if (!r) std::printf("%s\n", r.error().message.c_str());
            else print_report(r.value());
        } else if (cmd == "koloni_kiti") {
            std::string t;
            in >> t;
            auto kit = colony_kit();
            auto r = g.launch(preset("agir", t, payload_mass_t(kit) + 0.5, 3), kit);
            if (!r) std::printf("Fırlatılamadı: %s\n", r.error().message.c_str());
            else std::printf("Görev #%d fırlatıldı\n", r.value());
        } else if (cmd == "arastir") {
            std::string k;
            in >> k;
            auto r = g.research().start(k);
            std::printf("%s\n", r ? "Araştırma başladı (koloni laboratuvarları puan üretir)" : r.error().message.c_str());
        } else if (cmd == "bekle") {
            double d = 1;
            in >> d;
            g.advance(std::clamp(d, 0.0, 3650.0));
            std::printf("Gün %.1f\n", g.day());
        } else if (cmd == "al" || cmd == "sat") {
            std::string m, k;
            double q = 0;
            in >> m >> k >> q;
            auto r = g.trade(m, k, q, cmd == "al");
            if (!r) std::printf("%s\n", r.error().message.c_str());
            else std::printf("%s %.2f %s, birim %.1f, toplam %.0f kredi\n", cmd == "al" ? "Alındı" : "Satıldı", q, k.c_str(),
                             r.value().unit_price, r.value().total);
        } else if (cmd == "insa") {
            std::string c;
            int t = -1;
            in >> c >> t;
            if (t < 0 || t > 8) { std::printf("Modül 0-8 arası\n"); continue; }
            auto r = g.build_module(c, static_cast<ModuleType>(t));
            std::printf("%s\n", r ? "İnşa edildi" : r.error().message.c_str());
        } else if (cmd == "kaydet") {
            std::string f;
            in >> f;
            std::ofstream(f) << g.save();
            std::printf("Kaydedildi: %s\n", f.c_str());
        } else if (cmd == "yukle") {
            std::string f;
            in >> f;
            std::ifstream is(f);
            std::stringstream ss;
            ss << is.rdbuf();
            auto r = g.load(ss.str());
            std::printf("%s\n", r ? "Yüklendi" : r.error().message.c_str());
        } else {
            std::printf("Bilinmeyen komut. 'yardim' yaz.\n");
        }
    }
    return 0;
}
