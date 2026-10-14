# fork: dependency provenance.
#
# Three build graphs consume the same third-party libraries out of this one tree,
# and until now nothing said which copy a build actually got:
#
#   A  host/desktop engine -- `make` into build/, deps from system packages on
#      Linux/Docker/MinGW (action-install-linux.sh) or from `make deps`, which
#      deps.mk installs into the repo's own include/ lib/ share/ (prefix ?=
#      $(rime_root)) and CMakeLists.txt then puts on CMAKE_PREFIX_PATH.
#   B  the Android cross build -- build/android-<abi>/ with a private $prefix,
#      every dep rebuilt from deps/<dep> by build-android.sh.
#   C  the dictionary toolchain -- dict/tools/.build/, a host build of opencc
#      with OPENCC_BUILD_DATA=ON whose opencc_dict generates dict/opencc/*.ocd2.
#
# The confusion is not hypothetical: a build of A on a machine with a distro
# opencc links 1.1.3 while C generated the committed .ocd2 with the pinned
# 1.1.9, and the soname is `libopencc.so.1.1` for both, so nothing downstream
# could tell. `librime.so`'s NEEDED entries and the configure log stayed silent.
#
# So: always report where each dependency resolved to and what version the
# resolved opencc claims, and -- when a build declares a dependency prefix with
# -DRIME_DEPS_PREFIX -- fail if any resolved path lives outside it. Provenance is
# checked by path, not by search order, because A already injects
# ${PROJECT_SOURCE_DIR} into CMAKE_PREFIX_PATH and no ordering survives that.

# The pin lives in the vendored tree, which is committed (deps/opencc is not a
# submodule), so it is readable on every checkout -- including a non-recursive
# one, where the submodules are empty. Read it; never restate it as a literal.
function(rime_read_opencc_pin)
  set(version_lines "")
  set(pin_file "${PROJECT_SOURCE_DIR}/deps/opencc/CMakeLists.txt")
  if(EXISTS "${pin_file}")
    file(STRINGS "${pin_file}" version_lines
         REGEX "^set *\\( *OPENCC_VERSION_(MAJOR|MINOR|REVISION)")
  endif()
  set(components MAJOR MINOR REVISION)
  set(pin "")
  foreach(component ${components})
    set(value "")
    foreach(line ${version_lines})
      if(line MATCHES "OPENCC_VERSION_${component} +([0-9]+)")
        set(value "${CMAKE_MATCH_1}")
      endif()
    endforeach()
    if(value STREQUAL "")
      set(pin "unknown")
      break()
    endif()
    set(pin "${pin}${pin_sep}${value}")
    set(pin_sep ".")
  endforeach()
  if(pin STREQUAL "")
    set(pin "unknown")
  endif()
  set(RIME_OPENCC_PIN "${pin}" PARENT_SCOPE)
endfunction()

