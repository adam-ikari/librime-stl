---
slug: background
title: Project background
role: project background
updated: "2026-10-13T05:37:10"
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
