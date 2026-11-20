#include "kozmo/json.hpp"

#include <cmath>
#include <cstdio>
#include <cstdlib>

namespace kozmo::json {

namespace {
const Value& null_value() {
    static const Value v;
    return v;
}
const std::string& empty_string() {
    static const std::string s;
    return s;
}
const Value::Array& empty_array() {
    static const Value::Array a;
    return a;
}
const Value::Object& empty_object() {
    static const Value::Object o;
    return o;
}

void escape(std::string& out, const std::string& s) {
    out += '"';
    for (unsigned char c : s) {
        switch (c) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if (c < 0x20) {
                    char buf[8];
                    std::snprintf(buf, sizeof buf, "\\u%04x", c);
                    out += buf;
                } else {
                    out += static_cast<char>(c);   // UTF-8 baytları olduğu gibi
                }
        }
    }
    out += '"';
}
}  // namespace

const std::string& Value::as_string() const { return t_ == Type::String ? s_ : empty_string(); }
const Value::Array& Value::as_array() const { return t_ == Type::Array ? *a_ : empty_array(); }
const Value::Object& Value::as_object() const { return t_ == Type::Object ? *o_ : empty_object(); }

const Value& Value::operator[](const std::string& k) const {
    if (t_ != Type::Object) return null_value();
    auto it = o_->find(k);
    return it == o_->end() ? null_value() : it->second;
}

const Value& Value::at(std::size_t i) const {
    if (t_ != Type::Array || i >= a_->size()) return null_value();
    return (*a_)[i];
}

std::size_t Value::size() const {
    if (t_ == Type::Array) return a_->size();
    if (t_ == Type::Object) return o_->size();
    return 0;
}

bool Value::has(const std::string& k) const { return t_ == Type::Object && o_->count(k) > 0; }

Value& Value::set(const std::string& k, Value v) {
    if (t_ != Type::Object) {
        t_ = Type::Object;
        o_ = std::make_shared<Object>();
    } else if (o_.use_count() > 1) {
        o_ = std::make_shared<Object>(*o_);     // yazarken kopyala
    }
    return (*o_)[k] = std::move(v);
}

Value& Value::push(Value v) {
    if (t_ != Type::Array) {
        t_ = Type::Array;
        a_ = std::make_shared<Array>();
    } else if (a_.use_count() > 1) {
        a_ = std::make_shared<Array>(*a_);
    }
    a_->push_back(std::move(v));
    return a_->back();
}

std::string Value::dump(int indent) const {
    std::string out;
    dump_to(out, indent, 0);
    return out;
}

void Value::dump_to(std::string& out, int indent, int depth) const {
    auto nl = [&](int d) {
        if (indent <= 0) return;
        out += '\n';
        out.append(static_cast<std::size_t>(indent * d), ' ');
    };
    switch (t_) {
        case Type::Null: out += "null"; break;
        case Type::Bool: out += b_ ? "true" : "false"; break;
        case Type::Number: {
            if (!std::isfinite(n_)) {
                out += "null";
                break;
            }
            char buf[40];
            if (n_ == std::floor(n_) && std::fabs(n_) < 1e15) std::snprintf(buf, sizeof buf, "%.0f", n_);
            else std::snprintf(buf, sizeof buf, "%.17g", n_);
            out += buf;
            break;
        }
        case Type::String: escape(out, s_); break;
        case Type::Array: {
            out += '[';
            bool first = true;
            for (const auto& v : *a_) {
                if (!first) out += ',';
                first = false;
                nl(depth + 1);
                v.dump_to(out, indent, depth + 1);
            }
            if (!a_->empty()) nl(depth);
            out += ']';
            break;
        }
        case Type::Object: {
            out += '{';
            bool first = true;
            for (const auto& [k, v] : *o_) {
                if (!first) out += ',';
                first = false;
                nl(depth + 1);
                escape(out, k);
                out += indent > 0 ? ": " : ":";
                v.dump_to(out, indent, depth + 1);
            }
            if (!o_->empty()) nl(depth);
            out += '}';
            break;
        }
    }
}

// ------------------------------------------------------------------------ ayrıştırıcı
namespace {
struct Parser {
    const std::string& s;
    std::size_t i = 0;
    std::string err;

