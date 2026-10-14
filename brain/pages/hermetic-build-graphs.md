---
id: hermetic-build-graphs
title: "三张编译图的边界与 hermetic 判据（RIME_DEPS_PREFIX）"
category: decision
status: active
tags: [build, opencc, android, ci]
created: "2026-10-14T07:08:55"
updated: "2026-10-14T07:09:19"
---

<!-- compiled_truth -->
## 三张编译图（不可混淆）

| 图 | 产物 | 构建树 | 依赖来源 | 系统库 |
|---|---|---|---|---|
| A host 引擎 | `librime.so`/`.a`、`rime_test` | `build/` | 发行版包（Linux/Docker/MinGW）或 `make deps`（装进仓库根 `include/ lib/ share/`） | 允许 |
| B Android 交叉 | JNI 用的 `librime.so` | `build/android-<abi>/`（私有 `$prefix`） | `deps/<dep>` 交叉静态构建 | 拒绝 |
| C 词库工具链 | `dict/opencc/*.ocd2`、`essay.txt` | `dict/tools/.build/` | `deps/opencc` 的 host 构建，`OPENCC_BUILD_DATA=ON` | host 是本意 |

C **从不 install**，因此不可能出现在 A/B 的搜索路径里；它交给引擎的只有提交物
（`dict/opencc/`、`test/opencc/`）。

## hermetic 的判据是路径，不是搜索顺序

`CMakeLists.txt` 把 `${PROJECT_SOURCE_DIR}` 放进 `CMAKE_PREFIX_PATH`，任何「靠顺序
优先命中 vendored」的做法都会在它面前失效。所以声明 `-DRIME_DEPS_PREFIX=<dir>`
后，门的内容是「每个解析到的依赖路径都必须以该 prefix 为前缀」，一次列出全部越界
项；并额外要求 opencc 版本等于 pin。prefix 为空时只报告不失败。

## 版本只能由打包元数据判定

opencc 安装后的头文件里没有版本宏，且 1.1.3 与 1.1.9 的 soname 同为
`libopencc.so.1.1`——soname 的分辨力为零。判定顺序：`lib/pkgconfig/opencc.pc` 的
`Version:`，其次 `lib/cmake/opencc/OpenCCConfigVersion.cmake`，都没有就如实报
`unknown`（`unknown` 在 hermetic 模式下即失败）。pin 从
`deps/opencc/CMakeLists.txt` 读取，绝不复制成 CMake 里的字面量。

真实事故：本机 A 图曾链到系统 opencc 1.1.3，而 `dict/opencc/*.ocd2` 由 pin 1.1.9
的 `opencc_dict` 生成，configure 与 CI 全程无话。

## host 图不把版本不符升为硬错误

Linux/Docker/MinGW 按设计就用系统 opencc；把它们改成 FATAL 等于推翻既有 CI 结论。
所以 A 打 `WARNING`（含解析路径 + resolved/pin），B 与 CI 的 `hermetic-deps` 打
`FATAL_ERROR`，并由 `hermetic-deps` 提供全 CI 唯一「用 pin 依赖构建并跑 `rime_test`」
的覆盖——它才是 `.ocd2` ↔ 运行时版本一致性的证据。macOS/Windows 的依赖缓存键必须
含 `deps/opencc/**` 与 `deps.mk`：opencc 是 vendored 文件，`submodule-status` 永不改变。

## 静态依赖的两个硬要求

- `CMAKE_POSITION_INDEPENDENT_CODE=ON`：Linux 上非 PIC 静态归档链不进共享库
  （`relocation R_X86_64_PC32 ... can not be used when making a shared object`）。
- glog 必须 `-DWITH_UNWIND=none`：默认 `libunwind` 会让 `libglog.a` 带着
  `_Ux86_64_getcontext`/`_ULx86_64_step` 的未定义引用，而 librime 按路径链接归档，
  没有任何地方补 `-lunwind`，于是 `rime_test` 在装有 libunwind 头文件的 host 上直接
  链接失败。

## 产物主张必须由脚本执行

`README-android.md` 里「`NEEDED` 只有 bionic」「导出 `rime_get_api`」原先只是散文。
现在 `build-android.sh` 构建结束即断言（`NEEDED` ⊆ `liblog.so libm.so libdl.so
libc.so`，且 `nm -D --defined-only` 有 ` T rime_get_api`），`VERIFY_ONLY=1`
（可配 `VERIFY_ARTIFACT=path`）重放同一组断言；host 的 `librime.so` 用它必须失败。
交叉树用戳文件（`toolchain|abi|platform`）防陈旧缓存，无戳的手工配置树拒绝复用。

## 对 JNI 交付物的结论

`librime.so` 已吸收 opencc 的静态码，因此 consumer 的 `librime_jni.so`
**不需要也不应该链 `libopencc.a`**。简繁/emoji 是运行时数据依赖：`dict/opencc/`
必须打进 `<shared_data_dir>/opencc/`，否则 `simplifier` 记一次
`opencc config not found` 后原样放行候选。引擎没有编译期的 opencc 数据目录
define（`src/rime/build_config.h.in` 里根本没有 opencc 项），唯一的构建期消费者是
`rime_test` 的 `test/opencc/` fixture。


## Timeline

- time: 2026-10-14T07:08:55
  kind: decision
  summary: "Created this page: 三张编译图的边界与 hermetic 判据（RIME_DEPS_PREFIX）"
  source: created via brain create-page
  affects: [hermetic-build-graphs]

- time: 2026-10-14T07:09:19
  kind: decision
  summary: Rewrote compiled_truth to the new best understanding
  source: "本轮 hermetic 构建改造（cmake/RimeDepProvenance.cmake + build-android.sh + CI）"
  affects: [hermetic-build-graphs]
