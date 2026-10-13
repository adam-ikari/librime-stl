---
id: vendored-upstream-pins
title: "外部来源的 pin 点（sources.lock / deps / rime-emoji）"
category: reference
status: active
tags: [provenance, license]
created: "2026-10-13T05:37:49"
updated: "2026-10-13T05:38:33"
---

<!-- compiled_truth -->
## 词库输入坐标（`dict/tools/sources.lock`）

- `essay-base = b1e8b2ab…`（rime-essay 的繁体快照，转简体前提交进仓）
- `opencc = 556ed224…`（vendored 在 `deps/opencc` 的上游对应提交）
- `luna-pinyin-base = 64eda4c7…`（**本仓**历史里那份繁体底本，不是上游 release）
- `emoji-base = 771d613b…`（rime-emoji 的 **`Emoji-14.0` 分支顶端**，LGPL-3.0）

必须钉 commit 而非分支名；底本从 git 历史取（`git show <SHA>:<path>`），浅克隆取不到。

## 教训：钉 SHA 与所测内容要互相核验

首次钉的 `master@39d23299` 那份 `emoji_word.txt` 只有 4668 行，而实际核验过的是
7218 行——哈希对不上才发现上游默认分支 `master` 覆盖比 `Emoji-14.0` 分支小。
vendored 数据落地时要「哈希 ↔ 行数 ↔ 分支」三者互相印证，别只信分支名或只信 SHA。

## 授权（逐文件，不是单一整体）

LGPL-3.0：`luna_pinyin.dict.yaml`、`essay.txt`、`opencc/emoji*`；
Apache-2.0：opencc 的 `t2s/t2hk/t2tw.json` 与 `*.ocd2`；
MIT：本仓原创的 `t2s_full.json`、`variants*.txt` 与自有代码。
emoji 三件是**逐字副本**，`rebuild_ocd2.sh` 只拷贝不生成，`make check` 仍比对它们。
详见 `dict/LICENSE` 与 `THIRD-PARTY.md`。


## Timeline

- time: 2026-10-13T05:37:49
  kind: decision
  summary: "Created this page: 外部来源的 pin 点（sources.lock / deps / rime-emoji）"
  source: session 2026-10-13
  affects: [vendored-upstream-pins]

- time: 2026-10-13T05:38:33
  kind: decision
  summary: "初版：记录 pin 点与 rime-emoji 分支陷阱"
  source: session 2026-10-13
  affects: [vendored-upstream-pins]
