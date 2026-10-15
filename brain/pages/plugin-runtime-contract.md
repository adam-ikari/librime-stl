---
id: plugin-runtime-contract
title: "插件面的运行时契约：e2e_lua 门与 Lua regex 的失败形态"
category: decision
status: active
tags: [engine, plugin, test]
created: "2026-10-15T02:41:58"
updated: "2026-10-15T03:10:41"
---

<!-- compiled_truth -->
## 结论

CI 证明插件能编能链，证明不了它能跑。本 fork 换掉的三样东西——dlopen 加载器、
`boost::regex`、`boost::signals2`——全都在「被加载并驱动」那一刻才见分号。门是
`test/e2e_lua.py`：standalone 图（`-DENABLE_EXTERNAL_PLUGINS=ON
-DBUILD_MERGED_PLUGINS=OFF`）里把真的 `librime-lua.so`/`.dylib` 装进真的引擎，用
`rime_console` 驱动，比对落盘产物。它已经在 CI 里：`.github/workflows/macos-build.yml`
`make test` 后一步，两个 macOS 矩阵项均绿（2026-10-15）。

## 图的边界（别按「CI 都跑了插件」想当然）

- **macOS** 是唯一被验证的 standalone 图：`make test` → `release` 目标
  （Makefile:86-93）就带那两个 flag，且 `action-install-plugins-macos.sh` 真的装插件。
- **Windows 两个作业都是 merged**：MSVC 走 `.\build.bat test`、MinGW 直接
  `cmake -B build`，都不传 `BUILD_MERGED_PLUGINS`/`ENABLE_EXTERNAL_PLUGINS`，因此吃
  CMake 默认值 `ON`/`OFF`——插件编进 librime，从不 dlopen。在这些作业上门只会退出 2
  （`MISSING`），要覆盖得先改产物形状，不是加一步。
- **Linux 作业不装插件**：`plugins/` 为空，`ENABLE_EXTERNAL_PLUGINS=ON` 只编出加载器
  本身。补覆盖需要 lua5.4-dev + `install-plugins.sh` 三步入场，收益与 macOS 重叠。

## 门断言什么

判据一律是可观测结果，不是日志文本。glog 的 `loading plugin 'lua'` 写到
`/tmp/rime.console.*`，不在 console 的 stdout/stderr 里——拿它做断言会在插件正常工作
时假失败，第一跑就是这么错的。

- **加载**：候选 `E2E-LUA-OK` 出现 ⇒ 插件被 dlopen 且 `rime.lua` 被执行，两者缺一都
  不会有这个候选。
- **regex**：`rime_api.regex_match/search/replace` 的输出逐字节比对。覆盖
  `\l`/`\u`（经 `TranslatePcreClasses`）、`$1` 格式串、以及 `regex_search` 的返回形状
  =「整个匹配 + 每个捕获组」：`(\l+)\d+` 对 `rime2026x` 得 `rime2026|rime`，只有两段。
- **signal**：四个 slot 按 group 2,0,0,1 连接，落盘顺序必须是 `g0a g0b g1a g2a`——
  group 升序、同 group 内按连接序。`test/signal_test.cc` 钉的是 C++ 侧，这一条钉真正
  调用它的那层绑定。
- **无效 pattern**：不变量是「绝不静默匹配」。abort 与可捕获两种结局都算过，只有
  `pcall=true` 算失败。这样门不把当前形态焊死，收紧它时照样绿。

## 已测得的偏离（不是推断）

`rime.lua` 里 ECMAScript 表达不了的 pattern（lookbehind 之类）让宿主进程 abort
（Linux 与 macOS CI 都是 exit -6，即 SIGABRT）。链条：插件的三个绑定直接构造 regex
（`plugins/lua/src/types.cc:2403-2427`，无 try/catch），而 Lua 是按 C 编的，C++ 异常
穿不过 Lua VM 的 C 帧，所以 Lua 的 `pcall` 拦不住。上游对 boost 自己也拒绝的 pattern
行为相同；本 fork 新增的失败类恰是「perl 语法可用、ECMAScript 不可」。schema 侧没有
这个问题——配置编译在 deployment task 的 catch 里，代价是一个方案不是整个进程。
真要支持 perl 语法，出路是在插件图里用 PCRE2（原则允许的轻量库），不是回到 Boost；
在此之前不主动加依赖。

## 三条部署事实（都会静默改变结论，故记下）

- `rime.lua` 放在 console 位置参数指向的那个目录。那个参数就是
  `deployer.user_data_dir`（`src/rime/setup.cc:50-52`），插件读它
  （`plugins/lua/src/modules.cc:43`）；`<deployment>/user/` 不是，`shared.yaml` 里的
  `user_data_dir` 也不参与。放错了引擎照跑，只是 lua 从不执行。
- `<schema>.custom.yaml` 对 `luna_pinyin.schema.yaml` 无效：它根节点已有 `__patch`
  （`data/minimal/luna_pinyin.schema.yaml:21`），上游
  `src/rime/config/auto_patch_config_plugin.cc:23-26` 见到根 `__patch` 就主动跳过
  auto-patch。这是上游规则，不是 fork 缺陷。门因此改自己那份 schema 副本的
  `engine/translators` 与 `engine/filters`。
- lua_filter 是协程：消费者停在第一页时循环尾部不执行。计数写在 yield 处，不写在循环
  之后。


## Timeline

- time: 2026-10-15T02:41:58
  kind: decision
  summary: "Created this page: 插件面的运行时契约：e2e_lua 门与 Lua regex 的失败形态"
  source: "test/e2e_lua.py 首轮实跑（2026-10-15）"
  affects: [plugin-runtime-contract]

- time: 2026-10-15T02:42:20
  kind: decision
  summary: Rewrote compiled_truth to the new best understanding
  source: "test/e2e_lua.py 首轮实跑（2026-10-15）"
  affects: [plugin-runtime-contract]

- time: 2026-10-15T03:10:41
  kind: decision
  summary: Rewrote compiled_truth to the new best understanding
  source: "macOS CI 两个矩阵项首次真加载 librime-lua.dylib（run 38674152030，2026-10-15）"
  affects: [plugin-runtime-contract]
