#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single-character reading audit: find the dead readings that hijack
initial-only (abbreviated) input.

The base snapshot ships a 《汉语大字典》-style broad reading table per character,
full of archaic and loan readings. The schema's
`abbrev/^([a-z]).+$/$1/` collapses every syllable to its initial, so the `fu`
reading of 仅 lets `fff` spell 不仅仅 -- a word no modern reading could type.
This tool scores each (character, reading) against three independent signals and
prints the shortlist, ordered by character frequency:

  phrase   times pypinyin's modern phrase table (47111 entries) pairs this
           character with this syllable -- evidence that the reading still
           composes words today; zero means only the character itself uses it.
  word     times this repo's own multi-character entries pair the character with
           this syllable. A literary reading with real support carries its own
           syllable string on the phrase row, so deleting the single-character
           row does not affect that word; this column is reference only.
  norm     whether pypinyin's broad per-character table (Handian-style) records
           this reading at all -- a record is not a modern standard.

The cut line: the reading's initial differs from the character's **dominant**
reading (first item of the broad table, ranked by currency) AND the reading has
zero real support in both the pypinyin phrase table and this repo's multi-char
entries -- nothing today pairs the character with that sound. Low-frequency
characters stay out of the list by default (`--min-freq`): users really do type
the archaic readings of rare characters, and abbreviation cannot pollute what
they type. The broad table (the attested/error column) only says "some old book
has this reading"; it is not a reason to keep one -- that column is exactly how
the base smuggled in 仅 fu.

Read-only, writes no data; `--emit-del` prints pinyin_fixes.txt `del` lines to be
checked against a dictionary by hand and pasted. pypinyin is a development-time
oracle: neither `make check` nor `make smoke` needs it.

Two further modes (the add-readings axis, which emits `add`):

  --words      phrase rows carrying only an archaic reading. Checks every
               (character, syllable) of each multi-character entry; one absent
               from the broad table is a bad syllable string in the base (the
               蚌埠市 bang fu shi kind). But "the old reading survives" is not
               "the word cannot be typed" -- the base keeps a row per reading for
               most words. `--confirmed-only` keeps only the third case: the
               modern standard reading cannot be typed by any row the word has.
  --coverage   composition blind spots from a character missing its standard
               reading. Takes essay words the dictionary does not have (the
               engine composes phrases from single-character rows, so the main
               dictionary deliberately omits anything composable): without a
               single-character row for that reading, ScriptEncoder cannot build
               the word. Ranked by the summed essay frequency of the blocked
               words, floored by `--min-weight`.

Both axes take `--emit-fix` to print `add` lines directly (--words for phrase
rows, --coverage for single characters); that is a draft only -- pypinyin's
context guesses (it says zuo for 精雕细琢) have to be vetoed against a dictionary.

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

# Interjections and sentence particles: their readings are pure convention, so
# neither the broad table nor the modern phrase table records them all. Judging
# "absent means wrong" would kill real readings such as 啊 o / 呵 ó / 噢 ò along
# with the errors. This class never enters the automatic list.
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
    """The readings this repo added explicitly in pinyin_fixes.txt: the audit
    must never propose deleting them."""
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
    """Phrase-row reading audit: for every row whose syllable the broad table
    does not record, print the evidence.

    Two causes produce a missing broad-table record: the base row is genuinely
    wrong, or pypinyin's own table is incomplete. And "the old reading survives"
    still does not mean "untypeable" -- the base keeps one row per reading for
    most such words (摇曳 has both yao ye and yao yi). So there is exactly one
    real defect: the modern standard reading cannot be typed by any row this repo
    has for the word. Only that justifies touching the data; everything else
    stays.
      broad    every reading pypinyin's per-character table lists for the character
      single   the character's single-character rows in this repo's dictionary
               (a phrase row contradicting them is the error)
      phrase   pypinyin's modern phrase table reading for this word
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
    """Composition blind spots: frequent essay words the dictionary cannot build
    because a character is missing a reading.

    For characters pypinyin does not know (rare extended code points) it echoes
    the character back; that is not evidence. The remaining gaps split in two by
    the broad table: recorded there means the dictionary omits it, so `add` is
    attested; absent means a context guess by pypinyin, possibly its own error (it
    says zuo where the standard is zhuo), which only a hand dictionary check can
    settle.
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
                continue            # pypinyin does not know this character; not the dictionary's fault
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
        """The character's dominant reading: ranked by corpus support (this
        dictionary's phrases + the modern phrase table), falling back to
        the broad table's first entry.

        That first entry is not trustworthy -- for the character 份 it is
        the archaic bin, which would brand the correct fen as the poison.
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
                continue            # added explicitly in this round; leave it alone
            if syllable[0] == dom[0]:
                continue            # same initial as the dominant reading; abbreviation cannot drift
            if phrase_counter[(char, syllable)] or word_support[(char, syllable)]:
                continue            # phrases really do pair it with this sound; deleting it kills composition
            norm = "attested" if syllable in char_norms[char] else "error"
            if norm == "attested" and not args.include_attested:
                continue            # a reading with literary attestation; leave it to hand review
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
