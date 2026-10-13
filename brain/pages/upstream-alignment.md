---
id: upstream-alignment
title: "与上游 librime 的对齐纪律（含注释与 fork 标记策略）"
category: decision
status: active
tags: [engine, upstream, style]
created: "2026-10-13T05:37:49"
updated: "2026-10-13T05:38:08"
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
「未引入新偏移」。


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
