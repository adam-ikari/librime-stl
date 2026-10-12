# 词库更新日志

词库与 librime 补丁同仓、共用一个 tag —— 版本号只在本仓的 tag 上。

## dict-2026.10.12

清理底本给高频单字收的死读音，修首字母简拼（纯数据，不涉引擎）。

症状：打 `ffff` 出「不仅仅 / 不复发 / 服不服」。这些词按现代读音是 bù jǐn jǐn，
走不到 f-f-f；能走到是底本给单字收了古读/通假行（仅 fù、不 fū），而 schema 的
`abbrev/^([a-z]).+$/$1/` 把每个音节缩成首字母。同一份词库在上游 librime 1.7.3 与
本 fork 上给出同类候选，污染在数据不在引擎。

新增只读审计工具 `tools/audit_readings.py`（`make -C tools audit`）：对每条
(字, 读音) 算声母冲突、本仓词库实配、pypinyin 现代词组实配、essay 字频，
`--emit-del` 直接出 `del` 指令。判定线与豁免面写在该文件头部。

- **149 条单字死读音删除**（档 A 120 条：连 pypinyin 汉典式宽表都没有这一读，
  纯底本错音——我 e、她 yi、月 rou、请 jing、钱 jian、开 jian/qian、页 xie、
  抓 chua、抢 chuang、鞋 hai、参 san、壳 que…；档 B 29 条：宽表有记录但
  《现代汉语词典》现代规范不收的古读，逐条人工判定——不 fu/fou、仅 fu、
  听 yi/yin、机 wei、女 ru、王 yu、儿 ren、台 si/yi、份 bin、需 ru/nuo/ruan、
  体 ben、冰 ning、造 cao、追 dui…）。
- **保留的**：合法多音字一律不动（说 shuō/shuì/yuè、会 huì/kuài、从 cóng/zōng、
  将 jiāng/qiāng、行 xíng/háng/héng、卡 kǎ/qiǎ、榜 bèng/péng、拓 tà/zhí、
  覃 tán/qín、汀 tīng/dīng…），低频字不进清单（生僻字古读真有人打，简拼
  污染不到），叹词/语气词整类豁免（啊 呵 噢 哦 嗯 咯 呢 吗 吧…俗成读音
  两套语料都收不全）。厂 hàn/yǎn 现代词典仍列，保留。
- **词条 67141 → 66992**（−149，纯删除无新增；被删行全部是单字行，词组行
  一条未动 —— 文言词组自带音节串，「进可替不」jin ke ti fou 删掉「不 fou」
  单字行后打全拼照样出）。
- **smoke 门加简拼断言**：`ABBREV_PROBES` 断言首页候选（`ffff` 必须出反反覆覆
  且不得出不仅仅/服不服/不复发/不悱不发；`bjj` 必须仍然出不仅仅，防止删过头）。
  在校准前的旧词库上跑同一批断言，5 条里 4 条红 —— 这道门是真能红的。
- 引擎实测前后对照：`fff` 从「不仅仅/服不服/不复发/烦不烦/放不放」变为
  「凤飞飞/方法/丰富/反复/反覆」；`rr` 不再出「女人/女儿」（女 rǔ 已删）；
  `sbsb` 不再出「身份识别」（份 bīn 已删）。

甄别方法：三条独立信号（pypinyin 现代词组表 47111 条、本仓词库 21713 条多字
词条、essay 字频）交叉，声母冲突且双零实配的进清单；档 A 由工具直接判定，
档 B 逐条查《现代汉语词典》人工判定。pypinyin 只是开发期 oracle，check/smoke
都不依赖它。

同日第二轮 —— 反向缺口：补现代规范读音（纯数据，不涉引擎）。

上一轮删「多收的打不出词的读音」，这一轮补「少收的打得出现代读音的行」。审计
工具加两个读数轴：`make -C tools audit-words`（词组行的音节串里宽表没有这一读，
再筛掉「另有现代读行」的，只剩现代读根本打不出来的）与 `make -C tools
audit-coverage`（essay 全表里不在词库的词，被单字缺读音卡住的组词盲区）。

