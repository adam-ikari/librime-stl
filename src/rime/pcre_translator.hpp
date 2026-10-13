//
// fork: PCRE -> ECMAScript pattern translation shared by every runtime
// regex entry point.
//
// Upstream librime compiles patterns with boost::regex (PCRE). This fork uses
// std::regex (ECMAScript) to drop Boost, which misreads PCRE's \l and \u
// shorthand classes (\l becomes the literal letter 'l'), rejects constructs
// ECMAScript lacks, and throws where the caller does not catch. A schema that
// works upstream therefore either stops matching or takes the process down.
//
// calculus.cc translates the algebra rules; the same pattern language also
// reaches four runtime entry points — recognizer patterns, encoder
// exclude_patterns, translator/patterns and speller auto_select_pattern — so
// the translation lives here and every site compiles through it inside a
// try/catch. An untranslatable pattern must degrade to "not loaded" (and one
// log line), never to a crash.
//
// \d \D \w \W \s \S are deliberately left alone: ECMAScript defines them with
// the same meaning as PCRE. \p{...} is not translated — ECMAScript has no
// Unicode property support, and silently matching something else would be
// worse than failing, so it is left to raise the regex_error it always did.
// Lookbehind/lookahead cannot be expressed in ECMAScript at all; patterns
// using them still raise regex_error, which the callers turn into a log line.
//
#ifndef RIME_PCRE_TRANSLATOR_HPP_
#define RIME_PCRE_TRANSLATOR_HPP_

#include <string>

namespace rime {

inline std::string TranslatePcreClasses(const std::string& pattern) {
  std::string out;
  out.reserve(pattern.size() + 8);
  bool in_class = false;  // inside [...]
  for (size_t i = 0; i < pattern.size(); ++i) {
    char c = pattern[i];
    if (c == '\\' && i + 1 < pattern.size()) {
      char next = pattern[i + 1];
      if (next == '\\') {  // an escaped backslash: copy both, stay literal
        out += c;
        out += next;
        ++i;
        continue;
      }
      // Inside a character class a bare range has to stay bare, because
      // "[[a-z]]" would nest instead of unioning. Outside one, the class form
      // is required — and it composes with quantifiers: \l+ -> [a-z]+.
      const char* expanded = nullptr;
      switch (next) {
        case 'l': expanded = in_class ? "a-z"   : "[a-z]"; break;
        case 'u': expanded = in_class ? "A-Z"   : "[A-Z]"; break;
        default: break;
      }
      if (expanded) {
        out += expanded;
      } else {
        out += c;
        out += next;
      }
      ++i;
      continue;
    }
    if (c == '[' && !in_class)
      in_class = true;
    else if (c == ']' && in_class)
      in_class = false;
    out += c;
  }
  return out;
}

}  // namespace rime

#endif  // RIME_PCRE_TRANSLATOR_HPP_