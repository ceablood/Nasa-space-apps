#include "kozmo/nova.hpp"
#include "test_framework.hpp"

using namespace kozmo;
using namespace kozmo::nova;

namespace {
void unlock(Game& g) {
    for (const char* k : {"cryo", "methalox"}) {
        g.research().start(k);
        g.research().add_points(1e6, nullptr);
    }
}
struct FakeOnline : OnlineConnector {
    bool up;
    int calls = 0;
    explicit FakeOnline(bool u) : up(u) {}
    bool available() const override { return up; }
    std::optional<std::string> complete(const std::string&, const std::string& ctx) override {
        ++calls;
        return "çevrimiçi: " + ctx.substr(0, 10);
    }
};
}  // namespace

TEST("nova: Türkçe ayrıştırma — ekler, büyük harf, Türkçe karakter") {
    CHECK(parse("MARS'A KOLONİ KİTİ FIRLAT").intent == Intent::LaunchColonyKit);
    CHECK(parse("mars'a koloni kiti firlat").planet == "mars");
    CHECK(parse("Ay'a koloni gönder").planet == "moon");
    CHECK(parse("Aya koloni gönder").planet == "moon");
    CHECK(parse("ayarlar").planet.empty());                       // "ay" ile karışmaz
    CHECK(parse("Jüpiter hakkında bilgi ver").intent == Intent::PlanetInfo);
    CHECK(parse("Jüpiter hakkında bilgi ver").planet == "jupiter");
    CHECK(parse("Mars penceresi ne zaman?").intent == Intent::LaunchWindow);
    CHECK(parse("fisyon reaktörünü araştır").intent == Intent::StartResearch);
    CHECK(parse("fisyon reaktörünü araştır").tech == "fission");
    CHECK(parse("Mars roketi 32,5 ton").has_number);
    CHECK_NEAR(parse("Mars roketi 32,5 ton").number, 32.5, 1e-9);
    CHECK(parse("ne araştırmalıyım").intent == Intent::ResearchAdvice);
    CHECK(parse("ONAYLA").intent == Intent::Confirm);
    CHECK(parse("vazgeç").intent == Intent::Cancel);
    CHECK(parse("koloni oksijen durumu").intent == Intent::ColonyAdvice);
    CHECK(parse("qwerty").intent == Intent::Unknown);
}

TEST("nova: gezegen bilgisi NASA kaynağıyla verilir") {
    Game g(1);
    g.new_game("A");
    Nova n(g);
    auto r = n.ask("Mars hakkında bilgi");
    CHECK(r.text.find("6792") != std::string::npos);              // NASA çapı
    CHECK(!r.sources.empty() && r.sources[0].find("NASA") != std::string::npos);
    auto j = n.ask("Jüpiter nedir");
    CHECK(j.text.find("Katı yüzeyi yoktur") != std::string::npos);
}

TEST("nova: kaynak harcayan fırlatma onaysız uygulanmaz; iptal hiçbir şey harcamaz") {
    Game g(7);
    g.new_game("A", 3e6);
    unlock(g);
    Nova n(g);
    const double before = g.wallet().balance();
    auto r = n.ask("Ay'a koloni kiti fırlat");
    CHECK(r.pending_action.has_value());
    CHECK(g.missions().empty());
    CHECK_NEAR(g.wallet().balance(), before, 1e-9);               // onaydan önce kuruş harcanmadı
    auto c = n.ask("iptal");
    CHECK(n.pending().empty());
    CHECK_NEAR(g.wallet().balance(), before, 1e-9);
    CHECK(g.missions().empty());
    n.ask("Ay'a koloni kiti fırlat");
    auto ok = n.ask("onayla");
    CHECK(g.missions().size() == 1);
    CHECK(g.wallet().balance() < before);
    CHECK(ok.text.find("Görev") != std::string::npos);
    CHECK(n.ask("onayla").text.find("bekleyen") != std::string::npos);
}

TEST("nova: araştırma başlatma onay ister; ilerleme kaybı uyarılır; kurgusal işaretlenir") {
    Game g(3);
    g.new_game("A");
    Nova n(g);
    auto r = n.ask("fisyon araştır");
    CHECK(r.pending_action.has_value());
    CHECK(g.research().active().empty());
    n.ask("onayla");
    CHECK(g.research().active() == "fission");
    auto r2 = n.ask("kapalı döngü araştır");
    CHECK(r2.text.find("sıfırlanır") != std::string::npos);
    n.ask("iptal");
    CHECK(g.research().active() == "fission");
    unlock(g);
    for (const char* k : {"fission", "nuclear", "isru"}) {
        g.research().start(k);
        g.research().add_points(1e6, nullptr);
    }
    CHECK(n.ask("füzyon araştır").text.find("kurgusal") != std::string::npos);
}

TEST("nova: pencere, roket tavsiyesi ve koloni uyarıları gerçek analizden") {
    Game g(11);
    g.new_game("A", 3e6);
    unlock(g);
    Nova n(g);
    auto w = n.ask("Mars penceresi");
    CHECK(w.text.find("faz") != std::string::npos);
    auto rk = n.ask("Ay roketi");
    CHECK(rk.text.find("delta-v") != std::string::npos);
    CHECK(n.ask("koloni durumu").text.find("Henüz koloni yok") != std::string::npos);
    n.ask("Ay'a koloni kiti fırlat");
    n.ask("onayla");
    g.advance(6.0);
    bool night_warning = false;
    for (const auto& x : n.warnings()) night_warning |= x.find("Ay gecesi") != std::string::npos;
    CHECK(night_warning);                                         // reaktörsüz Ay kolonisi
    CHECK(n.ask("ne araştırmalıyım").text.find("fisyon") != std::string::npos);
}

TEST("nova: çevrimiçi model yoksa çevrimdışı çalışır, varsa yanıt etiketlenir") {
    Game g(1);
    g.new_game("A");
    Nova n(g);
    auto off = std::make_shared<FakeOnline>(false);
    n.set_online(off);
    auto r = n.ask("kara deliklerin kökeni");
    CHECK(!r.from_online_model);
    CHECK(off->calls == 0);
    auto on = std::make_shared<FakeOnline>(true);
    n.set_online(on);
    auto r2 = n.ask("kara deliklerin kökeni");
    CHECK(r2.from_online_model);
    CHECK(r2.text.find("garanti edilmez") != std::string::npos);
    auto r3 = n.ask("durum");                                     // bilinen komut çevrimiçine gitmez
    CHECK(!r3.from_online_model);
    CHECK(on->calls == 1);
}