# Version of the opencc a find module actually resolved to.
#
# opencc exposes no version macro in its installed headers (opencc.h and
# opencc_config.h carry none), so the only usable records are the packaging
# metadata next to the resolved library: the pkg-config file, which both the
# vendored install and the distro packages ship, and the CMake package version
# file, which the vendored install writes (deps/opencc/CMakeLists.txt) but the
# Debian one does not. "unknown" is a real answer and is reported as one -- in
# hermetic mode it fails, because an unverified version proves nothing.
function(rime_detect_opencc_version)
  set(version "unknown")
  set(opencc_pc "")
  set(opencc_config_version "")

  if(Opencc_LIBRARY)
    get_filename_component(lib_dir "${Opencc_LIBRARY}" DIRECTORY)
    foreach(candidate
        "${lib_dir}/pkgconfig/opencc.pc"
        "${lib_dir}/../pkgconfig/opencc.pc")
      if(EXISTS "${candidate}")
        set(opencc_pc "${candidate}")
        break()
      endif()
    endforeach()
    file(GLOB config_version_candidates
         "${lib_dir}/cmake/opencc/OpenCCConfigVersion.cmake"
         "${lib_dir}/../cmake/opencc/OpenCCConfigVersion.cmake")
    if(config_version_candidates)
      list(GET config_version_candidates 0 opencc_config_version)
    endif()
  endif()

  if(opencc_pc)
    file(STRINGS "${opencc_pc}" version_lines REGEX "^Version:")
    if(version_lines)
      list(GET version_lines 0 version_line)
      string(REGEX REPLACE "^Version:[ ]*([^ ]+).*" "\\1" version "${version_line}")
    endif()
  elseif(opencc_config_version)
    file(STRINGS "${opencc_config_version}" version_lines
         REGEX "^set *\(*PACKAGE_VERSION")
    if(version_lines)
      list(GET version_lines 0 version_line)
      string(REGEX REPLACE "^set *\\( *PACKAGE_VERSION +\"([^\"]+)\".*" "\\1"
             version "${version_line}")
    endif()
  endif()

  # A Debug build of the vendored opencc installs itself as `1.1.9.Debug`.
  string(REGEX REPLACE "^([0-9]+\\.[0-9]+\\.[0-9]+).*$" "\\1" version "${version}")
  set(Opencc_VERSION "${version}" PARENT_SCOPE)
endfunction()

# Deps whose resolved paths are the provenance question. X11/keysym.h is
# deliberately absent: it is vendored into this repo's include/ and is not a
# dependency anyone installs.
set(RIME_PROVENANCE_DEPS Gflags Glog LevelDb Marisa Opencc YamlCpp)

# GTest comes from CMake's own FindGTest, which names its results differently and
# sometimes holds keywords (`debug`, `optimized`) rather than paths. It is a
# test-only dependency, but a build that claims to be hermetic should not be
# quietly taking its gtest from the distro either.
set(RIME_PROVENANCE_EXTRA_VARS GTEST_INCLUDE_DIRS GTEST_LIBRARIES GTEST_MAIN_LIBRARIES)

function(rime_report_dep_provenance)
  message(STATUS "rime dependency provenance (RIME_DEPS_PREFIX='${RIME_DEPS_PREFIX}')")
  foreach(dep ${RIME_PROVENANCE_DEPS})
    if(dep STREQUAL "Opencc")
      set(extra " [resolved ${Opencc_VERSION} / vendored pin ${RIME_OPENCC_PIN}]")
    else()
      set(extra "")
    endif()
    message(STATUS "  ${dep}: include='${${dep}_INCLUDE_PATH}' library='${${dep}_LIBRARY}'${extra}")
  endforeach()
  if(GTEST_INCLUDE_DIRS OR GTEST_LIBRARIES)
    message(STATUS "  GTest: include='${GTEST_INCLUDE_DIRS}' library='${GTEST_LIBRARIES}'")
  endif()
  # librime has no compile-time notion of an opencc data directory; it resolves
  # <shared_data_dir>/opencc/<config> at runtime (src/rime/gear/simplifier.cc).
  # The only build-time consumer of an opencc dict dir is rime_test, which
  # test/CMakeLists.txt pins to the committed test/opencc fixture.
  message(STATUS "  opencc data: engine: none (runtime <shared_data_dir>/opencc/); rime_test: test/opencc fixture")
endfunction()

