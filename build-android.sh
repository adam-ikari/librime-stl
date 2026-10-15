#!/bin/sh
# Cross-compile the Android engine library: librime.so with a plain C API.
#
# The dictionary toolchain (dict/tools/) is not involved -- this builds the
# engine only; the runtime dictionary data (dict/) is packaged by the consumer
# (see dict/README.md). deps.mk's flag table keeps opencc's data and tools off,
# which is what this script asks the table for instead of deciding per library:
# generating that data needs a host Python plus a freshly built host opencc_dict,
# and under cross compilation that dies with Exec format error.
# See deps/opencc/UPSTREAM.md.
#
# This tree is a separate build graph from build/, and hermetic on purpose: every
# dependency is cross-built from deps/<dep> into $prefix, and the engine
# configure is handed -DRIME_DEPS_PREFIX=$prefix so it fails rather than quietly
# resolving a dependency from the host. What that buys the consumer is a
# librime.so that has already absorbed opencc's static code -- verify_artifact
# below proves it, and README-android.md states what the JNI layer then needs.
#
# Usage: NDK=/path/to/android-ndk-r28 ./build-android.sh [arm64-v8a|armeabi-v7a|x86_64]
# Environment: CLEAN=1 discards the build tree for this ABI before configuring.
#              VERIFY_ONLY=1 skips every build step and re-checks a librime.so
#              with the same assertions used after a build: by default the one
#              this script produced for the requested ABI, or VERIFY_ARTIFACT=path
#              to check any library (a host build's librime.so must fail them).
#              NDK is only required for the checks it needs a tool for; readelf
#              and nm fall back to PATH.
# Output: build/android-<abi>/rime/lib/librime.so
set -eu

: "${NDK:=}"
abi=${1:-arm64-v8a}
platform=android-21
toolchain="$NDK/build/cmake/android.toolchain.cmake"

rime_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
build="$rime_root/build/android-$abi"
prefix="$build/prefix"
lib="$build/rime/lib/librime.so"

