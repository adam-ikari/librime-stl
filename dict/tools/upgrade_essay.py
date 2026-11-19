#!/usr/bin/env python3
"""Regenerate dict/essay.txt from its traditional source.

essay.txt is the preset vocabulary (`use_preset_vocabulary`), i.e. where phrase
candidates come from. It is not a convenience file: without it candidates degrade
to codepoint-ordered single characters. So the generation contract below is
load-bearing for input quality, not just for reproducibility.

The traditional source is upstream rime/rime-essay@054920de (see `essay-base` in
sources.lock), which this repo carried as a committed dict/essay.txt before the
2026-10 simplification. It is read from git history rather than fetched over the
network for the same reason convert_dict.py reads its luna_pinyin base that way:
the reproduction gate must run offline and must not depend on
raw.githubusercontent's intermittent truncation of this 5.6 MB file.

Contract:
  * take every entry -- 437873 of them -- and trim none. 91.2% of these words
    are absent from luna_pinyin.dict.yaml, so "unused" entries are exactly the
    ones that make long phrases reachable.
  * character-level traditional -> simplified only (see t2s_char.json). Phrase
    tables would rewrite lexically distinct words (家俱 -> 家具) and the variant
    tables would fold rare codepoints onto a common one (㐀 -> 丘); a dictionary
    re-encoding must not do either.
  * keep protected characters (乾, 薹) as they are.
  * collapse entries that collide after conversion, keeping the highest weight.
  * merge the pinned rime-ice snapshot's word frequencies: a word already in
    rime-essay keeps this repo's weight (its ranking is already calibrated);
    a word only in rime-ice is added with its highest rime-ice weight scaled
    into (0, 1), so additions rank among themselves but never outrank an
    existing word whose weight is at least 1. Its weight-only tencent table is
    part of this merge; its reading tables are not.
  * order by codepoint, which is byte order under UTF-8.
"""

import argparse
import pathlib
import subprocess
import sys
import tarfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import t2s

REPO_ROOT = t2s.HERE.parent.parent


def base_from_git():
    sha = t2s.pin("essay-base")
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"{sha}:dict/essay.txt"],
        capture_output=True, text=True)
    if proc.returncode:
        sys.exit(
            f"cannot read base {sha} from git history:\n{proc.stderr.strip()}\n"
            "This repo was probably cloned with --depth. Fetch the object first:\n"
            f"  git fetch --depth=1 origin {sha} && git cat-file -e {sha}^{{commit}}")
    return proc.stdout


RIME_ICE_TABLES = ("8105", "base", "ext", "others", "tencent")

def rime_ice_weights():
    """Read the pinned rime-ice snapshot and return {word: highest weight}.

    Only rows with a numeric weight are useful here: the reading tables carry
    (word, syllables, weight), tencent carries (word, weight), and 41448 has no
    weight at all. The snapshot is vendored as a tarball so regeneration stays
    offline, the same contract as the git-history bases above.
    """
    sha = t2s.pin("rime-ice-base")
    archive = pathlib.Path(__file__).resolve().parent / "upstream" / f"rime-ice-{sha}.tar.gz"
    if not archive.exists():
        sys.exit(f"missing vendored rime-ice snapshot: {archive}")
    rows = []
    with tarfile.open(archive, "r:gz") as tf:
        for name in RIME_ICE_TABLES:
            member = tf.getmember(f"cn_dicts/{name}.dict.yaml")
            lines = tf.extractfile(member).read().decode("utf-8").splitlines()
            for line in lines[lines.index("...") + 1:]:
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                fields = line.split("\t")
                if len(fields) == 3 and fields[2].isdigit():
                    rows.append((fields[0], int(fields[2])))
                elif len(fields) == 2 and fields[1].isdigit():
                    rows.append((fields[0], int(fields[1])))
    converted = t2s.simplify("\n".join(w for w, _ in rows)).splitlines()
    best = {}
    for (_, weight), word in zip(rows, converted):
        if word not in best or weight > best[word]:
            best[word] = weight
    print(f"  rime-ice: {len(best)} weighted words from {len(RIME_ICE_TABLES)} tables")
    return best

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="traditional essay.txt; read from git history if omitted")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    source = pathlib.Path(args.input).read_text(encoding="utf-8") if args.input else base_from_git()

    # Upstream ships rime-essay with a # header; the committed product has none.
    body = [l for l in source.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    converted = t2s.simplify("\n".join(body)).splitlines()

    best = {}
    for line in converted:
        word, _, weight = line.partition("\t")
        weight = weight.strip()
        if not word or not weight.isdigit():
            sys.exit(f"unexpected essay line: {line!r}")
        if word not in best or int(weight) > int(best[word]):
            best[word] = weight

    rime = rime_ice_weights()
    ceiling = max(rime.values(), default=0) + 1
    for word, weight in rime.items():
        if word not in best:
            best[word] = f"{weight / ceiling:.9g}"

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(f"{w}\t{best[w]}\n" for w in sorted(best)), encoding="utf-8")
    print(f"{out}: {len(best)} entries (from {len(body)} upstream lines)")


if __name__ == "__main__":
    main()
