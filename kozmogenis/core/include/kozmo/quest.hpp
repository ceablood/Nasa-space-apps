// KozmoCore — oyuncu görev günlüğü (V41 §4.5 "koloni görevlerini alabilmeli", §7 senaryolar).
// Görevler NPC'lerden (diyalog), NOVA'dan ya da olaylardan (arıza, keşif) gelir; hedefler oyun olaylarıyla
// (binaya gir, konsol kullan, NPC ile konuş, numune topla, modül inşa et, onar, analiz et) ilerler.
// Ödüller: kredi, araştırma puanı, görevi veren NPC ile ilişki. Ödül miktarları OYUN VARSAYIMIDIR.
#pragma once

#include <string>
#include <vector>

#include "kozmo/core.hpp"
#include "kozmo/json.hpp"

namespace kozmo::quest {

enum class Goal { EnterDistrict, UseItem, TalkToJob, CollectSamples, BuildModule, RepairPower, AnalyzeSample, ReturnToCraft, ReachOrbit };
const char* to_string(Goal g);

struct Objective {
    Goal goal;
    int target = 0;          // bölge / meslek / modül türü (int) ya da adet
    std::string item = "";   // UseItem için konsol kimliği
    int count = 1, progress = 0;
    std::string text;
    bool done() const { return progress >= count; }
};

enum class State { Active, Completed, Failed };
const char* to_string(State s);

struct Reward {
    double credits = 0, research = 0, affinity = 0;
};

struct Quest {
    int id = 0;
    std::string key, title, description;
    int giver = -1;                  // NPC kimliği (-1 NOVA/sistem)
    std::vector<Objective> objectives;
    Reward reward;
    State state = State::Active;
    double accepted_h = 0, deadline_h = 0;   // 0 = süresiz
    bool rewarded = false;
    double progress() const;
};

struct Event {
    Goal goal;
    int arg = 0;                     // bölge / meslek / modül türü
    std::string item = "";
    int amount = 1;
};

struct Completion {
    int quest_id;
    std::string title;
    Reward reward;
    int giver;
};

class Log {
public:
    // hazır şablonlar: "power_crisis", "sample_hunt", "new_home", "health_check", "security_round", "orbit_test"
    Result<int> offer(const std::string& template_key, int giver, double now_h);
    Result<int> add(Quest q, double now_h);
    // olay geldi: ilgili hedefleri ilerletir; tamamlanan görevleri döner (ödül bir kez)
    std::vector<Completion> notify(const Event& e, double now_h);
    void tick(double now_h);                          // süre aşımı -> Failed
    Status abandon(int id);
    const std::vector<Quest>& quests() const { return quests_; }
    const Quest* find(int id) const;
    const Quest* find_key(const std::string& key) const;
    int active_count() const;
    std::string summary() const;

    json::Value to_json() const;
    Status from_json(const json::Value& v);

private:
    std::vector<Quest> quests_;
    int next_id_ = 1;
};

std::vector<std::string> template_keys();

}  // namespace kozmo::quest
