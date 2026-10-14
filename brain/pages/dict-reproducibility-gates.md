---
id: dict-reproducibility-gates
title: "dict/ 的复现契约与两道门（check / smoke）"
category: decision
status: active
tags: [dict, gates]
created: "2026-10-13T05:37:49"
updated: "2026-10-14T07:09:36"
---

<!-- compiled_truth -->
## 契约

`dict/` 里全是产物，产物不许手改。订正只进 `dict/tools/pinyin_fixes.txt`
（`fix` 整词换读 / `del` 删一条读音 / `add` 补一个读音），由 `convert_dict.py` 每次
生成时套上，于是 `make -C dict/tools check` 仍能逐字节复现。输入版本坐标钉在
`sources.lock`，底本要从 git 历史取（浅克隆取不到）。

契约覆盖的是**所有已提交的生成物**，不止 `dict/`：引擎测试用的 opencc 数据
`test/opencc/` 同样只能由 `dict/tools/` 的脚本现生成、由 check 现比对。

五条生成契约（写进 `tools/` 脚本）：essay.txt 不裁剪；只做逐字转换；乾 gān/qián、
薹 tái 逐字保护且按 (词, 拼音) 去重；错音只改 fixes 表；删读与补读是同一校准的两个
方向、判据要能写成代码但不能只有一条证据。

## 门

- **`make -C dict/tools check`**：一致性门。重新生成并与已提交内容逐字节比对，四条
  闭包分别报错——essay.txt / luna_pinyin.dict.yaml / opencc/ / test/opencc/。
  看不见「引擎用不用得动」。
- **`make -C dict/tools smoke`**：可用性门。建临时部署（`data/minimal/` 引擎数据 +
  `dict/` 覆盖同名 + `dict/opencc/` 装进 `<root>/opencc/`），用 `rime_console` 真编译
  真查词，断言四类事：零 glog error、提交文本含多音字两读、简拼首页（`ABBREV_PROBES`
  守删除、`ADD_PROBES` 守补读）、emoji 滤镜开关两侧（`EMOJI_PROBES`）。

`toolchain` 是全仓唯一允许 host Python 与 host 执行 `opencc_dict` 的地方；引擎的
配置/构建图永远够不到两者（`dict-check.yml` 把这条写成了注释）。

## test/opencc/：rime_test 的 opencc 固定数据集

`deps.mk` 以 `OPENCC_BUILD_DATA=OFF` 编译 vendored opencc（那一步要 host Python 生成
`*Rev.txt`、又要 host 执行 `opencc_dict`，NDK 交叉编译直接 `Exec format error`），
代价是 macOS/Windows 上根本没有 `<prefix>/share/opencc`，而上游
`test/CMakeLists.txt` 在配置期硬要求 `Opencc_DICT_DIR`。两条出路都被本仓的不变量否掉：
重开 opencc 数据步＝把 host Python/host 工具请回构建图；`GTEST_SKIP`＝在唯一两个
没有系统 opencc 的平台上取消 simplifier↔opencc 的覆盖。

取第三条形同 `dict/opencc/`：把 opencc 自身安装目录的忠实镜像（14 个 config + 16 个
`.ocd2`，即这 14 个 config 引用闭包）由 `rebuild_test_opencc.sh` 现生成、提交在
`test/opencc/`，`test/CMakeLists.txt` 用一个 `# fork:` 块**无条件**把
`Opencc_DICT_DIR` 指过去——有系统 opencc 的平台（Linux、Docker）也用同一份，断言内容
不随平台变。它是测试夹具，不进 `make package` 的 tarball。

## 门本身也要被证伪

新增断言后要确认它真能红。已验过的三次：注掉 `luna_pinyin.schema.yaml` 的 `__patch`
行再跑 smoke，`EMOJI_PROBES` 两条立刻失败；删掉 `test/opencc/t2s.json` 再跑
`OpenccTest.*`，3 条 t2s 断言立刻失败（证明测试真读这份固定集，而不是系统 opencc）；
给 `test/opencc/tw2t.json` 尾随加一个字节再跑 check，`DIFF test/opencc/` 立刻红。
2026-10-13 之前 smoke **从不部署 opencc 目录**，schema 里所有 simplifier 都是空转——
「零 error」的断言因此一直是绿的，因为那条路径根本没走过。


## Timeline

- time: 2026-10-13T05:37:49
  kind: decision
  summary: "Created this page: dict/ 的复现契约与两道门（check / smoke）"
  source: session 2026-10-09..13
  affects: [dict-reproducibility-gates]

- time: 2026-10-13T05:38:08
  kind: decision
  summary: "初版：写死复现契约与两道门的分工"
  source: sessions 2026-10-09..13
  affects: [dict-reproducibility-gates]

- time: 2026-10-14T01:36:03
  kind: decision
  summary: Rewrote compiled_truth to the new best understanding
  source: brain update-truth
  affects: [dict-reproducibility-gates]

- time: 2026-10-14T07:09:36
  kind: evidence
  summary: "check/smoke 之外新增第三道来源门：configure 打印每个依赖的解析路径与 opencc 的 resolved/pin，声明 -DRIME_DEPS_PREFIX 的构建（Android 交叉、CI hermetic-deps）把「opencc 不是 pin」变成硬错误。见 [[hermetic-build-graphs]]。"
  affects: [dict-reproducibility-gates]