find_tool() {
	for candidate in "$NDK"/toolchains/llvm/prebuilt/*/bin/"$1"; do
		[ -x "$candidate" ] && {
			echo "$candidate"
			return 0
		}
	done
	command -v "llvm-$1" 2>/dev/null || command -v "$1" 2>/dev/null || true
}

# The claims README-android.md used to make in prose, executed against the
# artifact instead. A dependency that leaked in from the build host shows up as a
# NEEDED entry -- and would mean the engine linked an opencc other than the
# vendored pin that generated dict/opencc/.
verify_artifact() {
	readelf_tool=$(find_tool readelf)
	[ -n "$readelf_tool" ] || { echo "no readelf to verify $1" >&2; return 1; }
	nm_tool=$(find_tool nm)
	[ -n "$nm_tool" ] || { echo "no nm to verify $1" >&2; return 1; }

	needed=$("$readelf_tool" --dynamic "$1" | sed -n 's/.*(NEEDED).*\[\(.*\)\]/\1/p')
	# Empty means the tool or the parse failed, not that the library is clean: a
	# shared librime always needs bionic's libc.
	[ -n "$needed" ] || { echo "no NEEDED entry parsed from $1" >&2; return 1; }

	unexpected=""
	for entry in $needed; do
		# bionic's own libraries are the only acceptable entries; anything else
		# means a dependency was taken as a host shared object rather than being
		# cross-built static into $prefix.
		case "$entry" in
			liblog.so* | libm.so* | libdl.so* | libc.so*) ;;
			*) unexpected="$unexpected $entry" ;;
		esac
	done
	if [ -n "$unexpected" ]; then
		echo "$1 links unexpected shared dependencies:$unexpected" >&2
		echo "Expected only bionic (liblog.so libm.so libdl.so libc.so): every dep is" >&2
		echo "cross-built static into $prefix." >&2
		return 1
	fi

	"$nm_tool" -D --defined-only "$1" | grep -q ' T rime_get_api' || {
		echo "$1 does not export rime_get_api as an unmangled C symbol" >&2
		return 1
	}

	echo "OK $1"
	echo "   NEEDED: $(echo "$needed" | tr '\n' ' ')"
	echo "   exports: rime_get_api"
}

if [ "${VERIFY_ONLY:-0}" = "1" ]; then
	target=${VERIFY_ARTIFACT:-$lib}
	[ -f "$target" ] || { echo "no librime.so at $target to verify" >&2; exit 1; }
	verify_artifact "$target"
	exit 0
fi

[ -n "$NDK" ] || { echo "set NDK to the Android NDK root, e.g. NDK=/opt/android-ndk-r28" >&2; exit 1; }
[ -f "$toolchain" ] || { echo "no toolchain file at $toolchain" >&2; exit 1; }

# cmake --fresh (>= 3.24) re-configures without the previous cache, so a
# dependency rebuilt into $prefix cannot stay resolved to its old path through
# cache inertia. Older cmake still gets the stamp check below, which catches a
# different toolchain, ABI or platform being pointed at this tree.
cmake_version=$(cmake --version | head -1 | awk '{print $3}')
fresh=""
if [ "$(printf '%s\n' 3.24 "$cmake_version" | sort -V | head -1)" = "3.24" ]; then
	fresh="--fresh"
fi

stamp="$build/.rime-android-stamp"
want_stamp="$toolchain|$abi|$platform"
if [ "${CLEAN:-0}" = "1" ]; then
	rm -rf "$build"
elif [ -f "$stamp" ] && [ "$(cat "$stamp")" != "$want_stamp" ]; then
	echo "== stale cross build tree for $abi (toolchain/ABI/platform changed); wiping $build =="
	rm -rf "$build"
elif [ -f "$build/rime/CMakeCache.txt" ] && [ ! -f "$stamp" ]; then
	# A tree this script did not create: someone configured it by hand, or it
	# predates the stamp. Wiping it silently could destroy their work.
	echo "$build/rime was configured without this script's stamp; refusing to reuse it." >&2
	echo "Re-run with CLEAN=1 to discard $build, or remove it yourself." >&2
	exit 1
fi
mkdir -p "$build"
printf '%s' "$want_stamp" >"$stamp"

# CMAKE_FIND_ROOT_PATH must include $prefix: the NDK toolchain file sets
# FIND_ROOT_PATH_MODE_LIBRARY=ONLY, so the engine's find modules would otherwise
# only see the sysroot and never the static deps we install there.
common="-DCMAKE_TOOLCHAIN_FILE=$toolchain -DANDROID_ABI=$abi -DANDROID_PLATFORM=$platform \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$prefix \
  -DCMAKE_FIND_ROOT_PATH=$prefix -DCMAKE_POSITION_INDEPENDENT_CODE=ON"

# The policy for each dependency is declared once, in deps.mk's flag table. This
# asks that table instead of keeping a second copy here: the two copies drifted
# once (glog's WITH_UNWIND), and a drifted flag only shows up as a link failure on
# whichever machine happens to have the package the flag depends on.
dep_flags() {
	make -C "$rime_root" -f deps.mk --no-print-directory print-flags DEP="$1"
}

jobs=$(nproc 2>/dev/null || echo 4)

# googletest is in deps.mk's list but not here: this configure sets
# BUILD_TEST=OFF, so no rime_test target needs it on the device side.
for dep in glog leveldb marisa-trie opencc yaml-cpp; do
	echo "== $dep ($abi) =="
	flags=$(dep_flags "$dep")
	# An empty flag list would make the cmake line above succeed with defaults:
	# silence here is not a pass, so refuse before configuring.
	[ -n "$flags" ] || { echo "deps.mk declares no build flags for $dep" >&2; exit 1; }
	cmake -S "$rime_root/deps/$dep" -B "$build/$dep" $fresh $common $flags
	cmake --build "$build/$dep" --target install -j"$jobs"
done

echo "== librime ($abi) =="
cmake -S "$rime_root" -B "$build/rime" $fresh $common \
	-DBUILD_SHARED_LIBS=ON -DBUILD_STATIC=ON \
	-DBUILD_TEST=OFF -DBUILD_SAMPLE=OFF \
	-DCMAKE_PREFIX_PATH="$prefix" \
	-DRIME_DEPS_PREFIX="$prefix"
cmake --build "$build/rime" --target rime -j"$jobs"

[ -f "$lib" ] || { echo "no librime.so at $lib" >&2; exit 1; }
verify_artifact "$lib"
