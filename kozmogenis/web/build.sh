#!/usr/bin/env bash
# KozmoCore'u (Unreal sürümüyle aynı C++ çekirdek) WebAssembly'ye derler: web/dist/kozmo.js + kozmo.wasm
# Gerekli: Emscripten (emsdk). Kullanım: EMSDK=/yol/emsdk ./web/build.sh
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v em++ >/dev/null 2>&1; then
  if [ -n "${EMSDK:-}" ] && [ -f "$EMSDK/emsdk_env.sh" ]; then source "$EMSDK/emsdk_env.sh" >/dev/null; else echo "em++ bulunamadı (EMSDK ayarla)"; exit 1; fi
fi
FUNCS='["_kz_version","_kz_new","_kz_tick","_kz_state","_kz_cmd","_kz_buildings","_kz_environment","_kz_management","_kz_porkchop","_kz_save","_kz_load","_kz_mesh_vertices","_kz_mesh_normals","_kz_mesh_indices","_kz_mesh_vertex_count","_kz_mesh_index_count","_kz_height","_malloc","_free"]'
em++ -std=c++17 -O3 -flto -fno-exceptions -fno-rtti -Icore/include core/src/*.cpp web/src/kozmo_web.cpp \
  -sMODULARIZE=1 -sEXPORT_ES6=1 -sEXPORT_NAME=KozmoCore -sALLOW_MEMORY_GROWTH=1 -sINITIAL_MEMORY=33554432 -sENVIRONMENT=web \
  -sEXPORTED_FUNCTIONS="$FUNCS" -sEXPORTED_RUNTIME_METHODS='["ccall","cwrap","UTF8ToString","HEAPF32","HEAPU32"]' \
  -sFILESYSTEM=0 -sASSERTIONS=0 -o web/dist/kozmo.js
ls -la web/dist/kozmo.js web/dist/kozmo.wasm
