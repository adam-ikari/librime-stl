//
// Minimal boost::signals2 replacement for this fork.
//
// Provides signal<Signature> and connection with the subset of the signals2 API
// that librime uses and that its plugin ecosystem asks for:
//   - connect(slot) -> connection
//   - connect(group, slot) -> connection  (grouped connect, emitted in group
//     order -- see the comment on the overload)
//   - connection::disconnect()  (removes that slot)
//   - connection default-constructible / copyable (held as class members)
//   - operator()(args...) to emit to all connected slots
// Not thread-safe (librime drives everything on one thread).
//
#ifndef RIME_SIGNAL_HPP_
#define RIME_SIGNAL_HPP_

#include <functional>
#include <memory>
#include <utility>
#include <vector>

namespace rime {

// Shared slot control block: a slot is "alive" until disconnect() flips this.
// Defined outside connection so signal<> can name it without a nested type
// (which complicates ADL with std headers included in the same TU).
struct slot_control {
  bool alive = true;
};

// A connection is a weak handle to one slot's control block. disconnect()
// marks the slot dead (the owning signal skips dead slots on emit). Default-
// constructible and copyable so it can be stored as a member and reassigned.
class connection {
 public:
  connection() = default;
  explicit connection(std::shared_ptr<slot_control> ctrl) : ctrl_(std::move(ctrl)) {}

  void disconnect() {
    if (auto c = ctrl_.lock()) c->alive = false;
  }
  bool connected() const {
    auto c = ctrl_.lock();
    return c && c->alive;
  }

 private:
  std::weak_ptr<slot_control> ctrl_;
};

template <typename Signature>
class signal;

template <typename... Args>
class signal<void(Args...)> {
 public:
  using slot_type = std::function<void(Args...)>;

  connection connect(slot_type slot) { return connect(0, std::move(slot)); }

  // boost::signals2 emits slots by ascending group, and slots connected in one
  // group in the order they were connected; connect(slot) joins group 0. The
  // engine never passes a group, but librime-lua binds
  // notifier:connect(fn, group), whose scripts do rely on that order.
  connection connect(int group, slot_type slot) {
    auto ctrl = std::make_shared<slot_control>();
    auto at = slots_.begin();
    while (at != slots_.end() && at->group <= group) {
      ++at;
    }
    slots_.insert(at, {ctrl, group, std::move(slot)});
    return connection(ctrl);
  }

  void operator()(Args... args) const {
    // Slots may disconnect() during emission, which only flips `alive`; the
    // vector itself is not mutated mid-iteration.
    for (auto& e : slots_) {
      if (e.ctrl->alive) e.fn(args...);
    }
  }

  void disconnect_all_slots() { slots_.clear(); }

 private:
  struct Entry {
    std::shared_ptr<slot_control> ctrl;
    int group;
    slot_type fn;
  };
  mutable std::vector<Entry> slots_;
};

}  // namespace rime

#endif  // RIME_SIGNAL_HPP_
