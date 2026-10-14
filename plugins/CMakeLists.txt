set(RIME_SOURCE_DIR ${PROJECT_SOURCE_DIR})

# fork: a plugin we do not own can still ask for <boost/algorithm/string.hpp>
# just to call boost::starts_with. <rime/string_utils.hpp> already provides that
# name, so on a toolchain that has no Boost at all (every platform in this CI)
# the include is answered from cmake/plugin-shim. Where real Boost headers exist
# it is left alone, and the check is a header probe rather than find_package(Boost)
# because this tree configures without Boost entirely. The shim sits under cmake/,
# not here: the discovery loop below reads every directory in this one as a plugin.
include(CheckIncludeFileCXX)
check_include_file_cxx(boost/algorithm/string.hpp RIME_HAVE_BOOST_ALGORITHM_STRING)
if(NOT RIME_HAVE_BOOST_ALGORITHM_STRING)
  message(STATUS "No boost/algorithm/string.hpp: plugins use the rime shim")
  include_directories(${RIME_SOURCE_DIR}/cmake/plugin-shim)
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
