//
// Minimal boost::dll::shared_library replacement for this fork.
//
// Provides the subset that plugins/plugins_module.cc uses — construction from a
// path, `suffix()`, and shared ownership of the loaded handle — exposed under
// the `boost::dll::` namespace so the call sites compile unchanged (only the
// #include changes), matching the other <rime/*.hpp> shims.
//
// Ownership matches Boost.DLL: shared_library is copyable and the library is
// unloaded only when the last copy dies, which is what keeps a plugin's static
// registrations alive while its name sits in PluginManager's map.
//
#ifndef RIME_SHARED_LIBRARY_HPP_
#define RIME_SHARED_LIBRARY_HPP_

#include <filesystem>
#include <memory>
#include <stdexcept>
#include <string>
#include <system_error>

#ifdef _WIN32
#include <windows.h>
#else
#include <dlfcn.h>
#endif

namespace boost {
namespace dll {

class shared_library {
 public:
  shared_library() = default;

  explicit shared_library(const std::filesystem::path& lib_path)
      : handle_(open(lib_path)) {}

  // Boost.DLL: ".dll" on Windows, ".dylib" on macOS/iOS, ".so" elsewhere.
  static std::filesystem::path suffix() {
#ifdef _WIN32
    return ".dll";
#elif defined(__APPLE__)
    return ".dylib";
#else
    return ".so";
#endif
  }

 private:
  // Boost.DLL normalizes its default load mode to RTLD_LAZY | RTLD_LOCAL on
  // POSIX and LoadLibraryExW(path, NULL, 0) on Windows; dlopen(2) rejects a
  // flag of 0, so the normalized values are spelled out.
  static std::shared_ptr<void> open(const std::filesystem::path& lib_path) {
#ifdef _WIN32
    HMODULE module = LoadLibraryExW(lib_path.c_str(), nullptr, 0);
    if (module == nullptr) {
      throw std::system_error(
          static_cast<int>(GetLastError()), std::system_category(),
          "cannot open shared library: " + lib_path.string());
    }
    return std::shared_ptr<void>(
        module, [](void* h) { FreeLibrary(static_cast<HMODULE>(h)); });
#else
    // A bare name without a directory means "search the library path", which is
    // not what a relative plugin path means; Boost.DLL forces it back to the
    // working directory the same way.
    std::filesystem::path path = lib_path;
    if (path.parent_path().empty()) {
      path = "." / path;
    }
    void* handle = dlopen(path.c_str(), RTLD_LAZY | RTLD_LOCAL);
    if (handle == nullptr) {
      const char* error = dlerror();
      throw std::runtime_error(
          "cannot open shared library: " + path.string() +
          (error != nullptr ? ": " + std::string(error) : ""));
    }
    return std::shared_ptr<void>(handle, [](void* h) { dlclose(h); });
#endif
  }

  std::shared_ptr<void> handle_;
};

}  // namespace dll
}  // namespace boost

#endif  // RIME_SHARED_LIBRARY_HPP_
