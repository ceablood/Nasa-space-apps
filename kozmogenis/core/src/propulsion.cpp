#include "kozmo/propulsion.hpp"

#include <algorithm>
#include <cmath>
#include <sstream>

namespace kozmo::prop {

namespace {
const std::vector<Engine>& table() {
    // Değerler yayımlanmış motor sınıflarının yuvarlanmış özellikleridir (mühendislik yaklaşımı).
    static const std::vector<Engine> t = {
        {"kerolox_gg", "Kerosen/LOX gaz jeneratörlü (Merlin 1D sınıfı)", "RP-1/LOX", 282, 311, 914, 0.47, 0.995, 6, ""},
        {"kerolox_vac", "Kerosen/LOX vakum (Merlin Vakum sınıfı)", "RP-1/LOX", 0, 348, 981, 0.49, 0.993, 8, ""},
        {"hydrolox_exp", "Hidrojen/LOX genişletici (RL10 sınıfı)", "LH2/LOX", 0, 465, 110, 0.30, 0.997, 12, "cryo"},
        {"methalox_fc", "Metan/LOX tam akışlı (Raptor sınıfı)", "CH4/LOX", 327, 350, 2300, 1.60, 0.990, 10, "methalox"},
        {"methalox_vac", "Metan/LOX vakum (Raptor Vakum sınıfı)", "CH4/LOX", 0, 380, 2500, 1.80, 0.990, 14, "methalox"},
        {"ntr", "Nükleer termal (NERVA sınıfı)", "LH2 (nükleer)", 0, 841, 333, 18.0, 0.980, 60, "nuclear"},
        {"ion", "Elektrikli iyon itici (NEXT sınıfı)", "Xenon", 0, 4190, 0.000236, 0.06, 0.999, 9, "ion"},
        // Katı yakıtlı güçlendirici: Uzay Mekiği SRB sınıfı (deniz seviyesi ~12.500 kN, Isp 242/268 s).
        // "Motor kütlesi" 0: gövde kütlesi Boosters::inert_fraction ile hesaplanır.
        {"srb", "Katı yakıtlı güçlendirici (Shuttle SRB sınıfı)", "APCP", 242, 268, 12500.0 * 268.0 / 242.0, 0.0, 0.998, 25, ""},
    };
    return t;
}

bool has(const std::vector<std::string>& v, const std::string& k) {
    return k.empty() || std::find(v.begin(), v.end(), k) != v.end();
}

}  // namespace

int engine_out_tolerance(int n) { return n >= 27 ? 2 : (n >= 9 ? 1 : 0); }

double stage_reliability(double p, int n) {
    // kademe, en fazla k motor arızasına dayanabilir (motor kaybı toleransı): P = sum_{i<=k} C(n,i) p^(n-i) q^i
    const int k = engine_out_tolerance(n);
    const double q = 1.0 - p;
    double sum = 0.0, comb = 1.0;
    for (int i = 0; i <= k && i <= n; ++i) {
        if (i > 0) comb = comb * (n - i + 1) / i;
        sum += comb * std::pow(p, n - i) * std::pow(q, i);
    }
    return std::min(1.0, sum);
}

namespace {
std::string fmt(double v, int prec = 1) {
    std::ostringstream o;
    o.setf(std::ios::fixed);
    o.precision(prec);
    o << v;
    return o.str();
}
}  // namespace

const std::vector<Engine>& engines() { return table(); }

Result<const Engine*> find_engine(const std::string& key) {
    for (const auto& e : table())
        if (e.key == key) return &e;
    return make_error(ErrorCode::NotFound, "Bilinmeyen motor: " + key);
}

Result<Report> analyze(const Design& d, const std::vector<std::string>& unlocked) {
    if (d.stages.empty()) return make_error(ErrorCode::InvalidArgument, "Tasarımda kademe yok");
    if (d.payload_t <= 0) return make_error(ErrorCode::InvalidArgument, "Yük kütlesi pozitif olmalı");
    auto budget = astro::mission_budget(d.target);
    if (!budget) return budget.error();
    auto target = astro::find(d.target);
    const bool can_land = target.ok() && target.value()->has_surface();

    Report r;
    r.required_dv_ms = budget.value().total(d.land && can_land, d.ret);

    // her kademenin kuru kütlesi ve motor verileri
    struct S { const Engine* e; double prop, dry; int n; };
    std::vector<S> st;
    for (std::size_t i = 0; i < d.stages.size(); ++i) {
        const Stage& s = d.stages[i];
        auto e = find_engine(s.engine);
        if (!e) return e.error();
        if (!has(unlocked, e.value()->research))
            return make_error(ErrorCode::Locked, e.value()->name_tr + " için araştırma gerekli: " + e.value()->research);
        if (s.engine_count < 1 || s.engine_count > 40)
            return make_error(ErrorCode::InvalidArgument, "Motor sayısı 1-40 arası olmalı");
        if (s.propellant_t < 0) return make_error(ErrorCode::InvalidArgument, "Yakıt negatif olamaz");
        if (s.structure_fraction < 0.02 || s.structure_fraction > 0.5)
            return make_error(ErrorCode::InvalidArgument, "Yapı oranı 0.02-0.5 arası olmalı");
        st.push_back({e.value(), s.propellant_t, s.propellant_t * s.structure_fraction + e.value()->mass_t * s.engine_count,
                      s.engine_count});
        r.cost_mcr += e.value()->cost_mcr * s.engine_count + s.propellant_t * 0.002 + s.propellant_t * s.structure_fraction * 0.05;
    }
    const double crew_module_t = d.crew > 0 ? 3.0 + 0.5 * d.crew : 0.0;   // oyun varsayımı: kapsül + yaşam desteği
    const double payload = d.payload_t + crew_module_t;
    r.cost_mcr += payload * 0.3;

    // yukarıdan aşağı: her kademenin üstündeki kütle
    double above = payload;
    std::vector<double> above_of(st.size());
    for (std::size_t i = st.size(); i-- > 0;) {
        above_of[i] = above;
        above += st[i].prop + st[i].dry;
    }
    // yan güçlendiriciler
    const Boosters& B = d.boosters;
    const prop::Engine* be = nullptr;
    double b_prop = 0, b_inert = 0;
    if (B.count > 0) {
        auto e = find_engine(B.engine);
        if (!e) return e.error();
        if (!has(unlocked, e.value()->research))
            return make_error(ErrorCode::Locked, e.value()->name_tr + " için araştırma gerekli: " + e.value()->research);
        if (B.count > 8 || B.propellant_t <= 0 || B.inert_fraction < 0.03 || B.inert_fraction > 0.5)
            return make_error(ErrorCode::InvalidArgument, "Güçlendirici: adet 1-8, yakıt > 0, gövde oranı 0.03-0.5 olmalı");
        be = e.value();
        b_prop = B.propellant_t * B.count;
        b_inert = b_prop * B.inert_fraction + be->mass_t * B.count;
        r.cost_mcr += be->cost_mcr * B.count + b_prop * 0.003;
    }
    r.liftoff_mass_t = above + b_prop + b_inert;

    double success = 1.0;
    if (be) success *= std::pow(be->reliability, B.count);      // katı yakıtlıda motor kaybı toleransı yok
    for (std::size_t i = 0; i < st.size(); ++i) {
        const S& s = st[i];
        if (i == 0 && be) {
            // PARALEL KADEME: A fazı (çekirdek + güçlendiriciler), B fazı (güçlendiriciler atıldıktan sonra çekirdek)
            const double isp_c = s.e->isp_sl_s > 0 ? 0.25 * s.e->isp_sl_s + 0.75 * s.e->isp_vac_s : s.e->isp_vac_s * 0.3;
            const double isp_b = 0.25 * be->isp_sl_s + 0.75 * be->isp_vac_s;
            const double mdot_c = s.e->thrust_vac_kn * 1000.0 * s.n / (s.e->isp_vac_s * kG0) / 1000.0;   // t/s
            const double mdot_b = be->thrust_vac_kn * 1000.0 * B.count / (be->isp_vac_s * kG0) / 1000.0;
            const double tb = b_prop / mdot_b;                       // güçlendirici yanma süresi
            const double tc = s.prop / mdot_c;
            if (tb > tc) r.problems.push_back("Güçlendiriciler çekirdek kademeden uzun yanıyor (çekirdek yakıtını artır)");
            const double tA = std::min(tb, tc);
            const double burnedA = (mdot_c + mdot_b) * tA;
            const double isp_eff = (mdot_c * isp_c + mdot_b * isp_b) / (mdot_c + mdot_b);   // kütle akışı ağırlıklı
            StageReport a{};
            a.label = "Güçlendiriciler + 1. kademe";
            a.m0_t = r.liftoff_mass_t;
            a.mf_t = a.m0_t - burnedA;
            a.isp_used_s = isp_eff;
            a.dv_ms = isp_eff * kG0 * std::log(a.m0_t / a.mf_t);
            a.twr = (s.e->thrust_sl_kn() * s.n + be->thrust_sl_kn() * B.count) * 1000.0 / (a.m0_t * 1000.0 * kG0);
            a.burn_s = tA;
            r.total_dv_ms += a.dv_ms;
            r.stages.push_back(a);
            // güçlendiriciler (ve kalan yakıtları) atılır
            const double b_left = std::max(0.0, b_prop - mdot_b * tA);
            const double core_left = std::max(0.0, s.prop - mdot_c * tA);
            StageReport c{};
            c.label = "1. kademe (güçlendiriciler atıldı)";
            c.m0_t = a.mf_t - b_inert - b_left;
            c.mf_t = c.m0_t - core_left;
            c.isp_used_s = s.e->isp_vac_s * 0.97;                   // ince üst atmosfer
            c.dv_ms = c.isp_used_s * kG0 * std::log(c.m0_t / c.mf_t);
            c.twr = s.e->thrust_vac_kn * s.n * 1000.0 / (c.m0_t * 1000.0 * kG0);
            c.burn_s = core_left / mdot_c;
            r.total_dv_ms += c.dv_ms;
            success *= stage_reliability(s.e->reliability, s.n);
            r.stages.push_back(c);
            continue;
        }
        StageReport sr{};
        sr.label = std::to_string(i + 1) + ". kademe";
        sr.m0_t = above_of[i] + s.prop + s.dry;
        sr.mf_t = above_of[i] + s.dry;
        // ilk kademe atmosferde başlar ama yakıtın çoğunu ince üst atmosferde yakar: Isp ağırlığı %25 deniz
        // seviyesi / %75 vakum (mühendislik yaklaşımı; yerçekimi/sürüklenme kayıpları LEO bütçesinde)
        if (i == 0) {
            if (s.e->isp_sl_s <= 0) r.problems.push_back("İlk kademe motoru atmosferde çalışamaz: " + s.e->name_tr);
            sr.isp_used_s = s.e->isp_sl_s > 0 ? 0.25 * s.e->isp_sl_s + 0.75 * s.e->isp_vac_s : s.e->isp_vac_s * 0.3;
        } else {
            sr.isp_used_s = s.e->isp_vac_s;
        }
        sr.dv_ms = sr.isp_used_s * kG0 * std::log(sr.m0_t / sr.mf_t);
        const double thrust_kn = (i == 0 ? s.e->thrust_sl_kn() : s.e->thrust_vac_kn) * s.n;
        sr.twr = thrust_kn * 1000.0 / (sr.m0_t * 1000.0 * kG0);
        const double mdot = s.e->thrust_vac_kn * 1000.0 * s.n / (s.e->isp_vac_s * kG0);     // kg/s
        sr.burn_s = mdot > 0 ? s.prop * 1000.0 / mdot : 0.0;
        r.total_dv_ms += sr.dv_ms;
        success *= stage_reliability(s.e->reliability, s.n);
        r.stages.push_back(sr);
    }
    r.liftoff_twr = r.stages.front().twr;
    r.margin_ms = r.total_dv_ms - r.required_dv_ms;

    if (r.liftoff_twr < 1.15)
        r.problems.push_back("Kalkış itki/ağırlık oranı " + fmt(r.liftoff_twr, 2) + " (en az 1.15 gerekli)");
    if (r.margin_ms < 0)
        r.problems.push_back("Delta-v yetersiz: " + fmt(r.total_dv_ms / 1000.0, 2) + " / " +
                             fmt(r.required_dv_ms / 1000.0, 2) + " km/s");
    for (std::size_t i = 1; i < st.size(); ++i) {
        const StageReport& sr = r.stages[i + (be ? 1 : 0)];
        if (sr.twr < 0.02 && st[i].e->key != "ion")
            r.problems.push_back("Kademe " + std::to_string(i + 1) + " itkisi çok düşük (yerçekimi kaybı)");
    }
    if (d.crew > 0 && be && r.liftoff_twr > 2.5)
        r.problems.push_back("Katı güçlendiriciler kısılamaz: kalkış itki/ağırlık " + fmt(r.liftoff_twr, 2) +
                             " mürettebat için fazla (ivme 4 g'yi aşar); güçlendirici sayısını/yakıtını azalt");
    if (d.crew > 0 && st.back().e->key == "ion")
        r.problems.push_back("Mürettebatlı görevde iyon itici ana tahrik olamaz (aylar sürer)");

    // risk modeli (oyun varsayımı): motor güvenilirliği x delta-v payı x itki/ağırlık payı
    const double dv_margin_frac = r.required_dv_ms > 0 ? r.margin_ms / r.required_dv_ms : 0.0;
    const double margin_factor = std::clamp(0.80 + dv_margin_frac * 2.0, 0.0, 1.0);
    const double twr_factor = std::clamp((r.liftoff_twr - 1.0) / 0.4, 0.0, 1.0);
    r.success_p = std::clamp(success * (0.6 + 0.4 * margin_factor) * (0.7 + 0.3 * twr_factor), 0.0, 1.0);
    r.feasible = r.problems.empty();
    if (!r.feasible) r.success_p = std::min(r.success_p, 0.05);
    return r;
}

Result<double> min_upper_propellant(Design d, const std::vector<std::string>& unlocked, double step, double max_t) {
    if (d.stages.empty()) return make_error(ErrorCode::InvalidArgument, "Tasarımda kademe yok");
    for (double p = step; p <= max_t; p += step) {
        d.stages.back().propellant_t = p;
        auto r = analyze(d, unlocked);
        if (!r) return r.error();
        if (r.value().margin_ms >= 0) return p;
    }
    return make_error(ErrorCode::Infeasible, "Bu kademe yapısıyla hedefe ulaşılamıyor (yakıt artırmak yetmiyor)");
}

}  // namespace kozmo::prop
