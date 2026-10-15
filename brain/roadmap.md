---
slug: roadmap
title: Roadmap
role: milestones
updated: "2026-10-15T01:34:33"
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
  librime-lua 进插件矩阵（桌面三图）       :done, c1, after a9, 1d
  section 待办
  文言读音按清单分流到扩展词库             :b1, after a6, 14d
  档 B 之外的古读复核（freq 1000–5000）    :b2, after b1, 10d
  emoji 数据换 pin 的例行流程演练          :b3, after a6, 3d
  Android 侧 librime-lua 交叉 + lua schema smoke :c2, after c1, 21d
```

- **文言读音分流（b1）**：底本里的文言/古读属扩展词库范畴，不是错音。曾试 Unihan
  kMandarin 自动分流，它是「最常用读音」单值字段，做不了多音字分类器，必然误伤日常
  输入；正确形态是**清单驱动**（逐条人工审定），且扩展词典要经 `schema/dependencies`
  或独立 schema 挂。
- **b3**：`emoji-base` 换 SHA 等于换 emoji 覆盖范围，要走 `make check` + smoke，且
  注意上游默认分支 `master` 的覆盖比 `Emoji-14.0` 小（见 [[vendored-upstream-pins]]）。

- **librime-lua（c1 已完成，桌面图）**：按 [[background]] 原则 1，lua 出局不能拿 Boost
  当理由，实测三条缺口都已合：`src/rime/signal.hpp` 的 `connect(group, slot)`
  （`test/signal_test.cc` 钉住分组顺序与 connection 生命周期）；插件图的
  `cmake/plugin-shim/boost/signals2.hpp` 别名到 `rime::connection`（插件从不自己 include
  它，名字是从上游 `common.h` 继承的，所以只能 force-include，且只对 C++ TU——同目录要编
  Lua 的 `.c`）；`regex.hpp` 用 `std::regex` 加已有的 PCRE→ECMAScript 转换。
  `optional.hpp` 不应答：插件自己在 C++17 下走 `std::optional` 分支（`src/optional.h:1`），
  那是条死路。两个反直觉的点是被测出来的：regex 必须**无条件**遮蔽真 Boost（本 fork 的
  librime 不再携带 boost_regex，装了真 Boost 的机器上 merged 构建链不动工具、standalone
  插件 .so 带未定义 boost 符号直到 dlopen 才炸），而 `algorithm/string.hpp` 反过来**只能**
  当无 Boost 时的退路（header-only，且 librime-charcode 用 `boost::split`/`is_any_of`，
  遮蔽它等于打挂一个我们并不支持的插件）。引擎头文件始终不准伪造 `namespace boost`。
- **Android（c2）**：交叉图 `ENABLE_EXTERNAL_PLUGINS=OFF`，产物只有 `librime.so`，
  所以带 lua 的 Android 是「另做一次插件交叉构建」，不是这里加一个开关。本机无 NDK，
  这一步只能在 CI 里第一次跑；不要在没有可复现判据之前把它写进文档当已支持。
