# term-ime 词库

拼音词库与简繁转换数据。原先在独立仓 `adam-ikari/term-ime-dict` 独立版本维护，
现并入本仓的 `dict/` 目录 —— 与 librime 补丁同仓、共用一个 tag，rime 栈从此只有
一个版本坐标。

## 文件

| 文件 | 说明 |
|------|------|
| `luna_pinyin.dict.yaml` | 词库本体。67051 条 (词, 拼音) 映射（2026-10 全部转简体并去重，原 70655 条繁体；再经 `tools/pinyin_fixes.txt` 订正错音、删污染简拼的死读音、补现代规范读音）。同词多读音保留为多行。 |
| `essay.txt` | 词频表，437873 条带权重词条（2026-10 升级到 rime-essay 官方最新版 442688 条，再全部转简体去重）。词库开了 `use_preset_vocabulary`，靠它加载词频 —— 缺了它候选会退化成按 Unicode 排序的单字（生僻字排在常用字前面），词组也出不来。 |
| `opencc/` | 简繁与字形转换数据，供 schema 的 simplifier 用：`t2s_full.json`（简体输出主路径）、`t2hk.json` / `t2tw.json`（港/臺字形）。 |

三个文件是一套：schema 按名字引用 `luna_pinyin` 词库，词库按名字加载 `essay.txt`，
简体方案再挂 opencc 转换。改其中任何一个都要另两个配套。

**主词库只放「组不出」的条目**。67051 条里 45306 条是单字、其余是成语与固定
搭配；像「中国」「人工智能」这种能按单字读音组合出来的词**故意不在主词库里**
——引擎的 `ScriptEncoder` 会动态组词，词频由 essay 提供（43.7 万条里 91%
不在主词库）。所以「某词不在 luna_pinyin.dict.yaml 里」并不等于打不出来，
判断词库缺词要先用引擎实测（`make -C tools smoke` 的做法），别看文件下结论。

## opencc/ 必须是自足的

librime 把 `opencc_config` 解析成 `<共享数据目录>/opencc/<配置文件>`
（`src/rime/gear/simplifier.cc`）；文件找不到时 `SimplifierComponent::Create`
返回 `nullptr` —— filter 静默不存在，候选退成未转换的字形，部署不报错、日志之外没有任何痕迹。

所以 `dict/opencc/` 里的每个 `.json` 所引用的 `.ocd2` / `.txt` 都必须和它一起提交，
不能靠 opencc 安装前缀兜底：`libopencc.a` 里的 `PKGDATADIR` 是编译期烧进去的绝对路径，
只在构建机上成立。本仓的 `CMakeLists.txt` 在 configure 期断言这条闭包，缺文件即失败。

**简体化（2026-10）**：两库原本是繁体（rime-essay 与 luna_pinyin 上游都是繁体），
靠 `luna_pinyin_simp` 的 simplifier 转简体上屏。现在两库内容本身已是简体，
simplifier 退化为幂等护栏。

转换有两个必须知道的坑：

- **`乾`（gān 干燥 / qián 乾隆）与 `薹`（tái 蒜薹）是合法简体字**，不是繁体
  残留，但 opencc `t2s` 会把它们误转成 `干`/`苔`。转换时逐字保护，否则输 `qian`
  会出「干」而不是「乾」。`tests/test_simplified_candidates.py` 的 KEEP 集合钉住了
  这条契约。
- **一简对多繁**：`乾` 有 gan/qian 两读、`乾/幹/榦/汫` 都归 `干`。转换按 (词, 拼音)
  对去重而非只按词去重，保留多读音独立行 —— 合并成单一读音会让输入另一读音时打不出
  该字。

