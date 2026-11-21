// KozmoCore — ticari fırlatma sözleşmeleri (V27 ajans ekonomisi). Teklifler müşteri, yük, yörünge, son tarih,
// ödül ve gecikme cezası içerir; ödüller gerçek piyasa fiyat mertebelerinden türetilir:
//   * Falcon 9 liste fiyatı ~67 milyon $ / 22.8 t LEO ~ 2 900 $/kg (2022); paylaşımlı (rideshare) ~5 500 $/kg (2023)
//   * GTO taşımacılığı kg başına LEO'nun ~2-3 katı; Ay yüzeyi (CLPS) ~1 milyon $/kg mertebesi
// 1 kredi = 1 000 $ (oyun ölçeği). İtibar (0..1) teklif kalitesini etkiler (OYUN VARSAYIMI).
#pragma once

#include <string>
#include <vector>

#include "kozmo/core.hpp"
#include "kozmo/economy.hpp"
#include "kozmo/json.hpp"

namespace kozmo::contracts {

enum class Destination { LEO, SSO, GTO, Moon };
const char* to_string(Destination d);
double price_usd_per_kg(Destination d, bool rideshare);

enum class Status_ { Offered, Accepted, Completed, Failed, Expired };
const char* to_string(Status_ s);

struct Contract {
    int id;
    std::string client;
    Destination dest;
    double payload_t;
    bool rideshare;
    double offered_day, deadline_day;
    double reward, penalty;      // kredi
    Status_ status = Status_::Offered;
};

class Board {
public:
    // yeni teklifler (slot ve itibara göre); seed'li
    void refresh(double day, int slots, Rng& rng);
    Status accept(int id, int max_active);
    // görev tamamlandı: taşıma kapasitesi (t) yeterliyse ödül; geç teslimde ceza
    Result<double> fulfil(int id, double capacity_t, double day, econ::Wallet& w);
    // süresi geçenler: kabul edilmişse ceza ve itibar kaybı
    std::vector<std::string> expire(double day, econ::Wallet& w);
    const std::vector<Contract>& contracts() const { return list_; }
    double reputation() const { return reputation_; }
    json::Value to_json() const;
    Status from_json(const json::Value& v);

private:
    std::vector<Contract> list_;
    int next_id_ = 1;
    double reputation_ = 0.5;
};

}  // namespace kozmo::contracts
