---
id: upstream-alignment
title: "与上游 librime 的对齐纪律（含注释与 fork 标记策略）"
category: decision
status: active
tags: [engine, upstream, style]
created: "2026-10-13T05:37:49"
updated: "2026-10-14T02:13:22"
---

<!-- compiled_truth -->
## 结论

本仓是 fork，不是重写。**除标注的差异外，与 rime/librime 逐字节一致**。
判据不是感觉，是一条命令：`git diff upstream/master HEAD` 就是本 fork 的全部所有权清单。

## 规则

- 差异注释统一 `# fork:` 前缀（旧写法 `# term-ime:` 已全量替换——消费方名字不属于
  引擎源码，差异的参照系是上游，不是某个产品）。
- **上游自己写的中文/繁体注释保持原样**。它们不是「本 fork 的中文注释」，翻译过来只会
  制造无谓的 upstream 冲突。曾按 `git diff --numstat upstream/master HEAD -- <file>`
  量过：仓内 988 行中文里绝大多数是上游的。
- 本 fork 自写的中文注释 → 译成等值英文（内容、位置不变）。
- 程序输出不算注释：`audit_readings.py` 的报告文字与 `argparse help=`、glog 文案
  保持中文；`dict/LICENSE` 的中文条款、`dict/tools/Makefile` 的包名与安装路径、
  `dict-release.yml` 的 tarball 路径同属「字符串本身是产物」，故意不动。
- 新增文件（`dict/`、`data/minimal/*patch*`、`BRAIN.md`/`brain/`）上游没有同名，
  不产生冲突面。

## 风格门

CI lint 用 **clang-format 23**（`action-install-clang-format.sh` 走 `sudo apt` +
`update-alternatives`）。本地版本不同（如 18）时不能直接以本地结论判 CI 红绿：
正确做法是在同一 formatter 下比对 HEAD 与工作区的违规行数——本次 51 vs 51 即
「未引入新偏移」。注意 lint 的 find 只收 `*.cc` 与 `*.h`，`.hpp`（含
`cmake/plugin-shim/**`、`src/rime/*.hpp`）不在门内。

## 「不含 Boost」在本机不可验证

开发机装了 Boost 头文件，CI 才是没有 Boost 的那个环境，所以这条主张只能靠构建产物
自证，两条都不需要新环境：

- `find build -name '*.o.d' | xargs grep -l include/boost` 必须零命中——配置期写出的
  依赖清单就是「这次构建实际读过哪些头」。
- 盯单个文件：`c++ <flags.make 里的 flags> -H -fsyntax-only <file>` 后 `grep -i boost`
  为空。

`8119a356` 删 CI 的 Boost 依赖时漏了 `plugins/plugins_module.cc`（仍 include
`<boost/algorithm/string.hpp>` 与 `<boost/dll.hpp>`），而 Makefile 的 `release` 一定带
`-DENABLE_EXTERNAL_PLUGINS=ON` 编它：本地全绿、CI 三平台从 `f6ea8d94` 起全红，就是这个
盲区。

补 shim 沿用既有模式：`src/rime/<name>.hpp` 在 `namespace boost` 里提供缺的能力，
上游文件只改 `#include` 那一行并标 `# fork:`。`boost::dll::shared_library` 的替身是
`src/rime/shared_library.hpp`（dlopen / LoadLibraryExW），语义必须逐条对齐 Boost.DLL，
差一条就是运行时行为差：dlopen 拒绝 flags=0（Boost 先把默认模式归一化成
`RTLD_LAZY|RTLD_LOCAL` 再传）、无父目录的裸文件名要补 `./`、句柄用 shared_ptr 共享
所有权——`map<string, shared_library>` 的拷贝赋值与 `operator[]` 默认构造都依赖最后
这条，插件的静态注册才会在库里活着期间不被卸载。

## 边界延伸：第三方插件用 Boost 当助手还是当语义

判据是这一条，不是「是不是我们的文件」：`boost::starts_with` 之类字符串助手，fork 已经
在 `namespace boost` 下提供，可以应答；`boost::regex`、signals2 的 connection 形状、
boost::locale/asio 承载的是语义，不假装能替，插件因此留在矩阵外（librime-lua 已摘，
librime-charcode 只在装了真 Boost 的 Docker 里编）。

