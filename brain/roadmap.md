---
slug: roadmap
title: Roadmap
role: milestones
updated: "2026-10-15T00:16:13"
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
  构建图边界 + 依赖来源硬门                :done, a8, 2026-10-14, 1d
  signal 替身补齐分组 connect              :done, a9, 2026-10-15, 1d
  section 待办
  文言读音按清单分流到扩展词库             :b1, after a6, 14d
  档 B 之外的古读复核（freq 1000–5000）    :b2, after b1, 10d
  emoji 数据换 pin 的例行流程演练          :b3, after a6, 3d
  librime-lua 进矩阵（Lua 5.4 交叉 + shim） :c1, after a9, 21d
```

- **文言读音分流（b1）**：底本里的文言/古读属扩展词库范畴，不是错音。曾试 Unihan
  kMandarin 自动分流，它是「最常用读音」单值字段，做不了多音字分类器，必然误伤日常
  输入；正确形态是**清单驱动**（逐条人工审定），且扩展词典要经 `schema/dependencies`
  或独立 schema 挂。
- **b3**：`emoji-base` 换 SHA 等于换 emoji 覆盖范围，要走 `make check` + smoke，且
  注意上游默认分支 `master` 的覆盖比 `Emoji-14.0` 小（见 [[vendored-upstream-pins]]）。

- **librime-lua（c1）**：按 [[background]] 原则 1，lua 出局不能拿 Boost 当理由。实测缺口
  只剩三条，第一条已补：`src/rime/signal.hpp` 的 `connect(group, slot)`（`test/signal_test.cc`
  钉住分组顺序与 connection 生命周期）；接着是 `cmake/plugin-shim/boost/` 应答
  `signals2.hpp`（别名到 `rime::connection`——插件从不自己 include 它，名字是从上游
  `common.h` 继承的）与 `optional.hpp`（`std::optional`），`regex.hpp` 要 `std::regex` 加
  已有的 PCRE→ECMAScript 转换；最后才是把 Lua 5.4 进 `deps/` 与那张 flag 表并交叉编译验证，
  再回插件矩阵跑一份带 lua 钩子的 schema smoke。Shim 只能出现在插件图里，引擎头文件不准
  伪造 `namespace boost`——装了真 Boost 的消费方会撞上两个不同的 `boost::signals2::connection`。
