cmake_minimum_required(VERSION 3.25)
project(re_lab LANGUAGES CXX)

# Every sample is built twice, unoptimised (O0) and optimised (O2), so the
# same source can be compared in a disassembler at both levels. Each build is
# checked against the sample's facts.json by tools/verify.py.

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
foreach(config Debug Release RelWithDebInfo MinSizeRel)
    string(TOUPPER ${config} upper)
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_${upper} ${CMAKE_BINARY_DIR}/bin)
endforeach()

# Optimisation is chosen per target below, so the build type adds nothing.
foreach(config DEBUG RELEASE RELWITHDEBINFO MINSIZEREL)
    set(CMAKE_CXX_FLAGS_${config} "")
endforeach()

find_package(Python3 3.9 REQUIRED COMPONENTS Interpreter)
enable_testing()

if(MSVC)
    set(RE_LAB_TOOLCHAIN msvc)
    set(RE_LAB_FLAGS_O0 /Od /W4 /EHsc)
    set(RE_LAB_FLAGS_O2 /O2 /W4 /EHsc)
    set(RE_LAB_LINK_FLAGS /DEBUG /INCREMENTAL:NO)
else()
    set(RE_LAB_TOOLCHAIN gcc)
    # -fno-pie keeps addresses in listings stable and easy to read.
    set(RE_LAB_FLAGS_O0 -O0 -g -Wall -Wextra -fno-pie)
    set(RE_LAB_FLAGS_O2 -O2 -g -Wall -Wextra -fno-pie)
    set(RE_LAB_LINK_FLAGS -no-pie)
endif()

function(re_lab_sample name)
    set(dir ${CMAKE_CURRENT_SOURCE_DIR}/samples/${name})
    foreach(level O0 O2)
        set(target ${name}_${level})
        add_executable(${target} ${dir}/main.cpp)
        set_target_properties(${target} PROPERTIES
            MSVC_RUNTIME_LIBRARY MultiThreaded
            MSVC_DEBUG_INFORMATION_FORMAT ProgramDatabase)
        target_compile_options(${target} PRIVATE ${RE_LAB_FLAGS_${level}})
        target_link_options(${target} PRIVATE ${RE_LAB_LINK_FLAGS})
        add_test(NAME ${target}
            COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tools/verify.py
                    --facts ${dir}/facts.json
                    --binary $<TARGET_FILE:${target}>
                    --level ${level}
                    --toolchain ${RE_LAB_TOOLCHAIN}
                    --listings ${CMAKE_BINARY_DIR}/listings)
    endforeach()
endfunction()

re_lab_sample(01_vtables)
re_lab_sample(02_crackme)
re_lab_sample(03_exceptions)
re_lab_sample(04_optimization)
