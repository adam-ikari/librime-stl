<meta charset="UTF-8">

RIME: Rime Input Method Engine
===
![Build status](https://github.com/rime/librime/actions/workflows/commit-ci.yml/badge.svg)
[![GitHub release](https://img.shields.io/github/release/rime/librime.svg)](https://github.com/rime/librime/releases)
[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

Rime with your keystrokes.

> **Fork.** This is `librime-stl`, a dependency-trimmed fork of
> [rime/librime](https://github.com/rime/librime): the engine configures and builds
> without Boost, without a host Python and without a host-built `opencc_dict`.
> Everything below is upstream's README, kept verbatim; a `Fork.` quote block and
> the two sections after “Build and install on Linux” are the only additions, and
> [Differences from upstream](#differences-from-upstream) is the full list.

Project home
---
[rime.im](https://rime.im)

License
---
[The 3-Clause BSD License](https://opensource.org/licenses/BSD-3-Clause)

> **Fork.** Licensing here is not uniform. The engine is upstream's, and the upstream
> `LICENSE` is kept verbatim -- the patches are an upstream-compatible derivative,
> not a relicense. Data under `dict/` is a separate matter and follows its own
> sources: LGPL-3.0 for `essay.txt` and `luna_pinyin.dict.yaml`, Apache-2.0 for the
> OpenCC-derived tables, MIT for this project's own tables. Full texts are vendored
> under [`licenses/`](licenses/); see [dict/LICENSE](dict/LICENSE) for the
> distribution obligations when bundling the data.

Features
===
  - A modular, extensible input method engine in cross-platform C++ code,
    built on top of open-source technologies
  - Covering features found in a large variety of Chinese input methods,
    either shape-based or phonetic-based
  - Built with native support for Traditional Chinese, conversion to Simplified
    Chinese and other regional standards via OpenCC
  - Rime input schema, a DSL in YAML syntax for fast trying out innovative ideas
    of input method design
  - Spelling Algebra, a mechanism to create variant spelling, especially useful
    for Chinese dialects
  - Support for chord-typing with a generic Qwerty keyboard

Install
===
Follow the instructions to build librime on platforms other than Linux:
  - [macOS](https://github.com/rime/librime/tree/master/README-mac.md)
  - [Windows](https://github.com/rime/librime/tree/master/README-windows.md)

> **Fork.** Android has no upstream guide; see
> [README-android.md](README-android.md) for this fork's cross-build.

Build dependencies
---
  - compiler with C++17 support
  - cmake>=3.12
  - libglog>=0.7 (optional)
  - libleveldb
  - libmarisa
  - libopencc>=1.0.2
  - libyaml-cpp>=0.5
  - libgtest (optional)

Runtime dependencies
---
  - libglog (optional)
  - libleveldb
  - libmarisa
  - libopencc
  - libyaml-cpp

> **Fork.** No Boost is required. These two lists are the only place this fork
> deletes upstream lines: `libboost>=1.74` above and `libboost` in the runtime
> list. Patterns compile with `std::regex`, and schema-supplied patterns go through
> a shared PCRE→ECMAScript translation so schemas written for upstream keep
> working. OpenCC is vendored under `deps/opencc` with its generated tables
> committed under `dict/opencc/`, so neither a host Python nor a host-executed
> `opencc_dict` is needed to build the engine.

Build and install on Linux
---
```
make
sudo make install
```

Differences from upstream
===
The engine stays a close derivative, so the list is short and each item is a
dependency question rather than a behaviour change.

  - **No Boost.** `std::regex` plus a minimal `<rime/*.hpp>` shim set replaces the
    boost facilities librime used (algorithm/string, signals2, interprocess, crc,
    uuid, regex). Upstream's Boost usage is translated at the `#include` line -- the
    shims live in the `boost::` namespace, so call sites are untouched. Constructs
    that cannot be shimmed are replaced at configure time instead (Boost.PP became
    `src/rime_extra_modules.h.in`).
  - **Regex compatibility layer.** Schema-supplied patterns go through a shared
    PCRE→ECMAScript translation ([src/rime/pcre_translator.hpp](src/rime/pcre_translator.hpp)),
    and a bad pattern can no longer take the engine down with it.
  - **OpenCC vendored** ([deps/opencc](deps/opencc)), with the `.ocd2` binaries it
    would otherwise generate at build time committed under `dict/opencc/`.
    Configure and build need no host Python and no host-built `opencc_dict` -- the
    latter used to break cross-compiling outright (`Exec format error` under NDK).
  - **The shared library builds for more platforms.** commit-ci builds it for
    Linux, macOS, Windows and Android and checks the produced library (Android
    verifies `librime.so` with `readelf -d`); consumers link against it through
    the pure C API ([include/rime_api.h](include/rime_api.h)).
  - **A bundled Simplified Chinese dictionary** ([dict/](dict)): `luna_pinyin.dict.yaml`
    + `essay.txt` + the opencc data, published as a versioned artifact
    ([dict/CHANGELOG.md](dict/CHANGELOG.md)). Upstream ships none. Its generators live
    in [dict/tools](dict/tools) and are driven by explicit `make`, never by the CMake
    build graph, so generating data and configuring the engine stay two separate
    jobs. Two gates: `make -C dict/tools check` regenerates and byte-compares the
    committed data, `make -C dict/tools smoke` deploys it and asserts candidate
    behaviour against the real engine.

Syncing upstream
===
```sh
git remote add upstream https://github.com/rime/librime
git fetch upstream
git merge upstream/master        # dict/ has no counterpart upstream; it never conflicts
```

`README.md` is upstream's text with the `Fork.` blocks and the two sections above
added, so a merge only conflicts where upstream rewrote a paragraph around one of
them. Expect conflicts otherwise only where this fork intentionally diverges --
the Boost shims. After merging, `make test` must be green, and
`make -C dict/tools check && make -C dict/tools smoke` must cover the bundled
dictionary.

Packaging status
---
[![Packaging status](https://repology.org/badge/vertical-allrepos/librime.svg?columns=4&minversion=1.10.0)](https://repology.org/project/librime/versions)

Frontends
===

Official:
  - [ibus-rime](https://github.com/rime/ibus-rime): IBus frontend for Linux
  - [Squirrel](https://github.com/rime/squirrel): frontend for macOS
  - [Weasel](https://github.com/rime/weasel): frontend for Windows

<!-- Sort in alphabetical order with :sort in vim -->
Community:
  - [ARIF](https://www.nongnu.org/arif/): frontend for Readline
  - [Hamster](https://github.com/imfuxiao/Hamster): frontend for iOS
  - [My RIME](https://github.com/LibreService/my_rime): frontend for web
  - [PIME](https://github.com/EasyIME/PIME): frontend for Windows
  - [Trime](https://github.com/osfans/trime): frontend for Android
  - [XIME](https://github.com/stackia/XIME): frontend for macOS
  - [YuyanIme](https://github.com/gurecn/YuyanIme): frontend for Android
  - [coc-rime](https://github.com/tonyfettes/coc-rime): frontend for Vim
  - [emacs-rime](https://github.com/DogLooksGood/emacs-rime): frontend for Emacs
  - [fcitx-rime](https://github.com/fcitx/fcitx-rime): Fcitx frontend for Linux
  - [fcitx5-android](https://github.com/fcitx5-android/fcitx5-android): frontend for Android
  - [fcitx5-macos](https://github.com/fcitx-contrib/fcitx5-macos): Fcitx5 frontend for macOS
  - [fcitx5-rime](https://github.com/fcitx/fcitx5-rime): Fcitx5 frontend for Linux
  - [fcitx5-ui.nvim](https://github.com/black-desk/fcitx5-ui.nvim): Fcitx5 frontend for Vim
  - [fcitx5.nvim](https://github.com/tonyfettes/fcitx5.nvim): Fcitx5 frontend for Vim
  - [pyrime](https://github.com/Freed-Wu/pyrime): frontend for Ptpython
  - [rabbit](https://github.com/amorphobia/rabbit): frontend for Windows
  - [rime.nvim](https://github.com/Freed-Wu/rime.nvim): frontend for Vim
  - [rl_custom_rime](https://github.com/Freed-Wu/rl_custom_rime): frontend for Readline
  - [tmux-rime](https://github.com/Freed-Wu/tmux-rime): frontend for Tmux
  - [zsh-rime](https://github.com/Freed-Wu/zsh-rime): frontend for Zsh

Plugins
===
  - [librime-charcode](https://github.com/rime/librime-charcode) (Deprecated) Module that
    deals with character encoding; depends on boost::locale and ICU libraries
  - [librime-legacy](https://github.com/rime/librime-legacy) (Deprecated) Legacy module with
    GPL-licensed code
  - [librime-lua](https://github.com/hchunhui/librime-lua) Lua scripting
  - [librime-octagram](https://github.com/lotem/librime-octagram) Language model
  - [librime-predict](https://github.com/rime/librime-predict) Predict next word
  - [librime-proto](https://github.com/lotem/librime-proto) IPC using CapnProto

Related works
===
  - [plum](https://github.com/rime/plum): Rime configuration (recipe) installer
  - [combo-pinyin](https://github.com/rime/home/wiki/ComboPinyin): an innovative
    chord-typing practice to input Pinyin
  - [rime-essay](https://github.com/rime/rime-essay): the preset vocabulary
  - [SCU](https://github.com/neolee/SCU): Squirrel Configuration Utilities

> **Fork.** `dict/luna_pinyin.dict.yaml` derives from
> [rime-luna-pinyin](https://github.com/rime/rime-luna-pinyin) (LGPL-3.0) and
> `dict/essay.txt` from [rime-essay](https://github.com/rime/rime-essay); both are
> pinned in [dict/tools/sources.lock](dict/tools/sources.lock).

Credits
===
We are grateful to the makers of the following open source libraries:

  - [Boost C++ Libraries](http://www.boost.org/) (Boost Software License)
  - [google-glog](https://github.com/google/glog) (The 3-Clause BSD License)
  - [Google Test](https://github.com/google/googletest) (The 3-Clause BSD License)
  - [LevelDB](https://github.com/google/leveldb) (The 3-Clause BSD License)
  - [marisa-trie](https://github.com/s-yata/marisa-trie) (BSD 2-Clause License, LGPL 2.1)
  - [OpenCC](https://github.com/BYVoid/OpenCC) (Apache License 2.0)
  - [yaml-cpp](https://github.com/jbeder/yaml-cpp) (MIT License)

Contributors
===
  - [佛振](https://github.com/lotem)
  - [鄒旭](https://github.com/zouxu09)
  - [Weng Xuetian](http://csslayer.info)
  - [Chongyu Zhu](http://lembacon.com)
  - [Zhiwei Liu](https://github.com/liuzhiwei)
  - [BYVoid](http://www.byvoid.com)
  - [雪齋](https://github.com/LEOYoon-Tsaw)
  - [瑾昀](https://github.com/kunki)
  - [osfans](https://github.com/osfans)
  - [jakwings](https://github.com/jakwings)
  - [Prcuvu](https://github.com/Prcuvu)
  - [hchunhui](https://github.com/hchunhui)
  - [Qijia Liu](https://github.com/eagleoflqj)
  - [WhiredPlanck](https://github.com/WhiredPlanck)
