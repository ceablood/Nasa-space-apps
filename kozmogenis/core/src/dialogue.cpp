#include "kozmo/dialogue.hpp"

#include <algorithm>
#include <cstdio>
#include <set>

namespace kozmo::dialogue {

using colony::Job;

const Node* Tree::node(int id) const {
    for (const auto& n : nodes)
        if (n.id == id) return &n;
    return nullptr;
}

namespace {
// ortak giriş düğümleri: 0 selam, 1 durum, 2 koloni, 3 yardım, 4 hoşça kal; 10+ mesleğe özgü
std::vector<Node> common() {
    using C = Cond;
    using E = Effect;
    return {
        {0, "{ad} ({meslek}) sana dönüyor.",
         {{"Nasılsın?", {}, {}, 1},
          {"Koloni nasıl gidiyor?", {}, {}, 2},
          {"Sana yardım edebilir miyim?", {}, {}, 3},
          {"İşin hakkında konuşalım.", {}, {}, 10},
          {"Geçen sefer için teşekkür ederim.", {{C::RemembersHelp}}, {{E::Affinity, 0.05}}, 5},
          {"Görüşürüz.", {}, {{E::End}}, -1}}},
        {1, "Şu an {is}.",
         {{"Aç görünüyorsun, yemek salonuna gitmelisin.", {{C::Hungry}}, {{E::Eat}, {E::Affinity, 0.05}, {E::Remember, 0, "Oyuncu yemek yememi hatırlattı"}}, 4},
          {"Çok yorgunsun, biraz dinlen.", {{C::Tired}}, {{E::Rest}, {E::Affinity, 0.05}}, 4},
          {"Revire gitmen gerek, seni oraya yönlendiriyorum.", {{C::Sick}}, {{E::Treat}, {E::Affinity, 0.1}, {E::Remember, 0, "Oyuncu beni revire yolladı"}}, 4},
          {"Anladım. Başka bir konu...", {}, {}, 0}}},
        {2, "Oksijen {o2} gün, su {su} gün, gıda {gida} gün yeter. Nüfus {nufus}.",
         {{"Alarm durumu ne?", {{C::Alarm}}, {}, 6}, {"Teşekkürler.", {}, {}, 0}}},
        {3, "Aslında bir işimiz var...",
         {{"Anlat, dinliyorum.", {}, {}, 10}, {"Şimdi olmaz.", {}, {{E::Affinity, -0.02}}, 0}}},
        {4, "Sağ ol, haklısın.", {{"Başka bir şey...", {}, {}, 0}, {"Görüşürüz.", {}, {{E::End}}, -1}}},
        {5, "Ne demek! Ekip olarak birbirimize destek oluyoruz.", {{"Görüşürüz.", {}, {{E::End}}, -1}}},
        {6, "Alarm sürüyor; güvenlik ekibi bölgeleri kontrol ediyor. Sığınağa yakın kal.", {{"Tamam.", {}, {}, 0}}},
    };
}

Tree build(Job job) {
    using C = Cond;
    using E = Effect;
    Tree t;
    t.nodes = common();
    switch (job) {
        case Job::Engineer:
            t.key = "muhendis";
            t.nodes.push_back({10, "Enerji sistemleri bugün zorlanıyor. Güneş dizilerini kontrol etmemiz lazım.",
                               {{"Enerji tesisine gidip paneli ben kontrol ederim.", {{C::QuestNotTaken, 0, "power_crisis"}}, {{E::GiveQuest, 0, "power_crisis"}, {E::Trust, 0.05}}, 11},
                                {"Ekip yeni bir habitat istiyor; inşaatı ben organize ederim.", {{C::QuestNotTaken, 0, "new_home"}}, {{E::GiveQuest, 0, "new_home"}}, 11},
                                {"Görev tamam, panelleri onardım.", {{C::QuestDone, 0, "power_crisis"}}, {{E::Affinity, 0.1}}, 12},
                                {"Kolay gelsin.", {}, {}, 0}}});
            break;
        case Job::Scientist:
            t.key = "bilim";
            t.nodes.push_back({10, "Yüzeyden taze numune bulursak analiz kuyruğumuz dolar.",
                               {{"Üç numune toplar, analiz ederim.", {{C::QuestNotTaken, 0, "sample_hunt"}}, {{E::GiveQuest, 0, "sample_hunt"}}, 11},
                                {"Numuneler analiz edildi.", {{C::QuestDone, 0, "sample_hunt"}}, {{E::Affinity, 0.1}, {E::Remember, 0, "Oyuncu numune görevini bitirdi"}}, 12},
                                {"Başarılar.", {}, {}, 0}}});
            break;
        case Job::Medic:
            t.key = "doktor";
            t.nodes.push_back({10, "Herkesin düzenli sağlık taramasından geçmesi gerekiyor. Sen de dahil.",
                               {{"Hemen hastaneye geliyorum.", {{C::QuestNotTaken, 0, "health_check"}}, {{E::GiveQuest, 0, "health_check"}}, 11},
                                {"Taramamı oldum.", {{C::QuestDone, 0, "health_check"}}, {{E::Trust, 0.1}}, 12},
                                {"Sonra.", {}, {}, 0}}});
            break;
        case Job::Security:
            t.key = "guvenlik";
            t.nodes.push_back({10, "Dış alanları kontrol etmek için bir göz daha lazım.",
                               {{"Hava kilidine gidip bakarım.", {{C::QuestNotTaken, 0, "security_round"}}, {{E::GiveQuest, 0, "security_round"}}, 11},
                                {"Alarmda nereye gitmeliyim?", {{C::Alarm}}, {}, 6},
                                {"Kolay gelsin.", {}, {}, 0}}});
            break;
        case Job::Pilot:
            t.key = "pilot";
            t.nodes.push_back({10, "Aracın yörünge testi yapılmadı. Yüzeyden kalkıp yörüngeye çıkman lazım.",
                               {{"Testi ben uçarım.", {{C::QuestNotTaken, 0, "orbit_test"}, {C::TrustAbove, 0.3}}, {{E::GiveQuest, 0, "orbit_test"}}, 11},
                                {"Henüz bana güvenmiyor musun?", {{C::AffinityBelow, 0.2}}, {}, 13},
                                {"Sonra.", {}, {}, 0}}});
            break;
        default:
            t.key = "genel";
            t.nodes.push_back({10, "İşler yolunda, sağ ol.", {{"İyi çalışmalar.", {}, {}, 0}}});
            break;
    }
    t.nodes.push_back({11, "Harika, görev günlüğüne ekledim.", {{"Başka bir konu...", {}, {}, 0}, {"Görüşürüz.", {}, {{E::End}}, -1}}});
    t.nodes.push_back({12, "Elinize sağlık, bunu unutmayacağım.", {{"Görüşürüz.", {}, {{E::End}}, -1}}});
    t.nodes.push_back({13, "Seni daha iyi tanıyınca, belki.", {{"Anlaşıldı.", {}, {}, 0}}});
    // yalnız girişten ulaşılabilen düğümler kalır (mesleğe göre kullanılmayan ortak düğümler budanır)
    std::set<int> reach = {0};
    for (bool grow = true; grow;) {
        grow = false;
        for (const auto& n : t.nodes)
            if (reach.count(n.id))
                for (const auto& o : n.options)
                    if (o.next >= 0 && reach.insert(o.next).second) grow = true;
    }
    t.nodes.erase(std::remove_if(t.nodes.begin(), t.nodes.end(), [&](const Node& n) { return !reach.count(n.id); }), t.nodes.end());
    return t;
}
}  // namespace

const Tree& tree_for(Job job) {
    static const Tree trees[] = {build(Job::Farmer), build(Job::Engineer), build(Job::Miner), build(Job::Scientist), build(Job::Medic), build(Job::Pilot), build(Job::Security)};
    return trees[std::clamp(static_cast<int>(job), 0, 6)];
}

std::vector<std::string> validate(const Tree& t) {
    std::vector<std::string> errs;
    std::set<int> ids;
    for (const auto& n : t.nodes) {
        if (!ids.insert(n.id).second) errs.push_back("Yinelenen düğüm " + std::to_string(n.id));
        if (n.options.empty()) errs.push_back("Seçeneksiz düğüm " + std::to_string(n.id));
    }
    std::set<int> reach = {0};
    for (bool grow = true; grow;) {
        grow = false;
        for (const auto& n : t.nodes) {
            if (!reach.count(n.id)) continue;
            for (const auto& o : n.options)
                if (o.next >= 0 && !reach.count(o.next)) {
                    reach.insert(o.next);
                    grow = true;
                }
        }
    }
    for (const auto& n : t.nodes) {
        for (const auto& o : n.options)
            if (o.next >= 0 && !ids.count(o.next)) errs.push_back("Kayıp hedef " + std::to_string(o.next));
        if (!reach.count(n.id)) errs.push_back("Ulaşılamayan düğüm " + std::to_string(n.id));
    }
    return errs;
}

Conversation::Conversation(int npc, life::Society& soc, colony::Colony& col, quest::Log& log, double day, double now_h)
    : npc_(npc), soc_(soc), col_(col), quests_(log), day_(day), now_h_(now_h) {
    const colony::Colonist* k = col_.colonist(npc);
    tree_ = &tree_for(k ? k->job : Job::Farmer);
    active_ = k && k->alive && soc_.npc(npc);
}

bool Conversation::ok(const Condition& c) const {
    const colony::Colonist* k = col_.colonist(npc_);
    const life::Relation* r = soc_.find_relation(life::Society::kPlayer, npc_);
    const double aff = r ? r->affinity : 0.0, trust = r ? r->trust : 0.5;
    const quest::Quest* q = c.key.empty() ? nullptr : quests_.find_key(c.key);
    switch (c.cond) {
        case Cond::AffinityAbove: return aff > c.value;
        case Cond::AffinityBelow: return aff < c.value;
        case Cond::TrustAbove: return trust > c.value;
        case Cond::RemembersHelp: {
            const life::Npc* n = soc_.npc(npc_);
            if (!n) return false;
            return std::any_of(n->memories.begin(), n->memories.end(), [](const life::Memory& m) { return m.about == life::Society::kPlayer && m.valence > 0.5; });
        }
        case Cond::IsJob: return k && static_cast<int>(k->job) == static_cast<int>(c.value);
        case Cond::Hungry: return k && k->needs.hunger > 0.6;
        case Cond::Tired: return k && k->needs.fatigue > 0.7;
        case Cond::Sick: return k && k->needs.health < 0.6;
        case Cond::Alarm: return soc_.alarm();
        case Cond::QuestActive: return q && q->state == quest::State::Active;
        case Cond::QuestDone: return q && q->state == quest::State::Completed;
        case Cond::QuestNotTaken: return !q || q->state == quest::State::Failed;
    }
    return false;
}

std::vector<const Option*> Conversation::available() const {
    std::vector<const Option*> v;
    const Node* n = tree_->node(node_);
    if (!n || !active_) return v;
    for (const auto& o : n->options)
        if (std::all_of(o.when.begin(), o.when.end(), [&](const Condition& c) { return ok(c); })) v.push_back(&o);
    return v;
}

std::string Conversation::fill(const std::string& s) const {
    const colony::Colonist* k = col_.colonist(npc_);
    const life::Npc* n = soc_.npc(npc_);
    const int pop = std::max(1, col_.population());
    auto num = [](double v) {
        char b[32];
        std::snprintf(b, sizeof(b), "%.0f", v);
        return std::string(b);
    };
    std::string out = s;
    auto rep = [&](const std::string& a, const std::string& b) {
        for (std::size_t p = out.find(a); p != std::string::npos; p = out.find(a, p + b.size())) out.replace(p, a.size(), b);
    };
    rep("{ad}", k ? k->name : "?");
    rep("{meslek}", k ? colony::job_name(k->job) : "?");
    rep("{o2}", num(col_.resource("oxygen") / (pop * colony::kO2PerPersonDay_t)));
    rep("{su}", num(col_.resource("water") / (pop * colony::kWaterPerPersonDay_t)));
    rep("{gida}", num(col_.resource("food") / (pop * colony::kFoodPerPersonDay_t)));
    rep("{nufus}", std::to_string(col_.population()));
    std::string is = n ? std::string(life::to_string(n->intent)) : "?";
    rep("{is}", is);
    return out;
}

std::string Conversation::text() const {
    const Node* n = tree_->node(node_);
    return n && active_ ? fill(n->text) : std::string();
}

std::vector<std::string> Conversation::options() const {
    std::vector<std::string> v;
    for (const Option* o : available()) v.push_back(o->text);
    return v;
}

Result<std::string> Conversation::choose(std::size_t index) {
    auto av = available();
    if (index >= av.size()) return make_error(ErrorCode::InvalidArgument, "Geçersiz seçenek");
    const Option& o = *av[index];
    log_.push_back("Oyuncu: " + o.text);
    life::Relation& r = soc_.relation(life::Society::kPlayer, npc_);
    life::Npc* n = soc_.npc(npc_);
    for (const auto& a : o.actions) {
        switch (a.effect) {
            case Effect::Affinity: r.affinity = std::clamp(r.affinity + a.value, -1.0, 1.0); break;
            case Effect::Trust: r.trust = std::clamp(r.trust + a.value, 0.0, 1.0); break;
            case Effect::GiveQuest: {
                auto id = quests_.offer(a.key, npc_, now_h_);
                if (id) log_.push_back("Görev alındı: " + quests_.find(id.value())->title);
                break;
            }
            case Effect::Eat: (void)col_.order(npc_, colony::Activity::Eat, 1.0); break;
            case Effect::Rest: (void)col_.order(npc_, colony::Activity::Sleep, 6.0); break;
            case Effect::Treat: (void)col_.order(npc_, colony::Activity::Treatment, 2.0); break;
            case Effect::Remember:
                if (n) soc_.remember(*n, {day_, life::Society::kPlayer, a.key, 0.7, 0.8});
                break;
            case Effect::End: active_ = false; break;
        }
    }
    if (o.next < 0) active_ = false;
    else node_ = o.next;
    const std::string t = active_ ? text() : std::string("(Konuşma bitti)");
    log_.push_back(t);
    return t;
}

}  // namespace kozmo::dialogue