插件源文件不属于本仓，改不动它写的 `#include <boost/algorithm/string.hpp>`，于是在
同一路径上给出答案：`cmake/plugin-shim/boost/algorithm/string.hpp` 只 include
`<rime/string_utils.hpp>`。三条硬约束：

- 只在 `check_include_file_cxx` 探不到真头文件时才进 include 路径——装了 Boost 的地方
  行为一字不变（用探针而不是 `find_package(Boost)`，因为本树配置期根本不引入 Boost）。
- 永不 install。fork 不宣称提供 Boost，消费方有真 Boost 就用真的。
- 放在 `cmake/` 而不是 `plugins/`：`plugins/CMakeLists.txt` 的发现循环把本目录下每个
  子目录都当插件，`plugins/shim/` 会被 add_subdirectory 掉。

本机如何证明（开发机有 Boost，走不到无 Boost 分支）：`check_*` 系列的缓存变量一旦
已定义就跳过探测，所以 `-DRIME_HAVE_BOOST_ALGORITHM_STRING=` 可强制进 shim 分支并编到
插件 obj；再用 `g++ -E -I…/cmake/plugin-shim` 与不带 `-I` 各跑一次，比对
`boost/algorithm/string.hpp` 分别解析到 shim 与 `/usr/include`。

## Windows 独有的一关：符号可见性

`librime.so` / `.dylib` 默认全部符号可见，Windows 的 `rime_test.exe` 只能经
`librime.dll` 的导出表取符号。因此「本 fork 自己新增的测试」在 Linux/macOS/Android
全绿仍可能在四组 Windows 作业上 LNK2019：`test/pcre_compat_test.cc` 用到
`RecognizerPatterns::LoadConfig` 与 `Patterns::Load`，上游没导出它们（上游没有这两个
测试），mingw 与 msvc/x64、msvc/x86、windows-clang 一起挂在同两处。

- 修法是上游自己的写法：只给成员函数标 `RIME_DLL`，不给 class 标。`Config`、
  `TableEncoder` 都按函数导出；class 级导出会让以 `std::map` / `std::vector` 为基类的
  `RecognizerPatterns`、`Patterns` 触发 MSVC C4251。
- 取舍：没有删掉那两条断言。「schema 里的 pattern 真走了翻译层、坏 pattern 只是不载入」
  正是翻译层存在的理由，退给部署冒烟等于放弃单元级定位。
- 推广规则：fork 新增任何直接调引擎内部的测试，先问「这个符号在 Windows DLL 上导出
  吗」。这条同样本机不可验证，只有 CI 能证。

## 跟踪例外：`data/*` 默认被 gitignore

`.gitignore` 里 `data/*`（`include/*`、`plugins/*/` 同理），`data/minimal/` 的那些
schema/default/dict 文件是逐个 `git add -f` 提进来的。在本目录新增文件时普通 `git add`
静默无效：工作区有文件 → 本地构建与 smoke 全绿；干净 checkout 没有 →
`tools/CMakeLists.txt` 的 `file(COPY)` 在 configure 期直接失败，schema 的
`__patch:` 引用也落空（`emoji_suggestion.yaml` 踩过）。新增这类文件后用
`git ls-files data/` 确认真的进了索引。`test/opencc/` 不受该规则影响（`data/*` 是根锚定
的），但也照例用 `git status --short` 核对进了索引。


## Timeline

- time: 2026-10-13T05:37:49
  kind: decision
  summary: "Created this page: 与上游 librime 的对齐纪律（含注释与 fork 标记策略）"
  source: session 2026-10-12/13
  affects: [upstream-alignment]

- time: 2026-10-13T05:38:08
  kind: decision
  summary: "初版：确立对齐纪律与注释策略"
  source: sessions 2026-10-12/13
  affects: [upstream-alignment]

- time: 2026-10-13T09:25:10
  kind: decision
  summary: "补两条：Boost-free 只能靠 .o.d/-H 自证（含 dll shim 的语义对齐清单），以及 data/* 被 gitignore、新增文件须 -f"
  source: "session 2026-10-13 (CI 排红)"
  affects: [upstream-alignment]

- time: 2026-10-14T02:13:22
  kind: decision
  summary: Rewrote compiled_truth to the new best understanding
  source: brain update-truth
  affects: [upstream-alignment]
