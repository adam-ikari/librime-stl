//
// fork: <rime/signal.hpp> stands in for boost::signals2. The engine only ever
// calls connect(slot), so the rest of that surface was untested until it was
// measured against librime-lua, which passes a slot group and keeps the
// returned connection. These cases pin the group ordering and the connection
// lifetime, rather than leaving them to "no current caller asks for them".
//
#include <gtest/gtest.h>
#include <rime/signal.hpp>

#include <string>
#include <vector>

using namespace rime;  // NOLINT(build/namespaces)

TEST(SignalTest, UngroupedConnectKeepsInsertionOrder) {
  rime::signal<void()> notifier;
  std::vector<std::string> log;
  notifier.connect([&] { log.push_back("a"); });
  notifier.connect([&] { log.push_back("b"); });
  notifier.connect([&] { log.push_back("c"); });
  notifier();
  EXPECT_EQ(log, (std::vector<std::string>{"a", "b", "c"}));
}

TEST(SignalTest, GroupOrderBeatsConnectionOrder) {
  rime::signal<void()> notifier;
  std::vector<std::string> log;
  auto c1 = notifier.connect([&] { log.push_back("plain"); });
  notifier.connect(-1, [&] { log.push_back("early"); });
  notifier.connect(0, [&] { log.push_back("zero"); });
  notifier.connect(7, [&] { log.push_back("last"); });
  notifier();
  // group -1 first, then group 0 in connection order, then group 7.
  EXPECT_EQ(log, (std::vector<std::string>{"early", "plain", "zero", "last"}));
  EXPECT_TRUE(c1.connected());
}

TEST(SignalTest, DisconnectSkipsOnlyThatSlot) {
  rime::signal<void()> notifier;
  std::vector<std::string> log;
  auto dropped = notifier.connect([&] { log.push_back("dropped"); });
  notifier.connect([&] { log.push_back("kept"); });
  // A connection is a handle: disconnecting through a copy removes the slot the
  // original connected, and the signal keeps the remaining order.
  auto copy = dropped;
  copy.disconnect();
  EXPECT_FALSE(dropped.connected());
  notifier();
  EXPECT_EQ(log, (std::vector<std::string>{"kept"}));
}

TEST(SignalTest, EmissionPassesArguments) {
  rime::signal<void(int, const std::string&)> notifier;
  std::vector<std::string> log;
  notifier.connect([&](int n, const std::string& s) {
    log.push_back(s + std::to_string(n));
  });
  notifier(1, "x");
  notifier(2, "y");
  EXPECT_EQ(log, (std::vector<std::string>{"x1", "y2"}));
}