- **32 条词组行补现代读**（旧读行保留，文言照打）：体癣 ti xuan（底本只有
  ti xian）、一怔 yi zheng（只有 yi leng）、桡骨 rao gu（只有 nao）、坯子 pi zi、
  咳血 ke xie/ke xue、蹦跶 beng da、哑然失笑 ya ran shi xiao、纲纪废弛
  gang ji fei chi、朴讷诚笃 pu ne cheng du、敬业乐群 jing ye le qun、
  仡佬族 ge lao zu、宁馨儿 ning xin er…（判据：essay 词频 >= 100）。
- **27 条单字补读**：睥 pi（词库只有 bì，睥睨 拼不出）、崤 xiao（只有 yáo）、
  瓿 bu（只有 pǒu，安瓿 拼不出）、骠 biao、券 xuan（拱券）、转 zhuai（转文）、
  掴 guai（掴耳光）、伧 chen（寒伧）、碡 zhou（碌碡）、柞 zha / 犍 qian（县名）、
  堡 bu（吴堡）、瞓 fen、畑 tian / 辻 shi / 麿 mi（和制汉字，词库整字缺行，
  essay 里小畑健、绫辻行人、近卫文麿 都在）…（判据：被卡词的词频之和 >= 100）。
- **不收的**：pypinyin 按上下文猜的读音（精雕细琢它给 zuo，规范 zhuo 已有行；
  区域网路它给 luo，正读 lu；收歛它给 han，正读 lian；啜饮它给 chuai，正读
  chuo）、嗯 n（成节音，加了等于把单字母 n 变成候选，简拼更乱）、文言长尾
  （essay freq 0 的 殽 xiao、襆 fu、跕 dian… 一百余条，收了没人打）。
- **词条 66992 → 67051**（+59：32 条词组行 + 27 条单字行，纯新增无删除）。
- **smoke 门加补读断言** `ADD_PROBES`（9 条：现代拼写在首页必须出该词）。在
  HEAD 的旧词库上跑同一批断言，9 条全红 —— `pini` 只出「比你/被你/比拟」，
  `anbu` 只出「暗部/阴部」，`jianwei` 连「犍为」的影子都没有。探针特意挑
  没有高频同拼写竞争的词：`xiaoshan` 补了崤 xiao 之后首页仍是「萧山」，那是
  词频的正确排序，不该由这道门断言。
- 两道门复验：`make check` 三个产物逐字节一致（essay/luna_pinyin/opencc 全 OK），
  `make smoke` 20 项断言全绿，部署日志零错误行。

## dict-2026.10.11

清理底本为超高频虚词保留的文言读音行（纯数据，不涉引擎）。

上游底本给 36 个超高频词保留了古读/旧读行（什么 shé me、还有 huán you、
大家 dà gǔ、中中的 zhōng dì、颜色 yán shǎi、矛盾 máo shùn、说服 shuì fú、
模样 mú yàng 等）。这些词的实际输入全走现代读音——essay 词频与引擎组词均
产出正确结果，引擎实测 shenme/haiyou/dajia 一直正确；文言行是历史包袱，且
与现代读音行并存、挤占同一批高频词的候选位。

- **36 条文言/错音行删除**（`tools/pinyin_fixes.txt` 的 `del` 指令，同词的
  现代读音行原样保留）：什么 she me、还有 huan you、大家 da gu、中的
  zhong di、那种 nei zhong、它们 tuo men、颜色 yan shai、多了 duo liao、
  咱们 za men、那时候/那边/那天/那位/那次 nei→na、矛盾 mao shun、罢了/
  不了/得了 liǎo→le、模板 mu ban、给予 ji yu、没人 mo ren、没了 mo le、
  完了/干了 liao→le、似的 shi de、活着 huo zhao、骑士 ji shi、概括 gai jie、
  暴露 pu lu、说服 shui fu、模样/一模一样 mu→mo、关卡 guan qia、打着
  da zhao、热血 re xie。
- **合法读音变体一律保留**，只删「拼写确错 + 现代读音已并存」的行：
  尴尬 jiān jiè、便宜 pián yi、穿着 zhuó 等底本另有的读法并非错音。
- 词条 67176 → **67141**（−35，纯删除无新增）。

