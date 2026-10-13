---
id: emoji-filter-dictionary
title: "emoji 扩展词典：滤镜词典 + option 运行时开关"
category: decision
status: active
tags: [dict, opencc, emoji]
created: "2026-10-13T05:37:49"
updated: "2026-10-13T05:38:33"
---

<!-- compiled_truth -->
## 结论

emoji **不进主词库**，做成一份独立的 opencc text 词典挂在滤镜上：
`dict/opencc/emoji.json` + `emoji_word.txt`(7218 行) + `emoji_category.txt`(212 行)，
由 `data/minimal/emoji_suggestion.yaml` 的 patch 把 `simplifier@emoji_suggestion`
前置进 `engine/filters`，`luna_pinyin.schema.yaml` 只加一行
`__patch: emoji_suggestion:/patch`。默认关（`reset: 0`），`Ctrl+Shift+6` 切换。

## 为什么只能是这个形态（引擎事实，不是偏好）

- 运行时决定候选出不出现，librime 里只有 **option 门控**的组件做得到；候选处理路径上
  就是 `simplifier`（`src/rime/gear/simplifier.cc:86` 读 `get_option(option_name_)`）。
- translator 没有 option 概念，只能按 **tag** 门控（tag 来自 `recognizer/patterns` +
  `affix_segmentor` 的前缀，即 `C:`/`P:` 那套 v 模式）——那是逐次显式触发，不是一键开关。
- `translator/packs` 与主词库共用同一个 prism（`dict_compiler.cc:152-205`），只能给
  已有音节补词条，既不能加音节也不能单独关。

## 取舍与坑

- 不改 `default.yaml` 的 `switcher/save_options`，因此开关**不跨方案重载持久**
  （`switcher.cc:280` 只从 default 配置读 save_options）。有意的取舍，写进 dict/README.md。
- `patch` 的 `key_binder/bindings/@next`：`@next` 追加**一个列表元素**，value 必须就是
  绑键本身；写成 `- {…}` 会把列表嵌进 bindings 被静默忽略（第一版就栽在这里，是看编译后
  的 `build/luna_pinyin.schema.yaml` 才抓出来）。绑键能穿过 `import_preset: default`
  的列表合并，无需退路去改 default.yaml。
- 命中词的其他 emoji 成为 `ShadowCandidate`，`tips: all` 把原词留在 comment
  （实测 `kaixin` 开后：`开心` / `😁`〔开心〕 / `🥳`〔开心〕）。
- tarball 只含 rime-data，不含 schema：消费方要在自己的方案里挂同样的 simplifier
  与 switch，照 `data/minimal/emoji_suggestion.yaml` 抄。


## Timeline

- time: 2026-10-13T05:37:49
  kind: decision
  summary: "Created this page: emoji 扩展词典：滤镜词典 + option 运行时开关"
  source: session 2026-10-13
  affects: [emoji-filter-dictionary]

- time: 2026-10-13T05:38:33
  kind: decision
  summary: "初版：emoji 采用滤镜词典 + option 开关的形态与取舍"
  source: session 2026-10-13
  affects: [emoji-filter-dictionary]
