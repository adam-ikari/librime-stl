#!/bin/sh
# Regenerate the opencc data directory rime_test converts against, from the
# vendored opencc in ../../deps/opencc. The output is a faithful mirror of what
# opencc's own install target puts in <prefix>/share/opencc: every config in
# data/config plus every .ocd2 those configs reference.
#
# Why it is committed instead of built: the engine's configure/build graph must
# never need a host Python or a host-executed opencc_dict -- both of which are
# opencc's data step (deps/opencc/data/CMakeLists.txt), and both of which
# deps.mk turns off with OPENCC_BUILD_DATA. rime_test still needs a real opencc
# dict directory at configure time, so the generated form is committed here and
# guarded by `make check`, exactly like dict/opencc/.
#
# Everything comes from opencc's own tables; the pin in deps/opencc is what
# makes it reproducible. Never hand-edit the output.
set -eu

out=${1:?usage: rebuild_test_opencc.sh <output-dir>}
build=${OPENCC_BUILD:?OPENCC_BUILD must point at the opencc build tree}
src=${OPENCC_SRC:?OPENCC_SRC must point at the vendored opencc source}

mkdir -p "$out"

for f in "$src"/data/config/*.json; do
	[ -f "$f" ] || { echo "missing $src/data/config/*.json" >&2; exit 1; }
	cp "$f" "$out/"
done

# opencc's data step builds the whole DICTS_RAW + DICTS_GENERATED set; the 14
# configs above are its closure over those files.
for f in "$build"/data/*.ocd2; do
	[ -f "$f" ] || { echo "missing $build/data/*.ocd2 -- run make toolchain first" >&2; exit 1; }
	cp "$f" "$out/"
done

echo "opencc test data -> $out"
