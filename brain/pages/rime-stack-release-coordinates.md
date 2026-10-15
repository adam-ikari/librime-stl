---
id: rime-stack-release-coordinates
title: "两个发布坐标：v…-rime-stack 与 dict-…"
category: project
status: active
tags: [release, consumers]
created: "2026-10-13T05:37:49"
updated: "2026-10-15T02:08:02"
---

<!-- compiled_truth -->
## 两个坐标

- **`v…-rime-stack`**：引擎 + 词库配套发布。消费方（term-ime）用 submodule 锁它的
  commit，组合关系固定在对方那次 tag 里。
- **`dict-<VERSION>`**：纯词库修订，不动引擎。版本号读 `dict/VERSION`，workflow 在
  tag 与 VERSION 不符时直接失败。当前 `2026.10.13`（emoji 扩展词典）。

并仓的理由：原先「装了新词库但 librime 没跟上」这种组合无法被命名。

## 发布物

`make -C dict/tools package` 出 `term-ime-dict-<VERSION>.tar.gz`（+ `.sha256`），
布局是 `share/term-ime/rime-data/`：词库两件 + 整个 `opencc/`（含 emoji）+ LICENSE +
VERSION。`dict-release.yml` 会校验归档里这些路径存在（emoji 三件已列入）。

## 提交纪律

commit 只在用户要求时做，push 由用户自己或明确授权后代跑。改动分主题提交：
注释/风格改动不与功能改动混在同一个 commit（2026-10-13 的两组改动即按此拆开，
三个同时被两组碰过的文件按 hunk 分到各自提交）。


## Timeline

- time: 2026-10-13T05:37:49
  kind: decision
  summary: "Created this page: 两个发布坐标：v…-rime-stack 与 dict-…"
  source: dict/README.md
  affects: [rime-stack-release-coordinates]

- time: 2026-10-13T05:38:33
  kind: decision
  summary: "初版：两个 tag 坐标与各自义务"
  source: "dict/README.md, session 2026-10-13"
  affects: [rime-stack-release-coordinates]

- time: 2026-10-15T02:08:02
  kind: reversal
  summary: "rime-stack tag 的数字改跟上游 librime：v1.17.0-rime-stack（HEAD f3825316，两条流水线全绿）取代 v1.1.7/1.1.8/1.1.9 那种栈内自增。理由：那三个数字与引擎版本无关（当时 rime_version 是 1.16.1），108 个提交之后没人能从 tag 名读出底本；现在数字直接取 CMakeLists.txt 的 rime_version，且底本同步到上游 master tip 7bc3fb00（上游自己在那儿也声明 1.17.0）。后缀 -rime-stack 保留，因为裸 1.17.0 会与 upstream 同名 tag 在同一个 clone 里互相 clobber。注意 release-ci 的 tag 触发过滤器 '[0-9]+.*' 匹配不到 v 前缀（也匹配不到裸 1.17.0，'.' 落在 + 的位置上），而本仓在 GitHub 上没有任何 Release——stack tag 一直是纯 git 坐标，消费方用 submodule 锁 commit，不产 artifacts。"
  affects: [CMakeLists.txt]