    void ws() {
        while (i < s.size() && (s[i] == ' ' || s[i] == '\n' || s[i] == '\r' || s[i] == '\t')) ++i;
    }
    bool fail(const std::string& m) {
        if (err.empty()) err = m + " (konum " + std::to_string(i) + ")";
        return false;
    }
    static void utf8(std::string& out, unsigned cp) {
        if (cp < 0x80) out += static_cast<char>(cp);
        else if (cp < 0x800) {
            out += static_cast<char>(0xC0 | (cp >> 6));
            out += static_cast<char>(0x80 | (cp & 0x3F));
        } else {
            out += static_cast<char>(0xE0 | (cp >> 12));
            out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
            out += static_cast<char>(0x80 | (cp & 0x3F));
        }
    }
    bool str(std::string& out) {
        if (s[i] != '"') return fail("'\"' bekleniyordu");
        ++i;
        while (i < s.size()) {
            char c = s[i++];
            if (c == '"') return true;
            if (c == '\\') {
                if (i >= s.size()) break;
                char e = s[i++];
                switch (e) {
                    case '"': out += '"'; break;
                    case '\\': out += '\\'; break;
                    case '/': out += '/'; break;
                    case 'n': out += '\n'; break;
                    case 'r': out += '\r'; break;
                    case 't': out += '\t'; break;
                    case 'b': out += '\b'; break;
                    case 'f': out += '\f'; break;
                    case 'u': {
                        if (i + 4 > s.size()) return fail("eksik \\u");
                        unsigned cp = static_cast<unsigned>(std::strtoul(s.substr(i, 4).c_str(), nullptr, 16));
                        i += 4;
                        utf8(out, cp);
                        break;
                    }
                    default: return fail("geçersiz kaçış");
                }
            } else {
                out += c;
            }
        }
        return fail("kapanmayan metin");
    }
    bool value(Value& v, int depth) {
        if (depth > 200) return fail("çok derin iç içe yapı");
        ws();
        if (i >= s.size()) return fail("beklenmeyen son");
        const char c = s[i];
        if (c == '{') {
            ++i;
            v = Value::object();
            ws();
            if (i < s.size() && s[i] == '}') {
                ++i;
                return true;
            }
            while (true) {
                ws();
                std::string k;
                if (!str(k)) return false;
                ws();
                if (i >= s.size() || s[i] != ':') return fail("':' bekleniyordu");
                ++i;
                Value child;
                if (!value(child, depth + 1)) return false;
                v.set(k, std::move(child));
                ws();
                if (i < s.size() && s[i] == ',') { ++i; continue; }
                if (i < s.size() && s[i] == '}') { ++i; return true; }
                return fail("',' ya da '}' bekleniyordu");
            }
        }
        if (c == '[') {
            ++i;
            v = Value::array();
            ws();
            if (i < s.size() && s[i] == ']') {
                ++i;
                return true;
            }
            while (true) {
                Value child;
                if (!value(child, depth + 1)) return false;
                v.push(std::move(child));
                ws();
                if (i < s.size() && s[i] == ',') { ++i; continue; }
                if (i < s.size() && s[i] == ']') { ++i; return true; }
                return fail("',' ya da ']' bekleniyordu");
            }
        }
        if (c == '"') {
            std::string out;
            if (!str(out)) return false;
            v = Value(std::move(out));
            return true;
        }
        if (s.compare(i, 4, "true") == 0) { i += 4; v = Value(true); return true; }
        if (s.compare(i, 5, "false") == 0) { i += 5; v = Value(false); return true; }
        if (s.compare(i, 4, "null") == 0) { i += 4; v = Value(); return true; }
        if (c == '-' || (c >= '0' && c <= '9')) {
            const char* begin = s.c_str() + i;
            char* end = nullptr;
            const double d = std::strtod(begin, &end);
            if (end == begin) return fail("geçersiz sayı");
            i += static_cast<std::size_t>(end - begin);
            v = Value(d);
            return true;
        }
        return fail(std::string("beklenmeyen karakter '") + c + "'");
    }
};
}  // namespace

Result<Value> parse(const std::string& text) {
    Parser p{text, 0, {}};
    Value v;
    if (!p.value(v, 0)) return make_error(ErrorCode::Parse, "JSON hatası: " + p.err);
    p.ws();
    if (p.i != text.size()) return make_error(ErrorCode::Parse, "JSON sonunda fazladan veri");
    return v;
}

}  // namespace kozmo::json
