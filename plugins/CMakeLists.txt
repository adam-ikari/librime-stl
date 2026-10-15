set(RIME_SOURCE_DIR ${PROJECT_SOURCE_DIR})

# fork: a plugin we do not own asks for Boost headers by name -- librime-lua for
# <boost/regex.hpp> (three Lua-callable functions), octagram and predict and
# plugins_module.cc for <boost/algorithm/string.hpp> (only boost::starts_with).
# The plugin cannot be edited, so the answer comes from the include path, and
# cmake/ holds it because the discovery loop below reads every directory in this
# one as a plugin.
#
# Two sets, because the two headers need different conditions.
#
# cmake/plugin-shim is always on the path. Overriding <boost/regex.hpp> even
# where real Boost headers exist is not a style choice: this fork's librime no
# longer carries boost_regex, which upstream did -- that is why librime-lua has
# never linked it. Bind the plugin to /usr/include/boost/regex.hpp and a merged
# build fails to link the tools against boost::re_detail_...::raise_runtime_error,
# while a standalone one links and then dies at dlopen on undefined boost symbols
# with no libboost_regex in NEEDED (both measured on a machine with libboost-dev
# installed). The directory only shadows the headers it lists; a plugin asking for
# anything else still gets real Boost where one exists -- librime-charcode's
# boost::locale and boost::asio in the Docker graph are the live cases.
include_directories(${RIME_SOURCE_DIR}/cmake/plugin-shim)

# cmake/plugin-shim-no-boost is a fallback, not an override: boost::algorithm is
# header-only, so where a real Boost exists it is the better answer, and shadowing
# it would break a plugin that uses more than the two helpers we cover
# (librime-charcode calls boost::split and boost::is_any_of). The stub exists so a
# Boost-free toolchain -- every platform in this CI -- can still build the plugins.
# The check is a header probe rather than find_package(Boost) because this tree
# configures without Boost entirely.
include(CheckIncludeFileCXX)
check_include_file_cxx(boost/algorithm/string.hpp RIME_HAVE_BOOST_ALGORITHM_STRING)
if(NOT RIME_HAVE_BOOST_ALGORITHM_STRING)
  message(STATUS "No boost/algorithm/string.hpp: plugins use the rime fallback shim")
  include_directories(${RIME_SOURCE_DIR}/cmake/plugin-shim-no-boost)
endif()

# fork: librime-lua names boost::signals2::connection (src/types.cc:1480, and the
# methods it binds at :1485) without including anything that declares the name --
# upstream librime's <rime/common.h> pulled <boost/signals2.hpp> in transitively,
# and this fork's common.h provides <rime/signal.hpp> instead. Without the name,
# the plugin does not compile even on a machine that has real Boost, because
# boost/regex.hpp does not declare signals2 either.
#
# So the alias is force-included into every C++ plugin translation unit, and
# applied whether or not Boost exists here: the type the plugin must name is
# rime::connection in every graph, because the engine's signals are rime::signal
# even where Boost is installed. A per-plugin list would be the smaller hammer,
# but reaching the plugin's own object target means naming an internal target of
# a repository we do not own. Safe because no plugin includes <boost/signals2.hpp>
# -- checked across plugins/*/src in octagram, predict and librime-lua -- so the
# aliased members are never followed by a second definition of the same names.
#
# C++ only, and that is not decoration: librime-lua compiles the Lua sources
# (lapi.c and friends) in the same directory scope, and force-including a C++
# header into them fails on the first #include <functional>.
if(MSVC)
  add_compile_options(
    $<$<COMPILE_LANGUAGE:CXX>:/FI${RIME_SOURCE_DIR}/cmake/plugin-shim/boost/signals2.hpp>)
else()
  add_compile_options(
    $<$<COMPILE_LANGUAGE:CXX>:-include>
    $<$<COMPILE_LANGUAGE:CXX>:${RIME_SOURCE_DIR}/cmake/plugin-shim/boost/signals2.hpp>)
endif()

# work around CMake build issues on macOS
set(rime_plugin_boilerplate_src "plugin.cc")

set(plugins_module_src "plugins_module.cc")

unset(plugins_objs)
unset(plugins_deps)
unset(plugins_modules)

if(ENABLE_EXTERNAL_PLUGINS)
  add_library(rime-plugins-objs OBJECT ${plugins_module_src})
  if(BUILD_SHARED_LIBS)
    set_target_properties(rime-plugins-objs
      PROPERTIES
      POSITION_INDEPENDENT_CODE ON)
  endif()

  set(plugins_objs ${plugins_objs} $<TARGET_OBJECTS:rime-plugins-objs>)
  set(plugins_modules ${plugins_modules} "plugins")
endif()

if(DEFINED ENV{RIME_PLUGINS})
  set(plugins $ENV{RIME_PLUGINS})
  message(STATUS "Prescribed plugins: ${plugins}")
  if(NOT "${plugins}" STREQUAL "")
    string(REGEX REPLACE "@[^ ]*" "" plugins ${plugins})
    string(REGEX REPLACE "[^ ]*/(librime-)?" "" plugins ${plugins})
    string(REPLACE " " ";" plugins ${plugins})
  endif()
else()
  file(GLOB plugin_files "*")
  foreach(file ${plugin_files})
    if(IS_DIRECTORY ${file})
      message(STATUS "Found plugin: ${file}")
      set(plugins ${plugins} ${file})
    endif()
  endforeach(file)
endif()

foreach(plugin ${plugins})
  unset(plugin_name)
  unset(plugin_objs)
  unset(plugin_deps)
  unset(plugin_modules)
  add_subdirectory(${plugin})
  if(BUILD_MERGED_PLUGINS)
    set(plugins_objs ${plugins_objs} ${plugin_objs})
    list(REMOVE_ITEM plugin_deps ${rime_library})
    set(plugins_deps ${plugins_deps} ${plugin_deps})
    set(plugins_modules ${plugins_modules} ${plugin_modules})
  else()
    message(STATUS "Plugin ${plugin_name} provides modules: ${plugin_modules}")
    add_library(${plugin_name} ${rime_plugin_boilerplate_src} ${plugin_objs})
    target_link_libraries(${plugin_name} ${plugin_deps})
    set_target_properties(${plugin_name}
      PROPERTIES
      LIBRARY_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/lib/${RIME_PLUGINS_DIR}
      RUNTIME_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/bin/${RIME_PLUGINS_DIR})
    if(XCODE_VERSION)
      set_target_properties(${plugin_name} PROPERTIES INSTALL_NAME_DIR "@rpath")
    endif(XCODE_VERSION)
    install(TARGETS ${plugin_name} DESTINATION ${CMAKE_INSTALL_FULL_LIBDIR}/${RIME_PLUGINS_DIR})
  endif()
endforeach(plugin)

set(rime_plugins_objs ${plugins_objs} PARENT_SCOPE)
set(rime_plugins_deps ${plugins_deps} PARENT_SCOPE)
set(rime_plugins_modules ${plugins_modules} PARENT_SCOPE)
