// KozmoCore — dallanan diyalog sistemi (V30 §11.2, V41 §5.9). Düğüm + seçenek ağaçları; seçenekler koşullara
// (ilişki, güven, hafıza, meslek, ihtiyaç, alarm, görev durumu) bağlıdır ve etkileri vardır (ilişki/güven
// değişimi, görev verme/teslim, NPC'yi yemeğe/dinlenmeye/tedaviye yönlendirme, hafızaya yazma).
// Metinler {ad}, {meslek}, {o2}, {su}, {gida}, {nufus}, {is} yer tutucularıyla canlı veriden doldurulur.
#pragma once

#include <string>
#include <vector>

#include "kozmo/colony.hpp"
#include "kozmo/core.hpp"
#include "kozmo/life.hpp"
#include "kozmo/quest.hpp"

namespace kozmo::dialogue {

enum class Cond { AffinityAbove, AffinityBelow, TrustAbove, RemembersHelp, IsJob, Hungry, Tired, Sick, Alarm, QuestActive, QuestDone, QuestNotTaken };
enum class Effect { Affinity, Trust, GiveQuest, Eat, Rest, Treat, Remember, End };

struct Condition {
    Cond cond;
    double value = 0;
    std::string key = "";     // görev şablonu
};

struct Action {
    Effect effect;
    double value = 0;
    std::string key = "";     // görev şablonu / hafıza metni
};

struct Option {
    std::string text;
    std::vector<Condition> when;
    std::vector<Action> actions;
    int next = -1;       // -1 konuşma biter
};

struct Node {
    int id;
    std::string text;
    std::vector<Option> options;
};

struct Tree {
    std::string key;
    std::vector<Node> nodes;
    const Node* node(int id) const;
};

// Meslek başına ağaç (ortak giriş + mesleğe özgü dal); tüm ağaçlar bağlantı denetiminden geçer
const Tree& tree_for(colony::Job job);
// Ağaç geçerliliği: tüm 'next' kimlikleri var mı, her düğüme ulaşılabilir mi (testler)
std::vector<std::string> validate(const Tree& t);

class Conversation {
public:
    Conversation(int npc_id, life::Society& soc, colony::Colony& col, quest::Log& log, double day, double now_h);
    bool active() const { return active_; }
    std::string text() const;                              // yer tutucular doldurulmuş metin
    std::vector<std::string> options() const;              // koşulları sağlayan seçenekler
    Result<std::string> choose(std::size_t index);         // seçilen seçeneğin etkileri; sonraki düğüm metni
    std::vector<std::string> log() const { return log_; }

private:
    bool ok(const Condition& c) const;
    std::vector<const Option*> available() const;
    std::string fill(const std::string& s) const;
    int npc_;
    life::Society& soc_;
    colony::Colony& col_;
    quest::Log& quests_;
    double day_, now_h_;
    const Tree* tree_;
    int node_ = 0;
    bool active_ = true;
    std::vector<std::string> log_;
};

}  // namespace kozmo::dialogue