甄别方法：以 Unihan kMandarin（现代通用读音）交叉核对多读音词，筛出
「essay 高频 + 现代读音行并存 + 另一行与 kMandarin 不符」的候选共 48 条，
再逐条查《现代汉语词典》人工判定。

## dict-2026.10.10

简体拼音词库修订（纯数据，不涉引擎）。

### 机制：错音订正表

上游底本是钉死的 git 对象（`sources.lock`），错音改不了源头。新增
`tools/pinyin_fixes.txt`，由 `convert_dict.py` 生成时套用，复现门
`make check` 不变。三个指令：`fix` 整词替换读音、`del` 删一条错读音、
`add` 给单字补读音。契约写进 `dict/README.md`。

### 内容

全库 composability 扫描（词条每音节必须能由对应单字的读音组合而成）：
违例 125 条 → **35 条**（剩余为方言词与生僻字存疑项，逐条核过不收）。

- **48 处错音订正**：蚌埠市 bang fu→**bu**、家蚕 chan→**can**、
  国有财产 can→**chan**、港埠 fu→**bu**、中山高速公路 shu→**su**、
  甚麼 she→**shen**、褶子 xue→**zhe**、哪咤 nuó→**né**、
  阿毗昙 tian→**tan**、肛瘘 lv→**lou** 等。
- **3 处词条文本订正**（读音暴露了底本的词形错误）：
  安静自在→**安闲自在**、心焦如火→**心焦如焚**、灵桩→**灵椿**。
- **19 处单字补读音**：行 heng（道行）、挝 wo（老挝）、倘 chang（倘佯）、
  喋 zha（唼喋）、趵 bo（趵趵）、摘 ti（摘伏）、唫 yin（呿唫）、
  碌 liu（碌碡）、榜 beng（榜人）、平 pian（平章）、舚 tian、乣 diu、
  弸 peng、摵 she、踶 zhi、髿 suo、椆 diao、杕 duo、勺 zhuo（舞勺）。
  补读对齐上游自身词条口径（底本里 道行 dao heng 已存在而 行 缺 heng）。

`luna_pinyin.dict.yaml`: 67164 → **67176** 条（+68 读音、−56 读音，
净 +12）。`essay.txt` 与 `opencc/` 未动，逐字节复现通过。

## v1.1.9-rime-stack

两个数据 commit 之后词库内容已变，本次给当前内容一个版本坐标（此前最新 tag
`v1.1.8-rime-stack` 停在简体化之前，dict 内容无 tag）。

### 全部转简体

`essay.txt` 与 `luna_pinyin.dict.yaml` 原为繁体（上游 rime-essay / luna_pinyin 都是
繁体），靠 `luna_pinyin_simp` 的 simplifier 转简体上屏；现在两库内容本身已是简体，
simplifier 退化为幂等护栏。

- `essay.txt`: 442688 -> **437873** 条（转简体 + 按词去重取最大权重）
- `luna_pinyin.dict.yaml`: 70655 -> **67164** 条 (词,拼音) 对（按对去重，同词多读音保留独立行）

两个坑写进 `dict/README.md`：`乾`(gān/qián)、`薹`(tái) 是合法简体字但 opencc `t2s`
会误转，需逐字保护；一简对多繁需按 (词,拼音) 对去重而非只按词去重。

### essay 升级

`essay.txt` 升级到 rime-essay 官方最新版（442688 条），并修正授权标注：essay.txt
派生自 rime/rime-essay，按 LGPL-3.0 授权，其余文件为 MIT。

## v1.1.0-rime-stack.1

词库并入本仓（原先在 `adam-ikari/term-ime-dict`）：

- `luna_pinyin.dict.yaml` —— 70655 条字词
- `essay.txt` —— 297731 条词频
- `opencc/` —— 简繁转换数据

词库内容与 `term-ime-dict` 的 `v1.0.0` 完全一致，本次只是换了位置，没有改动任何
一个字节。目的是让「用哪个 librime」与「用哪个词库」变成同一个版本坐标。

并入前的独立版本记录见 git 历史里 `dict/` 之前的独立仓；词库自 v1.0.0 起的内容
未变。