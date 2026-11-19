---
id: rime-ice-dictionary-merge
title: "rime-ice 词库并入 dict/ 的契约"
category: decision
status: active
tags: [dict, rime-ice, licensing]
created: "2026-11-19T08:47:02"
updated: "2026-11-19T10:18:13"
---

<!-- compiled_truth -->
## 契约

- 上游坐标：iDvel/rime-ice `927e1cf1d3eeb9bf4be85e3f684dba4dd485b6f6`，随仓
  `dict/tools/upstream/rime-ice-<SHA>.tar.gz`（cn_dicts + en_dicts + LICENSE +
  rime_ice.dict.yaml）。`make check` 必须离线复现，禁止生成期联网取上游。
- 中文读音：`cn_dicts/` 的 8105/41448/base/ext/others 转简体、按 (词, 拼音) 去重后
  并入 `luna_pinyin.dict.yaml`，本地底本与 `pinyin_fixes.txt` 优先。
- 词频：`tencent` 只带权重，不进主词库；rime-ice 各表取每词最高权重并入 `essay.txt`。
  已在 rime-essay 的词保留本地权重；新词权重映射到 `(0, 1)`，保留新词间顺序但绝不
  压过本仓权重 ≥ 1 的词。这是避免大词库扰乱已校准首页的关键不变量。
- 英文词表：`en_dicts/` 不进中文生成链，由 `vendor_en_dicts.py` 逐字拷进 `dict/en/`，
  进入 check 与 package 闭包，供英文 schema 按需挂载。
- THUOCL 联动：`build_thuocl.py` 按合并后的 luna/essay 去重，产物 74938 → 3239 条；
  旧长尾示例已进主词库，`THUOCL_PROBES` 正侧必须用只有导入才提供的词，否则门会假绿。
- 授权：rime-ice 整体 GPL-3.0、cn_dicts 多来源汇编；派生部分保持 GPL-3.0，合并产物
  按 GPL-3.0 分发，不单方面改挂 MIT/LGPL。
- 可用性门：`smoke.py` 的两处探针随大词库语义化——`是不是` 改用真实三音节简拼 `sbs`，
  死读音 `身份识别` 守卫独立留在 `sbsb`；`犍为` 改用补读后的 `qianwei`。断言强度不减。

## 验证

`make -C dict/tools check` 六闭包全 OK；`make -C dict/tools smoke` 全绿；
`make -C dict/tools package` 产物含 `en/`。抽空 `thuocl.dict.yaml` 的三条正探针
立刻失败，证明 THUOCL 门仍守导入而非主词库。


## Timeline

- time: 2026-11-19T08:47:02
  kind: decision
  summary: "Created this page: rime-ice 词库并入 dict/ 的契约"
  source: 2026-11-19 integration session
  affects: [rime-ice-dictionary-merge]

- time: 2026-11-19T08:47:02
  kind: decision
  summary: "rime-ice 全量并入 dict/：离线 pin、权重缩放、英文词表独立落库、smoke 探针语义化"
  source: brain update-truth
  affects: [rime-ice-dictionary-merge]

- time: 2026-11-19T08:47:02
  kind: decision
  summary: "全量并入 rime-ice；新增词频缩放到 (0,1) 保留本地排序；英文词表独立 vendor；smoke 探针按真实读音拆分"
  source: 2026-11-19 integration session
  affects: [rime-ice-dictionary-merge]

- time: 2026-11-19T10:18:13
  kind: decision
  summary: Rewrote compiled_truth to the new best understanding
  source: 2026-11-19 integration session
  affects: [rime-ice-dictionary-merge]

- time: 2026-11-19T10:18:13
  kind: decision
  summary: "THUOCL 产物随主词库合并重算为 3239 条；正探针换成只有导入才提供的词，抽空导入验证会红"
  source: 2026-11-19 integration session
  affects: [rime-ice-dictionary-merge]
