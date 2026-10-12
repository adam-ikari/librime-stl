#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单字读音审计：找出会污染首字母简拼的死读音。

底本（繁体快照）按《汉语大字典》式宽表给单字收了大量古音/通假读法。schema 的
`abbrev/^([a-z]).+$/$1/` 把每个音节缩成首字母，于是「仅」的 fu 一读让 `fff` 能
拼出不可能用现代读音打出来的「不仅仅」。本工具把每条 (字, 读音) 放到三个独立
信号下打分，按字频排序输出待甄别清单：

  phrase   pypinyin 现代词组表（47111 条）里，该字被配成这一音节的次数。
           这是「这个读音今天还能组出词吗」的证据；为零说明只剩单字自己用。
  word     本仓词库的多字词条把该字配成这一音节的次数。有实配的文言读法由词组行
           自己带着音节串，删单字行不影响那个词，所以这一列只作参考。
  norm     该字在 pypinyin 单字宽表（汉典式）里有这一读 —— 有记录不等于现代规范。

判定线：该读音与字的**主导读音**（宽表首项，按常用度排）声母不同，且在 pypinyin
现代词组表与本仓词库的多字词条里**双零实配**——今天没有任何词把它配成这个音。
低频字默认不进清单（`--min-freq`），生僻字的古读是用户真会打的，简拼污染不到。
宽表（attested/error 列）只说明「古书有这个读」，不作为保留理由：底本正是靠
这一列把「仅 fu」塞进来的。

只读，不改数据；`--emit-del` 打印 pinyin_fixes.txt 的 del 行，供人工逐条核对后粘贴。
pypinyin 是开发期 oracle，`make check` / `make smoke` 都不需要它。

另两种读数（补读轴，输出的是 add）：

  --words      词组行只有旧读。逐条检查多字词条的每个 (字, 音节)，宽表没有这一读
              的就是底本音节串错误（蚌埠市 bang fu shi 那一类）；但「旧读还在」不
              等于「打不出词」，底本对多数新旧两读的词各留一行。`--confirmed-only`
              只留下第三种：现代规范读音在该词现有各行里根本打不出来。
  --coverage   单字缺规范读导致的组词盲区。取 essay 里词库没有的词（引擎靠单字行
              组合词组，主词库故意不收能组出的词），只要该字没有这一读的单字行，
              ScriptEncoder 就组不出它。按「被卡词的 essay 词频之和」排序，
              `--min-weight` 设下限。

两个轴都可 `--emit-fix` 直接出 add 行（--words 出词组行，--coverage 出单字行）；
这只是草稿，pypinyin 按上下文猜的读音（精雕细琢它给 zuo）必须人工查字典否掉。

Usage:
    python3 audit_readings.py [--min-freq 1000] [--limit 400] [--emit-del]
    python3 audit_readings.py --words [--confirmed-only] [--emit-fix] [--limit 60]
    python3 audit_readings.py --coverage [--top-words 437873] [--min-weight 100]
                              [--emit-fix] [--limit 60]
