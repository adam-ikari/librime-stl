//
// Copyright RIME Developers
// Distributed under the BSD License
//
// 2012-01-01 GONG Chen <chen.sst@gmail.com>
//
#ifndef RIME_RECOGNIZER_H_
#define RIME_RECOGNIZER_H_

#include <regex>
#include <rime/common.h>
#include <rime/processor.h>

namespace rime {

class Config;
class Segmentation;

struct RecognizerMatch {
  string tag;
  size_t start = 0, end = 0;

  RecognizerMatch() = default;
  RecognizerMatch(const string& a_tag, size_t a_start, size_t an_end)
      : tag(a_tag), start(a_start), end(an_end) {}

  bool found() const { return start < end; }
};

class RecognizerPatterns : public map<string, std::regex> {
 public:
  // fork: exported because a Windows rime_test links librime.dll, where only
  // exported members are importable, and test/pcre_compat_test.cc drives this
  // wiring. Marking the member, not the class, keeps MSVC's C4251 away from a
  // std::map base.
  RIME_DLL void LoadConfig(Config* config, const string& name_space);
  RecognizerMatch GetMatch(const string& input,
                           const Segmentation& segmentation) const;
};

class Recognizer : public Processor {
 public:
  Recognizer(const Ticket& ticket);

  virtual ProcessResult ProcessKeyEvent(const KeyEvent& key_event);

 protected:
  RecognizerPatterns patterns_;
  bool use_space_ = false;
};

}  // namespace rime

#endif  // RIME_RECOGNIZER_H_
