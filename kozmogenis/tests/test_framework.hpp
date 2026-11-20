// Küçük, bağımlılıksız test çerçevesi (KozmoCore yalnızca standart C++17 kullanır).
#pragma once
#include <cmath>
#include <cstdio>
#include <functional>
#include <string>
#include <vector>

namespace kt {
struct Case { const char* name; std::function<void()> fn; };
inline std::vector<Case>& cases() { static std::vector<Case> c; return c; }
inline int& failures() { static int f = 0; return f; }
inline int& checks() { static int c = 0; return c; }
struct Reg { Reg(const char* n, std::function<void()> f) { cases().push_back({n, std::move(f)}); } };
inline void fail(const char* file, int line, const std::string& what) {
    ++failures();
    std::printf("  BAŞARISIZ %s:%d  %s\n", file, line, what.c_str());
}
}  // namespace kt

#define KT_CAT2(a, b) a##b
#define KT_CAT(a, b) KT_CAT2(a, b)
#define TEST(name) \
    static void KT_CAT(test_fn_, __LINE__)(); \
    static kt::Reg KT_CAT(test_reg_, __LINE__)(name, KT_CAT(test_fn_, __LINE__)); \
    static void KT_CAT(test_fn_, __LINE__)()
#define CHECK(cond) do { ++kt::checks(); if (!(cond)) kt::fail(__FILE__, __LINE__, #cond); } while (0)
#define CHECK_NEAR(a, b, tol) do { ++kt::checks(); double _a = (a), _b = (b); \
    if (!(std::fabs(_a - _b) <= (tol))) kt::fail(__FILE__, __LINE__, std::string(#a " ~ " #b "  (") + \
        std::to_string(_a) + " vs " + std::to_string(_b) + ")"); } while (0)