"""

import argparse
import collections
import pathlib
import sys

try:
    from pypinyin import pinyin, Style
    from pypinyin.contrib.tone_convert import to_normal
    from pypinyin.phrases_dict import phrases_dict
    from pypinyin.pinyin_dict import pinyin_dict
except ImportError:
    sys.exit("需要 pypinyin 作对照：pip install pypinyin")

HERE = pathlib.Path(__file__).resolve().parent
DICT = HERE.parent / "luna_pinyin.dict.yaml"
ESSAY = HERE.parent / "essay.txt"
FIXES = HERE / "pinyin_fixes.txt"

# 叹词/语气词：读音全靠约定俗成，宽表与现代词组表都收不全，按「无记录即错音」
# 判会把「啊 o」「呵 ó」「噢 ò」这类真读法一起打死。这一类不进自动清单。
INTERJECTIONS = set("啊呵噢哦喔嗯咯呢吗吧呀哈咦哎唉嘻哼呸呗嘛哇耶咩哟唷嘞哒")


def load_rows(path):
    started = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() == "...":
            started = True
            continue
        if not started or not line.strip() or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) >= 2:
            yield fields[0], " ".join(fields[1].split())


def load_essay_freq(path):
    freq = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "\t" not in line:
            continue
        word, weight = line.rsplit("\t", 1)
        try:
            freq[word.strip()] = int(weight)
        except ValueError:
            pass
    return freq


def load_fixes_adds(path):
    """pinyin_fixes.txt 里显式补过的读音：审计不得建议删掉它们。"""
    adds = set()
    if not path.exists():
        return adds
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) == 3 and fields[0] == "add" and len(fields[1]) == 1:
            adds.add((fields[1], fields[2].strip()))
    return adds


def audit_words(args, freq, char_norms, char_syllables, words):
    """词组行读音审计：宽表没有这一读的词组行，逐条给证据。

    宽表缺记录有两成因：底本这一行真错，或 pypinyin 表本身不全；而「旧读还在」也
    不等于「打不出来」——底本对多数新旧两读的词各留一行（摇曳 yao ye / yao yi 都
    在）。所以真正的缺陷只有一种：现代规范读音在本仓这个词的现有各行里根本打不出
    来。只有这种才值得动数据，其余一律不改。
      宽表   pypinyin 单字宽表里该字的全部读音
      单字   本仓词库该字的单字行读音（与词组行自相矛盾即错）
      词表   pypinyin 现代词组表对这个词的读音
    """
    readings = collections.defaultdict(set)
    for word, syllables in words:
        readings[word].add(syllables)

    bad = []
    for word, syllables in words:
        cells = syllables.split()
        if len(cells) != len(word):
            continue
        wrong = [(char, syl) for char, syl in zip(word, cells)
                 if char in char_norms and syl not in char_norms[char]]
        if wrong:
            bad.append((freq.get(word, 0), word, syllables, wrong))
    bad.sort(key=lambda r: -r[0])

    actionable = []
    suspect_rows = []
    for f, word, syllables, wrong in bad:
        exact = word in phrases_dict
        word_reading = " ".join(
            to_normal(cell[0]) for cell in phrases_dict[word]) if exact else \
            " ".join(cell[0] for cell in pinyin(word, style=Style.NORMAL))
        mismatch = exact and word_reading.split() != syllables.split()
        untypeable = mismatch and word_reading not in readings[word]
        label = ("词表精配不符" + ("，且现代读打不出来" if untypeable else "，但另有该行")) if mismatch else (
            "词表精配一致（宽表不全，非错音）" if exact else
            "词表无此词（回退单字默认，非证据）")
        row = (f, word, syllables, wrong, word_reading, label)
        suspect_rows.append(row)
        if untypeable:
            actionable.append(row)

    if args.emit_fix:
        for f, word, syllables, wrong, word_reading, label in actionable:
            print(f"add\t{word}\t{word_reading}")
        return actionable

    shown = actionable if args.confirmed_only else suspect_rows
    for f, word, syllables, wrong, word_reading, label in shown[: args.limit]:
        marks = []
        for char, syl in wrong:
            evidence = ",".join(sorted(char_norms[char])) or "-"
            own = "/".join(sorted(char_syllables.get(char, []))) or "-"
            marks.append(f"{char}={syl} | 宽表[{evidence}] 单字行[{own}]")
        have = "/".join(sorted(readings[word]))
        print(f"{word}  freq={f}  现有行: {have}")
        for m in marks:
            print(f"    {m}")
        print(f"    {label}: {word_reading}")
    print(f"\n词组行嫌疑 {len(suspect_rows)} 条，其中 {len(actionable)} 条现代规范读"
          f"音在本仓根本打不出来（需要 add）；显示前 "
          f"{min(args.limit, len(shown))} 条"
          + ("（仅需 add 者）" if args.confirmed_only else ""))
    return actionable


def audit_coverage(args, freq, dict_words, char_norms, char_syllables):
    """essay 里词库没有的高频词，因单字缺读音而组不出来的盲区。

    pypinyin 认不出的字（生僻扩展码位）会把字本身吐回来，这类不算证据。剩下的缺口
    按宽表分两档：宽表有此读 = 词库漏收，`add` 有据；宽表无此读 = pypinyin 按上下
    文猜的读音，可能是它自己错（精雕细琢它给 zuo，规范是 zhuo），只能人工查字典。
    """
    blocked = collections.Counter()
    owners = collections.defaultdict(list)
    weight = collections.Counter()
    ranked = sorted(freq.items(), key=lambda kv: -kv[1])[: args.top_words]
    for word, f in ranked:
        if word in dict_words or len(word) < 2:
            continue
        reading = [x[0] for x in pinyin(word, style=Style.NORMAL)]
        if len(reading) != len(word):
            continue
        for char, syllable in zip(word, reading):
            if not syllable.isascii():
                continue            # pypinyin 不认识这个字，不是词库的错
            if syllable not in char_syllables.get(char, ()):
                blocked[(char, syllable)] += 1
                weight[(char, syllable)] += f
                owners[(char, syllable)].append((f, word))
    rows = sorted((kv for kv in blocked.items()
                   if weight[kv[0]] >= args.min_weight),
                  key=lambda kv: -weight[kv[0]])
    if args.emit_fix:
        for (char, syllable), n in rows:
            if syllable in char_norms.get(char, ()):
                print(f"add\t{char}\t{syllable}")
        return rows
    for (char, syllable), n in rows[: args.limit]:
        sample = "、".join(w for _, w in sorted(owners[(char, syllable)], reverse=True)[:3])
        attested = "宽表有" if syllable in char_norms.get(char, ()) else "宽表无"
        own = "/".join(sorted(char_syllables.get(char, ()))) or "整字缺"
        print(f"{char} {syllable:<7} 卡住 {n:>4} 词  加权 {weight[(char, syllable)]:>8}  "
              f"{attested}  现有[{own}]  例：{sample}")
    total = sum(n for _, n in rows)
    attested = sum(1 for ((c, s), _) in rows if s in char_norms.get(c, ()))
    print(f"\n组词盲区 {len(rows)} 个 (字,读音)，涉及被卡词条 {total}；其中宽表有记录"
          f"（可直接 add）{attested} 个")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-freq", type=int, default=1000)
    ap.add_argument("--limit", type=int, default=400)
    ap.add_argument("--emit-del", action="store_true",
                    help="输出 pinyin_fixes.txt 的 del 行而不是表格")
    ap.add_argument("--include-attested", action="store_true",
                    help="把宽表有记录的读法也计入（默认只出无记录纯错音）")
    ap.add_argument("--words", action="store_true", help="词组行错音审计")
    ap.add_argument("--confirmed-only", action="store_true",
                    help="词组行审计只出现代规范读音根本打不出来的")
    ap.add_argument("--emit-fix", action="store_true",
                    help="对需补读的词组行输出 add 行（读音取自现代词组表，仍须逐条核对）")
    ap.add_argument("--coverage", action="store_true", help="组词盲区审计")
    ap.add_argument("--top-words", type=int, default=20000,
                    help="盲区审计取 essay 词频前 N 条（默认 20000）")
    ap.add_argument("--min-weight", type=int, default=0,
                    help="盲区审计只看被卡词频之和不低于 N 的 (字,读音)")
    args = ap.parse_args()

    freq = load_essay_freq(ESSAY)
    char_norms = collections.defaultdict(set)
    first_norm = {}
    for codepoint, toned_list in pinyin_dict.items():
        char = chr(codepoint)
        for toned in toned_list.split(","):
            char_norms[char].add(to_normal(toned))
        if toned_list:
            first_norm[char] = to_normal(toned_list.split(",")[0])

    char_syllables = collections.defaultdict(set)
    words = []
    for word, syllables in load_rows(DICT):
        if len(word) == 1:
            char_syllables[word].add(syllables)
        else:
            words.append((word, syllables))

    if args.words:
        audit_words(args, freq, char_norms, char_syllables, words)
        return 0
    if args.coverage:
        audit_coverage(args, freq, {w for w, _ in words}, char_norms,
                       char_syllables)
        return 0

    word_support = collections.Counter()
    for word, syllables in words:
        cells = syllables.split()
        if len(cells) != len(word):
            continue
        for char, syllable in zip(word, cells):
            word_support[(char, syllable)] += 1

    phrase_counter = collections.Counter()
    for phrase, syllables in phrases_dict.items():
        cells = [to_normal(cell[0]) for cell in syllables]
        if len(cells) != len(phrase):
            continue
        for char, syllable in zip(phrase, cells):
            phrase_counter[(char, syllable)] += 1

    def dominant_of(char, syllables):
        """该字的主导读音：先按语料实配（词库词组 + 现代词组），再退回宽表首位。

        宽表首位不可靠 —— 「份」的第一项是古读 bìn，照它判会把正读 fen 当成毒。
        """
        return max(syllables,
                   key=lambda s: (word_support[(char, s)] + phrase_counter[(char, s)],
                                  s == first_norm.get(char)), default=None)

    adds = load_fixes_adds(FIXES)
    rows = []
    for char, syllables in char_syllables.items():
        f = freq.get(char, 0)
        if f < args.min_freq or char in INTERJECTIONS:
            continue
        dom = dominant_of(char, syllables)
        if not dom:
            continue
        for syllable in sorted(syllables):
            if (char, syllable) in adds:
                continue            # 本轮显式补过的读音，不动
            if syllable[0] == dom[0]:
                continue            # 与主导读音同声母，简拼不会跑偏
            if phrase_counter[(char, syllable)] or word_support[(char, syllable)]:
                continue            # 有词组真把它配成这一音，删了打死组词
            norm = "attested" if syllable in char_norms[char] else "error"
            if norm == "attested" and not args.include_attested:
                continue            # 有文献记录的读法，留给人工判定
            rows.append((f, char, syllable, norm, dom))
    rows.sort(key=lambda r: -r[0])

    if args.emit_del:
        for f, char, syllable, norm, dom in rows:
            print(f"del\t{char}\t{syllable}")
        return 0

    print(f"{'字':<3} {'读音':<6} {'字频':>9}  {'宽表':<9} 主导")
    for f, char, syllable, norm, dom in rows[: args.limit]:
        print(f"{char:<3} {syllable:<6} {f:>9}  {norm:<9} {dom}")
    print(f"\n候选 {len(rows)} 条：字频>={args.min_freq}、与主导读声母冲突、"
          f"且在现代词组表与本仓词库中双零实配")
    return 0


if __name__ == "__main__":
    sys.exit(main())