`LICENSE` 按文件分别标注授权，跟随各自上游：`luna_pinyin.dict.yaml` 派生自
[rime/rime-luna-pinyin](https://github.com/rime/rime-luna-pinyin)，`essay.txt` 派生自
[rime/rime-essay](https://github.com/rime/rime-essay)，两者均为 **LGPL-3.0**；
`opencc/` 的 `t2s.json`/`t2hk.json`/`t2tw.json` 与 `*.ocd2` 来自
[BYVoid/OpenCC](https://github.com/BYVoid/OpenCC)，为 **Apache-2.0**；而
`opencc/t2s_full.json` 与 `variants*.txt` 是本项目原创转换表，**MIT**。本项目对这些
数据只做生成性修改（转简体、去重、升级版本），派生作品的许可证跟随上游 —— 整个
`dict/` 不是 MIT，也不是任何单一授权。完整条款与打包分发义务（可随其他程序分发，
含 LGPL 的 notice/源码义务）见 [`LICENSE`](LICENSE) 与 [`../licenses/`](../licenses/)。

## 为什么并进来

原先词库与 librime 是两个 submodule、两个独立的 pin 点。librime 那边锁的是
`1.16.1` 之后的无名 commit（没有 tag），所以「term-ime 用的哪个 librime」无法
命名；词库这边只有 `v1.0.0`。两个坐标要靠人脑记住它们配套。

并成一个 tag 之后，词库数据与消费它的 librime 补丁同一次提交、同一个版本号，
不存在「装了新词库但 librime 没跟上」这种组合。

代价：本仓不再是干净的 librime fork。日后同步上游：

```sh
git remote add upstream https://github.com/rime/librime
git fetch upstream
git merge upstream/master        # dict/ 与上游无交集，正常不会冲突
```

`dict/` 是上游不存在的目录，所以合并只会碰 librime 自己的文件。

## 生成与复现

`dict/` 里的东西全是产物。引擎构建不生成它们 —— 生成需要 host Python 和一个
现编译、现执行的 `opencc_dict`，Windows 上要装 Python、NDK 交叉编译会直接
`Exec format error`，而 librime 运行时只需要数据本身。

生成工具在 `tools/`，全部显式调用，故意不接进 CMake：接进去哪怕做成非 `ALL`
目标，也会把「配置引擎」和「生成词库」重新绑回同一张编译图。

```sh
make -C tools check            # 重新生成，并与本目录已提交内容逐字节比对
make -C tools smoke            # 部署真实引擎，断言词库可用（需先构建引擎）
make -C tools audit            # 单字死读音审计（只读）：污染首字母简拼的读音
make -C tools audit-words      # 词组行只有旧读、现代规范读打不出来（只读）
make -C tools audit-coverage   # 单字漏收规范读造成的组词盲区（只读）
make -C tools package          # 打成 term-ime-dict-<VERSION>.tar.gz
```

三个 `audit*` 是校准用的读数工具，需要开发期 oracle（`pip install pypinyin`）；
它们不改数据，人工核对后的结论落成 `pinyin_fixes.txt` 的 `del`/`add` 行
（`EMIT=1` 出可直接粘贴的指令行，仍须逐条查字典）。check/smoke 都不依赖 oracle。
`MIN_WEIGHT`/`TOP_WORDS`/`LIMIT`/`MIN_FREQ` 用来调读数阈值。

五条契约，写进 `tools/` 的脚本里，改脚本前先读：

- **essay.txt 不裁剪**。437873 条全留：`luna_pinyin` 开了 `use_preset_vocabulary`，
  词频与大部分词组只在这份表里（91.2% 不在主词库），删条目等于删候选。
- **只做逐字转换**（`tools/t2s_char.json` 只挂 `TSCharacters.ocd2`）。词组表会把
  词本身换掉（家俱 → 家具），异体表会把生僻码位折叠到常用字（㐀 → 丘）；词库
  要的是一次字符级重编码，不是一次用词规范化。运行时那条 `t2s_full.json` 链是
  给上屏文本用的，两件事不能混。
- **乾(gān/qián)、薹(tái) 逐字保护**（`tools/protected_chars.txt`），去重按
  **(词, 拼音)** 而非只按词 —— 一简对多繁，同词多读音必须各留一行，否则输入
  另一读音打不出该字。
- **错音只改 `tools/pinyin_fixes.txt`，不改产物**。上游底本是钉死的 git 对象，
  改不了源头；产物里发现的错音（蚌埠市 bang fu shi）、单字缺读音（老挝 wo）
  一律写进这张表，由 `convert_dict.py` 每次生成时套上，`make check` 仍逐字节
  复现。手改 `dict/luna_pinyin.dict.yaml` 等于放弃复现门。表里三个指令：
  `fix` 整词替换读音、`del` 删一条错读音、`add` 补一个读音（单字或词组都可）。
- **删读和补读是同一处校准的两个方向，判据要能写成代码也不能只有一条**。删的
  门槛：该读音与主导读声母冲突、且在现代词组表与本仓词库双零实配（简拼会被它
  带偏，见 `audit`）。补的门槛：宽表有这一读、本仓该字/该词现有各行里没有、
  essay 里真有用到（词组行看词频、单字行看被卡词的词频之和）。两条都不许只凭
  「字典里查得到这字能这么读」下手；pypinyin 按上下文猜出来的读音（精雕细琢它
  给 zuo、区域网路它给 luo）一律不作证据。

五条契约管「怎么生成」，另有一道门管「生成的东西引擎读不读得动」：
`make -C tools smoke` 把本目录按安装布局（引擎数据取 `data/minimal/`，词库与
essay 取本目录覆盖同名 minimal 文件）装进临时部署，用 `rime_console` 真编译
一遍，断言三类事 —— 部署日志零错误行（模式编译失败、词条被表构建器拒绝这类
问题只在真部署里现形，逐字节比对看不见）；几条探针能提交出预期文字（含一个
多音字的两个读音）；简拼首页候选既不出现只靠死读音才拼得出的词，也必须出现
现代读音应有的词（`ABBREV_PROBES` 守删除那一半，`ADD_PROBES` 守补读这一半）。
check 证明「与已提交内容一致」，smoke 证明「引擎用得动」，两道门缺一不可。

**关于文言读音**：底本里的文言/古读（乡 yuān、于 xū、兒 ní 等）属于**扩展词库
范畴**，不是错音。它们当前留在主词库里，与上游底本保持一致——底本钉死在
sources.lock，改源头就放弃复现契约。曾尝试按 Unihan kMandarin 自动分流到独立
扩展词库文件，但 kMandarin 是「最常用读音」单值字段，做不了多音字分类器：
它把「万 wanmo」「参 can」这类读音判成非现代、把「参差 cēn cī」这种标准现代
不规则变调判成文言，自动分流必然误伤日常输入。若将来要做，正确形态是**清单
驱动**（逐条人工审定的文言词清单），而非自动判定；且 librime 的
`translator/dictionary` 只支持单个词典，挂扩展词典需经 `translator/packs`
或独立 schema。

`tools/sources.lock` 钉住三个输入坐标。`luna_pinyin` 的底本不是上游某个 release，
而是本仓 `64eda4c7` 里那份繁体快照（上游此后加了读音权重、补了日文国字与注音
索引，本仓又剪过 115 行），所以取底本要读 git 历史，浅克隆取不到。

## 版本：两个坐标

- `v…-rime-stack`：引擎 + 词库配套发布。term-ime 用 submodule 锁它的 commit，
  组合关系固定在 term-ime 那次 tag 里。
- `dict-<VERSION>`：纯词库重发，不动引擎。版本号读 `VERSION` 文件，tag 与它不符
  时 workflow 直接失败。内容不变、只是数据修订时走这一条。

`dict-*` 的最低可用 stack：

| 词库 | 最低 librime | 为什么 |
|---|---|---|
| `dict-2026.10.09` | `v1.1.8-rime-stack` | 简繁数据闭包（`t2hk`/`t2tw` + `HK`/`TWVariants.ocd2`）与 `use_preset_vocabulary` 的词频依赖都从这次起 |
| `dict-2026.10.10` | `v1.1.8-rime-stack` | 纯数据修订：`luna_pinyin.dict.yaml` 错音订正与单字补读音（`tools/pinyin_fixes.txt`），无新引擎依赖 |
| `dict-2026.10.11` | `v1.1.8-rime-stack` | 纯数据修订：清理底本为超高频虚词保留的文言读音行（36 条 `del`），无新引擎依赖 |

（`v1.1.9-rime-stack` 之后的引擎变更——上游 67 提交合并、PCRE 翻译层——属引擎侧，
不改变词库的最低 stack 要求。）

改词库：在这里改，`make -C tools check` 过，随引擎一起发 stack tag；只动数据就发
`dict-*`。term-ime 更新 submodule 指针。
