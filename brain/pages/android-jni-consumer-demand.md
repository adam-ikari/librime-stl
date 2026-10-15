---
id: android-jni-consumer-demand
title: "真实 Android 消费者怎么链 librime（Trime / fcitx5-android 取证）"
category: reference
status: active
tags: [android, jni, plugins, opencc]
created: "2026-10-14T17:01:46"
updated: "2026-10-14T17:27:35"
---

<!-- compiled_truth -->
## 取证范围与可信度

2026-10-14 对两家真实 Android 消费者做外部取证。以下两处**我亲自读过原始文件**（`gh api contents`）：
Trime `app/src/main/jni/cmake/Rime.cmake`，fcitx5-android `prebuilder/src/Rules/LibRime.hs`。
其余（`librime_jni/CMakeLists.txt` 的链接行、`plugin/rime/.../CMakeLists.txt` 的 `WHOLE_ARCHIVE`、
Trime PR #2156 的拒绝理由、SELinux 策略细节）来自子代理检索，标为「转述」，用于背景不用于断言。

## 两家都是「编译期合并模块 + 静态链进自己的 JNI 库」

Trime `cmake/Rime.cmake:6`：`set(RIME_PLUGINS librime-lua librime-octagram librime-predict)`；
`:23 option(BUILD_TEST OFF)`、`:24 option(BUILD_STATIC ON)`，`jni/CMakeLists.txt` 里
`option(BUILD_SHARED_LIBS "" OFF)`（转述：`librime_jni` 链 `rime-static` 与 `${Opencc_LIBRARY}`）。
fcitx5-android `LibRime.hs:26-35` 把 lua/octagram/predict 三个仓 symlink 进
`librime/plugins/{lua,octagram,predict}` 后由 `BUILD_MERGED_PLUGINS` 合并，`:49-53` 的旗标是
`BUILD_SHARED_LIBS=OFF BUILD_STATIC=ON BUILD_TEST=OFF BUILD_TOOLS=OFF ALSO_LOG_TO_STDERR=ON`，
产物是 `librime/<abi>/lib/librime.a`。

结论一：**octagram 与 predict 属于「通用 Android 引擎该带」的模块**，两家都带。本仓交叉图把
它们编进 `librime.so`（实测注册 10 个 `rime_require_module`，代价是代码段 113537/2851809 = 4.0%）
与真实需求一致；此前我用的「4% 不划算」只是副证，正证是消费者事实。

结论二：**lua 是需求第一名**。GitHub 代码搜索（yaml）：`lua_filter` 3104 个文件、
`lua_translator` 2996、`lua_processor` 2344、`lua_segmentor` 68；插件真实注册的只有
`lua_translator/lua_filter/lua_processor/lua_segmentor` 四类（`src/modules.cc`，我先前记的
`lua_sanitizer`/`lua_reverser` 不存在）。部署量最大的两套中文配置 rime-ice 与 rime-frost 每份
schema 挂 10–15 个 lua 钩子（选字、日期/农历/UUID/Unicode、计算器、错音错字提示、置顶、长词
优先、辅助码反查……），其中多数在引擎里没有 C++ 等价物。两家真机前端都把 librime-lua 编进去：
Trime `.gitmodules` 有 `librime-lua` 子模块，fcitx5-android 链 `liblua_static.a`。反向事实：
上游 rime 组织内 `lua_translator` **0 命中**，plum 的 preset/extra 包与 rime-wubi 都不需要 lua，
librime 自己的 README 把 lua 列为可选插件——所以 lua 是**社区配置生态**的要求，不是引擎核心的要求。
「不带 lua」是可辩护的选择（做上游兼容引擎），但它必须写成选择加代价，代价是：第三方 schema 里
那些组件名解析不了，功能**静默消失**而不是报错停机。

排除理由已在 [[upstream-alignment]] 翻案：不是 Boost 语义不可替（实测 Boost 面 3 文件 / ~70 行，
regex 与 optional 本 fork 已有能力覆盖），真缺口是 `src/rime/signal.hpp` 只有 `connect(slot)`
而插件要 `connect(group, slot)`，以及「无 Boost 树的 Lua 5.4 Android 交叉」没有先例。

## 没人用 librime 自己的 dlopen 插件通道

两家代码搜索 `ENABLE_EXTERNAL_PLUGINS` / `RIME_PLUGINS_DIR` 均 0 命中；转述：Trime PR #2156
（从 `files/rime-plugins` 热加载原生插件）被维护者以「hot loading native libraries can be an
attack surface」拒收。平台侧（转述自 Android 官方 behavior-changes-10 与 agnostic-apollo 的
policy 分析）：API 29 起可写 app 目录执行属 W^X 违规被禁的是 `execve`/文本重定位，`dlopen` 从
`/data/data/<pkg>/` 目前仍能成，但 `extractNativeLibs=false` 时 APK 内没有真实文件可扫，可辩护的
做法是插件随 APK 打包、从 `nativeLibraryDir` dlopen（fcitx5-android 对 fcitx5 addon 正是如此）。

所以本仓交叉图保持 `ENABLE_EXTERNAL_PLUGINS=OFF` 是**有依据的决定**，不再是「上游默认，没人说过」。
见 [[hermetic-build-graphs]]。

## 交付形状与契约主张需要重新对表

两家真实消费者都把 librime 当**静态库**链进自己的 JNI/addon `.so`；本仓交叉图产出的是 shared
`librime.so`（`NEEDED ⊆ bionic`，opencc 已被吸收）。形状不同是选择不是错误，但
`README-android.md` 写的消费者契约（「consumer 链 `librime.so` 且不链 `libopencc.a`」）在野外
**没有对应的真实消费者**——Trime 恰恰自己链了 `${Opencc_LIBRARY}`。要么承认这是为本仓自有 JNI
层定的私有契约，要么补一个静态库变体（`BUILD_SHARED_LIBS=OFF` 的另一张 configure）。


## Timeline

- time: 2026-10-14T17:01:46
  kind: decision
  summary: "Created this page: 真实 Android 消费者怎么链 librime（Trime / fcitx5-android 取证）"
  source: created via brain create-page
  affects: [android-jni-consumer-demand]

- time: 2026-10-14T17:02:58
  kind: decision
  summary: Rewrote compiled_truth to the new best understanding
  source: "外部取证 Trime develop / fcitx5-android prebuilder（2026-10-14），关键两处亲自读原文件"
  affects: [android-jni-consumer-demand]

- time: 2026-10-14T17:27:35
  kind: decision
  summary: Rewrote compiled_truth to the new best understanding
  source: "GitHub 代码搜索计数 + rime-ice/rime-frost schema 逐行 + 前端构建文件"
  affects: [android-jni-consumer-demand]
