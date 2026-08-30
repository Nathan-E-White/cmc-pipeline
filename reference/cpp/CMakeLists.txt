cmake_minimum_required(VERSION 3.20)
project(cmc_reference_mesh_audit LANGUAGES CXX)

find_path(GMSH_INCLUDE_DIR gmsh.h REQUIRED)
find_library(GMSH_LIBRARY NAMES gmsh REQUIRED)

add_executable(mesh-audit src/mesh_audit.cpp)
target_compile_features(mesh-audit PRIVATE cxx_std_20)
target_include_directories(mesh-audit PRIVATE ${GMSH_INCLUDE_DIR})
target_link_libraries(mesh-audit PRIVATE ${GMSH_LIBRARY})

include(CTest)
if(BUILD_TESTING)
  add_test(NAME mesh_audit_requires_arguments COMMAND mesh-audit)
  set_tests_properties(mesh_audit_requires_arguments PROPERTIES WILL_FAIL TRUE)
endif()

install(TARGETS mesh-audit RUNTIME DESTINATION bin)
