# Rime with Android

Build the engine library (pure C API `librime.so`) for Android with the NDK.

The JNI bridge is **not** part of this repository: this library exposes the
upstream C API (`rime_api.h`, entry point `rime_get_api`), and the consumer
(Terminal/Trime/fcitx5-android style frontend) is responsible for its own JNI
layer. The dictionary toolchain (`dict/tools/`) is also not involved — this
build only compiles the engine; the runtime dictionary data (`dict/`) is
packaged by the consumer.

## Build

``` sh
# download the NDK once, e.g. r28
# https://developer.android.com/ndk/downloads

git clone --recursive https://github.com/adam-ikari/librime-stl.git
cd librime-stl

NDK=/path/to/android-ndk-r28 ./build-android.sh arm64-v8a   # or: x86_64, armeabi-v7a
```

Output: `build/android-<abi>/rime/lib/librime.so`

The script cross-compiles the five static deps
(glog/leveldb/marisa-trie/opencc/yaml-cpp) into a private prefix under
`build/android-<abi>/prefix`, then configures the engine with
`-DRIME_DEPS_PREFIX` pointed at it, so the build fails outright if any dependency
resolves outside that prefix or if the opencc it finds is not the version
vendored under `deps/opencc`. How each dep is configured lives in one place, the
`<dep>_flags` table in `deps.mk`, which this script reads via `make -f deps.mk
print-flags DEP=x`; opencc's entry has data and tools off, so dictionary
generation never runs on the NDK build — see `dict/README.md`.

The graph compiles one library and nothing else. `googletest` is in `deps.mk` but
not cross-built (`BUILD_TEST=OFF`, so no `rime_test` needs it); `tools/`' six
command-line programs are not even generated for Android; and gflags is not
searched, because this graph builds against the vendored glog that `deps.mk`
configures `WITH_GFLAGS=OFF`, so there is nothing for gflags to satisfy. Host
graphs keep both the `tools/` targets and the gflags search — a distro
`libglog.a` built with gflags does need linking it.

Environment: `CLEAN=1` discards the tree for that ABI before configuring;
`VERIFY_ONLY=1` skips every build step and re-checks a library with the same
assertions a build ends with — the `librime.so` already there for that ABI, or
`VERIFY_ARTIFACT=path` for any other (a host build's library fails them, which
is the point). `NDK` is needed to find the toolchain; the checks themselves fall
back to `readelf`/`nm` on `PATH`. Reusing a tree configured by a different
toolchain, ABI or platform is refused rather than silently re-cached.

## What the artifact is checked against

The script ends by reading its own output, and fails if any of this is untrue:

- the `NEEDED` entries of `librime.so` are bionic system libraries only
  (`liblog.so libm.so libdl.so libc.so`) — every dependency, opencc included, is
  cross-built static and absorbed into the library;
- `rime_get_api` is exported as an unmangled C symbol.

The graph is the engine alone: `ENABLE_EXTERNAL_PLUGINS` stays off, so this
artifact neither loads nor contains plugins, and a Lua-enabled Android build is a
separate cross build of the plugin, not a flag here.

Which is what the JNI layer needs to know: the consumer links `librime_jni.so`
against this `librime.so` and **does not link `libopencc.a`** — opencc's code is
already inside `librime.so`, and nothing else provides it. The runtime side is
data, not libraries: the `dict/opencc/` configs and tables have to be packaged
under `<shared_data_dir>/opencc/`, or the `simplifier` filters (emoji suggestions,
traditional/simplified conversion) log `opencc config not found` once and pass
candidates through unconverted.

Still unverified: the binary has never run on Android hardware. These checks read
the ELF; none of them is a device test.
