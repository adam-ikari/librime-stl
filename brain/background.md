---
slug: background
title: Project background
role: project background
updated: "2026-10-15T00:15:46"
---

# Project background

## Why

两件事装在一个仓里：

1. **引擎**：rime/librime 的 fork。上游依赖 Boost，交叉编译（NDK）与分发都被拖重，
   本 fork 把 Boost 整个摘掉——`boost::regex` → `std::regex`，
   `boost::algorithm/signals2/interprocess/crc/uuid` → `src/rime/*.hpp` 里的自写 shim。
2. **词库**：`dict/` 是一份自足的简体中文拼音词库产品。原先词库与 librime 是两个
   submodule、两个 pin 点，「term-ime 用的哪个 librime」无法命名；并仓后数据与消费它
   的引擎补丁同一次提交、同一个版本坐标。

## Goals

- 引擎不含 Boost 依赖，Linux / macOS / Windows / Android 四平台都能出库，
  消费方只通过纯 C API（`include/rime_api.h`）链接。
- `dict/` 逐字节可复现（`make -C dict/tools check`）且引擎用得动
  （`make -C dict/tools smoke`），两道门分开：一致性门与可用性门。
- 源码与上游可对齐：除标注的差异外与 rime/librime 一致，`git diff upstream/master HEAD`
  就是本 fork 的全部所有权清单。

## Non-goals

- 不做输入法前端、不做 GUI、不做词库语义的「更好设计」——数据修订只走复现契约。
- 不把词库生成接进 CMake 构建图：生成需要 host Python 与一个现编译现执行的
  `opencc_dict`，NDK 上直接 `Exec format error`，而运行时只需要数据本身。
- 不重授权上游数据（派生作品许可证跟随上游，`dict/` 不是单一授权整体）。

## Target user

term-ime（装 `rime-data` 并链接本 fork 的 librime）；以及任何需要「无 Boost 的
librime」的嵌入方。

## 原则

1. **去 Boost 是手段，不是排除理由。** 上游用到 Boost 的地方一律换成 STL 或更轻的库
   （`std::regex`、`std::optional`、`src/rime/*.hpp` 里的自写 shim）。换不动的判据是
   「这个语义本 fork 没有」（boost::locale、asio），才留在插件矩阵外；某功能不能因为
   「它用到 Boost」就出局——那是待补的缺口，不是边界。
2. **交叉编译与 Android JNI 的构建体验是产品目标**，与引擎功能同优先级：三张编译图边界
   清楚、每个依赖的配置策略只有一个来源、产物能自证（判据见 [[hermetic-build-graphs]]）。
3. **与上游保持可合并**，API、词库、源码升级三条都算：差异逐字节可枚举
   （`git diff upstream/master HEAD`），而替代实现必须覆盖上游同名符号被真实用到的 API
   面——覆盖不足，插件和未来的一次 upgrade 都会撞墙。
