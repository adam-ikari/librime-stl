---
id: dict-reproducibility-gates
title: "dict/ 的复现契约与两道门（check / smoke）"
category: decision
status: active
tags: [dict, gates]
created: "2026-10-13T05:37:49"
updated: "2026-10-13T05:38:08"
---

<!-- compiled_truth -->
## 契约

`dict/` 里全是产物，产物不许手改。订正只进 `dict/tools/pinyin_fixes.txt`
（`fix` 整词换读 / `del` 删一条读音 / `add` 补一个读音），由 `convert_dict.py` 每次
生成时套上，于是 `make -C dict/tools check` 仍能逐字节复现。输入版本坐标钉在
`sources.lock`，底本要从 git 历史取（浅克隆取不到）。

五条生成契约（写进 `tools/` 脚本）：essay.txt 不裁剪；只做逐字转换；乾 gān/qián、
薹 tái 逐字保护且按 (词, 拼音) 去重；错音只改 fixes 表；删读与补读是同一校准的两个
方向、判据要能写成代码但不能只有一条证据。

## 两道门的分工

- **`make -C dict/tools check`**：一致性门。重新生成并与已提交内容逐字节比对
  （essay.txt / luna_pinyin.dict.yaml / opencc/）。看不见「引擎用不用得动」。
- **`make -C dict/tools smoke`**：可用性门。建临时部署（`data/minimal/` 引擎数据 +
  `dict/` 覆盖同名 + `dict/opencc/` 装进 `<root>/opencc/`），用 `rime_console` 真编译
  真查词，断言四类事：零 glog error、提交文本含多音字两读、简拼首页（`ABBREV_PROBES`
  守删除、`ADD_PROBES` 守补读）、emoji 滤镜开关两侧（`EMOJI_PROBES`）。

## 门本身也要被证伪

新增断言后要确认它真能红：注掉 `luna_pinyin.schema.yaml` 的 `__patch` 行再跑 smoke，
`EMOJI_PROBES` 两条立刻失败。2026-10-13 之前 smoke **从不部署 opencc 目录**，schema 里
所有 simplifier 都是空转——「零 error」的断言因此一直是绿的，因为那条路径根本没走过。


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
