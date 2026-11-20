// KozmoCore — bağımlılıksız küçük JSON değeri, yazıcı ve ayrıştırıcı (kayıt/yükleme için).
#pragma once

#include <map>
#include <memory>
#include <string>
#include <vector>

#include "kozmo/core.hpp"

namespace kozmo::json {

class Value {
public:
    enum class Type { Null, Bool, Number, String, Array, Object };
    using Array = std::vector<Value>;
    using Object = std::map<std::string, Value>;

    Value() = default;
    Value(std::nullptr_t) {}
    Value(bool b) : t_(Type::Bool), b_(b) {}
    Value(double d) : t_(Type::Number), n_(d) {}
    Value(int i) : t_(Type::Number), n_(i) {}
    Value(long long i) : t_(Type::Number), n_(static_cast<double>(i)) {}
    Value(const char* s) : t_(Type::String), s_(s) {}
    Value(std::string s) : t_(Type::String), s_(std::move(s)) {}
    Value(Array a) : t_(Type::Array), a_(std::make_shared<Array>(std::move(a))) {}
    Value(Object o) : t_(Type::Object), o_(std::make_shared<Object>(std::move(o))) {}

    static Value array() { return Value(Array{}); }
    static Value object() { return Value(Object{}); }

    Type type() const { return t_; }
    bool is_null() const { return t_ == Type::Null; }
    bool is_object() const { return t_ == Type::Object; }
    bool is_array() const { return t_ == Type::Array; }

    bool as_bool(bool def = false) const { return t_ == Type::Bool ? b_ : def; }
    double as_number(double def = 0.0) const { return t_ == Type::Number ? n_ : def; }
    int as_int(int def = 0) const { return t_ == Type::Number ? static_cast<int>(n_) : def; }
    const std::string& as_string() const;
    const Array& as_array() const;
    const Object& as_object() const;

    // nesne erişimi (yoksa null döner); yazma için set/push
    const Value& operator[](const std::string& k) const;
    const Value& at(std::size_t i) const;
    std::size_t size() const;
    bool has(const std::string& k) const;
    Value& set(const std::string& k, Value v);
    Value& push(Value v);

    std::string dump(int indent = 0) const;

private:
    void dump_to(std::string& out, int indent, int depth) const;
    Type t_ = Type::Null;
    bool b_ = false;
    double n_ = 0.0;
    std::string s_;
    std::shared_ptr<Array> a_;
    std::shared_ptr<Object> o_;
};

Result<Value> parse(const std::string& text);

}  // namespace kozmo::json
