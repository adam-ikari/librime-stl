# a minimal build of third party libraries for static linking

rime_root = $(CURDIR)
src_dir = $(rime_root)/deps

ifndef NOPARALLEL
  MAKEFLAGS += -j$(shell expr $$(nproc 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || getconf NPROCESSORS_ONLN 2>/dev/null || echo 8) + 1)
endif

build ?= build
prefix ?= $(rime_root)

# fork: these are static archives, and on Linux a non-PIC one cannot be linked
# into a shared librime.so -- ld fails with "relocation R_X86_64_PC32 ... can not
# be used when making a shared object". macOS and Windows emit position
# independent code anyway, so this only unblocks the Linux path; build-android.sh
# passes the same flag when it cross-builds these deps.
pic_flags = -DCMAKE_POSITION_INDEPENDENT_CODE:BOOL=ON

rime_deps = glog googletest leveldb marisa-trie opencc yaml-cpp

# fork: one dependency's build-time policy is declared once, in this table. The
# Android cross build reads it from here (`make -f deps.mk print-flags DEP=x`),
# so the two build graphs cannot configure the same library two ways -- they did,
# and glog's WITH_UNWIND was the flag that drifted: a static libglog.a built with
# the default libunwind driver has undefined _U* references that nothing supplies,
# which fails rime_test's link only on hosts that happen to ship libunwind.
#
# BUILD_SHARED_LIBS=OFF is stated instead of inherited. CMake's default is static,
# so today's archives are static by accident of an unset variable, not by policy:
# a toolchain file or caller that turns it ON would silently produce shared
# objects here and the engine would link them into a cross build.
#
# Each entry is one cmake flag per line: the cross script takes the printed value
# as shell words, so a value containing a space would split into two arguments.
glog_flags = \
	-DBUILD_SHARED_LIBS:BOOL=OFF \
	-DBUILD_TESTING:BOOL=OFF \
	-DWITH_GFLAGS:BOOL=OFF \
	-DWITH_UNWIND:STRING=none
googletest_flags = \
	-DBUILD_GMOCK:BOOL=OFF
leveldb_flags = \
	-DBUILD_SHARED_LIBS:BOOL=OFF \
	-DLEVELDB_BUILD_BENCHMARKS:BOOL=OFF \
	-DLEVELDB_BUILD_TESTS:BOOL=OFF
marisa-trie_flags = \
	-DBUILD_SHARED_LIBS:BOOL=OFF \
	-DBUILD_TESTING:BOOL=OFF \
	-DENABLE_TOOLS:BOOL=OFF
opencc_flags = \
	-DBUILD_SHARED_LIBS:BOOL=OFF \
	-DOPENCC_BUILD_DATA:BOOL=OFF \
	-DOPENCC_BUILD_TOOLS:BOOL=OFF
yaml-cpp_flags = \
	-DBUILD_SHARED_LIBS:BOOL=OFF \
	-DYAML_CPP_BUILD_CONTRIB:BOOL=OFF \
	-DYAML_CPP_BUILD_TESTS:BOOL=OFF \
	-DYAML_CPP_BUILD_TOOLS:BOOL=OFF

.PHONY: all clean clean-dist clean-src print-flags $(rime_deps)

all: $(rime_deps)

# Existence is tested with $(value ...), which reads the definition without
# expanding it; the echo expands, exactly like the recipe below does, so a flag
# that references another make variable prints the same text it configures with.
print-flags:
	$(if $(value $(DEP)_flags),,$(error unknown dependency '$(DEP)': no flags declared in deps.mk))
	@echo $(strip $($(DEP)_flags))

clean: clean-src clean-dist

clean-dist:
	git rev-parse --is-inside-work-tree > /dev/null && \
	find $(prefix)/bin $(prefix)/include $(prefix)/lib $(prefix)/share \
	-depth -maxdepth 1 \
	-exec bash -c 'git ls-files --error-unmatch "$$0" > /dev/null 2>&1 || rm -rv "$$0"' {} \; || true
	rmdir $(prefix) 2> /dev/null || true

# note: this won't clean output files under bin/, include/, lib/ and share/.
clean-src:
	for dep in $(rime_deps); do \
		rm -r $(src_dir)/$${dep}/$(build) || true; \
	done

glog:
	cd $(src_dir)/glog; \
	cmake . -B$(build) $(pic_flags) $(glog_flags) \
	-DCMAKE_BUILD_TYPE:STRING="Release" \
	-DCMAKE_INSTALL_PREFIX:PATH="$(prefix)" \
	&& cmake --build $(build) --target install

googletest:
	cd $(src_dir)/googletest; \
	cmake . -B$(build) $(pic_flags) $(googletest_flags) \
	-DCMAKE_BUILD_TYPE:STRING="Release" \
	-DCMAKE_INSTALL_PREFIX:PATH="$(prefix)" \
	&& cmake --build $(build) --target install

leveldb:
	cd $(src_dir)/leveldb; \
	cmake . -B$(build) $(pic_flags) $(leveldb_flags) \
	-DCMAKE_BUILD_TYPE:STRING="Release" \
	-DCMAKE_INSTALL_PREFIX:PATH="$(prefix)" \
	&& cmake --build $(build) --target install

marisa-trie:
	cd $(src_dir)/marisa-trie; \
	cmake . -B$(build) $(pic_flags) $(marisa-trie_flags) \
	-DCMAKE_BUILD_TYPE:STRING="Release" \
	-DCMAKE_INSTALL_PREFIX:PATH="$(prefix)" \
	&& cmake --build $(build) --target install

opencc:
	cd $(src_dir)/opencc; \
	cmake . -B$(build) $(pic_flags) $(opencc_flags) \
	-DCMAKE_BUILD_TYPE:STRING="Release" \
	-DCMAKE_INSTALL_PREFIX:PATH="$(prefix)" \
	&& cmake --build $(build) --target install

yaml-cpp:
	cd $(src_dir)/yaml-cpp; \
	cmake . -B$(build) $(pic_flags) $(yaml-cpp_flags) \
	-DCMAKE_BUILD_TYPE:STRING="Release" \
	-DCMAKE_INSTALL_PREFIX:PATH="$(prefix)" \
	&& cmake --build $(build) --target install
