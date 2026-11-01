if(DEVILUTIONX_STATIC_SDL3)
  set(BUILD_SHARED_LIBS OFF)
  set(SDL_SHARED OFF)
  set(SDL_STATIC ON)
  if(PIE)
    set(SDL_STATIC_PIC ON)
  endif()
else()
  set(BUILD_SHARED_LIBS ON)
  set(SDL_SHARED ON)
  set(SDL_STATIC OFF)
endif()
set(SDL_TEST_ENABLED_BY_DEFAULT OFF)

include(functions/FetchContent_ExcludeFromAll_backport)
include(FetchContent)

FetchContent_Declare(SDL3
  URL https://github.com/libsdl-org/SDL/archive/570f72297b7da622a21d541bb4673b03c58bc863.tar.gz
  URL_HASH SHA256=1a785df6d5420d669e7246944e23bc4e442f8ff6b4a51e048caeba90845a06dc
)
FetchContent_MakeAvailable_ExcludeFromAll(SDL3)

# SDL's public GPU API has no timestamp queries at this pinned revision.
# Compile its unchanged D3D12 backend through our narrow bridge translation unit.
if(WIN32 AND TARGET SDL3-static)
  set(_d1r_d3d12 "${sdl3_SOURCE_DIR}/src/gpu/d3d12/SDL_gpu_d3d12.c")
  get_target_property(_d1r_sdl_sources SDL3-static SOURCES)
  list(REMOVE_ITEM _d1r_sdl_sources "${_d1r_d3d12}")
  set_property(TARGET SDL3-static PROPERTY SOURCES "${_d1r_sdl_sources}")
  target_sources(SDL3-static PRIVATE "${PROJECT_SOURCE_DIR}/Source/reincarnated/sdl_d3d12_bridge.c")
  target_include_directories(SDL3-static PRIVATE "${sdl3_SOURCE_DIR}/src/gpu/d3d12")
  target_compile_definitions(SDL3-static INTERFACE D1R_SDL_D3D12_BRIDGE)
endif()
