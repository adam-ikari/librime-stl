// fork: build-time shim, not a librime header.
//
// librime-lua includes <boost/regex.hpp> unconditionally (src/types.cc:22) and
// uses it in three Lua-callable functions: regex_search, regex_match and
// regex_replace. Its Boost use there is an API shape, not a semantic dependency
// -- so the shape is answered from std::regex, through the same PCRE translation
// every runtime regex entry point in this engine already goes through
// (src/rime/pcre_translator.hpp).
//
// Where this is NOT equivalent, and the difference is a deliberate one:
// boost::regex defaults to the perl grammar, which accepts constructs ECMAScript
// has no spelling for -- lookbehind, possessive and atomic quantifiers, \p{...}.
// Such a pattern raises std::regex_error at construction instead of matching.
// That is the policy this fork already applies to schema patterns: an
// unsupported pattern fails loudly rather than silently matching something else.
// The replacement format string is not affected: `$1`/`$&` mean the same thing
// in ECMAScript as in boost::regex, and iterating a match yields sub_matches that
// convert to std::string the way the plugin's `for (auto str : sm)` expects.
//
// Never installed. Reachable through the include directory that
// plugins/CMakeLists.txt adds unconditionally, so this is the answer in every
// graph: binding the plugin to a real <boost/regex.hpp> instead leaves it with
// boost symbols this fork's librime does not provide.
#ifndef RIME_PLUGIN_SHIM_BOOST_REGEX_HPP_
#define RIME_PLUGIN_SHIM_BOOST_REGEX_HPP_

#include <regex>
#include <string>

#include <rime/pcre_translator.hpp>

namespace boost {

using ::std::smatch;

class regex : public std::regex {
 public:
  explicit regex(const std::string& pattern)
      : std::regex(rime::TranslatePcreClasses(pattern), std::regex::ECMAScript) {}
  explicit regex(const char* pattern) : regex(std::string(pattern)) {}
};

inline bool regex_search(const std::string& target,
                         ::std::smatch& matches,
                         const regex& expression) {
  return std::regex_search(target, matches, expression);
}

inline bool regex_match(const std::string& target, const regex& expression) {
  return std::regex_match(target, expression);
}

inline std::string regex_replace(const std::string& target,
                                 const regex& expression,
                                 const std::string& format) {
  return std::regex_replace(target, expression, format);
}

}  // namespace boost

#endif  // RIME_PLUGIN_SHIM_BOOST_REGEX_HPP_
