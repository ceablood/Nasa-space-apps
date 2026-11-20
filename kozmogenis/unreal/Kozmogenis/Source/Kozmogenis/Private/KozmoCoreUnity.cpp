// KozmoCore kaynaklarını Unreal modülüne tek derleme birimi olarak dahil eder.
// Çekirdek kendi CMake projesinde -fno-rtti -fno-exceptions ile de derlenip test edilir (bkz. kozmogenis/CMakeLists.txt).
#include "CoreMinimal.h"

THIRD_PARTY_INCLUDES_START
#include "../../../../../core/src/core.cpp"
#include "../../../../../core/src/astro.cpp"
#include "../../../../../core/src/propulsion.cpp"
#include "../../../../../core/src/economy.cpp"
#include "../../../../../core/src/json.cpp"
#include "../../../../../core/src/colony.cpp"
#include "../../../../../core/src/research.cpp"
#include "../../../../../core/src/game.cpp"
THIRD_PARTY_INCLUDES_END
