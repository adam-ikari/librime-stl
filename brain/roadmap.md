---
slug: roadmap
title: Roadmap
role: milestones
updated: "2026-10-13T05:37:39"
---

# Roadmap

## Milestones

```mermaid
gantt
  title Roadmap
  dateFormat YYYY-MM-DD
  section 已完成
  去 Boost（std::regex + shim）           :done, a1, 2026-06-01, 60d
  词库并仓 + 两道门                        :done, a2, 2026-09-01, 30d
  简繁数据闭包与 ocd2 复现                 :done, a3, 2026-10-01, 8d
  简拼死读音校准（149 条 del）             :done, a4, 2026-10-09, 4d
  补现代规范读音（add 行）                 :done, a5, 2026-10-11, 2d
  emoji 扩展词典（滤镜 + 运行时开关）      :done, a6, 2026-10-13, 1d
  源码注释策略（中译英 + fork 标记）       :done, a7, 2026-10-13, 1d
  section 待办
  文言读音按清单分流到扩展词库             :b1, after a6, 14d
  档 B 之外的古读复核（freq 1000–5000）    :b2, after b1, 10d
  emoji 数据换 pin 的例行流程演练          :b3, after a6, 3d
```

- **文言读音分流（b1）**：底本里的文言/古读属扩展词库范畴，不是错音。曾试 Unihan
  kMandarin 自动分流，它是「最常用读音」单值字段，做不了多音字分类器，必然误伤日常
  输入；正确形态是**清单驱动**（逐条人工审定），且扩展词典要经 `schema/dependencies`
  或独立 schema 挂。
- **b3**：`emoji-base` 换 SHA 等于换 emoji 覆盖范围，要走 `make check` + smoke，且
  注意上游默认分支 `master` 的覆盖比 `Emoji-14.0` 小（见 [[vendored-upstream-pins]]）。
