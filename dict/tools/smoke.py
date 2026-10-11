#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End-to-end smoke test: load dict/ with the real engine and check candidates.

`make check` byte-compares the generated products against what is committed.
That cannot tell whether the engine can actually *use* them: an untoned pinyin
column, a schema pattern this fork's std::regex cannot compile, a dictionary
entry the table builder rejects -- none of those show up as a diff. This script
answers the other half of the question by deploying dict/ the way an install
does (engine data from data/minimal/, dictionary and essay from dict/, both
overriding the minimal ones) and driving rime_console against it.

Two kinds of check:

  1. the deployment must build with zero glog error lines. A pattern or entry
     that fails to compile is exactly the class of problem that is otherwise
     invisible until a user's IME misbehaves;
  2. a few probes must commit the expected text, including both readings of a
     polyphone, so a dictionary that only routes the default reading fails.

Usage:
    python3 smoke.py [--rime-console PATH] [--keep]

PATH defaults to <repo>/build/bin/rime_console (the engine build).
Exit status: 0 all green, 1 a check failed, 2 the engine binary is missing.
"""

import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DEFAULT_CONSOLE = REPO_ROOT / "build" / "bin" / "rime_console"

# engine data that luna_pinyin.schema.yaml pulls in
ENGINE_DATA = [
    "luna_pinyin.schema.yaml",
    "cangjie5.schema.yaml",
    "cangjie5.dict.yaml",
    "default.yaml",
    "symbols.yaml",
]
# the dictionary this repo ships, overriding data/minimal's copy
DICT_DATA = [
    "essay.txt",
    "luna_pinyin.dict.yaml",
]

# glog prints errors as `E1011 10:00:00.000000 1234 file.cc:42] message`
GLOG_ERROR = re.compile(r"^E\d{4}\s", re.MULTILINE)

# key sequence -> text rime_console must commit on Enter. Polyphones appear
# twice (both readings must reach a candidate); the rest are plain words that
# exercise dictionary lookup, the table builder and preset vocabulary.
PROBES = [
    ("nihao", "你好"),
    ("chonglai", "重来"),   # 重 chóng
    ("zhongyao", "重要"),   # 重 zhòng
    ("xing", "行"),         # 行 xíng
    ("yinyue", "音乐"),     # 音 乐 (yīn yuè), a word whose two syllables
                           # are each also readings of other characters
]


def fail(msg):
    print(f"FAIL {msg}")
    return 1


def build_deployment(root):
    """Lay out a deployment dir: engine data from data/minimal, dict from dict."""
    for name in ENGINE_DATA:
        src = REPO_ROOT / "data" / "minimal" / name
        if not src.exists():
            return f"missing engine data: {src}"
        shutil.copy(src, root / name)
    for name in DICT_DATA:
        src = REPO_ROOT / "dict" / name
        if not src.exists():
            return f"missing dictionary data: {src}"
        shutil.copy(src, root / name)
    (root / "shared.yaml").write_text(
        f"shared_data_dir: {root}\n"
        f"user_data_dir: {root / 'user'}\n"
        "distribution_name: DictSmoke\n"
        "distribution_version: \"smoke\"\n",
        encoding="utf-8")
    (root / "user.yaml").write_text(
        "var:\n  previously_selected_schema: luna_pinyin\n", encoding="utf-8")
    return None


def run_deploy(console, root):
    proc = subprocess.run([str(console), "--build", str(root)], cwd=root,
                          capture_output=True, text=True)
    return proc.stdout + proc.stderr


def probe(console, root, keys):
    proc = subprocess.run([str(console), str(root)], cwd=root,
                          input=f"{keys}\n", capture_output=True, text=True)
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rime-console", default=str(DEFAULT_CONSOLE))
    parser.add_argument("--keep", action="store_true",
                        help="keep the temporary deployment for inspection")
    args = parser.parse_args()

    console = pathlib.Path(args.rime_console)
    if not console.exists():
        print(f"engine binary not found: {console}\n"
              "build it first (make test at the repo root), or pass "
              "--rime-console PATH")
        return 2

    failures = 0
    root = pathlib.Path(tempfile.mkdtemp(prefix="rime-dict-smoke-"))
    try:
        err = build_deployment(root)
        if err:
            return fail(err)

        log = run_deploy(console, root)
        errors = GLOG_ERROR.findall(log)
        if errors:
            failures += fail(
                f"deployment logged {len(errors)} error line(s); the engine "
                "cannot load part of this dictionary/schema:\n"
                + "\n".join(line for line in log.splitlines()
                           if GLOG_ERROR.match(line)))
        else:
            print("OK   deployment builds with zero error lines")

        for keys, expected in PROBES:
            got = probe(console, root, keys)
            if got == expected:
                print(f"OK   {keys} -> {got}")
            else:
                failures += fail(f"{keys} -> {got!r}, expected {expected!r}")
    finally:
        if args.keep:
            print(f"deployment kept at {root}")
        else:
            shutil.rmtree(root, ignore_errors=True)

    if failures:
        print(f"smoke test failed ({failures} check(s))")
        return 1
    print("smoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())