# Appends to the offenders list when ${path} is not under the prefix probe set by
# rime_assert_deps_hermetic(). A macro because it has to mutate that caller-side
# list; CMake functions would need PARENT_SCOPE per variable.
macro(rime_check_dep_path label path)
  if(NOT "${${path}}" STREQUAL "")
    foreach(_candidate ${${path}})
      # FindGTest interleaves keywords with paths in its *_LIBRARIES lists.
      if(_candidate STREQUAL "debug" OR _candidate STREQUAL "optimized"
         OR _candidate STREQUAL "general")
        continue()
      endif()
      file(TO_CMAKE_PATH "${_candidate}" _candidate_path)
      # Bare library names (`gtest`) are not provenance evidence; only absolute
      # paths -- with a leading / or a Windows drive -- can be checked.
      if(NOT _candidate_path MATCHES "^(/|[A-Za-z]:)")
        continue()
      endif()
      string(FIND "${_candidate_path}" "${_RIME_HERMETIC_PREFIX_PROBE}" _at)
      if(_at EQUAL 0)
        continue()
      endif()
      # Windows filesystems are case-insensitive; two spellings of one path must
      # not look like a leak.
      if(WIN32)
        string(TOLOWER "${_candidate_path}" _candidate_lower)
        string(FIND "${_candidate_lower}" "${_RIME_HERMETIC_PREFIX_LOWER}" _at_lower)
        if(_at_lower EQUAL 0)
          continue()
        endif()
      endif()
      set(_RIME_HERMETIC_OFFENDERS
          "${_RIME_HERMETIC_OFFENDERS}\n  ${label}=${_candidate_path}")
    endforeach()
  endif()
endmacro()

function(rime_assert_deps_hermetic)
  if(RIME_DEPS_PREFIX STREQUAL "")
    if(NOT (Opencc_VERSION STREQUAL RIME_OPENCC_PIN))
      message(WARNING
        "This build links opencc ${Opencc_VERSION} but the dictionary data in "
        "dict/opencc/ was generated by the vendored opencc ${RIME_OPENCC_PIN} "
        "(dict/tools/.build, OPENCC_BUILD_DATA=ON). Configure against a prefix "
        "holding the vendored build -- `make deps prefix=<dir>` plus "
        "-DRIME_DEPS_PREFIX=<dir> -- to get that checked. "
        "Resolved opencc: ${Opencc_LIBRARY}")
    endif()
    return()
  endif()

  file(TO_CMAKE_PATH "${RIME_DEPS_PREFIX}" _prefix)
  string(REGEX REPLACE "/$" "" _prefix "${_prefix}")
  set(_RIME_HERMETIC_PREFIX_PROBE "${_prefix}/")
  string(TOLOWER "${_RIME_HERMETIC_PREFIX_PROBE}" _RIME_HERMETIC_PREFIX_LOWER)
  set(_RIME_HERMETIC_OFFENDERS "")
  foreach(dep ${RIME_PROVENANCE_DEPS})
    rime_check_dep_path("${dep}_INCLUDE_PATH" ${dep}_INCLUDE_PATH)
    rime_check_dep_path("${dep}_LIBRARY" ${dep}_LIBRARY)
  endforeach()
  foreach(var ${RIME_PROVENANCE_EXTRA_VARS})
    rime_check_dep_path("${var}" ${var})
  endforeach()
  set(offenders "${_RIME_HERMETIC_OFFENDERS}")
  string(REGEX REPLACE "^\n+" "" offenders "${offenders}")

  if(offenders)
    message(FATAL_ERROR
      "RIME_DEPS_PREFIX='${RIME_DEPS_PREFIX}' says this build must take every "
      "dependency from that prefix, but these resolved paths live outside it:"
      "\n${offenders}\n"
      "A dependency leaking in from outside the prefix is how a build ends up "
      "linking an opencc other than the vendored pin that generated dict/opencc/.")
  endif()

  if(NOT Opencc_VERSION STREQUAL RIME_OPENCC_PIN)
    message(FATAL_ERROR
      "Hermetic build resolved opencc ${Opencc_VERSION} "
      "(${Opencc_LIBRARY}) but deps/opencc is pinned at ${RIME_OPENCC_PIN}. "
      "The committed .ocd2 tables in dict/opencc/ come from the pinned one, so "
      "either the prefix holds a stale build or the find modules hit a system "
      "install.")
  endif()
  message(STATUS "rime dependencies are hermetic to ${RIME_DEPS_PREFIX} (opencc ${Opencc_VERSION})")
endfunction()
