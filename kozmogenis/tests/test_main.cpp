#include "test_framework.hpp"

int main() {
    int failed_cases = 0;
    for (auto& c : kt::cases()) {
        const int before = kt::failures();
        c.fn();
        const bool ok = kt::failures() == before;
        if (!ok) ++failed_cases;
        std::printf("%s %s\n", ok ? "[ OK ]" : "[FAIL]", c.name);
    }
    std::printf("\n%zu test, %d kontrol, %d başarısız kontrol, %d başarısız test\n", kt::cases().size(), kt::checks(),
                kt::failures(), failed_cases);
    return kt::failures() == 0 ? 0 : 1;
}
