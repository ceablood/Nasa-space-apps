cmake_minimum_required(VERSION 3.16)
project(KozmoCore LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(MSVC)
  add_compile_options(/W4 /permissive- /utf-8)
else()
  add_compile_options(-Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wno-sign-conversion)
endif()

file(GLOB KOZMO_SOURCES CONFIGURE_DEPENDS core/src/*.cpp)
add_library(kozmocore STATIC ${KOZMO_SOURCES})
target_include_directories(kozmocore PUBLIC core/include)

file(GLOB KOZMO_TESTS CONFIGURE_DEPENDS tests/test_*.cpp)
add_executable(kozmo_tests ${KOZMO_TESTS})
target_link_libraries(kozmo_tests PRIVATE kozmocore)

enable_testing()
add_test(NAME kozmo_tests COMMAND kozmo_tests)

if(EXISTS ${CMAKE_SOURCE_DIR}/tools/kozmo_cli.cpp)
  add_executable(kozmo_cli tools/kozmo_cli.cpp)
  target_link_libraries(kozmo_cli PRIVATE kozmocore)
endif()

# Unreal Engine uyumluluk denetimi: UE modülleri RTTI ve C++ istisnaları kapalı derlenir.
# Çekirdek bu bayraklarla da derlenmeli (UE katmanı aynı kaynakları içerir).
option(KOZMO_UE_COMPAT_CHECK "Çekirdeği -fno-rtti -fno-exceptions ile ayrıca derle" ON)
if(KOZMO_UE_COMPAT_CHECK AND NOT MSVC)
  add_library(kozmocore_uecheck STATIC ${KOZMO_SOURCES})
  target_include_directories(kozmocore_uecheck PUBLIC core/include)
  target_compile_options(kozmocore_uecheck PRIVATE -fno-rtti -fno-exceptions)
endif()
