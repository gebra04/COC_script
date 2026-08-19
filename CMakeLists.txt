cmake_minimum_required(VERSION 3.20)
project(GymAIDigitalTwin VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Cross-Platform build configurations
if(ANDROID)
    message(STATUS "[*] Configuring for Android NDK (AArch64/x86_64)")
    # Additional NDK flags could be added here if needed
elseif(UNIX AND NOT APPLE)
    message(STATUS "[*] Configuring for Linux POSIX")
elseif(WIN32)
    message(STATUS "[*] Configuring for Windows MSVC / Win32")
endif()

# Include Directories
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/native/include)

# Native Middleware Source Files (Layer 1)
set(LAYER1_SOURCES
    native/src/layer1_native_hook.cpp
)

# Create Static Library for Layer 1 (can be changed to SHARED for Android .so later)
add_library(layer1_native_hook STATIC ${LAYER1_SOURCES})

# Target Specific Compiler Flags
if(MSVC)
    target_compile_options(layer1_native_hook PRIVATE /W4 /WX-)
else()
    target_compile_options(layer1_native_hook PRIVATE -Wall -Wextra -Wno-unused-parameter)
endif()

# Test Executable for Layer 1
add_executable(main_test_layer1 native/src/main_test_layer1.cpp)
target_link_libraries(main_test_layer1 layer1_native_hook)

# Middleware Application (Layers 1-3): native server that runs inside Waydroid
# and bridges the game engine to the Python host via zero-copy shared memory.
# Header-only Layers 2/3 (layer2_forensic_heap.hpp / layer3_ipc_bridge.hpp) plus
# the static Layer 1 library. POSIX-only (memfd_create / SCM_RIGHTS / eventfd).
if(UNIX AND NOT APPLE)
    add_executable(coc_dt_middleware native/src/middleware_main.cpp)
    target_link_libraries(coc_dt_middleware layer1_native_hook)
    if(NOT MSVC)
        target_compile_options(coc_dt_middleware PRIVATE -Wall -Wextra -Wno-unused-parameter)
    endif()
    find_package(Threads REQUIRED)
    target_link_libraries(coc_dt_middleware Threads::Threads)
endif()
