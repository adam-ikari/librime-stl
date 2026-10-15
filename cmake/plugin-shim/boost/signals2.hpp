// fork: build-time alias, not a librime header.
//
// librime-lua names `boost::signals2::connection` when it registers the handle
// returned by `notifier:connect()` (src/types.cc:1480, and the ConnectionReg
// methods bound at :1485). It never includes the header that declares that name:
// upstream librime's <rime/common.h> pulled <boost/signals2.hpp> in
// transitively, and this fork's common.h provides <rime/signal.hpp> instead. So
// the plugin's type name has to resolve to that same replacement signal, and the
// only thing missing on the engine side was the grouped connect overload the
// plugin's binding passes a slot group through -- <rime/signal.hpp> has it, with
// signals2's ordering (ascending group, connection order within a group).
//
// It is deliberately never installed, and reachable only through the include
// directory added in plugins/CMakeLists.txt: a header in src/ that opens
// `namespace boost` would, for a consumer that does have Boost, put two
// different boost::signals2::connection types in one program.
#ifndef RIME_PLUGIN_SHIM_BOOST_SIGNALS2_HPP_
#define RIME_PLUGIN_SHIM_BOOST_SIGNALS2_HPP_

#include <rime/signal.hpp>

namespace boost {
namespace signals2 {

using ::rime::connection;

}  // namespace signals2
}  // namespace boost

#endif  // RIME_PLUGIN_SHIM_BOOST_SIGNALS2_HPP_
