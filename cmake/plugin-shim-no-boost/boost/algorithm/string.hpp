// fork: build-time alias, not a librime header.
//
// Third-party plugins include <boost/algorithm/string.hpp> for one string
// helper (boost::starts_with on a metadata format tag). This fork already
// provides that helper under `namespace boost` in <rime/string_utils.hpp>, so
// this file — reachable only through the include directory added in
// plugins/CMakeLists.txt, and only where no real Boost headers exist — lets an
// unmodified plugin build against a Boost-free toolchain.
//
// It is deliberately never installed: the fork does not claim to provide Boost.
// This one is a fallback rather than an override -- plugins/CMakeLists.txt adds
// this directory only where the probe finds no real boost/algorithm/string.hpp,
// because boost::algorithm is header-only and a plugin that uses more than these
// two helpers (librime-charcode calls boost::split) needs the real library.
#ifndef RIME_PLUGIN_SHIM_BOOST_ALGORITHM_STRING_HPP_
#define RIME_PLUGIN_SHIM_BOOST_ALGORITHM_STRING_HPP_

#include <rime/string_utils.hpp>

#endif  // RIME_PLUGIN_SHIM_BOOST_ALGORITHM_STRING_HPP_
