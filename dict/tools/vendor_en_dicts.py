#!/usr/bin/env python3
"""Vendor rime-ice's English dictionaries verbatim from the pinned snapshot.

They are Latin-script tables for the separate English schema, not pinyin
entries, so they are copied byte-for-byte rather than run through t2s or
merged into luna_pinyin.dict.yaml. Same offline, pinned-input contract as the
other generators.
"""

import argparse
import pathlib
import sys
import tarfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import t2s

FILES = ("en.dict.yaml", "en_ext.dict.yaml")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    sha = t2s.pin("rime-ice-base")
    archive = pathlib.Path(__file__).resolve().parent / "upstream" / f"rime-ice-{sha}.tar.gz"
    if not archive.exists():
        sys.exit(f"missing vendored rime-ice snapshot: {archive}")
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tf:
        for name in FILES:
            data = tf.extractfile(f"en_dicts/{name}").read()
            (out_dir / name).write_bytes(data)
            print(f"{out_dir / name}: {len(data)} bytes")

if __name__ == "__main__":
    main()
